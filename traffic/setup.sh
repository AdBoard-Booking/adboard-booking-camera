#!/bin/bash

cat <<EOL | sudo tee /etc/systemd/system/traffic.service
[Unit]
Description=My Python Script
After=network.target

[Service]
WorkingDirectory=/home/pi
ExecStart=/home/pi/.pyenv/shims/python3 /home/pi/streaming.py
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target

EOL

# Enable and start FFmpeg service
echo "Enabling and starting service..."

sudo systemctl daemon-reload
sudo systemctl enable traffic.service
sudo systemctl start traffic.service
sudo systemctl status traffic.service
