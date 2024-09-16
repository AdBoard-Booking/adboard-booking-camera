## Setup instruction

1. Run setup.sh to install the ffmpeg service to auto relaunch on boot
2. Run register.sh, This will register the camera to adboardbooking server

Setup.sh 
* Needs to be run once 
* Scan the rtsp links
* Setup ngnix

* Setup the pitunnel


Register.sh
* Needs to be run on each boot

start_ffmpeg.sh
* This service is responsible for hosting camera feed

ffmpeg.service
* This is a systemctl file, required for configuring auto boot service

Python 3.9.19

sudo sh ./setup.sh 
sudo journalctl -u adboardbookingai.service -n 50

/usr/local/bin/adboardbooking/registered_cameras.json

code /home/pi/adboard-booking-camera/CameraStreamingAI/billboard_data.json
sudo systemctl stop adboardbookingai.service
sudo systemctl start adboardbookingai.service
sudo systemctl status adboardbookingai.service

cat /var/log/adboardbookingai_stream.err