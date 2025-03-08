import cv2
import torch
import threading
import supervision as sv
from collections import defaultdict
from ultralytics import YOLO
import os
import re
import base64
import sys
import time
import statistics
import datetime
import json
import requests
import pytz
import logging

# Set up logging
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_folder = os.path.join(current_dir, '..','boot','services','utils')
sys.path.append(utils_folder)

from utils import load_config_for_device
from mqtt import publish_log, subscribe_to_topic


ist_tz = pytz.timezone('Asia/Kolkata')
logging.Formatter.converter = lambda *args: datetime.datetime.now(ist_tz).timetuple()

CONFIG_REFRESH_INTERVAL = 300

# Configure logging to write to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # This ensures logs go to stdout
    ]
)

logger = logging.getLogger(__name__)

test_topic = "camera-processing"

def message_handler(client, userdata, message):
    """Handle incoming MQTT messages"""
    try:
        topic = message.topic
        payload = message.payload.decode()
        
        # Try to parse JSON if possible
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            pass  # Keep payload as string if it's not JSON
            
        logger.info(f"Received message on topic {topic}: {payload}")
        
        if topic.startswith(test_topic):
            # Handle system topic messages
            if payload == "reload":
                logger.info("Reloading service")
                # reload service
                os.system(f"sudo systemctl restart {test_topic}")
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")

# Subscribe to topic with message handler after logger is initialized
subscribe_to_topic(test_topic, message_handler)


# Load YOLO model
model = YOLO("yolov8n.pt")

# Initialize Supervision tracker (ByteTrack)
tracker = sv.ByteTrack()

# Update global variables
config_lock = threading.Lock()
global_config = None

def update_config():
    """Continuously update config in background"""
    global global_config
    while True:
        try:
            new_config = load_config_for_device()
            if new_config:  # Only update if we got a valid config
                with config_lock:
                    global_config = new_config
                logger.info(f"Configuration refreshed successfully: \n{json.dumps(new_config, indent=2)}")
        except Exception as e:
            logger.error(f"Error refreshing config: {str(e)}")
        
        time.sleep(CONFIG_REFRESH_INTERVAL)

def get_current_config():
    """Thread-safe getter for current config"""
    with config_lock:
        return global_config

# Latest frame storage with thread lock
latest_frame = None
frame_lock = threading.Lock()

# Dictionary to track unique objects per class
unique_objects = defaultdict(set)  # To count unique objects over time

def capture_frames():
    """ Continuously capture frames and update the latest frame """
    global latest_frame, cap
    connection_attempts = 0
    max_attempts = 3
    retry_delay = 10

    while True:
        current_config = get_current_config()
        if not current_config:
            time.sleep(5)
            continue
            
        current_url = current_config.get('rtspStreamUrl')
        if not current_url:
            logger.error("Missing rtspStreamUrl in configuration")
            publish_log("Missing rtspStreamUrl in configuration", "error")
            time.sleep(5)
            continue
        
        try:
            cap = cv2.VideoCapture(current_url)
            if not cap.isOpened():
                connection_attempts += 1
                logger.warning(f"Failed to open video stream (attempt {connection_attempts}/{max_attempts})")
                
                if connection_attempts >= max_attempts:
                    logger.error(f"Failed to connect to stream after {max_attempts} attempts. Waiting longer before retry.")
                    time.sleep(retry_delay * 2)  # Longer wait after multiple failures
                    connection_attempts = 0
                else:
                    time.sleep(retry_delay)
                continue

            # Reset connection attempts on successful connection
            connection_attempts = 0
            logger.info(f"Successfully connected to video stream {current_url}")

            while cap.isOpened():  # Keep reading while connection is good
                ret, frame = cap.read()
                if not ret:
                    break

                with frame_lock:
                    latest_frame = frame

            # If we exit the while loop, the connection was lost
            logger.warning("Lost connection to video stream")
            cap.release()
            
        except Exception as e:
            logger.error(f"Error in video capture: {str(e)}")
            if cap:
                cap.release()
            time.sleep(retry_delay)

