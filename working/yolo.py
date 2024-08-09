import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Initialize counters
counts = {
    "person": 0,
    "bicycle": 0,
    "car": 0,
    "motorcycle": 0,
    "bus": 0,
    "truck": 0
}

# Frame skip parameter
FRAME_SKIP = 10  # Process every 10th frame
frame_count = 0

# Class IDs
CLASS_IDS = {
    "person": 0,
    "bicycle": 1,
    "car": 2,
    "motorcycle": 3,
    "bus": 5,
    "truck": 7
}

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

    # Update counters
    for obj, class_id in CLASS_IDS.items():
        counts[obj] = len(detections[detections.class_id == class_id])

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

    # Show the frame
    cv2.imshow("YOLOv8 Multi-object Counting", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()