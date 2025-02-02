import cv2
from ultralytics import YOLO
import time

def initialize_camera():
    """Initialize the Raspberry Pi camera"""
    cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2")  # Use 0 for default webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap

def main():
    # Load the YOLOv8n-face model
    try:
        model = YOLO('yolov8n-person.pt')
        print("Model loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # Initialize camera
    cap = initialize_camera()
    if not cap.isOpened():
        print("Error: Could not open camera")
        return

    # FPS calculation variables
    fps_start_time = time.time()
    fps_counter = 0
    fps = 0

    print("Starting face detection... Press 'q' to quit")
    class_names = model.names

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame")
            break

        # Update FPS calculation
        fps_counter += 1
        if (time.time() - fps_start_time) > 1:
            fps = fps_counter
            fps_counter = 0
            fps_start_time = time.time()

        # Perform detection
        results = model(frame, conf=0.5, verbose=False)  # Confidence threshold of 0.5

        # Process and display results
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                class_name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)

                # Get box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Add confidence score
                conf = float(box.conf[0])
                cv2.putText(frame, f"{class_name} {conf:.2f} ", (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Display FPS
        cv2.putText(frame, f"FPS: {fps}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Show the frame
        cv2.imshow('YOLOv8 Face Detection', frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()