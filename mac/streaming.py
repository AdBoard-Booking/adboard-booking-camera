import time
import cv2
import requests
import numpy as np

# If using ultralytics YOLO
try:
    from ultralytics import YOLO
    use_ultralytics = True
except ImportError:
    use_ultralytics = False
    # fallback or custom YOLO code here

#############################
# DEMOGRAPHIC ESTIMATION (Placeholder)
#############################
def estimate_demography(face_image):
    """
    Face-based demographic estimation: age, gender, etc.
    In a real implementation, you need:
      1. A face detection or alignment step.
      2. A pretrained age/gender classification model.

    This function is just a stub that returns demo data.
    """
    return {
        "age_estimate": 30,   # e.g., 30
        "gender": "male"      # or "female"
    }

#############################
# MAIN DETECTION SCRIPT
#############################
def main():
    # -------------------------
    # CONFIGURATION
    # -------------------------
    RTSP_STREAM_URL = "rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream1"  # Replace with your RTSP URL
    INFERENCE_INTERVAL = 1.0   # seconds between each frame processing
    API_ENDPOINT = "https://YOUR_API_ENDPOINT"  # Replace with your actual endpoint

    # The batch size that triggers an API call (set to 10 or 100 or your desired threshold)
    BATCH_SIZE = 1

    # Load your detection model
    if use_ultralytics:
        # Choose a small model for Raspberry Pi (e.g., YOLOv8n)
        model = YOLO("yolov8n.pt")  
    else:
        raise NotImplementedError(
            "No detection model available. Please install ultralytics or provide your own YOLO code."
        )

    # Open the RTSP stream
    cap = cv2.VideoCapture(RTSP_STREAM_URL)
    if not cap.isOpened():
        print("Error: Unable to open RTSP stream.")
        return

    print("RTSP stream opened successfully. Starting detection loop...")

    last_inference_time = 0

    # Buffer for batched results
    results_buffer = []

    while True:
        # Grab a frame
        ret, frame = cap.read()
        if not ret:
            print("Warning: Could not read frame from stream. Retrying...")
            time.sleep(1)
            continue

        # Only process if enough time has passed
        current_time = time.time()
        if (current_time - last_inference_time) >= INFERENCE_INTERVAL:
            last_inference_time = current_time

            # Run YOLO inference
            results = model(frame, verbose=False)[0]  # for ultralytics YOLO
            detections = results.boxes
            class_names = model.names if hasattr(model, 'names') else []

            person_count = 0
            car_count = 0
            demographies = []

            if detections is not None:
                for box in detections:
                    cls_id = int(box.cls[0].item())
                    confidence = float(box.conf[0].item())

                    # skip low-confidence detections
                    if confidence < 0.3:
                        continue

                    detected_class_name = (
                        class_names[cls_id] 
                        if cls_id < len(class_names) 
                        else str(cls_id)
                    )

                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                    # Count persons + optional demographic
                    if detected_class_name == "person":
                        person_count += 1
                        face_crop = frame[y1:y2, x1:x2]
                        demography = estimate_demography(face_crop)
                        demographies.append(demography)

                    # Count cars
                    if detected_class_name == "car":
                        car_count += 1

            # Build a single detection record
            detection_data = {
                "timestamp": int(time.time()),
                "person_count": person_count,
                "car_count": car_count,
                "demography": demographies
            }
            results_buffer.append(detection_data)

            # Check if we have enough data to send
            if len(results_buffer) >= BATCH_SIZE:
                # Send entire batch to the API
                payload = {
                    "batch": results_buffer
                }

                # try:
                #     response = requests.post(API_ENDPOINT, json=payload, timeout=5)
                #     if response.status_code == 200:
                #         print(f"[INFO] Sent {len(results_buffer)} results successfully.")
                #     else:
                #         print("[WARN] API returned status:", response.status_code, response.text)
                # except requests.exceptions.RequestException as e:
                #     print("[ERROR] Error sending data to API:", e)
                print(f"[INFO] Simulated sending {(results_buffer)} results to API.")

                # Clear the buffer after sending
                results_buffer.clear()

        # (Optional) to display feed:
        cv2.imshow("RTSP Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
           break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
