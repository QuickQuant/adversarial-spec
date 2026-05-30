"""Tests for power-law batch tiering (Phase 4 helper).

The function under test is purely deterministic: given identical input,
identical output. These tests verify partition correctness, edge cases,
and configuration validation. There are no LLM calls or randomness here.
"""

import pytest

from gauntlet.batch_tiering import (
    DEFAULT_PERCENTILE_CUTS,
    DEFAULT_TIER_BATCH_SIZES,
    BatchTier,
    _percentile_threshold,
    per_adversary_distribution,
    pick_eval_batch_arg,
    summarize_tiers,
    tier_concerns_by_length,
)
from gauntlet.core_types import Concern


def _c(text: str, adversary: str = "architect") -> Concern:
    return Concern(adversary=adversary, text=text, source_model="codex/gpt-5.5")


# -----------------------------------------------------------------------------
# Percentile helper
# -----------------------------------------------------------------------------


class TestPercentileThreshold:
    def test_empty_returns_zero(self):
        assert _percentile_threshold([], 50) == 0

    def test_below_zero_returns_min(self):
        assert _percentile_threshold([1, 2, 3, 4, 5], -10) == 1

    def test_above_hundred_returns_max(self):
        assert _percentile_threshold([1, 2, 3, 4, 5], 150) == 5

    def test_p50_picks_middle(self):
        # 5 items, ceil(50% * 5) = 3 → values[2] = 3 (1-indexed rank).
        assert _percentile_threshold([1, 2, 3, 4, 5], 50) == 3

    def test_p100_returns_max(self):
        assert _percentile_threshold([1, 2, 3, 4, 5], 100) == 5

    def test_p1_returns_first_or_near(self):
        # ceil(1% * 100) = 1 → values[0]
        assert _percentile_threshold(list(range(100)), 1) == 0


# -----------------------------------------------------------------------------
# Tiering correctness
# -----------------------------------------------------------------------------


