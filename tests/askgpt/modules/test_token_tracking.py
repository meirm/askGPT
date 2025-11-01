"""
Tests for Token Tracking Module.

Tests token usage tracking, cost calculation, and reporting functionality.
"""

from datetime import datetime, timedelta

import pytest
from askgpt.modules.token_tracking import (MODEL_PRICING,
                                               InputTokensDetails,
                                               OutputTokensDetails,
                                               TokenTracker, TokenUsageReport,
                                               Usage, format_cost,
                                               format_token_count)


class TestTokenTracker:
    """Test the TokenTracker class."""

    def test_initialization(self):
        """Test tracker initialization with different models."""
        # Default initialization
        tracker = TokenTracker()
        assert tracker.model == "gpt-5-mini"
        assert tracker.provider == "openai"
        assert tracker.total_usage.total_tokens == 0

        # Custom model
        tracker = TokenTracker(model="gpt-5", provider="openai")
        assert tracker.model == "gpt-5"
        assert tracker.provider == "openai"

    def test_reset(self):
        """Test resetting the tracker."""
        tracker = TokenTracker()

        # Add some usage
        usage = Usage(requests=1, input_tokens=100, output_tokens=50, total_tokens=150)
        tracker.update(usage)
        tracker.track_tool("test_tool", 150)

        # Reset
        tracker.reset()

        assert tracker.total_usage.total_tokens == 0
        assert tracker.total_usage.requests == 0
        assert len(tracker.tool_usage) == 0

    def test_update_usage(self):
        """Test updating usage from Usage object."""
        tracker = TokenTracker()

        # First update
        usage1 = Usage(requests=1, input_tokens=100, output_tokens=50, total_tokens=150)
        tracker.update(usage1)

        assert tracker.total_usage.requests == 1
        assert tracker.total_usage.input_tokens == 100
        assert tracker.total_usage.output_tokens == 50
        assert tracker.total_usage.total_tokens == 150

        # Second update (cumulative)
        usage2 = Usage(
            requests=1, input_tokens=200, output_tokens=100, total_tokens=300
        )
        tracker.update(usage2)

        assert tracker.total_usage.requests == 2
        assert tracker.total_usage.input_tokens == 300
        assert tracker.total_usage.output_tokens == 150
        assert tracker.total_usage.total_tokens == 450

    def test_track_tool(self):
        """Test tracking tool-specific usage."""
        tracker = TokenTracker()

        # Track first tool
        tracker.track_tool("read_file", 100)
        assert "read_file" in tracker.tool_usage
        assert tracker.tool_usage["read_file"]["tokens"] == 100
        assert tracker.tool_usage["read_file"]["calls"] == 1

        # Track same tool again
        tracker.track_tool("read_file", 50)
        assert tracker.tool_usage["read_file"]["tokens"] == 150
        assert tracker.tool_usage["read_file"]["calls"] == 2

        # Track different tool
        tracker.track_tool("write_file", 200)
        assert "write_file" in tracker.tool_usage
        assert tracker.tool_usage["write_file"]["tokens"] == 200
        assert tracker.tool_usage["write_file"]["calls"] == 1

    def test_checkpoint(self):
        """Test checkpoint functionality."""
        tracker = TokenTracker()

        # Initial usage
        usage1 = Usage(total_tokens=100)
        tokens_since = tracker.checkpoint(usage1)
        assert tokens_since == 100

        # More usage
        usage2 = Usage(total_tokens=250)
        tokens_since = tracker.checkpoint(usage2)
        assert tokens_since == 150  # 250 - 100

        # No change
        tokens_since = tracker.checkpoint(usage2)
        assert tokens_since == 0

    def test_calculate_cost_gpt5(self):
        """Test cost calculation for GPT-5 models."""
        tracker = TokenTracker(model="gpt-5", provider="openai")

        # Create usage with 1M input and 500K output tokens
        usage = Usage(
            input_tokens=1_000_000, output_tokens=500_000, total_tokens=1_500_000
        )

        input_cost, output_cost, cached_savings, total_cost = tracker.calculate_cost(
            usage
        )

        # GPT-5: $1.25 per 1M input, $10 per 1M output
        assert input_cost == 1.25
        assert output_cost == 5.00
        assert cached_savings == 0.0
        assert total_cost == 6.25

    def test_calculate_cost_with_cached_tokens(self):
        """Test cost calculation with cached tokens."""
        tracker = TokenTracker(model="gpt-5-mini", provider="openai")

        # Create usage with cached tokens
        usage = Usage(
            input_tokens=1_000_000,
            input_tokens_details=InputTokensDetails(cached_tokens=500_000),
            output_tokens=200_000,
            total_tokens=1_200_000,
        )

        input_cost, output_cost, cached_savings, total_cost = tracker.calculate_cost(
            usage
        )

        # GPT-5-mini: $0.25 per 1M input, $2 per 1M output
        # Cached tokens get 50% discount
        assert input_cost == 0.25
        assert output_cost == 0.40
        assert cached_savings == pytest.approx(0.0625)  # 500K * ($0.25 - $0.125) / 1M
        assert total_cost == pytest.approx(0.5875)

    def test_calculate_cost_with_reasoning_tokens(self):
        """Test cost calculation with reasoning tokens (GPT-5 models)."""
        tracker = TokenTracker(model="gpt-5", provider="openai")

        # Create usage with reasoning tokens
        usage = Usage(
            input_tokens=100_000,
            output_tokens=50_000,
            output_tokens_details=OutputTokensDetails(reasoning_tokens=20_000),
            total_tokens=150_000,
        )

        input_cost, output_cost, cached_savings, total_cost = tracker.calculate_cost(
            usage
        )

        # GPT-5: $1.25 per 1M input, $10 per 1M output (including reasoning)
        assert input_cost == pytest.approx(0.125)
        assert output_cost == pytest.approx(
            0.70
        )  # 50K output + 20K reasoning at $10/1M
        assert total_cost == pytest.approx(0.825)

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model."""
        tracker = TokenTracker(model="unknown-model", provider="unknown")

        usage = Usage(input_tokens=1_000_000, output_tokens=500_000)
        input_cost, output_cost, cached_savings, total_cost = tracker.calculate_cost(
            usage
        )

        assert input_cost == 0.0
        assert output_cost == 0.0
        assert cached_savings == 0.0
        assert total_cost == 0.0

    def test_generate_report(self):
        """Test generating a comprehensive report."""
        tracker = TokenTracker(model="gpt-5-mini", provider="openai")

        # Simulate some usage
        usage = Usage(
            requests=5,
            input_tokens=100_000,
            input_tokens_details=InputTokensDetails(cached_tokens=20_000),
            output_tokens=50_000,
            output_tokens_details=OutputTokensDetails(reasoning_tokens=5_000),
            total_tokens=150_000,
        )
        tracker.update(usage)
        tracker.track_tool("read_file", 30_000)
        tracker.track_tool("write_file", 20_000)
        tracker.track_tool("read_file", 15_000)

        # Generate report
        report = tracker.generate_report()

        assert report.total_requests == 5
        assert report.total_input_tokens == 100_000
        assert report.total_output_tokens == 50_000
        assert report.total_tokens == 150_000
        assert report.cached_input_tokens == 20_000
        assert report.reasoning_tokens == 5_000
        assert report.model == "gpt-5-mini"
        assert report.provider == "openai"

        # Check tool usage
        assert "read_file" in report.tool_usage
        assert report.tool_usage["read_file"]["tokens"] == 45_000
        assert report.tool_usage["read_file"]["calls"] == 2
        assert report.tool_usage["write_file"]["tokens"] == 20_000
        assert report.tool_usage["write_file"]["calls"] == 1

        # Check costs (GPT-5-mini: $0.25/$2 per 1M)
        assert report.input_cost == pytest.approx(0.025)
        assert report.output_cost == pytest.approx(0.10)
        assert report.total_cost == pytest.approx(0.1225)  # With cached savings

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        report = TokenUsageReport(
            total_requests=10,
            total_input_tokens=100_000,
            total_output_tokens=50_000,
            total_tokens=150_000,
            cached_input_tokens=10_000,
            reasoning_tokens=5_000,
            input_cost=0.025,
            output_cost=0.10,
            cached_savings=0.005,
            total_cost=0.12,
            model="gpt-5-mini",
            provider="openai",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=30),
            duration_seconds=30.0,
            tool_usage={"read_file": {"tokens": 50_000, "calls": 5}},
        )

        report_dict = report.to_dict()

        assert report_dict["token_counts"]["requests"] == 10
        assert report_dict["token_counts"]["total_tokens"] == 150_000
        assert report_dict["costs"]["total_cost"] == 0.12
        assert report_dict["metadata"]["model"] == "gpt-5-mini"
        assert report_dict["metadata"]["duration_seconds"] == 30.0
        assert "read_file" in report_dict["tool_usage"]

    def test_report_format_summary(self):
        """Test formatting human-readable summary."""
        report = TokenUsageReport(
            total_requests=10,
            total_input_tokens=100_000,
            total_output_tokens=50_000,
            total_tokens=150_000,
            cached_input_tokens=10_000,
            reasoning_tokens=5_000,
            input_cost=0.025,
            output_cost=0.10,
            cached_savings=0.005,
            total_cost=0.12,
            model="gpt-5-mini",
            provider="openai",
            duration_seconds=30.5,
            tool_usage={"read_file": {"tokens": 50_000, "calls": 5}},
        )

        summary = report.format_summary()

        assert "Token Usage Report" in summary
        assert "Model: openai/gpt-5-mini" in summary
        assert "Duration: 30.50s" in summary
        assert "Total: 150,000 tokens" in summary
        assert "Total: $0.1200" in summary
        assert "read_file: 50,000 tokens (5 calls)" in summary


class TestCostEstimation:
    """Test cost estimation functions."""

    def test_estimate_monthly_cost(self):
        """Test monthly cost estimation."""
        estimate = TokenTracker.estimate_monthly_cost(
            model="gpt-5-mini",
            provider="openai",
            daily_input_tokens=1_000_000,
            daily_output_tokens=500_000,
            cache_rate=0.2,
        )

        assert estimate["daily_input_tokens"] == 1_000_000
        assert estimate["daily_output_tokens"] == 500_000
        assert estimate["monthly_input_tokens"] == 30_000_000
        assert estimate["monthly_output_tokens"] == 15_000_000
        assert estimate["cached_tokens"] == 6_000_000
        assert estimate["cache_rate"] == 0.2

        # Check costs (GPT-5-mini: $0.25 input, $2 output per 1M)
        # 24M uncached at $0.25 + 6M cached at $0.125 = $6 + $0.75 = $6.75
        # 15M output at $2 = $30
        assert estimate["input_cost"] == pytest.approx(6.75)
        assert estimate["output_cost"] == pytest.approx(30.0)
        assert estimate["total_monthly_cost"] == pytest.approx(36.75)
        assert estimate["daily_average_cost"] == pytest.approx(1.225)

    def test_estimate_monthly_cost_no_cache(self):
        """Test monthly cost estimation without caching."""
        estimate = TokenTracker.estimate_monthly_cost(
            model="gpt-5",
            provider="openai",
            daily_input_tokens=100_000,
            daily_output_tokens=50_000,
            cache_rate=0.0,
        )

        # GPT-5: $1.25 input, $10 output per 1M
        # 3M input at $1.25 = $3.75
        # 1.5M output at $10 = $15
        assert estimate["input_cost"] == pytest.approx(3.75)
        assert estimate["output_cost"] == pytest.approx(15.0)
        assert estimate["total_monthly_cost"] == pytest.approx(18.75)

    def test_estimate_monthly_cost_unknown_model(self):
        """Test monthly cost estimation for unknown model."""
        estimate = TokenTracker.estimate_monthly_cost(
            model="unknown",
            provider="unknown",
            daily_input_tokens=100_000,
            daily_output_tokens=50_000,
        )

        assert estimate == {"error": "Model not found"}


class TestFormatting:
    """Test formatting utility functions."""

    def test_format_token_count(self):
        """Test token count formatting."""
        assert format_token_count(100) == "100"
        assert format_token_count(1_500) == "1.5K"
        assert format_token_count(10_000) == "10.0K"
        assert format_token_count(1_000_000) == "1.00M"
        assert format_token_count(2_500_000) == "2.50M"

    def test_format_cost(self):
        """Test cost formatting."""
        assert format_cost(0.00001) == "$0.000010"
        assert format_cost(0.005) == "$0.005000"
        assert format_cost(0.1234) == "$0.1234"
        assert format_cost(1.5) == "$1.50"
        assert format_cost(100.789) == "$100.79"


class TestModelPricing:
    """Test model pricing configuration."""

    def test_gpt5_family_pricing(self):
        """Test GPT-5 family pricing is correctly configured."""
        gpt5_models = MODEL_PRICING["openai"]

        # GPT-5
        assert gpt5_models["gpt-5"]["input_token_per_million_cost"] == 1.25
        assert gpt5_models["gpt-5"]["output_token_per_million_cost"] == 10.00

        # GPT-5-mini
        assert gpt5_models["gpt-5-mini"]["input_token_per_million_cost"] == 0.25
        assert gpt5_models["gpt-5-mini"]["output_token_per_million_cost"] == 2.00

        # GPT-5-nano
        assert gpt5_models["gpt-5-nano"]["input_token_per_million_cost"] == 0.05
        assert gpt5_models["gpt-5-nano"]["output_token_per_million_cost"] == 0.40

    def test_cached_pricing(self):
        """Test cached token pricing (50% discount)."""
        gpt5_models = MODEL_PRICING["openai"]

        for model_name, pricing in gpt5_models.items():
            if "cached_input_token_per_million_cost" in pricing:
                cached_price = pricing["cached_input_token_per_million_cost"]
                full_price = pricing["input_token_per_million_cost"]
                assert cached_price == full_price * 0.5

    def test_oss_models_free(self):
        """Test that OSS models have zero token costs."""
        oss_models = MODEL_PRICING["gpt-oss"]

        for model_name, pricing in oss_models.items():
            assert pricing["input_token_per_million_cost"] == 0.0
            assert pricing["output_token_per_million_cost"] == 0.0
            # But they should have compute costs
            assert "compute_cost_per_hour" in pricing
            assert pricing["compute_cost_per_hour"] > 0
