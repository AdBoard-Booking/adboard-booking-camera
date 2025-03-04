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

current_dir = os.path.dirname(os.path.abspath(__file__))
utils_folder = os.path.join(current_dir, '..','boot','services','utils')
sys.path.append(utils_folder)

from mqtt import publish_log
from utils import load_config_for_device
# Load YOLO model
model = YOLO("yolov8n.pt")

# Initialize Supervision tracker (ByteTrack)
tracker = sv.ByteTrack()

config = load_config_for_device()

def get_rtsp_url():
    try:
        publish_log(f"Config: {config}",'info')
        if not config:
            publish_log("Failed to load configuration",'error')
            return None
            
        rtsp_url = config.get('services', {}).get('billboardMonitoring', {}).get('rtspStreamUrl')
        if not rtsp_url:
            publish_log("No RTSP URL found in configuration",'error')
            return None
            
        return rtsp_url
    except Exception as e:
        print(f"Error fetching RTSP URL: {str(e)}")
        publish_log(f"Error fetching RTSP URL: {str(e)}", "error")
        return None

# Get initial RTSP URL
RTSP_URL = get_rtsp_url()
if not RTSP_URL:
    RTSP_URL = "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2"  # fallback URL
    print(f"Using fallback RTSP URL: {RTSP_URL}")
    publish_log("Using fallback RTSP URL", "warning")

cap = cv2.VideoCapture(RTSP_URL)

# Latest frame storage with thread lock
latest_frame = None
frame_lock = threading.Lock()

# Dictionary to track unique objects per class
unique_objects = defaultdict(set)  # To count unique objects over time

def capture_frames():
    """ Continuously capture frames and update the latest frame """
    global latest_frame, cap, RTSP_URL
    while True:
        if not cap.isOpened():
            print(f"Error: Unable to connect to stream {RTSP_URL}. Retrying in 10 seconds...")
            publish_log("Camera stream connection failed. Retrying in 10 seconds...", "error")
            time.sleep(10)
            cap = cv2.VideoCapture(RTSP_URL)
            continue

        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame. Reconnecting to stream...")
            publish_log("Failed to read frame. Reconnecting to stream...", "error")
            cap.release()
            time.sleep(10)
            cap = cv2.VideoCapture(RTSP_URL)
            continue

        with frame_lock:
            latest_frame = frame

def analyze_image(image_blob):
    billboardMonitoring = config['services']['billboardMonitoring']
    OPENROUTER_API_KEY = billboardMonitoring.get('aiApiKey')
    print("Analyzing image using OpenRouter AI")
    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "I am a billboard owner, I want to know if my billboard is running. This is a digital billboard. Return a JSON response in the structure {hasScreenDefects:true, hasPatches:true, isOnline:true, details:''} that can be used directly in code."},
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
            
            print(f"Image analysis completed successfully")
            return json_object
    else:
        publish_log(f"OpenRouter AI request failed {response.json()}", "error")
        return None


def monitor_billboard():
    global latest_frame
    while True:
        try:
            with frame_lock:
                if latest_frame is None:
                    print("No frame available, waiting...")
                    time.sleep(10)
                    continue
                frame = latest_frame.copy()
            
            _, buffer = cv2.imencode(".jpg", frame)
            image_blob = base64.b64encode(buffer).decode("utf-8")
            analysis_result = analyze_image(image_blob)

            if not analysis_result:
                publish_log("Failed to analyze image", "error")
            else:
                publish_log(json.dumps(analysis_result), "billboardMonitoring")
                print("Billboard monitoring completed, waiting for next interval")
            
            # Wait for 30 minutes before next analysis
            time.sleep(30 * 60)  # 30 minutes in seconds
            
        except Exception as e:
            print(f"Error in monitor_billboard: {str(e)}")
            publish_log(f"Billboard monitoring error: {str(e)}", "error")
            time.sleep(60)  # Wait a minute before retrying if there's an error

def process_frames2():
    print("Starting process_frames2...")  # Add debug log
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
                print(f"Publishing traffic data: {json_object}")  # Add debug log
                publish_log(json.dumps(json_object), "traffic")
                sys.stdout.flush()  # Force flush

            prev_stable_count = stable_count

            #print the count window for all objects
            # for obj in count_window:
                # print(f"Count window for {obj}: {count_window[obj]}")
            
        except Exception as e:
            print(f"Error in process_frames2: {str(e)}")
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
                publish_log(f"New detection: {class_name} (ID: {track_id})",'info')
                
      
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Start threads
def main():
    print("Starting camera processing...")
    sys.stdout.flush()
    
    capture_thread = threading.Thread(target=capture_frames, daemon=True)
    process_thread = threading.Thread(target=process_frames2, daemon=True)
    billboard_thread = threading.Thread(target=monitor_billboard, daemon=True)

    try:
        capture_thread.start()
        process_thread.start()
        billboard_thread.start()  # Start the billboard monitoring thread

        # Keep main thread alive and flush output
        while True:
            sys.stdout.flush()
            time.sleep(1)

    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()