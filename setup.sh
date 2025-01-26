#!/bin/bash

echo "Starting setup process..."

# Check if the boot/setup.sh script exists and is executable
if [ -f "boot/setup.sh" ] && [ -x "boot/setup.sh" ]; then
    echo "Running boot/setup.sh..."
    sh boot/setup.sh
else
    echo "Error: boot/setup.sh not found or not executable."
    exit 1
fi

# Check if the traffic/setup.sh script exists and is executable
if [ -f "traffic/setup.sh" ] && [ -x "traffic/setup.sh" ]; then
    echo "Running traffic/setup.sh..."
    sh traffic/setup.sh
else
    echo "Error: traffic/setup.sh not found or not executable."
    exit 1
fi

cpu_serial=$(cat /proc/cpuinfo | grep "Serial" | awk '{print $3}')

curl -X POST -H "Content-Type: application/json" -d "{\"deviceId\": \"$cpu_serial\"}" https://railway.adboardbooking.com/api/camera/v1/streaming-device

echo "Setup process completed successfully!"
