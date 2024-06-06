#!/bin/bash

# File to store the RTSP URL
RTSP_URL_FILE="/usr/local/bin/rtsp_url.txt"
LOG_FILE="/var/log/ffmpeg_stream.log"
HLS_DIR="/var/www/html/hls"

# Check if RTSP URL file exists
if [ ! -f "$RTSP_URL_FILE" ]; then
  echo "RTSP URL file not found. Please run setup_streaming.sh first."
  exit 1
fi

RTSP_URL=$(cat $RTSP_URL_FILE)

# Ensure the HLS directory exists
if [ ! -d "$HLS_DIR" ]; then
  mkdir -p $HLS_DIR
fi

# Ensure the directory has correct permissions
chown -R www-data:www-data $HLS_DIR
chmod -R 755 $HLS_DIR

# Ensure the log file exists and has the correct permissions
touch $LOG_FILE
chown www-data:www-data $LOG_FILE
chmod 644 $LOG_FILE

# Start FFmpeg to transcode RTSP to HLS
echo "Starting FFmpeg to transcode RTSP to HLS..."
sudo -u www-data ffmpeg -i $RTSP_URL -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -hls_segment_filename "$HLS_DIR/segment_%03d.ts" -f hls $HLS_DIR/stream.m3u8 > $LOG_FILE 2>&1
