#!/usr/bin/env python3

import os
import json
import requests
import subprocess
from datetime import datetime

# API Endpoint
API_URL = "https://api.adboardbooking.com/api/camera/v1/config/UNKNOWN"

# Paths
CONFIG_FILE = "/var/www/stream/camera_config.json"
STREAM_SCRIPT = "/var/www/stream/start_ffmpeg.sh"
LOG_FILE = "/var/log/fetch_camera_url.log"

# Function to log messages
def log(message):
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")
    print(message)

def fetch_camera_config():
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code != 200:
            log(f"API request failed: {response.status_code} - {response.text}")
            return None
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"Error fetching API: {str(e)}")
        return None

def update_ffmpeg_script(rtsp_url):
    script_content = f"""#!/bin/bash
/usr/bin/ffmpeg -i "{rtsp_url}" -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -f hls /var/www/stream/live.m3u8
"""
    with open(STREAM_SCRIPT, "w") as script_file:
        script_file.write(script_content)
    
    os.chmod(STREAM_SCRIPT, 0o755)  # Make it executable
    log("Updated FFmpeg script.")

def main():
    log("Fetching camera configuration...")
    config = fetch_camera_config()
    
    if not config:
        log("Failed to retrieve valid camera configuration.")
        return
    
    rtsp_url = config.get('services').get('billboardMonitoring').get("rtspStreamUrl", "")
    
    if not rtsp_url or rtsp_url == "0":
        log("Invalid RTSP URL received.")
        return
    
    log(f"Received RTSP URL: {rtsp_url}")

    # Save config to file
    with open(CONFIG_FILE, "w") as config_file:
        json.dump(config, config_file, indent=4)
    
    # Update FFmpeg script
    update_ffmpeg_script(rtsp_url)
    
    log("Fetch process completed successfully.")

if __name__ == "__main__":
    main()
