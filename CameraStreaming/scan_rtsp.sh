#!/bin/bash

# Function to check if a command exists
command_exists () {
    type "$1" &> /dev/null ;
}

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Check for force flag
FORCE=false
while getopts "f" opt; do
  case $opt in
    f) FORCE=true ;;
    *) echo "Usage: $0 [-f]" >&2
       exit 1 ;;
  esac
done

# Function to generate a hash from the RTSP URL
generate_hash() {
    echo -n "$1" | md5sum | awk '{print $1}'
}

# Initialize JSON_DATA variable
JSON_DATA=""
CAMERAS_FILE="/usr/local/bin/adboardbooking/registered_cameras.json"

# Check if file exists and not forcing
if [ -f $CAMERAS_FILE ] && [ "$FORCE" = false ]; then
  JSON_DATA=$(cat $CAMERAS_FILE)
  echo "Registered cameras file exists. Loading content... "
  echo $JSON_DATA
else
  # Install Nmap if not installed
  if command_exists nmap; then
    echo "Nmap is already installed."
  else
    echo "Installing Nmap..."
    sudo apt-get install -y nmap
  fi

  # Discover RTSP streams on the local network
  echo "Scanning for cameras on the local network..."
  NETWORK_PREFIX=$(ip -o -f inet addr show | awk '/scope global/ {print $4}' | cut -d'/' -f1 | awk 'NR==1{print}')
  SCAN_RESULTS=$(nmap -p 554 --open $NETWORK_PREFIX/24 -oG - | awk '/554\/open/ {print $2}')

  # Check for RTSP streams with the specified format
  RTSP_URL="rtps://192.168.29.204/stream2"
  # for IP in $SCAN_RESULTS; do
  #     TEST_URL="rtsp://adboardbooking:adboardbooking@$IP/stream2"
  #     if ffmpeg -i $TEST_URL -t 1 -f null - 2>&1 | grep -q "Input #0"; then
  #         RTSP_URL=$TEST_URL
  #         CAMERA_IP=$IP
  #         break
  #     fi
  # done

  # Ensure RTSP URL is found
  if [ -z "$RTSP_URL" ]; then
    echo "No suitable RTSP URL found. Exiting."
    exit 1
  fi

  # Generate a device ID from CPU info
  DEVICE_ID=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
  
  # Get the hostname
  HOST_NAME=$(hostname)

  # Get the public IP
  PUBLIC_IP=$(curl -s ifconfig.me)

  # Get the private IP
  PRIVATE_IP=$(hostname -I | awk '{print $1}')
  HASH=$(generate_hash "$RTSP_URL")
  USERNAME=${whoami}
  CAMERA_URL="https://$DEVICE_ID-ankurkus.in1.pitunnel.com/?hash=$HASH"

  # Create the JSON data
  JSON_DATA=$(cat <<EOF
[{
  "deviceId": "$DEVICE_ID",
  "rtspUrl": "$RTSP_URL",
  "hostName": "$HOST_NAME",
  "userName": "$USERNAME",
  "cameraIp": "$CAMERA_IP",
  "publicIp": "$PUBLIC_IP",
  "privateIp": "$PRIVATE_IP",
  "cameraUrl": "$CAMERA_URL"
}]
EOF
)

  # Save the JSON data to a file
  echo "$JSON_DATA" > $CAMERAS_FILE
  echo "Camera data saved to $CAMERAS_FILE"
fi

# Call the API with the JSON data
REGISTER_URL="https://railway.adboardbooking.com/api/camera/register"
curl --location $REGISTER_URL \
  --header 'Content-Type: application/json' \
  --data-raw "$JSON_DATA" \
  2>&1 | tee curl_output.log