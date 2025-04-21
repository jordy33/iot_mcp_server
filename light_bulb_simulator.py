from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json
import threading
import logging
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# MQTT Settings
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DEVICE_ID = "light_bulb_001"
COMMAND_TOPIC = f"devices/{DEVICE_ID}/command"
STATE_TOPIC = f"devices/{DEVICE_ID}/state"
STATE_REQUEST_TOPIC = f"devices/{DEVICE_ID}/state/request"

# Global device state
device_state = {
    "device_id": DEVICE_ID,
    "type": "light",  # Add device type
    "online": True,
    "last_seen": None,
    "properties": {
        "power": False,  # False is off, True is on
        "brightness": 100,
        "color": "#FFFF00"  # Yellow light
    }
}

# Initialize MQTT client with protocol version parameter to address deprecation warning
mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)

# Set up MQTT callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        # Subscribe to command topic
        client.subscribe(COMMAND_TOPIC)
        client.subscribe(STATE_REQUEST_TOPIC)
        # Subscribe to broadcast requests
        client.subscribe("devices/broadcast/request")
        # Publish initial state immediately after connection
        publish_state()
    else:
        logger.error(f"Failed to connect to MQTT broker with result code {rc}")

def on_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode("utf-8")
    logger.info(f"Received message on {topic}: {payload}")
    
    try:
        # Handle command messages
        if topic == COMMAND_TOPIC:
            handle_command(payload)
        # Handle state request messages
        elif topic == STATE_REQUEST_TOPIC:
            publish_state()
        # Handle broadcast requests
        elif topic == "devices/broadcast/request":
            # Parse the message
            msg_data = json.loads(payload)
            action = msg_data.get("action")
            
            # If action is to report state, publish our state
            if action == "report_state":
                logger.info(f"Responding to broadcast request: {msg_data.get('request_id')}")
                publish_state()
                
                # Also publish to the broadcast response topic
                response = {
                    "device_id": DEVICE_ID,
                    "response_to": msg_data.get("request_id"),
                    "state": device_state
                }
                mqtt_client.publish("devices/broadcast/response", json.dumps(response))
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

def handle_command(payload_str):
    try:
        payload = json.loads(payload_str)
        command = payload.get("command")
        
        logger.info(f"Processing command: {command} with payload: {payload_str}")
        
        if command == "toggle":
            # Toggle power state
            device_state["properties"]["power"] = not device_state["properties"]["power"]
            logger.info(f"Toggled light bulb power to: {device_state['properties']['power']}")
        
        elif command == "set_power" and "payload" in payload:
            # Set power state directly
            power_state = payload["payload"].get("power", False)
            old_state = device_state["properties"]["power"]
            device_state["properties"]["power"] = bool(power_state)
            logger.info(f"Set light bulb power from {old_state} to {device_state['properties']['power']}")
        
        elif command == "set_brightness" and "payload" in payload:
            # Set brightness
            brightness = payload["payload"].get("brightness", 100)
            device_state["properties"]["brightness"] = max(0, min(100, int(brightness)))
            logger.info(f"Set light bulb brightness to: {device_state['properties']['brightness']}")
        
        elif command == "set_color" and "payload" in payload:
            # Set color
            color = payload["payload"].get("color")
            if color:
                device_state["properties"]["color"] = color
                logger.info(f"Set light bulb color to: {device_state['properties']['color']}")
        else:
            logger.warning(f"Unknown command or missing payload: {command}")
        
        # Publish updated state
        publish_state()
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON payload: {payload_str}")
    except Exception as e:
        logger.error(f"Error handling command: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def publish_state():
    """Publish current state to MQTT"""
    try:
        # Update last_seen timestamp
        device_state["last_seen"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        mqtt_client.publish(STATE_TOPIC, json.dumps(device_state))
        logger.info(f"Published state: {json.dumps(device_state)}")
    except Exception as e:
        logger.error(f"Error publishing state: {str(e)}")

# Heartbeat function to periodically publish state
def heartbeat():
    while True:
        try:
            publish_state()
        except Exception as e:
            logger.error(f"Error in heartbeat: {str(e)}")
        time.sleep(60)  # Publish state every 60 seconds

# Routes
@app.route('/')
def index():
    return render_template('index.html', device_state=device_state)

@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify(device_state)

@app.route('/api/toggle', methods=['POST'])
def toggle_light():
    device_state["properties"]["power"] = not device_state["properties"]["power"]
    publish_state()
    return jsonify({"success": True, "power": device_state["properties"]["power"]})

@app.route('/api/brightness', methods=['POST'])
def set_brightness():
    data = request.json
    brightness = data.get('brightness', 100)
    device_state["properties"]["brightness"] = max(0, min(100, int(brightness)))
    publish_state()
    return jsonify({"success": True, "brightness": device_state["properties"]["brightness"]})

@app.route('/api/color', methods=['POST'])
def set_color():
    data = request.json
    color = data.get('color', "#FFFF00")
    device_state["properties"]["color"] = color
    publish_state()
    return jsonify({"success": True, "color": device_state["properties"]["color"]})

def start_mqtt():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {str(e)}")

if __name__ == '__main__':
    # Start MQTT client in a separate thread
    mqtt_thread = threading.Thread(target=start_mqtt)
    mqtt_thread.daemon = True
    mqtt_thread.start()
    
    # Start heartbeat in a separate thread
    heartbeat_thread = threading.Thread(target=heartbeat)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()
    
    # Give MQTT client time to connect and publish initial state
    time.sleep(2)
    
    # Start Flask web server
    app.run(host='0.0.0.0', port=7003, debug=True, use_reloader=False)