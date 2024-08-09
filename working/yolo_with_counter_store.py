import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import json
import os
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress YOLO's console output
os.environ['YOLO_VERBOSE'] = 'False'

# Class IDs
CLASS_IDS = {
    "person": 0,
    "car": 2
}

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

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Function to initialize video capture
def init_video_capture():
    return cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Load previous count data
count_data_file = 'count_data.json'
total_counts = load_count_data(count_data_file)

# Initialize tracker
tracker = sv.ByteTrack()

# Sets to keep track of unique IDs for the current session
unique_ids = {class_name: set() for class_name in CLASS_IDS.keys()}

# Main loop
try:
    cap = init_video_capture()
    consecutive_errors = 0
    max_consecutive_errors = 10

    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                raise Exception("Failed to read frame")

            # Reset consecutive errors counter on successful frame read
            consecutive_errors = 0

            resized_frame = cv2.resize(frame, (640, 480))

            # Perform inference
            results = model(resized_frame, verbose=False)[0]
            
            # Convert YOLOv8 results to supervision Detections
            detections = sv.Detections.from_ultralytics(results)

            # Track objects
            tracked_detections = tracker.update_with_detections(detections)

            # Update counters
            new_detection = False
            for class_name, class_id in CLASS_IDS.items():
                class_detections = tracked_detections[tracked_detections.class_id == class_id]
                for track_id in class_detections.tracker_id:
                    if track_id not in unique_ids[class_name]:
                        unique_ids[class_name].add(track_id)
                        total_counts[class_name] += 1
                        new_detection = True

            # Save count data when new detection occurs
            if new_detection:
                save_count_data(count_data_file, total_counts)

        except Exception as e:
            logging.error(f"Error processing frame: {str(e)}")
            consecutive_errors += 1

            if consecutive_errors >= max_consecutive_errors:
                logging.warning("Too many consecutive errors. Reinitializing video capture.")
                cap.release()
                time.sleep(5)  # Wait before attempting to reconnect
                cap = init_video_capture()
                consecutive_errors = 0

        # Add a small delay to reduce CPU usage
        time.sleep(0.01)

except KeyboardInterrupt:
    logging.info("Script interrupted by user.")

finally:
    # Save final count data before exiting
    save_count_data(count_data_file, total_counts)
    logging.info("Final counts saved. Exiting...")
    cap.release()