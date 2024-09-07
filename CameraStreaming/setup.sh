#!/bin/bash

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

sudo apt install nmap nginx jq -y
sudo sh ./scan_rtsp.sh 

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
        if (\$request_method = 'GET') {
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
            add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range' always;
        }
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
    }
    location = /5xx.html {
        internal;
        root /var/www/html;
        add_header Content-Type text/html;
    }
}
EOL

# Restart Nginx to apply changes
echo "Restarting Nginx..."
systemctl restart nginx

cat > /var/www/html/404.html <<EOL
<!DOCTYPE html>
<html>
<head>
    <title>Adboard Booking</title>
</head>
<body>
</body>
</html>
EOL

cat > /var/www/html/5xx.html <<EOL
<!DOCTYPE html>
<html>
<head>
    <title>Adboard Booking</title>
</head>
<body>
</body>
</html>
EOL

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
sudo mkdir /usr/local/bin/adboardbooking
sudo cp ./run_on_boot.sh /usr/local/bin/adboardbooking/run_on_boot.sh
sudo cp ./start_ffmpeg.sh /usr/local/bin/adboardbooking/start_ffmpeg.sh
sudo cp ./scan_rtsp.sh /usr/local/bin/adboardbooking/scan_rtsp.sh
sudo cp ./yolo_supervision_lite.py /usr/local/bin/adboardbooking/yolo_supervision_lite.py

sudo chmod +x /usr/local/bin/adboardbooking/*.sh
sudo chmod +x /usr/local/bin/adboardbooking/*.py

# Copy service files
sudo cp adboardbooking.service /etc/systemd/system/adboardbooking.service

# Reload systemd daemon
systemctl daemon-reload

# Enable and start services
systemctl enable adboardbooking.service
systemctl start adboardbooking.service

echo "Setup complete. Services are running."
