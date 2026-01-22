# How to Use askGPT as an Advanced LLM Provider

This guide explains how to deploy and use askGPT as a production-ready LLM provider service. askGPT provides a unified API interface that supports multiple LLM backends (OpenAI, Anthropic, Ollama, etc.) with advanced features like agent capabilities, tool usage, session management, and streaming.

## Table of Contents

1. [Overview](#overview)
2. [Why Use askGPT as a Provider?](#why-use-askgpt-as-a-provider)
3. [Quick Start](#quick-start)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [API Endpoints](#api-endpoints)
7. [Integration Examples](#integration-examples)
8. [Advanced Features](#advanced-features)
9. [Production Deployment](#production-deployment)
10. [Comparison with Other Providers](#comparison-with-other-providers)

## Overview

askGPT is more than just a CLI tool—it's a complete LLM provider service that offers:

- **Multi-Provider Support**: Unified API for OpenAI, Anthropic, Ollama, and more
- **Agent Capabilities**: Built-in agent system with tool usage (file operations, web search, code execution)
- **Session Management**: Persistent conversation sessions with context retention
- **Streaming Support**: Real-time streaming via REST, WebSocket, and SSE
- **Offline-First**: Works with local models (Ollama) without API keys
- **Flexible Configuration**: YAML-based configuration with environment variable overrides
- **Production-Ready**: Docker/Podman images, health checks, CORS support

## Why Use askGPT as a Provider?

### 1. **Unified Interface**
Instead of managing multiple provider SDKs (OpenAI, Anthropic, etc.), use a single API that works with all of them:

```python
# Same API for all providers
POST /api/v1/chat
{
  "message": "Hello",
  "provider": "ollama",      # or "openai", "anthropic", etc.
  "model": "gpt-oss:20b"
}
```

### 2. **Agent Capabilities**
Unlike basic chat APIs, askGPT provides autonomous agents that can:
- Read and write files
- Execute shell commands
- Search the web
- Analyze code
- Perform complex multi-step tasks

### 3. **Cost Efficiency**
- Use local models (Ollama) for development and testing
- Switch to cloud providers only when needed
- Mix and match providers based on task requirements

### 4. **No Vendor Lock-In**
Change providers or models without changing your code:

```python
# Switch from OpenAI to Ollama
response = requests.post("http://askgpt:8000/api/v1/chat", json={
    "message": "Analyze this code",
    "provider": "ollama",  # Just change this
    "model": "gpt-oss:20b"
})
```

## Quick Start

### Option 1: Docker/Podman (Recommended)

```bash
# Build the image
podman build -f Dockerfile.api -t askgpt-api .

# Run the server
podman run -d --name askgpt-api --replace \
  -p 8010:8010 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  -e ASKGPT_PORT=8010 \
  askgpt-api

# Test it
curl http://localhost:8010/api/v1/health
```

### Option 2: Python Package

```bash
# Install
pip install askgpt[web]

# Start server
askgpt serve --host 0.0.0.0 --port 8000
```

### Option 3: Python Library

```python
import uvicorn
from askgpt.web_server import app

uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Installation

### Prerequisites

- Python 3.12+ (for Python installation)
- Docker or Podman (for container deployment)
- Ollama (optional, for local models)

### Install from PyPI

```bash
pip install askgpt[web]
```

### Install from Source

```bash
git clone https://github.com/yourusername/askGPT.git
cd askGPT
pip install -e ".[web]"
```

### Container Deployment

See [PODMAN_QUICKSTART.md](./PODMAN_QUICKSTART.md) for detailed container setup instructions.

## Configuration

askGPT uses a YAML configuration file to manage providers, models, and settings.

### Configuration File Location

The server looks for configuration in this order:
1. `ASKGPT_CONFIG_PATH` environment variable
2. `~/.askgpt/config.yaml` (user config)
3. `.askgpt/config.yaml` (project config)
4. Default configuration

### Basic Configuration

Create `~/.askgpt/config.yaml`:

```yaml
# Default provider and model
default_provider: ollama
default_model: gpt-oss:20b

# Provider configurations
providers:
  # Ollama (local, no API key needed)
  ollama:
    api_base: http://localhost:11434/v1
    known_models:
      - gpt-oss:20b
      - gpt-oss:120b
    allow_unknown_models: true
    discover_models: true

  # OpenAI (requires API key)
  openai:
    api_key: ${OPENAI_API_KEY}
    api_base: https://api.openai.com/v1
    known_models:
      - gpt-5-mini
      - gpt-5
      - gpt-4o
    allow_unknown_models: true

  # Anthropic (requires API key)
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    api_base: https://api.anthropic.com
    known_models:
      - claude-opus-4-1-20250805
      - claude-sonnet-4-20250514
    allow_unknown_models: true
```

### Environment Variables

Override configuration with environment variables:

```bash
# Provider-specific
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export OLLAMA_API_BASE="http://localhost:11434/v1"

# Server settings
export ASKGPT_PORT=8000
export ASKGPT_HOST=0.0.0.0
```

### Container Configuration

When using containers, mount your config file:

```bash
podman run -d \
  -v $(pwd)/my_config.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api
```

See [CONFIG_MOUNTING.md](./examples/CONFIG_MOUNTING.md) for detailed configuration mounting instructions.

## API Endpoints

### Base URL

```
http://localhost:8000/api/v1
```

### Health Check

```bash
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

### Chat (REST)

```bash
POST /api/v1/chat
```

**Request:**
```json
{
  "message": "Write a Python function to calculate fibonacci numbers",
  "session_id": "optional_session_id",
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "temperature": 0.7,
  "max_tokens": 2000,
  "agent_name": "coder",
  "read_only": false,
  "allowed_tools": ["read_file", "write_file"],
  "blocked_tools": ["execute_command"]
}
```

**Response:**
```json
{
  "response": "Here's a Python function...",
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

### Streaming Chat (WebSocket)

```bash
WebSocket: ws://localhost:8000/api/v1/chat/stream
```

**Client Message:**
```json
{
  "message": "Tell me a story",
  "session_id": "optional_session_id",
  "provider": "ollama",
  "model": "gpt-oss:20b"
}
```

**Server Messages (streaming):**
```json
{"chunk": "Once", "done": false, "session_id": "session_123"}
{"chunk": " upon", "done": false, "session_id": "session_123"}
{"chunk": " a time...", "done": false, "session_id": "session_123"}
{"chunk": "", "done": true, "session_id": "session_123"}
```

### Streaming Chat (SSE)

```bash
GET /api/v1/chat/stream?message=Hello&provider=ollama&model=gpt-oss:20b
```

**Response (Server-Sent Events):**
```
data: {"chunk": "Hello", "done": false, "session_id": "session_123"}

data: {"chunk": " there!", "done": false, "session_id": "session_123"}

data: {"chunk": "", "done": true, "session_id": "session_123"}
```

### Session Management

```bash
# List sessions
GET /api/v1/sessions?limit=10

# Get session details
GET /api/v1/sessions/{session_id}

# Create session
POST /api/v1/sessions
{
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "session_id": "optional_custom_id"
}

# Delete session
DELETE /api/v1/sessions/{session_id}
```

### List Available Models

```bash
GET /api/v1/models
```

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
  }
}
```

## Integration Examples

### Python Client

```python
import requests

# Simple chat
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "Hello!",
        "provider": "ollama",
        "model": "gpt-oss:20b"
    }
)
data = response.json()
print(data["response"])

# Multi-turn conversation with session
session_id = None
for message in ["My name is Alice", "What's my name?"]:
    response = requests.post(
        "http://localhost:8000/api/v1/chat",
        json={
            "message": message,
            "session_id": session_id,
            "provider": "ollama",
            "model": "gpt-oss:20b"
        }
    )
    data = response.json()
    session_id = data["session_id"]
    print(f"Bot: {data['response']}")
```

### JavaScript/TypeScript Client

```javascript
// REST API
async function chat(message, sessionId = null) {
  const response = await fetch('http://localhost:8000/api/v1/chat', {
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
  return data;
}

// Usage
const result = await chat('Hello!');
console.log(result.response);
```

### WebSocket Client (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/stream');

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: 'Write a Python function',
    provider: 'ollama',
    model: 'gpt-oss:20b',
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.done) {
    console.log('\nStream complete');
    ws.close();
  } else {
    process.stdout.write(data.chunk);
  }
};
```

### SSE Client (JavaScript)

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

### Using the Python Library

```python
from askgpt import AskGPTClient

# Create client
client = AskGPTClient()

# Simple chat
response = await client.chat("Hello!")
print(response.result)

# Streaming
async for chunk in client.chat_stream("Tell me a story"):
    print(chunk, end="", flush=True)

# Session management
session = client.create_session(provider="ollama", model="gpt-oss:20b")
response1 = await client.chat("My name is Alice", session_id=session.session_id)
response2 = await client.chat("What's my name?", session_id=session.session_id)
```

## Advanced Features

### 1. Agent Personalities

Use pre-configured agent personalities for different use cases:

```json
{
  "message": "Analyze this code",
  "agent_name": "coder",
  "provider": "ollama",
  "model": "gpt-oss:20b"
}
```

Available agents:
- `coder`: Optimized for code analysis and generation
- `analyst`: Data analysis and reporting
- `creative`: Creative writing and brainstorming
- `default`: General-purpose agent

### 2. Tool Permissions

Control which tools the agent can use:

```json
{
  "message": "Read config.yaml and summarize it",
  "allowed_tools": ["read_file", "list_directory"],
  "blocked_tools": ["write_file", "execute_command"],
  "read_only": true
}
```

Available tools:
- `read_file`: Read files from the filesystem
- `write_file`: Write files to the filesystem
- `list_directory`: List directory contents
- `execute_command`: Execute shell commands
- `web_search`: Search the web (if configured)
- `codebase_search`: Semantic code search

### 3. Multi-Provider Fallback

Implement fallback logic across providers:

```python
providers = ["openai", "anthropic", "ollama"]
for provider in providers:
    try:
        response = requests.post(
            "http://askgpt:8000/api/v1/chat",
            json={
                "message": "Important query",
                "provider": provider,
                "model": get_model_for_provider(provider)
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Provider {provider} failed: {e}")
        continue
```

### 4. Cost Tracking

Monitor token usage and costs:

```python
response = requests.post("http://askgpt:8000/api/v1/chat", json={
    "message": "Hello",
    "provider": "openai",
    "model": "gpt-5-mini"
})

data = response.json()
metadata = data["metadata"]
token_usage = metadata["token_usage"]

print(f"Tokens used: {token_usage['total_tokens']}")
print(f"Cost: ${token_usage['total_cost']:.4f}")
```

### 5. Session Persistence

Maintain conversation context across requests:

```python
# Create session
session_response = requests.post(
    "http://askgpt:8000/api/v1/sessions",
    json={"provider": "ollama", "model": "gpt-oss:20b"}
)
session_id = session_response.json()["session_id"]

# Use session for conversation
messages = [
    "I'm building a web app",
    "What framework should I use?",
    "Tell me more about that framework"
]

for message in messages:
    response = requests.post(
        "http://askgpt:8000/api/v1/chat",
        json={
            "message": message,
            "session_id": session_id,
            "provider": "ollama",
            "model": "gpt-oss:20b"
        }
    )
    print(response.json()["response"])
```

## Production Deployment

### 1. Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  askgpt-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - ASKGPT_PORT=8000
      - OLLAMA_API_BASE=http://ollama:11434/v1
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./config.yaml:/root/.askgpt/config_orig.yaml:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama-data:
```

### 2. Reverse Proxy (Nginx)

```nginx
upstream askgpt {
    server localhost:8000;
}

server {
    listen 80;
    server_name askgpt.example.com;

    location / {
        proxy_pass http://askgpt;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 3. Authentication

Add authentication middleware (example with API keys):

```python
# Add to web_server.py
from fastapi import Header, HTTPException

API_KEYS = ["your-secret-key-1", "your-secret-key-2"]

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path.startswith("/api/v1"):
        api_key = request.headers.get("X-API-Key")
        if api_key not in API_KEYS:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return await call_next(request)
```

### 4. Rate Limiting

Add rate limiting with `slowapi`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/chat")
@limiter.limit("10/minute")
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    # ... existing code
```

### 5. Monitoring

Add health checks and metrics:

```python
from prometheus_client import Counter, Histogram
from fastapi import Response
from fastapi.responses import JSONResponse

chat_requests = Counter('chat_requests_total', 'Total chat requests')
chat_duration = Histogram('chat_duration_seconds', 'Chat request duration')

@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest):
    chat_requests.inc()
    with chat_duration.time():
        # ... existing code
```

### 6. Environment Variables

Production environment variables:

```bash
# Server
export ASKGPT_PORT=8000
export ASKGPT_HOST=0.0.0.0

# Providers
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export OLLAMA_API_BASE="http://ollama:11434/v1"

# Security
export ASKGPT_API_KEYS="key1,key2,key3"

# Logging
export LOG_LEVEL=INFO
```

## Comparison with Other Providers

### vs. Direct OpenAI/Anthropic SDK

| Feature | askGPT | Direct SDK |
|---------|--------|------------|
| Multi-provider support | ✅ Single API | ❌ Separate SDKs |
| Agent capabilities | ✅ Built-in | ❌ Manual implementation |
| Local models | ✅ Ollama support | ❌ Cloud only |
| Tool usage | ✅ Built-in | ❌ Manual implementation |
| Session management | ✅ Automatic | ❌ Manual |
| Streaming | ✅ REST/WS/SSE | ⚠️ Limited |

### vs. LangChain/LlamaIndex

| Feature | askGPT | LangChain/LlamaIndex |
|---------|--------|---------------------|
| Setup complexity | ✅ Simple | ⚠️ Complex |
| Agent system | ✅ Built-in | ✅ Built-in |
| Multi-provider | ✅ Unified | ✅ Supported |
| Local models | ✅ First-class | ⚠️ Requires setup |
| API server | ✅ Included | ❌ Manual setup |
| Configuration | ✅ YAML-based | ⚠️ Code-based |

### Use Cases

**Choose askGPT when:**
- You need a unified API for multiple providers
- You want agent capabilities without complex setup
- You need to support both cloud and local models
- You want a production-ready API server
- You need simple configuration management

**Choose direct SDKs when:**
- You only need one provider
- You need provider-specific features
- You want maximum control over the implementation

**Choose LangChain/LlamaIndex when:**
- You need complex agent orchestration
- You're building a complex RAG system
- You need extensive customization
- You're comfortable with more setup complexity

## Troubleshooting

### Connection Errors

**Problem:** Cannot connect to Ollama
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# For containers, use host.containers.internal
export OLLAMA_API_BASE=http://host.containers.internal:11434/v1
```

### Module Not Found

**Problem:** `ModuleNotFoundError: No module named 'askgpt'`
```bash
# Reinstall the package
pip install -e ".[web]"

# Or rebuild the container
podman build -f Dockerfile.api -t askgpt-api .
```

### Configuration Not Loading

**Problem:** Config file not being read
```bash
# Check config file location
ls -la ~/.askgpt/config.yaml

# Use explicit path
export ASKGPT_CONFIG_PATH=/path/to/config.yaml
```

### Port Already in Use

**Problem:** Port 8000 already in use
```bash
# Use a different port
askgpt serve --port 8010

# Or set environment variable
export ASKGPT_PORT=8010
```

## Additional Resources

- [API Documentation](./docs/api.md) - Complete API reference
- [Podman Quickstart](./PODMAN_QUICKSTART.md) - Container deployment guide
- [Config Mounting](./examples/CONFIG_MOUNTING.md) - Configuration guide
- [API Examples](./examples/api/README.md) - Code examples
- [Release Notes](./release_notes_v2.0.0.md) - Version 2.0.0 features

## Support

For issues, questions, or contributions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/askGPT/issues)
- Documentation: See the `docs/` directory
- Examples: See the `examples/` directory
