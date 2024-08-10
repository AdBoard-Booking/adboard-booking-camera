import cv2
import numpy as np
from ultralytics import YOLO
from Sort import Sort, KalmanBoxTracker


# Load the YOLOv8 model using the ultralytics package
model = YOLO('yolov8s.pt')  # You can change this to 'yolov5s.pt' if you prefer YOLOv5

# Initialize the SORT tracker
tracker = Sort()

# Open the RTSP stream
cap = cv2.VideoCapture('rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2')

car_count = 0
tracked_ids = set()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Perform object detection using YOLO
    results = model(frame)
    
    detections = []
    for result in results:
        for box in result.boxes:
            if box.cls == 2:  # Check if the detected class is a car (class ID 2)
                xmin, ymin, xmax, ymax = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                detections.append([xmin, ymin, xmax, ymax, conf])

    # Convert detections to a NumPy array for SORT
    detections = np.array(detections)

    # Update the tracker with the detections
    tracks = tracker.update(detections)

    for track in tracks:
        xmin, ymin, xmax, ymax, track_id = track.astype(int)
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
        cv2.putText(frame, f"ID: {track_id}", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Count car if it's a new track
        if track_id not in tracked_ids:
            tracked_ids.add(track_id)
            car_count += 1

    cv2.putText(frame, f"Cars Counted: {car_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.imshow('Car Tracker', frame)

    # Press 'q' to exit the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
