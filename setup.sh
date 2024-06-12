#!/bin/bash

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

echo "Updating package list..."
apt-get update
apt-get install -y ffmpeg
apt-get install -y nginx

echo "All dependencies are installed."

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

# Copy scripts to /usr/local/bin
sudo cp ./start_ffmpeg.sh /usr/local/bin/start_ffmpeg.sh

# Change permissions
sudo chmod +x /usr/local/bin/start_ffmpeg.sh

# Copy service files
sudo cp ffmpeg.service /etc/systemd/system/ffmpeg.service

# Reload systemd daemon
systemctl daemon-reload

# Enable and start services
systemctl enable ffmpeg.service
systemctl start ffmpeg.service

echo "Setup complete. Services are running."
