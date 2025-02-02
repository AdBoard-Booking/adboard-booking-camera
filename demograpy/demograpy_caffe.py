import cv2
import numpy as np

# Load face detection model
face_proto = "models/face_deploy.prototxt"
face_model = "models/face_net.caffemodel"
face_net = cv2.dnn.readNetFromCaffe(face_proto, face_model)

# Load age and gender models
age_proto = "models/age_deploy.prototxt"
age_model = "models/age_net.caffemodel"
age_net = cv2.dnn.readNetFromCaffe(age_proto, age_model)

gender_proto = "models/gender_deploy.prototxt"
gender_model = "models/gender_net.caffemodel"
gender_net = cv2.dnn.readNetFromCaffe(gender_proto, gender_model)

# Define age and gender labels
age_list = ['0-2', '4-6', '8-12', '15-20', '25-32', '38-43', '48-53', '60-100']
gender_list = ['Male', 'Female']

# Initialize webcam
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream1")

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    # Read frame from webcam
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break

    # Get frame dimensions
    (h, w) = frame.shape[:2]

    # Create a blob from the frame for face detection
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))

    # Pass the blob through the face detection network
    face_net.setInput(blob)
    detections = face_net.forward()

    # Loop over the detections
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        # Filter out weak detections
        if confidence > 0.5:
            # Get the bounding box for the face
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # Extract the face ROI
            face = frame[startY:endY, startX:endX]

            # Create a blob for age and gender detection
            face_blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227), (78.4263377603, 87.7689143744, 114.895847746), swapRB=False)

            # Predict gender
            gender_net.setInput(face_blob)
            gender_preds = gender_net.forward()
            gender = gender_list[gender_preds[0].argmax()]

            # Predict age
            age_net.setInput(face_blob)
            age_preds = age_net.forward()
            age = age_list[age_preds[0].argmax()]

            # Draw bounding box and label
            label = f"{gender}, {age}"
            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
            cv2.putText(frame, label, (startX, startY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Display the frame
    cv2.imshow("Webcam - Age and Gender Detection", frame)

    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()