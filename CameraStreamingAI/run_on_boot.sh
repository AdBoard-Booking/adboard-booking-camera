#!/bin/bash

sudo -u pi bash << EOF
export PYENV_ROOT="\$HOME/.pyenv"
export PATH="\$PYENV_ROOT/bin:\$PATH"
eval "\$(pyenv init -)"
eval "\$(pyenv virtualenv-init -)"
pyenv shell 3.9.19
python /usr/local/bin/adboardbookingai/yolo_across_frame_cmd.py
EOF