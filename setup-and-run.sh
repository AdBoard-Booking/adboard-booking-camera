#!/bin/bash

# Define the repository URL and the local directory
REPO_URL="https://github.com/AdBoard-Booking/adboard-booking-camera.git"
LOCAL_DIR="adboard-booking-camera"

# Clone the repository
if [ -d "$LOCAL_DIR" ]; then
  echo "Directory $LOCAL_DIR already exists. Pulling the latest changes..."
  cd $LOCAL_DIR
  git pull
else
  echo "Cloning the repository..."
  git clone $REPO_URL $LOCAL_DIR
  cd $LOCAL_DIR
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Run the main file specified in package.json
echo "Running the main file..."
npm start