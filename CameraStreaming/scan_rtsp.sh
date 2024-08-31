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

# Check if file exists and not forcing
if [ -f /usr/local/bin/rtsp_url.txt ] && [ "$FORCE" = false ]; then
  echo "RTSP URL file exists. Content:"
  cat /usr/local/bin/rtsp_url.txt
  exit 0
fi

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
RTSP_URL=""
for IP in $SCAN_RESULTS; do
    TEST_URL="rtsp://adboardbooking:adboardbooking@$IP/stream2"
    if ffmpeg -i $TEST_URL -t 1 -f null - 2>&1 | grep -q "Input #0"; then
        RTSP_URL=$TEST_URL
        CAMERA_IP=$IP
        break
    fi
done

# Ensure RTSP URL is found
if [ -z "$RTSP_URL" ]; then
  echo "No suitable RTSP URL found. Exiting."
  exit 1
fi

# Save the RTSP URL to a file
echo $RTSP_URL > /usr/local/bin/rtsp_url.txt
echo "RTSP URL saved: $RTSP_URL"