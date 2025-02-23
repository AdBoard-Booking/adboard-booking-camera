import subprocess
import os
import sys
import time
import signal
from services.utils import utils

# Dictionary to track running child processes
processes = {}

def terminate_all():
    """Terminate all running child processes and exit."""
    print("Terminating all child processes...")
    for process in processes.values():
        try:
            process.terminate()  # Send SIGTERM
        except Exception as e:
            print(f"Error terminating process: {e}")

    # Ensure processes are killed
    for process in processes.values():
        process.wait()
    
    print("All child processes stopped. Exiting parent process.")
    sys.exit(1)

def handle_signal(sig, frame):
    """Handle termination signals (SIGTERM, SIGINT) and kill all child processes."""
    print(f"Received signal {sig}. Stopping all processes.")
    terminate_all()

def main():
    try:
        # Register signal handlers (so Ctrl+C or system kill stops all processes)
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

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

        # Start child processes
        for service_name, service_details in config["services"].items():
            if not service_details:
                continue  # Skip if service details are empty
            
            print(f"Starting Service: {service_name}")
            service_dir = os.path.join(base_dir, 'services', service_name)
            file_path = os.path.join(service_dir, "main.py")
            file_path = os.path.abspath(file_path)  # Get absolute path

            # Check if the file exists
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue

            # Check if RTSP stream URL is present
            if not service_details.get("rtspStreamUrl"):  
                print(f"Skipping {service_name} due to missing 'rtspStreamUrl'")
                continue

            # Log file next to the executing script
            log_file = os.path.join(service_dir, f"{service_name}.log")

            # Start the child process
            print(f"Executing {file_path} in background...")
            with open(log_file, "a") as log:
                process = subprocess.Popen(
                    [python_path, file_path],
                    stdout=log, stderr=log, close_fds=True
                )
                processes[service_name] = process  # Store process in dictionary

        # Monitor child processes
        while True:
            for service_name, process in list(processes.items()):  # Convert to list to avoid runtime dict changes
                retcode = process.poll()  # Check if process has exited
                if retcode is not None:
                    print(f"Process {service_name} stopped with exit code {retcode}. Terminating all...")
                    terminate_all()  # Stop everything

            time.sleep(1)  # Reduce CPU usage

    except Exception as e:
        print(f"Unexpected error: {e}")
        terminate_all()

if __name__ == "__main__":
    main()
