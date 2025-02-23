#!/bin/bash

# Get script directory dynamically
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

echo "Script is running from: $SCRIPT_DIR"

# Create systemd service
SERVICE_FILE="/etc/systemd/system/adboardbooking.service"

echo "Creating systemd service at $SERVICE_FILE..."
cat <<EOL | sudo tee $SERVICE_FILE
[Unit]
Description=AdboardBooking Service
After=network.target

[Service]
WorkingDirectory=/home/pi
ExecStart=/home/pi/.pyenv/shims/python3 $SCRIPT_DIR/boot.py
Restart=always
RestartSec=10
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
echo "Enabling and starting AdboardBooking service..."
sudo systemctl daemon-reload
sudo systemctl enable adboardbooking.service
sudo systemctl start adboardbooking.service

# Wait for service startup, then check status
sleep 3
sudo systemctl status adboardbooking.service --no-pager

# Setting up Nginx
echo "Configuring Nginx..."

NGINX_CONFIG="/etc/nginx/sites-available/default"

cat <<EOL | sudo tee $NGINX_CONFIG
server {
    listen 80;

    # Add a Content Security Policy
    add_header Content-Security-Policy "frame-ancestors 'self' http://localhost https://*.adboardbooking.com";

    # Apply CORS headers globally
    add_header 'Access-Control-Allow-Origin' '*';
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
    add_header 'Access-Control-Allow-Headers' 'Origin, Content-Type, Accept, Authorization';
    add_header 'Access-Control-Allow-Credentials' 'true';

    root $SCRIPT_DIR/services/cameraStreaming/public;

     # Point index to the Laravel front controller.
    index           index.html;

    location / {
        # URLs to attempt, including pretty ones.
        try_files   $uri $uri/ /index.html?$query_string;
    }

    # Remove trailing slash to please routing system.
    if (!-d $request_filename) {
            rewrite     ^/(.+)/$ /$1 permanent;
    }
}
EOL

# Check Nginx Configuration
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
sudo systemctl status nginx --no-pager
