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

# Function to generate a hash from the RTSP URL
generate_hash() {
    echo -n "$1" | md5sum | awk '{print $1}'
}

# Function to get the private IP address
get_private_ip() {
    hostname -I | awk '{print $1}'
}

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

# Generate a hash from the RTSP URL
HASH=$(generate_hash "$RTSP_URL")

# Create directory for HLS output based on the hash
BASE_HLS_DIR="/var/www/html/hls"
HLS_DIR="$BASE_HLS_DIR/$HASH"
if [ ! -d "$HLS_DIR" ]; then
  mkdir -p $HLS_DIR
fi

# Ensure the directory has correct permissions
chown -R root:root $HLS_DIR
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

    # Add this block to set the CSP header
    add_header Content-Security-Policy "frame-ancestors 'self' http://localhost https://*.adboardbooking.com";

    location / {
        try_files \$uri \$uri/ =404;
    }

    location /wifi-setup {
        alias /var/www/html/wifi-setup;
        index index.php;
    }

    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php7.3-fpm.sock;
    }

    location ~ /\.ht {
        deny all;
    }

    location /hls {
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
        alias /var/www/html/hls;
        add_header Cache-Control no-cache;
    }
    error_page 404 /404.html;
    error_page 500 502 503 504 /5xx.html;
    location = /404.html {
        internal;
        root /var/www/html;
        add_header Content-Type text/html;
        return 404 "";
    }
    location = /5xx.html {
        internal;
        root /var/www/html;
        add_header Content-Type text/html;
        return 500 "";
    }
}
EOL

# Restart Nginx to apply changes
echo "Restarting Nginx..."
systemctl restart nginx

sudo touch /var/www/html/404.html
sudo touch /var/www/html/5xx.html

# Copy the updated HTML file to serve the HLS stream
cat > /var/www/html/index.html <<EOL
<!DOCTYPE html>
<html>
<head>
    <title>Adboard Booking</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<style>
    html,body {
        margin: 0;
        padding: 0;
        overflow: hidden;
    }
    video {
        height: 100vh;
        width: 100%;
        object-fit: fill; 
        position: absolute;
    }
</style>
<body>
    <video id="video" controls></video>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const params = new URLSearchParams(window.location.search);
            const hash = params.get('hash');
            if (!hash) {
                alert("No stream hash provided!");
                return;
            }

            const video = document.getElementById('video');
            const hlsUrl = "/hls/" + hash + "/stream.m3u8";

            if (Hls.isSupported()) {
                const hls = new Hls();
                hls.loadSource(hlsUrl);
                hls.attachMedia(video);
                hls.on(Hls.Events.MEDIA_ATTACHED, function () {
                    video.muted = true;
                    video.play();
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = hlsUrl;
                video.addEventListener('loadedmetadata', function() {
                    video.muted = true;
                    video.play();
                });
            }
        });
    </script>
</body>
</html>
EOL

# Get the CPU serial number as the device ID
DEVICE_ID=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
echo "Using CPU serial number as device ID: $DEVICE_ID"

# Register the tunnel with Pitunnel using the device ID
echo "Registering Pitunnel..."
pitunnel --remove 1
pitunnel --port=80 --http --name=$DEVICE_ID --persist

# Register the device with the server
REGISTER_URL="https://railway.adboardbooking.com/api/camera/register"
PUBLIC_IP=$(curl -s http://whatismyip.akamai.com/)
PRIVATE_IP=$(get_private_ip)

echo "Registering device with server..."

CAMERA_URL="https://$DEVICE_ID-ankurkus.in1.pitunnel.com/?hash=$HASH"
echo "Stream URL: $CAMERA_URL"

echo '{
  "deviceId": "'"$DEVICE_ID"'",
  "rtspUrl": "'"$RTSP_URL"'",
  "publicIp": "'"$PUBLIC_IP"'",
  "privateIp": "'"$PRIVATE_IP"'",
  "cameraUrl": "'"$CAMERA_URL"'
}'

curl -X POST -H "Content-Type: application/json" -d '{
  "deviceId": "'"$DEVICE_ID"'",
  "rtspUrl": "'"$RTSP_URL"'",
  "publicIp": "'"$PUBLIC_IP"'",
  "privateIp": "'"$PRIVATE_IP"'",
  "cameraUrl": "'"$CAMERA_URL"'"
}' $REGISTER_URL

echo "Setup complete. You can now access the stream via the Pitunnel URL provided."

# Log file for FFmpeg
LOG_FILE="/var/log/ffmpeg_stream.log"

# Ensure the log file exists and has the correct permissions
touch $LOG_FILE
chown root:root $LOG_FILE
chmod 644 $LOG_FILE

# Start FFmpeg to transcode RTSP to HLS
echo "Starting FFmpeg to transcode RTSP to HLS..."
sudo ffmpeg -i $RTSP_URL -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -hls_segment_filename "$HLS_DIR/segment_%03d.ts" -f hls $HLS_DIR/stream.m3u8 > $LOG_FILE 2>&1

# Output the URL to access the stream

