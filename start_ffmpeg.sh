#!/bin/bash

# Function to check if a command exists
command_exists () {
    type "$1" &> /dev/null ;
}

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Function to generate a hash from the RTSP URL
generate_hash() {
    echo -n "$1" | md5sum | awk '{print $1}'
}

# Function to get the private IP address
get_private_ip() {
    hostname -I | awk '{print $1}'
}

cd /home/pi/adboard-booking-camera
git fetch
git reset --hard origin/main

# File to store the RTSP URL
RTSP_URL_FILE="/usr/local/bin/rtsp_url.txt"

# Check if RTSP URL is provided as a command-line argument
if [ -z "$1" ]; then
  if [ ! -f "$RTSP_URL_FILE" ]; then
    echo "Usage: $0 <RTSP_URL>"
    exit 1
  else
    RTSP_URL=$(cat $RTSP_URL_FILE)
    echo "Using RTSP URL from file: $RTSP_URL"
  fi
else
  RTSP_URL=$1
  echo "Saving RTSP URL to file: $RTSP_URL"
  echo $RTSP_URL > $RTSP_URL_FILE
fi

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

# Get the CPU serial number as the device ID
DEVICE_ID=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
echo "Using CPU serial number as device ID: $DEVICE_ID"

# Register the device with the server
REGISTER_URL="https://railway.adboardbooking.com/api/camera/register"
PUBLIC_IP=$(curl -s http://whatismyip.akamai.com/)
PRIVATE_IP=$(get_private_ip)

echo "Registering device with server..."

CAMERA_URL="https://$DEVICE_ID-ankurkus.in1.pitunnel.com/?hash=$HASH"
echo "Stream URL: $CAMERA_URL"

HOSTNAME=$(hostname)

echo '{
  "deviceId": "'"$DEVICE_ID"'",
  "rtspUrl": "'"$RTSP_URL"'",
  "publicIp": "'"$PUBLIC_IP"'",
  "privateIp": "'"$PRIVATE_IP"'",
  "hostName": "'"$HOSTNAME"'",
  "cameraUrl": "'"$CAMERA_URL"'"
}'

curl -X POST -H "Content-Type: application/json" -d '{
  "deviceId": "'"$DEVICE_ID"'",
  "rtspUrl": "'"$RTSP_URL"'",
  "hostName": "'"$HOSTNAME"'",
  "publicIp": "'"$PUBLIC_IP"'",
  "privateIp": "'"$PRIVATE_IP"'",
  "cameraUrl": "'"$CAMERA_URL"'"
}' $REGISTER_URL

echo "Setup complete. You can now access the stream via the Pitunnel URL provided."

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
KILL_INTERVAL="10m"         # Interval to kill ffmpeg process (e.g., 10m for 10 minutes)

echo "$(date) - Starting ffmpeg..." | tee -a $LOG_FILE
    
# Start ffmpeg process in the background
ffmpeg -i $RTSP_URL -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -hls_segment_filename "$HLS_DIR/segment_%03d.ts" -f hls $HLS_DIR/stream.m3u8 >> $LOG_FILE 2>&1 &
FFMPG_PID=$!

SLEEP_TIME="1m"

# Get the last modification time of the file
LAST_MODIFICATION=$(stat -c %s "$LOG_FILE")

while true; do
    echo "$(date) - Slepping for $SLEEP_TIME"
    # Wait for specified time
    sleep $SLEEP_TIME

    # Check current modification time
    CURRENT_MODIFICATION=$(stat -c %s "$LOG_FILE")

    # Compare the last modification time with the current modification time
    if [[ $LAST_MODIFICATION == $CURRENT_MODIFICATION ]]; then
        echo "$(date) - Log file has not been updated. Exiting." 
        # Command to kill the process or perform any action needed
        exit 1
    else
        echo "$(date) - Log file has been updated. Current: $CURRENT_MODIFICATION, Last: $LAST_MODIFICATION"
        # Update LAST_MODIFICATION to the new modification time
        LAST_MODIFICATION=$CURRENT_MODIFICATION
    fi
done
 