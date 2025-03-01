import cv2
import torch
import threading
import supervision as sv
from collections import defaultdict
from ultralytics import YOLO
import os
import sys
import time
import statistics
import datetime
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
utils_folder = os.path.join(current_dir, '..','boot','services','utils')
sys.path.append(utils_folder)

from mqtt import publish_log

# Load YOLO model
model = YOLO("yolov8n.pt")

# Initialize Supervision tracker (ByteTrack)
tracker = sv.ByteTrack()

# RTSP Camera Stream
RTSP_URL = "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2"
cap = cv2.VideoCapture(RTSP_URL)

# Latest frame storage with thread lock
latest_frame = None
frame_lock = threading.Lock()

# Dictionary to track unique objects per class
unique_objects = defaultdict(set)  # To count unique objects over time

def capture_frames():
    """ Continuously capture frames and update the latest frame """
    global latest_frame
    while True:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                latest_frame = frame

def process_frames2():
    count_window_size = 5
    LONG_STAY_THRESHOLD = 20
    count_window = defaultdict(list)  # Changed to defaultdict for dynamic class handling
    prev_stable_count = defaultdict(int)  # Changed to defaultdict for dynamic class handling
    global latest_frame
    last_increase_time = time.time()
    all_classes = ['person', 'car','bicycle','motorcycle','bus','train']
    
    last_process_time = time.time()
    while True:
        current_time = time.time()
        # Only process if at least 1 second has passed since last processing
        if current_time - last_process_time < 1.0:
            continue
            
        with frame_lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()

        last_process_time = current_time
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
            "timestamp": int(time.time()),
            "count": new_count
        }

        #publish the json object to mqtt
        if(len(new_count) > 0):
            publish_log(json.dumps(json_object), "traffic")

        prev_stable_count = stable_count

        #print the count window for all objects
        # for obj in count_window:
            # print(f"Count window for {obj}: {count_window[obj]}")
        
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
                publish_log(f"New detection: {class_name} (ID: {track_id})")
                
      
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Start threads
def main():
    capture_thread = threading.Thread(target=capture_frames, daemon=True)
    process_thread = threading.Thread(target=process_frames2, daemon=True)

    capture_thread.start()
    process_thread.start()

    capture_thread.join()
    process_thread.join()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()