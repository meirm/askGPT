"""
Regression test suite for API functionality.

Tests known working scenarios and catches breaking changes.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from askgpt.modules.data_types import PromptNanoAgentResponse
from askgpt.web_server import app


def load_regression_cases() -> Dict[str, Any]:
    """Load regression test cases from JSON file."""
    cases_file = Path(__file__).parent / "regression_cases.json"
    with open(cases_file, "r") as f:
        return json.load(f)


@pytest.fixture
def regression_cases() -> Dict[str, Any]:
    """Load regression test cases."""
    return load_regression_cases()


class TestRegressionSuite:
    """Regression test suite."""

    @pytest.mark.regression
    def test_regression_001_basic_chat(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Basic chat response."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_001")
        
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            start_time = time.time()
            response = test_client.post("/api/v1/chat", json=case["request"])
            response_time = time.time() - start_time
            
            assert response.status_code == 200
            data = response.json()
            
            # Check expected conditions
            expected = case["expected"]
            assert data["success"] == expected["success"]
            
            if "contains" in expected:
                response_text = data["response"].lower()
                for keyword in expected["contains"]:
                    assert keyword.lower() in response_text, f"Response should contain '{keyword}'"
            
            if "max_response_time" in expected:
                assert response_time <= expected["max_response_time"], \
                    f"Response time {response_time}s exceeds max {expected['max_response_time']}s"
            
            if expected.get("has_session_id"):
                assert "session_id" in data
                assert data["session_id"] is not None

    @pytest.mark.regression
    def test_regression_002_session_persistence(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Session persistence."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_002")
        
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            # First request
            response1 = test_client.post("/api/v1/chat", json=case["request"])
            assert response1.status_code == 200
            data1 = response1.json()
            session_id = data1["session_id"]
            
            # Follow-up request with same session
            follow_up = case["follow_up"]
            request2 = follow_up["message"]
            response2 = test_client.post(
                "/api/v1/chat",
                json={
                    "message": request2,
                    "session_id": session_id,
                    "provider": case["request"]["provider"],
                    "model": case["request"]["model"],
                },
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Check expected conditions
            expected = case["expected"]
            if "follow_up_contains" in expected:
                response_text = data2["response"].lower()
                for keyword in expected["follow_up_contains"]:
                    assert keyword.lower() in response_text, \
                        f"Follow-up response should contain '{keyword}'"
            
            if expected.get("session_persists"):
                assert data2["session_id"] == session_id

    @pytest.mark.regression
    def test_regression_003_error_handling(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Error handling."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_003")
        
        # Empty message should be rejected by validation
        response = test_client.post("/api/v1/chat", json=case["request"])
        
        # Should return validation error (422) or handle gracefully
        assert response.status_code in [422, 400, 500]
        
        if response.status_code == 500:
            # If it's a server error, check error message
            data = response.json()
            expected = case["expected"]
            if expected.get("has_error"):
                assert "detail" in data or "error" in data

    @pytest.mark.regression
    def test_regression_004_parameter_validation(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Parameter validation."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_004")
        
        # Invalid temperature (3.0 > 2.0) should be rejected
        response = test_client.post("/api/v1/chat", json=case["request"])
        
        expected = case["expected"]
        if expected.get("validates") is False:
            # Should return validation error
            assert response.status_code == 422

    @pytest.mark.regression
    def test_regression_006_session_creation(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Session creation."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_006")
        
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            start_time = time.time()
            response = test_client.post(
                case["request"]["endpoint"].replace("/api/v1", ""),
                json=case["request"]["body"],
            )
            response_time = time.time() - start_time
            
            expected = case["expected"]
            assert response.status_code == expected["status_code"]
            
            data = response.json()
            if expected.get("has_session_id"):
                assert "session_id" in data
                assert data["session_id"] is not None
            
            if expected.get("provider_matches"):
                assert data["provider"] == case["request"]["body"]["provider"]
            
            if expected.get("model_matches"):
                assert data["model"] == case["request"]["body"]["model"]
            
            # Check performance baseline
            baseline = regression_cases["performance_baselines"]["session_creation_time"]
            assert response_time <= baseline * 2, \
                f"Session creation time {response_time}s exceeds baseline {baseline}s"

    @pytest.mark.regression
    def test_regression_007_session_retrieval(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Session retrieval."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_007")
        
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            # Create session first
            session = client.create_session(provider="ollama", model="gpt-oss:20b")
            mock_get_client.return_value = client
            
            start_time = time.time()
            response = test_client.get(
                f"/api/v1/sessions/{session.session_id}"
            )
            response_time = time.time() - start_time
            
            expected = case["expected"]
            assert response.status_code == expected["status_code"]
            
            data = response.json()
            if expected.get("has_session_data"):
                assert "session_id" in data
                assert "provider" in data
                assert "model" in data
            
            if expected.get("has_conversation"):
                assert "message_count" in data
            
            # Check performance baseline
            baseline = regression_cases["performance_baselines"]["session_retrieval_time"]
            assert response_time <= baseline * 2, \
                f"Session retrieval time {response_time}s exceeds baseline {baseline}s"

    @pytest.mark.regression
    def test_regression_008_health_check(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Health check."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_008")
        
        response = test_client.get(case["request"]["endpoint"].replace("/api/v1", ""))
        
        expected = case["expected"]
        assert response.status_code == expected["status_code"]
        
        data = response.json()
        assert data["status"] == expected["status"]
        
        if expected.get("has_version"):
            assert "version" in data

    @pytest.mark.regression
    def test_regression_009_models_listing(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Models listing."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_009")
        
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            response = test_client.get(case["request"]["endpoint"].replace("/api/v1", ""))
            
        expected = case["expected"]
        assert response.status_code == expected["status_code"]
        
        data = response.json()
        if expected.get("has_default_provider"):
            assert "default_provider" in data
        
        if expected.get("has_default_model"):
            assert "default_model" in data
        
        if expected.get("has_providers"):
            assert "providers" in data
            assert isinstance(data["providers"], dict)

    @pytest.mark.regression
    def test_regression_010_read_only_mode(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Regression test: Read-only mode."""
        case = next(c for c in regression_cases["test_cases"] if c["id"] == "regression_010")
        
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            response = test_client.post("/api/v1/chat", json=case["request"])
            
            # Read-only mode should be respected
            # The agent should not be able to write files
            expected = case["expected"]
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == expected["success"]
            # Note: Actual write blocking is tested in agent execution tests


class TestPerformanceBaselines:
    """Test performance baselines from regression cases."""

    @pytest.mark.regression
    def test_chat_response_time_baseline(
        self, test_client: TestClient, regression_cases: Dict[str, Any]
    ):
        """Test that chat response time meets baseline."""
        baseline = regression_cases["performance_baselines"]["chat_response_time"]
        
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            start_time = time.time()
            response = test_client.post(
                "/api/v1/chat",
                json={"message": "Test performance", "provider": "ollama", "model": "gpt-oss:20b"},
            )
            response_time = time.time() - start_time
            
            # Allow 2x baseline for test environment
            assert response_time <= baseline * 2, \
                f"Response time {response_time}s exceeds baseline {baseline}s"
