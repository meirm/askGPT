"""
Central constants and configuration for askGPT.

This module contains all shared constants, default values, and configuration
used across the askGPT codebase.
"""

import os

# Default Model Configuration - Offline-first approach
# Check environment variables first, then fall back to hardcoded defaults
# TODO: Implement online/offline mode switching feature that allows users
#       to easily toggle between local (offline) and cloud (online) providers
DEFAULT_MODEL = os.getenv(
    "ASKGPT_DEFAULT_MODEL", "gpt-oss:20b"
)  # Default to local model for offline-first usage
DEFAULT_PROVIDER = os.getenv(
    "ASKGPT_DEFAULT_PROVIDER", "ollama"
)  # Default to ollama for offline-first usage

# Available Models by Provider
AVAILABLE_MODELS = {
    "openai": ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-4o"],
    "anthropic": [
        "claude-opus-4-1-20250805",
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
        "claude-3-haiku-20240307",
    ],
    "ollama": ["gpt-oss:20b", "gpt-oss:120b"],
    "lmstudio": ["qwen/qwen3-coder-30b", "openai/gpt-oss-20b"],
    "ollama-native": ["gpt-oss:20b", "gpt-oss:120b", "llama3.2:3b", "codellama:7b"],
}

# Model Display Names and Descriptions
MODEL_INFO = {
    "gpt-5-nano": "GPT-5 Nano - Fastest, best for simple tasks",
    "gpt-5-mini": "GPT-5 Mini - Efficient, fast, good for most tasks",
    "gpt-5": "GPT-5 - Most powerful, best for complex reasoning",
    "gpt-4o": "GPT-4o - Previous generation, proven reliability",
    "claude-opus-4-1-20250805": "Claude Opus 4.1 - Latest Anthropic flagship",
    "claude-opus-4-20250514": "Claude Opus 4 - Powerful reasoning",
    "claude-sonnet-4-20250514": "Claude Sonnet 4 - Balanced performance",
    "claude-3-haiku-20240307": "Claude 3 Haiku - Fast and efficient",
    "gpt-oss:20b": "GPT-OSS 20B - Local open-source model",
    "gpt-oss:120b": "GPT-OSS 120B - Large local model",
    "qwen/qwen3-coder-30b": "Qwen3 Coder 30B - Local model",
}

# Provider API Key Requirements
PROVIDER_REQUIREMENTS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": None,  # No API key needed
    "lmstudio": None,  # No API key needed
    "ollama-native": None,  # No API key needed
}

# Agent Configuration
MAX_AGENT_TURNS = 20  # Maximum turns in agent loop
DEFAULT_TEMPERATURE = 0.2  # Temperature for agent responses
MAX_TOKENS = 4000  # Maximum tokens per response

# Tool Names
TOOL_READ_FILE = "read_file"
TOOL_LIST_DIRECTORY = "list_directory"
TOOL_WRITE_FILE = "write_file"
TOOL_GET_FILE_INFO = "get_file_info"
TOOL_EDIT_FILE = "edit_file"

# Available Tools List
AVAILABLE_TOOLS = [
    TOOL_READ_FILE,
    TOOL_LIST_DIRECTORY,
    TOOL_WRITE_FILE,
    TOOL_GET_FILE_INFO,
    TOOL_EDIT_FILE,
]

# Demo Configuration
DEMO_PROMPTS = [
    ("List all files in the current directory", DEFAULT_MODEL),
    (
        "Create a file called demo.txt with the content 'Hello from askGPT!'",
        DEFAULT_MODEL,
    ),
    ("Read the file demo.txt and tell me what it says", DEFAULT_MODEL),
]

# System Prompts
ASKGPT_SYSTEM_PROMPT = """You are a helpful autonomous agent that can perform file operations.

Your capabilities:
1. Read files to understand their contents
2. List directories to explore project structure
3. Write files to create or modify content
4. Get detailed file information
5. Search files by name
6. Execute shell commands
7. Search files by content

When given a task:
1. First understand what needs to be done
2. Explore the relevant files and directories
3. Complete the task step by step
4. Verify your work

IMPORTANT TOOL CALLING INSTRUCTIONS:
- When calling a tool, output ONLY the JSON arguments - no explanatory text
- Do NOT include reasoning, thoughts, or explanations before the JSON
- The JSON must be valid and complete on its own

CORRECT tool call format:
{"file_path": "/path/to/file.py"}

INCORRECT tool call format (DO NOT DO THIS):
Let me read this file {"file_path": "/path/to/file.py"}
I need to check {"file_path": "/path/to/file.py"}
Reading the file now: {"file_path": "/path/to/file.py"}

Be thorough but concise. Always verify files exist before trying to read them.
When writing files, ensure the content is correct before saving.

If asked about general information, respond and do not use any tools.
"""

# Error Messages
ERROR_NO_API_KEY = "{} environment variable is not set"
ERROR_PROVIDER_NOT_SUPPORTED = "Provider '{}' not supported. Available providers: openai, anthropic, ollama, lmstudio, ollama-native"
ERROR_FILE_NOT_FOUND = "Error: File not found: {}"
ERROR_NOT_A_FILE = "Error: Path is not a file: {}"
ERROR_DIR_NOT_FOUND = "Error: Directory not found: {}"
ERROR_NOT_A_DIR = "Error: Path is not a directory: {}"

# Success Messages
SUCCESS_FILE_WRITE = "Successfully wrote {} bytes to {}"
SUCCESS_FILE_EDIT = "updated"
SUCCESS_AGENT_COMPLETE = "Agent completed successfully in {:.2f}s"

# Version Info
VERSION = "1.0.3"
