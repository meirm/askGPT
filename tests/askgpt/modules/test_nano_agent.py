"""
Tests for Nano Agent MCP Server Tools.

These are integration tests that actually call the OpenAI API.
"""


import pytest
from askgpt.modules.data_types import PromptNanoAgentRequest
from askgpt.modules.nano_agent import (_execute_nano_agent,
                                           get_agent_status, prompt_nano_agent,
                                           validate_model_provider_combination)

# Load environment variables from .env file


class TestExecuteNanoAgent:
    """Test the internal _execute_nano_agent function with real API calls."""

    def test_execute_nano_agent_success(self):
        """Test successful execution with valid request."""
        request = PromptNanoAgentRequest(
            agentic_prompt="Say 'Hello, World!' in exactly 2 words",
            model="gpt-5-mini",  # Use efficient model for tests
            provider="openai",
        )

        response = _execute_nano_agent(request)

        assert response.success is True
        assert response.error is None
        assert response.result is not None
        assert len(response.result) > 0
        assert response.metadata["model"] == "gpt-5-mini"
        assert response.metadata["provider"] == "openai"
        assert response.execution_time_seconds >= 0

    def test_execute_nano_agent_with_tools(self):
        """Test execution that uses tools."""
        request = PromptNanoAgentRequest(
            agentic_prompt="List the current directory",
            model="gpt-5-mini",
            provider="openai",
        )

        response = _execute_nano_agent(request)

        assert response.success is True
        assert response.metadata["turns_used"] >= 1

    def test_execute_nano_agent_different_models(self):
        """Test execution with different model configurations."""
        # Just test one model to save API costs
        request = PromptNanoAgentRequest(
            agentic_prompt="What is 2+2? Answer with just the number.",
            model="gpt-5-mini",
            provider="openai",
        )

        response = _execute_nano_agent(request)

        assert response.success is True
        assert "4" in response.result


class TestPromptNanoAgentTool:
    """Test the MCP tool prompt_nano_agent with real API."""

    @pytest.mark.asyncio
    async def test_prompt_nano_agent_basic(self):
        """Test basic execution without context."""
        result = await prompt_nano_agent(
            agentic_prompt="What is 1+1? Answer with just the number.",
            model="gpt-5-mini",
            provider="openai",
        )

        assert result["success"] is True
        assert "error" not in result or result["error"] is None
        assert "2" in result["result"]
        assert result["execution_time_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_prompt_nano_agent_default_parameters(self):
        """Test that default parameters work."""
        result = await prompt_nano_agent(agentic_prompt="Say hello")

        assert result["success"] is True
        assert result["result"] is not None

    @pytest.mark.asyncio
    async def test_prompt_nano_agent_invalid_provider(self):
        """Test error handling for invalid provider."""
        result = await prompt_nano_agent(
            agentic_prompt="Test", provider="invalid_provider"
        )

        assert result["success"] is False
        assert "Input should be 'openai' or 'anthropic'" in result["error"]


class TestUtilityFunctions:
    """Test utility functions."""

    def test_validate_model_provider_combination_valid(self):
        """Test validation of valid model-provider combinations."""
        valid_combos = [
            ("gpt-5-mini", "openai"),
            ("gpt-5-nano", "openai"),
            ("gpt-5", "openai"),
        ]

        for model, provider in valid_combos:
            assert validate_model_provider_combination(model, provider) is True

    def test_validate_model_provider_combination_invalid(self):
        """Test validation of invalid model-provider combinations."""
        invalid_combos = [
            ("gpt-5", "anthropic"),  # Wrong provider
            ("claude-3-opus", "openai"),  # Wrong provider
            ("gpt-6", "openai"),  # Non-existent model
        ]

        for model, provider in invalid_combos:
            assert validate_model_provider_combination(model, provider) is False

    @pytest.mark.asyncio
    async def test_get_agent_status(self):
        """Test agent status retrieval."""
        status = await get_agent_status()

        assert status["status"] == "operational"
        assert status["version"] == "1.0.0"
        assert "gpt-5-mini" in status["available_models"]
        assert "openai" in status["available_providers"]
        assert "read_file" in status["tools_available"]
        assert "write_file" in status["tools_available"]


class TestIntegration:
    """Integration tests for the MCP tools with real API."""

    @pytest.mark.asyncio
    async def test_simple_task(self):
        """Test a simple task."""
        result = await prompt_nano_agent(
            agentic_prompt="What is the capital of France? Answer with just the city name.",
            model="gpt-5-mini",
        )

        assert result["success"] is True
        assert "Paris" in result["result"]
        assert result["execution_time_seconds"] >= 0
        assert "timestamp" in result["metadata"]
