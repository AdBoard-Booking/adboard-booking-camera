import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import json
import os
import gc

# Function to load count data from file
def load_count_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        return data['total_person_count'], data['total_car_count']
    return 0, 0

# Function to save count data to file
def save_count_data(filename, total_person_count, total_car_count):
    data = {
        'total_person_count': int(total_person_count),
        'total_car_count': int(total_car_count)
    }
    with open(filename, 'w') as f:
        json.dump(data, f)

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Load previous count data
count_data_file = 'count_data.json'
total_person_count, total_car_count = load_count_data(count_data_file)

# Initialize counters
counts = defaultdict(int)

# Frame skip parameter
FRAME_SKIP = 7  # Process every 7th frame
frame_count = 0

# Class IDs
CLASS_IDS = {
    "person": 0,
    "car": 2,
    "motorcycle": 3,
    "bus": 5
}

# Initialize tracker
tracker = sv.ByteTrack()

# Memory management variables
MEMORY_CLEAR_INTERVAL = 1000  # Clear memory every 1000 frames
last_memory_clear = 0

# Sets to keep track of unique IDs for the current session
unique_person_ids = set()
unique_car_ids = set()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    
    # Memory management
    if frame_count - last_memory_clear >= MEMORY_CLEAR_INTERVAL:
        gc.collect()
        last_memory_clear = frame_count
        # Reset unique ID sets periodically to prevent unbounded growth
        unique_person_ids.clear()
        unique_car_ids.clear()

    if frame_count % FRAME_SKIP != 0:
        # Show the frame without processing
        y_offset = 30
        for obj, count in counts.items():
            cv2.putText(
                frame,
                f"{obj.capitalize()}: {count}",
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            y_offset += 30
        cv2.putText(
            frame,
            f"Total Persons Passed: {total_person_count}",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )
        y_offset += 30
        cv2.putText(
            frame,
            f"Total Cars Passed: {total_car_count}",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )
        cv2.imshow("YOLOv8 Multi-object Counting", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    # Perform inference
    results = model(frame, agnostic_nms=True)[0]
    
    # Convert YOLOv8 results to supervision Detections
    detections = sv.Detections(
        xyxy=results.boxes.xyxy.cpu().numpy(),
        confidence=results.boxes.conf.cpu().numpy(),
        class_id=results.boxes.cls.cpu().numpy().astype(int)
    )

    # Track objects
    tracked_detections = tracker.update_with_detections(detections)

    # Update counters
    counts.clear()
    for obj, class_id in CLASS_IDS.items():
        counts[obj] = len(tracked_detections[tracked_detections.class_id == class_id])

    # Update total person and car counts
    for class_name, class_id in [("person", CLASS_IDS["person"]), ("car", CLASS_IDS["car"])]:
        class_detections = tracked_detections[tracked_detections.class_id == class_id]
        for track_id in class_detections.tracker_id:
            if class_name == "person" and track_id not in unique_person_ids:
                unique_person_ids.add(track_id)
                total_person_count += 1
            elif class_name == "car" and track_id not in unique_car_ids:
                unique_car_ids.add(track_id)
                total_car_count += 1

    # Draw counters
    y_offset = 30
    for obj, count in counts.items():
        cv2.putText(
            frame,
            f"{obj.capitalize()}: {count}",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        y_offset += 30

    # Draw total person and car counts
    cv2.putText(
        frame,
        f"Total Persons Passed: {total_person_count}",
        (10, y_offset),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )
    y_offset += 30
    cv2.putText(
        frame,
        f"Total Cars Passed: {total_car_count}",
        (10, y_offset),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )

    # Show the frame
    cv2.imshow("YOLOv8 Multi-object Counting", frame)

    # Save count data periodically (e.g., every 100 frames)
    if frame_count % 100 == 0:
        save_count_data(count_data_file, total_person_count, total_car_count)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Save final count data before exiting
save_count_data(count_data_file, total_person_count, total_car_count)

cap.release()
cv2.destroyAllWindows()