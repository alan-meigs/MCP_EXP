# Terminal-based Chat Client with MCP Server Integration

This project demonstrates how to build a terminal-based chat client interface that connects to an MCP server and integrates with OpenAI's API. It includes a simple weather service as an example of MCP functionality.

## Prerequisites

- Python 3.8 or higher
- UV package manager (a fast, reliable Python package installer and resolver)

## Installation

### 1. Install UV

UV is a modern Python package manager that offers significant performance improvements over traditional tools like pip. It's written in Rust and provides:
- Faster package installation
- Reliable dependency resolution
- Built-in virtual environment management
- Compatible with existing Python tooling

To install UV, run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Project Setup

1. Initialize a new project:
```bash
uv init
```

2. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install required packages:
```bash
uv pip install httpx mcp[cli] openai python-dotenv
```

## Project Structure and Implementation Guide

The project consists of two main components: a chat client (`client.py`) and a weather service (`weather.py`). Let's walk through how each component was built and what each part does.

### Building the Chat Client (client.py)

The chat client is built as an asynchronous Python application that connects to both an MCP server and OpenAI's API. Here's how it was constructed:

1. **Imports and Setup**
   ```python
   import asyncio
   import os
   import sys
   from typing import Optional
   from contextlib import AsyncExitStack
   from dotenv import load_dotenv
   import openai
   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client
   ```
   - `asyncio`: For asynchronous programming
   - `AsyncExitStack`: Manages cleanup of async resources
   - `dotenv`: Loads environment variables from .env file
   - `mcp`: Core MCP functionality for server communication

2. **MCPClient Class**
   The main client class handles:
   - Connection to the MCP server
   - OpenAI API integration
   - Message processing
   - Tool execution

   Key methods:
   - `connect_to_server()`: Establishes connection to the MCP server
   - `process_query()`: Handles user queries and tool execution
   - `chat_loop()`: Manages the interactive chat session
   - `cleanup()`: Ensures proper resource cleanup

3. **Main Function**
   ```python
   async def main():
       client = MCPClient()
       try:
           await client.connect_to_server(sys.argv[1])
           await client.chat_loop()
       finally:
           await client.cleanup()
   ```
   - Entry point that initializes the client
   - Connects to the specified server
   - Runs the chat loop
   - Ensures proper cleanup

### Building the Weather Service (weather.py)

The weather service is built as an MCP server that provides weather information through the National Weather Service API:

1. **Service Initialization**
   ```python
   from mcp.server.fastmcp import FastMCP
   mcp = FastMCP("weather")
   ```
   - Creates an MCP server instance named "weather"
   - Sets up the server infrastructure

2. **API Integration**
   ```python
   NWS_API_BASE = "https://api.weather.gov"
   USER_AGENT = "weather-app/1.0"
   ```
   - Defines constants for the National Weather Service API
   - Sets up proper user agent for API requests

3. **Helper Functions**
   - `make_nws_request()`: Handles API requests with proper error handling
   - `format_alert()`: Formats weather alerts into readable text

4. **MCP Tools**
   Two main tools are implemented:
   
   a. `get_alerts(state)`:
   - Fetches active weather alerts for a US state
   - Returns formatted alert information
   
   b. `get_forecast(latitude, longitude)`:
   - Retrieves weather forecast for a location
   - Returns detailed forecast information

5. **Server Execution**
   ```python
   if __name__ == "__main__":
       mcp.run(transport="stdio")
   ```
   - Runs the MCP server using stdio transport
   - Enables communication with the chat client

## Usage

1. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

2. Start the MCP server:
```bash
python weather.py
```

3. In a separate terminal, run the chat client:
```bash
python client.py weather.py
```

4. Interact with the chat interface:
   - Ask general questions to chat with the AI
   - Use weather-related queries to get weather information
   - Example: "What's the weather in California?" or "Are there any alerts in New York?"

## Features

- Real-time chat interface with OpenAI integration
- MCP server integration for extensible functionality
- Weather service with alerts and forecasts
- Asynchronous operation for better performance
- Proper error handling and resource cleanup
- Environment variable configuration for API keys

## Contributing

Feel free to submit issues and enhancement requests!
