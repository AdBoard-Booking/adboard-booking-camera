import cv2
from ultralytics import YOLO
import supervision as sv

# Load the YOLOv8n model
model = YOLO("../traffic/yolov8n-person.pt")

# Initialize the tracker
tracker = sv.ByteTrack()

# Open the video stream
video_path = 'rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2'  # 0 for webcam, or video file path
cap = cv2.VideoCapture(video_path)

# Initialize the annotator
box_annotator = sv.BoxAnnotator()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Perform object detection
    results = model(frame,verbose=True)[0]

    # Convert to supervision Detections
    detections = sv.Detections.from_ultralytics(results)

    # Update tracker
    detections = tracker.update_with_detections(detections)

    # Create labels with class names and tracking IDs
    labels = [
        f"{tracker_id} {model.model.names[class_id]} {confidence:0.2f}"
        for class_id, confidence, tracker_id in 
        zip(detections.class_id, detections.confidence, detections.tracker_id)
    ]

    # Annotate the frame
    annotated_frame = box_annotator.annotate(
        scene=frame.copy(),
        detections=detections,
        labels=labels
    )

    cv2.imshow("YOLOv8 Tracking", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

