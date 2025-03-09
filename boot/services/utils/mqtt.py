import paho.mqtt.client as mqtt
import logging
from utils import get_cpu_serial
import json
from datetime import datetime
import sys
import os
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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)  # This ensures logs go to stdout
        ]
    ) # Set to CRITICAL to disable INFO, WARNING, and DEBUG logs


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

def on_message(client, userdata, message):
    logger.info(f"Received message on topic {message.topic}:\n{message.payload}")

class MQTTClient:
    _instance = None
    _is_connected = False
    _subscribed_topics = set()
    _connection_attempts = 0
    MAX_RETRIES = 2

    @staticmethod
    def get_instance(force_new=False):
        if MQTTClient._instance is None or force_new:
            if force_new:
                logger.info("Creating new MQTT client instance...")
                # Clean up old instance if it exists
                if MQTTClient._instance is not None:
                    try:
                        MQTTClient._instance.loop_stop()
                        MQTTClient._instance.disconnect()
                    except:
                        pass
            
            MQTTClient._instance = mqtt.Client(protocol=mqtt.MQTTv5)
            client = MQTTClient._instance
            MQTTClient._is_connected = False
            
            # Set up callbacks
            client.on_connect = lambda client, userdata, flags, rc, properties=None: MQTTClient._on_connect(client, userdata, flags, rc, properties)
            client.on_disconnect = on_disconnect
            client.on_publish = on_publish
            client.on_log = on_log
            client.on_message = on_message
            
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
        """Wait for the connection to be established with retry logic"""
        import time
        start_time = time.time()
        
        while not MQTTClient._is_connected:
            if time.time() - start_time > timeout:
                MQTTClient._connection_attempts += 1
                if MQTTClient._connection_attempts <= MQTTClient.MAX_RETRIES:
                    logger.warning(f"Connection attempt {MQTTClient._connection_attempts} failed. Creating new instance...")
                    # Get a new instance and reset the timer
                    MQTTClient.get_instance(force_new=True)
                    start_time = time.time()
                else:
                    MQTTClient._connection_attempts = 0  # Reset for next time
                    raise TimeoutError("Connection timeout after all retries")
            time.sleep(0.1)
        
        MQTTClient._connection_attempts = 0  # Reset on successful connection

    @staticmethod
    def subscribe(topic, qos=1, message_handler=None):
        """Subscribe to a topic"""
        try:
            client = MQTTClient.get_instance()
            
            # Wait for connection before subscribing
            try:
                MQTTClient.wait_for_connection()
            except TimeoutError:
                logger.error("Timed out waiting for MQTT connection")
                return False
                
            result = client.subscribe(topic, qos)
            if result[0] == 0:
                logger.info(f"Successfully subscribed to topic: {topic}")
                MQTTClient._subscribed_topics.add(topic)
                
                if message_handler:
                    client.message_callback_add(topic, message_handler)
                return True
            else:
                logger.error(f"Failed to subscribe to topic {topic}. Result code: {result[0]}")
                return False
                
        except Exception as e:
            logger.error(f"Error in subscribe: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def unsubscribe(topic):
        """Unsubscribe from a topic"""
        try:
            client = MQTTClient.get_instance()
            result = client.unsubscribe(topic)
            if result[0] == 0:
                logger.info(f"Successfully unsubscribed from topic: {topic}")
                MQTTClient._subscribed_topics.remove(topic)
                return True
            else:
                logger.error(f"Failed to unsubscribe from topic {topic}. Result code: {result[0]}")
                return False
        except Exception as e:
            logger.error(f"Error in unsubscribe: {str(e)}", exc_info=True)
            return False

def publish_message(message, topic=TOPIC):
    try:
        client = MQTTClient.get_instance()
        
        # Wait for connection before publishing
        try:
            MQTTClient.wait_for_connection()
        except TimeoutError:
            logger.error("Timed out waiting for MQTT connection")
            return
            
        # Convert message to JSON-compatible dict if it's not already
        if isinstance(message, str):
            try:
                # Check if the string is already valid JSON
                msg_dict = json.loads(message)
            except json.JSONDecodeError:
                # If not JSON, create a new JSON object
                msg_dict = {
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
        else:
            # If message is dict or other type, convert to JSON-compatible dict
            if isinstance(message, dict):
                msg_dict = message.copy()  # Create a copy to avoid modifying original
                msg_dict["timestamp"] = datetime.now().isoformat()
            else:
                msg_dict = {
                    "message": str(message),
                    "timestamp": datetime.now().isoformat()
                }
        
        # Pretty print for logging
        logger.info(f"Attempting to publish message to {topic}:\n{json.dumps(msg_dict, indent=2)}")
        
        # Convert to compact JSON string for publishing
        msg_str = json.dumps(msg_dict)
        result = client.publish(topic, msg_str)
        
        # Check if the message was published
        if result[0] == 0:
            logger.debug(f"Message queued successfully. Message ID: {result[1]}")
        else:
            logger.error(f"Failed to publish message. Result code: {result[0]}")
            
    except Exception as e:
        logger.error(f"Error in publish_message: {str(e)}", exc_info=True)

def publish_log(message, topic):
    publish_message(message, f"{topic}/{DEVICE_ID}")

def subscribe_to_topic(topic, message_handler):
    MQTTClient.subscribe(f"{topic}/{DEVICE_ID}", 0, message_handler)

def publish_log_to_system_topic(message):
    print(message, "system")

if __name__ == "__main__":
    # Example of publishing and subscribing
    test_topic = "ffmpeg-stream"
    
    # Subscribe to test topic
    subscribe_to_topic(test_topic,publish_log_to_system_topic)
    
    # Publish a test message
    message = "Car detected at intersection at 10:45 AM"
    publish_message(message, test_topic)
    
    # Keep the program running to receive messages
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        MQTTClient.unsubscribe(test_topic)
