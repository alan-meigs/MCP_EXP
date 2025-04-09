import asyncio
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack
from dotenv import load_dotenv
import openai

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# =====================================================
# 💬 CHAT CLIENT WITH MCP SERVER INTEGRATION
# =====================================================
# This file creates a terminal-based chat client that:
# 1. Connects to an MCP server (like our weather service)
# 2. Integrates with OpenAI's API for natural language processing
# 3. Allows users to chat with an AI that can use the MCP tools
# =====================================================

# Load environment variables from .env file
# This is where we store sensitive information like API keys
load_dotenv()
openai.api_key = os.getenv("ALAN_API_KEY")

class MCPClient:
    """
    A client that connects to an MCP server and OpenAI's API.
    
    This class manages:
    - Connection to the MCP server
    - Communication with OpenAI
    - Processing user queries
    - Executing MCP tools
    - Managing the chat session
    """
    def __init__(self):
        # AsyncExitStack helps us manage async resources properly
        # It ensures everything gets cleaned up when we're done
        self.exit_stack = AsyncExitStack()

        # We'll store our MCP session here after connecting
        self.session: Optional[ClientSession] = None

    async def connect_to_server(self, server_script_path: str):
        """
        Launch and connect to an MCP server over stdio transport.
        
        This function:
        1. Determines how to run the server script (Python or Node.js)
        2. Sets up the stdio transport for communication
        3. Initializes the MCP session
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        # Figure out which command to use based on the file extension
        if server_script_path.endswith('.py'):
            command = "python"
        elif server_script_path.endswith('.js'):
            command = "node"
        else:
            raise ValueError("Server script must end in .py or .js")

        # Create parameters for the stdio server
        # These tell the client how to launch and communicate with the server
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        # Establish stdio transport to server
        # This creates a two-way communication channel with the server
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

        # Initialize MCP session
        # This sets up the protocol for communicating with the server
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # Show available tools
        # This helps users know what capabilities are available
        response = await self.session.list_tools()
        tool_names = [tool.name for tool in response.tools]
        print("\n✅ Connected to server with tools:", tool_names)

    async def process_query(self, query: str) -> str:
        """
        Send a user query to OpenAI with tool descriptions,
        handle tool calls if returned, and display the final response.
        
        This function:
        1. Sends the user's query to OpenAI
        2. If OpenAI wants to use a tool, executes it via MCP
        3. Sends the tool result back to OpenAI
        4. Returns the final response
        
        Args:
            query: The user's input text
            
        Returns:
            The assistant's response text
        """
        # Start with the user's query
        messages = [
            {"role": "user", "content": query}
        ]

        # Get the list of tools from the MCP server
        # We need to convert these to OpenAI's function-calling format
        response = await self.session.list_tools()
        tools = response.tools
        openai_tools = []

        # Convert each MCP tool to OpenAI's format
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })

        # Call OpenAI with the query and available tools
        # This allows OpenAI to decide if it needs to use any tools
        completion = openai.chat.completions.create(
            model="gpt-4o",  
            messages=messages,
            tools=openai_tools,
            tool_choice="auto"  # Let OpenAI decide if it needs to use tools
        )

        # Get OpenAI's response
        assistant_message = completion.choices[0].message
        final_text = []

        # If OpenAI wants to use a tool, execute it
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                # Extract the tool name and arguments
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments

                # Parse the JSON arguments
                import json
                parsed_args = json.loads(tool_args)

                # Execute the tool via MCP session
                # This is where we actually call our weather service functions
                result = await self.session.call_tool(tool_name, parsed_args)

                # Add the tool call and result to the conversation
                # This helps OpenAI understand what happened
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tool_args
                        }
                    }]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": result.content
                })

                # Send the updated conversation back to OpenAI
                # This allows it to incorporate the tool result into its response
                completion = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                assistant_message = completion.choices[0].message
                if assistant_message.content:
                    final_text.append(assistant_message.content)
        else:
            # If OpenAI didn't use any tools, just use its direct response
            if assistant_message.content:
                final_text.append(assistant_message.content)

        # Join any multiple responses and return
        return "\n".join(final_text)

    async def chat_loop(self):
        """
        Start an interactive command-line chat session.
        
        This function:
        1. Displays a welcome message
        2. Repeatedly asks for user input
        3. Processes each query and displays the response
        4. Continues until the user types 'quit'
        """
        print("\n💬 MCP Client (OpenAI) Started!")
        print("Type a query or 'quit' to exit.")

        # Main chat loop
        while True:
            # Get user input
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break

            try:
                # Process the query and display the response
                response = await self.process_query(query)
                print("\n🧠 Assistant:\n" + response)
            except Exception as e:
                # Handle any errors that occur
                print(f"\n❌ Error: {e}")

    async def cleanup(self):
        """
        Close the MCP session and other resources.
        
        This ensures everything is properly cleaned up when we're done.
        """
        await self.exit_stack.aclose()

# Main function to launch the client
async def main():
    """
    Entry point for the application.
    
    This function:
    1. Checks for command-line arguments
    2. Creates and initializes the client
    3. Connects to the server
    4. Runs the chat loop
    5. Ensures proper cleanup
    """
    # Check if a server script was provided
    # This program expects to run the client and any additional servers so the expected run script is :
    # uv run client.py path/to/server.py path/to/additional/server.py
    if len(sys.argv) < 2:
        print("Usage: uv run client.py path/to/server.py path/to/additional/server.py")
        print("Example: uv run client.py server.py additional_server.py")
        sys.exit(1)

    # Create the client
    client = MCPClient()
    try:
        # Connect to the server and start the chat loop
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        # Always clean up, even if there's an error
        await client.cleanup()

# Run the main function when this script is executed
if __name__ == "__main__":#
    # asyncio.run() is needed to run async code in the main thread
    asyncio.run(main())
