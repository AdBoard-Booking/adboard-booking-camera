import subprocess

subprocess.run([
    "/home/pi/.pyenv/shims/python3", '/home/pi/adboard-booking-camera/billboardMonitoring/monitoring.py',
    "--publish", "1",
    "--verbose", "0"
    ], check=True)