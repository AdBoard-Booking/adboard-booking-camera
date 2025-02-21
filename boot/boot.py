import requests
import subprocess
import os
import utils

def main():
    DEVICE_ID = utils.get_cpu_serial()

    config = utils.load_config(DEVICE_ID)
    if config is None:
        print("Failed to load configuration. Exiting...")
        return
    
    for service_name,service_details in config["services"].items():
        
        if not service_details:
            continue
            
        print(f"Service: {service_name}")
        filePath = f'/home/pi/adboard-booking-camera/{service_name}/main.py'

        #if file exists
        if not os.path.exists(filePath):
            print(f"File not found: {filePath}")
            continue

        if not service_details['rtspStreamUrl']:
            continue

        print(f"Executing file: {filePath}")
        subprocess.run(["/home/pi/.pyenv/shims/python3", filePath], check=True)

if __name__ == "__main__":
    main()
   