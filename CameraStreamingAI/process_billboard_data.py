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

def analyze_traffic_flow(data, aggregation_level):
    aggregated_data = defaultdict(lambda: defaultdict(list))
    for timestamp_str, detections in sorted(data.items()):
        timestamp = int(timestamp_str)
        time_key = get_time_key(timestamp, aggregation_level)
        for obj_type in detections:
            aggregated_data[time_key][obj_type].append(timestamp)

    flow_metrics = defaultdict(dict)
    for time_key, objects in aggregated_data.items():
        for obj_type, timestamps in objects.items():
            total_duration = 0
            unique_objects = 0
            last_end = None

            for timestamp in sorted(timestamps):
                if last_end is None or timestamp - last_end > 1:
                    unique_objects += 1
                    if last_end is not None:
                        total_duration += last_end - timestamps[0]
                    timestamps[0] = timestamp
                last_end = timestamp

            if last_end is not None:
                total_duration += last_end - timestamps[0]

            avg_duration = total_duration / unique_objects if unique_objects > 0 else 0
            
            if aggregation_level == 'hourly':
                time_period = 1
            elif aggregation_level == 'daily':
                time_period = 24
            elif aggregation_level == 'monthly':
                time_period = 24 * 30  # Approximation

            flow_rate = unique_objects / time_period  # objects per hour

            flow_metrics[time_key][obj_type] = {
                "uniqueObjects": unique_objects,
                "totalDuration": total_duration,
                "averageDuration": avg_duration,
                "flowRate": flow_rate
            }

    return flow_metrics

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

def print_flow_metrics(metrics, aggregation_level):
    for time_key, objects in sorted(metrics.items()):
        print(f"\n{aggregation_level.capitalize()} Period: {time_key}")
        for obj_type, data in objects.items():
            print(f"  Object Type: {obj_type}")
            print(f"    Estimated Unique Objects: {data['uniqueObjects']}")
            print(f"    Total Presence Duration: {data['totalDuration']} seconds")
            print(f"    Average Presence Duration: {data['averageDuration']:.2f} seconds")
            print(f"    Estimated Flow Rate: {data['flowRate']:.2f} per hour")

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
    
    aggregation_levels = ['hourly', 'daily', 'monthly']
    for level in aggregation_levels:
        print(f"\nAnalyzing at {level.capitalize()} level:")
        flow_metrics = analyze_traffic_flow(data, level)
        print_flow_metrics(flow_metrics, level)
        
        # Save the analyzed data to a JSON file in the output directory
        output_filename = f'billboardMetrics_{level}.json'
        save_json(flow_metrics, output_filename)
        print(f"Updated {level} metrics in output/{output_filename}")
    
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