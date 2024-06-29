# Setup

## Guide
`https://singleboardblog.com/install-python-opencv-on-raspberry-pi/`

## Python
* Install raspian OS
```
rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2
```

* Install git using
`sudo apt install git`

* Install venv
`python3 -m venv venv`

* Activate the virtual environment: 
`source venv/bin/activate`

* Install depdendencies
`pip install opencv-python numpy scipy`

* Run program
`python billboard_tracker.py` 

* Camera IP
`rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2`

Issues
* Installation is taking too much time

## Nodejs

Install Nodejs
`sudo apt install -y nodejs`
`sudo apt install npm`
`npm install node-rtsp-stream opencv4nodejs ws`

Issues
* Install npm and nodejs 