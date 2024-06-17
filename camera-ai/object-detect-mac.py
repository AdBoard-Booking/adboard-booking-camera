import cv2
import tensorflow as tf
import numpy as np
import datetime

# Load the model with signature
model = tf.saved_model.load('ssd_mobilenet_v2_coco_2018_03_29/saved_model')
infer = model.signatures['serving_default']

# Function to run inference
def run_inference(infer, frame):
    input_tensor = tf.convert_to_tensor(frame, dtype=tf.uint8)
    input_tensor = tf.expand_dims(input_tensor, axis=0)
    detections = infer(input_tensor)
    return detections

# Initialize video capture
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run inference
    detections = run_inference(infer, frame)

    person_count = 0
    car_count = 0

    # Visualize detections and log them
    for i in range(int(detections['num_detections'][0])):
        score = detections['detection_scores'][0][i].numpy()
        if score > 0.3:  # Confidence threshold
            class_id = int(detections['detection_classes'][0][i].numpy())
            bbox = detections['detection_boxes'][0][i].numpy()
            ymin, xmin, ymax, xmax = bbox
            start_point = (int(xmin * frame.shape[1]), int(ymin * frame.shape[0]))
            end_point = (int(xmax * frame.shape[1]), int(ymax * frame.shape[0]))

            # Check if the detected object is a car or person
            if class_id == 1:  # Person
                label = 'Person'
                color = (0, 255, 0)  # Green
                person_count += 1
            elif class_id == 3:  # Car
                label = 'Car'
                color = (255, 0, 0)  # Blue
                car_count += 1
            else:
                continue

            # Draw bounding box
            cv2.rectangle(frame, start_point, end_point, color, 1)
            cv2.putText(frame, label, (start_point[0], start_point[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 1)

    # Display counts on the frame
    cv2.putText(frame, f'Persons: {person_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 1)
    cv2.putText(frame, f'Cars: {car_count}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 1)

    # Log the counts to console
    # print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - Persons: {person_count}, Cars: {car_count}')

    # Display the frame with detections
    cv2.imshow('AI Processed Stream', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
