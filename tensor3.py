import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
from sort import Sort

# Load TFLite model and allocate tensors.
interpreter = tflite.Interpreter(model_path="detect.tflite")
interpreter.allocate_tensors()

# Get input and output tensors.
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Initialize video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Initialize SORT tracker
tracker = Sort()

# Initialize car count
car_count = 0
tracked_ids = set()

# Define vehicle class IDs
vehicle_class_ids = [2]  # Car

frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    # Preprocess the frame
    input_data = cv2.resize(frame, (300, 300))

    # Check the type of the input tensor and convert if necessary
    if input_details[0]['dtype'] == np.uint8:
        input_data = np.array(input_data, dtype=np.uint8)
    else:
        input_data = np.array(input_data, dtype=np.float32)
        # Normalize the image to the range [0, 1]
        input_data = input_data / 255.0

    input_data = np.expand_dims(input_data, axis=0)

    # Perform inference
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    # Get detection results
    boxes = interpreter.get_tensor(output_details[0]['index'])[0]
    classes = interpreter.get_tensor(output_details[1]['index'])[0]
    scores = interpreter.get_tensor(output_details[2]['index'])[0]

    # Prepare detections for SORT
    detections = []
    for i in range(len(scores)):
        if scores[i] > 0.5 and classes[i] in vehicle_class_ids:
            ymin, xmin, ymax, xmax = boxes[i]
            xmin = int(xmin * frame.shape[1])
            xmax = int(xmax * frame.shape[1])
            ymin = int(ymin * frame.shape[0])
            ymax = int(ymax * frame.shape[0])
            detections.append([xmin, ymin, xmax, ymax, scores[i]])

    # Check if there are any detections before updating the tracker
    if len(detections) > 0:
        tracked_objects = tracker.update(np.array(detections))
    else:
        tracked_objects = []

    # Process tracked objects and count unique car IDs
    for d in tracked_objects:
        track_id = int(d[4])
        if track_id not in tracked_ids:
            tracked_ids.add(track_id)
            car_count += 1

    # Log the car count every 10 frames
    if frame_count % 10 == 0:
        print(f"Car Count: {car_count}")

cap.release()
