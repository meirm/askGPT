"""Tests for the output formatting system."""

import json

from askgpt.modules.output_formats import (AgentResponse, BillingInfo,
                                               JSONFormatter, OutputFormat,
                                               RichFormatter, SimpleFormatter,
                                               clean_agent_output,
                                               create_formatter)


class TestOutputFormat:
    """Test the OutputFormat enum."""

    def test_enum_values(self):
        """Test that enum values are correct."""
        assert OutputFormat.SIMPLE.value == "simple"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.RICH.value == "rich"

    def test_from_string(self):
        """Test creating OutputFormat from string."""
        assert OutputFormat.from_string("simple") == OutputFormat.SIMPLE
        assert OutputFormat.from_string("JSON") == OutputFormat.JSON
        assert OutputFormat.from_string("rich") == OutputFormat.RICH

    def test_from_string_invalid_defaults_to_rich(self):
        """Test that invalid string defaults to rich."""
        assert OutputFormat.from_string("invalid") == OutputFormat.RICH
        assert OutputFormat.from_string("") == OutputFormat.RICH


class TestBillingInfo:
    """Test the BillingInfo dataclass."""

    def test_default_values(self):
        """Test that default values are correct."""
        billing = BillingInfo()
        assert billing.total_tokens == 0
        assert billing.total_cost == 0.0
        assert billing.cached_tokens == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        billing = BillingInfo(
            total_tokens=1000, input_tokens=800, output_tokens=200, total_cost=0.002
        )
        result = billing.to_dict()

        assert result["total_tokens"] == "1,000"
        assert result["input_tokens"] == "800"
        assert result["output_tokens"] == "200"
        assert result["total_cost"] == "$0.0020"

    def test_to_simple_string(self):
        """Test conversion to simple string."""
        billing = BillingInfo(total_tokens=1500, total_cost=0.003)
        result = billing.to_simple_string()

        assert "Tokens: 1,500" in result
        assert "Cost: $0.0030" in result

    def test_to_simple_string_empty(self):
        """Test that empty billing returns empty string."""
        billing = BillingInfo()
        assert billing.to_simple_string() == ""


class TestAgentResponse:
    """Test the AgentResponse dataclass."""

    def test_basic_response(self):
        """Test basic response creation."""
        response = AgentResponse(
            success=True, message="Test completed", data="Test result"
        )

        assert response.success is True
        assert response.message == "Test completed"
        assert response.data == "Test result"

    def test_to_dict_without_billing(self):
        """Test conversion to dict without billing."""
        response = AgentResponse(success=True, message="Success", data="Result data")

        result = response.to_dict(include_billing=False)

        assert result["success"] is True
        assert result["message"] == "Success"
        assert result["data"] == "Result data"
        assert "billing" not in result

    def test_to_dict_with_billing(self):
        """Test conversion to dict with billing."""
        billing = BillingInfo(total_tokens=100, total_cost=0.001)
        response = AgentResponse(
            success=True, message="Success", data="Result", billing=billing
        )

        result = response.to_dict(include_billing=True)

        assert "billing" in result
        assert result["billing"]["total_tokens"] == "100"
        assert result["billing"]["total_cost"] == "$0.0010"

    def test_to_dict_with_metadata(self):
        """Test conversion to dict with metadata."""
        response = AgentResponse(
            success=True,
            message="Success",
            metadata={"model": "test-model", "provider": "test"},
        )

        result = response.to_dict()

        assert "metadata" in result
        assert result["metadata"]["model"] == "test-model"

    def test_to_dict_with_error(self):
        """Test conversion to dict with error."""
        response = AgentResponse(
            success=False, message="Failed", error="Something went wrong"
        )

        result = response.to_dict()

        assert result["success"] is False
        assert result["error"] == "Something went wrong"


class TestSimpleFormatter:
    """Test the SimpleFormatter class."""

    def test_format_success_response(self):
        """Test formatting successful response."""
        formatter = SimpleFormatter(show_billing=False)
        response = AgentResponse(
            success=True, message="Operation completed", data="Result data here"
        )

        output = formatter.format_response(response)

        assert "Operation completed" in output
        assert "Result data here" in output

    def test_format_error_response(self):
        """Test formatting error response."""
        formatter = SimpleFormatter()
        response = AgentResponse(success=False, error="Something failed")

        output = formatter.format_response(response)

        assert "Error: Something failed" in output

    def test_format_with_billing(self):
        """Test formatting with billing information."""
        formatter = SimpleFormatter(show_billing=True)
        billing = BillingInfo(total_tokens=500, total_cost=0.001)
        response = AgentResponse(
            success=True, message="Success", data="Result", billing=billing
        )

        output = formatter.format_response(response)

        assert "Success" in output
        assert "Result" in output
        assert "[Tokens: 500 | Cost: $0.0010]" in output

    def test_format_with_execution_time(self):
        """Test formatting with execution time."""
        formatter = SimpleFormatter()
        response = AgentResponse(success=True, message="Done", execution_time=3.14159)

        output = formatter.format_response(response)

        assert "[Time: 3.14s]" in output

    def test_format_error(self):
        """Test formatting standalone error."""
        formatter = SimpleFormatter()
        output = formatter.format_error("Test error")
        assert output == "Error: Test error"

    def test_format_info(self):
        """Test formatting info message."""
        formatter = SimpleFormatter()
        output = formatter.format_info("Info message")
        assert output == "Info message"


