"""Token usage tracking for model calls."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from providers import DEFAULT_COST, MODEL_COSTS


@dataclass
class TokenTracker:
    """Track token usage and costs across model calls."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    by_model: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def record_call(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record usage for a model call and return the cost."""
        # CLI-routed models are subscription-based and do not use token pricing.
        cli_prefixes = ("codex/", "gemini-cli/", "claude-cli/")
        free_cost = {"input": 0.0, "output": 0.0}
        default = free_cost if model.startswith(cli_prefixes) else DEFAULT_COST
        costs = MODEL_COSTS.get(model, default)
        cost = (input_tokens / 1_000_000 * costs["input"]) + (
            output_tokens / 1_000_000 * costs["output"]
        )

        with self._lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost += cost

            if model not in self.by_model:
                self.by_model[model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            self.by_model[model]["input_tokens"] += input_tokens
            self.by_model[model]["output_tokens"] += output_tokens
            self.by_model[model]["cost"] += cost

        return cost

    def summary(self) -> str:
        """Generate cost summary string."""
        lines = ["", "=== Cost Summary ==="]
        lines.append(
            f"Total tokens: {self.total_input_tokens:,} in / {self.total_output_tokens:,} out"
        )
        lines.append(f"Total cost: ${self.total_cost:.4f}")
        if len(self.by_model) > 1:
            lines.append("")
            lines.append("By model:")
            for model, data in self.by_model.items():
                lines.append(
                    f"  {model}: ${data['cost']:.4f} ({data['input_tokens']:,} in / {data['output_tokens']:,} out)"
                )
        return "\n".join(lines)


tracker = TokenTracker()