def analyze_image(image_blob):
    try:
        config = get_current_config()  # Use get_current_config instead of direct load
        if not config or 'billboardMonitoring' not in config:
            logger.error("Missing billboard monitoring configuration")
            publish_log("Missing billboard monitoring configuration", "error")
            return None

        OPENROUTER_API_KEY = config['aiApiKey']
        
        if not OPENROUTER_API_KEY:
            publish_log("Missing AI API key", "error")
            return None


        custom_instructions = config['billboardMonitoring'].get('customInstructions', '')
        
        payload = {
            # "model": "qwen/qwen2.5-vl-72b-instruct:free",
            "model": "google/gemini-flash-1.5-8b-exp",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"I am a billboard owner, I want to know if my billboard is running. This is a digital billboard. It should not be pure black or white. Return a JSON response in the structure {{hasScreenDefects:true,illumunated:true, hasPatches:true, isOnline:true, details:'' , currentlyPlaying:''}} that can be used directly in code. Custom instructions will suggest the location of the billboard. Custom instructions: {custom_instructions}"},
                        {
                            "type": "image_url",
                            "image_url":{
                                "url": f"data:image/jpeg;base64,{image_blob}"
                            }
                         }
                    ]
                }
            ]
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        
        if response.status_code == 200:
            response = response.json()
            
            output = response.get("choices")[0].get("message").get("content")
            cleaned_string = match = re.search(r'```json\n(.*?)\n```', output, re.DOTALL)
            
            if match: 
                json_string = match.group(1).strip() # Extract JSON content 
                
                json_object = json.loads(json_string) # Con
                json_object['customInstructions'] = custom_instructions
                
                return json_object
        else:
            return None
    except Exception as e:
        return None

def monitor_billboard():
    global latest_frame
    while True:
        try:
            config = get_current_config()  # Use get_current_config instead of direct load
            if not config or 'billboardMonitoring' not in config :
                logger.error("Missing billboard monitoring configuration, retrying in 60 seconds")
                publish_log("Missing billboard monitoring configuration, retrying in 60 seconds", "error")
                time.sleep(60)
                continue

            with frame_lock:
                if latest_frame is None:
                    time.sleep(10)
                    continue
                frame = latest_frame.copy()
            
            _, buffer = cv2.imencode(".jpg", frame)
            image_blob = base64.b64encode(buffer).decode("utf-8")
            analysis_result = analyze_image(image_blob)

            if not analysis_result:
                time.sleep(60)
                continue

            publish_log(analysis_result, "billboardMonitoring")
            
            monitoring_interval = config['billboardMonitoring'].get('monitoringInterval', 30)
            time.sleep(monitoring_interval * 60)
            
        except Exception as e:
            time.sleep(60)

