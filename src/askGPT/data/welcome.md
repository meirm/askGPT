# 🚀 Welcome to askGPT Interactive Mode

## Getting Started

You're now in the interactive shell for **askGPT**, a multi-provider AI-powered assistant with **offline-first** support. By default, askGPT runs locally using Ollama, but you can switch to cloud providers anytime.

askGPT can help you with:
- 💻 **Code Development** - Write, review, and refactor code
- 📊 **Analysis** - Analyze files, data, and systems
- 📝 **Documentation** - Create and improve documentation
- 🔧 **Problem Solving** - Debug issues and find solutions
- 🎨 **Creative Tasks** - Generate ideas and content

## Quick Commands

### Essential Commands
- `/help` - Show available commands
- `/commands` - List command templates
- `/agents` - View available agent personalities
- `/ps1` - Customize your prompt
- `/exit` or `/quit` - Exit interactive mode

### Agent Personalities
Switch between specialized agents using `@`:
- `@coder` - Software engineering expert
- `@analyst` - Data analysis specialist
- `@creative` - Creative problem solver
- `@h4x0r` - L33t speak enthusiast

### Shell Integration
- `!command` - Execute shell commands (e.g., `!ls -la`)
- `/model <name>` - Change AI model (e.g., `/model gpt-oss:20b`)
- `/provider <name>` - Switch providers (e.g., `/provider ollama`, `/provider openai`)

## Tips

1. **Tab Completion**: Press Tab to autocomplete commands and models
2. **History**: Use ↑/↓ arrows to navigate command history
3. **Commands**: Start with `/` for special commands
4. **Direct Chat**: Type normally to chat with the AI
5. **Offline Mode**: Defaults to local Ollama - no API keys needed!
6. **Multi-Provider**: Switch between Ollama, OpenAI, Anthropic, LM Studio

## Configuration

Your settings are saved in `~/.askgpt/config.yaml`
- Default provider: `ollama` (offline/local)
- Default model: `gpt-oss:20b` (local model)
- To hide this welcome message: `/welcome off`
- To configure providers: Edit `~/.askgpt/config.yaml` or use `askgpt init`

## Quick Start

1. **Offline Mode** (default): Works immediately, no setup needed!
   ```
   askgpt "Explain this code"
   ```

2. **Cloud Provider**: Set API keys and switch providers
   ```
   export OPENAI_API_KEY=your-key
   /provider openai
   /model gpt-5-mini
   ```

---
*Happy coding! Type your first question or `/help` to explore.*