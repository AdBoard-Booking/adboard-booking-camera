import cv2
import requests
import numpy as np
import time
import base64

API_TOKEN = 'your_api_token_here'
MODEL_URL = 'https://api-inference.huggingface.co/models/dandelin/vilt-b32-finetuned-vqa'
IMAGE_PATH = './processing-camera/image.jpg'
RTSP_URL = 'rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2'

def analyze_billboard(image_path):
    try:
        with open(image_path, 'rb') as image_file:
            image_buffer = image_file.read()

        response = requests.post(
            MODEL_URL,
            headers={
                'Authorization': f'Bearer {API_TOKEN}',
                'Content-Type': 'application/octet-stream'
            },
            data=image_buffer
        )

        print('Response:', response.json())
        return "Analysis successful"
    except requests.RequestException as e:
        print('Error:', e)
        raise Exception('An unexpected error occurred')

def is_billboard_running(image_path):
    with open(image_path, 'rb') as image_file:
        image = base64.b64encode(image_file.read()).decode()

    try:
        response = requests.post(
            MODEL_URL,
            json={
                'inputs': {
                    'image': image,
                    'question': 'Is the billboard running?',
                    'topK': 1
                }
            },
            headers={'Authorization': f'Bearer {API_TOKEN}'}
        )
        
        if response.json():
            return response.json()[0]['answer'] == 'yes'
        else:
            raise Exception('No response from model')
    except requests.RequestException as e:
        print('Error in request:', e)
        raise Exception('An unexpected error occurred')

def capture_image_from_rtsp(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print("Error: Could not open RTSP stream.")
        return None
    
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        cv2.imwrite(IMAGE_PATH, frame)  # Save the captured frame
        return IMAGE_PATH
    else:
        print("Error: Could not read frame.")
        return None

def post_status(status):
    print(status)

def main():
    while True:
        image_path = capture_image_from_rtsp(RTSP_URL)
        if image_path:
            running_status = is_billboard_running(image_path)
            post_status(running_status)
            analyze_billboard(image_path)

        time.sleep(60)  # Wait for 1 minute

if __name__ == "__main__":
    main()
