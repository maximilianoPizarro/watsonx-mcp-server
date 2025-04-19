# client-flow.py

import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure basic logging for the client
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] CLIENT: %(message)s"
)

async def main():
    # 1. Setup Server Connection Parameters
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=None
    )

    logging.info("Attempting to connect to the MCP server via stdio...")

    try:
        # 2. Establish Connection and Session
        async with stdio_client(server_params) as (reader, writer):
            logging.info("Stdio streams established.")
            async with ClientSession(reader, writer) as sess:
                logging.info("Initializing MCP session...")
                await sess.initialize()
                logging.info("MCP Session initialized successfully.")

                # --- Step 1: Get Name and Fetch Greeting Resource ---
                name = input("Please enter your name: ")
                resource_uri = f"greeting://patient/{name}"
                try:
                    logging.info(f"Fetching greeting resource for name: {name}")
                    greeting = await sess.read_resource(resource_uri)
                    print(f"\nServer: {greeting}")
                except Exception as e:
                    logging.error(f"Error fetching greeting '{resource_uri}': {e}", exc_info=True)
                    print(f"Error: Could not fetch greeting. {e}")
                    return

                # --- Step 2: Get Symptoms and Generate Prompt ---
                symptoms = input("Please describe your symptoms: ")
                try:
                    logging.info("Requesting 'assess_symptoms' prompt generation.")
                    prompt_resp = await sess.get_prompt(
                        "assess_symptoms",
                        arguments={"symptoms": symptoms}
                    )

                    # --- EXTRACT the raw text from the PromptResponse ---
                    # Most PromptResponse objects have a `.messages` list of PromptMessage,
                    # each with a `.content.text` field.
                    msgs = getattr(prompt_resp, 'messages', None)
                    if msgs:
                        pieces = []
                        for m in msgs:
                            # m.content may be a TextContent or a plain string
                            content = getattr(m, 'content', m)
                            text = getattr(content, 'text', content)
                            # If the first line looks like a module repr, drop it
                            if text.startswith("<module"):
                                text = text.split("\n", 1)[1]
                            pieces.append(text)
                        diagnosis_prompt = "\n".join(pieces).strip()
                    else:
                        # fallback to description or raw repr
                        diagnosis_prompt = getattr(prompt_resp, 'description', str(prompt_resp))

                    print("\nGenerated prompt (to be sent to AI):")
                    print("---------------------------------------")
                    print(diagnosis_prompt)
                    print("---------------------------------------")
                    logging.info("Successfully parsed diagnosis prompt.")

                except Exception as e:
                    logging.error(f"Error generating prompt 'assess_symptoms': {e}", exc_info=True)
                    print(f"Error: Could not generate the diagnosis prompt. {e}")
                    return

                # --- Step 3: Call Chat Tool with Generated Prompt ---
                print("\nSending symptoms to the AI for analysis…")
                try:
                    logging.info(f"Calling 'chat' tool with query: {diagnosis_prompt!r}")
                    tool_resp = await sess.call_tool(
                        "chat",
                        arguments={"query": diagnosis_prompt}
                    )

                    # --- EXTRACT the AI’s reply text ---
                    cont = getattr(tool_resp, 'content', None)
                    if isinstance(cont, list):
                        reply_parts = []
                        for c in cont:
                            reply_parts.append(getattr(c, 'text', str(c)))
                        response_text = "\n".join(reply_parts).strip()
                    else:
                        response_text = str(cont).strip()

                    print("\nAI Diagnosis/Advice:")
                    print("---------------------")
                    print(response_text)
                    logging.info("Received and processed response from 'chat' tool.")

                except Exception as e:
                    logging.error(f"Error calling 'chat' tool: {e}", exc_info=True)
                    print("\nError: Could not get diagnosis from the AI.")
                    print(f"Details: {e}")
                    return

                logging.info("Client flow completed successfully.")

    except ConnectionRefusedError:
        logging.error("Connection Refused: Is server.py running?")
        print("Error: Failed to connect. Please ensure server.py is running.")
    except Exception as e:
        logging.error(f"Unexpected error during client execution: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")
    finally:
        logging.info("Client execution finished.")


if __name__ == "__main__":
    asyncio.run(main())
