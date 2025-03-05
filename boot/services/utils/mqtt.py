import paho.mqtt.client as mqtt
import logging
from utils import get_cpu_serial
import json
from datetime import datetime

DEVICE_ID = get_cpu_serial()    

# EMQX Broker Settings
BROKER = '67eb329c985848aa8f600b2543575c8e.s1.eu.hivemq.cloud'
# BROKER='ie2c39d3.ala.us-east-1.emqxsl.com'
PORT = 8883
TOPIC = f"logs/{DEVICE_ID}"
USERNAME = "test123"    # Add your EMQX username here
PASSWORD = "Test@123"    # Add your EMQX password here

# Set up logging only if debug is enabled
DEBUG = False  # Set this to True to enable debug logging

logger = logging.getLogger(__name__)
if DEBUG:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)  # Set to CRITICAL to disable INFO, WARNING, and DEBUG logs


# Callback functions for debugging
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
    else:
        logger.error(f"Failed to connect, return code {rc}")
        # rc meanings:
        # 0: Connection successful
        # 1: Connection refused - incorrect protocol version
        # 2: Connection refused - invalid client identifier
        # 3: Connection refused - server unavailable
        # 4: Connection refused - bad username or password
        # 5: Connection refused - not authorised

def on_disconnect(client, userdata, rc, properties=None):
    logger.info(f"Disconnected with result code: {rc}")

def on_publish(client, userdata, mid, properties=None):
    logger.debug(f"Message {mid} published successfully")

def on_log(client, userdata, level, buf):
    logger.debug(f"MQTT Log: {buf}")

class MQTTClient:
    _instance = None
    _is_connected = False
    
    @staticmethod
    def get_instance():
        if MQTTClient._instance is None:
            MQTTClient._instance = mqtt.Client(protocol=mqtt.MQTTv5)
            client = MQTTClient._instance
            
            # Set up callbacks
            client.on_connect = lambda client, userdata, flags, rc, properties=None: MQTTClient._on_connect(client, userdata, flags, rc, properties)
            client.on_disconnect = on_disconnect
            client.on_publish = on_publish
            client.on_log = on_log
            
            # Enable SSL/TLS
            client.tls_set()
            
            # Set username and password
            client.username_pw_set(USERNAME, PASSWORD)
            
            logger.debug(f"Attempting to connect to {BROKER}:{PORT}")
            client.connect(BROKER, PORT, keepalive=60)
            
            # Start the loop in a background thread
            client.loop_start()
            
        return MQTTClient._instance

    @staticmethod
    def _on_connect(client, userdata, flags, rc, properties=None):
        MQTTClient._is_connected = (rc == 0)
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
        else:
            logger.error(f"Failed to connect, return code {rc}")

    @staticmethod
    def wait_for_connection(timeout=10):
        """Wait for the connection to be established"""
        import time
        start_time = time.time()
        while not MQTTClient._is_connected:
            if time.time() - start_time > timeout:
                raise TimeoutError("Connection timeout")
            time.sleep(0.1)

def publish_message(message, topic=TOPIC):
    try:
        client = MQTTClient.get_instance()
        
        # Wait for connection before publishing
        try:
            MQTTClient.wait_for_connection()
        except TimeoutError:
            logger.error("Timed out waiting for MQTT connection")
            return
            
        # Convert message to JSON if it's not already
        if isinstance(message, str):
            try:
                # Check if the string is already valid JSON
                json.loads(message)
                msg_dict = message
            except json.JSONDecodeError:
                # If not JSON, create a new JSON object
                msg_dict = {
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
                msg_dict = json.dumps(msg_dict)
        else:
            # If message is dict or other type, convert to JSON
            if isinstance(message, dict):
                message["timestamp"] = datetime.now().isoformat()
                msg_dict = json.dumps(message)
            else:
                msg_dict = json.dumps({
                    "message": str(message),
                    "timestamp": datetime.now().isoformat()
                })
            
        logger.debug(f"Attempting to publish message: {msg_dict}")
        result = client.publish(topic, msg_dict)
        
        # Check if the message was published
        if result[0] == 0:
            logger.debug(f"Message queued successfully. Message ID: {result[1]}")
        else:
            logger.error(f"Failed to publish message. Result code: {result[0]}")
            
    except Exception as e:
        logger.error(f"Error in publish_message: {str(e)}", exc_info=True)

def publish_log(message, topic):
    logger.info(f"Publishing log: {message} to topic: {topic}/{DEVICE_ID}")
    publish_message(message, f"{topic}/{DEVICE_ID}")

if __name__ == "__main__":
    message = "Car detected at intersection at 10:45 AM"
    publish_message(message)
