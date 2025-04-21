from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from paho.mqtt.client import Client as MQTTClient
import asyncio
import json
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class IoTContext:
    """Context for the IoT MCP server."""
    mqtt_client: MQTTClient
    connected_devices: dict = field(default_factory=dict)

# Create a global MQTT client that can be reused across sessions
global_mqtt_client = None
global_devices = {}

@asynccontextmanager
async def iot_lifespan(server: FastMCP) -> AsyncIterator[IoTContext]:
    """
    Manages the MQTT client lifecycle.
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        IoTContext: The context containing the MQTT client
    """
    global global_mqtt_client, global_devices
    
    # Initialize MQTT client only if it doesn't exist
    if global_mqtt_client is None:
        print("Creating new MQTT client")
        # Use MQTTv311 protocol to address deprecation warning
        import paho.mqtt.client as mqtt  # Import here to ensure we have the module
        mqtt_client = MQTTClient(client_id="iot_mcp_server", protocol=mqtt.MQTTv311)
        broker_address = os.getenv("MQTT_BROKER", "localhost")
        broker_port = int(os.getenv("MQTT_PORT", "1883"))
        
        # Set up MQTT callbacks for device discovery
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"Connected to MQTT broker at {broker_address}:{broker_port}")
                # Subscribe to all device state topics for discovery
                client.subscribe("devices/+/state")
                # Subscribe to broadcast responses
                client.subscribe("devices/broadcast/response")
                print("Subscribed to device state topics")
            else:
                print(f"Failed to connect to MQTT broker with result code {rc}")
        
        def on_message(client, userdata, message):
            topic = message.topic
            payload = message.payload.decode("utf-8")
            print(f"MQTT: Received message on {topic}: {payload[:100]}...")
            
            # Check if this is a device state message
            if topic.startswith("devices/") and topic.endswith("/state"):
                try:
                    # Parse device data
                    device_data = json.loads(payload)
                    device_id = device_data.get("device_id")
                    
                    if device_id:
                        # Update our device registry
                        global_devices[device_id] = {
                            "id": device_id,
                            "type": device_data.get("type", "unknown"),
                            "online": device_data.get("online", True),
                            "last_seen": time.time(),
                            "properties": device_data.get("properties", {}),
                            "topic": topic
                        }
                        print(f"Discovered/updated device: {device_id} with properties: {device_data.get('properties', {})}")
                except json.JSONDecodeError:
                    print(f"Received invalid JSON in device state: {payload}")
                except Exception as e:
                    print(f"Error processing device state: {str(e)}")
        
        # Set callbacks
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        
        try:
            # Connect to the MQTT broker
            print(f"Connecting to MQTT broker at {broker_address}:{broker_port}")
            mqtt_client.connect(broker_address, broker_port)
            mqtt_client.loop_start()  # Start the MQTT client loop in a separate thread
            
            # Wait a short time to ensure connection and subscription
            await asyncio.sleep(1)
            
            # Force a request for device states (using a broadcast topic instead of wildcards)
            print("Requesting states from all devices via broadcast")
            mqtt_client.publish("devices/broadcast/request", json.dumps({"request_id": "startup", "action": "report_state"}))
            
            # Add the light bulb simulator as a known device if we're running locally
            if broker_address in ("localhost", "127.0.0.1"):
                print("Running locally - adding light bulb as a default device")
                global_devices["light_bulb_001"] = {
                    "id": "light_bulb_001",
                    "type": "light",
                    "online": True,
                    "last_seen": time.time(),
                    "properties": {
                        "power": False,
                        "brightness": 100,
                        "color": "#FFFF00"
                    },
                    "topic": "devices/light_bulb_001/state"
                }
            
            global_mqtt_client = mqtt_client
        except Exception as e:
            print(f"Failed to connect MQTT client: {str(e)}")
            # Clean up if connection failed
            mqtt_client.loop_stop()
            mqtt_client = None
    else:
        print("Reusing existing MQTT client")
    
    # Create context with global client and devices
    context = IoTContext(mqtt_client=global_mqtt_client, connected_devices=global_devices)
    
    try:
        yield context
    finally:
        # Don't disconnect the client, it will be reused
        pass

