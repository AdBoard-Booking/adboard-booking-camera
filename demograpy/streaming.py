import datetime
import time
import statistics
import cv2
import numpy as np
import requests
import threading
import queue
import json

ENABLE_IMG_SHOW = True
ENABLE_API_CALL = True
ENABLE_BOUNDING_BOX = True

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
        batch = queue.get()
        if batch is None:
            break

        try:
            print(f"[DEBUG] Sending batch: {len(batch)}")
            response = requests.post(endpoint, json={"data": batch}, timeout=5)
            if response.status_code == 200:
                print(f"[INFO] Batch sent successfully: {len(batch)}")
                save_detection_batch(detection_batch_file, [])
            else:
                print(f"[WARN] API returned: {response.status_code}, {response.text}")
                queue.put(batch)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API request error: {e}")
            queue.put(batch)

        queue.task_done()

def load_age_gender_models():
    face_net = cv2.dnn.readNetFromCaffe("models/face_deploy.prototxt", "models/face_net.caffemodel")
    age_net = cv2.dnn.readNetFromCaffe("models/age_deploy.prototxt", "models/age_net.caffemodel")
    gender_net = cv2.dnn.readNetFromCaffe("models/gender_deploy.prototxt", "models/gender_net.caffemodel")
    return face_net, age_net, gender_net

def detect_age_gender(face, models):
    face_net, age_net, gender_net = models
    age_list = ['0-2', '4-6', '8-12', '15-20', '25-32', '38-43', '48-53', '60-100']
    gender_list = ['Male', 'Female']

    face_blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227), 
                                      (78.4263377603, 87.7689143744, 114.895847746), swapRB=False)
    
    gender_net.setInput(face_blob)
    gender_preds = gender_net.forward()
    gender = gender_list[gender_preds[0].argmax()]

    age_net.setInput(face_blob)
    age_preds = age_net.forward()
    age = age_list[age_preds[0].argmax()]

    return age, gender

def main():
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
    SAVE_INTERVAL = config.get("saveInterval", 60)
    API_CALL_INTERVAL = config.get("apiCallInterval", 300)
    count_window_size = config.get("countWindowSize", 5)
    DETECTION_BATCH_FILE = "detection_batch.json"

    print(f"[INFO] Loaded configuration: {config}")

    model = YOLO("yolov8n-person.pt")
    face_net, age_net, gender_net = load_age_gender_models()

    cap = cv2.VideoCapture(RTSP_STREAM_URL)
    if not cap.isOpened():
        print("Error: Unable to open RTSP stream.")
        return

    last_inference_time = 0
    last_save_time = time.time()
    last_api_call_time = time.time()

    detection_batch = load_detection_batch(DETECTION_BATCH_FILE)
    
    last_increase_time = time.time()

    count_window = {"person": []}
    prev_stable_count = {"person": 0}

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

            results = model(frame, verbose=False)[0]
            detections = results.boxes
            class_names = model.names

            raw_count = {"person": 0}
            new_count = {"person": 0}
            new_people_info = []
            if detections is not None:
                for box in detections:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    if conf < 0.3:
                        continue
                    class_name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
                    # Get box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                     # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Add confidence score
                    conf = float(box.conf[0])
                    cv2.putText(frame, f"{class_name} {conf:.2f} ", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    if class_name == "person":
                        raw_count["person"] += 1
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        face = frame[y1:y2, x1:x2]
                        if face.size > 0:
                            age, gender = detect_age_gender(face, (face_net, age_net, gender_net))
                            new_people_info.append({"age": age, "gender": gender})

            count_window["person"].append(raw_count["person"])
            if len(count_window["person"]) > count_window_size:
                count_window["person"].pop(0)

            stable_count = {
                "person": int(round(statistics.median(count_window["person"]))) if count_window["person"] else 0
            }

            if stable_count["person"] > prev_stable_count["person"]:
                diff = stable_count["person"] - prev_stable_count["person"]
                new_count['person'] = diff
                last_increase_time = current_time
                print(f"[INFO] Detected {diff} new people.")
                print(f"[INFO] New people details: {new_people_info}")

            time_since_increase = current_time - last_increase_time
            for obj in raw_count:
                if time_since_increase > LONG_STAY_THRESHOLD and stable_count[obj] > 0:
                    new_count[obj] = stable_count[obj]
                    print(f"[INFO] Long stay triggered, added {stable_count[obj]} {obj}s")
                    last_increase_time = current_time

            prev_stable_count = stable_count

            if any(new_count[obj] > 0 for obj in new_count):
                detection_batch.append({
                    "cameraUrl": RTSP_STREAM_URL,
                    "deviceId": DEVICE_ID,
                    "timestamp": int(current_time) * 1000,
                    "newCount": new_count,  # New detections since last inference
                    "newPeopleInfo": new_people_info,
                    "stableCount": stable_count,
                })

            if (current_time - last_save_time) >= SAVE_INTERVAL:
                save_detection_batch(DETECTION_BATCH_FILE, detection_batch)
                last_save_time = current_time

            if ENABLE_API_CALL and (current_time - last_api_call_time) >= API_CALL_INTERVAL and detection_batch:
                api_queue.put(detection_batch.copy())
                detection_batch.clear()
                last_api_call_time = current_time

            print(f"[{current_time}] raw_count={raw_count} stable_count={stable_count}")

        if ENABLE_IMG_SHOW:
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    api_queue.put(None)
    api_thread.join()

if __name__ == "__main__":
    main()
