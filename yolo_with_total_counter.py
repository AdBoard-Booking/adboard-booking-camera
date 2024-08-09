import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import threading
import queue

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Initialize counters
counts = defaultdict(int)
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

# Set to keep track of unique car IDs
unique_car_ids = set()

# Create queues for communication between threads
frame_queue = queue.Queue(maxsize=5)
result_queue = queue.Queue(maxsize=5)

# Flag to signal threads to stop
stop_flag = threading.Event()

def inference_thread():
    while not stop_flag.is_set():
        try:
            frame = frame_queue.get(timeout=1)
            results = model(frame, agnostic_nms=True)[0]
            detections = sv.Detections(
                xyxy=results.boxes.xyxy.cpu().numpy(),
                confidence=results.boxes.conf.cpu().numpy(),
                class_id=results.boxes.cls.cpu().numpy().astype(int)
            )
            tracked_detections = tracker.update_with_detections(detections)
            result_queue.put(tracked_detections)
        except queue.Empty:
            continue

# Start the inference thread
inference_thread = threading.Thread(target=inference_thread)
inference_thread.start()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    if frame_count % FRAME_SKIP == 0:
        # Put frame in queue for processing
        if not frame_queue.full():
            frame_queue.put(frame)

    # Try to get results from the result queue
    try:
        tracked_detections = result_queue.get_nowait()
        
        # Update counters
        counts.clear()
        for obj, class_id in CLASS_IDS.items():
            counts[obj] = len(tracked_detections[tracked_detections.class_id == class_id])

        # Update total car count
        for class_id in [CLASS_IDS["car"]]:
            class_detections = tracked_detections[tracked_detections.class_id == class_id]
            for track_id in class_detections.tracker_id:
                if track_id not in unique_car_ids:
                    unique_car_ids.add(track_id)
                    total_car_count += 1

    except queue.Empty:
        pass

    # Draw counters
    y_offset = 40
    cv2.putText(
        frame,
        f"Cars Passed: {total_car_count}",
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

# Signal threads to stop and wait for them to finish
stop_flag.set()
inference_thread.join()

cap.release()
cv2.destroyAllWindows()