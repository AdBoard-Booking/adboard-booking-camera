#!/usr/bin/env python3

import requests
import subprocess
import time
import os
import sys

# Add the boot/service directory to Python path to import utils
# sys.path.append('/opt/adboard/boot/service')

current_dir = os.path.dirname(os.path.abspath(__file__))
adjacent_folder = os.path.join(current_dir, '..', 'boot', 'services', 'utils')  # Assuming 'utils' is the adjacent folder
sys.path.append(adjacent_folder)
from utils import load_config_for_device
    
def fetch_rtsp_url():
    try:
        config = load_config_for_device()
        if not config:
            print("Failed to load configuration")
            return None
            
        rtsp_url = config.get('services', {}).get('billboardMonitoring', {}).get('rtspStreamUrl')
        if not rtsp_url:
            print("No RTSP URL found in configuration")
            return None
            
        return rtsp_url
    except Exception as e:
        print(f"Error fetching configuration: {e}")
    return None

def start_ffmpeg(rtsp_url):
    command = [
        "ffmpeg", "-i", rtsp_url, "-c:v", "copy", "-hls_time", "1",
        "-hls_list_size", "3", "-hls_flags", "delete_segments+append_list",
        "-start_number", "1", "-f", "hls", "/var/www/stream/live.m3u8"
    ]
    return subprocess.Popen(command, stdout=open("/var/log/ffmpeg_stream.log", "a"), stderr=open("/var/log/ffmpeg_stream.err", "a"))

if __name__ == "__main__":
    while True:
        rtsp_url = fetch_rtsp_url()
        if rtsp_url:
            print(f"Starting stream from: {rtsp_url}")
            process = start_ffmpeg(rtsp_url)
            process.wait()
        else:
            print("Failed to fetch RTSP URL. Retrying in 10 seconds...")
        time.sleep(10) 