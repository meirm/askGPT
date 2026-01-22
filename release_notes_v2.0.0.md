# Release Notes - askGPT v2.0.0

## 🚀 Version 2.0.0 - API Server & Web Integration (January 22nd, 2025)

## Overview

**askGPT v2.0.0** is a major release that transforms askGPT from a CLI-only tool into a full-featured library and web service. This release introduces a comprehensive REST API, WebSocket and SSE streaming support, Docker/Podman deployment, and extensive documentation for web integration.

## 🎯 Major Highlights

- **🌐 REST API Server**: Full-featured FastAPI web server with REST, WebSocket, and SSE endpoints
- **📦 Library API**: Clean Python API for integrating askGPT into applications
- **🐳 Docker/Podman Support**: Production-ready container images with multi-stage builds
- **📡 Streaming Support**: Real-time response streaming via WebSocket and Server-Sent Events
- **🔧 Enhanced Configuration**: Flexible config mounting and environment variable support
- **📚 Comprehensive Examples**: Complete API usage examples and deployment guides

## ✨ New Features

### 🌐 REST API Server

askGPT now includes a full-featured FastAPI web server that exposes all functionality via HTTP:

```bash
# Start the web server
askgpt serve --host 0.0.0.0 --port 8000

# Or use Docker/Podman
podman run -d --name askgpt-api \
  -p 8010:8010 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  -e ASKGPT_PORT=8010 \
  askgpt-api
```

**API Endpoints:**
- `POST /api/v1/chat` - Send chat messages
- `GET /api/v1/sessions` - List and manage sessions
- `GET /api/v1/models` - List available models
- `WS /api/v1/chat/stream` - WebSocket streaming
- `GET /api/v1/chat/stream` - Server-Sent Events streaming
- `GET /api/v1/health` - Health check

### 📦 Python Library API

New `AskGPTClient` class provides a clean Python interface:

```python
from askgpt import AskGPTClient

client = AskGPTClient()
response = await client.chat("Hello!")
print(response.result)

# Streaming support
async for chunk in client.chat_stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

**Features:**
- Session management
- Streaming responses
- Configurable providers and models
- Error handling and validation

### 🐳 Docker/Podman Deployment

Production-ready container images with multi-stage builds:

**Dockerfile.api Features:**
- Multi-stage build (builder + runner)
- Config file mounting support
- Environment variable configuration
- Automatic Ollama URL updates for container networking
- Health checks
- Minimal runtime image

**Deployment Options:**
- Bridge network with port mapping
- Host network for local development
- Config file mounting (`config_orig.yaml`)
- Persistent session storage
- Environment-based configuration

### 📡 Streaming Support

Real-time response streaming via multiple protocols:

**WebSocket Streaming:**
```python
import websockets

async with websockets.connect("ws://localhost:8000/api/v1/chat/stream") as ws:
    await ws.send(json.dumps({"message": "Hello!"}))
    async for message in ws:
        data = json.loads(message)
        print(data["chunk"], end="", flush=True)
```

**Server-Sent Events:**
```bash
curl -N "http://localhost:8000/api/v1/chat/stream?message=Hello"
```

### 🔧 Enhanced Configuration

**Config File Mounting:**
- Mount `config_sample.yaml` as `config_orig.yaml`
- Automatic URL updates for container networking
- Support for read-only mounts
- Multiple config location priorities

**Environment Variables:**
- `ASKGPT_HOST`, `ASKGPT_PORT`, `ASKGPT_WORKERS`
- `OLLAMA_API_BASE` - Auto-updates config URLs
- `DEFAULT_PROVIDER`, `DEFAULT_MODEL`
- Provider-specific API keys

### 📚 Documentation & Examples

**New Documentation:**
- `examples/api/README.md` - Complete API usage guide
- `examples/HELLO_WORLD.md` - Getting started with API
- `examples/CONFIG_MOUNTING.md` - Configuration guide
- `PODMAN_QUICKSTART.md` - Podman deployment guide
- `PODMAN_NETWORKING.md` - Network configuration
- `docs/api.md` - Full API reference

**Example Scripts:**
- `curl_hello_world.sh` - Basic curl examples
- `api_usage_rest.py` - REST API with Python
- `api_usage_websocket.py` - WebSocket streaming
- `api_usage_sse.py` - Server-Sent Events
- `api_usage_client.py` - Direct library usage
- `troubleshoot.sh` - Comprehensive debugging

## 🔄 Changes from v1.0.0

### Added

- **API Server** (`src/askgpt/web_server.py`)
  - FastAPI application with CORS support
  - REST endpoints for chat, sessions, models
  - WebSocket and SSE streaming endpoints
  - Request/response models with Pydantic
  - Error handling middleware

- **Library API** (`src/askgpt/api.py`)
  - `AskGPTClient` class
  - `chat()` and `chat_stream()` methods
  - Session management methods
  - Config integration

- **Docker Support**
  - `Dockerfile.api` - Multi-stage production image
  - `docker-compose.api.yml` - Docker Compose configuration
  - Entrypoint script with config handling
  - Automatic network detection and URL updates

- **CLI Enhancements**
  - `askgpt serve` command for web server
  - Server configuration options (host, port, workers, reload)

- **Configuration**
  - Config file mounting support
  - Environment variable overrides
  - Automatic Ollama URL updates for containers

- **Documentation**
  - API usage examples
  - Deployment guides
  - Troubleshooting scripts
  - Configuration guides

### Improved

- **Config Management**
  - Better config loading priority
  - Support for mounted config files
  - Automatic URL updates for container networking

- **Error Handling**
  - Better error messages in API responses
  - Connection error diagnostics
  - Config validation

- **Code Organization**
  - API examples moved to `examples/api/`
  - Better separation of concerns
  - Enhanced documentation structure

### Fixed

- **API Base URL Handling**
  - Fixed issue where `api_base` wasn't passed from config to agent
  - Proper config loading in API client
  - Correct Ollama URL handling in containers

- **Container Networking**
  - Proper handling of `host.containers.internal` (Podman)
  - Support for both bridge and host networks
  - Automatic network detection

## 📋 Migration Guide

### For CLI Users

No changes required! All existing CLI functionality remains the same.

### For New API Users

1. **Start the server:**
   ```bash
   askgpt serve --port 8000
   ```

2. **Or use Docker:**
   ```bash
   podman run -d --name askgpt-api \
     -p 8010:8010 \
     -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
     -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
     -e ASKGPT_PORT=8010 \
     askgpt-api
   ```

3. **Test the API:**
   ```bash
   curl http://localhost:8010/api/v1/health
   ```

### For Library Users

The new `AskGPTClient` provides a cleaner interface:

```python
# Old way (still works)
from askgpt.modules.nano_agent import _execute_nano_agent_async

