# Test

Generate comprehensive test cases and unit tests for code.

## Prompt Template

Please create comprehensive test cases for the following code or functionality: $ARGUMENTS

Include:
1. Unit tests covering main functionality
2. Edge case tests
3. Error handling tests
4. Integration test suggestions if applicable
5. Test data and fixtures needed
6. Expected outcomes for each test

Use appropriate testing framework syntax (pytest, unittest, etc.) based on the language.

## Usage

```bash
askgpt /test "code to test"
askgpt /test "$(cat module.py)"
```

## Examples

```bash
# Generate tests for a function
askgpt /test "def add(a, b): return a + b"

# Generate tests for a class
askgpt /test "$(cat user_service.py)"
```

## Notes

This command helps ensure code quality by generating comprehensive test coverage.