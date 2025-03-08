#!/bin/bash


rm -rf /var/log/camera-streaming.log

# Stop the streaming service
echo "Stopping camera-streaming"
sudo systemctl restart camera-streaming

echo "Showing logs"

tail -f /var/log/camera-streaming.log

# sudo systemctl status camera-streaming

# journalctl -u camera-streaming -f
