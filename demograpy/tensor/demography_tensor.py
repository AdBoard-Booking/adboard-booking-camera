import tensorflow as tf
import tensorflow_hub as hub
import cv2
import numpy as np

# Load a pre-trained model from TensorFlow Hub
model_url = "https://tfhub.dev/google/imagenet/mobilenet_v2_100_224/classification/4"
model = hub.load(model_url)

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
    resized_frame = cv2.resize(frame, (224, 224))  # Resize to model input size
    input_data = np.expand_dims(resized_frame, axis=0).astype(np.float32)
    input_data = input_data / 255.0  # Normalize pixel values to [0, 1]

    # Run inference
    predictions = model(input_data)

    # Process predictions (example: classification)
    predicted_class = np.argmax(predictions)  # Get the predicted class index

    # Map the predicted class to age and gender labels
    # Note: This is a placeholder. You need to train or fine-tune the model for age/gender detection.
    age = age_labels[predicted_class % len(age_labels)]
    gender = gender_labels[predicted_class % len(gender_labels)]

    # Display results on the frame
    label = f"Age: {age}, Gender: {gender}"
    cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Show the frame
    cv2.imshow("Webcam - Age and Gender Detection", frame)

    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()