# IoT Device Control MCP Server

A Model Context Protocol (MCP) server for controlling and monitoring IoT devices such as smart lights, sensors, and other connected devices.

## Purpose

This server provides a standardized interface for IoT device control, monitoring, and state management through the Model Context Protocol.

## Use Cases

- Home automation
- Industrial IoT monitoring
- Remote device management
- Smart building control systems

## Features

- Send commands to IoT devices
- Query device state and status
- Subscribe to real-time device updates
- Support for MQTT protocol

## Getting Started

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your MQTT broker in `.env` file
4. Run the server: `python iot_mcp_server.py`

## Environment Variables

- `MQTT_BROKER`: MQTT broker address (default: "localhost")
- `HOST`: Server host address (default: "0.0.0.0")
- `PORT`: Server port (default: "8090")
- `TRANSPORT`: Transport type, "sse" or "stdio" (default: "sse")

## API Tools

- `send_command`: Send a command to an IoT device
- `get_device_state`: Get the current state of an IoT device
- `subscribe_to_updates`: Subscribe to real-time updates from a device