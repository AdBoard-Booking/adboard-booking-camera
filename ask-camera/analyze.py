import cv2
import requests
import json
import time
import logging
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RTSP_URL = 'rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2'
FINAL_API_URL = "https://your-api-endpoint.com/process"  # Replace with final API endpoint
OPENROUTER_API_KEY = "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"
INTERVAL = 60  # Interval in seconds


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
        output = response.json().get("choices")[0].get("message").get("content")
        logging.info(f"Image analysis completed successfully {output}")

        return response.json()
    else:
        logging.error("OpenRouter AI request failed")
        return None


def send_result(result):
    logging.info("Sending result to final API")
    response = requests.post(FINAL_API_URL, json=result)
    
    if response.status_code == 200:
        logging.info("Final API call successful")
        return True
    else:
        logging.error("Final API call failed")
        return False


def main():
    while True:
        logging.info("Starting new iteration")
        image_blob = capture_frame(RTSP_URL)
        if not image_blob:
            time.sleep(INTERVAL)
            continue
        
        analysis_result = analyze_image(image_blob)
        if not analysis_result:
            time.sleep(INTERVAL)
            continue
        
        # send_result(analysis_result)
        logging.info("Iteration completed, waiting for next interval")
        
        time.sleep(INTERVAL)


if __name__ == "__main__":
    logging.info("Starting RTSP frame processing script")
    main()
