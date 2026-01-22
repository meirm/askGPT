"""
Structure tests that don't require full dependency chain.
These tests verify the code structure and basic functionality.
"""

import ast
import json
import re
from pathlib import Path


def test_api_file_structure():
    """Test that api.py has the expected structure."""
    api_file = Path(__file__).parent.parent.parent.parent / "src" / "askgpt" / "api.py"
    assert api_file.exists(), "api.py should exist"
    
    content = api_file.read_text()
    
    # Check for AskGPTClient class
    assert "class AskGPTClient" in content, "Should have AskGPTClient class"
    
    # Check for required methods
    assert "async def chat(" in content, "Should have chat method"
    assert "async def chat_stream(" in content, "Should have chat_stream method"
    assert "def create_session(" in content, "Should have create_session method"
    assert "def get_session(" in content, "Should have get_session method"
    assert "def list_sessions(" in content, "Should have list_sessions method"
    
    # Check syntax
    ast.parse(content)
    print("✓ api.py structure is valid")


def test_web_server_structure():
    """Test that web_server.py has the expected structure."""
    ws_file = Path(__file__).parent.parent.parent.parent / "src" / "askgpt" / "web_server.py"
    assert ws_file.exists(), "web_server.py should exist"
    
    content = ws_file.read_text()
    
    # Check for FastAPI app
    assert "app = FastAPI(" in content, "Should create FastAPI app"
    
    # Check for endpoints
    endpoints = [
        ("@app.get", "/api/v1/health"),
        ("@app.post", "/api/v1/chat"),
        ("@app.get", "/api/v1/sessions"),
        ("@app.post", "/api/v1/sessions"),
        ("@app.websocket", "/api/v1/chat/stream"),
        ("@app.get", "/api/v1/chat/stream"),  # SSE
    ]
    
    for decorator, path in endpoints:
        pattern = f'{decorator}\\(["\']{re.escape(path)}'
        assert re.search(pattern, content), f"Should have {decorator} endpoint for {path}"
    
    # Check syntax
    ast.parse(content)
    print("✓ web_server.py structure is valid")


def test_cli_serve_command():
    """Test that CLI has serve command."""
    cli_file = Path(__file__).parent.parent.parent.parent / "src" / "askgpt" / "cli.py"
    assert cli_file.exists(), "cli.py should exist"
    
    content = cli_file.read_text()
    
    # Check for serve command
    assert '@app.command("serve")' in content or '@app.command()' in content and 'def serve(' in content, \
        "Should have serve command"
    assert "uvicorn.run" in content, "Should use uvicorn to run server"
    
    print("✓ CLI serve command is present")


def test_regression_cases():
    """Test that regression cases JSON is valid."""
    cases_file = Path(__file__).parent / "regression_cases.json"
    assert cases_file.exists(), "regression_cases.json should exist"
    
    with open(cases_file) as f:
        cases = json.load(f)
    
    assert "test_cases" in cases, "Should have test_cases"
    assert len(cases["test_cases"]) > 0, "Should have at least one test case"
    assert "performance_baselines" in cases, "Should have performance_baselines"
    
    print(f"✓ Regression cases: {len(cases['test_cases'])} test cases loaded")


def test_init_exports():
    """Test that __init__.py exports correctly."""
    init_file = Path(__file__).parent.parent.parent.parent / "src" / "askgpt" / "__init__.py"
    assert init_file.exists(), "__init__.py should exist"
    
    content = init_file.read_text()
    
    # Check for exports
    assert "AskGPTClient" in content, "Should export AskGPTClient"
    assert "get_app" in content or "app" in content, "Should export app or get_app"
    
    print("✓ __init__.py exports are correct")


def test_example_files():
    """Test that example files exist and are valid."""
    # Go up from tests/askgpt/api/test_structure.py to project root
    # tests/askgpt/api -> tests/askgpt -> tests -> root (3 levels up)
    project_root = Path(__file__).parent.parent.parent.parent
    examples_dir = project_root / "examples"
    
    api_usage = examples_dir / "api_usage.py"
    web_chatbot = examples_dir / "web_chatbot.py"
    
    assert api_usage.exists(), f"api_usage.py should exist at {api_usage}"
    assert web_chatbot.exists(), f"web_chatbot.py should exist at {web_chatbot}"
    
    # Check syntax
    ast.parse(api_usage.read_text())
    ast.parse(web_chatbot.read_text())
    
    print("✓ Example files are valid")


def test_documentation():
    """Test that documentation exists."""
    # Go up from tests/askgpt/api/test_structure.py to project root
    project_root = Path(__file__).parent.parent.parent.parent
    docs_file = project_root / "docs" / "api.md"
    
    assert docs_file.exists(), f"api.md should exist at {docs_file}"
    
    content = docs_file.read_text()
    
    # Check for key sections
    assert "# askGPT Web API Documentation" in content, "Should have title"
    assert "REST Endpoints" in content, "Should document REST endpoints"
    assert "WebSocket" in content, "Should document WebSocket"
    
    print("✓ Documentation is present")


def test_config_example():
    """Test that config example exists."""
    # Go up from tests/askgpt/api/test_structure.py to project root
    project_root = Path(__file__).parent.parent.parent.parent
    config_file = project_root / "config" / "examples" / "web_server.yaml"
    
    assert config_file.exists(), f"web_server.yaml should exist at {config_file}"
    
    content = config_file.read_text()
    
    # Check for key settings
    assert "default_provider" in content, "Should have default_provider"
    assert "ollama" in content, "Should configure Ollama"
    
    print("✓ Config example is present")


if __name__ == "__main__":
    print("=" * 60)
    print("Running Structure Tests")
    print("=" * 60)
    
    tests = [
        test_api_file_structure,
        test_web_server_structure,
        test_cli_serve_command,
        test_regression_cases,
        test_init_exports,
        test_example_files,
        test_documentation,
        test_config_example,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        exit(1)
