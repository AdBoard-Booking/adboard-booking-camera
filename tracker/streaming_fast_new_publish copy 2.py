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
    count_window = {"car": [], "person": []}
    prev_stable_count = {"car": 0, "person": 0}
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()

        current_time = time.time()
        results = model(frame, verbose=False)[0]
        detections = results.boxes
        class_names = model.names

        raw_count = {"car": 0, "person": 0}
        new_count = {"car": 0, "person": 0}
        new_people_info = []
        if detections is not None:
            for box in detections:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                if conf < 0.3:
                    continue

                class_name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)

                if class_name in raw_count:
                    raw_count[class_name] += 1
                    # Get box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Add confidence score
                    conf = float(box.conf[0])
                    cv2.putText(frame, f"{class_name} {conf:.2f} ", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Add this raw count to our rolling window
        for obj in raw_count:
            count_window[obj].append(raw_count[obj])
            if len(count_window[obj]) > count_window_size:
                count_window[obj].pop(0)

        ################################
        # 2) Compute stable_count
        ################################
        stable_count = {
            obj: int(round(statistics.median(count_window[obj]))) if count_window[obj] else 0
            for obj in raw_count
        }

        # 3) Naive Heuristics
        for obj in raw_count:
            if stable_count[obj] > prev_stable_count[obj]:
                diff = stable_count[obj] - prev_stable_count[obj]
                last_increase_time = current_time
                new_count[obj] = diff
                print(f"[++++++++++++++++++++++++++++++++] Detected an increase of {diff} {obj}s.")

        time_since_increase = current_time - last_increase_time
        for obj in raw_count:
            if time_since_increase > LONG_STAY_THRESHOLD and stable_count[obj] > 0:
                new_count[obj] = stable_count[obj]
                print(f"[^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^] Long stay triggered, added {stable_count[obj]} {obj}s")
                last_increase_time = current_time

        prev_stable_count = stable_count

        ################################
        # Add to batch only if stableCount > 0
        ################################
        if any(new_count[obj] > 0 for obj in new_count):
            publish_log(f"New detection: {new_count}")

        
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