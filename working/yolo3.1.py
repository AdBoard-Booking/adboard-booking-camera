import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import threading
import queue
import logging
import requests
import time
import json

# Suppress YOLO logs
logging.getLogger("ultralytics").setLevel(logging.ERROR)

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Initialize counters
counts = defaultdict(int)
total_car_count = 0

# Load the car count from file
def load_count():
    global total_car_count
    try:
        with open('car_count.json', 'r') as file:
            data = json.load(file)
            total_car_count = data.get('total_car_count', 0)
    except FileNotFoundError:
        pass

# Store the car count to file
def save_count():
    with open('car_count.json', 'w') as file:
        json.dump({'total_car_count': total_car_count}, file)

load_count()

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

def api_call_and_save_thread():
    while not stop_flag.is_set():
        time.sleep(300)  # Wait for 5 minutes (300 seconds)
        try:
            response = requests.post("https://example.com/api/endpoint", json={"car_count": total_car_count})
            print("API response:", response.status_code, response.json())
        except Exception as e:
            print("API call failed:", e)
        save_count()
        print(f"Total car count: {total_car_count}")

# Start the inference thread
inference_thread = threading.Thread(target=inference_thread)
inference_thread.start()

# Start the API call and save thread
api_thread = threading.Thread(target=api_call_and_save_thread)
api_thread.start()

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

        # Debug: Print the tracked detections to inspect the structure
        # print(tracked_detections)

        # Update counters
        counts.clear()
        for obj, class_id in CLASS_IDS.items():
            counts[obj] = len([i for i, cls_id in enumerate(tracked_detections.class_id) if cls_id == class_id])

        # Update total car count
        for class_id in [CLASS_IDS["car"]]:
            class_detections = [i for i, cls_id in enumerate(tracked_detections.class_id) if cls_id == class_id]
            for i in class_detections:
                track_id = tracked_detections.tracker_id[i]
                if track_id not in unique_car_ids:
                    unique_car_ids.add(track_id)
                    total_car_count += 1
        
        print('Total count', total_car_count)

    except queue.Empty:
        pass

# Signal threads to stop and wait for them to finish
stop_flag.set()
inference_thread.join()
api_thread.join()

# Save the car count to file one last time
save_count()

cap.release()
