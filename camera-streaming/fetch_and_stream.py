#!/usr/bin/env python3

import requests
import subprocess
import time
import os
import sys
import logging
from datetime import datetime

# Add the boot/service directory to Python path to import utils
# sys.path.append('/opt/adboard/boot/service')

current_dir = os.path.dirname(os.path.abspath(__file__))
adjacent_folder = os.path.join(current_dir, '..', 'boot', 'services', 'utils')  # Assuming 'utils' is the adjacent folder
sys.path.append(adjacent_folder)

from utils import load_config_for_device
from mqtt import publish_log

# Set up logging
LOG_FILE = '/var/log/camera_stream.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def print(message, level='info'):
    """Log message to both file and MQTT"""
    if level == 'error':
        logger.error(message)
    else:
        logger.info(message)
    publish_log(message, level)

def fetch_rtsp_url():
    try:
        config = load_config_for_device()
        print(f"Config: {config}")
        if not config:
            print("Failed to load configuration", 'error')
            return None
            
        rtsp_url = config.get('services', {}).get('billboardMonitoring', {}).get('rtspStreamUrl')
        if not rtsp_url:
            print("No RTSP URL found in configuration", 'error')
            return None
            
        return rtsp_url
    except Exception as e:
        print(f"Error fetching configuration: {e}", 'error')
    return None

def start_ffmpeg(rtsp_url):
    try:
        # Ensure the output directory exists
        os.makedirs("/var/www/stream", exist_ok=True)
        
        # FFmpeg command with detailed logging
        command = [
            "ffmpeg",
            "-loglevel", "warning",  # Set log level to show warnings and errors
            "-i", rtsp_url,
            "-c:v", "copy",
            "-hls_time", "1",
            "-hls_list_size", "3",
            "-hls_flags", "delete_segments+append_list",
            "-start_number", "1",
            "-f", "hls",
            "/var/www/stream/live.m3u8"
        ]
        
        print(f"Starting FFmpeg with command: {' '.join(command)}")
        
        # Create a process with pipe for stdout and stderr
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Create separate threads to handle stdout and stderr
        def log_output(pipe, log_type):
            for line in pipe:
                line = line.strip()
                if line:
                    logger.info(f"FFmpeg {log_type}: {line}")

        from threading import Thread
        Thread(target=log_output, args=(process.stdout, "stdout"), daemon=True).start()
        Thread(target=log_output, args=(process.stderr, "stderr"), daemon=True).start()

        return process

    except Exception as e:
        print(f"Error starting FFmpeg: {str(e)}", 'error')
        return None

def monitor_process(process):
    """Monitor the FFmpeg process and return True if it needs to be restarted"""
    if process is None:
        return True
        
    return_code = process.poll()
    if return_code is not None:
        print(f"FFmpeg process exited with code {return_code}", 'error')
        # Get any remaining output
        stdout, stderr = process.communicate()
        if stdout:
            logger.info(f"Final stdout: {stdout}")
        if stderr:
            logger.error(f"Final stderr: {stderr}")
        return True
    return False

if __name__ == "__main__":
    print("Starting camera streaming service")
    process = None
    while True:
        try:
            if monitor_process(process):
                rtsp_url = fetch_rtsp_url()
                if rtsp_url:
                    print(f"Starting stream from: {rtsp_url}")
                    process = start_ffmpeg(rtsp_url)
                    if process is None:
                        print("Failed to start FFmpeg process", 'error')
                        time.sleep(10)
                else:
                    print("Failed to fetch RTSP URL. Retrying in 10 seconds...", 'error')
                    time.sleep(10)
            time.sleep(1)  # Check process status every second
            
        except Exception as e:
            print(f"Unexpected error in main loop: {str(e)}", 'error')
            time.sleep(10) 