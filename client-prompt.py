import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Set up the server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"]
    )

    # Connect to the MCP server via stdio
    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as sess:
            await sess.initialize()

            # Prompt for symptoms input
            symptoms = input("Please describe your symptoms: ")

            # Correct method to call a prompt
            prompt_text = await sess.get_prompt("assess_symptoms", arguments={
                "symptoms": symptoms
            })

            # Display the generated prompt
            print("\nGenerated prompt to be sent to the model:")
            print("------------------------------------------")
            print(prompt_text)

if __name__ == "__main__":
    asyncio.run(main())
