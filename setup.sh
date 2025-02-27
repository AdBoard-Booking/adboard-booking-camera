#!/bin/bash

echo "Starting setup process..."

sudo tailscale up --operator=pi

# Check if the boot/setup.sh script exists and is executable
if [ -f "boot/setup.sh" ] && [ -x "boot/setup.sh" ]; then
    echo "Running boot/setup.sh..."
    sh boot/setup.sh
    sh CameraStreaming/setup.sh
else
    echo "Error: boot/setup.sh not found or not executable."
    exit 1
fi

cpu_serial=$(cat /proc/cpuinfo | grep "Serial" | awk '{print $3}')

curl -X POST -H "Content-Type: application/json" -d "{\"deviceId\": \"$cpu_serial\"}" https://railway.adboardbooking.com/api/camera/v1/streaming-device

echo "Setup process completed successfully!"
