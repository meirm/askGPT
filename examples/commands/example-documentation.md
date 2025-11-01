---
name: documentation
description: Generate comprehensive documentation including API docs, code comments, and README content.
tools: ["read_file", "write_file"]
---

# Documentation Command

Generate comprehensive documentation for code, APIs, or projects.

## Prompt Template

Please generate comprehensive documentation for: $ARGUMENTS

Include:
1. **Code Documentation**
   - Function/class docstrings
   - Parameter descriptions
   - Return value documentation
   - Usage examples
   - Error conditions

2. **API Documentation** (if applicable)
   - Endpoint descriptions
   - Request/response formats
   - Authentication requirements
   - Rate limits and constraints

3. **Project Documentation** (if applicable)
   - README with setup instructions
   - Architecture overview
   - Configuration guide
   - Contributing guidelines

4. **Additional Documentation**
   - Code comments for complex logic
   - Inline documentation
   - Example code snippets
   - Troubleshooting guide

Format documentation according to language conventions (JSDoc, Python docstrings, etc.).

## Usage

```bash
# Document a specific file
askgpt /documentation "$(cat src/api.py)"

# Generate README for project
askgpt /documentation "Generate README for this Python project with setup and usage"

# Document an API endpoint
askgpt /documentation "$(cat routes/users.py)"
```

## Examples

```bash
# Generate API documentation
askgpt /documentation "$(cat app/api/routes.py)"

# Generate comprehensive project docs
askgpt /documentation "Create full documentation for this FastAPI application"
```

## Notes

- Adapts documentation style to the code language
- Includes practical examples
- Follows language-specific documentation conventions
- Can generate multiple documentation files

