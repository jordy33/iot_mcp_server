# MCP Servers for IoT and Memory Management

This repository contains two Model Context Protocol (MCP) servers:
1. IoT Device Control MCP Server
2. Memory Management MCP Server

## IoT Device Control MCP Server

A Model Context Protocol (MCP) server for controlling and monitoring IoT devices such as smart lights, sensors, and other connected devices.

### Purpose

This server provides a standardized interface for IoT device control, monitoring, and state management through the Model Context Protocol.

### Use Cases

- Home automation
- Industrial IoT monitoring
- Remote device management
- Smart building control systems

### Features

- Send commands to IoT devices
- Query device state and status
- Subscribe to real-time device updates
- Support for MQTT protocol

### API Tools

- `send_command`: Send a command to an IoT device
- `get_device_state`: Get the current state of an IoT device
- `subscribe_to_updates`: Subscribe to real-time updates from a device

## Memory Management MCP Server

A Model Context Protocol (MCP) server for persistent memory storage and retrieval using the Mem0 framework.

### Purpose

This server enables long-term memory storage and semantic search capabilities through the Model Context Protocol.

### Use Cases

- Conversation history storage
- Knowledge management
- Contextual awareness in AI applications
- Persistent information storage

### Features

- Save information to long-term memory
- Retrieve all stored memories
- Search memories using semantic search

### API Tools

- `save_memory`: Save information to long-term memory
- `get_all_memories`: Get all stored memories for the user
- `search_memories`: Search memories using semantic search

## Getting Started

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file based on the `.env.example` template
4. Run the IoT server: `python iot_mcp_server.py`
5. Run the Memory server: `python memory_mcp_server.py`

## Environment Variables

### IoT MCP Server
- `MQTT_BROKER`: MQTT broker address (default: "localhost")
- `MQTT_PORT`: MQTT broker port (default: 1883)
- `HOST`: Server host address (default: "0.0.0.0")
- `PORT`: Server port (default: "8090")
- `TRANSPORT`: Transport type, "sse" or "stdio" (default: "sse")

### Memory MCP Server
- `MEM0_API_KEY`: API key for Mem0 service (optional)
- `MEM0_ENDPOINT`: Endpoint URL for Mem0 service (default: "https://api.mem0.ai")
- `HOST`: Server host address (default: "0.0.0.0")
- `PORT`: Server port (default: "8050")
- `TRANSPORT`: Transport type, "sse" or "stdio" (default: "sse")

## Repository Structure

- `iot_mcp_server.py` - IoT device control MCP server implementation
- `memory_mcp_server.py` - Memory management MCP server implementation
- `utils.py` - Utility functions used by the servers
- `requirements.txt` - Package dependencies
- `.env.example` - Template for environment variables configuration
- `README.md` - Documentation