class TestTierConcernsByLength:
    def test_empty_input_returns_three_empty_tiers(self):
        tiers = tier_concerns_by_length([])
        assert len(tiers) == 3
        assert all(t.concerns == [] for t in tiers)
        assert [t.batch_size for t in tiers] == list(DEFAULT_TIER_BATCH_SIZES)
        assert [t.name for t in tiers] == ["easy", "med", "hard"]

    def test_single_concern_lands_in_easy_tier(self):
        # A single value's percentiles all collapse onto itself, so it goes
        # into the easy tier (text length ≤ low_threshold).
        tiers = tier_concerns_by_length([_c("only one")])
        assert [len(t.concerns) for t in tiers] == [1, 0, 0]

    def test_partition_assigns_each_concern_exactly_once(self):
        concerns = [_c("x" * (i + 1)) for i in range(50)]
        tiers = tier_concerns_by_length(concerns)
        partitioned = sum(len(t.concerns) for t in tiers)
        assert partitioned == 50
        # No concern appears in more than one tier.
        seen_ids: set[str] = set()
        for t in tiers:
            for c in t.concerns:
                assert c.id not in seen_ids
                seen_ids.add(c.id)
        assert seen_ids == {c.id for c in concerns}

    def test_easy_tier_is_smallest_text(self):
        concerns = [_c("a" * length) for length in [10, 20, 30, 100, 200, 500, 1000]]
        tiers = tier_concerns_by_length(concerns)
        easy_max = max(len(c.text) for c in tiers[0].concerns) if tiers[0].concerns else 0
        hard_min = min(len(c.text) for c in tiers[2].concerns) if tiers[2].concerns else 10**9
        assert easy_max <= hard_min

    def test_default_cuts_at_60_90(self):
        # 100 concerns, lengths 1..100 → cuts at p60=60, p90=90.
        # Easy: len ≤ 60 (60 concerns). Med: 60 < len ≤ 90 (30 concerns).
        # Hard: len > 90 (10 concerns).
        concerns = [_c("x" * (i + 1)) for i in range(100)]
        tiers = tier_concerns_by_length(concerns)
        assert len(tiers[0].concerns) == 60
        assert len(tiers[1].concerns) == 30
        assert len(tiers[2].concerns) == 10

    def test_custom_cuts_and_sizes(self):
        concerns = [_c("x" * (i + 1)) for i in range(100)]
        tiers = tier_concerns_by_length(
            concerns,
            percentile_cuts=(50, 80),
            tier_batch_sizes=(100, 25, 5),
            tier_names=("trivial", "moderate", "gnarly"),
        )
        assert [t.batch_size for t in tiers] == [100, 25, 5]
        assert [t.name for t in tiers] == ["trivial", "moderate", "gnarly"]
        # 100 concerns, p50=50, p80=80 → 50/30/20.
        assert [len(t.concerns) for t in tiers] == [50, 30, 20]

    def test_all_equal_lengths_collapse_into_easy(self):
        concerns = [_c("xxxxx") for _ in range(20)]
        tiers = tier_concerns_by_length(concerns)
        # Both percentile thresholds equal the only length value, so every
        # concern's length is ≤ low_threshold → all go to "easy".
        assert len(tiers[0].concerns) == 20
        assert len(tiers[1].concerns) == 0
        assert len(tiers[2].concerns) == 0

    def test_within_tier_order_is_preserved(self):
        # Build concerns with a mix of lengths but a deterministic input order.
        sources = [
            _c("short A"),
            _c("a longer one B " * 10),
            _c("short C"),
            _c("an even longer concern D with lots of text " * 30),
            _c("short E"),
        ]
        tiers = tier_concerns_by_length(sources)
        # Within whatever tier they end up in, the original order should be
        # preserved (we iterate the input list once).
        for t in tiers:
            ids_in_input_order = [c.id for c in sources if c.id in {x.id for x in t.concerns}]
            ids_in_tier_order = [c.id for c in t.concerns]
            assert ids_in_tier_order == ids_in_input_order

    def test_idempotent_on_re_run(self):
        concerns = [_c("x" * (i * 3 + 5)) for i in range(40)]
        first = tier_concerns_by_length(concerns)
        second = tier_concerns_by_length(concerns)
        for a, b in zip(first, second):
            assert [c.id for c in a.concerns] == [c.id for c in b.concerns]
            assert a.batch_size == b.batch_size

    def test_invalid_percentile_cuts_raise(self):
        with pytest.raises(ValueError, match="strictly increasing"):
            tier_concerns_by_length([_c("x")], percentile_cuts=(60, 60))
        with pytest.raises(ValueError, match="strictly increasing"):
            tier_concerns_by_length([_c("x")], percentile_cuts=(90, 60))

    def test_invalid_batch_sizes_raise(self):
        with pytest.raises(ValueError, match="must all be positive"):
            tier_concerns_by_length([_c("x")], tier_batch_sizes=(75, 0, 12))
        with pytest.raises(ValueError, match="must all be positive"):
            tier_concerns_by_length([_c("x")], tier_batch_sizes=(75, 30, -1))


# -----------------------------------------------------------------------------
# Summary helpers
# -----------------------------------------------------------------------------


class TestSummarize:
    def test_summary_shows_all_tier_names_and_counts(self):
        tiers = [
            BatchTier(name="easy", concerns=[_c("a")] * 75, batch_size=75),
            BatchTier(name="med", concerns=[_c("b")] * 30, batch_size=30),
            BatchTier(name="hard", concerns=[_c("c")] * 12, batch_size=12),
        ]
        out = summarize_tiers(tiers)
        assert "easy" in out and "75 concerns" in out
        assert "med" in out and "30 concerns" in out
        assert "hard" in out and "12 concerns" in out
        # Total line.
        assert "117 concerns total" in out
        # Each tier contributes 1 call (since count == batch_size).
        assert "→ 3 calls/model" in out

    def test_summary_handles_empty_tiers(self):
        tiers = [
            BatchTier(name="easy", concerns=[], batch_size=75),
            BatchTier(name="med", concerns=[], batch_size=30),
            BatchTier(name="hard", concerns=[], batch_size=12),
        ]
        out = summarize_tiers(tiers)
        assert "0 concerns total" in out


class TestPerAdversaryDistribution:
    def test_returns_per_adversary_per_tier_counts(self):
        tiers = tier_concerns_by_length([
            _c("short", "architect"),
            _c("a longer one " * 10, "architect"),
            _c("short", "paranoid_security"),
            _c("an even longer concern " * 30, "paranoid_security"),
        ])
        dist = per_adversary_distribution(tiers)
        assert "architect" in dist
        assert "paranoid_security" in dist
        # Counts should sum to the per-adversary total.
        for adv, counts in dist.items():
            assert sum(counts.values()) == 2  # 2 concerns each in this fixture

    def test_empty_tiers_return_empty_dict(self):
        tiers = tier_concerns_by_length([])
        assert per_adversary_distribution(tiers) == {}


