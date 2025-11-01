---
name: test-generator
description: Generate comprehensive unit tests for the provided code with edge cases and error handling.
tools: ["read_file", "write_file"]
---

# Test Generator Command

Generate comprehensive unit tests for code, including edge cases and error handling.

## Prompt Template

Please generate comprehensive unit tests for the following code: $ARGUMENTS

Requirements:
1. **Test Coverage**
   - Main functionality tests
   - Edge cases and boundary conditions
   - Error handling and exception cases
   - Integration scenarios

2. **Test Structure**
   - Use appropriate testing framework (pytest, unittest, jest, etc.)
   - Clear test names describing what is being tested
   - Arrange-Act-Assert pattern
   - Proper test fixtures and setup/teardown

3. **Test Quality**
   - Assertions should be specific and meaningful
   - Test one concept per test case
   - Include both positive and negative test cases
   - Mock external dependencies appropriately

4. **Additional Considerations**
   - Test data and fixtures needed
   - Performance tests if applicable
   - Documentation for test setup

Provide the complete test file(s) with imports and proper structure.

## Usage

```bash
# Generate tests for a function
askgpt /test-generator "$(cat src/calculator.py)"

# Generate tests with specific framework
askgpt /test-generator "$(cat api/endpoints.py)" --model gpt-5
```

## Examples

```bash
# Generate tests for a class
askgpt /test-generator "$(cat models/user.py)"

# Generate tests for an entire module
askgpt /test-generator "$(cat utils/validator.py)"
```

## Notes

- Automatically detects language and uses appropriate framework
- Includes both unit and integration test suggestions
- Provides test data examples
- Can generate test files ready to save

