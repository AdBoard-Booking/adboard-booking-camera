#!/bin/bash

sudo sh ./scan_rtsp.sh
sudo sh ./start_ffmpeg.sh &
python ./yolo_supervision_lite.py