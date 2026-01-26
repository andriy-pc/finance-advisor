import time
from typing import Any

from advisor.constants import LLMProvider


class MetricsCollector:
    """
    Collects LLM usage metrics for observability and cost tracking.

    For now: in-memory storage with summary statistics.
    """

    # Simplified pricing per 1M tokens
    # TODO: ! update with actual rates !
    PRICING = {
        LLMProvider.OPENAI: {
            "gpt-4": {"input": 1.0, "output": 1.0},
            "gpt-4-turbo": {"input": 1.0, "output": 1.0},
        },
        LLMProvider.ANTHROPIC: {
            "claude-4-sonnet": {"input": 1.0, "output": 1.0},
            "claude-4.5-haiku": {"input": 1.0, "output": 1.0},
        },
        LLMProvider.OLLAMA: {"default": {"input": 0.0, "output": 0.0}},
    }

    def __init__(self) -> None:
        """Initialize with empty metrics storage."""
        self._metrics: list[dict[str, Any]] = []

    def record_call(
        self,
        provider: LLMProvider,
        model: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        """
        Record metrics for a single LLM call.

        Args:
            provider: LLM provider used
            model: Model identifier
            latency_ms: Request latency in milliseconds
            input_tokens: Input token count
            output_tokens: Output token count
            success: Whether call succeeded
            error_type: Error classification if failed
        """
        metric = {
            "timestamp": time.time(),
            "provider": provider.value,
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "success": success,
            "error_type": error_type,
            "cost_usd": self.estimate_cost(provider, model, input_tokens, output_tokens),
        }
        self._metrics.append(metric)

    def estimate_cost(self, provider: LLMProvider, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost based on provider pricing.

        Args:
            provider: Provider enum
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Estimated cost in USD
        """
        provider_pricing = self.PRICING.get(provider, {})

        # Try exact model match
        pricing = provider_pricing.get(model)

        # Fallback to default or zero
        if not pricing:
            pricing = provider_pricing.get("default", {"input": 0, "output": 0})

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def get_summary(self) -> dict[str, Any]:
        """
        Get aggregated metrics summary.

        Returns:
            Dict with totals, averages, and success rates
        """
        if not self._metrics:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "success_rate": 0.0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "total_tokens": 0,
            }

        total = len(self._metrics)
        successful = sum(1 for m in self._metrics if m["success"])
        total_cost = sum(m["cost_usd"] for m in self._metrics)
        avg_latency = sum(m["latency_ms"] for m in self._metrics) / total
        total_tokens = sum(m["total_tokens"] for m in self._metrics)

        return {
            "total_calls": total,
            "successful_calls": successful,
            "success_rate": successful / total,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens": total_tokens,
        }

    def get_metrics(self) -> list[dict[str, Any]]:
        """Return raw metrics for detailed analysis."""
        return self._metrics.copy()
