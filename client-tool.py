# client-tool.py
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

async def main():
    server_params = StdioServerParameters(command="python", args=["server.py"])
    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            # Call the chat tool
            user_msg = "Hello, how are you today?"
            response = await session.call_tool("chat", arguments={"query": user_msg})
            print("Bot:", response)

if __name__ == "__main__":
    asyncio.run(main())