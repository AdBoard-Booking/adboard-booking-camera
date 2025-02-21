import cv2
import threading
import supervision as sv
from collections import defaultdict
from ultralytics import YOLO
from datetime import datetime, timedelta

# Load YOLO model
model = YOLO("yolov8n.pt")

# Initialize Supervision tracker (ByteTrack)
tracker = sv.ByteTrack(
    track_activation_threshold=0.25,  # Lower threshold for tracking
    lost_track_buffer=30,    # Buffer size for lost tracks
    minimum_matching_threshold=0.8,   # Matching threshold for tracks
    frame_rate=15       # Expected frame rate
)

# RTSP Camera Stream
RTSP_URL = "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2"
cap = cv2.VideoCapture(RTSP_URL)

# Latest frame storage with thread lock
latest_frame = None
frame_lock = threading.Lock()

# Dictionary to track unique objects per class
unique_objects = defaultdict(set)  # Using a set to track unique object IDs

# File to log detections
LOG_FILE = "detections_log.txt"

def log_detection(class_name, object_id):
    """ Log the timestamp, class, and ID of a newly detected object """
    utc_now = datetime.now()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    timestamp_ist = ist_now.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp_ist}, {class_name}, {object_id}\n")

def capture_frames():
    """ Continuously capture frames and update the latest frame """
    global latest_frame
    while True:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                latest_frame = frame

def process_frames():
    """ Process only the latest frame and track unique objects """
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()

        # Detect objects using YOLO
        results = model(frame, conf=0.25, verbose=True)

        # Convert YOLO results to Supervision Tracker format
        detections = sv.Detections.from_ultralytics(results[0])

        # Update detections with tracker IDs
        detections = tracker.update_with_detections(detections)

        if detections.tracker_id is None:
            continue  # Skip frame if tracking IDs are not assigned

         # Extract class labels and tracker IDs
        class_ids = detections.class_id
        # class_labels = [model.names[class_id] for class_id in class_ids]
        tracker_ids = detections.tracker_id  # Get tracker IDs
        
        # current_frame_objects = [f"{cls}:#{tid}" for cls, tid in zip(class_labels, tracker_ids)]
       
        # print(f"Current: {current_frame_objects}")

        # Extract class labels and tracker IDs
        for class_id, track_id in zip(class_ids,tracker_ids):
        
            class_name = model.names[class_id]  # Get class name

            # Check if the object is newly detected
            if track_id not in unique_objects[class_name]:
                unique_objects[class_name].add(track_id)  # Track unique object
                print(f"New detection: {class_name} (ID: {track_id})")
                log_detection(class_name, track_id)  # Log the new detection

        # Display the frame (optional)
        # cv2.imshow("Object Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Start threads
capture_thread = threading.Thread(target=capture_frames, daemon=True)
process_thread = threading.Thread(target=process_frames, daemon=True)

capture_thread.start()
process_thread.start()

capture_thread.join()
process_thread.join()

cap.release()
cv2.destroyAllWindows()