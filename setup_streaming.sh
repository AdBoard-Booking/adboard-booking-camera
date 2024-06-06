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

# Create directory for HLS output if it doesn't exist
HLS_DIR="/var/www/html/hls"
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

# Create an HTML file to play the HLS stream if it doesn't exist
HTML_FILE="/var/www/html/index.html"
if [ ! -f "$HTML_FILE" ]; then
  echo "Creating HTML file to play the HLS stream..."
  cat > $HTML_FILE <<EOL
<!DOCTYPE html>
<html>
<head>
    <title>RTSP to HLS Stream</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<style>
  video {
        width: 100%;
        object-fit: fill; // use "cover" to avoid distortion
        position: absolute;
    }
</style>
<body>
    <video id="video" controls></video>
    <script>
        if (Hls.isSupported()) {
            var video = document.getElementById('video');
            var hls = new Hls();
            hls.loadSource('/hls/stream.m3u8');
            hls.attachMedia(video);
            hls.on(Hls.Events.MEDIA_ATTACHED, function () {
              video.muted = true;
              video.play();
            });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = '/hls/stream.m3u8';
            video.addEventListener('loadedmetadata', function() {
                video.muted = true;
                video.play();
            });
        }
    </script>
</body>
</html>
EOL
fi

# Get the CPU serial number as the device ID
DEVICE_ID=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
echo "Using CPU serial number as device ID: $DEVICE_ID"

# Stop any existing Pitunnel processes to avoid conflicts
# pkill -f pitunnel

# Register the tunnel with Pitunnel using the device ID
echo "Registering Pitunnel..."
pitunnel --port=80 --http --name=$DEVICE_ID --persist

# Register the device with the server
# REGISTER_URL="http://your-registration-server.com/register"
PUBLIC_IP=$(curl -s http://whatismyip.akamai.com/)
echo "Registering device with server..."
# curl -X POST -H "Content-Type: application/json" -d '{"deviceId": "'"$DEVICE_ID"'", "ipAddress": "'"$PUBLIC_IP"'"}' $REGISTER_URL

echo "Setup complete. You can now access the stream via the Pitunnel URL provided."
