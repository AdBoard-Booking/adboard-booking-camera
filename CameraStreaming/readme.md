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

# Python 3.9.19
curl https://pyenv.run | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

sudo apt-get install bzip2 ncurses libffi readline OpenSSL

pyenv install 3.9
pyenv global 3.9


# Service
sudo systemctl stop adboardbooking.service
sudo systemctl start adboardbooking.service
sudo systemctl status adboardbooking.service

 tail -f /var/log/ffmpeg_stream.log