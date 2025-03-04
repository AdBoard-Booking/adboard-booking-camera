#!/usr/bin/env python3

import requests
import subprocess
import time
import os
import sys
from datetime import datetime

# Add the boot/service directory to Python path to import utils
# sys.path.append('/opt/adboard/boot/service')

current_dir = os.path.dirname(os.path.abspath(__file__))
adjacent_folder = os.path.join(current_dir, '..', 'boot', 'services', 'utils')  # Assuming 'utils' is the adjacent folder
sys.path.append(adjacent_folder)

from utils import load_config_for_device
from mqtt import publish_log
    
def fetch_rtsp_url():
    try:
        config = load_config_for_device()
        publish_log(f"Config: {config}",'info')
        if not config:
            publish_log("Failed to load configuration",'error')
            return None
            
        rtsp_url = config.get('services', {}).get('billboardMonitoring', {}).get('rtspStreamUrl')
        if not rtsp_url:
            publish_log("No RTSP URL found in configuration",'error')
            return None
            
        return rtsp_url
    except Exception as e:
        publish_log(f"Error fetching configuration: {e}",'error')
    return None

def start_ffmpeg(rtsp_url):
    # Create a process with pipe for stdout and stderr
    command = [
        "ffmpeg", "-i", rtsp_url, "-c:v", "copy", "-hls_time", "1",
        "-hls_list_size", "3", "-hls_flags", "delete_segments+append_list",
        "-start_number", "1", "-f", "hls", "/var/www/stream/live.m3u8"
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    # Create separate threads to handle stdout and stderr
    def log_output(pipe):
        for line in pipe:
            print(line.strip())
            
    from threading import Thread
    Thread(target=log_output, args=(process.stdout,)).start()

    return process

if __name__ == "__main__":
    while True:
        rtsp_url = fetch_rtsp_url()
        if rtsp_url:
            publish_log(f"Starting stream from: {rtsp_url}",'info')
            process = start_ffmpeg(rtsp_url)
            process.wait()
        else:
            publish_log("Failed to fetch RTSP URL. Retrying in 10 seconds...", 'error')
        time.sleep(10) 