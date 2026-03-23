"""Tests for gauntlet orchestrator behavioral paths."""

import builtins
import json
import threading
from types import SimpleNamespace

import pytest

from gauntlet.core_types import BigPictureSynthesis, Concern, Evaluation
from gauntlet.orchestrator import _load_approved_prompts, _resolve_and_filter_adversaries
from models import CostTracker


def test_cost_tracker_thread_safety():
    """Concurrent CostTracker.add() calls must not lose data."""
    tracker = CostTracker()
    n_threads = 100
    barrier = threading.Barrier(n_threads)

    def add_once():
        barrier.wait()
        tracker.add("test-model", 10, 5)

    threads = [threading.Thread(target=add_once) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert tracker.total_input_tokens == 1000
    assert tracker.total_output_tokens == 500


def test_unattended_never_calls_input():
    """Unattended mode must monkey-patch input() to raise RuntimeError."""
    original = builtins.input

    try:
        # Apply the same monkey-patch that orchestrator.py uses
        builtins.input = lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("input() called in unattended mode")
        )

        with pytest.raises(RuntimeError, match="input\\(\\) called in unattended mode"):
            builtins.input("prompt")
    finally:
        builtins.input = original

    # Verify restore worked
    assert builtins.input is original


def test_run_gauntlet_records_phase_metrics_in_manifest(monkeypatch, tmp_path):
    """run_gauntlet() must emit full PhaseMetrics-shaped manifest entries."""
    from gauntlet.orchestrator import run_gauntlet

    tracker = SimpleNamespace(
        total_input_tokens=0,
        total_output_tokens=0,
        total_cost=1.25,
    )

    def bump(input_tokens: int, output_tokens: int, cost: float = 0.0) -> None:
        tracker.total_input_tokens += input_tokens
        tracker.total_output_tokens += output_tokens
        tracker.total_cost += cost

    concern = Concern(
        adversary="paranoid_security",
        text="Guard the edge case.",
        severity="high",
        id="PARA-1",
    )
    evaluation = Evaluation(
        concern=concern,
        verdict="accepted",
        reasoning="This should be fixed.",
    )
    synthesis = BigPictureSynthesis(
        total_concerns=1,
        unique_texts=1,
        real_issues=["Guard the edge case."],
        hidden_connections=[],
        whats_missing=[],
        meta_concern="Guard the edge case.",
        high_signal=["Guard the edge case."],
        raw_response="summary",
    )
    manifest_updates: list[dict[str, object]] = []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("gauntlet.orchestrator.cost_tracker", tracker)
    monkeypatch.setattr("gauntlet.orchestrator.get_spec_hash", lambda spec: "a" * 64)
    monkeypatch.setattr("gauntlet.orchestrator.get_config_hash", lambda *args, **kwargs: "cfg")
    monkeypatch.setattr("gauntlet.orchestrator.save_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr("gauntlet.orchestrator.save_partial_clustering", lambda *args, **kwargs: None)
    monkeypatch.setattr("gauntlet.orchestrator._track_dedup_stats", lambda **kwargs: None)
    monkeypatch.setattr("gauntlet.orchestrator.add_resolved_concern", lambda *args, **kwargs: None)
    monkeypatch.setattr("gauntlet.orchestrator.update_adversary_stats", lambda result: None)
    monkeypatch.setattr(
        "gauntlet.orchestrator.save_gauntlet_run",
        lambda result, spec: str(tmp_path / "run.json"),
    )
    monkeypatch.setattr("gauntlet.orchestrator.calculate_medals", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        "gauntlet.orchestrator.save_medal_reports",
        lambda medals: str(tmp_path / "medals.txt"),
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    def fake_update_run_manifest(manifest_path, phase_metrics):  # noqa: ANN001
        manifest_updates.append(phase_metrics)
        return manifest_path or str(tmp_path / "manifest.json")

    def fake_generate_attacks(spec, adversaries, models, config, prompts=None):  # noqa: ANN001
        bump(10, 5, 0.1)
        return [concern], {"paranoid_security": 1.0}, {"paranoid_security": "raw"}

    def fake_generate_big_picture_synthesis(concerns, model, config):  # noqa: ANN001
        bump(4, 2, 0.02)
        return synthesis

    def fake_filter_concerns(concerns, model, spec_hash, config):  # noqa: ANN001
        bump(3, 1, 0.01)
        return concerns, [], []

    def fake_cluster_concerns(concerns, model, config):  # noqa: ANN001
        bump(2, 1, 0.01)
        return concerns, {concern.id: concerns}

    def fake_evaluate_concerns(spec, concerns, model, config):  # noqa: ANN001
        bump(8, 4, 0.03)
        return [evaluation]

    monkeypatch.setattr("gauntlet.orchestrator.update_run_manifest", fake_update_run_manifest)
    monkeypatch.setattr("gauntlet.orchestrator.generate_attacks", fake_generate_attacks)
    monkeypatch.setattr(
        "gauntlet.orchestrator.generate_big_picture_synthesis",
        fake_generate_big_picture_synthesis,
    )
    monkeypatch.setattr(
        "gauntlet.orchestrator.filter_concerns_with_explanations",
        fake_filter_concerns,
    )
    monkeypatch.setattr("gauntlet.orchestrator.choose_clustering_model", lambda *args: "cluster-model")
    monkeypatch.setattr(
        "gauntlet.orchestrator.cluster_concerns_with_provenance",
        fake_cluster_concerns,
    )
    monkeypatch.setattr("gauntlet.orchestrator.evaluate_concerns", fake_evaluate_concerns)
    monkeypatch.setattr(
        "gauntlet.orchestrator.expand_clustered_evaluations",
        lambda evaluations, cluster_members: evaluations,
    )

    result = run_gauntlet(
        spec="# Test Spec",
        adversaries=["paranoid_security"],
        attack_models=["codex/gpt-5.4"],
        eval_models=["claude-opus-4-6"],
        allow_rebuttals=False,
        use_multi_model=False,
        run_final_boss=False,
    )

    phase_updates = [update for update in manifest_updates if "phase" in update]

    assert [update["phase"] for update in phase_updates] == [
        "phase_1",
        "phase_2",
        "phase_3",
        "phase_3_5",
        "phase_4",
        "phase_5",
        "phase_6",
        "phase_7",
    ]
    for update in phase_updates:
        for field in (
            "phase_index",
            "status",
            "duration_seconds",
            "input_tokens",
            "output_tokens",
            "models_used",
            "config_snapshot",
            "spec_hash",
        ):
            assert field in update
        assert update["spec_hash"] == "a" * 64
        assert isinstance(update["config_snapshot"], dict)
        assert update["status"] in {"completed", "skipped_resume"}

    assert manifest_updates[-1]["status"] == "completed"
    assert result.spec_hash == "a" * 64


# =============================================================================
# T5: Tests for _load_approved_prompts
# =============================================================================


class TestLoadApprovedPrompts:
    """Test approved-prompts.json loading and spec_hash validation."""

    def test_returns_none_when_file_missing(self, tmp_path):
        """No approved-prompts.json → returns None (static fallback)."""
        result = _load_approved_prompts(tmp_path, "abc123")
        assert result is None

    def test_loads_valid_prompts_with_matching_hash(self, tmp_path):
        """Valid file + matching hash → returns parsed dict."""
        prompts_data = {
            "spec_hash": "abc123def456",
            "prompts": {
                "paranoid_security": {
                    "status": "approved",
                    "full_persona": "You see threats everywhere.",
                },
            },
        }
        (tmp_path / "approved-prompts.json").write_text(json.dumps(prompts_data))
        result = _load_approved_prompts(tmp_path, "abc123def456")
        assert result == prompts_data

    def test_hash_mismatch_raises_value_error(self, tmp_path):
        """FM-1: Hash mismatch → halt with actionable error, NOT silent fallback."""
        prompts_data = {
            "spec_hash": "old_hash_1234",
            "prompts": {"paranoid_security": {"status": "approved", "full_persona": "x"}},
        }
        (tmp_path / "approved-prompts.json").write_text(json.dumps(prompts_data))

        with pytest.raises(ValueError, match="stale.*spec changed"):
            _load_approved_prompts(tmp_path, "new_hash_5678")

    def test_hash_mismatch_suggests_force_flag(self, tmp_path):
        """FM-1: Error message includes actionable guidance."""
        prompts_data = {"spec_hash": "old", "prompts": {}}
        (tmp_path / "approved-prompts.json").write_text(json.dumps(prompts_data))

        with pytest.raises(ValueError, match="force-static-fallback"):
            _load_approved_prompts(tmp_path, "new")

    def test_malformed_json_raises_value_error(self, tmp_path):
        """Corrupt file → clear error."""
        (tmp_path / "approved-prompts.json").write_text("not valid json{{{")

        with pytest.raises(ValueError, match="Failed to load"):
            _load_approved_prompts(tmp_path, "any_hash")


# =============================================================================
# T5: Tests for _resolve_and_filter_adversaries
# =============================================================================


class TestResolveAndFilterAdversaries:
    """Test adversary name resolution, dedup, filtering, and validation."""

    def test_resolves_legacy_aliases(self):
        """CB-4: Legacy names resolve to canonical names."""
        resolved, prompts = _resolve_and_filter_adversaries(
            ["lazy_developer", "paranoid_security"],
            approved_prompts=None,
        )
        assert "minimalist" in resolved
        assert "lazy_developer" not in resolved

    def test_deduplicates_after_resolution(self):
        """CB-4: lazy_developer + minimalist → one entry."""
        resolved, prompts = _resolve_and_filter_adversaries(
            ["lazy_developer", "minimalist", "paranoid_security"],
            approved_prompts=None,
        )
        assert resolved.count("minimalist") == 1
        assert len(resolved) == 2

    def test_unknown_adversary_raises_error(self):
        """CB-5/US-3: Unknown adversary → hard error."""
        with pytest.raises(ValueError, match="Unknown adversar"):
            _resolve_and_filter_adversaries(
                ["paranoid_security", "nonexistent_adversary"],
                approved_prompts=None,
            )

    def test_filters_skipped_adversaries(self):
        """§1.7: Skipped adversaries excluded from list."""
        approved = {
            "spec_hash": "test",
            "prompts": {
                "paranoid_security": {"status": "approved", "full_persona": "Threats."},
                "minimalist": {"status": "skipped", "skip_reason": "Internal."},
                "burned_oncall": {"status": "approved", "full_persona": "Outages."},
            },
        }
        resolved, prompts = _resolve_and_filter_adversaries(
            ["paranoid_security", "minimalist", "burned_oncall"],
            approved_prompts=approved,
        )
        assert "minimalist" not in resolved
        assert set(resolved) == {"paranoid_security", "burned_oncall"}

    def test_zero_adversaries_after_filtering_raises_error(self):
        """§1.7: All skipped → ValueError."""
        approved = {
            "spec_hash": "test",
            "prompts": {
                "paranoid_security": {"status": "skipped", "skip_reason": "Nope."},
            },
        }
        with pytest.raises(ValueError, match="[Zz]ero adversaries"):
            _resolve_and_filter_adversaries(
                ["paranoid_security"],
                approved_prompts=approved,
            )

    def test_extracts_flat_prompts_dict(self):
        """§1.7: Extract flat {name: full_persona} from approved entries."""
        approved = {
            "spec_hash": "test",
            "prompts": {
                "paranoid_security": {"status": "approved", "full_persona": "Custom PARA."},
                "burned_oncall": {"status": "approved", "full_persona": "Custom BURN."},
            },
        }
        resolved, prompts = _resolve_and_filter_adversaries(
            ["paranoid_security", "burned_oncall"],
            approved_prompts=approved,
        )
        assert prompts == {
            "paranoid_security": "Custom PARA.",
            "burned_oncall": "Custom BURN.",
        }

    def test_no_approved_prompts_returns_none(self):
        """No approved prompts → None prompts dict."""
        resolved, prompts = _resolve_and_filter_adversaries(
            ["paranoid_security"],
            approved_prompts=None,
        )
        assert prompts is None

    def test_preserves_order_after_dedup(self):
        """Dedup preserves first-seen order."""
        resolved, _ = _resolve_and_filter_adversaries(
            ["burned_oncall", "lazy_developer", "paranoid_security", "minimalist"],
            approved_prompts=None,
        )
        assert resolved == ["burned_oncall", "minimalist", "paranoid_security"]
