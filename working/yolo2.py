import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")
tracker = sv.ByteTrack()
label_annotator = sv.LabelAnnotator(text_position=sv.Position.TOP_CENTER)

while True:
    ret, frame = cap.read()

    # Show the frame

    result = model(frame)[0]
    detections = sv.Detections.from_ultralytics(result)
    detections = tracker.update_with_detections(detections)
    labels = [f"#{tracker_id}" for tracker_id in detections.tracker_id]

    annotated_frame = label_annotator.annotate(
        scene=frame, detections=detections, labels=labels)

    cv2.imshow("YOLO", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()