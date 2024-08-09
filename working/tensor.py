import numpy as np
import cv2
import tflite_runtime.interpreter as tflite

# Load the TFLite model
interpreter = tflite.Interpreter(model_path="models/detect.tflite")
interpreter.allocate_tensors()

# Get input and output tensors
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Input details:")
print(input_details)

def preprocess_frame(frame, input_shape):
    resized = cv2.resize(frame, (input_shape[1], input_shape[2]))
    # Convert to RGB if the model expects 3 channels
    if input_shape[3] == 3:
        resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    # Expand dimensions to match the model's expected input shape
    input_data = np.expand_dims(resized, axis=0)
    return input_data.astype(np.uint8)

def detect_objects(frame):
    # Preprocess the frame
    input_shape = input_details[0]['shape']
    input_data = preprocess_frame(frame, input_shape)

    # Set the input tensor
    interpreter.set_tensor(input_details[0]['index'], input_data)

    # Run inference
    interpreter.invoke()

    # Get the output tensors
    boxes = interpreter.get_tensor(output_details[0]['index'])
    classes = interpreter.get_tensor(output_details[1]['index'])
    scores = interpreter.get_tensor(output_details[2]['index'])
    num_detections = interpreter.get_tensor(output_details[3]['index'])

    return boxes, classes, scores, num_detections

def draw_boxes(frame, boxes, classes, scores, num_detections, threshold=0.6):
    for i in range(int(num_detections[0])):
        if scores[0][i] > threshold:
            ymin, xmin, ymax, xmax = boxes[0][i]
            (left, right, top, bottom) = (xmin * frame.shape[1], xmax * frame.shape[1],
                                          ymin * frame.shape[0], ymax * frame.shape[0])
            left, right, top, bottom = int(left), int(right), int(top), int(bottom)
            
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, f"Class: {int(classes[0][i])}, Score: {scores[0][i]:.2f}",
                        (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return frame

# RTSP stream URL
rtsp_url = "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2"

# Open the video stream
cap = cv2.VideoCapture(rtsp_url)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Perform object detection
    boxes, classes, scores, num_detections = detect_objects(frame)

    # Draw bounding boxes on the frame
    frame_with_boxes = draw_boxes(frame, boxes, classes, scores, num_detections)

    # Display the result
    cv2.imshow('Object Detection', frame_with_boxes)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()