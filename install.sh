#!/bin/bash

echo "Starting installation process..."

# Example: Update packages
echo "Updating packages..."
sudo apt update && sudo apt upgrade -y

# Example: Install dependencies
echo "Installing dependencies..."
curl https://pyenv.run | bash

# Add pyenv to bashrc if not already added
if ! grep -q 'export PYENV_ROOT="$HOME/.pyenv"' ~/.bashrc; then
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc
fi

source ~/.bashrc

sudo apt-get install -y bzip2 ncurses libffi-dev libreadline-dev libssl-dev

# Check if Python 3.9.11 is already installed
if pyenv versions | grep -q "3.9.11"; then
    echo "Python 3.9.11 is already installed. Skipping installation."
else
    echo "Installing Python 3.9.11..."
    pyenv install 3.9.11
fi

pyenv global 3.9.11

# Example: Clone a GitHub repository (replace with your repo)
echo "Cloning repository..."
rm -rf ~/adboard-booking-camera
git clone https://github.com/AdBoard-Booking/adboard-booking-camera.git ~/adboard-booking-camera

# Example: Execute a setup script in the repository
echo "Running setup script..."
bash ~/adboard-booking-camera/setup.sh

echo "Installation completed successfully!"