# -----------------------------------------------------------------------------
# Realistic-shape sanity (1092-concern fixture mimicking the andrew run)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# pick_eval_batch_arg — strategy + auto-fallback policy
# -----------------------------------------------------------------------------


class TestPickEvalBatchArg:
    def test_flat_strategy_returns_int(self):
        concerns = [_c("x" * 50) for _ in range(100)]
        result = pick_eval_batch_arg(
            strategy="flat",
            concerns=concerns,
            flat_batch_size=15,
            tier_min_concerns=30,
        )
        assert result == 15

    def test_power_law_length_returns_tier_list_when_n_is_large(self):
        concerns = [_c("x" * (50 + i)) for i in range(100)]
        result = pick_eval_batch_arg(
            strategy="power_law_length",
            concerns=concerns,
            flat_batch_size=15,
            tier_min_concerns=30,
        )
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(t, BatchTier) for t in result)
        assert sum(len(t.concerns) for t in result) == 100

    def test_power_law_length_falls_back_when_n_below_threshold(self):
        """Tiering 12 concerns into 75/30/12-sized batches is silly. Fall back."""
        concerns = [_c("x" * 50) for _ in range(12)]
        result = pick_eval_batch_arg(
            strategy="power_law_length",
            concerns=concerns,
            flat_batch_size=15,
            tier_min_concerns=30,
        )
        assert result == 15  # fell back to flat

    def test_fallback_uses_caller_supplied_flat_batch_size(self):
        concerns = [_c("x") for _ in range(5)]
        # Caller customized flat_batch_size=25; fallback honors it.
        result = pick_eval_batch_arg(
            strategy="power_law_length",
            concerns=concerns,
            flat_batch_size=25,
            tier_min_concerns=30,
        )
        assert result == 25

    def test_fallback_threshold_is_inclusive_of_min(self):
        # At exactly tier_min_concerns, we tier (the comparison is `< min`).
        concerns = [_c("x" * (10 + i)) for i in range(30)]
        result = pick_eval_batch_arg(
            strategy="power_law_length",
            concerns=concerns,
            flat_batch_size=15,
            tier_min_concerns=30,
        )
        assert isinstance(result, list)

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown eval_tier_strategy"):
            pick_eval_batch_arg(
                strategy="bogus_strategy",
                concerns=[_c("x")],
                flat_batch_size=15,
                tier_min_concerns=30,
            )

    def test_empty_concerns_with_flat_returns_int(self):
        result = pick_eval_batch_arg(
            strategy="flat",
            concerns=[],
            flat_batch_size=15,
            tier_min_concerns=30,
        )
        assert result == 15

    def test_empty_concerns_with_power_law_falls_back(self):
        # 0 < 30 → fallback path. Returns int. evaluate_concerns_multi_model
        # short-circuits empty input either way; we just don't waste cycles
        # building empty tiers.
        result = pick_eval_batch_arg(
            strategy="power_law_length",
            concerns=[],
            flat_batch_size=15,
            tier_min_concerns=30,
        )
        assert result == 15


# -----------------------------------------------------------------------------
# Realistic-shape sanity (1092-concern fixture mimicking the andrew run)
# -----------------------------------------------------------------------------


def test_realistic_shape_smoke():
    """1092 concerns with mixed lengths → roughly 60/30/10 split per defaults.

    Concerns with mixed length distributions (short / medium / long) produce a
    tier-1 / tier-2 / tier-3 partition that scales with the cuts.
    """
    concerns = []
    for i in range(800):
        concerns.append(_c("short concern " * 5))         # ~70 chars
    for i in range(200):
        concerns.append(_c("medium length concern " * 15))  # ~330 chars
    for i in range(92):
        concerns.append(_c("very long concern with lots of detail " * 40))  # ~1500 chars
    tiers = tier_concerns_by_length(concerns)

    # Tier 1 should capture the 800 short-concerns plus possibly some medium.
    # Tier 3 should be approximately the long ones.
    assert len(tiers[0].concerns) >= 800   # all shorts at minimum
    assert len(tiers[2].concerns) <= 200   # bounded by p90
    # All 1092 partitioned exactly once.
    assert sum(len(t.concerns) for t in tiers) == 1092
