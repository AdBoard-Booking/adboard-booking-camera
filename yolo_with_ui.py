import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress YOLO's console output
os.environ['YOLO_VERBOSE'] = 'False'

# Class IDs
CLASS_IDS = {
    "car": 2
}


# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")
tracker = sv.ByteTrack()
label_annotator = sv.LabelAnnotator(text_position=sv.Position.TOP_CENTER)

# Global variables
car_count = 0
tracker_history = set()

# Suppress YOLO's console output
os.environ['YOLO_VERBOSE'] = 'False'

frame_counter = 0

# Function to load count data from file
def load_count_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        return {class_name: data.get(f'total_{class_name}_count', 0) for class_name in CLASS_IDS.keys()}
    return {class_name: 0 for class_name in CLASS_IDS.keys()}

# Function to save count data to file
def save_count_data(filename, total_counts):
    logging.info(f"Saving data: {str(total_counts)}")
    data = {f'total_{class_name}_count': int(count) for class_name, count in total_counts.items()}
    with open(filename, 'w') as f:
        json.dump(data, f)

# Sets to keep track of unique IDs for the current session
unique_ids = {class_name: set() for class_name in CLASS_IDS.keys()}


while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_counter += 1

    # Process only every 5th frame
    if frame_counter % 5 != 0:
        continue

    # Reduce input resolution
    resized_frame = cv2.resize(frame, (640, 480))

    # Show the frame
    result = model(resized_frame, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(result)
    detections = tracker.update_with_detections(detections)
    labels = [f"#{tracker_id}" for tracker_id in detections.tracker_id]

    # Log tracker count for each class
    tracker_count = defaultdict(int)
    for detection in detections:
        bbox, mask, score, class_id, tracker_id, additional_info = detection
        
        # Only count cars (assuming class_id 2 is for cars, change if different)
        if class_id == 2:
            if tracker_id not in tracker_history:
                car_count += 1
                tracker_history.add(tracker_id)
        tracker_count[class_id] += 1

    # Print total car count
    print(f"Total cars passed: {car_count}")

    annotated_frame = label_annotator.annotate(
        scene=resized_frame, detections=detections, labels=labels)

    cv2.imshow("YOLO", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
