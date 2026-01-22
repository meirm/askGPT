#!/usr/bin/env python3
"""
Example web chatbot using askGPT API.

This demonstrates how to integrate askGPT into a web application.
You can use this as a starting point for building your own chatbot.
"""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from askgpt import AskGPTClient

# Create FastAPI app
app = FastAPI(title="askGPT Chatbot Example")

# Initialize askGPT client
client = AskGPTClient()


@app.get("/", response_class=HTMLResponse)
async def get_chat_interface():
    """Serve the chat interface."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>askGPT Chatbot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            #chat-container {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 20px;
                height: 400px;
                overflow-y: auto;
                margin-bottom: 20px;
                background: #f9f9f9;
            }
            .message {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
            }
            .user-message {
                background: #007bff;
                color: white;
                text-align: right;
            }
            .assistant-message {
                background: #e9ecef;
                color: #333;
            }
            #input-container {
                display: flex;
                gap: 10px;
            }
            #message-input {
                flex: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            #send-button {
                padding: 10px 20px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            #send-button:hover {
                background: #0056b3;
            }
            #send-button:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
        </style>
    </head>
    <body>
        <h1>askGPT Chatbot</h1>
        <div id="chat-container"></div>
        <div id="input-container">
            <input type="text" id="message-input" placeholder="Type your message..." />
            <button id="send-button" onclick="sendMessage()">Send</button>
        </div>
        
        <script>
            let sessionId = null;
            
            function addMessage(text, isUser) {
                const container = document.getElementById('chat-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + (isUser ? 'user-message' : 'assistant-message');
                messageDiv.textContent = text;
                container.appendChild(messageDiv);
                container.scrollTop = container.scrollHeight;
            }
            
            async function sendMessage() {
                const input = document.getElementById('message-input');
                const button = document.getElementById('send-button');
                const message = input.value.trim();
                
                if (!message) return;
                
                // Disable input while processing
                input.disabled = true;
                button.disabled = true;
                
                // Add user message to chat
                addMessage(message, true);
                input.value = '';
                
                try {
                    // Send to API
                    const response = await fetch('/api/v1/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            session_id: sessionId,
                            provider: 'ollama',
                            model: 'gpt-oss:20b',
                        }),
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        addMessage(data.response, false);
                        sessionId = data.session_id;
                    } else {
                        addMessage('Error: ' + (data.detail || 'Unknown error'), false);
                    }
                } catch (error) {
                    addMessage('Error: ' + error.message, false);
                } finally {
                    // Re-enable input
                    input.disabled = false;
                    button.disabled = false;
                    input.focus();
                }
            }
            
            // Allow Enter key to send
            document.getElementById('message-input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """
    return html


@app.post("/api/v1/chat")
async def chat_endpoint(request: dict):
    """
    Chat endpoint that proxies to askGPT.
    
    In a real application, you might want to add authentication,
    rate limiting, and other middleware here.
    """
    try:
        response = await client.chat(
            message=request.get("message", ""),
            session_id=request.get("session_id"),
            model=request.get("model"),
            provider=request.get("provider"),
            temperature=request.get("temperature"),
            max_tokens=request.get("max_tokens"),
        )
        
        if response.success:
            return {
                "success": True,
                "response": response.result,
                "session_id": client.session_manager.current_session.session_id if client.session_manager.current_session else None,
                "metadata": response.metadata,
            }
        else:
            return {
                "success": False,
                "error": response.error,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            if not message:
                continue
            
            # Get response from askGPT
            response = await client.chat(
                message=message,
                session_id=session_id,
                model=data.get("model"),
                provider=data.get("provider", "ollama"),
            )
            
            # Update session ID
            if client.session_manager.current_session:
                session_id = client.session_manager.current_session.session_id
            
            # Send response
            await websocket.send_json({
                "response": response.result if response.success else response.error,
                "success": response.success,
                "session_id": session_id,
            })
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    
    print("Starting askGPT Chatbot Example...")
    print("Open http://localhost:8080 in your browser")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
