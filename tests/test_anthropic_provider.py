#!/usr/bin/env python
"""
Test script for Anthropic provider with nano-agent.

This test validates that the Anthropic provider works correctly
through both CLI and MCP interfaces.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askgpt.modules.data_types import PromptNanoAgentRequest
from askgpt.modules.nano_agent import (_execute_nano_agent,
                                           prompt_nano_agent)


def test_anthropic_cli():
    """Test Anthropic provider through CLI interface."""
    print("\n=== Testing Anthropic through CLI ===")

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set")
        return False

    # Create a simple request
    request = PromptNanoAgentRequest(
        agentic_prompt="List the files in the current directory",
        model="claude-3-haiku-20240307",
        provider="anthropic",
    )

    try:
        # Execute without rich logging to see raw output
        response = _execute_nano_agent(request, enable_rich_logging=False)

        if response.success:
            print("✅ CLI test passed!")
            print(f"   Model: {response.metadata.get('model')}")
            print(f"   Provider: {response.metadata.get('provider')}")
            print(f"   Execution time: {response.execution_time_seconds:.2f}s")
            return True
        else:
            print(f"❌ CLI test failed: {response.error}")
            print(f"   Error type: {response.metadata.get('error_type')}")
            return False

    except Exception as e:
        print(f"❌ CLI test error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_anthropic_mcp():
    """Test Anthropic provider through MCP interface."""
    print("\n=== Testing Anthropic through MCP ===")

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set")
        return False

    try:
        # Call through MCP interface
        result = await prompt_nano_agent(
            agentic_prompt="Create a simple test file called anthropic_test.txt with the content 'Hello from Claude'",
            model="claude-3-haiku-20240307",
            provider="anthropic",
        )

        if result["success"]:
            print("✅ MCP test passed!")
            print(f"   Model: {result['metadata'].get('model')}")
            print(f"   Provider: {result['metadata'].get('provider')}")
            print(f"   Execution time: {result['execution_time_seconds']:.2f}s")

            # Clean up test file
            test_file = Path("anthropic_test.txt")
            if test_file.exists():
                test_file.unlink()
                print("   Cleaned up test file")

            return True
        else:
            print(f"❌ MCP test failed: {result['error']}")
            print(f"   Error type: {result['metadata'].get('error_type')}")
            return False

    except Exception as e:
        print(f"❌ MCP test error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_python_version():
    """Check Python version."""
    print("\n=== Python Version Check ===")
    print(f"Python version: {sys.version}")

    if sys.version_info < (3, 11):
        print("⚠️  Warning: Python 3.11+ recommended for best compatibility")
        return False
    else:
        print("✅ Python version OK")
        return True


def test_packages():
    """Check package versions."""
    print("\n=== Package Versions ===")

    try:
        import openai
        import openai_agents as agents
        import pydantic

        print(f"✅ openai: {openai.__version__}")
        print(f"✅ openai-agents: {agents.__version__}")
        print(f"✅ pydantic: {pydantic.__version__}")

        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 50)
    print("Anthropic Provider Test Suite")
    print("=" * 50)

    results = []

    # Run tests
    results.append(("Python Version", test_python_version()))
    results.append(("Package Check", test_packages()))
    results.append(("CLI Interface", test_anthropic_cli()))
    results.append(("MCP Interface", await test_anthropic_mcp()))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")

    return all_passed


if __name__ == "__main__":
    # Load environment variables

    # Run tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
