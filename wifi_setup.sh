#!/bin/bash

set -e

echo "Updating package list and installing required packages..."
sudo apt-get update
# sudo apt-get install -y dnsmasq hostapd nginx php-fpm

echo "Configuring hostapd..."
sudo bash -c 'cat > /etc/hostapd/hostapd.conf << EOF
interface=wlan0
driver=nl80211
ssid=adboard-booking-pi
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
EOF'

sudo sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

echo "Configuring dnsmasq..."
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
sudo bash -c 'cat > /etc/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF'

echo "Configuring network..."
sudo bash -c 'cat >> /etc/dhcpcd.conf << EOF
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF'

echo "Setting up web server..."
sudo mkdir -p /var/www/html/wifi-setup
sudo bash -c 'cat > /var/www/html/wifi-setup/index.php << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Adboard Booking - Wi-Fi Setup</title>
    <link href="https://unpkg.com/tailwindcss@^2.0/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded shadow-md w-full max-w-sm">
        <h1 class="text-2xl font-bold mb-4">Adboard Booking - Wi-Fi Setup</h1>
        <form method="post" class="space-y-4">
            <div>
                <label for="ssid" class="block text-sm font-medium text-gray-700">SSID:</label>
                <input type="text" name="ssid" id="ssid" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            </div>
            <div>
                <label for="password" class="block text-sm font-medium text-gray-700">Password:</label>
                <input type="password" name="password" id="password" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            </div>
            <div>
                <input type="submit" value="Submit" class="w-full bg-indigo-600 text-white py-2 px-4 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
            </div>
        </form>
        <?php
        if (\$_SERVER["REQUEST_METHOD"] == "POST") {
            \$ssid = \$_POST["ssid"];
            \$password = \$_POST["password"];
            \$conf = "country=US\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\n\nnetwork={\n    ssid=\\"\$ssid\\"\n    psk=\\"\$password\\"\n    key_mgmt=WPA-PSK\n}\n";
            file_put_contents("/etc/wpa_supplicant/wpa_supplicant.conf", \$conf);
            echo "Configuration saved. Rebooting...";
            shell_exec('sudo reboot');
        }
        ?>
    </div>
</body>
</html>
EOF'

echo "Configuring Nginx..."
sudo bash -c 'cat > /etc/nginx/sites-available/default << EOF
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
EOF'

echo "Enabling and starting services..."
sudo systemctl restart dhcpcd
sudo systemctl start hostapd
sudo systemctl start dnsmasq
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl enable nginx

echo "Setup complete. Please reboot the Raspberry Pi."
