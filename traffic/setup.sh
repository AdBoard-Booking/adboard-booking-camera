#!/bin/bash

pip3 install ultralytics opencv-python requests   

cp -r /home/pi/adboard-booking-camera/boot/streaming.py /home/pi/streaming.py

cat <<EOL | sudo tee /etc/systemd/system/traffic.service
[Unit]
Description=Traffic Service
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
