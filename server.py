# server.py

import os
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# IBM Watsonx.ai SDK
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# For prompt templates
from mcp.server.fastmcp.prompts import base

# Load .env variables
load_dotenv()

# Fetch credentials
API_KEY    = os.getenv("WATSONX_APIKEY")
URL        = os.getenv("WATSONX_URL")
PROJECT_ID = os.getenv("PROJECT_ID")
MODEL_ID   = os.getenv("MODEL_ID", "ibm/granite-13b-instruct-v2")

# Validate env vars
for name, val in [
    ("WATSONX_APIKEY", API_KEY),
    ("WATSONX_URL", URL),
    ("PROJECT_ID", PROJECT_ID)
]:
    if not val:
        raise RuntimeError(f"{name} is not set. Please add it to your .env file.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Initialize IBM credentials & client
creds  = Credentials(url=URL, api_key=API_KEY)
client = APIClient(credentials=creds, project_id=PROJECT_ID)

# Initialize the inference model
model = ModelInference(
    model_id=MODEL_ID,
    credentials=creds,
    project_id=PROJECT_ID
)

logging.info(
    f"Initialized Watsonx.ai model '{MODEL_ID}' "
    f"for project '{PROJECT_ID}'."
)

# Create the MCP server instance
mcp = FastMCP("Watsonx Chatbot Server")


@mcp.tool()
def chat(query: str) -> str:
    """
    MCP tool: generate a chatbot response via Watsonx.ai

    :param query: User's input message
    :return: Watsonx.ai generated response
    """
    logging.info("Received chat query: %r", query)

    # Define generation parameters
    params = {
        GenParams.DECODING_METHOD: "greedy",
        GenParams.MAX_NEW_TOKENS:   200,
    }

    # Run the model
    try:
        # Request the full JSON response rather than just a string
        resp = model.generate_text(
            prompt=query,
            params=params,
            raw_response=True
        )
        print("AI raw response:", resp)

        # Extract the generated text from the dict
        text = resp["results"][0]["generated_text"].strip()
        logging.info("Generated response: %r", text)
        return text

    except Exception as e:
        logging.error("Inference error: %s", e, exc_info=True)
        return f"Error generating response: {e}"


# Expose a greeting resource that dynamically constructs a personalized greeting.
@mcp.resource("greeting://patient/{name}")
def get_greeting(name: str) -> str:
    """
    Return a medical‑style greeting for the given patient name.

    :param name: The patient's name.
    :return: A personalized greeting.
    """
    return f"Hello {name}, I’m your medical assistant. How can I help you today?"


@mcp.prompt()
def assess_symptoms(symptoms: str) -> str:
    """
    Prompt template for symptom assessment.

    :param symptoms: Description of patient symptoms.
    :return: A prompt asking the LLM to analyze and suggest next steps.
    """
    return (
        f"{base}\n"
        "You are a qualified medical assistant. The patient reports the following symptoms:\n"
        f"{symptoms}\n\n"
        "Please provide possible causes, recommended next steps, and when to seek immediate care."
      )


if __name__ == "__main__":
    # Start the MCP server (blocking call)
    logging.info("Starting MCP server on STDIO transport...")
    mcp.run()