def process_frames2():
    
    count_window_size = 5
    LONG_STAY_THRESHOLD = 20
    count_window = defaultdict(list)
    prev_stable_count = defaultdict(int)
    global latest_frame
    last_increase_time = time.time()
    all_classes = ['person', 'car','bicycle','motorcycle','bus','train']
    
    last_process_time = time.time()
    while True:
        try:  # Add try-except block for better error visibility
            current_time = time.time()
            if current_time - last_process_time < 1.0:
                continue
                
            with frame_lock:
                if latest_frame is None:
                    continue
                frame = latest_frame.copy()

            # Force flush the output buffer
            sys.stdout.flush()
            
            results = model(frame, verbose=False)[0]
            detections = results.boxes
            class_names = model.names

            raw_count = defaultdict(int)  # Changed to defaultdict for dynamic class handling
            
            if detections is not None:
                for box in detections:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    if conf < 0.3:
                        continue

                    class_name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
                    # Only count if class_name is in our specified list
                    if class_name in all_classes:
                        raw_count[class_name] += 1
                
                        # # Get box coordinates and draw only for specified classes
                        # x1, y1, x2, y2 = map(int, box.xyxy[0])
                        # cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        # cv2.putText(frame, f"{class_name} {conf:.2f} ", (x1, y1 - 10),
                        #         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Specify classes to track like person, car, etc.
            
            
            # Update count window for specified classes only
            for class_name in all_classes:
                count_window[class_name].append(raw_count.get(class_name, 0))
                if len(count_window[class_name]) > count_window_size:
                    count_window[class_name].pop(0)

            ################################
            # 2) Compute stable_count
            ################################
            stable_count = defaultdict(int)  # Changed to defaultdict
            new_count = defaultdict(int)
            for obj in raw_count:
                if count_window[obj]:  # If we have counts for this object
                    stable_count[obj] = int(round(statistics.median(count_window[obj])))

            # 3) Naive Heuristics
            for obj in raw_count:
                if stable_count[obj] > prev_stable_count[obj]:
                    diff = stable_count[obj] - prev_stable_count[obj]
                    last_increase_time = current_time
                    new_count[obj] = diff
                    # print(f"[++++++++++++++++++++++++++++++++] Detected an increase of {diff} {obj}s. previous: {prev_stable_count[obj]} current: {stable_count[obj]}")

            # time_since_increase = current_time - last_increase_time
            # for obj in raw_count:
            #     if time_since_increase > LONG_STAY_THRESHOLD and stable_count[obj] > 0:
            #         new_count[obj] = stable_count[obj]
            #         print(f"[^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^] Long stay triggered, added {stable_count[obj]} {obj}s")
            #         last_increase_time = current_time

            #print stable count for all objects
            # for obj in stable_count:
            # print(f"Stable count for person: {stable_count['person']} new count: {new_count['person']}")

            ################################
            # Add to batch only if stableCount > 0
            ################################

            #create a json object with the new count and the count window
            json_object = {
                "timestamp": int(time.time())*1000,
                "count": new_count
            }


            #publish the json object to mqtt
            if(len(new_count) > 0):
                publish_log(json.dumps(json_object), "traffic")
                sys.stdout.flush()  # Force flush

            prev_stable_count = stable_count

            #print the count window for all objects
            # for obj in count_window:
                # print(f"Count window for {obj}: {count_window[obj]}")
            
        except Exception as e:
            sys.stdout.flush()
            time.sleep(1)  # Add small delay to prevent tight error loops

def process_frames():
    """ Process only the latest frame and track unique objects """
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()

        # Detect objects using YOLO
        results = model(frame)

        # Convert YOLO results to Supervision Tracker format
        detections = sv.Detections.from_ultralytics(results[0])

        detections = tracker.update_with_detections(detections)

         # Extract class labels and tracker IDs
        class_ids = detections.class_id
        class_labels = [model.names[class_id] for class_id in class_ids]
        tracker_ids = detections.tracker_id  # Get tracker IDs
        
        class_ids = detections.class_id
        # class_labels = [model.names[class_id] for class_id in class_ids]
        tracker_ids = detections.tracker_id  # Get tracker IDs
        
        for class_id, track_id in zip(class_ids,tracker_ids):
        
            class_name = model.names[class_id]  # Get class name

            # Check if the object is newly detected
            if track_id not in unique_objects[class_name]:
                unique_objects[class_name].add(track_id)  # Track unique object
                
      
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
# Start threads
def main():
    sys.stdout.flush()
    
    config_thread = threading.Thread(target=update_config, daemon=True)
    capture_thread = threading.Thread(target=capture_frames, daemon=True)
    process_thread = threading.Thread(target=process_frames2, daemon=True)
    billboard_thread = threading.Thread(target=monitor_billboard, daemon=True)

    try:
        config_thread.start()  # Start config update thread first
        time.sleep(2)  # Give it time to get initial config
        capture_thread.start()
        # process_thread.start()
        billboard_thread.start()

        while True:
            sys.stdout.flush()
            time.sleep(1)

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()