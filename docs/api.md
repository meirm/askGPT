# askGPT Web API Documentation

## Overview

askGPT provides a REST API, WebSocket, and Server-Sent Events (SSE) interface for integrating AI agent capabilities into web applications and services.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider adding authentication middleware.

## REST Endpoints

### Health Check

**GET** `/api/v1/health`

Check if the API server is running.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

### Chat

**POST** `/api/v1/chat`

Send a chat message and get a response.

**Request Body:**
```json
{
  "message": "Hello, how are you?",
  "session_id": "optional_session_id",
  "model": "gpt-oss:20b",
  "provider": "ollama",
  "temperature": 0.7,
  "max_tokens": 1000,
  "agent_name": "optional_agent_personality",
  "read_only": false,
  "allowed_tools": ["read_file", "list_directory"],
  "blocked_tools": ["write_file"]
}
```

**Response:**
```json
{
  "response": "Hello! I'm doing well, thank you for asking.",
  "session_id": "session_20240101_120000_abc123",
  "metadata": {
    "model": "gpt-oss:20b",
    "provider": "ollama",
    "token_usage": {
      "total_tokens": 150,
      "input_tokens": 100,
      "output_tokens": 50,
      "total_cost": 0.0
    },
    "execution_time_seconds": 2.5
  },
  "success": true
}
```

**Error Response:**
```json
{
  "detail": "Error message here"
}
```

### Sessions

#### List Sessions

**GET** `/api/v1/sessions?limit=10`

List recent chat sessions.

**Response:**
```json
[
  {
    "session_id": "session_20240101_120000_abc123",
    "created_at": "2024-01-01T12:00:00",
    "last_updated": "2024-01-01T12:05:00",
    "provider": "ollama",
    "model": "gpt-oss:20b",
    "message_count": 4,
    "metadata": {
      "total_tokens": 500,
      "total_cost": 0.0
    }
  }
]
```

#### Get Session

**GET** `/api/v1/sessions/{session_id}`

Get details of a specific session.

**Response:**
```json
{
  "session_id": "session_20240101_120000_abc123",
  "created_at": "2024-01-01T12:00:00",
  "last_updated": "2024-01-01T12:05:00",
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "message_count": 4,
  "metadata": {
    "total_tokens": 500,
    "total_cost": 0.0
  }
}
```

#### Create Session

**POST** `/api/v1/sessions`

Create a new chat session.

**Request Body:**
```json
{
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "session_id": "optional_custom_id"
}
```

**Response:**
```json
{
  "session_id": "session_20240101_120000_abc123",
  "created_at": "2024-01-01T12:00:00",
  "last_updated": "2024-01-01T12:00:00",
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "message_count": 0,
  "metadata": {}
}
```

#### Delete Session

**DELETE** `/api/v1/sessions/{session_id}`

Delete a session.

**Response:**
```json
{
  "message": "Session session_20240101_120000_abc123 deleted successfully"
}
```

### Models

**GET** `/api/v1/models`

List available models and providers.

**Response:**
```json
{
  "default_provider": "ollama",
  "default_model": "gpt-oss:20b",
  "providers": {
    "ollama": {
      "known_models": ["gpt-oss:20b", "gpt-oss:120b"],
      "allow_unknown_models": true,
      "discover_models": true
    },
    "openai": {
      "known_models": ["gpt-5-mini", "gpt-5"],
      "allow_unknown_models": true,
      "discover_models": false
    }
  },
  "model_aliases": {
    "gpt5": "gpt-5",
    "qwen": "qwen2.5-coder:3b"
  }
}
```

## WebSocket Endpoint

### Streaming Chat

**WebSocket** `ws://localhost:8000/api/v1/chat/stream`

Real-time streaming chat via WebSocket.

**Client Message:**
```json
{
  "message": "Tell me a story",
  "session_id": "optional_session_id",
  "model": "gpt-oss:20b",
  "provider": "ollama",
  "temperature": 0.7
}
```

