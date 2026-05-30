"""Integration tests for evaluate_concerns_multi_model with BatchTier input.

The function under test was extended to accept either:
  - int batch_size (historical flat batching), or
  - list[BatchTier] (per-tier batch sizes from gauntlet.batch_tiering).

These tests verify the new dispatch path produces equivalent evaluations
and respects per-tier batch sizes. We mock `call_model` so the tests run
fast and deterministically — the real-LLM path is exercised by other suites.
"""

import json

import pytest

from gauntlet.batch_tiering import BatchTier
from gauntlet.core_types import Concern, Evaluation, GauntletConfig
from gauntlet.phase_4_evaluation import evaluate_concerns_multi_model


def _make_concern(idx: int, adversary: str = "architect", text_len: int = 100) -> Concern:
    """Build a concern with a deterministic id-by-text and length-controlled text."""
    text = f"Concern {idx}: " + ("x " * (text_len // 2))
    return Concern(adversary=adversary, text=text, source_model="codex/gpt-5.5")


def _fake_call_model_factory(per_call_batch_sizes: list[int]):
    """Return a fake call_model that records each call's concern count.

    The fake returns a JSON response that fabricates an evaluation per concern
    in the user_message, so evaluate_concerns can build Evaluation objects.
    """

    def fake(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
        # Count concerns in this batch by counting "### Concern" headers in
        # the user message (matches the real format from evaluate_concerns).
        concern_count = user_message.count("### Concern")
        per_call_batch_sizes.append(concern_count)
        # Fabricate evaluations for each concern.
        evaluations = [
            {
                "concern_index": i,
                "verdict": "accepted",
                "reasoning": f"fake reasoning {i}",
                "severity": "medium",
            }
            for i in range(concern_count)
        ]
        response = json.dumps({"evaluations": evaluations})
        return response, 1000, 1000

    return fake


# -----------------------------------------------------------------------------
# Backward compatibility: flat int batch_size still works
# -----------------------------------------------------------------------------


def test_flat_int_batch_size_unchanged_path(monkeypatch):
    """With int batch_size, the function uses the historical batching path."""
    concerns = [_make_concern(i) for i in range(20)]
    sizes_seen: list[int] = []
    monkeypatch.setattr(
        "gauntlet.phase_4_evaluation.call_model",
        _fake_call_model_factory(sizes_seen),
    )

    evals = evaluate_concerns_multi_model(
        spec="dummy spec",
        concerns=concerns,
        models=["model-a", "model-b"],
        config=GauntletConfig(),
        batch_size=10,
    )

    # 20 concerns / 10 = 2 batches × 2 models = 4 calls expected.
    assert len(sizes_seen) == 4
    # Each call processes 10 concerns.
    assert all(s == 10 for s in sizes_seen)
    # Output contains one consensus eval per concern.
    assert len(evals) == 20


# -----------------------------------------------------------------------------
# Tier dispatch: list[BatchTier] argument
# -----------------------------------------------------------------------------


def test_tier_dispatch_runs_each_tier_with_its_own_batch_size(monkeypatch):
    """Tiered call: each tier evaluated with its declared batch size."""
    easy = [_make_concern(i, text_len=50) for i in range(10)]
    med = [_make_concern(i + 100, text_len=200) for i in range(6)]
    hard = [_make_concern(i + 200, text_len=600) for i in range(4)]
    tiers = [
        BatchTier(name="easy", concerns=easy, batch_size=5),
        BatchTier(name="med", concerns=med, batch_size=3),
        BatchTier(name="hard", concerns=hard, batch_size=2),
    ]
    sizes_seen: list[int] = []
    monkeypatch.setattr(
        "gauntlet.phase_4_evaluation.call_model",
        _fake_call_model_factory(sizes_seen),
    )

    evals = evaluate_concerns_multi_model(
        spec="dummy spec",
        concerns=[],  # ignored under tier dispatch
        models=["model-a", "model-b"],
        config=GauntletConfig(),
        batch_size=tiers,
    )

    # Calls per tier per model:
    #   easy: 10/5  = 2 batches × 2 models = 4 calls of size 5
    #   med:  6/3   = 2 batches × 2 models = 4 calls of size 3
    #   hard: 4/2   = 2 batches × 2 models = 4 calls of size 2
    # Total: 12 calls.
    assert len(sizes_seen) == 12
    # Each batch's size should match its tier's batch_size.
    sizes_count = {s: sizes_seen.count(s) for s in set(sizes_seen)}
    assert sizes_count == {5: 4, 3: 4, 2: 4}, sizes_count

    # Output: every input concern got an evaluation.
    assert len(evals) == 10 + 6 + 4
    # Output ordering follows tier order (easy first, hard last). Verify by
    # checking that easy-tier concern ids come before hard-tier ids in evals.
    eval_concern_ids = [e.concern.id for e in evals]
    easy_ids = {c.id for c in easy}
    hard_ids = {c.id for c in hard}
    last_easy_idx = max(i for i, cid in enumerate(eval_concern_ids) if cid in easy_ids)
    first_hard_idx = min(i for i, cid in enumerate(eval_concern_ids) if cid in hard_ids)
    assert last_easy_idx < first_hard_idx


def test_tier_dispatch_with_empty_tier_list(monkeypatch):
    """Empty tier list returns empty evaluations and makes no calls."""
    sizes_seen: list[int] = []
    monkeypatch.setattr(
        "gauntlet.phase_4_evaluation.call_model",
        _fake_call_model_factory(sizes_seen),
    )
    evals = evaluate_concerns_multi_model(
        spec="dummy spec",
        concerns=[_make_concern(99)],  # ignored
        models=["model-a", "model-b"],
        config=GauntletConfig(),
        batch_size=[],
    )
    assert evals == []
    assert sizes_seen == []


def test_tier_dispatch_skips_empty_tiers(monkeypatch):
    """A tier with no concerns is silently skipped."""
    populated = [_make_concern(i) for i in range(4)]
    tiers = [
        BatchTier(name="easy", concerns=[], batch_size=5),
        BatchTier(name="med", concerns=populated, batch_size=2),
        BatchTier(name="hard", concerns=[], batch_size=12),
    ]
    sizes_seen: list[int] = []
    monkeypatch.setattr(
        "gauntlet.phase_4_evaluation.call_model",
        _fake_call_model_factory(sizes_seen),
    )

    evals = evaluate_concerns_multi_model(
        spec="dummy spec",
        concerns=[],
        models=["model-a", "model-b"],
        config=GauntletConfig(),
        batch_size=tiers,
    )

    # Only the 'med' tier has concerns: 4/2 = 2 batches × 2 models = 4 calls.
    assert len(sizes_seen) == 4
    assert all(s == 2 for s in sizes_seen)
    assert len(evals) == 4


def test_tier_dispatch_equivalence_with_flat_when_single_tier_matches(monkeypatch):
    """Single-tier dispatch with batch=N produces same eval count as flat=N."""
    concerns = [_make_concern(i) for i in range(15)]

    # Flat call.
    flat_sizes: list[int] = []
    monkeypatch.setattr(
        "gauntlet.phase_4_evaluation.call_model",
        _fake_call_model_factory(flat_sizes),
    )
    flat_evals = evaluate_concerns_multi_model(
        spec="dummy spec",
        concerns=concerns,
        models=["model-a", "model-b"],
        config=GauntletConfig(),
        batch_size=5,
    )

    # Single-tier call.
    tier_sizes: list[int] = []
    monkeypatch.setattr(
        "gauntlet.phase_4_evaluation.call_model",
        _fake_call_model_factory(tier_sizes),
    )
    tier_evals = evaluate_concerns_multi_model(
        spec="dummy spec",
        concerns=[],
        models=["model-a", "model-b"],
        config=GauntletConfig(),
        batch_size=[BatchTier(name="all", concerns=concerns, batch_size=5)],
    )

    # Same number of calls (3 batches × 2 models = 6) and same eval count.
    assert len(flat_sizes) == len(tier_sizes) == 6
    assert len(flat_evals) == len(tier_evals) == 15
    # Same set of concern ids in both outputs.
    assert {e.concern.id for e in flat_evals} == {e.concern.id for e in tier_evals}
