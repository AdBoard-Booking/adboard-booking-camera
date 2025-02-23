#!/bin/bash

# Update and install required packages
echo "Updating system and installing dependencies..."
# sudo apt install -y nginx ffmpeg curl

# Get Workspace ID and Camera URL from environment variables
# WORKSPACE_ID=${WORKSPACE_ID:-""}
CAMERA_URL=rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2

# if [ -z "$WORKSPACE_ID" ]; then
#   echo "Error: WORKSPACE_ID is not set. Please export it as an environment variable."
#   exit 1
# fi

# if [ -z "$CAMERA_URL" ]; then
#   echo "Error: CAMERA_URL is not set. Please export it as an environment variable."
#   exit 1
# fi

# echo "Using Workspace ID: $WORKSPACE_ID"
# echo "Using Camera URL: $CAMERA_URL"

# Register camera with the server


# Set up directories for streaming
echo "Creating streaming directory..."
sudo mkdir -p /var/www/stream/

# Copy HLS player file
echo "Creating HLS player file..."
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
        let url = new URLSearchParams(window.location.search).get('url')||'/stream/live.m3u8'

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

# Create FFmpeg service file
echo "Creating FFmpeg service file..."
cat <<EOL | sudo tee /etc/systemd/system/ffmpeg-stream.service
[Unit]
Description=FFmpeg RTSP to HLS Stream
After=network.target

[Service]
ExecStart=/usr/bin/ffmpeg -i $CAMERA_URL -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -f hls /var/www/stream/live.m3u8
Restart=always
RestartSec=10
StandardOutput=file:/var/log/ffmpeg_stream.log
StandardError=file:/var/log/ffmpeg_stream.err
User=root

[Install]
WantedBy=multi-user.target
EOL

# Enable and start FFmpeg service
echo "Enabling and starting FFmpeg service..."
sudo systemctl enable ffmpeg-stream
sudo systemctl start ffmpeg-stream

# Configure Nginx
echo "Configuring Nginx..."
cat <<EOL | sudo tee /etc/nginx/sites-available/default
server {
    listen 80;

    # Add a Content Security Policy
    add_header Content-Security-Policy "frame-ancestors 'self' http://localhost https://*.adboardbooking.com";

    # Apply CORS headers globally
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

# Test and restart Nginx
echo "Testing Nginx configuration..."
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "Restarting Nginx..."
    sudo systemctl reload nginx
else
    echo "Nginx configuration test failed. Please check the configuration file."
    exit 1
fi

# Check Nginx status
echo "Checking Nginx status..."
echo "Setup completed successfully."

tailscale funnel --bg 80
sleep 5

FUNNEL_URL=$(tailscale funnel status | grep -o 'https://[^ ]*' | head -n 1)
echo "Funnel URL: $FUNNEL_URL"

# Send request and capture full response
REGISTRATION_RESPONSE=$(curl -s --fail -X POST "https://api.adboardbooking.com/camera/register" \
    -H "Content-Type: application/json" \
    -d '{"workspaceId": "'"$WORKSPACE_ID"'", "cameraUrl": "'"$CAMERA_URL"'", "zerotierIp": "'"$FUNNEL_URL"'"}' \
    -w "%{http_code}")

# Extract HTTP status using `expr`
HTTP_STATUS=$(echo "$REGISTRATION_RESPONSE" | awk '{print substr($0,length($0)-2,3)}')
RESPONSE_BODY=$(echo "$REGISTRATION_RESPONSE" | awk '{print substr($0,1,length($0)-3)}')

echo "Registration Response: $RESPONSE_BODY"
echo "HTTP Status Code: $HTTP_STATUS"

# Wait for successful response
if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "Registration successful!"
else
    echo "Registration failed with status code: $HTTP_STATUS"
    exit 1
fi