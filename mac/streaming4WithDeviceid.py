import time
import statistics
import cv2
import numpy as np
import requests
import threading
import queue
import json

ENABLE_IMG_SHOW = False
ENABLE_API_CALL = True
ENABLE_BOUNDING_BOX = False

try:
    from ultralytics import YOLO
except ImportError:
    raise ImportError("Please install ultralytics or provide your own detection code.")

def get_cpu_serial():
    """Fetch the CPU serial number as a unique device ID."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.strip().split(":")[1].strip()
    except Exception as e:
        print(f"[ERROR] Unable to read CPU serial: {e}")
    return "UNKNOWN"

def load_detection_batch(filename):
    """Load detection batch from a file."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_detection_batch(filename, detection_batch):
    """Save detection batch to a file."""
    try:
        with open(filename, "w") as f:
            json.dump(detection_batch, f)
    except Exception as e:
        print(f"[ERROR] Unable to save detection batch: {e}")

def load_config(device_id):
    """Load configuration from the API."""
    # config_url = f"http://localhost:3000/api/camera/v1/config/{device_id}"
    config_url = f"https://api.adboardbooking.com/api/camera/v1/config/{device_id}"
    try:
        response = requests.get(config_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Unable to load config: {e}")
        return None

def api_worker(queue, endpoint, detection_batch_file):
    """Worker thread to send API requests."""
    while True:
        batch = queue.get()  # Get a batch from the queue
        if batch is None:
            break  # Stop the thread if None is received

        try:
            print(f"[DEBUG] Sending batch: {len(batch)}")
            response = requests.post(endpoint, json={"data": batch}, timeout=5)
            if response.status_code == 200:
                print(f"[INFO] Batch sent successfully: {len(batch)}")
                save_detection_batch(detection_batch_file, [])  # Clear the file after successful API call
            else:
                print(f"[WARN] API returned: {response.status_code}, {response.text}")
                # Re-add batch to the queue for retry
                queue.put(batch)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API request error: {e}")
            # Re-add batch to the queue for retry
            queue.put(batch)

        queue.task_done()

def main():
    ##########################
    # Configuration
    ##########################
    DEVICE_ID = get_cpu_serial()
    print(f"[INFO] Device ID: {DEVICE_ID}")

    config = load_config(DEVICE_ID)
    if not config:
        print("[ERROR] Failed to load configuration. Exiting...")
        return

    RTSP_STREAM_URL = config.get("rtspStreamUrl", "rtsp://default_url")
    INFERENCE_INTERVAL = config.get("inferenceInterval", 1.0)
    LONG_STAY_THRESHOLD = config.get("longStayThreshold", 20)
    API_ENDPOINT = config.get("apiEndpoint", "https://api.adboardbooking.com/api/camera/v1/traffic")
    SAVE_INTERVAL = config.get("saveInterval", 10)  # Save to file every 10 minutes (600 seconds)
    API_CALL_INTERVAL = config.get("apiCallInterval", 300)
    count_window_size = config.get("countWindowSize", 5)
    DETECTION_BATCH_FILE = "detection_batch.json"

    print(f"[INFO] Loaded configuration: {config}")

    model = YOLO("yolov8n.pt")  # YOLOv8 nano; pick a small model for Raspberry Pi

    cap = cv2.VideoCapture(RTSP_STREAM_URL)
    if not cap.isOpened():
        print("Error: Unable to open RTSP stream.")
        return

    last_inference_time = 0
    last_save_time = time.time()
    last_api_call_time = time.time()

    # Variables for our naive logic
    detection_batch = load_detection_batch(DETECTION_BATCH_FILE)
    if detection_batch:
        passed_count = detection_batch[-1]["passedCount"]
    else:
        passed_count = {"car": 0, "person": 0}
    print(f"[INFO] Loaded passed count: {passed_count}")
    last_increase_time = time.time()

    # We'll keep a short history (window) of detection counts to smooth out flickers
    count_window = {"car": [], "person": []}

    # We also store a "stable_count" from the previous loop to compare changes
    prev_stable_count = {"car": 0, "person": 0}

    # Queue for API requests
    api_queue = queue.Queue()
    api_thread = threading.Thread(target=api_worker, args=(api_queue, API_ENDPOINT, DETECTION_BATCH_FILE), daemon=True)
    api_thread.start()

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
            # 1) Detect how many cars and persons
            ################################
            results = model(frame, verbose=False)[0]
            detections = results.boxes
            class_names = model.names

            raw_count = {"car": 0, "person": 0}
            if detections is not None:
                for box in detections:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    if conf < 0.3:
                        continue
                    class_name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
                    if class_name in raw_count:
                        raw_count[class_name] += 1

            # Add this raw count to our rolling window
            for obj in raw_count:
                count_window[obj].append(raw_count[obj])
                if len(count_window[obj]) > count_window_size:
                    count_window[obj].pop(0)

            ################################
            # 2) Compute stable_count
            ################################
            stable_count = {
                obj: int(round(statistics.median(count_window[obj]))) if count_window[obj] else 0
                for obj in raw_count
            }

            # 3) Naive Heuristics
            for obj in raw_count:
                if stable_count[obj] > prev_stable_count[obj]:
                    diff = stable_count[obj] - prev_stable_count[obj]
                    passed_count[obj] += diff
                    last_increase_time = current_time
                    print(f"[INFO] Detected an increase of {diff} {obj}s. Passed count: {passed_count[obj]}")

            time_since_increase = current_time - last_increase_time
            for obj in raw_count:
                if time_since_increase > LONG_STAY_THRESHOLD and stable_count[obj] > 0:
                    passed_count[obj] += stable_count[obj]
                    print(f"[INFO] Long stay triggered, added {stable_count[obj]} {obj}s, total: {passed_count[obj]}")
                    last_increase_time = current_time

            prev_stable_count = stable_count

            ################################
            # Add to batch only if stableCount > 0
            ################################
            if any(stable_count[obj] > 0 for obj in stable_count):
                detection_batch.append({
                    "cameraUrl": RTSP_STREAM_URL,
                    "deviceId": DEVICE_ID,
                    "timestamp": int(current_time),
                    "rawCount": raw_count,
                    "stableCount": stable_count,
                    "passedCount": passed_count
                })

            ################################
            # Save detection batch every SAVE_INTERVAL
            ################################
            if (current_time - last_save_time) >= SAVE_INTERVAL:
                save_detection_batch(DETECTION_BATCH_FILE, detection_batch)
                last_save_time = current_time

            ################################
            # Make API call every API_CALL_INTERVAL
            ################################
            if ENABLE_API_CALL and (current_time - last_api_call_time) >= API_CALL_INTERVAL:
                api_queue.put(detection_batch.copy())
                detection_batch.clear()
                last_api_call_time = current_time

            print(f"[{int(current_time)*1000}] raw_count={raw_count}, stable_count={stable_count}, passed={passed_count}, detection_batch={len(detection_batch)}")

        if detections is not None and ENABLE_BOUNDING_BOX and ENABLE_IMG_SHOW:
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

        # (Optional) Show the frame
        if ENABLE_IMG_SHOW:
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    api_queue.put(None)  # Signal the API thread to exit
    api_thread.join()

if __name__ == "__main__":
    main()
