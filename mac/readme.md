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