"""
Minimal test of OpenAI SDK compatibility with multiple providers.

This test validates that the OpenAI SDK can be used with:
- Ollama (local models)
- Anthropic (Claude models)

No mocking - these are real API calls.
"""

import os

import pytest
from openai import OpenAI

# Load environment variables


class TestOllamaProvider:
    """Test OpenAI SDK with Ollama local models."""

    @pytest.mark.skipif(
        not os.path.exists("/usr/local/bin/ollama")
        and not os.path.exists("/usr/bin/ollama"),
        reason="Ollama not installed. Install from https://ollama.com/download",
    )
    def test_ollama_basic_chat(self):
        """Test basic chat completion with Ollama."""
        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # Required but unused
        )

        response = client.chat.completions.create(
            model="gpt-oss:20b",  # Assuming this model is pulled
            messages=[{"role": "user", "content": "Say hello in exactly one word"}],
            max_tokens=200,  # Increased significantly to allow model to complete
            temperature=0,
        )

        # Assert we got a response
        assert response.choices
        assert len(response.choices) > 0
        assert response.choices[0].message

        # Check for content or reasoning field (gpt-oss model may use reasoning)
        message = response.choices[0].message
        content = message.content or ""
        reasoning = getattr(message, "reasoning", "")

        # Either content or reasoning should have text
        assert (
            content or reasoning
        ), f"No content or reasoning in response. Message: {message}"

        # The response should contain some text
        actual_response = content.strip() if content else reasoning.strip()
        assert len(actual_response) > 0
        print(f"Ollama response: {actual_response[:100]}")

    @pytest.mark.skipif(
        not os.path.exists("/usr/local/bin/ollama")
        and not os.path.exists("/usr/bin/ollama"),
        reason="Ollama not installed. Install from https://ollama.com/download",
    )
    def test_ollama_with_system_message(self):
        """Test Ollama with system message."""
        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )

        response = client.chat.completions.create(
            model="gpt-oss:20b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that only responds with single words.",
                },
                {
                    "role": "user",
                    "content": "What is 2+2? Answer with just the number.",
                },
            ],
            max_tokens=200,  # Increased significantly to allow model to complete
            temperature=0,
        )

        # Check for content or reasoning field
        message = response.choices[0].message
        content = message.content or ""
        reasoning = getattr(message, "reasoning", "")

        actual_response = content.strip() if content else reasoning.strip()
        assert actual_response
        print(f"Ollama math response: {actual_response[:100]}")


class TestAnthropicProvider:
    """Test OpenAI SDK with Anthropic Claude models."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set"
    )
    def test_anthropic_basic_chat(self):
        """Test basic chat completion with Anthropic."""
        client = OpenAI(
            base_url="https://api.anthropic.com/v1/",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

        response = client.chat.completions.create(
            model="claude-3-haiku-20240307",
            messages=[{"role": "user", "content": "Say hello in exactly one word"}],
            max_tokens=10,
            temperature=0,
        )

        # Assert we got a response
        assert response.choices
        assert len(response.choices) > 0
        assert response.choices[0].message
        assert response.choices[0].message.content

        # The response should contain some text
        content = response.choices[0].message.content.strip()
        assert len(content) > 0
        print(f"Anthropic response: {content}")

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set"
    )
    def test_anthropic_with_system_message(self):
        """Test Anthropic with system message."""
        client = OpenAI(
            base_url="https://api.anthropic.com/v1/",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

        response = client.chat.completions.create(
            model="claude-3-haiku-20240307",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that only responds with single words.",
                },
                {
                    "role": "user",
                    "content": "What is 2+2? Answer with just the number.",
                },
            ],
            max_tokens=10,
            temperature=0,
        )

        assert response.choices[0].message.content
        content = response.choices[0].message.content.strip()
        print(f"Anthropic math response: {content}")
        # Could be "4" or "Four" depending on interpretation
        assert "4" in content.lower() or "four" in content.lower()


class TestOpenAIAgentSDKCompatibility:
    """Test if OpenAI Agent SDK can work with alternative providers."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set"
    )
    def test_agent_sdk_with_anthropic(self):
        """Attempt to use Agent SDK with Anthropic (may not work)."""
        try:
            from agents import Agent, Runner

            # This likely won't work as Agent SDK expects OpenAI models
            # but we test to document the behavior
            os.environ["OPENAI_BASE_URL"] = "https://api.anthropic.com/v1/"
            os.environ["OPENAI_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")

            agent = Agent(
                name="TestAgent",
                instructions="You are a helpful assistant.",
                model="claude-3-haiku-20240307",
            )

            result = Runner.run_sync(agent, "Say hello", max_turns=1)

            assert result
            print(f"Agent SDK with Anthropic: {result}")

        except Exception as e:
            # Expected to fail - Agent SDK is OpenAI-specific
            print(f"Agent SDK with Anthropic failed (expected): {e}")
            pytest.skip(f"Agent SDK doesn't support Anthropic: {e}")

    @pytest.mark.skipif(
        not os.path.exists("/usr/local/bin/ollama")
        and not os.path.exists("/usr/bin/ollama"),
        reason="Ollama not installed. Install from https://ollama.com/download",
    )
    def test_agent_sdk_with_ollama(self):
        """Attempt to use Agent SDK with Ollama (may not work)."""
        try:
            from agents import Agent, Runner

            # This likely won't work as Agent SDK expects OpenAI models
            os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
            os.environ["OPENAI_API_KEY"] = "ollama"

            agent = Agent(
                name="TestAgent",
                instructions="You are a helpful assistant.",
                model="gpt-oss:20b",
            )

            result = Runner.run_sync(agent, "Say hello", max_turns=1)

            assert result
            print(f"Agent SDK with Ollama: {result}")

        except Exception as e:
            # Expected to fail - Agent SDK is OpenAI-specific
            print(f"Agent SDK with Ollama failed (expected): {e}")
            pytest.skip(f"Agent SDK doesn't support Ollama: {e}")


def test_providers_documented():
    """Test that we have documented how to use alternative providers."""
    # Check that our documentation files exist
    docs_dir = "/Users/indydevdan/Documents/projects/experimental/nano-agent/ai_docs"

    assert os.path.exists(f"{docs_dir}/anthropic_openai_compat.md")
    assert os.path.exists(f"{docs_dir}/ollama_openai_compat.md")

    # Verify basic content
    with open(f"{docs_dir}/anthropic_openai_compat.md") as f:
        content = f.read()
        assert "claude-3-haiku-20240307" in content
        assert "base_url" in content
        assert "https://api.anthropic.com/v1/" in content

    with open(f"{docs_dir}/ollama_openai_compat.md") as f:
        content = f.read()
        assert "http://localhost:11434/v1" in content
        assert "ollama pull" in content


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
