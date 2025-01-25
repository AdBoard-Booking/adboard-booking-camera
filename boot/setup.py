import json
import os
import requests

# Load the registry file

def download_file(url, path):
    response = requests.get(url)
    response.raise_for_status()  # Check if the request was successful
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as file:
        file.write(response.content)
    print(f"Downloaded {url} to {path}")

def maintain_download_registry(registry):
    for item in registry.get('download', []):
        url = item.get('url')
        path = item.get('path')
        if url and path:
            download_file(url, path)

if __name__ == "__main__":
    maintain_download_registry({
    "download":[{
        "url":"https://raw.githubusercontent.com/AdBoard-Booking/adboard-booking-camera/refs/heads/main/traffic/streaming.py",
        "path":"/home/pi/streaming.py"
    }]
})