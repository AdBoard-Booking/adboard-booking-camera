import paho.mqtt.client as mqtt
import logging
from utils import get_cpu_serial

DEVICE_ID = get_cpu_serial()    

# EMQX Broker Settings
BROKER = '67eb329c985848aa8f600b2543575c8e.s1.eu.hivemq.cloud'
PORT = 8883
TOPIC = f"devicelogs/{DEVICE_ID}"
USERNAME = "test123"    # Add your EMQX username here
PASSWORD = "Test@123"    # Add your EMQX password here

# Set up logging only if debug is enabled
DEBUG = False  # Set this to True to enable debug logging

if DEBUG:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())

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
    logger.info(f"Message {mid} published successfully")

def on_log(client, userdata, level, buf):
    logger.debug(f"MQTT Log: {buf}")

def publish_message(message):
    try:
        # Using MQTT v5 protocol
        client = mqtt.Client(protocol=mqtt.MQTTv5)
        
        # Set up callbacks
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_publish = on_publish
        client.on_log = on_log
        
        # Enable SSL/TLS
        client.tls_set()
        
        # Set username and password
        client.username_pw_set(USERNAME, PASSWORD)
        
        logger.info(f"Attempting to connect to {BROKER}:{PORT}")
        client.connect(BROKER, PORT, keepalive=60)
        
        # Start the loop to process callbacks
        client.loop_start()
        
        logger.info(f"Attempting to publish message: {message}")
        result = client.publish(TOPIC, message)
        
        # Check if the message was published
        if result[0] == 0:
            logger.info(f"Message queued successfully. Message ID: {result[1]}")
        else:
            logger.error(f"Failed to publish message. Result code: {result[0]}")
        
        # Wait a moment for the publish to complete
        import time
        time.sleep(2)
        
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        logger.error(f"Error in publish_message: {str(e)}", exc_info=True)

def publish_log(message):
    print(message)
    publish_message(message)

if __name__ == "__main__":
    message = "Car detected at intersection at 10:45 AM"
    publish_message(message)
