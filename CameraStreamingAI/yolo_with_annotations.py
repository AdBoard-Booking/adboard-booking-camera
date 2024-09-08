import cv2
import numpy as np
import json
import time
import os
from ultralytics import YOLO
import logging
import threading
from process_billboard_data import process_billboard_data  # Import the function

logging.getLogger("ultralytics").setLevel(logging.ERROR)

with open('/usr/local/bin/adboardbooking/registered_cameras.json', 'r') as f:
    camera_config = json.load(f)

# Load YOLO model
model = YOLO("/home/pi/adboard-booking-camera/CameraStreamingAI/yolov8n.pt")  # Using YOLOv8 nano model

# RTSP stream URL
rtsp_url = camera_config[0]['rtspUrl']

# Initialize video capture
cap = cv2.VideoCapture(rtsp_url)

# Initialize data storage
data = {}

CONFIDENCE_THRESHOLD = 0.5

def process_frame(frame):
    # Perform object detection
    results = model(frame)
    
    # Extract detected objects
    detected_objects = {}
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            name = model.names[cls]

            if conf >= CONFIDENCE_THRESHOLD:
                # Annotate the frame
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f'{name} {conf:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                
                if name in detected_objects:
                    detected_objects[name] += 1
                else:
                    detected_objects[name] = 1
    
    return frame, detected_objects

def periodic_processing():
    while True:
        process_billboard_data()  # Call the function from process_billboard_data.py
        time.sleep(600)  # Sleep for 10 minutes (600 seconds)

def save_data(timestamp, objects, filename='/home/pi/adboard-booking-camera/CameraStreamingAI/billboard_data.json'):
    
    # Load existing data
    data = {}
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading {filename}. Starting with empty data.")

    # Update data only if objects is not empty
    if objects:
        if timestamp in data:
            # If timestamp exists, update the objects for that timestamp
            data[timestamp].update(objects)
        else:
            # If timestamp doesn't exist, add a new entry
            data[timestamp] = objects
        print(f"Updated {timestamp}: {objects}")
    else:
        print(f"{timestamp}: No objects detected")

    # Save updated data
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

    return data  # Return the updated data dictionary

def main():
    last_process_time = 0

    # Start the periodic processing in a separate thread
    processing_thread = threading.Thread(target=periodic_processing, daemon=True)
    processing_thread.start()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        current_time = int(time.time())
        
        # Process one frame per second
        if current_time > last_process_time:
            annotated_frame, detected_objects = process_frame(frame)
            save_data(current_time, detected_objects)
            last_process_time = current_time
            
            # Display the annotated frame
            # cv2.imshow('Annotated Frame', annotated_frame)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()