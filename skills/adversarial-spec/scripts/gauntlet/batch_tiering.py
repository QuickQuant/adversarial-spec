"""Power-law batch tiering for Phase 4 concern evaluation.

Why this exists
---------------
Phase 4 batches concerns and re-sends the spec with each batch. The spec is
~31K tokens; a batch of 15 concerns is ~1.2K tokens of concern text. Per-batch
input cost is therefore dominated by the spec, not by N. Naively raising the
flat batch size to 50 cuts call count by ~70% but creates a quality risk: the
hardest ~5-10% of concerns (long FLOW/ARCH prose with multi-section refs) get
diluted in a 50-mixed batch and grade poorly.

Power-law batching solves both axes at once: easy concerns go in big batches
(amortize the spec re-send), hard concerns go in small batches (preserve
attention quality). The complexity signal in v1 is intentionally simple —
``len(text)`` alone — because it is highly correlated with the multi-signal
proxies (section refs, code identifiers, etc.) and avoids calibration risk.

Revert path
-----------
This module is opt-in. The default ``GauntletConfig.eval_tier_strategy`` is
``"flat"``, which preserves the historical behavior. If power-law tiering
turns out to grade worse than flat batching on real runs, callers flip the
strategy back and this module stops being on the hot path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from gauntlet.core_types import Concern


@dataclass(frozen=True)
class BatchTier:
    """A subset of concerns to send through Phase 4 with a specific batch size.

    Attributes:
        name: Human-readable label for logs ("easy", "med", "hard").
        concerns: The concerns assigned to this tier, in stable order.
        batch_size: How many concerns per evaluator call for this tier.
    """
    name: str
    concerns: list[Concern]
    batch_size: int


# Empirically reasonable defaults for this skill's typical spec sizes
# (1000–2000 lines). Calibrate in place if real-run data argues otherwise.
DEFAULT_PERCENTILE_CUTS: tuple[int, int] = (60, 90)
DEFAULT_TIER_BATCH_SIZES: tuple[int, int, int] = (75, 30, 12)
DEFAULT_TIER_NAMES: tuple[str, str, str] = ("easy", "med", "hard")


def _percentile_threshold(values: Sequence[int], pct: int) -> int:
    """Inclusive nearest-rank percentile on a sorted list of ints.

    Uses the simple "rank = ceil(p/100 * n)" definition. We don't need scipy
    here — this is one signal, and the percentile choice is approximate by
    design (calibration matters more than 0.1-percentile accuracy).
    """
    if not values:
        return 0
    if pct <= 0:
        return values[0]
    if pct >= 100:
        return values[-1]
    n = len(values)
    rank = max(1, (pct * n + 99) // 100)  # ceil
    return values[min(rank, n) - 1]


def tier_concerns_by_length(
    concerns: list[Concern],
    *,
    percentile_cuts: tuple[int, int] = DEFAULT_PERCENTILE_CUTS,
    tier_batch_sizes: tuple[int, int, int] = DEFAULT_TIER_BATCH_SIZES,
    tier_names: tuple[str, str, str] = DEFAULT_TIER_NAMES,
) -> list[BatchTier]:
    """Split concerns into 3 length-based tiers and assign per-tier batch sizes.

    Args:
        concerns: Input concerns. Must be in a stable order — within a tier,
            the original order is preserved (matters for downstream parse-fail
            detection that pairs concerns with timing).
        percentile_cuts: (low_pct, high_pct) — concerns at or below the
            low_pct text-length percentile go to tier 1; concerns above the
            high_pct percentile go to tier 3; the rest go to tier 2.
        tier_batch_sizes: (easy_size, med_size, hard_size). Each tier's
            evaluator call processes this many concerns.
        tier_names: (easy, med, hard) labels surfaced in logs and tier metadata.

    Returns:
        A list of three BatchTier objects in (easy, med, hard) order. Tiers
        with zero members are still returned (with empty concerns list) so
        the caller can iterate uniformly.

    Notes:
        * Stable: identical input → identical output.
        * Idempotent: re-running on already-tiered output yields the same
          partition (since this is a pure function of (text-length, cuts)).
        * Edge cases: empty input → three empty tiers. All-equal lengths →
          everything ends up in the lowest tier whose threshold matches.
    """
    if not concerns:
        return [BatchTier(name=tier_names[i], concerns=[], batch_size=tier_batch_sizes[i]) for i in range(3)]

    if percentile_cuts[0] >= percentile_cuts[1]:
        raise ValueError(
            f"percentile_cuts must be strictly increasing; got {percentile_cuts!r}"
        )
    if any(b <= 0 for b in tier_batch_sizes):
        raise ValueError(
            f"tier_batch_sizes must all be positive; got {tier_batch_sizes!r}"
        )

    # Compute percentile thresholds from a sorted copy. We don't reorder the
    # caller's concerns — assignment uses the threshold values, not positions.
    lengths = sorted(len(c.text) for c in concerns)
    low_threshold = _percentile_threshold(lengths, percentile_cuts[0])
    high_threshold = _percentile_threshold(lengths, percentile_cuts[1])

    easy: list[Concern] = []
    med: list[Concern] = []
    hard: list[Concern] = []
    for c in concerns:
        n = len(c.text)
        if n <= low_threshold:
            easy.append(c)
        elif n <= high_threshold:
            med.append(c)
        else:
            hard.append(c)

    return [
        BatchTier(name=tier_names[0], concerns=easy, batch_size=tier_batch_sizes[0]),
        BatchTier(name=tier_names[1], concerns=med, batch_size=tier_batch_sizes[1]),
        BatchTier(name=tier_names[2], concerns=hard, batch_size=tier_batch_sizes[2]),
    ]


def summarize_tiers(tiers: list[BatchTier]) -> str:
    """Human-readable one-liner per tier, plus a totals row. Used in stderr logs.

    Example output::

        Tiering: easy 656 concerns @ batch=75 (9 calls/model)
                 med  328 concerns @ batch=30 (11 calls/model)
                 hard 108 concerns @ batch=12 (9 calls/model)
                 ---
                 1092 concerns total → 29 calls/model
    """
    lines: list[str] = []
    total_concerns = 0
    total_calls = 0
    name_width = max(len(t.name) for t in tiers) if tiers else 4

    for t in tiers:
        n = len(t.concerns)
        calls = (n + t.batch_size - 1) // t.batch_size if n else 0
        total_concerns += n
        total_calls += calls
        lines.append(
            f"  {t.name.ljust(name_width)}  {n:5d} concerns @ batch={t.batch_size:>3d}  "
            f"({calls} calls/model)"
        )
    lines.append("  " + "-" * (name_width + 2))
    lines.append(f"  {'total'.ljust(name_width)}  {total_concerns:5d} concerns total → {total_calls} calls/model")
    return "\n".join(lines)


def pick_eval_batch_arg(
    *,
    strategy: str,
    concerns: list[Concern],
    flat_batch_size: int,
    tier_min_concerns: int,
) -> int | list[BatchTier]:
    """Decide what batching argument to hand to evaluate_concerns_multi_model.

    Implements the strategy + auto-fallback policy in a single pure-function
    point so it's directly unit-testable without needing the orchestrator's
    full Phase 4 plumbing.

    Args:
        strategy: ``"flat"`` or ``"power_law_length"``.
        concerns: Post-filter concerns about to be evaluated.
        flat_batch_size: Batch size used for the flat path.
        tier_min_concerns: Minimum concern count before ``power_law_length``
            actually tiers. Below this, falls back to ``flat_batch_size``.

    Returns:
        Either an int (flat) or a list[BatchTier] (tiered). Callers pass the
        result straight through to ``evaluate_concerns_multi_model``.

    Raises:
        ValueError: if ``strategy`` is not a recognized value.
    """
    if strategy == "flat":
        return flat_batch_size
    if strategy == "power_law_length":
        if len(concerns) < tier_min_concerns:
            # Tiering 12 concerns into 75/30/12 sizes is identical to one flat
            # batch, just with extra ceremony. Skip the ceremony.
            return flat_batch_size
        return tier_concerns_by_length(concerns)
    raise ValueError(
        f"Unknown eval_tier_strategy: {strategy!r}. "
        "Expected 'flat' or 'power_law_length'."
    )


def per_adversary_distribution(tiers: list[BatchTier]) -> dict[str, dict[str, int]]:
    """Per-adversary count of concerns per tier — useful for post-mortem.

    Returns: {adversary: {tier_name: count}}. Empty if no concerns.
    """
    out: dict[str, dict[str, int]] = {}
    for t in tiers:
        for c in t.concerns:
            adv = out.setdefault(c.adversary, {})
            adv[t.name] = adv.get(t.name, 0) + 1
    return out


__all__ = (
    "BatchTier",
    "DEFAULT_PERCENTILE_CUTS",
    "DEFAULT_TIER_BATCH_SIZES",
    "DEFAULT_TIER_NAMES",
    "tier_concerns_by_length",
    "summarize_tiers",
    "per_adversary_distribution",
    "pick_eval_batch_arg",
)