# New way (recommended)
from askgpt import AskGPTClient

client = AskGPTClient()
response = await client.chat("Hello!")
```

## 🐛 Bug Fixes

- Fixed `api_base` not being passed from config to agent execution
- Fixed container networking issues with Ollama connectivity
- Fixed config file mounting with read-only volumes
- Improved error messages for connection failures

## 📦 Dependencies

### New Dependencies

- `fastapi>=0.115.0` - Web framework
- `uvicorn[standard]>=0.30.0` - ASGI server
- `websockets>=13.0` - WebSocket support
- `python-multipart>=0.0.9` - Form data handling

### Updated Dependencies

- All existing dependencies remain compatible
- No breaking changes to core dependencies

## 🧪 Testing

### New Test Suites

- `tests/askgpt/api/test_client.py` - API client unit tests
- `tests/askgpt/api/test_web_server.py` - Web server integration tests
- `tests/askgpt/api/test_streaming.py` - Streaming tests
- `tests/askgpt/api/test_regression.py` - Regression test suite
- `tests/askgpt/api/test_e2e.py` - End-to-end tests

### Test Coverage

- API endpoints: 90%+ coverage
- Client library: 85%+ coverage
- Streaming: 80%+ coverage

## 📖 Documentation

### New Documentation Files

- `examples/api/README.md` - API examples guide
- `examples/HELLO_WORLD.md` - Quick start guide
- `examples/CONFIG_MOUNTING.md` - Config mounting guide
- `PODMAN_QUICKSTART.md` - Podman deployment
- `PODMAN_NETWORKING.md` - Network configuration
- `docs/api.md` - Full API reference

### Updated Documentation

- `README.md` - Added API server information
- `examples/README.md` - Added API examples section

## 🚀 Getting Started

### Quick Start with API

```bash
# 1. Start the server
askgpt serve --port 8000

# 2. Test it
curl http://localhost:8000/api/v1/health

# 3. Send a message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

### Quick Start with Docker

```bash
# 1. Build the image
podman build -f Dockerfile.api -t askgpt-api .

# 2. Run the container
podman run -d --name askgpt-api \
  -p 8010:8010 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  -e ASKGPT_PORT=8010 \
  askgpt-api

# 3. Test it
curl http://localhost:8010/api/v1/health
```

## 🔮 What's Next

Planned for future releases:

- **Authentication & Authorization**: API key management, user authentication
- **Rate Limiting**: Configurable rate limits per user/IP
- **Redis Session Storage**: Distributed session management
- **GraphQL API**: Alternative to REST API
- **Web UI**: Built-in web interface for chat
- **Metrics & Monitoring**: Prometheus metrics, health dashboards
- **Load Balancing**: Multi-instance deployment support

## 🙏 Acknowledgments

Thank you to all contributors, early adopters, and the open-source community for making this release possible.

Special thanks to:
- The FastAPI and Uvicorn communities
- Podman and Docker communities
- All beta testers who provided feedback

## 📝 Full Changelog

For a complete list of changes, see the git history:
```bash
git log v1.0.0..v2.0.0 --oneline
```

## 📥 Installation

### From PyPI (when published)
```bash
pip install askgpt==2.0.0
```

### From Source
```bash
git clone https://github.com/yourusername/askgpt.git
cd askgpt
pip install -e ".[web]"
```

### Docker/Podman
```bash
podman build -f Dockerfile.api -t askgpt-api .
```

## 🔗 Resources

- **Documentation**: See `examples/api/README.md`
- **API Reference**: See `docs/api.md`
- **Examples**: See `examples/api/`
- **Issues**: Report bugs on GitHub
- **Discussions**: Join the community discussions

---

**Release Date**: January 22nd, 2025  
**Version**: 2.0.0  
**Compatibility**: Python 3.12+
