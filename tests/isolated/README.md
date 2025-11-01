# Isolated Multi-Provider Tests

This directory contains minimal tests for using the OpenAI SDK with alternative providers.

## Providers Tested

1. **Ollama** - Local models via Ollama
   - Model: `gpt-oss:20b`
   - Endpoint: `http://localhost:11434/v1`

2. **Anthropic** - Claude models via OpenAI compatibility
   - Model: `claude-3-haiku-20240307`
   - Endpoint: `https://api.anthropic.com/v1/`

## Setup

### For Ollama Tests

1. Install Ollama: https://ollama.com/download
2. Pull the model: `ollama pull gpt-oss:20b`
3. Ensure Ollama is running (it starts automatically after install)

### For Anthropic Tests

1. Get an API key from https://console.anthropic.com/
2. Set environment variable: `export ANTHROPIC_API_KEY=your-key-here`

## Running Tests

```bash
cd apps/nano_agent_mcp_server

# Run all multi-provider tests
uv run pytest tests/isolated/test_multi_provider_openai_sdk.py -v -s

# Run only Ollama tests (requires Ollama installed)
uv run pytest tests/isolated/test_multi_provider_openai_sdk.py::TestOllamaProvider -v -s

# Run only Anthropic tests
uv run pytest tests/isolated/test_multi_provider_openai_sdk.py::TestAnthropicProvider -v -s

# Check documentation exists
uv run pytest tests/isolated/test_multi_provider_openai_sdk.py::test_providers_documented -v
```

## Test Structure

The tests are minimal and focused:
- Send a simple "hello" prompt
- Assert that we get a response
- No mocking - real API calls

## Notes

- The OpenAI Agent SDK (`from agents import Agent`) is designed specifically for OpenAI models and may not work with alternative providers
- The standard OpenAI SDK (`from openai import OpenAI`) works well with both Ollama and Anthropic via their OpenAI-compatible endpoints
- These tests document the current state of compatibility