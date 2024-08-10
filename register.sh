#!/bin/bash

FORCE=false
while getopts "f" opt; do
  case $opt in
    f)
      FORCE=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# Check for /usr/local/bin/rtsp_url.txt, if empty or doesn't exist, call the scan with -f
RTSP_URL_FILE="/usr/local/bin/rtsp_url.txt"
if [ ! -s "$RTSP_URL_FILE" ] || [ "$FORCE" = true ]; then
    echo "Running scan with force option..."
    sudo sh scan_rtsp.sh -f
else
    sudo sh scan_rtsp.sh
fi

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

# Only run pitunnel if -f is passed
if [ "$FORCE" = true ]; then
    echo "Registering Pitunnel..."
    pitunnel --remove 1
    pitunnel --port=80 --http --name=$DEVICE_ID --persist
fi


# Register the device with the server
REGISTER_URL="https://railway.adboardbooking.com/api/camera/register"
PUBLIC_IP=$(curl -s http://whatismyip.akamai.com/)
PRIVATE_IP=$(get_private_ip)

echo "Registering device with server..."

CAMERA_URL="https://$DEVICE_ID-ankurkus.in1.pitunnel.com/?hash=$HASH"
echo "Stream URL: $CAMERA_URL"

HOSTNAME=$(hostname)

# Create the POST body and save it to a file
POST_BODY='{
  "deviceId": "'"$DEVICE_ID"'",
  "rtspUrl": "'"$RTSP_URL"'",
  "hostName": "'"$HOSTNAME"'",
  "publicIp": "'"$PUBLIC_IP"'",
  "privateIp": "'"$PRIVATE_IP"'",
  "cameraUrl": "'"$CAMERA_URL"'"
}'

echo "[$POST_BODY]" | tee /usr/local/bin/registered_cameras.json
echo "[$POST_BODY]" | tee ./registered_cameras.json

curl -X POST -H "Content-Type: application/json" -d "$POST_BODY" $REGISTER_URL