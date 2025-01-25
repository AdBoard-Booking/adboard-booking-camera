#!/bin/bash

echo "Starting installation process..."

# Example: Update packages
echo "Updating packages..."
sudo apt update && sudo apt upgrade -y

# Example: Install dependencies
echo "Installing dependencies..."
sudo apt install -y curl git python3-pip


# Example: Clone a GitHub repository (replace with your repo)
echo "Cloning repository..."
rm -rf ~/adboard-booking-camera
git clone https://github.com/AdBoard-Booking/adboard-booking-camera.git ~/adboard-booking-camera

# Example: Execute a setup script in the repository
echo "Running setup script..."
bash ~/repository/setup.sh

echo "Installation completed successfully!"