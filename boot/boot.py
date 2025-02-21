import requests
import subprocess
import os
import sys
import utils

def main():
    try:
        # Get the Python path dynamically
        python_path = sys.executable
        print(f"Using Python: {python_path}")

        # Get the base directory dynamically
        base_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Base Directory: {base_dir}")

        # Get device ID
        DEVICE_ID = utils.get_cpu_serial()

        # Load configuration
        config = utils.load_config(DEVICE_ID)
        if not config or "services" not in config:
            print("Failed to load configuration or missing 'services'. Exiting...")
            return

        # Iterate through services
        for service_name, service_details in config["services"].items():
            if not service_details:
                continue  # Skip if service details are empty
            
            print(f"Service: {service_name}")
            file_path = os.path.join(base_dir, "..", service_name, "main.py")
            file_path = os.path.abspath(file_path)  # Get absolute path

            # Check if the file exists
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue

            # Check if RTSP stream URL is present
            if not service_details.get("rtspStreamUrl"):  
                print(f"Skipping {service_name} due to missing 'rtspStreamUrl'")
                continue

            # Redirect logs
            log_file = os.path.join(base_dir, f"{service_name}.log")

            # Execute the script in the background
            print(f"Executing {file_path} in background...")
            with open(log_file, "a") as log:
                subprocess.Popen(
                    [python_path, file_path],
                    stdout=log, stderr=log, close_fds=True
                )

    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
