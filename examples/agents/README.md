# Agent Examples

Agents are specialized personalities that extend the base nano-agent system prompt, allowing you to customize how the AI behaves and responds to your requests.

## What are Agents?

Agents are markdown files stored in `~/.askgpt/agents/` that define:
- **Personality traits**: How the agent communicates
- **Expertise areas**: What the agent is specialized in
- **Behavioral guidelines**: How the agent should approach tasks
- **Response style**: How the agent formats its output

When you use an agent, its content is appended to the base system prompt, effectively giving the AI a specialized "personality" for that session.

## Agent File Format

Agent files are markdown files with optional YAML frontmatter:

```markdown
---
name: agent-name
description: Brief description of the agent's purpose.
keywords: [keyword1, keyword2]
---

# Agent Name

Brief description of the agent's purpose.

## Personality

Description of the agent's personality traits and communication style.

## Expertise

- Area of expertise 1
- Area of expertise 2
- Area of expertise 3

## Behavioral Guidelines

- How the agent should behave
- What it should prioritize
- How it approaches problems

## Response Style

How the agent structures and formats its responses.

## Examples

Specific examples of how this agent handles requests.

## Notes

Any additional context or requirements.
```

### YAML Frontmatter (Optional)

The YAML frontmatter provides metadata:
- **name**: Agent identifier (defaults to filename)
- **description**: Brief description (used in listings)
- **keywords**: Searchable keywords for discovery

## Usage

### Command Line

```bash
# Use an agent with the run command
askgpt run "Write a Python function" --agent coder

# Use an agent with interactive mode
askgpt interactive --agent analyst
```

### Interactive Mode

```bash
# Switch to an agent
nano-agent> @coder

# Switch to another agent
nano-agent> @analyst

# Show current agent and list available
nano-agent> @
```

## Example Agents

### Coder Agent
**File**: `example-coder.md`

A senior software engineer personality that:
- Focuses on clean code and best practices
- Emphasizes design patterns
- Prioritizes code quality and maintainability
- Includes comprehensive testing

**Best for**: Software development, code review, refactoring, technical problem-solving

### Analyst Agent
**File**: `example-analyst.md`

A data analyst personality that:
- Performs statistical analysis
- Creates data visualizations
- Generates business insights
- Validates data quality

**Best for**: Data analysis, reporting, business intelligence, statistical work

## Creating Your Own Agent

1. **Choose a specialization**: What domain or task is this agent for?
2. **Define personality**: How should it communicate and behave?
3. **List expertise**: What areas should it be knowledgeable about?
4. **Set guidelines**: What principles should it follow?
5. **Describe style**: How should it format responses?

### Example Template

```markdown
---
name: my-agent
description: Specialized agent for [your domain]
---

# My Agent

[Description of what this agent does]

## Personality

[Describe communication style and traits]

## Expertise

- [Expertise area 1]
- [Expertise area 2]

## Behavioral Guidelines

- [Guideline 1]
- [Guideline 2]

## Response Style

[How responses should be formatted]
```

## Installation

Copy agent files to `~/.askgpt/agents/`:

```bash
# Copy a single agent
cp examples/agents/example-coder.md ~/.askgpt/agents/coder.md

# Copy all example agents
cp examples/agents/*.md ~/.askgpt/agents/
```

## Tips

- **Be specific**: Clear, focused agents work better than generic ones
- **Include examples**: Show how the agent should handle common tasks
- **Keep it concise**: Agents that are too long may dilute their effectiveness
- **Test different styles**: Experiment with different personalities for the same domain
- **Combine with commands**: Use agents with commands for powerful workflows

## Advanced: Agent Switching

In interactive mode, you can switch agents mid-conversation:

```bash
nano-agent> @coder
Switched to agent: coder

nano-agent> Write a Python class
[Response with coder personality]

nano-agent> @analyst
Switched to agent: analyst

nano-agent> Analyze this data
[Response with analyst personality]
```

This allows you to use different specializations within the same session.

## See Also

- Main documentation: `apps/nano_agent_mcp_server/AGENTS.md`
- Example agents in this directory
- Built-in agents in `examples/dot.askgpt/agents/`

