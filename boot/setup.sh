#!/bin/bash

cp -r /home/pi/adboard-booking-camera/boot/boot.py /home/pi/boot.py

cat <<EOL | sudo tee /etc/systemd/system/adboardbooking.service
[Unit]
Description=AdboardBooking Service
After=network.target

[Service]
WorkingDirectory=/home/pi
ExecStart=/home/pi/.pyenv/shims/python3 /home/pi/adboard-booking-camera/boot/boot.py
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target

EOL

# Enable and start FFmpeg service
echo "Enabling and starting service..."

sudo systemctl daemon-reload
sudo systemctl enable adbardbooking.service
sudo systemctl start adbardbooking.service
sudo systemctl status adbardbooking.service
