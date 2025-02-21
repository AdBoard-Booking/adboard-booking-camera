import cv2
import torch
from collections import defaultdict
from yolov5.models.experimental import attempt_load
from yolov5.utils.general import non_max_suppression
from byte_tracker import BYTETracker

# Load YOLO model
model = attempt_load("yolov5s.pt", map_location="cpu")  # Use 'cpu' or 'cuda' if available

# Initialize ByteTrack
tracker = BYTETracker()

# Open camera
cap = cv2.VideoCapture(0)

# Dictionary to store counts of detected objects
object_counts = defaultdict(int)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLO inference
    img = cv2.resize(frame, (320, 320))  # Resize for faster inference
    img = torch.from_numpy(img).permute(2, 0, 1).float().unsqueeze(0) / 255.0
    pred = model(img)[0]
    pred = non_max_suppression(pred, conf_thres=0.4, iou_thres=0.5)

    # Process detections
    detections = []
    for det in pred:
        if det is not None and len(det):
            for *xyxy, conf, cls in det:
                x1, y1, x2, y2 = map(int, xyxy)
                class_id = int(cls)
                detections.append([x1, y1, x2, y2, conf, class_id])

                # Update object count
                object_counts[class_id] += 1

    # Update tracker
    tracks = tracker.update(detections)

    # Draw tracks
    for track in tracks:
        x1, y1, x2, y2, track_id = map(int, track[:5])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    print(f"{object_counts}")
    # Display frame
    # cv2.imshow("Frame", frame)

    # Print unique detected objects with counts
    print("Detected Objects:")
    for class_id, count in object_counts.items():
        print(f"Class ID: {class_id}, Count: {count}")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()