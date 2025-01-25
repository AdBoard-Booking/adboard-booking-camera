#!/bin/bash

echo "Starting installation process..."
cp -r /home/pi/adboard-booking-camera/boot/boot.py /home/pi/boot.py
cp -r /home/pi/adboard-booking-camera/boot/streaming.py /home/pi/streaming.py

sh boot/setup.sh
sh traffic/setup.sh