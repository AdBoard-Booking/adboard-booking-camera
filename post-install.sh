#!/bin/bash

git pull origin main
sudo cp setup_streaming.sh /usr/local/bin/setup_streaming.sh
sudo cp scan_rtsp.sh /usr/local/bin/scan_rtsp.sh
sudo chmod +x /usr/local/bin/setup_streaming.sh
sudo chmod +x /usr/local/bin/scan_rtsp.sh