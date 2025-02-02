import cv2
from deepface import DeepFace

# Initialize the webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()

    if not ret:
        print("Error: Could not read frame.")
        break

    # Analyze the frame for demographic details
    try:
        # Analyze the image using DeepFace
        analysis = DeepFace.analyze(frame, actions=['age', 'gender'], enforce_detection=True)

        # Extract the first face's details (assuming only one face in the frame)
        demographics = analysis[0]

        # Get the bounding box coordinates
        x, y, w, h = demographics['region']['x'], demographics['region']['y'], demographics['region']['w'], demographics['region']['h']

        # Draw the bounding box around the face
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Prepare the text to display
        text = f"Age: {demographics['age']}, Gender: {demographics['gender']}, Race: {demographics['dominant_race']}"

        # Put the text on the image
        cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    except Exception as e:
        print(f"Error analyzing frame: {e}")

    # Display the frame with bounding box and text
    cv2.imshow('Webcam - Demographic Details', frame)

    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()