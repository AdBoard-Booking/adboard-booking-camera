#!/usr/bin/env python3

import requests
import subprocess
import time
import os
import sys
import logging
import threading
import json
import datetime
import pytz
# Add the boot/service directory to Python path to import utils
# sys.path.append('/opt/adboard/boot/service')

current_dir = os.path.dirname(os.path.abspath(__file__))
adjacent_folder = os.path.join(current_dir, '..', 'boot', 'services', 'utils')  # Assuming 'utils' is the adjacent folder
sys.path.append(adjacent_folder)

from utils import load_config_for_device
from mqtt import publish_log, subscribe_to_topic

test_topic = "ffmpeg-stream"

config_lock = threading.Lock()
global_config = None

CONFIG_REFRESH_INTERVAL = 300

ist_tz = pytz.timezone('Asia/Kolkata')
logging.Formatter.converter = lambda *args: datetime.datetime.now(ist_tz).timetuple()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # This ensures logs go to stdout
    ]
)

logger = logging.getLogger(__name__)

def message_handler(client, userdata, message):
    """Handle incoming MQTT messages"""
    try:
        topic = message.topic
        payload = message.payload.decode()
        
        # Try to parse JSON if possible
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            pass  # Keep payload as string if it's not JSON
            
        logger.info(f"Received message on topic {topic}: {payload}")
        
        if topic.startswith(test_topic):
            # Handle system topic messages
            if payload == "reload":
                logger.info("Reloading service")
                # reload service
                os.system("sudo systemctl restart ffmpeg-stream")
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")

# Subscribe to topic with message handler after logger is initialized
subscribe_to_topic(test_topic, message_handler)

def update_config():
    """Continuously update config in background"""
    global global_config
    while True:
        try:
            new_config = load_config_for_device()
            if new_config:  # Only update if we got a valid config
                with config_lock:
                    global_config = new_config
                logger.info(f"Configuration refreshed successfully: \n{json.dumps(new_config, indent=2)}")
        except Exception as e:
            logger.error(f"Error refreshing config: {str(e)}")
        
        time.sleep(CONFIG_REFRESH_INTERVAL)

def get_current_config():
    """Thread-safe getter for current config"""
    with config_lock:
        return global_config

def fetch_rtsp_url():
    while True:
        try:
            config = get_current_config()

            if not config:
                print("No configuration found", 'error')
                sys.stdout.flush()
                time.sleep(5)
                continue
                
            rtsp_url = config.get('rtspStreamUrl')
            if not rtsp_url:
                print("No RTSP URL found in configuration", 'error')
                sys.stdout.flush()
                time.sleep(5)
                continue
                
            return rtsp_url
        except Exception as e:
            print(f"Error fetching configuration: {e}", 'error')
            sys.stdout.flush()
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
        sys.stdout.flush()
        
        # Create a process with pipe for stdout and stderr
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        return process

    except Exception as e:
        print(f"Error starting FFmpeg: {str(e)}", 'error')
        sys.stdout.flush()
        return None

def monitor_process(process):
    """Monitor the FFmpeg process and return True if it needs to be restarted"""
    if process is None:
        return True
        
    return_code = process.poll()
    if return_code is not None:
        print(f"FFmpeg process exited with code {return_code}", 'error')
        sys.stdout.flush()
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
    sys.stdout.flush()
    process = None

    config_thread = threading.Thread(target=update_config, daemon=True)
    config_thread.start()
    time.sleep(2)

    while True:
        try:
            if monitor_process(process):
                rtsp_url = fetch_rtsp_url()
                if rtsp_url:
                    print(f"Starting stream from: {rtsp_url}")
                    sys.stdout.flush()
                    process = start_ffmpeg(rtsp_url)
                    if process is None:
                        print("Failed to start FFmpeg process", 'error')
                        sys.stdout.flush()
                        time.sleep(10)
                else:
                    print("Failed to fetch RTSP URL. Retrying in 10 seconds...", 'error')
                    sys.stdout.flush()
                    time.sleep(10)
            time.sleep(1)  # Check process status every second
            
        except Exception as e:
            print(f"Unexpected error in main loop: {str(e)}", 'error')
            sys.stdout.flush()
            time.sleep(10) 