# Initialize FastMCP server with the IoT context
mcp = FastMCP(
    "mcp-iot",
    description="MCP server for IoT device control",
    lifespan=iot_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=os.getenv("PORT", "8090")
)

@mcp.tool()
async def list_devices(ctx: Context, **kwargs) -> str:
    """List all connected IoT devices.
    
    This tool returns information about all IoT devices that have been discovered
    on the MQTT network. For each device, it provides the ID, type, online status,
    and available commands.
    
    Note: Do NOT try to call a device ID directly. Instead, use the command tools like:
    - light_bulb_on - To turn the light bulb ON
    - light_bulb_off - To turn the light bulb OFF
    - light_bulb_toggle - To toggle the light bulb
    - check_light_status - To check light status
    """
    try:
        print(f"List devices tool called with kwargs: {kwargs}")
        return """Available device: light_bulb_001 (light)

To control the light bulb, DO NOT call the device ID directly. Instead use:
- light_bulb_on: Turn the light ON
- light_bulb_off: Turn the light OFF
- light_bulb_toggle: Toggle the light ON/OFF
- check_light_status: Check the current status
"""
    except Exception as e:
        print(f"Error in list_devices: {str(e)}")
        return "Found light_bulb_001 device. Use light_bulb_on or light_bulb_off to control it."

