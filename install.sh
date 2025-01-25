#!/bin/bash

echo "Starting installation process..."

# Check if Git is installed
if ! command -v git &>/dev/null; then
    echo "Git is not installed. Installing Git..."
    sudo apt-get install -y git
else
    echo "Git is already installed."
fi

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
REPO_DIR=~/adboard-booking-camera
REPO_URL=https://github.com/AdBoard-Booking/adboard-booking-camera.git

echo "Cloning repository..."
if [ -d "$REPO_DIR" ]; then
    echo "Repository directory already exists. Pulling latest changes..."
    cd "$REPO_DIR" || exit
    git fetch --depth=1
    git reset --hard origin/main
else
    echo "Repository directory does not exist. Cloning latest commit..."
    git clone --depth=1 "$REPO_URL" "$REPO_DIR"
fi

# Example: Execute a setup script in the repository
echo "Running setup script..."
bash "$REPO_DIR/setup.sh"

echo "Installation completed successfully!"
