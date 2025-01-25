import requests

def download_file_from_github(url, output_path):
    """
    Downloads a file from a GitHub URL and saves it locally.
    
    :param url: The URL of the GitHub file (raw file URL recommended).
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

if __name__ == "__main__":
    # Replace with your GitHub file's raw URL
    github_file_url = "https://raw.githubusercontent.com/username/repository/branch/filename"
    save_path = "local_filename"

    download_file_from_github(github_file_url, save_path)