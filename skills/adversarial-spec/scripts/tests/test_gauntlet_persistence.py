"""Contract tests for gauntlet persistence and manifest formatting."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from gauntlet.core_types import Concern, Evaluation, GauntletConfig, PhaseMetrics
from gauntlet.persistence import (
    CONCERNS_PHASE,
    EVALUATION_PHASE,
    _write_json_atomic,
    format_path_safe,
    get_config_hash,
    load_partial_run,
    load_run_manifest,
    save_checkpoint,
    save_partial_clustering,
    save_run_manifest,
    update_run_manifest,
)
from gauntlet.reporting import format_run_manifest


@pytest.fixture
def checkpoint_dir(monkeypatch, tmp_path):
    """Isolate gauntlet checkpoint/manifest files under a temp directory."""
    path = tmp_path / ".adversarial-spec-gauntlet"
    monkeypatch.setattr("gauntlet.persistence.GAUNTLET_DIR", path)
    return path


def _concern(adversary: str, text: str, concern_id: str) -> Concern:
    return Concern(
        adversary=adversary,
        text=text,
        severity="medium",
        id=concern_id,
    )


def test_write_json_atomic_crash_safety(monkeypatch, checkpoint_dir):
    """Failed writes should preserve the original file and clean up temp files."""
    target = checkpoint_dir / "atomic.json"
    _write_json_atomic(target, {"key": "value"})
    original = json.loads(target.read_text())

    def broken_dump(data, fp, indent=2):  # noqa: ANN001
        fp.write('{"broken": ')
        raise OSError("disk full")

    monkeypatch.setattr("gauntlet.persistence.json.dump", broken_dump)

    with pytest.raises(OSError, match="disk full"):
        _write_json_atomic(target, {"key": "new-value"})

    assert json.loads(target.read_text()) == original
    assert list(checkpoint_dir.glob("*.tmp")) == []


def test_load_partial_run_valid_checkpoint(checkpoint_dir):
    """Matching checkpoint envelopes should deserialize into resumable objects."""
    config = GauntletConfig()
    spec_hash = "a1b2c3d4" * 8
    config_hash = get_config_hash(config)
    concern = _concern("paranoid_security", "Test concern", "PARA-1234")

    save_checkpoint("concerns", CONCERNS_PHASE, [concern], spec_hash, config_hash)
    raw_path = checkpoint_dir / f"raw-responses-{spec_hash[:8]}.json"
    raw_path.write_text(json.dumps({"paranoid_security": "raw llm output"}))

    partial = load_partial_run(spec_hash, config)

    assert partial["phase_1"]["concerns"][0].id == "PARA-1234"
    assert partial["phase_1"]["concerns"][0].adversary == "paranoid_security"
    assert partial["phase_1"]["raw_responses"] == {"paranoid_security": "raw llm output"}
    assert partial["phase_1"]["timing"] == {}


def test_load_partial_run_corrupted_json(checkpoint_dir, capsys):
    """Corrupt checkpoint files should be ignored without crashing."""
    spec_hash = "deadbeef" * 8
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / f"concerns-{spec_hash[:8]}.json").write_bytes(b"not json {{{")

    partial = load_partial_run(spec_hash, GauntletConfig())

    assert partial == {}
    assert "ignoring unreadable JSON file" in capsys.readouterr().err


def test_load_partial_run_config_mismatch(checkpoint_dir, capsys):
    """Changing the config should invalidate old checkpoint data."""
    original_config = GauntletConfig(timeout=300)
    new_config = GauntletConfig(timeout=120)
    spec_hash = "cafebabe" * 8
    concern = _concern("burned_oncall", "Mismatch concern", "BURN-1")

    save_checkpoint(
        "concerns",
        CONCERNS_PHASE,
        [concern],
        spec_hash,
        get_config_hash(original_config),
    )

    partial = load_partial_run(spec_hash, new_config)

    assert partial == {}
    assert "Config changed since last run" in capsys.readouterr().err


def test_load_partial_run_legacy_format(checkpoint_dir, capsys):
    """Bare JSON arrays remain readable for diagnostics but are not resumable."""
    spec_hash = "1234abcd" * 8
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    legacy = [{"adversary": "test", "text": "legacy concern", "id": "TEST-1"}]
    (checkpoint_dir / f"concerns-{spec_hash[:8]}.json").write_text(json.dumps(legacy))

    partial = load_partial_run(spec_hash, GauntletConfig())

    assert partial == {}
    assert "legacy checkpoint format is not resumable" in capsys.readouterr().err


def test_concern_set_hash_mismatch_forces_reeval(checkpoint_dir, capsys):
    """Phase 4 checkpoints should be discarded when Phase 3.5 concern IDs changed."""
    config = GauntletConfig()
    spec_hash = "ff00aa11" * 8
    config_hash = get_config_hash(config)

    concern_a = _concern("paranoid_security", "Concern A", "PARA-1")
    concern_b = _concern("burned_oncall", "Concern B", "BURN-2")
    concern_b_new = _concern("burned_oncall", "Concern B replacement", "BURN-3")
    evaluation_a = Evaluation(concern=concern_a, verdict="accepted", reasoning="valid")
    evaluation_b = Evaluation(concern=concern_b, verdict="dismissed", reasoning="invalid")

    save_partial_clustering(spec_hash, [concern_a, concern_b_new], config_hash)
    save_checkpoint(
        "evaluations",
        EVALUATION_PHASE,
        [evaluation_a, evaluation_b],
        spec_hash,
        config_hash,
    )

    partial = load_partial_run(spec_hash, config)

    assert "phase_3_5" in partial
    assert "phase_4" not in partial
    assert "concern set changed" in capsys.readouterr().err


def test_config_hash_deterministic():
    """Config hashes should be stable and sensitive to meaningful changes."""
    config_a = GauntletConfig(timeout=300)
    config_b = GauntletConfig(timeout=300)
    config_c = GauntletConfig(timeout=120)

    hash_a = get_config_hash(config_a, ["codex/gpt-5.4"], ["claude-opus-4-6"], ["paranoid_security"])
    hash_b = get_config_hash(config_b, ["codex/gpt-5.4"], ["claude-opus-4-6"], ["paranoid_security"])
    hash_c = get_config_hash(config_c, ["codex/gpt-5.4"], ["claude-opus-4-6"], ["paranoid_security"])

    assert hash_a == hash_b
    assert hash_a != hash_c


def test_format_path_safe_rejects_traversal(tmp_path):
    """Traversal attempts should fail before any checkpoint path is used."""
    safe = format_path_safe(tmp_path, "concerns-abcd1234.json")
    assert safe == (tmp_path / "concerns-abcd1234.json").resolve()

    with pytest.raises(ValueError, match="Path traversal attempt"):
        format_path_safe(tmp_path, "../escape.json")


def test_manifest_round_trip_and_formatting(checkpoint_dir):
    """Run manifests should round-trip and render into readable CLI text."""
    spec_hash = "feedface" * 8
    manifest_path = save_run_manifest({}, spec_hash)

    update_run_manifest(
        manifest_path,
        PhaseMetrics(
            phase="phase_1_attacks",
            phase_index=1,
            status="completed",
            duration_seconds=12.5,
            input_tokens=123,
            output_tokens=456,
            models_used=["codex/gpt-5.4"],
            config_snapshot={"timeout": 300},
            spec_hash=spec_hash,
        ),
    )
    update_run_manifest(manifest_path, {"status": "completed"})

    manifest = load_run_manifest(spec_hash[:8])

    assert manifest is not None
    assert manifest["status"] == "completed"
    assert len(manifest["phases"]) == 1

    formatted = format_run_manifest(manifest)
    assert "Gauntlet Run Manifest" in formatted
    assert "phase_1_attacks" in formatted
    assert "codex/gpt-5.4" in formatted
    assert "completed" in formatted
