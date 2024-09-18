#!/bin/bash

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Copy scripts to /usr/local/bin
sudo mkdir /usr/local/bin/adboardbookingai
sudo cp ./run_on_boot.sh /usr/local/bin/adboardbookingai/run_on_boot.sh
sudo cp ./yolo_across_frame_cmd.py /usr/local/bin/adboardbookingai/yolo_across_frame_cmd.py
sudo cp ./process_billboard_data.py /usr/local/bin/adboardbookingai/process_billboard_data.py

# Change permissions
sudo chmod +x /usr/local/bin/adboardbookingai/*.sh

sudo setfacl -m u:pi:rwx /usr/local/bin/adboardbookingai

# Copy service files
sudo cp adboardbookingai.service /etc/systemd/system/adboardbookingai.service

# Reload systemd daemon
systemctl daemon-reload

# Enable and start services
systemctl enable adboardbookingai.service
systemctl start adboardbookingai.service

echo "Setup complete. Services are running."
