import cv2
import requests
import json
import time
import logging
import os
import base64
import sys
import argparse
import datetime
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
adjacent_folder = os.path.join(current_dir, '..', 'utils')  # Assuming 'utils' is the adjacent folder
sys.path.append(adjacent_folder)
import utils

# Argument parser for command-line parameters
parser = argparse.ArgumentParser(description="Object Tracking with YOLO and Supervision")
parser.add_argument("--verbose", type=int, choices=[0, 1], default=0, 
                    help="Set YOLO model verbosity: 0 (Silent), 1 (Default)")
parser.add_argument("--publish", type=int, choices=[0, 1], default=0, 
                    help="Set publish to server: 0 (Silent), 1 (Default)")

args = parser.parse_args()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



config = utils.load_config_for_device()

billboardMonitoring = config['services']['billboardMonitoring']
INTERVAL = billboardMonitoring.get('apiCallInterval', 60)  # Default interval of 60 seconds
FINAL_API_URL = billboardMonitoring.get('publishApiEndpoint')
OPENROUTER_API_KEY = billboardMonitoring.get('aiApiKey')
RTSP_STREAM_URL = billboardMonitoring.get("rtspStreamUrl", "rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2")

def capture_frame(rtsp_url):
    logging.info("Capturing frame from RTSP stream")
    cap = cv2.VideoCapture(rtsp_url)
    time.sleep(2)  # Allow buffer time for stream to stabilize
    
    if not cap.isOpened():
        logging.error("Couldn't open RTSP stream")
        return None
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        logging.error("Couldn't capture frame")
        return None
    
    _, buffer = cv2.imencode(".jpg", frame)
    image_blob = base64.b64encode(buffer).decode("utf-8")
    logging.info("Frame captured and converted to blob successfully")
    return image_blob


def analyze_image(image_blob):

    logging.info("Analyzing image using OpenRouter AI")
    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "I am a billboard owner, I want to know if my billboard is running. This is a digital billboard. Return a JSON response in the structure {hasScreenDefects:true, hasPatches:true, isOnline:true, details:''} that can be used directly in code."},
                    {
                        "type": "image_url",
                        "image_url":{
                            "url": f"data:image/jpeg;base64,{image_blob}"
                        }
                     }
                ]
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    
    if response.status_code == 200:
        response = response.json()
        
        output = response.get("choices")[0].get("message").get("content")
        cleaned_string = match = re.search(r'```json\n(.*?)\n```', output, re.DOTALL)
        
        if match: 
            json_string = match.group(1).strip() # Extract JSON content 
            
            json_object = json.loads(json_string) # Con
            
            logging.info(f"Image analysis completed successfully")
            return json_object
    else:
        logging.error(f"OpenRouter AI request failed {response.json()}")
        return None


def send_result(result):
    

    payload = {
        "deviceId": config.get("deviceId", "UNKNOWN"),  # Default if missing
        "timestamp": datetime.datetime.utcnow().isoformat(),  # Current timestamp in UTC
        **result  # Merge result JSON into the request body
    }

    logging.info(f"Sending result to final API {payload}")

    response = requests.post(billboardMonitoring.get('publishApiEndpoint'), json={"data": payload})
    
    if response.status_code == 200:
        logging.info("Final API call successful")
        return True
    else:
        logging.error("Final API call failed")
        return False


def main():

    while True:
        logging.info("Starting new iteration")
        image_blob = capture_frame(RTSP_STREAM_URL)
        if not image_blob:
            time.sleep(INTERVAL)
            continue
        
        analysis_result = analyze_image(image_blob)
        if not analysis_result:
            time.sleep(INTERVAL)
            continue
        
        if args.publish:
            send_result(analysis_result)

        logging.info("Iteration completed, waiting for next interval")
        
        time.sleep(INTERVAL)


if __name__ == "__main__":
    logging.info("Starting RTSP frame processing script")
    main()
