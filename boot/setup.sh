#!/bin/bash

curl -L -o "/home/pi/boot.py" "https://raw.githubusercontent.com/AdBoard-Booking/adboard-booking-camera/refs/heads/main/boot/boot.py"

cat <<EOL | sudo tee /etc/systemd/system/adbardbooking.service
[Unit]
Description=My Python Script
After=network.target

[Service]
WorkingDirectory=/home/pi
ExecStart=/home/pi/.pyenv/shims/python3 /home/pi/boot.py
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
