import cv2
import threading
import supervision as sv
from collections import defaultdict
from ultralytics import YOLO
from datetime import datetime, timedelta
import argparse
import json
import requests
import queue

# Load YOLO model
model = YOLO("yolov8n.pt")

# Argument parser for command-line parameters
parser = argparse.ArgumentParser(description="Object Tracking with YOLO and Supervision")
parser.add_argument("--verbose", type=int, choices=[0, 1], default=0, 
                    help="Set YOLO model verbosity: 0 (Silent), 1 (Default)")
parser.add_argument("--imgshow", type=int, choices=[0, 1], default=0, 
                    help="Set imgshow: 0 (Silent), 1 (Default)")

parser.add_argument("--publish", type=int, choices=[0, 1], default=0, 
                    help="Set publish to server: 0 (Silent), 1 (Default)")

args = parser.parse_args()


# Initialize Supervision tracker (ByteTrack)
tracker = sv.ByteTrack()

# RTSP Camera Stream
IMG_SHOW = bool(args.imgshow)
ENABLE_API_CALL = bool(args.publish)

RTSP_URL = "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2"
cap = cv2.VideoCapture(RTSP_URL)

# Latest frame storage with thread lock
latest_frame = None
frame_lock = threading.Lock()

# Dictionary to track unique objects per class
unique_objects = defaultdict(set)  # Using a set to track unique object IDs

# File to log detections
LOG_FILE = "detections_log.txt"


def get_cpu_serial():
    """Fetch the CPU serial number as a unique device ID."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.strip().split(":")[1].strip()
    except Exception as e:
        print(f"[ERROR] Unable to read CPU serial: {e}")
    return "UNKNOWN"

def load_detection_batch(filename):
    """Load detection batch from a file."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_detection_batch(filename, detection_batch):
    print("Save detection batch to a file.")
    try:
        with open(filename, "w") as f:
            json.dump(detection_batch, f)
    except Exception as e:
        print(f"[ERROR] Unable to save detection batch: {e}")

def load_config(device_id):
    """Load configuration from the API."""
    # config_url = f"http://localhost:3000/api/camera/v1/config/{device_id}"
    config_url = f"https://api.adboardbooking.com/api/camera/v1/config/{device_id}"
    try:
        response = requests.get(config_url, timeout=5)
        response.raise_for_status()
        print(f"Configs: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Unable to load config: {e}")
        return None

def api_worker(queue, endpoint, detection_batch_file):
    """Worker thread to send API requests."""
    while True:
        batch = queue.get()  # Get a batch from the queue
        if batch is None:
            break  # Stop the thread if None is received

        try:
            print(f"[DEBUG] Sending batch: {len(batch)}")
            response = requests.post(endpoint, json={"data": batch}, timeout=5)
            if response.status_code == 200:
                print(f"[INFO] Batch sent successfully: {len(batch)}")
                save_detection_batch(detection_batch_file, [])  # Clear the file after successful API call
            else:
                print(f"[WARN] API returned: {response.status_code}, {response.text}")
                # Re-add batch to the queue for retry
                queue.put(batch)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API request error: {e}")
            # Re-add batch to the queue for retry
            queue.put(batch)

        queue.task_done()


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



DEVICE_ID = get_cpu_serial()
print(f"[INFO] Device ID: {DEVICE_ID}")
config = load_config(DEVICE_ID)

if not config:
    print("[ERROR] Failed to load configuration. Exiting...")

DETECTION_BATCH_FILE = "detection_batch.json"
RTSP_STREAM_URL = config.get("rtspStreamUrl", "rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2")
INFERENCE_INTERVAL = config.get("inferenceInterval", 1.0)
LONG_STAY_THRESHOLD = config.get("longStayThreshold", 20)
API_ENDPOINT = config.get("apiEndpoint", "https://api.adboardbooking.com/api/camera/v1/traffic")
SAVE_INTERVAL = config.get("saveInterval", 60)  # Save to file every 1 minutes (60 seconds)
API_CALL_INTERVAL = config.get("apiCallInterval", 300)
count_window_size = config.get("countWindowSize", 5)

 # Queue for API requests
api_queue = queue.Queue()
api_thread = threading.Thread(target=api_worker, args=(api_queue, API_ENDPOINT, DETECTION_BATCH_FILE), daemon=True)
api_thread.start()

def process_frames():
    """ Process only the latest frame and track unique objects """
    global latest_frame
    DEVICE_ID = get_cpu_serial()
    detection_batch = load_detection_batch(DETECTION_BATCH_FILE)
    last_save_time = datetime.now()
    last_api_call_time = datetime.now()

    while True:
        current_time = datetime.now()
        with frame_lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()

        # Detect objects using YOLO
        results = model(frame, verbose=bool(args.verbose))

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
        

        object_counts = defaultdict(int)  # Temporary dictionary to count new detections

        for class_id, track_id in zip(class_ids, tracker_ids):
            class_name = model.names[class_id]  # Get class name

            # Check if the object is newly detected
            if track_id not in unique_objects[class_name]:
                unique_objects[class_name].add(track_id)  # Track unique object
                object_counts[class_name] += 1  # Increment count for this class

        # Append to detection_batch after counting
        if object_counts:  # Only append if there are new detections
            detection_batch.append({
                "cameraUrl": RTSP_URL,
                "deviceId": DEVICE_ID,
                "timestamp": int(current_time.timestamp() * 1000),
                "newCount": object_counts,  # New detections counted
                "stableCount": {},  # Smoothed detection count (if needed)
                "newPeopleInfo": {}
            })

        if (current_time - last_save_time).total_seconds() >= SAVE_INTERVAL and len(detection_batch) > 0:
            save_detection_batch(DETECTION_BATCH_FILE, detection_batch)
            last_save_time = current_time

        if ((current_time - last_api_call_time).total_seconds()) >= API_CALL_INTERVAL and len(detection_batch) > 0:
                # print(f"[INFO] Sending batch: {len(detection_batch)}")
            if ENABLE_API_CALL:
                api_queue.put(detection_batch.copy())
            detection_batch.clear()
            last_api_call_time = current_time
        
        # Display the frame (optional)
        if IMG_SHOW:
            cv2.imshow("Object Tracking", frame)
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
