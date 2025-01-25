import time
import statistics
import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    raise ImportError("Please install ultralytics or provide your own detection code.")


def get_cpu_serial():
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.strip().split(":")[1].strip()
    except Exception as e:
        print(f"[ERROR] Unable to read CPU serial: {e}")
    return "UNKNOWN"

def main():
    ##########################
    # Configuration
    ##########################
    RTSP_STREAM_URL = "rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2"
    INFERENCE_INTERVAL = 1.0  # 1 FPS
    LONG_STAY_THRESHOLD = 20  # 20 seconds for "long-stay" logic
    DEVICE_ID = get_cpu_serial()

    # (Optional) Where to send data
    API_ENDPOINT = "https://YOUR_API_ENDPOINT"

    model = YOLO("yolov8n.pt")  # YOLOv8 nano; pick a small model for Raspberry Pi

    cap = cv2.VideoCapture(RTSP_STREAM_URL)
    if not cap.isOpened():
        print("Error: Unable to open RTSP stream.")
        return

    last_inference_time = 0

    # Variables for our naive logic
    passed_count = 0  # total "passed" so far
    last_increase_time = time.time()

    # We'll keep a short history (window) of detection counts to smooth out flickers
    count_window_size = 3
    count_window = []

    # We also store a "stable_count" from the previous loop to compare changes
    prev_stable_count = 0

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
            # 1) Detect how many persons
            ################################
            results = model(frame, verbose=False)[0]
            detections = results.boxes
            class_names = model.names

            raw_count = 0
            if detections is not None:
                for box in detections:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    if conf < 0.3:
                        continue
                    class_name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
                    if class_name == "car":
                        raw_count += 1

            # Add this raw count to our rolling window
            count_window.append(raw_count)
            if len(count_window) > count_window_size:
                count_window.pop(0)

            ################################
            # 2) Compute stable_count
            ################################
            # We can use median to ignore outliers (or use mean if you prefer).
            if count_window:
                stable_count = int(round(statistics.mean(count_window)))
            else:
                stable_count = 0

            # 3) Naive Heuristics

            # Rule A: If stable_count > prev_stable_count, new people arrived
            if stable_count > prev_stable_count:
                diff = stable_count - prev_stable_count
                passed_count += diff
                last_increase_time = current_time
                print(f"[INFO] Detected an increase of {diff}. Passed count: {passed_count}")

            # Rule B: If no increases for LONG_STAY_THRESHOLD and stable_count still > 0,
            # we assume those are 'new' people who haven't triggered a count increase
            time_since_increase = current_time - last_increase_time
            if time_since_increase > LONG_STAY_THRESHOLD and stable_count > 0:
                passed_count += stable_count
                print(f"[INFO] Long stay triggered, added {stable_count}, total: {passed_count}")
                last_increase_time = current_time

            # Update prev_stable_count
            prev_stable_count = stable_count

            ################################
            # (Optional) Send data to an API
            ################################
            # payload = {
            #     "timestamp": int(current_time),
            #     "raw_count": raw_count,            # detection before smoothing
            #     "stable_count": stable_count,      # after smoothing
            #     "people_passed_estimate": passed_count
            # }
            # try:
            #     response = requests.post(API_ENDPOINT, json=payload, timeout=5)
            #     if response.status_code != 200:
            #         print("[WARN] API returned:", response.status_code, response.text)
            # except requests.exceptions.RequestException as e:
            #     print("[ERROR] API request error:", e)

            print(f"[DEBUG] raw_count={raw_count}, stable_count={stable_count}, passed={passed_count}")

        # (Optional) Show the frame
        # cv2.imshow("Frame", frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
