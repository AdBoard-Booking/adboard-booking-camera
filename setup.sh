#!/bin/bash

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Run the installation script
# ./install_dependencies.sh

# Copy scripts to /usr/local/bin
cp start_streaming.sh /usr/local/bin/start_streaming.sh
cp start_ffmpeg.sh /usr/local/bin/start_ffmpeg.sh

# Change permissions
sudo chmod +x /usr/local/bin/start_streaming.sh
sudo chmod +x /usr/local/bin/start_ffmpeg.sh

# Copy service files
cp setup.service /etc/systemd/system/setup_streaming.service
cp ffmpeg.service /etc/systemd/system/ffmpeg-streaming.service

# Reload systemd daemon
systemctl daemon-reload

# Enable and start services
systemctl enable setup_streaming.service
systemctl start setup_streaming.service

systemctl enable ffmpeg-streaming.service
systemctl start ffmpeg-streaming.service

echo "Setup complete. Services are running."