**Server Messages (streaming):**
```json
{
  "chunk": "Once upon a time...",
  "done": false,
  "session_id": "session_123"
}
```

```json
{
  "chunk": "",
  "done": true,
  "session_id": "session_123"
}
```

**Error Message:**
```json
{
  "error": "Error message here",
  "done": true
}
```

## Server-Sent Events (SSE)

### Streaming Chat

**GET** `/api/v1/chat/stream?message=Hello&session_id=optional&model=gpt-oss:20b&provider=ollama`

Stream chat responses using Server-Sent Events.

**Response Headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Response Format:**
```
data: {"chunk": "Hello", "done": false, "session_id": "session_123"}

data: {"chunk": " there!", "done": false, "session_id": "session_123"}

data: {"chunk": "", "done": true, "session_id": "session_123"}

```

## Error Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (session not found)
- `422` - Validation Error (invalid request format)
- `500` - Internal Server Error

## Rate Limiting

Rate limiting is not currently implemented but can be added via FastAPI middleware.

## Configuration

The API uses the same configuration system as the CLI. Configuration is loaded from:
1. `~/.askgpt/config.yaml` (user config)
2. `.askgpt/config.yaml` (project config)
3. Environment variables (prefixed with `ASKGPT_`)
4. Default values

See `config/examples/web_server.yaml` for configuration options.

## Examples

### Python Client

```python
import requests

# Send a chat message
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "Hello!",
        "provider": "ollama",
        "model": "gpt-oss:20b",
    }
)

data = response.json()
print(data["response"])
```

### JavaScript/TypeScript Client

```javascript
// REST API
const response = await fetch('http://localhost:8000/api/v1/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Hello!',
    provider: 'ollama',
    model: 'gpt-oss:20b',
  }),
});

const data = await response.json();
console.log(data.response);
```

### WebSocket Client

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/stream');

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: 'Hello!',
    provider: 'ollama',
    model: 'gpt-oss:20b',
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.done) {
    console.log('Stream complete');
  } else {
    process.stdout.write(data.chunk);
  }
};
```

### SSE Client

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/chat/stream?message=Hello&provider=ollama&model=gpt-oss:20b'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.done) {
    eventSource.close();
  } else {
    process.stdout.write(data.chunk);
  }
};
```

## Using askGPT as a Library

### Basic Usage

```python
from askgpt import AskGPTClient

client = AskGPTClient()

# Send a message
response = await client.chat("Hello, how are you?")
print(response.result)

# Stream responses
async for chunk in client.chat_stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

### Session Management

```python
# Create a session
session = client.create_session(provider="ollama", model="gpt-oss:20b")

# Use session for conversation
response1 = await client.chat("My name is Alice", session_id=session.session_id)
response2 = await client.chat("What's my name?", session_id=session.session_id)

# List sessions
sessions = client.list_sessions(limit=10)
for s in sessions:
    print(f"{s.session_id}: {s.model}")
```

## Starting the Server

### Using CLI

```bash
askgpt serve --host 0.0.0.0 --port 8000
```

### Using Python

```python
import uvicorn
from askgpt.web_server import app

uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Default Configuration

By default, askGPT uses Ollama as the provider (no API keys required):

- **Provider**: `ollama`
- **Model**: `gpt-oss:20b`
- **API Base**: `http://localhost:11434/v1`

Make sure Ollama is running:
```bash
ollama serve
```

## Production Considerations

1. **Authentication**: Add authentication middleware before deploying
2. **Rate Limiting**: Implement rate limiting to prevent abuse
3. **CORS**: Configure CORS appropriately for your frontend domain
4. **Session Storage**: Consider using Redis or a database for session storage
5. **Logging**: Configure appropriate logging levels
6. **Monitoring**: Add health checks and monitoring
7. **SSL/TLS**: Use HTTPS in production

## Support

For issues, questions, or contributions, please see the main askGPT repository.
