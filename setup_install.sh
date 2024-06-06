#!/bin/bash

# Function to check if a command exists
command_exists () {
    type "$1" &> /dev/null ;
}

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Update package list
echo "Updating package list..."
apt-get update

# Install FFmpeg if not installed
if command_exists ffmpeg; then
  echo "FFmpeg is already installed."
else
  echo "Installing FFmpeg..."
  apt-get install -y ffmpeg
fi

# Install Nginx if not installed
if command_exists nginx; then
  echo "Nginx is already installed."
else
  echo "Installing Nginx..."
  apt-get install -y nginx
fi

# Install Pitunnel if not installed
if command_exists pitunnel; then
  echo "Pitunnel is already installed."
else
  echo "Installing Pitunnel..."
  sudo npm install -g pitunnel
fi