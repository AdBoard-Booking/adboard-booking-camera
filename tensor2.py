import cv2
import numpy as np
import time
from sort import Sort
import torch
import tensorflow as tf

# Load YOLOv5 model
yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Load TensorFlow model (e.g., SSD MobileNet V2)
tf_model_path = '1.tflite'  # Change this to your model path
tf_model = tf.saved_model.load(tf_model_path)

# Initialize video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Initialize SORT tracker
tracker = Sort()

# Initialize vehicle and person count
tracked_ids = set()
vehicle_person_count = 0

# Define vehicle and person class IDs
vehicle_person_class_ids = [0, 2, 3, 5]  # Person, Car, Motorcycle, Bus in COCO dataset
frame_count = 0

# Function to run YOLOv5 inference
def run_yolo(frame):
    results = yolo_model(frame)
    detections = results.xyxy[0].cpu().numpy()
    return detections

# Function to run TensorFlow inference
def run_tensorflow(frame):
    input_tensor = tf.convert_to_tensor(cv2.resize(frame, (320, 320))[np.newaxis, ...])
    detections = tf_model(input_tensor)
    boxes = detections['detection_boxes'][0].numpy()
    classes = detections['detection_classes'][0].numpy().astype(np.int32)
    scores = detections['detection_scores'][0].numpy()
    return boxes, classes, scores

# Main loop
while True:
    start_time = time.time()
    
    # Video Capture
    capture_start = time.time()
    ret, frame = cap.read()
    capture_end = time.time()
    capture_time = capture_end - capture_start

    if not ret:
        break

    # Increment frame count and skip alternate frames
    frame_count += 1
    if frame_count % 2 != 0:
        continue

    # Select the model for inference
    model_type = "tensorflow"  # Change to "tensorflow" to compare with TensorFlow model

    if model_type == "yolo":
        # Model Inference with YOLOv5
        inference_start = time.time()
        detections = run_yolo(frame)
        inference_end = time.time()
        inference_time = inference_end - inference_start
        
        # Prepare detections for SORT
        prepare_detections_start = time.time()
        sort_detections = []
        for detection in detections:
            x1, y1, x2, y2, score, class_id = detection
            if class_id in vehicle_person_class_ids and score > 0.5:
                sort_detections.append([x1, y1, x2, y2, score])
        prepare_detections_end = time.time()
        prepare_detections_time = prepare_detections_end - prepare_detections_start

    else:
        # Model Inference with TensorFlow
        inference_start = time.time()
        boxes, classes, scores = run_tensorflow(frame)
        inference_end = time.time()
        inference_time = inference_end - inference_start
        
        # Prepare detections for SORT
        prepare_detections_start = time.time()
        sort_detections = []
        for i in range(len(scores)):
            if classes[i] in vehicle_person_class_ids and scores[i] > 0.5:
                ymin, xmin, ymax, xmax = boxes[i]
                sort_detections.append([xmin * frame.shape[1], ymin * frame.shape[0], xmax * frame.shape[1], ymax * frame.shape[0], scores[i]])
        prepare_detections_end = time.time()
        prepare_detections_time = prepare_detections_end - prepare_detections_start

    # SORT Tracker Update
    tracker_update_start = time.time()
    if len(sort_detections) > 0:
        tracked_objects = tracker.update(np.array(sort_detections))
    else:
        tracked_objects = []
    tracker_update_end = time.time()
    tracker_update_time = tracker_update_end - tracker_update_start

    # Draw bounding boxes and track IDs
    draw_start = time.time()
    for d in tracked_objects:
        x1, y1, x2, y2, track_id = map(int, d)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)  # Thinner box
        cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)  # Thinner text

        # Count unique vehicle and person IDs
        if track_id not in tracked_ids:
            tracked_ids.add(track_id)
            vehicle_person_count += 1
    draw_end = time.time()
    draw_time = draw_end - draw_start

    # Display vehicle and person count
    display_start = time.time()
    cv2.putText(frame, f"Count: {vehicle_person_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)  # Thinner text
    display_end = time.time()
    display_time = display_end - display_start

    # Show the frame
    show_frame_start = time.time()
    cv2.imshow("Detection and Counting", frame)
    show_frame_end = time.time()
    show_frame_time = show_frame_end - show_frame_start

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    end_time = time.time()
    total_time = end_time - start_time

    print(f"Total Time: {total_time:.4f}s | Capture: {capture_time:.4f}s | Inference: {inference_time:.4f}s | "
          f"Prepare Detections: {prepare_detections_time:.4f}s | Tracker Update: {tracker_update_time:.4f}s | "
          f"Draw: {draw_time:.4f}s | Display: {display_time:.4f}s | Show Frame: {show_frame_time:.4f}s")

cap.release()
cv2.destroyAllWindows()