class TestJSONFormatter:
    """Test the JSONFormatter class."""

    def test_format_response_basic(self):
        """Test basic JSON formatting."""
        formatter = JSONFormatter(show_billing=False, pretty=False)
        response = AgentResponse(success=True, message="Test", data="Result")

        output = formatter.format_response(response)
        result = json.loads(output)

        assert result["success"] is True
        assert result["message"] == "Test"
        assert result["data"] == "Result"

    def test_format_response_with_billing(self):
        """Test JSON formatting with billing."""
        formatter = JSONFormatter(show_billing=True, pretty=False)
        billing = BillingInfo(total_tokens=100)
        response = AgentResponse(success=True, message="Test", billing=billing)

        output = formatter.format_response(response)
        result = json.loads(output)

        assert "billing" in result
        assert result["billing"]["total_tokens"] == "100"

    def test_format_pretty_json(self):
        """Test pretty JSON formatting."""
        formatter = JSONFormatter(pretty=True)
        response = AgentResponse(success=True, message="Test")

        output = formatter.format_response(response)

        # Pretty JSON should have newlines and indentation
        assert "\n" in output
        assert "  " in output  # indentation

    def test_format_error_json(self):
        """Test JSON error formatting."""
        formatter = JSONFormatter(pretty=False)
        output = formatter.format_error("Test error")

        result = json.loads(output)
        assert result["success"] is False
        assert result["error"] == "Test error"

    def test_format_info_json(self):
        """Test JSON info formatting."""
        formatter = JSONFormatter(pretty=False)
        output = formatter.format_info("Test info")

        result = json.loads(output)
        assert result["success"] is True
        assert result["message"] == "Test info"


class TestCreateFormatter:
    """Test the create_formatter factory function."""

    def test_create_simple_formatter(self):
        """Test creating simple formatter."""
        formatter = create_formatter(OutputFormat.SIMPLE, show_billing=True)
        assert isinstance(formatter, SimpleFormatter)
        assert formatter.show_billing is True

    def test_create_json_formatter(self):
        """Test creating JSON formatter."""
        formatter = create_formatter(OutputFormat.JSON, show_billing=False)
        assert isinstance(formatter, JSONFormatter)
        assert formatter.show_billing is False

    def test_create_rich_formatter(self):
        """Test creating rich formatter."""
        formatter = create_formatter(OutputFormat.RICH)
        assert isinstance(formatter, RichFormatter)

    def test_create_formatter_default(self):
        """Test that invalid format defaults to rich."""
        # This would need to be handled by the enum validation
        formatter = create_formatter(OutputFormat.RICH)
        assert isinstance(formatter, RichFormatter)


class TestContentCleaning:
    """Test the content cleaning functionality for removing thinking text."""

    def test_clean_agent_output_with_user_assistant_markers(self):
        """Test cleaning output with #### user and #### assistant markers."""
        raw_output = """#### user
What is 2+2?

#### assistant
Let me calculate that for you.

2 + 2 = 4"""

        expected = """Let me calculate that for you.

2 + 2 = 4"""

        cleaned = clean_agent_output(raw_output, show_thinking=False)
        assert cleaned == expected

    def test_clean_agent_output_preserve_when_show_thinking(self):
        """Test that content is preserved when show_thinking is True."""
        raw_output = """#### user
Hello

#### assistant
Hello! How can I help you?"""

        cleaned = clean_agent_output(raw_output, show_thinking=True)
        assert cleaned == raw_output

    def test_clean_agent_output_with_thinking_tags(self):
        """Test cleaning output with <thinking> tags."""
        raw_output = """<thinking>
I need to calculate 2+2. This is a simple addition.
</thinking>

The answer is 4."""

        expected = "The answer is 4."
        cleaned = clean_agent_output(raw_output, show_thinking=False)
        assert cleaned == expected

    def test_clean_agent_output_with_let_me_think(self):
        """Test cleaning 'Let me think' patterns."""
        raw_output = """Let me think about this problem step by step.

The solution is to use recursion."""

        expected = "The solution is to use recursion."
        cleaned = clean_agent_output(raw_output, show_thinking=False)
        assert cleaned == expected

    def test_clean_agent_output_with_mixed_patterns(self):
        """Test cleaning output with multiple pattern types."""
        raw_output = """#### user
Explain recursion

#### assistant
<thinking>
This is a complex topic. I should provide a clear explanation.
</thinking>

Let me explain recursion clearly.

Recursion is a programming technique where a function calls itself."""

        expected = "Recursion is a programming technique where a function calls itself."
        cleaned = clean_agent_output(raw_output, show_thinking=False)
        assert cleaned == expected

    def test_clean_agent_output_normalize_whitespace(self):
        """Test that excessive whitespace is normalized."""
        raw_output = """#### user
Test



#### assistant


The answer is here.



With extra spaces."""

        expected = """The answer is here.

With extra spaces."""
        cleaned = clean_agent_output(raw_output, show_thinking=False)
        assert cleaned == expected

    def test_clean_agent_output_empty_after_cleaning(self):
        """Test handling when all content is thinking text."""
        raw_output = """#### user
Test

#### assistant"""

        cleaned = clean_agent_output(raw_output, show_thinking=False)
        assert cleaned == ""

    def test_clean_agent_output_with_code_blocks(self):
        """Test that code blocks are preserved during cleaning."""
        raw_output = """#### user
Write hello world

#### assistant
Here's the code:

```python
print("Hello, World!")
```

This prints a greeting."""

        expected = """Here's the code:

```python
print("Hello, World!")
```

This prints a greeting."""

        cleaned = clean_agent_output(raw_output, show_thinking=False)
        assert cleaned == expected

    def test_clean_agent_output_with_special_a_pattern(self):
        """Test cleaning the special 'A' pattern from user examples."""
        raw_output = """Hello! I'm here to help.

  A
#### user
No specific task, just a greeting.

#### assistant
Great! Feel free to ask if you need anything."""

        expected = """Hello! I'm here to help.

Great! Feel free to ask if you need anything."""

        cleaned = clean_agent_output(raw_output, show_thinking=False)
        assert cleaned == expected
