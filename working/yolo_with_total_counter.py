import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Initialize counters
counts = defaultdict(int)
total_person_count = 0
total_car_count = 0

# Frame skip parameter
FRAME_SKIP = 7  # Process every 10th frame
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

# Sets to keep track of unique person and car IDs
unique_person_ids = set()
unique_car_ids = set()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
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

    # Draw counters and bounding boxes
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

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()