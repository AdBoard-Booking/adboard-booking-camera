import socketio
import requests
import time

# Create a Socket.IO client with reconnection options
sio = socketio.Client(reconnection=True, reconnection_attempts=5, reconnection_delay=2)

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

deviceId = get_cpu_serial()

@sio.event
def connect():
    print("Connected to the server.")
    # Send a message to the server upon connecting
    sio.emit('message', {'deviceId': deviceId})

@sio.event
def message(data):
    print("Received response from server:", data)

@sio.event
def disconnect():
    print("Disconnected from the server. Attempting to reconnect...")

@sio.event
def connect_error(data):
    print(f"[ERROR] Connection failed: {data}. Retrying...")

# Connect to the Next.js server
WEB_SERVER_URL = 'http://localhost:3000'
API_ENDPOINT = '/api/websocket/server'

# Function to handle reconnection attempts
def connect_with_retry():
    while True:
        try:
            requests.get(f"{WEB_SERVER_URL}{API_ENDPOINT}")
            sio.connect(WEB_SERVER_URL)
            sio.wait()  # Keep the connection alive
        except (socketio.exceptions.ConnectionError, OSError) as e:
            print(f"[ERROR] Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(10)

# Start the connection
connect_with_retry()
