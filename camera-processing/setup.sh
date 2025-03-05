#!/bin/bash

# Ensure the script runs with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./setup.sh)"
    exit 1
fi

echo "Setting up the camera stream..."

# Copy Python script to destination
echo "Installing Python script..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install Python dependencies
# apt install -y python3-pip
# pip3 install requests

# Create systemd service
cat <<EOL | sudo tee /etc/systemd/system/camera-processing.service
[Unit]
Description=Camera Processing
After=network.target

[Service]
ExecStartPre=sh $SCRIPT_DIR/pre-start.sh
ExecStart=/home/pi/.pyenv/shims/python $SCRIPT_DIR/streaming_fast_new_publish.py
Restart=always
RestartSec=10
StandardOutput=file:/var/log/camera-processing.log
StandardError=file:/var/log/camera-processing.err
User=root

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
systemctl daemon-reload
systemctl enable camera-processing
systemctl start camera-processing

echo "Camera processing service created and started."

echo "Setup completed successfully!"


# debug process
# sudo systemctl status camera-processing
# sudo journalctl -xe -u camera-processing
# tail -f /var/log/camera-processing.log
# tail -f /var/log/camera-processing.err
