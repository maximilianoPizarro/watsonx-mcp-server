import os
import atexit
import asyncio
from flask import Flask, render_template, request, redirect, url_for, session
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# MCP server parameters
SERVER_PARAMS = StdioServerParameters(command="python", args=["server.py"], env=None)

# Create a dedicated asyncio event loop for MCP client
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Globals to hold the long-lived stdio client and session contexts
_stdio_ctx = None
_session_ctx = None
SESSION = None

async def _init_session():
    global _stdio_ctx, _session_ctx, SESSION
    # Create the stdio client context and enter it
    _stdio_ctx = stdio_client(SERVER_PARAMS)
    _reader, _writer = await _stdio_ctx.__aenter__()
    # Create the ClientSession context and enter it
    _session_ctx = ClientSession(_reader, _writer)
    SESSION = await _session_ctx.__aenter__()
    # Initialize the MCP session
    await SESSION.initialize()

# Run initialization at import time
loop.run_until_complete(_init_session())
app.logger.info("MCP client session initialized once.")

async def _close_session():
    """
    Clean up the MCP session and stdio client on exit.
    """
    global _stdio_ctx, _session_ctx, SESSION
    if _session_ctx:
        await _session_ctx.__aexit__(None, None, None)
    if _stdio_ctx:
        await _stdio_ctx.__aexit__(None, None, None)

# Register cleanup handler
atexit.register(lambda: loop.run_until_complete(_close_session()))

# Helper functions using the single SESSION

def fetch_greeting(name: str) -> str:
    resp = loop.run_until_complete(SESSION.read_resource(f"greeting://patient/{name}"))
    contents = getattr(resp, 'contents', None)
    if isinstance(contents, list):
        texts = [getattr(c, 'text', str(c)) for c in contents]
        return "\n".join(texts).strip()
    return str(resp)


def assess_symptoms(symptoms: str) -> str:
    # Generate the prompt
    prompt_resp = loop.run_until_complete(
        SESSION.get_prompt("assess_symptoms", arguments={"symptoms": symptoms})
    )
    # Extract text from prompt_resp.messages
    msgs = getattr(prompt_resp, 'messages', None)
    if msgs:
        parts = []
        for m in msgs:
            content = getattr(m, 'content', m)
            text = getattr(content, 'text', content)
            if text.startswith("<module"):
                text = text.split("\n", 1)[1]
            parts.append(text)
        diagnosis_prompt = "\n".join(parts).strip()
    else:
        diagnosis_prompt = getattr(prompt_resp, 'description', str(prompt_resp))

    # Call the chat tool
    tool_resp = loop.run_until_complete(
        SESSION.call_tool("chat", arguments={"query": diagnosis_prompt})
    )
    cont = getattr(tool_resp, 'content', None)
    if isinstance(cont, list):
        texts = [getattr(c, 'text', str(c)) for c in cont]
        return "\n".join(texts).strip()
    return str(cont).strip()

# Flask routes
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        session['name'] = request.form['name']
        return redirect(url_for('symptoms'))
    return render_template("home.html")

@app.route("/symptoms", methods=["GET", "POST"])
def symptoms():
    name = session.get('name')
    if not name:
        return redirect(url_for('home'))

    if request.method == "POST":
        symptoms_text = request.form['symptoms']
        diagnosis = assess_symptoms(symptoms_text)
        return render_template("diagnosis.html", diagnosis=diagnosis)

    greeting = fetch_greeting(name)
    return render_template("symptoms.html", greeting=greeting)

if __name__ == "__main__":
    app.run(debug=True)
