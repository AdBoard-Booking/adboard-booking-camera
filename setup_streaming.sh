#!/bin/bash

# Function to check if a command exists
command_exists () {
    type "$1" &> /dev/null ;
}

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# File to store the RTSP URL
RTSP_URL_FILE="/usr/local/bin/rtsp_url.txt"

# Check if RTSP URL is provided as a command-line argument
if [ -z "$1" ]; then
  if [ ! -f "$RTSP_URL_FILE" ]; then
    echo "Usage: $0 <RTSP_URL>"
    exit 1
  else
    RTSP_URL=$(cat $RTSP_URL_FILE)
    echo "Using RTSP URL from file: $RTSP_URL"
  fi
else
  RTSP_URL=$1
  echo "Saving RTSP URL to file: $RTSP_URL"
  echo $RTSP_URL > $RTSP_URL_FILE
fi

# Create directory for HLS output if it doesn't exist
HLS_DIR="/var/www/html/hls"
if [ ! -d "$HLS_DIR" ]; then
  mkdir -p $HLS_DIR
fi

# Ensure the directory has correct permissions
chown -R www-data:www-data $HLS_DIR
chmod -R 755 $HLS_DIR

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

    location /hls {
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
        alias /var/www/html/hls;
        add_header Cache-Control no-cache;
    }
}
EOL

# Restart Nginx to apply changes
echo "Restarting Nginx..."
systemctl restart nginx

# Copy the HTML file to serve the HLS stream
sudo cp ./stream.html /var/www/html/index.html

# Get the CPU serial number as the device ID
DEVICE_ID=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
echo "Using CPU serial number as device ID: $DEVICE_ID"

# Register the tunnel with Pitunnel using the device ID
echo "Registering Pitunnel..."
pitunnel --port=80 --http --name=$DEVICE_ID --persist

# Register the device with the server
REGISTER_URL="http://your-registration-server.com/register"
PUBLIC_IP=$(curl -s http://whatismyip.akamai.com/)
echo "Registering device with server..."
curl -X POST -H "Content-Type: application/json" -d '{"deviceId": "'"$DEVICE_ID"'", "ipAddress": "'"$PUBLIC_IP"'"}' $REGISTER_URL

echo "Setup complete. You can now access the stream via the Pitunnel URL provided."
