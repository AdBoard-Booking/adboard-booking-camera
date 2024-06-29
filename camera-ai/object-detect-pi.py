import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import datetime 

# Load the TFLite model and allocate tensors
interpreter = tflite.Interpreter(model_path="detect.tflite")
interpreter.allocate_tensors()

# Get input and output tensors
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Function to run inference 
def run_inference(interpreter, frame):
    input_data = np.expand_dims(frame, axis=0).astype(np.uint8)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output_data = [interpreter.get_tensor(output_details[i]['index']) for i in range(len(output_details))]
    return output_data

# Initialize video capture
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize frame to the size expected by the model
    input_size = input_details[0]['shape'][1:3]
    resized_frame = cv2.resize(frame, (input_size[1], input_size[0]))

    # Run inference
    detections = run_inference(interpreter, resized_frame)

    person_count = 0
    car_count = 0

    # Visualize detections and log them
    for i in range(len(detections[1][0])):
        score = detections[1][0][i]
        if score > 0.5:  # Confidence threshold
            class_id = int(detections[3][0][i])
            bbox = detections[0][0][i]
            ymin, xmin, ymax, xmax = bbox
            start_point = (int(xmin * frame.shape[1]), int(ymin * frame.shape[0]))
            end_point = (int(xmax * frame.shape[1]), int(ymax * frame.shape[0]))

            # Check if the detected object is a car or person
            if class_id == 0:  # Person (class ID 0 in COCO SSD MobileNet v1)
                label = 'Person'
                color = (0, 255, 0)  # Green
                person_count += 1
            elif class_id == 2:  # Car (class ID 2 in COCO SSD MobileNet v1)
                label = 'Car'
                color = (255, 0, 0)  # Blue
                car_count += 1
            else:
                continue

            # Draw bounding box
            cv2.rectangle(frame, start_point, end_point, color, 2)
            cv2.putText(frame, label, (start_point[0], start_point[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    # Display counts on the frame
    cv2.putText(frame, f'Persons: {person_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, f'Cars: {car_count}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # Log the counts to console
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - Persons: {person_count}, Cars: {car_count}')

    # Display the frame with detections
    cv2.imshow('AI Processed Stream', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
