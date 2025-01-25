import requests
import subprocess
# Load the registry file

def download_file_from_github(url, output_path):
    """
    Download a file from a given URL and save it to the specified local path.
    :param url: The URL of the file to download.
    :param output_path: The local path to save the downloaded file.
    """
    try:
        print(f"Downloading file from: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Check for HTTP request errors

        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):  # Download in chunks
                file.write(chunk)

        print(f"File downloaded successfully and saved to: {output_path}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")


def execute_python_file(file_path):
    """
    Execute a Python file.
    :param file_path: The path to the Python file to execute.
    """
    try:
        print(f"Executing file: {file_path}")
        subprocess.run(["python3", file_path], check=True)
        print(f"File executed successfully: {file_path}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while executing the file: {e}")

def maintain_download_registry(registry):
    for item in registry.get('download', []):
        url = item.get('url')
        path = item.get('path')
        if url and path:
            download_file_from_github(url, path)
            

if __name__ == "__main__":
    maintain_download_registry({
    "download":[{
        "url":"https://raw.githubusercontent.com/AdBoard-Booking/adboard-booking-camera/refs/heads/main/traffic/streaming.py",
        "path":"streaming.py"
    }]
})