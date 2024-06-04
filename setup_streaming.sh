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

# Create directory for HLS output
HLS_DIR="/var/www/html/hls"
mkdir -p $HLS_DIR

# Start FFmpeg to transcode RTSP to HLS
RTSP_URL="rtsp://username:password@camera_ip:554/stream"
echo "Starting FFmpeg to transcode RTSP to HLS..."
ffmpeg -i $RTSP_URL -c:v copy -hls_time 2 -hls_list_size 5 -hls_flags delete_segments -f hls $HLS_DIR/stream.m3u8 &

# Configure Nginx to serve HLS
NGINX_CONF="/etc/nginx/sites-available/default"
echo "Configuring Nginx..."
cat > $NGINX_CONF <<EOL
server {
    listen 80;
    server_name localhost;

    location /hls {
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
        root /var/www/html;
        add_header Cache-Control no-cache;
    }
}
EOL

# Restart Nginx to apply changes
echo "Restarting Nginx..."
systemctl restart nginx

# Create an HTML file to play the HLS stream
HTML_FILE="/var/www/html/index.html"
echo "Creating HTML file to play the HLS stream..."
cat > $HTML_FILE <<EOL
<!DOCTYPE html>
<html>
<head>
    <title>RTSP to HLS Stream</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<body>
    <h1>RTSP to HLS Stream</h1>
    <video id="video" controls></video>
    <script>
        if (Hls.isSupported()) {
            var video = document.getElementById('video');
            var hls = new Hls();
            hls.loadSource('/hls/stream.m3u8');
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, function () {
                video.play();
            });
        }
    </script>
</body>
</html>
EOL

# Get the CPU serial number as the device ID
DEVICE_ID=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
echo "Using CPU serial number as device ID: $DEVICE_ID"

# Register the tunnel with Pitunnel using the device ID
echo "Registering Pitunnel..."
pitunnel --port=80 --http --name=$DEVICE_ID --persist &

# Register the device with the server
# REGISTER_URL="http://your-registration-server.com/register"
# PUBLIC_IP=$(curl -s http://whatismyip.akamai.com/)
echo "Registering device with server..."
# curl -X POST -H "Content-Type: application/json" -d '{"deviceId": "'"$DEVICE_ID"'", "ipAddress": "'"$PUBLIC_IP"'"}' $REGISTER_URL

echo "Setup complete. You can now access the stream via the Pitunnel URL provided."
