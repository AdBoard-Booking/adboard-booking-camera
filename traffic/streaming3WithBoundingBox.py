import time
import statistics
import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    raise ImportError("Please install ultralytics or provide your own detection code.")


def main():
    ##########################
    # Configuration
    ##########################
    RTSP_STREAM_URL = "rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2"
    INFERENCE_INTERVAL = 1.0  # 1 FPS
    LONG_STAY_THRESHOLD = 20  # 20 seconds for "long-stay" logic

    # (Optional) Where to send data
    API_ENDPOINT = "https://YOUR_API_ENDPOINT"

    # Load YOLO model (e.g., YOLOv8n)
    model = YOLO("yolov8n.pt")

    # Open RTSP stream
    cap = cv2.VideoCapture(RTSP_STREAM_URL)
    if not cap.isOpened():
        print("Error: Unable to open RTSP stream.")
        return

    last_inference_time = 0

    # Variables for naive counting
    passed_count = 0  # total "passed" so far
    last_increase_time = time.time()

    # We'll keep a short history (window) of detection counts to smooth out flickers
    count_window_size = 3
    count_window = []

    # We also store a "stable_count" from the previous loop to compare changes
    prev_stable_count = 0

    class_names = model.names  # e.g. {0: 'person', 1: 'bicycle', 2: 'car', ...}

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Could not read frame. Retrying...")
            time.sleep(1)
            continue

        current_time = time.time()
        if (current_time - last_inference_time) >= INFERENCE_INTERVAL:
            last_inference_time = current_time

            ################################
            # 1) Detect how many "cars"
            ################################
            results = model(frame, verbose=False)[0]  
            detections = results.boxes

            raw_count = 0
            if detections is not None:
                for box in detections:
                    cls_id = int(box.cls[0].item())   # class index
                    conf = float(box.conf[0].item()) # confidence
                    if conf < 0.3:
                        continue

                    class_name = (
                        class_names[cls_id] if cls_id in class_names else str(cls_id)
                    )

                    # We are specifically interested in "car"
                    if class_name == "car":
                        raw_count += 1

                # -- End of loop counting cars --
            
            # 2) Keep a rolling window of the raw_count to smooth it
            count_window.append(raw_count)
            if len(count_window) > count_window_size:
                count_window.pop(0)

            # 3) Compute stable_count (using mean or median)
            if count_window:
                stable_count = int(round(statistics.mean(count_window)))
            else:
                stable_count = 0

            # 4) Naive Heuristics

            # Rule A: If stable_count > prev_stable_count, new "cars" arrived
            if stable_count > prev_stable_count:
                diff = stable_count - prev_stable_count
                passed_count += diff
                last_increase_time = current_time
                print(f"[INFO] Detected an increase of {diff}. Passed count: {passed_count}")

            # Rule B: If no increases for LONG_STAY_THRESHOLD & stable_count > 0,
            # we assume those are 'new' cars that haven't triggered a count increase
            time_since_increase = current_time - last_increase_time
            if time_since_increase > LONG_STAY_THRESHOLD and stable_count > 0:
                passed_count += stable_count
                print(f"[INFO] Long stay triggered, added {stable_count}, total: {passed_count}")
                last_increase_time = current_time

            # 5) Update previous stable count
            prev_stable_count = stable_count

            ###############################
            # 6) Print debug info
            ###############################
            print(
                f"[DEBUG] raw_count={raw_count}, stable_count={stable_count}, passed={passed_count}"
            )

            ################################
            # (Optional) Send data to an API
            ################################
            # payload = {
            #     "timestamp": int(current_time),
            #     "raw_count": raw_count,
            #     "stable_count": stable_count,
            #     "cars_passed_estimate": passed_count
            # }
            # try:
            #     response = requests.post(API_ENDPOINT, json=payload, timeout=5)
            #     if response.status_code != 200:
            #         print("[WARN] API returned:", response.status_code, response.text)
            # except requests.exceptions.RequestException as e:
            #     print("[ERROR] API request error:", e)

        #################################
        # 7) Draw bounding boxes on frame
        #################################
        # We can re-run YOLO or reuse `results`
        # For best performance, you could store `results` from above 
        # but keep in mind it might be from a second ago (depending on timing).
        # For simplicity, let's just reuse the same `results` from the last detection.

        if detections is not None:
            for box in detections:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                if conf < 0.3:
                    continue
                
                class_name = class_names[cls_id] if cls_id in class_names else str(cls_id)
                
                # We can draw bounding boxes for *any* class or specifically for "car".
                if class_name == "car":
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                    # Draw rectangle
                    color = (0, 255, 0)  # BGR: green
                    thickness = 2
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

                    # Label text with class and confidence
                    label_text = f"{class_name} {conf:.2f}"
                    font_scale = 0.5
                    font_thickness = 1
                    cv2.putText(
                        frame,
                        label_text,
                        (x1, max(0, y1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale,
                        color,
                        font_thickness
                    )
        
        # 8) Show the video with bounding boxes
        cv2.imshow("Frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
