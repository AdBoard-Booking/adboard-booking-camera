import json
import os
import requests
from datetime import datetime
from collections import defaultdict

with open('/usr/local/bin/adboardbooking/registered_cameras.json', 'r') as f:
    camera_config = json.load(f)

def load_data(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def get_time_key(timestamp, aggregation_level):
    dt = datetime.fromtimestamp(timestamp)
    if aggregation_level == 'hourly':
        return dt.strftime("%Y-%m-%d %H:00")
    elif aggregation_level == 'daily':
        return dt.strftime("%Y-%m-%d")
    elif aggregation_level == 'monthly':
        return dt.strftime("%Y-%m")
    else:
        raise ValueError("Invalid aggregation level. Choose 'hourly', 'daily', or 'monthly'.")

def ensure_output_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_existing_data(filename, directory='output'):
    file_path = os.path.join(directory, filename)
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def save_json(new_data, filename, directory='output'):
    ensure_output_directory(directory)
    file_path = os.path.join(directory, filename)
    
    # Load existing data
    existing_data = load_existing_data(filename, directory)
    
    # Merge new data with existing data
    existing_data.update(new_data)
    
    # Save merged data
    with open(file_path, 'w') as f:
        json.dump(existing_data, f, indent=2)

def make_api_call(data, url='https://railway.adboardbooking.com/api/camera/feed'):
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()
    except requests.RequestException as e:
        print(f"API call failed: {e}")
        return None
    
def process_billboard_data():
    input_file = '/home/pi/adboard-booking-camera/CameraStreamingAI/billboard_data.json'
    data = load_data(input_file)
    
    # Prepare data for API call
    api_data = {
        "data": data,
        "deviceId": camera_config[0]["deviceId"],
        "cameraIp": camera_config[0]["cameraIp"]
    }
    
    # Make API call
    api_response = make_api_call(api_data)
    
    if api_response and api_response.get('response'):
        count = api_response['response'][0].get('count', 0)
        if count > 0:
            # Delete the input file after processing
            os.remove(input_file)
            print(f"\nAPI call successful. Deleted input file: {input_file}")
        else:
            print(f"\nAPI call successful, but count was not greater than 0. Input file not deleted.")
    else:
        print(f"\nAPI call failed or returned unexpected response. Input file not deleted.")

if __name__ == "__main__":
    process_billboard_data()