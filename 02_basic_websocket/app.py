"""A minimal FastAPI + WebSocket example.

This app shows the smallest useful WebSocket mental model:
- a client connects
- the server accepts the connection
- the server receives messages
- the server sends messages back immediately

Run:
    uvicorn app:app --reload --port 8001
Then open:
    http://127.0.0.1:8001/
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Basic WebSocket Example", version="1.0.0")

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Basic WebSocket Demo</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; }
    input, button { padding: 8px; font-size: 16px; }
    #messages { margin-top: 20px; padding-left: 20px; }
  </style>
</head>
<body>
  <h2>Basic WebSocket Demo</h2>
  <p>This page sends a message over a WebSocket and prints the reply from the server.</p>
  <input id="messageInput" placeholder="Type a message" size="40" />
  <button onclick="sendMessage()">Send</button>
  <ul id="messages"></ul>

  <script>
    const socket = new WebSocket(`ws://${location.host}/ws`);
    const messages = document.getElementById("messages");

    socket.onmessage = (event) => {
      const item = document.createElement("li");
      item.textContent = event.data;
      messages.appendChild(item);
    };

    function sendMessage() {
      const input = document.getElementById("messageInput");
      if (!input.value) return;
      socket.send(input.value);
      input.value = "";
    }
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve a tiny client so students can test WebSockets in the browser."""

    return HTML_PAGE


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept a client connection and echo every message back."""

    await websocket.accept()
    await websocket.send_text("Connected to the WebSocket server.")

    try:
        while True:
            client_message = await websocket.receive_text()
            await websocket.send_text(f"Server received: {client_message}")
    except WebSocketDisconnect:
        # A silent exit is perfectly fine for this small demo.
        print("Client disconnected")
