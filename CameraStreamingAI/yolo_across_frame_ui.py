import cv2
import numpy as np
import os
import json
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import time

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Initialize counters
counts = defaultdict(int)
total_person_count = 0
total_car_count = 0

# Frame skip parameter
FRAME_SKIP = 10  # Process every 10th frame
frame_count = 0

# Class IDs
CLASS_IDS = { 
    "car": 2
}

# Initialize tracker
tracker = sv.ByteTrack()

# Sets to keep track of unique person and car IDs
unique_person_ids = set()
unique_car_ids = set()

def save_data(timestamp, objects, filename='/home/pi/adboard-booking-camera/CameraStreamingAI/billboard_data.json'):
    
    # Load existing data
    data = {}
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading {filename}. Starting with empty data.")

    # Update data only if objects is not empty
    if objects:
        if timestamp in data:
            # If timestamp exists, update the objects for that timestamp
            data[timestamp].update(objects)
        else:
            # If timestamp doesn't exist, add a new entry
            data[timestamp] = objects
        print(f"Updated {timestamp}: {objects}")
    else:
        print(f"{timestamp}: No objects detected")

    # Save updated data
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

    return data  # Return the updated data dictionary


while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    if frame_count % FRAME_SKIP != 0:
        # Show the frame without processing
        y_offset = 30
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
    current_time = int(time.time())
    detected_objects = {}
    # Update total person and car counts
    frame_car_count=0
    for class_name, class_id in [("car", CLASS_IDS["car"])]:
        class_detections = tracked_detections[tracked_detections.class_id == class_id]

        for track_id in class_detections.tracker_id:
            if class_name == "car" and track_id not in unique_car_ids:
                unique_car_ids.add(track_id)
                total_car_count += 1
                frame_car_count += 1
    
    
    if frame_car_count > 0 :
        detected_objects["car"] = frame_car_count
        save_data(current_time,detected_objects)

    # Draw counters and bounding boxes
    y_offset = 30
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

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()