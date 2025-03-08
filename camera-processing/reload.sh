#!/bin/bash


# Stop the streaming service
echo "Stopping camera-processing.service"
sudo systemctl stop camera-processing.service
echo "Starting camera-processing.service"
sudo systemctl start camera-processing.service
echo "Showing logs"
tail -f /var/log/camera-processing.log