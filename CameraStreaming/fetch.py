#!/usr/bin/env python3

import os
import json
import requests
import subprocess
from datetime import datetime
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Endpoint
API_URL = "https://railway.adboardbooking.com/api/camera/v1/config/UNKNOWN"

# Paths
CONFIG_FILE = "/var/www/stream/camera_config.json"
STREAM_SCRIPT = "/var/www/stream/start_ffmpeg.sh"
LOG_FILE = "/var/log/fetch_camera_url.log"

# Function to log messages
def log(message):
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")
    print(message)

def get_cpu_serial():
    """Fetch the CPU serial number as a unique device ID."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.strip().split(":")[1].strip()
    except Exception as e:
        logger.error(f"Unable to read CPU serial: {e}")
    return "UNKNOWN"

def fetch_camera_config():
    """Fetch camera configuration from the API."""
    device_id = get_cpu_serial()
    config_url = f"https://railway.adboardbooking.com/api/camera/v1/config/{device_id}"
    
    try:
        response = requests.get(config_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch camera config: {e}")
        return None

def update_ffmpeg_script(rtsp_url):
    script_content = f"""#!/bin/bash
/usr/bin/ffmpeg -i "{rtsp_url}" -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -f hls /var/www/stream/live.m3u8
"""
    with open(STREAM_SCRIPT, "w") as script_file:
        script_file.write(script_content)
    
    os.chmod(STREAM_SCRIPT, 0o755)  # Make it executable
    log("Updated FFmpeg script.")

def generate_ffmpeg_config():
    """Generate FFmpeg configuration file."""
    config = fetch_camera_config()
    if not config:
        logger.error("Failed to fetch configuration")
        sys.exit(1)

    rtsp_url = config.get("rtspStreamUrl", "rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2")
    
    ffmpeg_cmd = f"""[Unit]
Description=FFmpeg RTSP to HLS Stream
After=network.target

[Service]
ExecStart=/usr/bin/ffmpeg -i {rtsp_url} -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -f hls /var/www/stream/live.m3u8
Restart=always
RestartSec=10
StandardOutput=file:/var/log/ffmpeg_stream.log
StandardError=file:/var/log/ffmpeg_stream.err
User=root

[Install]
WantedBy=multi-user.target
"""
    
    # Write the configuration to the systemd service file
    service_file = "/etc/systemd/system/ffmpeg-stream.service"
    try:
        with open(service_file, "w") as f:
            f.write(ffmpeg_cmd)
        logger.info(f"FFmpeg service configuration written to {service_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to write FFmpeg service configuration: {e}")
        return False

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
    if generate_ffmpeg_config():
        logger.info("FFmpeg configuration generated successfully")
        sys.exit(0)
    else:
        logger.error("Failed to generate FFmpeg configuration")
        sys.exit(1)
