#!/bin/bash

# Set up the hotspot
setup_hotspot() {
    echo "Setting up hotspot..."

    # Stop the services if they are running
    sudo systemctl stop dnsmasq
    sudo systemctl stop hostapd

    # Configure the static IP for wlan0
    cat <<EOF | sudo tee /etc/dhcpcd.conf
interface wlan0
static ip_address=192.168.50.1/24
nohook wpa_supplicant
EOF

    # Restart the DHCP service
    sudo service dhcpcd restart

    # Configure dnsmasq
    cat <<EOF | sudo tee /etc/dnsmasq.conf
interface=wlan0
dhcp-range=192.168.50.10,192.168.50.100,12h
EOF

    # Enable and start dnsmasq
    sudo systemctl start dnsmasq

    # Configure hostapd
    cat <<EOF | sudo tee /etc/hostapd/hostapd.conf
interface=wlan0
driver=nl80211
ssid=PiHotspot
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=raspberry
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

    sudo sed -i 's/#DAEMON_CONF=""/DAEMON_CONF="\/etc\/hostapd\/hostapd.conf"/' /etc/default/hostapd

    # Enable and start hostapd
    sudo systemctl start hostapd
    sudo systemctl enable hostapd

    echo "Hotspot setup complete."
}

# Set up the web server
setup_web_server() {
    echo "Setting up web server..."

    # Create the HTML form
    sudo mkdir -p /var/www/html
    cat <<EOF | sudo tee /var/www/html/index.html
<!DOCTYPE html>
<html>
<head>
    <title>WiFi Setup</title>
</head>
<body>
    <h1>Enter WiFi Credentials</h1>
    <form action="/submit.php" method="post">
        SSID: <input type="text" name="ssid"><br>
        Password: <input type="password" name="password"><br>
        <input type="submit" value="Submit">
    </form>
</body>
</html>
EOF

    # Create the PHP script to handle the form submission
    cat <<EOF | sudo tee /var/www/html/submit.php
<?php
if (\$_SERVER["REQUEST_METHOD"] == "POST") {
    \$ssid = escapeshellarg(\$_POST["ssid"]);
    \$password = escapeshellarg(\$_POST["password"]);

    // Write the WiFi credentials to the wpa_supplicant.conf file
    \$wpa_conf = "/etc/wpa_supplicant/wpa_supplicant.conf";
    \$wpa_content = "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\n\nnetwork={\n    ssid=\\"\$ssid\\"\n    psk=\\"\$password\\"\n}";

    file_put_contents(\$wpa_conf, \$wpa_content);

    // Restart the WiFi interface
    shell_exec("sudo systemctl restart dhcpcd");
    shell_exec("sudo systemctl restart wpa_supplicant");

    echo "WiFi credentials saved. Reconnecting...";
}
?>
EOF

    # Configure lighttpd
    sudo lighttpd-enable-mod fastcgi-php
    sudo systemctl restart lighttpd

    echo "Web server setup complete."
}

# Main script
main() {
    setup_hotspot
    setup_web_server
}

main
