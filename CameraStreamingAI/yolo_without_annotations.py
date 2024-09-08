import cv2
import numpy as np
import json
import time
from ultralytics import YOLO
import logging

logging.getLogger("ultralytics").setLevel(logging.ERROR)


# Load YOLO model
model = YOLO('yolov8n.pt')  # Using YOLOv8 nano model

# RTSP stream URL
rtsp_url = "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2"

# Initialize video capture
cap = cv2.VideoCapture(rtsp_url)

# Initialize data storage
data = {}

def process_frame(frame):
    # Perform object detection
    results = model(frame)
    
    # Extract detected objects
    detected_objects = {}
    for r in results:
        boxes = r.boxes
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            name = model.names[cls]
            if name in detected_objects:
                detected_objects[name] += 1
            else:
                detected_objects[name] = 1
    
    return detected_objects

def save_data(timestamp, objects):
    data[timestamp] = objects
    print(f"Objects: {objects}")
    with open('billboard_data.json', 'w') as f:
        json.dump(data, f, indent=4)

def main():
    last_process_time = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        current_time = int(time.time())
        
        # Process one frame per second
        if current_time > last_process_time:
            detected_objects = process_frame(frame)
            save_data(current_time, detected_objects)
            last_process_time = current_time
        
        # Optional: Display the resulting frame
        cv2.imshow('Frame', frame)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()