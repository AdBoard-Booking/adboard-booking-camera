import cv2
import torch
import threading
import supervision as sv
from collections import defaultdict
from ultralytics import YOLO
import os
import sys

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
    process_thread = threading.Thread(target=process_frames, daemon=True)

    capture_thread.start()
    process_thread.start()

    capture_thread.join()
    process_thread.join()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()