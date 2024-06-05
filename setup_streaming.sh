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

# Read the RTSP URL from the file
RTSP_URL_FILE="/usr/local/bin/rtsp_url.txt"
if [ ! -f "$RTSP_URL_FILE" ]; then
  echo "RTSP URL file not found. Please run scan_rtsp.sh first."
  exit 1
fi

RTSP_URL=$(cat $RTSP_URL_FILE)

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

# Extract the last octet from the camera IP address
CAMERA_IP=$(echo $RTSP_URL | grep -oP '(?<=@)[^/]+')
LAST_OCTET=$(echo $CAMERA_IP | awk -F. '{print $4}')
STREAM_NAME="stream_$LAST_OCTET"
TUNNEL_NAME="tunnel_$LAST_OCTET"

echo "Using RTSP URL: $RTSP_URL"
echo "Stream name: $STREAM_NAME"
echo "Tunnel name: $TUNNEL_NAME"

# Create directory for HLS output if it doesn't exist
HLS_DIR="/var/www/html/$STREAM_NAME"
if [ ! -d "$HLS_DIR" ]; then
  mkdir -p $HLS_DIR
fi

# Ensure the directory has correct permissions
chown -R www-data:www-data $HLS_DIR
chmod -R 755 $HLS_DIR

# Stop any existing FFmpeg processes to avoid conflicts
pkill -f ffmpeg

# Start FFmpeg to transcode RTSP to HLS
echo "Starting FFmpeg to transcode RTSP to HLS..."
ffmpeg -i $RTSP_URL -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -hls_segment_filename "$HLS_DIR/segment_%03d.ts" -f hls $HLS_DIR/stream.m3u8 &

# Configure Nginx to serve HLS
NGINX_CONF="/etc/nginx/sites-available/default"
echo "Configuring Nginx..."
cat > $NGINX_CONF <<EOL
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html index.htm;

    server_name _;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location /$STREAM_NAME {
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
        alias /var/www/html/$STREAM_NAME;
        add_header Cache-Control no-cache;
    }
}
EOL

# Restart Nginx to apply changes
echo "Restarting Nginx..."
systemctl restart nginx

# Copy the HTML file to serve the HLS stream
HTML_FILE_SOURCE="/usr/local/bin/stream.html"
HTML_FILE_DEST="/var/www/html/index.html"
if [ -f "$HTML_FILE_SOURCE" ]; then
  echo "Copying HTML file to play the HLS stream..."
  cp $HTML_FILE_SOURCE $HTML_FILE_DEST
fi

# Get the CPU serial number as the device ID
DEVICE_ID=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
echo "Using CPU serial number as device ID: $DEVICE_ID"

# Register the tunnel with Pitunnel using the device ID
echo "Registering Pitunnel..."
pitunnel --port=80 --http --name=$TUNNEL_NAME --persist

# Register the device with the server
REGISTER_URL="http://your-registration-server.com/register"
PUBLIC_IP=$(curl -s http://whatismyip.akamai.com/)
echo "Registering device with server..."
# curl -X POST -H "Content-Type: application/json" -d '{"deviceId": "'"$DEVICE_ID"'", "ipAddress": "'"$PUBLIC_IP"'", "streamName": "'"$STREAM_NAME"'"}' $REGISTER_URL

echo "Setup complete. You can now access the stream via the Pitunnel URL provided."
