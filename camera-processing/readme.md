# How to debug

cat /etc/systemd/system/ffmpeg-stream.service

sudo systemctl status ffmpeg-stream

sudo systemctl enable ffmpeg-stream
sudo systemctl stop ffmpeg-stream
sudo systemctl start ffmpeg-stream

#########################################################

sudo apt update
sudo apt install nginx ffmpeg -y

CameraIP: rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2


sudo mkdir /var/www/stream/
sudo nano /etc/systemd/system/ffmpeg-stream.service

```
[Unit]
Description=FFmpeg RTSP to RTMP Stream
After=network.target

[Service]
ExecStart=/usr/bin/ffmpeg -i rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2 -c:v copy -hls_time 1 -hls_list_size 3 -hls_flags delete_segments+append_list -start_number 1 -f hls /var/www/stream/live.m3u8
Restart=always
RestartSec=10
StandardOutput=file:/var/log/ffmpeg_stream.log
StandardError=file:/var/log/ffmpeg_stream.err
User=root

[Install]
WantedBy=multi-user.target
```


sudo systemctl enable ffmpeg-stream
sudo systemctl start ffmpeg-stream
sudo systemctl status ffmpeg-stream

sudo nano /etc/nginx/sites-available/default 


```
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

    location /camera {
        root /var/www/stream;
        hls.html
    }

    location /stream {
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
        alias /var/www/stream/;
    }
}

//check config
sudo nginx -t 
sudo systemctl restart nginx
sudo systemctl status nginx