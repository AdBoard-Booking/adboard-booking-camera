import cv2
import threading
import supervision as sv
from collections import defaultdict
from ultralytics import YOLO
import datetime
import argparse
import json
import requests
import queue
import logging
import pytz
import os
import sys
import base64
import re
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
utils_folder = os.path.join(current_dir, '..', 'utils')
sys.path.append(utils_folder)

from mqtt import publish_message
import utils

# Configure logging with IST timezone
ist_tz = pytz.timezone('Asia/Kolkata')
logging.Formatter.converter = lambda *args: datetime.datetime.now(ist_tz).timetuple()
logging.basicConfig(level=logging.INFO, format='%(asctime)s IST - %(levelname)s - %(message)s')

# Argument parser
parser = argparse.ArgumentParser(description="Unified Monitoring Service")
parser.add_argument("--verbose", type=int, choices=[0, 1], default=0, 
                    help="Set YOLO model verbosity: 0 (Silent), 1 (Default)")
parser.add_argument("--imgshow", type=int, choices=[0, 1], default=0, 
                    help="Set imgshow: 0 (Silent), 1 (Default)")
args = parser.parse_args()

class MonitoringService:
    def __init__(self):
        self.config = utils.load_config_for_device()
        if not self.config:
            raise Exception("Failed to load configuration")

        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # Common settings
        self.RTSP_URL = self.config.get("rtspStreamUrl", "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")
        self.DEVICE_ID = self.config.get("deviceId", "UNKNOWN")
        self.IMG_SHOW = bool(args.imgshow)

        # Initialize video capture
        self.cap = cv2.VideoCapture(self.RTSP_URL)
        
        # Initialize services based on config
        if "trafficMonitoring" in self.config.get("services", {}):
            self.init_traffic_monitoring()
            
        if "billboardMonitoring" in self.config.get("services", {}):
            self.init_billboard_monitoring()

    def init_traffic_monitoring(self):
        """Simplified initialization without batch processing"""
        logging.info("Initializing traffic monitoring")
        self.traffic_config = self.config["services"]["trafficMonitoring"]
        
        # Initialize YOLO model and tracker
        self.model = YOLO("yolov8n.pt")
        self.tracker = sv.ByteTrack()
        
        # Traffic monitoring specific settings
        self.unique_objects = defaultdict(set)

    def init_billboard_monitoring(self):
        logging.info("Initializing billboard monitoring")
        self.billboard_config = self.config["services"]["billboardMonitoring"]
        self.OPENROUTER_API_KEY = self.billboard_config.get("aiApiKey")

    def capture_frames(self):
        while True:
            ret, frame = self.cap.read()
            if ret:
                with self.frame_lock:
                    self.latest_frame = frame
            else:
                logging.error("Failed to capture frame")
                time.sleep(1)  # Wait before retrying

    def run_monitoring(self):
        """Combined monitoring loop for both traffic and billboard monitoring"""
        billboard_last_check = 0
        billboard_interval = self.billboard_config.get("apiCallInterval", 60) if hasattr(self, 'billboard_config') else 0
        services = self.config.get("services", {})

        while True:
            current_time = time.time()
            
            with self.frame_lock:
                if self.latest_frame is None:
                    time.sleep(0.1)  # Short sleep if no frame
                    continue
                frame = self.latest_frame.copy()

            # Traffic monitoring
            if "trafficMonitoring" in services:
                results = self.model(frame, verbose=bool(args.verbose))
                detections = sv.Detections.from_ultralytics(results[0])
                detections = self.tracker.update_with_detections(detections)

                if detections.tracker_id is not None:
                    self.process_detections(detections, None, datetime.datetime.now())

            # Billboard monitoring
            if "billboardMonitoring" in services and \
               (current_time - billboard_last_check) >= billboard_interval:
                _, buffer = cv2.imencode(".jpg", frame)
                image_blob = base64.b64encode(buffer).decode("utf-8")
                
                analysis_result = self.analyze_billboard_image(image_blob)
                if analysis_result:
                    self.send_billboard_result(analysis_result)
                
                billboard_last_check = current_time

            # Display frame if requested
            if self.IMG_SHOW:
                cv2.imshow("Monitoring", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    def start(self):
        try:
            # Start frame capture thread
            capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
            capture_thread.start()

            # Start combined monitoring thread
            monitoring_thread = threading.Thread(target=self.run_monitoring, daemon=True)
            monitoring_thread.start()

            # Wait for monitoring thread
            monitoring_thread.join()

        except Exception as e:
            logging.error(f"Error in monitoring service: {e}")
        finally:
            self.cap.release()

    def process_detections(self, detections, detection_batch, current_time):
        """Process detections and publish messages immediately"""
        object_counts = defaultdict(int)
        
        # Extract class labels and tracker IDs
        class_ids = detections.class_id
        tracker_ids = detections.tracker_id

        # Count new unique objects
        for class_id, track_id in zip(class_ids, tracker_ids):
            class_name = self.model.names[class_id]
            
            # Check if object is newly detected
            if track_id not in self.unique_objects[class_name]:
                self.unique_objects[class_name].add(track_id)
                object_counts[class_name] += 1

        # Publish message if new objects found
        if object_counts:
            message = {
                "cameraUrl": self.RTSP_URL,
                "deviceId": self.DEVICE_ID,
                "timestamp": int(current_time.timestamp() * 1000),
                "newCount": dict(object_counts),
                "stableCount": {}
            }
            publish_message(json.dumps(message))
            logging.info(f"Published detection message: {message}")

    def analyze_billboard_image(self, image_blob):
        """Analyze billboard image using OpenRouter AI"""
        payload = {
            "model": "qwen/qwen2.5-vl-72b-instruct:free",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "I am a billboard owner, I want to know if my billboard is running. This is a digital billboard. Return a JSON response in the structure {hasScreenDefects:true, hasPatches:true, isOnline:true, details:''}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_blob}"
                            }
                        }
                    ]
                }
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions", 
                headers=headers, 
                json=payload
            )
            
            if response.status_code == 200:
                response_data = response.json()
                output = response_data["choices"][0]["message"]["content"]
                
                # Extract JSON from markdown if present
                json_match = re.search(r'```json\n(.*?)\n```', output, re.DOTALL)
                if json_match:
                    json_string = json_match.group(1).strip()
                    return json.loads(json_string)
                
                # If no markdown, try parsing the whole response
                return json.loads(output)
            else:
                logging.error(f"OpenRouter AI request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error analyzing billboard image: {e}")
            return None

    def send_billboard_result(self, result):
        """Modified to use publish_message"""
        message = {
            "deviceId": self.DEVICE_ID,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            **result
        }

        try:
            publish_message(json.dumps(message))
            logging.info("Billboard analysis results published successfully")
            return True
                
        except Exception as e:
            logging.error(f"Error publishing billboard results: {e}")
            return False

def main():
    try:
        service = MonitoringService()
        service.start()
    except KeyboardInterrupt:
        logging.info("Service stopped by user")
    except Exception as e:
        logging.error(f"Service error: {e}")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 