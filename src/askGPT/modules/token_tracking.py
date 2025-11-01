"""
Token Tracking Module for Nano Agent.

This module provides comprehensive token usage tracking, cost calculation,
and reporting for OpenAI Agent SDK operations.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

# Import Agent SDK Usage class
try:
    from agents import Usage
    from agents.usage import InputTokensDetails, OutputTokensDetails
except ImportError:
    # Fallback for testing without Agent SDK
    @dataclass
    class InputTokensDetails:
        cached_tokens: int = 0

    @dataclass
    class OutputTokensDetails:
        reasoning_tokens: int = 0

    @dataclass
    class Usage:
        requests: int = 0
        input_tokens: int = 0
        input_tokens_details: InputTokensDetails = field(
            default_factory=lambda: InputTokensDetails()
        )
        output_tokens: int = 0
        output_tokens_details: OutputTokensDetails = field(
            default_factory=lambda: OutputTokensDetails()
        )
        total_tokens: int = 0

        def add(self, other: "Usage") -> None:
            self.requests += other.requests if other.requests else 0
            self.input_tokens += other.input_tokens if other.input_tokens else 0
            self.output_tokens += other.output_tokens if other.output_tokens else 0
            self.total_tokens += other.total_tokens if other.total_tokens else 0


# Initialize logger
logger = logging.getLogger(__name__)


# Model pricing map (per 1M tokens in USD)
MODEL_PRICING: Dict[str, Dict[str, Dict[str, float]]] = {
    "openai": {
        # GPT-5 Family (August 2025 pricing)
        "gpt-5": {
            "input_token_per_million_cost": 1.25,
            "output_token_per_million_cost": 10.00,
            "cached_input_token_per_million_cost": 0.625,  # 50% discount for cached
            "reasoning_token_per_million_cost": 10.00,  # Same as output for reasoning
        },
        "gpt-5-mini": {
            "input_token_per_million_cost": 0.25,
            "output_token_per_million_cost": 2.00,
            "cached_input_token_per_million_cost": 0.125,
            "reasoning_token_per_million_cost": 2.00,
        },
        "gpt-5-nano": {
            "input_token_per_million_cost": 0.05,
            "output_token_per_million_cost": 0.40,
            "cached_input_token_per_million_cost": 0.025,
            "reasoning_token_per_million_cost": 0.40,
        },
        "gpt-5-chat-latest": {
            "input_token_per_million_cost": 1.25,
            "output_token_per_million_cost": 10.00,
            "cached_input_token_per_million_cost": 0.625,
            "reasoning_token_per_million_cost": 0.00,  # No reasoning for chat model
        },
        # GPT-4 Family (for comparison)
        "gpt-4o": {
            "input_token_per_million_cost": 5.00,
            "output_token_per_million_cost": 15.00,
            "cached_input_token_per_million_cost": 2.50,
            "reasoning_token_per_million_cost": 0.00,  # GPT-4 doesn't have reasoning tokens
        },
        "gpt-4-turbo": {
            "input_token_per_million_cost": 10.00,
            "output_token_per_million_cost": 30.00,
            "cached_input_token_per_million_cost": 5.00,
            "reasoning_token_per_million_cost": 0.00,
        },
    },
    "anthropic": {
        # Claude models (August 2025 pricing)
        "claude-opus-4-1-20250805": {
            "input_token_per_million_cost": 15.00,
            "output_token_per_million_cost": 75.00,
            "cached_input_token_per_million_cost": 1.50,  # Cache hits & refreshes
            "cache_write_5m_per_million_cost": 18.75,  # 5 min cache writes
            "cache_write_1h_per_million_cost": 30.00,  # 1 hour cache writes
            "reasoning_token_per_million_cost": 0.00,
        },
        "claude-opus-4-20250514": {
            "input_token_per_million_cost": 15.00,
            "output_token_per_million_cost": 75.00,
            "cached_input_token_per_million_cost": 1.50,
            "cache_write_5m_per_million_cost": 18.75,
            "cache_write_1h_per_million_cost": 30.00,
            "reasoning_token_per_million_cost": 0.00,
        },
        "claude-sonnet-4-20250514": {
            "input_token_per_million_cost": 3.00,
            "output_token_per_million_cost": 15.00,
            "cached_input_token_per_million_cost": 0.30,
            "cache_write_5m_per_million_cost": 3.75,
            "cache_write_1h_per_million_cost": 6.00,
            "reasoning_token_per_million_cost": 0.00,
        },
        "claude-3-haiku-20240307": {
            "input_token_per_million_cost": 0.25,
            "output_token_per_million_cost": 1.25,
            "cached_input_token_per_million_cost": 0.03,
            "cache_write_5m_per_million_cost": 0.30,
            "cache_write_1h_per_million_cost": 0.48,
            "reasoning_token_per_million_cost": 0.00,
        },
    },
    "ollama": {
        # Open-source models via Ollama (free to run, but include compute costs)
        "gpt-oss:120b": {
            "input_token_per_million_cost": 0.00,  # Free model
            "output_token_per_million_cost": 0.00,
            "cached_input_token_per_million_cost": 0.00,
            "reasoning_token_per_million_cost": 0.00,
            "compute_cost_per_hour": 4.00,  # Estimated GPU cost
        },
        "gpt-oss:20b": {
            "input_token_per_million_cost": 0.00,
            "output_token_per_million_cost": 0.00,
            "cached_input_token_per_million_cost": 0.00,
            "reasoning_token_per_million_cost": 0.00,
            "compute_cost_per_hour": 1.00,  # Lower GPU requirements
        },
    },
}


@dataclass
class TokenUsageReport:
    """Detailed token usage report."""

    # Token counts
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0

    # Cost breakdown
    input_cost: float = 0.0
    output_cost: float = 0.0
    cached_savings: float = 0.0
    total_cost: float = 0.0

    # Metadata
    model: str = ""
    provider: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "token_counts": {
                "requests": self.total_requests,
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "total_tokens": self.total_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "reasoning_tokens": self.reasoning_tokens,
            },
            "costs": {
                "input_cost": round(self.input_cost, 4),
                "output_cost": round(self.output_cost, 4),
                "cached_savings": round(self.cached_savings, 4),
                "total_cost": round(self.total_cost, 4),
            },
            "metadata": {
                "model": self.model,
                "provider": self.provider,
                "duration_seconds": round(self.duration_seconds, 2),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
            },
        }

    def format_summary(self) -> str:
        """Format a human-readable summary."""
        lines = [
            "=== Token Usage Report ===",
            f"Model: {self.provider}/{self.model}",
            f"Duration: {self.duration_seconds:.2f}s",
            "",
            "Token Usage:",
            f"  Requests: {self.total_requests:,}",
            f"  Input: {self.total_input_tokens:,} tokens",
            f"    - Cached: {self.cached_input_tokens:,} tokens",
            f"  Output: {self.total_output_tokens:,} tokens",
            f"    - Reasoning: {self.reasoning_tokens:,} tokens",
            f"  Total: {self.total_tokens:,} tokens",
            "",
            "Costs:",
            f"  Input: ${self.input_cost:.4f}",
            f"  Output: ${self.output_cost:.4f}",
            f"  Cached Savings: ${self.cached_savings:.4f}",
            f"  Total: ${self.total_cost:.4f}",
        ]

        return "\n".join(lines)


class TokenTracker:
    """Tracks token usage and calculates costs."""

    def __init__(self, model: str = "gpt-5-mini", provider: str = "openai"):
        """Initialize token tracker.

        Args:
            model: Model identifier
            provider: Provider name (openai, anthropic, gpt-oss)
        """
        self.model = model
        self.provider = provider
        self.reset()

    def reset(self):
        """Reset tracking counters."""
        self.total_usage = Usage()
        self.start_time = datetime.now()

    def update(self, usage: Usage):
        """Update total usage from a Usage object.

        Args:
            usage: Usage object from Agent SDK
        """
        self.total_usage.add(usage)
        logger.debug(
            f"Updated usage: {usage.total_tokens} new tokens, total: {self.total_usage.total_tokens}"
        )

    def calculate_cost(
        self, usage: Optional[Usage] = None
    ) -> Tuple[float, float, float, float]:
        """Calculate costs based on usage.

        Args:
            usage: Usage object to calculate cost for (defaults to total_usage)

        Returns:
            Tuple of (input_cost, output_cost, cached_savings, total_cost)
        """
        if usage is None:
            usage = self.total_usage

        # Get pricing for the model
        pricing = self._get_pricing()
        if not pricing:
            # Local providers (ollama, lmstudio, ollama-native) have no costs
            if self.provider in ["ollama", "lmstudio", "ollama-native"]:
                logger.debug(f"Local provider {self.provider} - no costs applied")
            else:
                logger.warning(f"No pricing found for {self.provider}/{self.model}")
            return 0.0, 0.0, 0.0, 0.0

        # Calculate base costs (convert from per million to actual)
        input_cost = (usage.input_tokens / 1_000_000) * pricing[
            "input_token_per_million_cost"
        ]
        output_cost = (usage.output_tokens / 1_000_000) * pricing[
            "output_token_per_million_cost"
        ]

        # Calculate cached savings
        cached_tokens = (
            usage.input_tokens_details.cached_tokens
            if usage.input_tokens_details
            else 0
        )
        if cached_tokens > 0:
            full_input_cost = (cached_tokens / 1_000_000) * pricing[
                "input_token_per_million_cost"
            ]
            cached_cost = (cached_tokens / 1_000_000) * pricing.get(
                "cached_input_token_per_million_cost",
                pricing["input_token_per_million_cost"] * 0.5,
            )
            cached_savings = full_input_cost - cached_cost
        else:
            cached_savings = 0.0

        # Add reasoning token costs if applicable
        reasoning_tokens = (
            usage.output_tokens_details.reasoning_tokens
            if usage.output_tokens_details
            else 0
        )
        if (
            reasoning_tokens > 0
            and pricing.get("reasoning_token_per_million_cost", 0) > 0
        ):
            reasoning_cost = (reasoning_tokens / 1_000_000) * pricing[
                "reasoning_token_per_million_cost"
            ]
            output_cost += reasoning_cost

        total_cost = input_cost + output_cost - cached_savings

        return input_cost, output_cost, cached_savings, total_cost

    def generate_report(self) -> TokenUsageReport:
        """Generate a comprehensive usage report.

        Returns:
            TokenUsageReport with all tracking data
        """
        input_cost, output_cost, cached_savings, total_cost = self.calculate_cost()

        report = TokenUsageReport(
            # Token counts
            total_requests=self.total_usage.requests,
            total_input_tokens=self.total_usage.input_tokens,
            total_output_tokens=self.total_usage.output_tokens,
            total_tokens=self.total_usage.total_tokens,
            cached_input_tokens=self.total_usage.input_tokens_details.cached_tokens
            if self.total_usage.input_tokens_details
            else 0,
            reasoning_tokens=self.total_usage.output_tokens_details.reasoning_tokens
            if self.total_usage.output_tokens_details
            else 0,
            # Costs
            input_cost=input_cost,
            output_cost=output_cost,
            cached_savings=cached_savings,
            total_cost=total_cost,
            # Metadata
            model=self.model,
            provider=self.provider,
            start_time=self.start_time,
            end_time=datetime.now(),
            duration_seconds=(datetime.now() - self.start_time).total_seconds(),
        )

        return report

    def add_usage(self, input_tokens: int = 0, output_tokens: int = 0):
        """Add token usage manually.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        usage = Usage()
        usage.input_tokens = input_tokens
        usage.output_tokens = output_tokens
        usage.total_tokens = input_tokens + output_tokens
        self.update(usage)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of token usage and costs.

        Returns:
            Dictionary with usage and cost information
        """
        input_cost, output_cost, cached_savings, total_cost = self.calculate_cost()

        summary = {
            "total_tokens": self.total_usage.total_tokens,
            "input_tokens": self.total_usage.input_tokens,
            "output_tokens": self.total_usage.output_tokens,
            "total_cost": total_cost,
            "input_cost": input_cost,
            "output_cost": output_cost,
        }

        # Add cached tokens info if available
        if (
            self.total_usage.input_tokens_details
            and self.total_usage.input_tokens_details.cached_tokens > 0
        ):
            summary[
                "cached_tokens"
            ] = self.total_usage.input_tokens_details.cached_tokens
            summary["cached_savings"] = cached_savings

        return summary

    def _get_pricing(self) -> Optional[Dict[str, float]]:
        """Get pricing for current model and provider.

        Returns:
            Pricing dictionary or None if not found
        """
        if self.provider not in MODEL_PRICING:
            return None

        provider_models = MODEL_PRICING[self.provider]
        if self.model not in provider_models:
            # Try to find a default or similar model
            if self.model.startswith("gpt-5"):
                return provider_models.get("gpt-5-mini", None)
            return None

        return provider_models[self.model]

    @staticmethod
    def estimate_monthly_cost(
        model: str,
        provider: str,
        daily_input_tokens: int,
        daily_output_tokens: int,
        cache_rate: float = 0.0,
    ) -> Dict[str, float]:
        """Estimate monthly costs for a usage pattern.

        Args:
            model: Model identifier
            provider: Provider name
            daily_input_tokens: Average daily input tokens
            daily_output_tokens: Average daily output tokens
            cache_rate: Percentage of input tokens that are cached (0.0 to 1.0)

        Returns:
            Dictionary with cost breakdown
        """
        if provider not in MODEL_PRICING or model not in MODEL_PRICING[provider]:
            return {"error": "Model not found"}

        pricing = MODEL_PRICING[provider][model]

        # Calculate monthly tokens
        monthly_input = daily_input_tokens * 30
        monthly_output = daily_output_tokens * 30
        monthly_cached = int(monthly_input * cache_rate)
        monthly_uncached = monthly_input - monthly_cached

        # Calculate costs
        uncached_cost = (monthly_uncached / 1_000_000) * pricing[
            "input_token_per_million_cost"
        ]
        cached_cost = (monthly_cached / 1_000_000) * pricing.get(
            "cached_input_token_per_million_cost",
            pricing["input_token_per_million_cost"] * 0.5,
        )
        output_cost = (monthly_output / 1_000_000) * pricing[
            "output_token_per_million_cost"
        ]

        total_cost = uncached_cost + cached_cost + output_cost

        return {
            "daily_input_tokens": daily_input_tokens,
            "daily_output_tokens": daily_output_tokens,
            "monthly_input_tokens": monthly_input,
            "monthly_output_tokens": monthly_output,
            "cached_tokens": monthly_cached,
            "cache_rate": cache_rate,
            "input_cost": uncached_cost + cached_cost,
            "output_cost": output_cost,
            "total_monthly_cost": total_cost,
            "daily_average_cost": total_cost / 30,
        }


def format_token_count(tokens: int) -> str:
    """Format token count for display.

    Args:
        tokens: Number of tokens

    Returns:
        Formatted string
    """
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.2f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    else:
        return str(tokens)


def format_cost(cost: float) -> str:
    """Format cost for display.

    Args:
        cost: Cost in USD

    Returns:
        Formatted string
    """
    if cost < 0.01:
        return f"${cost:.6f}"
    elif cost < 1.00:
        return f"${cost:.4f}"
    else:
        return f"${cost:.2f}"
