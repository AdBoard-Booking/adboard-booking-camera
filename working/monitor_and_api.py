import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
from datetime import datetime, timezone

# Configuration
FILE_PATH = 'count_data.json'
API_ENDPOINT = 'http://localhost:3000/api/camera/feed/'
CAMERA_ID = '667fca1dbe954ea1238a2042'
CHECK_INTERVAL = 1  # seconds

class CountDataHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_modified = time.time()
        self.last_data = None

    def on_modified(self, event):
        if event.src_path == FILE_PATH:
            current_time = time.time()
            if (current_time - self.last_modified) > 1:  # Debounce to avoid multiple calls for a single save
                self.last_modified = current_time
                self.handle_file_change()

    def handle_file_change(self):
        try:
            with open(FILE_PATH, 'r') as file:
                data = json.load(file)
            
            if data != self.last_data:
                self.last_data = data
                print(f"File changed. New data: {data}")
                self.make_api_call(data)
        except json.JSONDecodeError:
            print("Error reading JSON file. It may be malformed.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def make_api_call(self, data):
        try:
            payload = {
                "cameraId": CAMERA_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "carsCount": data.get("total_car_count", 0)
            }
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.post(API_ENDPOINT, json=payload, headers=headers)
            if response.status_code == 200:
                print("API call successful")
            else:
                print(f"API call failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
        except requests.RequestException as e:
            print(f"API call failed: {str(e)}")

if __name__ == "__main__":
    event_handler = CountDataHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    print(f"Monitoring {FILE_PATH} for changes. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()