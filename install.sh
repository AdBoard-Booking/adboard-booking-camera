#!/bin/bash

echo "Starting installation process..."

# Example: Update packages
echo "Updating packages..."
sudo apt update && sudo apt upgrade -y

# Example: Install dependencies
echo "Installing dependencies..."
curl https://pyenv.run | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

sudo apt-get install bzip2 ncurses libffi readline OpenSSL

pyenv install 3.9.11
pyenv global 3.9.11

# Example: Clone a GitHub repository (replace with your repo)
echo "Cloning repository..."
rm -rf ~/adboard-booking-camera
git clone https://github.com/AdBoard-Booking/adboard-booking-camera.git ~/adboard-booking-camera

# Example: Execute a setup script in the repository
echo "Running setup script..."
bash ~/repository/setup.sh

echo "Installation completed successfully!"