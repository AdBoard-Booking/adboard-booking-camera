#!/bin/bash

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Copy scripts to /usr/local/bin
# sudo cp ./setup_streaming.sh /usr/local/bin/setup_streaming.sh
sudo cp ./start_ffmpeg.sh /usr/local/bin/start_ffmpeg.sh

# Change permissions
# sudo chmod +x ./setup_streaming.sh
# sudo sh ./setup_streaming.sh
sudo chmod +x /usr/local/bin/start_ffmpeg.sh

# Copy service files
# sudo cp setup.service /etc/systemd/system/setup_streaming.service
sudo cp ffmpeg.service /etc/systemd/system/ffmpeg-streaming.service

# Reload systemd daemon
systemctl daemon-reload

# Enable and start services
# systemctl enable setup_streaming.service
# systemctl start setup_streaming.service

systemctl enable ffmpeg-streaming.service
systemctl start ffmpeg-streaming.service

echo "Setup complete. Services are running."
