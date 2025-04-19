# resource.py

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Launch the MCP server over stdio
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=None
    )

    # Open a session, ask for name, and print greeting
    # The `stdio_client` context manager provides the reader and writer streams
    async with stdio_client(server_params) as (reader, writer):
        # The `ClientSession` context manager initializes the session
        async with ClientSession(reader, writer) as sess:
            await sess.initialize()

            # Prompt for the user's name
            name = input("Please enter your name: ")

            # Fetch and display greeting resource
            # FIX: Remove the 'arguments' keyword argument.
            # The 'name' is passed as part of the resource URI itself
            # and the server's resource definition expects it there.
            greeting = await sess.read_resource(
                f"greeting://patient/{name}"
            )
            print(greeting)

if __name__ == "__main__":
    # Run the asyncio event loop
    asyncio.run(main())