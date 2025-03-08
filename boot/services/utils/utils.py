import requests
import logging
import sys

DEBUG = False
logger = logging.getLogger(__name__)
if DEBUG:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logger.addHandler(logging.NullHandler())
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)  # This ensures logs go to stdout
        ]
    ) # Set to CRITICAL to disable INFO, WARNING, and DEBUG logs


def get_cpu_serial():
    """Fetch the CPU serial number as a unique device ID."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.strip().split(":")[1].strip()
    except Exception as e:
        print(f"[ERROR] Unable to read CPU serial: {e}")
    return "UNKNOWN"

def load_config(device_id):
    logger.info("""Loading configuration from the API.""")
    # config_url = f"http://localhost:3000/api/camera/v1/config/{device_id}"
    config_url = f"https://railway.adboardbooking.com/api/camera/v1/config/{device_id}"
    try:
        response = requests.get(config_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Unable to load config: {e}")
        return None
    

def load_config_for_device():
    DEVICE_ID = get_cpu_serial()    
    return load_config(DEVICE_ID)