---
name: code-review
description: Perform a thorough code review analyzing code quality, best practices, and potential improvements.
tools: ["read_file", "grep_search"]
---

# Code Review Command

Perform a comprehensive code review of the provided code or file.

## Prompt Template

Please perform a thorough code review of the following code: $ARGUMENTS

Focus on:
1. **Code Quality**
   - Readability and clarity
   - Code organization and structure
   - Naming conventions
   - Comments and documentation

2. **Best Practices**
   - Design patterns usage
   - Error handling
   - Security considerations
   - Performance optimizations

3. **Potential Issues**
   - Bugs and edge cases
   - Logic errors
   - Resource leaks
   - Race conditions (if applicable)

4. **Suggestions**
   - Refactoring opportunities
   - Test coverage gaps
   - Documentation improvements
   - Alternative approaches

Provide specific examples with line numbers where applicable.

## Usage

```bash
# Review code from a file
askgpt /code-review "$(cat src/main.py)"

# Review inline code
askgpt /code-review "def process(data): return data * 2"

# Review multiple files
askgpt /code-review "$(cat src/*.py)"
```

## Examples

```bash
# Review a specific function
askgpt /code-review "$(sed -n '10,30p' app.py)"

# Review an entire module
askgpt /code-review "$(cat utils/helpers.py)"
```

## Notes

- Use this command for peer review workflows
- Works best with complete, compilable code
- Can analyze multiple files at once
- Provides actionable feedback with examples

