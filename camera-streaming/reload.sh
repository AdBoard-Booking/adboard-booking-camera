#!/bin/bash


# Stop the streaming service
echo "Stopping ffmpeg-stream"
sudo systemctl stop ffmpeg-stream
echo "Starting ffmpeg-stream"
sudo systemctl start ffmpeg-stream
echo "Showing logs"
tail -f /var/log/ffmpeg_stream.log

# sudo systemctl status ffmpeg-stream