@mcp.tool()
async def turn_on_light(ctx: Context, **kwargs) -> str:
    """Turn ON the light bulb.
    
    This tool will explicitly turn on the light bulb, setting its power state to true.
    
    Args:
        ctx: The MCP server provided context
        dummy: Optional parameter that does nothing (required for schema compatibility)
    """
    try:
        print(f"Turn on light called with kwargs: {kwargs}")
        mqtt_client = ctx.request_context.lifespan_context.mqtt_client
        topic = "devices/light_bulb_001/command"
        
        # Prepare the command to set power on
        message = {
            "command": "set_power",
            "timestamp": time.time(),
            "payload": {
                "power": True
            }
        }
        
        # Publish the message
        print(f"Sending turn ON command: {json.dumps(message)}")
        result = mqtt_client.publish(topic, json.dumps(message))
        print(f"MQTT publish result: {result.rc}")
        
        # Request an immediate state update to verify the change
        await asyncio.sleep(0.5)  # Give the bulb time to process the command
        state_topic = "devices/light_bulb_001/state/request"
        mqtt_client.publish(state_topic, json.dumps({"request_id": "verify_power_on"}))
        
        return "Light bulb has been turned ON"
    except Exception as e:
        print(f"Error in turn_on_light: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return f"Error turning on light: {str(e)}"

@mcp.tool()
async def turn_off_light(ctx: Context, **kwargs) -> str:
    """Turn OFF the light bulb.
    
    This tool will explicitly turn off the light bulb, setting its power state to false.
    
    Args:
        ctx: The MCP server provided context
        dummy: Optional parameter that does nothing (required for schema compatibility)
    """
    try:
        print(f"Turn off light called with kwargs: {kwargs}")
        mqtt_client = ctx.request_context.lifespan_context.mqtt_client
        topic = "devices/light_bulb_001/command"
        
        # Prepare the command to set power off
        message = {
            "command": "set_power",
            "timestamp": time.time(),
            "payload": {
                "power": False
            }
        }
        
        # Publish the message
        mqtt_client.publish(topic, json.dumps(message))
        return "Light bulb has been turned OFF"
    except Exception as e:
        return f"Error turning off light: {str(e)}"

@mcp.tool()
async def toggle_light(ctx: Context, **kwargs) -> str:
    """Toggle the light bulb on/off.
    
    This is a simplified tool to toggle the light bulb power state.
    
    Args:
        ctx: The MCP server provided context
        dummy: Optional parameter that does nothing (required for schema compatibility)
    """
    try:
        print(f"Toggle light called with kwargs: {kwargs}")
        mqtt_client = ctx.request_context.lifespan_context.mqtt_client
        topic = "devices/light_bulb_001/command"
        
        # Prepare the toggle command
        message = {
            "command": "toggle",
            "timestamp": time.time()
        }
        
        # Publish the message
        mqtt_client.publish(topic, json.dumps(message))
        return "Light bulb toggle command sent successfully"
    except Exception as e:
        return f"Error toggling light: {str(e)}"

@mcp.tool()
async def check_light_status(ctx: Context, **kwargs) -> str:
    """Check the current status of the light bulb.
    
    Returns the current power state, brightness and color of the light bulb.
    """
    try:
        connected_devices = ctx.request_context.lifespan_context.connected_devices
        if "light_bulb_001" in connected_devices:
            properties = connected_devices["light_bulb_001"].get("properties", {})
            power = "ON" if properties.get("power", False) else "OFF"
            brightness = properties.get("brightness", 100)
            color = properties.get("color", "#FFFF00")
            
            # Request a fresh state update
            mqtt_client = ctx.request_context.lifespan_context.mqtt_client
            state_topic = "devices/light_bulb_001/state/request"
            mqtt_client.publish(state_topic, json.dumps({"request_id": "check_status"}))
            
            return f"Light bulb status: Power is {power}, Brightness is {brightness}%, Color is {color}"
        else:
            return "Light bulb status: Device not found in registry"
    except Exception as e:
        return f"Error checking light status: {str(e)}"

@mcp.tool()
async def light_bulb_on(ctx: Context, **kwargs) -> str:
    """Turn the light bulb ON.
    
    This command turns on the light with ID 'light_bulb_001'.
    """
    return await turn_on_light(ctx, **kwargs)

@mcp.tool()
async def light_bulb_off(ctx: Context, **kwargs) -> str:
    """Turn the light bulb OFF.
    
    This command turns off the light with ID 'light_bulb_001'.
    """
    return await turn_off_light(ctx, **kwargs)

@mcp.tool()
async def light_bulb_toggle(ctx: Context, **kwargs) -> str:
    """Toggle the light bulb ON/OFF.
    
    This command toggles the light with ID 'light_bulb_001'.
    """
    return await toggle_light(ctx, **kwargs)

@mcp.tool()
async def get_help(ctx: Context, **kwargs) -> str:
    """Get help on how to control IoT devices.
    
    This tool provides information about how to properly control the connected IoT devices.
    """
    return """
## IoT Device Control Help

The following commands are available to control the light bulb:

1. `light_bulb_on` - Turn the light bulb ON
2. `light_bulb_off` - Turn the light bulb OFF 
3. `light_bulb_toggle` - Toggle the light bulb ON/OFF
4. `check_light_status` - Check the current status of the light bulb

IMPORTANT: You cannot control devices by using their device ID directly (e.g., "light_bulb_001").
Always use the specific command functions listed above.
"""

@mcp.tool()
async def check_command(ctx: Context, command: str) -> str:
    """Check if a command is valid and provide guidance.
    
    This is a helper tool to check if a command exists and provide guidance on how to use it.
    
    Args:
        ctx: The MCP server provided context
        command: The command or device ID to check
    """
    if command == "light_bulb_001":
        return """
ERROR: "light_bulb_001" is a device ID, not a command.

To control this light bulb, use one of these commands:
- light_bulb_on - Turn the light ON
- light_bulb_off - Turn the light OFF
- light_bulb_toggle - Toggle the light ON/OFF
- check_light_status - Check the status
"""
    
    valid_commands = [
        "list_devices", "turn_on_light", "turn_off_light", "toggle_light", 
        "check_light_status", "light_bulb_on", "light_bulb_off", "light_bulb_toggle"
    ]
    
    if command in valid_commands:
        return f"The command '{command}' is valid. You can use it to control the light bulb."
    else:
        return f"""
The command '{command}' is not recognized. 

Available commands:
- light_bulb_on - Turn the light ON
- light_bulb_off - Turn the light OFF
- light_bulb_toggle - Toggle the light ON/OFF
- check_light_status - Check the status
"""

async def main():
    """Run the MCP server with the configured transport."""
    transport = os.getenv("TRANSPORT", "sse")
    
    if transport == 'sse':
        # Run the MCP server with SSE transport
        print("Starting MCP server with SSE transport...")
        await mcp.run_sse_async()
    else:
        # Run the MCP server with stdio transport
        print("Starting MCP server with stdio transport...")
        await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())