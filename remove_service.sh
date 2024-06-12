#!/bin/bash

# Define the service name
SERVICE_NAME="ffmpeg.service "

echo "Stopping the service..."
sudo systemctl stop $SERVICE_NAME

echo "Disabling the service..."
sudo systemctl disable $SERVICE_NAME

echo "Removing the service file..."
sudo rm /etc/systemd/system/$SERVICE_NAME.service

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Optional: Remove the symlink if it exists
if [ -L /lib/systemd/system/$SERVICE_NAME.service ]; then
    echo "Removing the symlink..."
    sudo rm /lib/systemd/system/$SERVICE_NAME.service
fi

echo "Verifying the service has been removed..."
sudo systemctl list-unit-files --type=service | grep $SERVICE_NAME

echo "Service removal complete."