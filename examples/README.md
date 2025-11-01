# Nano Agent Examples

This directory contains example files demonstrating how to create and use agents, commands, and skills in nano-agent.

## Directory Structure

```
examples/
├── agents/          # Example agent personality files
├── commands/        # Example command templates
├── skills/          # Example skill directories
└── README.md        # This file
```

## Agents

Agent files define specialized personalities that extend the base system prompt. They are stored in `~/.askgpt/agents/` as markdown files.

### Example: Coder Agent
**File**: `agents/example-coder.md`

A senior software engineer personality focused on:
- Clean code and best practices
- Design patterns
- Code quality and maintainability
- Testing and documentation

### Example: Analyst Agent
**File**: `agents/example-analyst.md`

A data analyst personality focused on:
- Statistical analysis
- Data visualization
- Business intelligence
- Insight generation

### Using Agents

```bash
# Use an agent with CLI
askgpt run "Write a Python function" --agent coder

# Switch agents in interactive mode
nano-agent> @coder
nano-agent> @analyst
```

## Commands

Command files are reusable prompt templates stored in `~/.askgpt/commands/`. They use YAML frontmatter for metadata and support `$ARGUMENTS` substitution.

### Example: Code Review Command
**File**: `commands/example-code-review.md`

Performs comprehensive code reviews focusing on:
- Code quality and readability
- Best practices
- Potential bugs
- Refactoring suggestions

### Example: Test Generator Command
**File**: `commands/example-test-generator.md`

Generates comprehensive unit tests including:
- Test coverage for main functionality
- Edge cases and error handling
- Integration scenarios
- Proper test structure

### Example: Documentation Command
**File**: `commands/example-documentation.md`

Generates documentation including:
- Code docstrings
- API documentation
- README files
- Inline comments

### Command Format

All commands use YAML frontmatter:

```markdown
---
name: command-name
description: Brief description of what the command does.
tools: ["read_file", "write_file"]
---

# Command Title

Command description...

## Prompt Template

Your prompt with $ARGUMENTS placeholder.
```

### Using Commands

```bash
# Execute a command
askgpt /code-review "$(cat src/main.py)"
askgpt /test-generator "$(cat utils/helper.py)"
askgpt /documentation "Generate README for this project"
```

## Skills

Skills are modular capabilities that extend nano-agent functionality. They are stored in `~/.askgpt/skills/` as directories containing `SKILL.md` files.

### Example: API Testing Skill
**Directory**: `skills/api-testing/`

A skill for generating comprehensive API tests:
- Endpoint testing
- Request/response validation
- Authentication testing
- Integration test scenarios

### Example: Data Analysis Skill
**Directory**: `skills/data-analysis/`

A skill for performing data analysis:
- Data exploration and cleaning
- Statistical analysis
- Visualization generation
- Insight extraction

### Example: Security Audit Skill
**Directory**: `skills/security-audit-example/`

A skill for security auditing:
- Vulnerability detection
- Authentication/authorization review
- Input validation checks
- Security best practices

### Skill Format

Skills use YAML frontmatter in `SKILL.md`:

```markdown
---
name: skill-name
description: When and how to use this skill.
tools: ["read_file", "write_file"]
---

# Skill Name

## Instructions

Detailed instructions for the skill...
```

### Using Skills

Skills are automatically matched based on user prompts. You can also:

```bash
# List available skills
askgpt skills list

# Show skill details
askgpt skills show api-testing

# Install builtin skills
askgpt skills install-builtin
```

## Installation

### Agents
Copy agent files to `~/.askgpt/agents/`:

```bash
cp examples/agents/*.md ~/.askgpt/agents/
```

### Commands
Copy command files to `~/.askgpt/commands/`:

```bash
cp examples/commands/*.md ~/.askgpt/commands/
```

### Skills
Copy skill directories to `~/.askgpt/skills/`:

```bash
cp -r examples/skills/* ~/.askgpt/skills/
```

## Customization

All examples can be customized:

1. **Edit the files** directly in your `.askgpt` directory
2. **Modify metadata** (name, description, tools)
3. **Adjust instructions** to match your workflow
4. **Add resources** (scripts, templates) to skills

## Best Practices

### Agents
- Keep personality descriptions clear and focused
- Define expertise areas explicitly
- Provide behavioral guidelines
- Include example interactions

### Commands
- Use descriptive names
- Include comprehensive prompt templates
- Document usage examples
- Specify required tools in metadata

### Skills
- Write clear, actionable instructions
- Include step-by-step workflows
- Provide example outputs
- Document best practices
- Specify all required tools

## More Information

- **Agents Documentation**: See `apps/nano_agent_mcp_server/AGENTS.md`
- **Commands Documentation**: See `apps/nano_agent_mcp_server/COMMANDS.md`
- **Skills Documentation**: See `apps/nano_agent_mcp_server/docs/SKILLS.md`

