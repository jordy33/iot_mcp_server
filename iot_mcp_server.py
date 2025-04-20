from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from paho.mqtt.client import Client
import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class IoTContext:
    """Context for the IoT MCP server."""
    mqtt_client: Client

@asynccontextmanager
async def iot_lifespan(server: FastMCP) -> AsyncIterator[IoTContext]:
    """
    Manages the MQTT client lifecycle.
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        IoTContext: The context containing the MQTT client
    """
    # Initialize MQTT client
    mqtt_client = Client()
    broker_address = os.getenv("MQTT_BROKER", "localhost")
    broker_port = int(os.getenv("MQTT_PORT", "1883"))
    
    try:
        # Connect to the MQTT broker
        print(f"Connecting to MQTT broker at {broker_address}:{broker_port}")
        mqtt_client.connect(broker_address, broker_port)
        mqtt_client.loop_start()  # Start the MQTT client loop in a separate thread
        
        yield IoTContext(mqtt_client=mqtt_client)
    finally:
        # Clean up MQTT client connection
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("MQTT client disconnected")

# Initialize FastMCP server with the IoT context
mcp = FastMCP(
    "mcp-iot",
    description="MCP server for IoT device control",
    lifespan=iot_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=os.getenv("PORT", "8090")
)

@mcp.tool()
async def send_command(ctx: Context, device_id: str, command: str, payload: str = None) -> str:
    """Send a command to an IoT device.
    
    This tool sends commands to specific IoT devices via MQTT.
    
    Args:
        ctx: The MCP server provided context which includes the MQTT client
        device_id: The unique identifier for the target device
        command: The command to send (e.g., "toggle", "set_brightness", "restart")
        payload: Optional JSON payload with command parameters
    """
    try:
        mqtt_client = ctx.request_context.lifespan_context.mqtt_client
        topic = f"devices/{device_id}/command"
        
        # Prepare the message payload
        message = {
            "command": command,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Add payload if provided
        if payload:
            try:
                payload_data = json.loads(payload)
                message["payload"] = payload_data
            except json.JSONDecodeError:
                message["payload"] = payload
        
        # Publish the message to the MQTT topic
        result = mqtt_client.publish(topic, json.dumps(message))
        
        if result.rc == 0:
            return f"Command '{command}' successfully sent to device '{device_id}'"
        else:
            return f"Failed to send command: MQTT publish error code {result.rc}"
    except Exception as e:
        return f"Error sending command: {str(e)}"

@mcp.tool()
async def get_device_state(ctx: Context, device_id: str) -> str:
    """Get the current state of an IoT device.
    
    This tool retrieves the latest known state of a device.
    
    Args:
        ctx: The MCP server provided context which includes the MQTT client
        device_id: The unique identifier for the device
    """
    try:
        mqtt_client = ctx.request_context.lifespan_context.mqtt_client
        
        # In a real implementation, you would likely:
        # 1. Query a database for the latest device state
        # 2. Or use MQTT to request the current state and wait for a response
        
        # This is a placeholder implementation
        # In practice, you might send a state request and use a Future to wait for the response
        state_topic = f"devices/{device_id}/state/request"
        request_id = f"req-{asyncio.get_event_loop().time()}"
        
        request_payload = json.dumps({"request_id": request_id})
        mqtt_client.publish(state_topic, request_payload)
        
        # Normally, we would wait for the response here
        # For this example, we'll return a placeholder state
        
        # Placeholder state (in a real implementation, this would come from the device)
        placeholder_state = {
            "device_id": device_id,
            "online": True,
            "last_seen": "2025-04-20T22:20:00Z",
            "properties": {
                "temperature": 21.5,
                "humidity": 45,
                "battery": 78
            }
        }
        
        return json.dumps(placeholder_state, indent=2)
    except Exception as e:
        return f"Error getting device state: {str(e)}"

@mcp.tool()
async def subscribe_to_updates(ctx: Context, device_id: str, update_type: str = "all") -> str:
    """Subscribe to real-time updates from an IoT device.
    
    This tool sets up a subscription for device updates.
    
    Args:
        ctx: The MCP server provided context which includes the MQTT client
        device_id: The unique identifier for the device
        update_type: Type of updates to subscribe to (e.g., "all", "state", "telemetry")
    """
    try:
        mqtt_client = ctx.request_context.lifespan_context.mqtt_client
        
        # Determine which topic to subscribe to based on update_type
        if update_type == "all":
            topic = f"devices/{device_id}/#"
        else:
            topic = f"devices/{device_id}/{update_type}"
        
        # Define a callback for receiving messages
        def on_message(client, userdata, message):
            # In a real implementation, messages would be forwarded to the client
            # through SSE or another mechanism
            print(f"Received message on {message.topic}: {message.payload.decode()}")
        
        # Set the callback and subscribe
        mqtt_client.on_message = on_message
        result = mqtt_client.subscribe(topic)
        
        if result[0] == 0:
            return f"Successfully subscribed to {update_type} updates for device {device_id}"
        else:
            return f"Failed to subscribe: MQTT error code {result[0]}"
    except Exception as e:
        return f"Error subscribing to updates: {str(e)}"

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