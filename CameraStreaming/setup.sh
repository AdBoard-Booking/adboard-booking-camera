#!/bin/bash

# Ensure the script runs with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./setup.sh)"
    exit 1
fi

echo "Setting up the camera stream..."

# Create directory for streaming files
mkdir -p /var/www/stream
chown -R www-data:www-data /var/www/stream

# Create index.html for HLS streaming
cat <<EOL | sudo tee /var/www/stream/index.html
<!DOCTYPE html>
<html>
<head>
    <title>Camera stream</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<body>
    <video id="video" controls autoplay style="width: 100%;"></video>
    <script>
        let url = new URLSearchParams(window.location.search).get('url') || '/stream/live.m3u8';

        if (Hls.isSupported()) {
            var video = document.getElementById('video');
            var hls = new Hls();
            hls.loadSource(url);
            hls.attachMedia(video);
            hls.on(Hls.Events.MEDIA_ATTACHED, function () {
                video.muted = true;
                video.play();
            });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = url;
            video.addEventListener('loadedmetadata', function() {
                video.muted = true;
                video.play();
            });
        }
    </script>
</body>
</html>
EOL

echo "HTML page created at /var/www/stream/index.html"

# Configure Nginx
echo "Configuring Nginx..."
cat <<EOL | sudo tee /etc/nginx/sites-available/default
server {
    listen 80;

    add_header Content-Security-Policy "frame-ancestors 'self' http://localhost https://*.adboardbooking.com";
    add_header 'Access-Control-Allow-Origin' '*';
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
    add_header 'Access-Control-Allow-Headers' 'Origin, Content-Type, Accept, Authorization';
    add_header 'Access-Control-Allow-Credentials' 'true';

    location / {
        root /var/www/stream;
        index index.html index.htm;
    }

    location /stream {
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
        alias /var/www/stream/;
    }
}
EOL

# Enable the Nginx config
sudo nginx -t
# ln -sf /etc/nginx/sites-available/streaming /etc/nginx/sites-enabled/
systemctl reload nginx

echo "Nginx configured and reloaded."

# Install FFmpeg if not installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    apt update && apt install -y ffmpeg
else
    echo "FFmpeg is already installed."
fi

# Copy Python script to destination
echo "Installing Python script..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp $SCRIPT_DIR/fetch_and_stream.py /usr/local/bin/
chmod +x /usr/local/bin/fetch_and_stream.py

# Install Python dependencies
# apt install -y python3-pip
# pip3 install requests

# Create systemd service
cat <<EOL | sudo tee /etc/systemd/system/ffmpeg-stream.service
[Unit]
Description=FFmpeg RTSP to HLS Stream
After=network.target

[Service]
ExecStart=/home/pi/.pyenv/shims/python $SCRIPT_DIR/fetch_and_stream.py
Restart=always
RestartSec=10
StandardOutput=file:/var/log/ffmpeg_stream.log
StandardError=file:/var/log/ffmpeg_stream.err
User=root

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
systemctl daemon-reload
systemctl enable ffmpeg-stream
systemctl start ffmpeg-stream

echo "FFmpeg streaming service created and started."

echo "Setup completed successfully!"
