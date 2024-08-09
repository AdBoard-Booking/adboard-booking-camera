import numpy as np
import cv2
import tflite_runtime.interpreter as tflite
import time
import logging

import kagglehub

# Download latest version
path = kagglehub.model_download("google/mobilenet-v3/tfLite/large-075-224-classification")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Load the TFLite model
interpreter = tflite.Interpreter(model_path="detect.tflite")
interpreter.allocate_tensors()

# Get input and output tensors
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

logging.info("Input details:")
logging.info(input_details)
logging.info("Output details:")
logging.info(output_details)

# Define labels
LABELS = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus',
    6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light', 10: 'fire hydrant',
    11: 'street sign', 12: 'stop sign', 13: 'parking meter', 14: 'bench', 15: 'bird',
    16: 'cat', 17: 'dog', 18: 'horse', 19: 'sheep', 20: 'cow', 21: 'elephant',
    22: 'bear', 23: 'zebra', 24: 'giraffe', 25: 'hat', 26: 'backpack', 27: 'umbrella',
    28: 'shoe', 29: 'eye glasses', 30: 'handbag', 31: 'tie', 32: 'suitcase',
    33: 'frisbee', 34: 'skis', 35: 'snowboard', 36: 'sports ball', 37: 'kite',
    38: 'baseball bat', 39: 'baseball glove', 40: 'skateboard', 41: 'surfboard',
    42: 'tennis racket', 43: 'bottle', 44: 'plate', 45: 'wine glass', 46: 'cup',
    47: 'fork', 48: 'knife', 49: 'spoon', 50: 'bowl', 51: 'banana', 52: 'apple',
    53: 'sandwich', 54: 'orange', 55: 'broccoli', 56: 'carrot', 57: 'hot dog',
    58: 'pizza', 59: 'donut', 60: 'cake', 61: 'chair', 62: 'couch', 63: 'potted plant',
    64: 'bed', 65: 'mirror', 66: 'dining table', 67: 'window', 68: 'desk', 69: 'toilet',
    70: 'door', 71: 'tv', 72: 'laptop', 73: 'mouse', 74: 'remote', 75: 'keyboard',
    76: 'cell phone', 77: 'microwave', 78: 'oven', 79: 'toaster', 80: 'sink',
    81: 'refrigerator', 82: 'blender', 83: 'book', 84: 'clock', 85: 'vase',
    86: 'scissors', 87: 'teddy bear', 88: 'hair drier', 89: 'toothbrush', 90: 'hair brush'
}

def preprocess_frame(frame, input_shape):
    resized = cv2.resize(frame, (input_shape[1], input_shape[2]))
    return np.expand_dims(resized, axis=0).astype(np.uint8)

def detect_objects(frame):
    input_shape = input_details[0]['shape']
    input_data = preprocess_frame(frame, input_shape)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    
    # Get all output tensors
    boxes = interpreter.get_tensor(output_details[0]['index'])
    classes = interpreter.get_tensor(output_details[1]['index'])
    scores = interpreter.get_tensor(output_details[2]['index'])
    num_detections = int(interpreter.get_tensor(output_details[3]['index'])[0])
    
    return boxes[0][:num_detections], classes[0][:num_detections], scores[0][:num_detections], num_detections

def log_detections(boxes, classes, scores, num_detections, threshold=0.5):
    for i in range(num_detections):
        if scores[i] > threshold:
            class_id = int(classes[i])
            label = LABELS.get(class_id, f"Class {class_id}")
            score = float(scores[i])
            box = boxes[i]
            logging.info(f"Detection: {label}, Score: {score:.2f}, Box: {box}")

# RTSP stream URL
rtsp_url = "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2"

# Open the video stream
cap = cv2.VideoCapture(rtsp_url)

# Set the interval for processing frames (e.g., every 1 second)
process_interval = 1.0  # seconds

last_process_time = time.time()

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.error("Failed to grab frame")
            break

        current_time = time.time()
        if current_time - last_process_time >= process_interval:
            # Perform object detection
            boxes, classes, scores, num_detections = detect_objects(frame)

            # Log the detections
            log_detections(boxes, classes, scores, num_detections)

            last_process_time = current_time

except KeyboardInterrupt:
    logging.info("Script interrupted by user")
finally:
    # Release resources
    cap.release()
    logging.info("Resources released. Script ended.")