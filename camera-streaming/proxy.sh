#!/bin/bash

# Update and install required packages
echo "Updating system and installing dependencies..."
sudo apt update
sudo apt install -y nginx 

# Install and configure ZeroTier
echo "Installing ZeroTier..."
curl -s https://install.zerotier.com | sudo bash
echo "Joining ZeroTier network..."
sudo zerotier-cli join 48d6023c46a723d4

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
        root /var/www/html;
        index index.html index.htm;
    }

    location ~ ^/proxy/([0-9\.]+)/(.+)$ {
        # Extract ZeroTier IP and path
        set \$zt_ip \$1;
        set \$zt_path /\$2;

        # Ensure trailing slash is added
        if (\$zt_path !~ /$/) {
            rewrite ^(.*[^/])$ \$1/ permanent;
        }

        # Proxy pass to the ZeroTier IP
        proxy_pass http://\$zt_ip\$zt_path;

        # Pass headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
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

echo "Setting up PiTunnel..."
curl -s pitunnel.com/get/kiYvJkacAJ | sudo bash
echo "Starting PiTunnel service..."
pitunnel --remove 1
pitunnel --port=80 --http --persist

echo "Setup completed successfully."
