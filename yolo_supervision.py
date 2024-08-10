import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import threading
import queue
import time
import requests

class RTSPDetector:
    def __init__(self, rtsp_url, model_path, frame_skip=2, api_url=None, api_key=None):
        self.rtsp_url = rtsp_url
        self.model_path = model_path
        self.frame_skip = frame_skip
        self.api_url = api_url
        self.api_key = api_key
        
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(rtsp_url)
        self.tracker = sv.ByteTrack()
        self.counts = defaultdict(int)
        self.total_car_count = 0
        self.previous_car_count = 0
        self.unique_car_ids = set()
        self.frame_queue = queue.Queue(maxsize=5)
        self.result_queue = queue.Queue(maxsize=5)
        self.stop_flag = threading.Event()
        self.fps_list = []
        self.FPS_HISTORY_SIZE = 20
        self.inference_thread = threading.Thread(target=self.inference_loop)
        self.callbacks = {
            "on_detection": None,
            "on_total_count": None
        }
        
    def set_callback(self, name, callback):
        if name in self.callbacks:
            self.callbacks[name] = callback
        else:
            raise ValueError(f"Invalid callback name: {name}")
    
    def send_car_count_to_cloud(self, count):
        if self.api_url:
            try:
                response = requests.post(
                    self.api_url,
                    json={"car_count": count},
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                )
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Failed to send car count to cloud: {e}")
    
    def inference_loop(self):
        while not self.stop_flag.is_set():
            try:
                frame = self.frame_queue.get(timeout=1)
                results = self.model(frame, agnostic_nms=True)[0]
                detections = sv.Detections(
                    xyxy=results.boxes.xyxy.cpu().numpy(),
                    confidence=results.boxes.conf.cpu().numpy(),
                    class_id=results.boxes.cls.cpu().numpy().astype(int)
                )
                tracked_detections = self.tracker.update_with_detections(detections)
                self.result_queue.put(tracked_detections)
            except queue.Empty:
                continue
    
    def process_frame(self):
        start_time = time.time()

        ret, frame = self.cap.read()
        if not ret:
            return False

        if self.frame_count % self.frame_skip == 0:
            if not self.frame_queue.full():
                self.frame_queue.put(frame)

        try:
            tracked_detections = self.result_queue.get_nowait()
            current_car_count = 0
            for class_id in [2]:  # Assuming 2 is the class ID for cars
                class_detections = [i for i, cls_id in enumerate(tracked_detections.class_id) if cls_id == class_id]
                for i in class_detections:
                    track_id = tracked_detections.tracker_id[i]
                    if track_id not in self.unique_car_ids:
                        self.unique_car_ids.add(track_id)
                        current_car_count += 1

            self.total_car_count += current_car_count

            if self.total_car_count != self.previous_car_count:
                if self.callbacks["on_total_count"]:
                    self.callbacks["on_total_count"](self.total_car_count)
                if self.api_url:
                    self.send_car_count_to_cloud(self.total_car_count)
                self.previous_car_count = self.total_car_count

            if self.callbacks["on_detection"]:
                self.callbacks["on_detection"](tracked_detections, current_car_count)

            for i, cls_id in enumerate(tracked_detections.class_id):
                if cls_id == 2:  # Assuming 2 is the class ID for cars
                    x1, y1, x2, y2 = map(int, tracked_detections.xyxy[i])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"Car {tracked_detections.tracker_id[i]}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        except queue.Empty:
            pass

        end_time = time.time()
        fps = 1 / (end_time - start_time)
        self.fps_list.append(fps)
        if len(self.fps_list) > self.FPS_HISTORY_SIZE:
            self.fps_list.pop(0)

        avg_fps = np.mean(self.fps_list)
        cv2.putText(frame, f"Cars Passed: {self.total_car_count}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, f"FPS: {avg_fps:.2f}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("YOLOv8 Multi-object Counting", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            return False

        return True

    def start(self):
        self.inference_thread.start()
        self.frame_count = 0

        while True:
            self.frame_count += 1
            if not self.process_frame():
                break

        self.stop_flag.set()
        self.inference_thread.join()
        self.cap.release()
        cv2.destroyAllWindows()

# Usage Example
def on_detection(tracked_detections, current_car_count):
    print(f"Current detections: {current_car_count}")

def on_total_count(total_car_count):
    print(f"Total cars passed: {total_car_count}")

detector = RTSPDetector(
    rtsp_url="rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2",
    model_path="yolov8n.pt",
    api_url="https://screens.adboardbooking.com/api/feed",
    api_key="your-api-key"
)

detector.set_callback("on_detection", on_detection)
detector.set_callback("on_total_count", on_total_count)

detector.start()
