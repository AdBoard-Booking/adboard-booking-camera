import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import threading
import queue
import time
import requests
import json
import logging
import os

logging.getLogger("ultralytics").setLevel(logging.ERROR)

class RTSPDetector:
    def __init__(self, rtsp_url, model_path, frame_skip=2, api_url=None, api_key=None, api_interval=5):
        self.rtsp_url = rtsp_url
        self.model_path = model_path
        self.frame_skip = frame_skip
        self.api_interval = api_interval  # Time in minutes between API calls
        self.last_api_call_time = 0  # Track the last time we made an API call
        self.api_url = api_url
        self.api_key = api_key
        # Load camera configuration
        with open('/usr/local/bin/adboardbooking/registered_cameras.json', 'r') as f:
            self.camera_config = json.load(f)
        
        # Find matching camera config
        self.camera_data = next((cam for cam in self.camera_config if cam['rtspUrl'] == self.rtsp_url), None)
        if not self.camera_data:
            raise ValueError(f"No matching camera configuration found for RTSP URL: {self.rtsp_url}")
        
        self.camera_ip = self.rtsp_url.split('@')[1].split('/')[0]
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(rtsp_url)
        self.tracker = sv.ByteTrack()
        self.counts = defaultdict(int)
        self.total_car_count = self.load_car_count()
        self.previous_car_count = self.total_car_count
        self.unique_car_ids = set()
        self.frame_queue = queue.Queue(maxsize=5)
        self.result_queue = queue.Queue(maxsize=5)
        self.stop_flag = threading.Event()
        self.fps_list = []
        self.FPS_HISTORY_SIZE = 20
        self.current_fps = 0
        self.inference_thread = threading.Thread(target=self.inference_loop)
        self.callbacks = {
            "on_detection": None,
            "on_total_count": None
        }

    def get_count_file_path(self):
        return f"/home/pi/adboard-booking-camera/CameraStreamingAI/car_count_{self.camera_ip.replace('.', '_')}.json"

    def load_car_count(self):
        count_file = self.get_count_file_path()
        if os.path.exists(count_file):
            with open(count_file, 'r') as f:
                data = json.load(f)
                return data.get('total_car_count', 0)
        return 0

    def save_car_count(self):
        count_file = self.get_count_file_path()
        data = {
            'total_car_count': self.total_car_count,
            'last_updated': time.strftime("%Y-%m-%d %H:%M:%S"),
            'device_id': self.camera_data['deviceId'],
            'current_fps': self.current_fps
        }
        with open(count_file, 'w') as f:
            json.dump(data, f, indent=4)
    
    def set_callback(self, name, callback):
        if name in self.callbacks:
            self.callbacks[name] = callback
        else:
            raise ValueError(f"Invalid callback name: {name}")
    
    def send_car_count_to_cloud(self):
        current_time = time.time()
        if self.api_url and (current_time - self.last_api_call_time >= self.api_interval * 60):
            try:
                payload = {
                    "carsCount": self.total_car_count,
                    "deviceId": self.camera_data['deviceId'],
                    "cameraIp": self.camera_ip,
                    "fps": self.current_fps
                }
                headers = {
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    self.api_url,
                    data=json.dumps(payload),
                    headers=headers
                )
                response.raise_for_status()
                self.save_car_count()  # Save the count after successful API call
                self.last_api_call_time = current_time  # Update the last API call time
                print(f"API call made at {time.strftime('%Y-%m-%d %H:%M:%S')}")
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
                self.previous_car_count = self.total_car_count

            # Check if it's time to make an API call
            self.send_car_count_to_cloud()

            if self.callbacks["on_detection"]:
                self.callbacks["on_detection"](tracked_detections, current_car_count)

            # for i, cls_id in enumerate(tracked_detections.class_id):
            #     if cls_id == 2:  # Assuming 2 is the class ID for cars
            #         x1, y1, x2, y2 = map(int, tracked_detections.xyxy[i])
            #         cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            #         cv2.putText(frame, f"Car {tracked_detections.tracker_id[i]}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        except queue.Empty:
            pass

        end_time = time.time()
        fps = 1 / (end_time - start_time)
        self.fps_list.append(fps)
        if len(self.fps_list) > self.FPS_HISTORY_SIZE:
            self.fps_list.pop(0)

        self.current_fps = np.mean(self.fps_list)
        # cv2.putText(frame, f"Cars Passed: {self.total_car_count}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        # cv2.putText(frame, f"FPS: {self.current_fps:.2f}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        # cv2.imshow("YOLOv8 Multi-object Counting", frame)

        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     return False

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
        self.save_car_count()  # Save the count when stopping

# Usage Example
def on_detection(tracked_detections, current_car_count):
    print(f"Current detections: {current_car_count}")

def on_total_count(total_car_count):
    print(f"Total cars passed: {total_car_count}")

detector = RTSPDetector(
    rtsp_url="rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2",
    model_path="/home/pi/adboard-booking-camera/CameraStreamingAI/yolov8n.pt",
    api_url="https://railway.adboardbooking.com/api/camera/feed",
    api_key="your-api-key",
    api_interval=5  # Set the interval to 5 minutes
)

detector.set_callback("on_detection", on_detection)
detector.set_callback("on_total_count", on_total_count)

detector.start()