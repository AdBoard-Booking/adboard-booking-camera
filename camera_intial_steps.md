# Camera setup

* Buy camera https://www.amazon.in/dp/B0BQJVKVQR/ref=twister_B0CYJQXYX5?_encoding=UTF8&psc=1
* Buy rpi zero https://robu.in/product/raspberry-pi-zero-2-w/?gad_source=1&gclid=Cj0KCQjwpZWzBhC0ARIsACvjWRNJfGQYgWpvc8pM5GC6O0k1tJBQTdndo4pn44hRunTYZ23_rLhyWYMaAp2qEALw_wcB
* Buy SD card https://www.amazon.in/HP-MicroSD-U1-TF-Card-32GB/dp/B07DJLFMPS/ref=sr_1_5?crid=TDDIM3GYZQ4N&dib=eyJ2IjoiMSJ9.ZfOvxJD5ryLocenOBv6PvIx7rLmGVwb-dLoTrNJDd5VhDXNLQdpx0Mnd5kgHwyItZ1PgYK4in26ni5NUz1lSBxlnbItiGlySeXVPeaXt4w5wsSUcEoWiJi2SCEXQlv_sZiDdo-qA-l_t8s8CHnSynRghxpDPyQE3dhQ4Nh07gystZno7OT8xnhXq-NTaFuFHMN7UOxmbDEoXLpG90itzipkvBhfkhjIOdWYcpSt5ltk.rILvNTjis2H346dj6D0Lytv66yntIu-EEdukVsy78po&dib_tag=se&keywords=32gb+memory+card&qid=1717931746&sprefix=32gb%2Caps%2C306&sr=8-5
* Cover: https://robu.in/product/official-raspberry-pi-zero-case/?gad_source=4&gclid=Cj0KCQjwpZWzBhC0ARIsACvjWRN1IuwKSf0fsgm9gn9PxvhqSxm2Owjto6K-gxs5_R7uH-ebT2xvWdoaAjfwEALw_wcB
* Adapter with type-b cable https://www.amazon.in/Charger-Multi-Layer-Protection-Certified-Charging/dp/B0B6JMGXHQ/ref=sr_1_14_f3_0o_fs?crid=3GMKPZE4ZYU01&dib=eyJ2IjoiMSJ9.n1qqzJeup_e1-rOjMoulcyF_fUVh1XYADQm_anlM8Mv9tDPcnbNt98hnn3_iKv3fkOJP1LIxJ8Vbyf-Z-uOmzjspsdfzA2cuH32HEyAvYbbS02nEy5-VJsZa4gBdSTRVuj5gtUdmBPvVhF2hhJEHmPbdc2HD3i03bqZ0xJ2utdH0Ptw2zalU0fB7ly5x12cbH_o3T2O5UBhI593kYJEChLyomS8dCq5EuHACssnq0Dw.s3WmD1phFI2n4y6emg9CnVfCV1mXo4q__2w3KNlHKYI&dib_tag=se&keywords=usb%2Btype%2Bb%2Bcharger&qid=1717931823&sprefix=usb%2Bcharger%2Bwith%2Btype%2Caps%2C299&sr=8-14&th=1

### Admin side
* Boot raspbian lite on sd card
* RPI Imager: https://www.raspberrypi.com/software/
* Raspi OS Lite: https://downloads.raspberrypi.com/raspios_lite_armhf/images/raspios_lite_armhf-2024-03-15/2024-03-15-raspios-bookworm-armhf-lite.img.xz?_gl=1*atq6xh*_ga*MTM3NzI0NDAzNy4xNzE3OTMxOTQ1*_ga_22FD70LWDS*MTcxNzkzMTk0NS4xLjEuMTcxNzkzMTk2MS4wLjAuMA..
* Setup pitunnel `curl -s pitunnel.com/get/kiYvJkacAJ | sudo bash`
* Change hostname to workspace alias, for automatic mapping to workspace `sudo raspi-config`
- Setup hostname
- Setup wifi //can be done if wifi user and password are known

```
git clone https://github.com/AdBoard-Booking/adboard-booking-camera
cd adboard-booking-camera
chmod +x ./setup.sh
sudo sh ./setup.sh
```

### client side
Wifi setup steps
```
git clone https://github.com/AdBoard-Booking/adboard-booking-camera
cd adboard-booking-camera
chmod +x setup_wifi_ap.sh
sudo ./setup_wifi_ap.sh
```

Connect wifi `adboard-booking-pi`
Open page http://192.168.4.1/wifi-setup

-- In case wifi setup fails
* Open memory card in laptop
* Setup Wifi
Add the following content to the wpa_supplicant.conf file, replacing your_SSID and your_password with your Wi-Fi network's SSID and password:
```
plaintext
Copy code
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="your_SSID"
    psk="your_password"
    key_mgmt=WPA-PSK
}
```

* Enable SSH:
Create an empty file named ssh (without any extension) in the root directory of the SD card. This will enable SSH on boot.

### Admin side
* Once pi is connected to internet
* Check if PI is visible on pitunnel
* Check if new camera server is available in adboardbooking


### Logs
sudo journalctl -u ffmpeg.service -f
tail -f /var/log/ffmpeg_stream.log

ps aux | grep -i '[f]fmpeg'