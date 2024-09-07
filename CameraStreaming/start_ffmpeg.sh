#!/bin/bash

# Function to check if a command exists
command_exists () {
    type "$1" &> /dev/null ;
}

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Function to generate a hash from the RTSP URL
generate_hash() {
    echo -n "$1" | md5sum | awk '{print $1}'
}

# Function to get the private IP address
get_private_ip() {
    hostname -I | awk '{print $1}'
}

# File to store the camera data
CAMERA_DATA_FILE="/usr/local/bin/adboardbooking/registered_cameras.json"

# Check if the camera data file exists
if [ ! -f "$CAMERA_DATA_FILE" ]; then
    echo "Error: $CAMERA_DATA_FILE not found."
    exit 1
fi

# Read RTSP URL from the JSON file
RTSP_URL=$(jq -r '.[0].rtspUrl' "$CAMERA_DATA_FILE")

if [ -z "$RTSP_URL" ] || [ "$RTSP_URL" == "null" ]; then
    echo "Error: Failed to read RTSP URL from $CAMERA_DATA_FILE"
    exit 1
fi

echo "Using RTSP URL: $RTSP_URL"

# Generate a hash from the RTSP URL
HASH=$(generate_hash "$RTSP_URL")

# Create directory for HLS output based on the hash
BASE_HLS_DIR="/var/www/html/hls"
HLS_DIR="$BASE_HLS_DIR/$HASH"
if [ ! -d "$HLS_DIR" ]; then
  mkdir -p $HLS_DIR
fi

# Ensure the directory has correct permissions
chown -R root:root $HLS_DIR
chmod -R 755 $HLS_DIR

# Log file for FFmpeg
LOG_FILE="/var/log/ffmpeg_stream.log"

# Ensure the log file exists and has the correct permissions
touch $LOG_FILE
chmod 644 $LOG_FILE

check_rtsp_stream() {
    ffprobe -v error -i "$RTSP_URL" -show_streams > /dev/null 2>&1
    return $?
}

# Wait for the RTSP stream to be available
until check_rtsp_stream; do
    echo "$(date) - Waiting for RTSP stream..." | tee -a $LOG_FILE
    sleep 5
done

# Start FFmpeg to transcode RTSP to HLS
echo "Starting FFmpeg to transcode RTSP to HLS..."
SLEEP_TIME="1m"

echo "$(date) - Starting ffmpeg..." | tee -a $LOG_FILE
    
# Start ffmpeg process in the background
ffmpeg -i $RTSP_URL -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -hls_segment_filename "$HLS_DIR/segment_%03d.ts" -f hls $HLS_DIR/stream.m3u8 >> $LOG_FILE 2>&1 &
FFMPEG_PID=$!

# Get the last modification time of the file
LAST_MODIFICATION=$(stat -c %s "$LOG_FILE")

while true; do
    echo "$(date) - Sleeping for $SLEEP_TIME"
    # Wait for specified time
    sleep $SLEEP_TIME

    # Check current modification time
    CURRENT_MODIFICATION=$(stat -c %s "$LOG_FILE")

    # Compare the last modification time with the current modification time
    if [[ $LAST_MODIFICATION == $CURRENT_MODIFICATION ]]; then
        echo "$(date) - Log file has not been updated. Exiting." 
        # Kill the ffmpeg process
        kill $FFMPEG_PID
        exit 1
    else
        echo "$(date) - Log file has been updated. Current: $CURRENT_MODIFICATION, Last: $LAST_MODIFICATION"
        # Update LAST_MODIFICATION to the new modification time
        LAST_MODIFICATION=$CURRENT_MODIFICATION
    fi
done