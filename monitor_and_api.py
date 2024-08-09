import time
import json
import requests
from datetime import datetime, timezone
import os

# Configuration
FILE_PATH = 'count_data.json'
API_ENDPOINT = 'https://railway.adboardbooking.com/api/camera/feed'
CAMERA_ID = '667fca1dbe954ea1238a2042'
CHECK_INTERVAL = 1  # seconds

class CountDataHandler:
    def __init__(self):
        self.last_modified = 0
        self.last_data = None

    def check_file_change(self):
        try:
            current_modified = os.path.getmtime(FILE_PATH)
            if current_modified != self.last_modified:
                self.last_modified = current_modified
                with open(FILE_PATH, 'r') as file:
                    data = json.load(file)
                
                if data != self.last_data:
                    self.last_data = data
                    print(f"File changed. New data: {data}")
                    self.make_api_call(data)
        except FileNotFoundError:
            print(f"File not found: {FILE_PATH}")
        except json.JSONDecodeError:
            print("Error reading JSON file. It may be malformed.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def make_api_call(self, data):
        try:
            payload = {
                "cameraId": CAMERA_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "carsCount": data.get("total_car_count", 0),
                "personsCount": data.get("total_person_count", 0)
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
    handler = CountDataHandler()

    print(f"Monitoring {FILE_PATH} for changes. Press Ctrl+C to stop.")

    try:
        while True:
            handler.check_file_change()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("Monitoring stopped.")