## Install python 
curl -fsSL https://pyenv.run | bash

pyenv install 3.9.11
pyenv global 3.9.11

Update zshrc file
`
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
`

Camera url: rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2

pip3 install opencv-python


Setting service
sudo nano /etc/systemd/system/traffic.service
```
[Unit]
Description=My Python Script
After=network.target

[Service]
WorkingDirectory=/home/pi
ExecStart=/home/pi/.pyenv/shims/python3 /home/pi/streaming.py
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target

```

Enable service

sudo systemctl daemon-reload
sudo systemctl enable traffic.service
sudo systemctl start traffic.service
sudo systemctl status traffic.service

sudo systemctl stop traffic.service

Logs
sudo journalctl -u traffic.service -f

Edit
rm -rf streaming.py
nano streaming.py

