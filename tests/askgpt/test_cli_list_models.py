"""Tests for CLI list-models command."""

import json
import os

import pytest
from askgpt.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestListModelsCommand:
    """Test the list-models CLI command."""

    def test_list_models_help(self):
        """Test list-models help text."""
        result = runner.invoke(app, ["list-models", "--help"])
        assert result.exit_code == 0
        assert "List available models" in result.stdout

    def test_list_models_anthropic(self):
        """Test listing models from Anthropic (hardcoded list)."""
        # This should work even without an API key since Anthropic models are hardcoded
        result = runner.invoke(app, ["list-models", "--provider", "anthropic"])

        assert result.exit_code == 0
        assert "anthropic" in result.stdout.lower()
        # Check for some expected Anthropic models
        assert "claude-3" in result.stdout.lower() or "claude" in result.stdout.lower()

    def test_list_models_json_output(self):
        """Test JSON output format with Anthropic."""
        # Use Anthropic since it doesn't require API connection
        result = runner.invoke(
            app, ["list-models", "--provider", "anthropic", "--format", "json"]
        )

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.stdout)
        assert isinstance(output_data, list)
        assert len(output_data) > 0

        # Check structure of first model
        first_model = output_data[0]
        assert "id" in first_model
        assert "provider" in first_model
        assert first_model["provider"] == "anthropic"

    @pytest.mark.skipif(
        not os.environ.get("OLLAMA_API_URL"), reason="Ollama not available"
    )
    def test_list_models_ollama(self):
        """Test listing models from Ollama if available."""
        result = runner.invoke(app, ["list-models", "--provider", "ollama"])

        # If Ollama is not running, it should fail gracefully
        if result.exit_code != 0:
            assert "Could not connect" in result.stdout or "Connection" in result.stdout
        else:
            assert "ollama" in result.stdout.lower()

    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"), reason="OpenAI API key not set"
    )
    def test_list_models_openai(self):
        """Test listing models from OpenAI if API key is available."""
        result = runner.invoke(app, ["list-models", "--provider", "openai"])

        if result.exit_code == 0:
            assert "openai" in result.stdout.lower()
            # Check for some expected OpenAI models
            assert "gpt" in result.stdout.lower()
        else:
            # Should show authentication error
            assert "Authentication" in result.stdout or "API" in result.stdout

    def test_list_models_all_providers(self):
        """Test listing models from all providers."""
        result = runner.invoke(app, ["list-models", "--all"])

        assert result.exit_code == 0
        # Should at least show Anthropic models since they're hardcoded
        assert "anthropic" in result.stdout.lower()

    def test_list_models_verbose(self):
        """Test verbose output."""
        result = runner.invoke(
            app, ["list-models", "--provider", "anthropic", "--verbose"]
        )

        assert result.exit_code == 0
        # Verbose mode should show additional columns
        assert "Context" in result.stdout or "Capabilities" in result.stdout
        # Should show summary
        assert "Total models:" in result.stdout

    def test_list_models_filter_by_capability(self):
        """Test filtering models by capability."""
        # Anthropic models have capabilities defined
        result = runner.invoke(
            app,
            [
                "list-models",
                "--provider",
                "anthropic",
                "--capability",
                "chat",
                "--format",
                "json",
            ],
        )

        if result.exit_code == 0:
            output_data = json.loads(result.stdout)
            # All returned models should have 'chat' capability
            for model in output_data:
                if model.get("capabilities"):
                    assert "chat" in model["capabilities"]

    def test_list_models_provider_not_found(self):
        """Test error handling for unknown provider."""
        result = runner.invoke(app, ["list-models", "--provider", "unknown-provider"])

        assert result.exit_code != 0
        assert (
            "not found" in result.stdout.lower() or "unknown" in result.stdout.lower()
        )
        assert "Available providers:" in result.stdout

    def test_list_models_show_deprecated(self):
        """Test showing deprecated models."""
        # Test with show-deprecated flag
        result = runner.invoke(
            app,
            [
                "list-models",
                "--provider",
                "anthropic",
                "--show-deprecated",
                "--format",
                "json",
            ],
        )

        if result.exit_code == 0:
            output_data = json.loads(result.stdout)
            # Check if deprecated field exists in output
            if output_data:
                assert "deprecated" in output_data[0]
