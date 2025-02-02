import cv2
import numpy as np
import tensorflow as tf

# Load the TensorFlow Lite model
model_path = "./gender_classification.tflite"  # Path to your TFLite model
interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

# Get input and output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Define age and gender labels (example)
age_labels = ['0-2', '4-6', '8-12', '15-20', '25-32', '38-43', '48-53', '60-100']
gender_labels = ['Male', 'Female']

# Initialize webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    # Read frame from webcam
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break

    # Preprocess the frame (resize, normalize, etc.)
    input_shape = input_details[0]['shape'][1:3]  # Get model input shape (e.g., 224x224)
    resized_frame = cv2.resize(frame, input_shape)
    input_data = np.expand_dims(resized_frame, axis=0).astype(np.float32)
    input_data = input_data / 255.0  # Normalize pixel values to [0, 1]

    # Set input tensor
    interpreter.set_tensor(input_details[0]['index'], input_data)

    # Run inference
    interpreter.invoke()

    # Get output tensors
    age_output = interpreter.get_tensor(output_details[0]['index'])  # Age output
    gender_output = interpreter.get_tensor(output_details[1]['index'])  # Gender output

    # Process outputs
    age_index = np.argmax(age_output[0])  # Get predicted age index
    gender_index = np.argmax(gender_output[0])  # Get predicted gender index

    age = age_labels[age_index]
    gender = gender_labels[gender_index]

    # Display results on the frame
    label = f"Age: {age}, Gender: {gender}"
    cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Show the frame
    cv2.imshow("Webcam - Age and Gender Detection (TFLite)", frame)

    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()