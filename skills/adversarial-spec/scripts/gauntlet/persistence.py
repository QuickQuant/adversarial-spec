"""Persistence layer for the gauntlet pipeline.

Extracted from gauntlet_monolith.py — file I/O, stats tracking, resolved
concerns database, and checkpoint/resume support.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
import uuid
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from filelock import FileLock
from gauntlet.core_types import (
    CheckpointMeta,
    Concern,
    DismissalReviewStats,
    Evaluation,
    FinalBossResult,
    FinalBossVerdict,
    GauntletConfig,
    GauntletResult,
    PhaseMetrics,
)

# =============================================================================
# PATH CONSTANTS
# =============================================================================

STATS_DIR = Path.home() / ".adversarial-spec"
STATS_FILE = STATS_DIR / "adversary_stats.json"
RUNS_DIR = STATS_DIR / "runs"
MEDALS_DIR = STATS_DIR / "medals"
RESOLVED_CONCERNS_FILE = STATS_DIR / "resolved_concerns.json"
GAUNTLET_DIR = Path(".adversarial-spec-gauntlet")
CHECKPOINT_SCHEMA_VERSION = 2
CONCERNS_PHASE = "phase_1_attacks"
CLUSTERING_PHASE = "phase_3_5_clustering"
EVALUATION_PHASE = "phase_4_evaluation"
FINAL_BOSS_PHASE = "phase_7_final_boss"

_CHECKPOINT_FILENAMES = {
    "concerns": (CONCERNS_PHASE, "concerns-{hash}.json"),
    CONCERNS_PHASE: (CONCERNS_PHASE, "concerns-{hash}.json"),
    "raw-responses": (CONCERNS_PHASE, "raw-responses-{hash}.json"),
    "clustered-concerns": (CLUSTERING_PHASE, "clustered-concerns-{hash}.json"),
    CLUSTERING_PHASE: (CLUSTERING_PHASE, "clustered-concerns-{hash}.json"),
    "evaluations": (EVALUATION_PHASE, "evaluations-{hash}.json"),
    EVALUATION_PHASE: (EVALUATION_PHASE, "evaluations-{hash}.json"),
    "final-boss": (FINAL_BOSS_PHASE, "final-boss-{hash}.json"),
    FINAL_BOSS_PHASE: (FINAL_BOSS_PHASE, "final-boss-{hash}.json"),
}


def _utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with a stable trailing Z."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _warn(message: str) -> None:
    """Emit a resume/persistence warning without raising."""
    print(message, file=sys.stderr)


def _lock_for(path: Path) -> FileLock:
    """Return the sidecar lock used for coordinated checkpoint I/O."""
    return FileLock(f"{path}.lock")


def _serialize_dataclass(obj: Any) -> Any:
    """Recursively serialize dataclasses, enums, and paths into JSON-safe values."""
    if is_dataclass(obj):
        return {
            field.name: _serialize_dataclass(getattr(obj, field.name))
            for field in fields(obj)
        }
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(key): _serialize_dataclass(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize_dataclass(item) for item in obj]
    return obj


def _canonical_json(data: Any) -> str:
    """Canonical JSON form for integrity hashing."""
    return json.dumps(
        _serialize_dataclass(data),
        sort_keys=True,
        separators=(",", ":"),
    )


def _data_hash(data: Any) -> str:
    """Hash serialized data for checkpoint integrity validation."""
    return hashlib.sha256(_canonical_json(data).encode()).hexdigest()


def _load_json_safe(path: Path) -> Optional[Any]:
    """Load JSON if present and valid, otherwise return None."""
    if not path.exists():
        return None

    try:
        with _lock_for(path):
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        _warn(f"Warning: ignoring unreadable JSON file {path}: {exc}")
        return None


def _write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON atomically using a same-directory temp file and replace."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with _lock_for(path):
        tmp = tempfile.NamedTemporaryFile(
            dir=path.parent,
            delete=False,
            suffix=".tmp",
            mode="w",
            encoding="utf-8",
        )
        try:
            json.dump(_serialize_dataclass(data), tmp, indent=2)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, path)
        except Exception:
            try:
                tmp.close()
            except OSError:
                pass
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise


def format_path_safe(base_dir: Path, filename: str) -> Path:
    """Resolve a path under base_dir and reject traversal outside it."""
    if ".." in filename or filename.startswith("/"):
        raise ValueError(f"Path traversal attempt: {filename!r}")

    resolved = (base_dir / filename).resolve()
    base_resolved = base_dir.resolve()

    try:
        resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(f"Path escapes base directory: {resolved}") from exc

    return resolved


def _resolve_checkpoint_path(path_or_key: str | Path, spec_hash: str) -> tuple[str, Path]:
    """Map a logical checkpoint name to its canonical file path."""
    if isinstance(path_or_key, Path):
        return "", path_or_key

    if path_or_key in _CHECKPOINT_FILENAMES:
        phase, pattern = _CHECKPOINT_FILENAMES[path_or_key]
        filename = pattern.format(hash=spec_hash[:8])
        return phase, format_path_safe(GAUNTLET_DIR, filename)

    if path_or_key.endswith(".json"):
        return "", format_path_safe(GAUNTLET_DIR, Path(path_or_key).name)

    raise ValueError(f"Unknown checkpoint path/key: {path_or_key!r}")


def _normalize_config_payload(config: Any) -> dict[str, Any]:
    """Keep only config fields that actually influence gauntlet outputs."""
    if isinstance(config, GauntletConfig):
        return {
            "timeout": config.timeout,
            "attack_codex_reasoning": config.attack_codex_reasoning,
            "eval_codex_reasoning": config.eval_codex_reasoning,
        }

    if is_dataclass(config):
        payload = _serialize_dataclass(config)
    elif isinstance(config, dict):
        payload = dict(config)
    else:
        payload = {
            key: value
            for key, value in vars(config).items()
            if not key.startswith("_")
        }

    for ephemeral_key in ("auto_checkpoint", "resume", "unattended"):
        payload.pop(ephemeral_key, None)
    return payload


def get_config_hash(
    config: Any,
    attack_models: Optional[list[str]] = None,
    eval_models: Optional[list[str]] = None,
    adversaries: Optional[list[str]] = None,
    flags: Optional[dict[str, Any]] = None,
) -> str:
    """Return a deterministic SHA-256 fingerprint for resume compatibility."""
    payload = {
        "config": _normalize_config_payload(config),
        "attack_models": attack_models or [],
        "eval_models": eval_models or [],
        "adversaries": adversaries or [],
        "flags": flags or {},
    }
    return hashlib.sha256(_canonical_json(payload).encode()).hexdigest()


def _deserialize_concern(data: dict[str, Any]) -> Concern:
    """Rehydrate a Concern from persisted JSON."""
    return Concern(
        adversary=data["adversary"],
        text=data["text"],
        severity=data.get("severity", "medium"),
        id=data.get("id", ""),
        source_model=data.get("source_model", ""),
    )


def _deserialize_evaluation(data: dict[str, Any]) -> Evaluation:
    """Rehydrate an Evaluation from persisted JSON."""
    return Evaluation(
        concern=_deserialize_concern(data["concern"]),
        verdict=data["verdict"],
        reasoning=data.get("reasoning", ""),
        severity=data.get("severity", ""),
    )


def _deserialize_dismissal_review_stats(data: Optional[dict[str, Any]]) -> DismissalReviewStats:
    """Rehydrate dismissal-review telemetry."""
    if not data:
        return DismissalReviewStats()
    return DismissalReviewStats(
        dismissed_simplifications_reviewed=data.get("dismissed_simplifications_reviewed", 0),
        dismissals_flagged_invalid=data.get("dismissals_flagged_invalid", 0),
        flagged_dismissals=data.get("flagged_dismissals", []),
    )


def _deserialize_final_boss_result(data: dict[str, Any]) -> FinalBossResult:
    """Rehydrate a FinalBossResult from persisted JSON."""
    verdict = data.get("verdict", FinalBossVerdict.REFINE.value)
    return FinalBossResult(
        verdict=FinalBossVerdict(verdict),
        response=data.get("response", ""),
        concerns=data.get("concerns", []),
        alternate_approaches=data.get("alternate_approaches", []),
        reconsider_reason=data.get("reconsider_reason", ""),
        model=data.get("model", ""),
        tokens_used=data.get("tokens_used", 0),
        dismissal_review_stats=_deserialize_dismissal_review_stats(
            data.get("dismissal_review_stats")
        ),
        process_meta_report=data.get("process_meta_report", ""),
        self_meta_report=data.get("self_meta_report", ""),
    )


def _load_checkpoint_envelope(
    path: Path,
    *,
    spec_hash: str,
    config_hash: Optional[str],
    allow_plain_json: bool = False,
) -> Optional[Any]:
    """Load and validate a checkpoint envelope, or optional plain JSON payload."""
    payload = _load_json_safe(path)
    if payload is None:
        return None

    if allow_plain_json and isinstance(payload, dict) and "_meta" not in payload:
        return payload

    if not isinstance(payload, dict) or "_meta" not in payload or "data" not in payload:
        if isinstance(payload, list):
            _warn(f"Warning: legacy checkpoint format is not resumable: {path.name}")
        else:
            _warn(f"Warning: invalid checkpoint format ignored: {path.name}")
        return None

    meta = payload["_meta"]
    if not isinstance(meta, dict):
        _warn(f"Warning: invalid checkpoint metadata ignored: {path.name}")
        return None

    if meta.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        _warn(f"Warning: unsupported checkpoint schema ignored: {path.name}")
        return None

    if meta.get("spec_hash") != spec_hash:
        _warn(f"Warning: checkpoint spec hash mismatch ignored: {path.name}")
        return None

    if config_hash is not None and meta.get("config_hash") != config_hash:
        _warn("Config changed since last run — starting fresh")
        return None

    expected_hash = meta.get("data_hash")
    if expected_hash and expected_hash != _data_hash(payload["data"]):
        _warn(f"Warning: checkpoint integrity check failed: {path.name}")
        return None

    return payload["data"]


# =============================================================================
# ADVERSARY STATS
# =============================================================================


def load_adversary_stats() -> dict:
    """Load adversary statistics from disk."""
    stats = _load_json_safe(STATS_FILE)
    if not isinstance(stats, dict):
        return {
            "last_updated": None,
            "total_runs": 0,
            "adversaries": {},
            "models": {},
        }
    return stats


def save_adversary_stats(stats: dict) -> None:
    """Save adversary statistics to disk."""
    stats["last_updated"] = datetime.now().isoformat()
    _write_json_atomic(STATS_FILE, stats)


def update_adversary_stats(result: GauntletResult) -> dict:
    """Update adversary statistics with results from a gauntlet run.

    Tracks cost-weighted metrics:
    - dismissal_effort_total: cumulative chars in dismissal reasoning
    - signal_score_sum: sum of signal scores across runs (for averaging)
    """
    stats = load_adversary_stats()

    stats["last_updated"] = datetime.now().isoformat()
    stats["total_runs"] = stats.get("total_runs", 0) + 1

    # Update per-adversary stats
    run_stats = result.get_adversary_stats()
    for adv, adv_run in run_stats.items():
        if adv not in stats["adversaries"]:
            stats["adversaries"][adv] = {
                "concerns_raised": 0,
                "accepted": 0,
                "acknowledged": 0,
                "dismissed": 0,
                "deferred": 0,
                "rebuttals_won": 0,
                "rebuttals_lost": 0,
                "dismissal_effort_total": 0,
                "signal_score_sum": 0.0,
                "runs_with_concerns": 0,
                "notable_finds": [],
            }

        existing = stats["adversaries"][adv]
        existing["concerns_raised"] += adv_run["concerns_raised"]
        existing["accepted"] += adv_run["accepted"]
        existing["acknowledged"] = existing.get("acknowledged", 0) + adv_run.get("acknowledged", 0)
        existing["dismissed"] += adv_run["dismissed"]
        existing["deferred"] += adv_run["deferred"]
        existing["rebuttals_won"] += adv_run["rebuttals_won"]
        existing["rebuttals_lost"] += adv_run["rebuttals_lost"]

        existing["dismissal_effort_total"] = existing.get("dismissal_effort_total", 0) + (
            adv_run["dismissal_effort"] * adv_run["dismissed"]
        )

        if adv_run["concerns_raised"] > 0:
            existing["signal_score_sum"] = existing.get("signal_score_sum", 0) + adv_run["signal_score"]
            existing["runs_with_concerns"] = existing.get("runs_with_concerns", 0) + 1

        total = existing["concerns_raised"]
        existing["acceptance_rate"] = round(existing["accepted"] / total, 3) if total > 0 else 0.0

        if existing["dismissed"] > 0:
            existing["avg_dismissal_effort"] = round(
                existing["dismissal_effort_total"] / existing["dismissed"], 0
            )
        else:
            existing["avg_dismissal_effort"] = 0

        if existing.get("runs_with_concerns", 0) > 0:
            existing["avg_signal_score"] = round(
                existing["signal_score_sum"] / existing["runs_with_concerns"], 3
            )
        else:
            existing["avg_signal_score"] = 0.0

    # Update model stats
    model_roles: list[tuple[str, str]] = []
    attack_models = [m.strip() for m in result.adversary_model.split(",") if m.strip()]
    eval_models = [m.strip() for m in result.eval_model.split(",") if m.strip()]
    for model in attack_models:
        model_roles.append((model, "adversary"))
    for model in eval_models:
        model_roles.append((model, "evaluation"))

    cost_share = result.total_cost / max(1, len(model_roles))
    for model, role in model_roles:
        if model not in stats["models"]:
            stats["models"][model] = {
                "role": role,
                "runs": 0,
                "total_cost": 0.0,
            }
        stats["models"][model]["runs"] += 1
        stats["models"][model]["total_cost"] += cost_share

    # Track model pairing effectiveness
    pairing_key = f"{result.adversary_model} + {result.eval_model}"
    if "model_pairings" not in stats:
        stats["model_pairings"] = {}
    if pairing_key not in stats["model_pairings"]:
        stats["model_pairings"][pairing_key] = {
            "runs": 0,
            "total_concerns": 0,
            "accepted": 0,
            "dismissed": 0,
            "avg_acceptance_rate": 0.0,
        }

    pairing = stats["model_pairings"][pairing_key]
    pairing["runs"] += 1
    total_concerns = len(result.concerns)
    accepted = len([e for e in result.evaluations if e.verdict in ("accepted", "acknowledged")])
    dismissed = len([e for e in result.evaluations if e.verdict == "dismissed"])
    pairing["total_concerns"] += total_concerns
    pairing["accepted"] += accepted
    pairing["dismissed"] += dismissed
    if pairing["total_concerns"] > 0:
        pairing["avg_acceptance_rate"] = round(pairing["accepted"] / pairing["total_concerns"], 3)

    save_adversary_stats(stats)
    return stats


# =============================================================================
# GAUNTLET RUN STORAGE
# =============================================================================


def save_gauntlet_run(result: GauntletResult, spec: str) -> str:
    """Save a full gauntlet run to disk for analysis and debugging.

    Returns path to saved file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    spec_hash = (result.spec_hash or get_spec_hash(spec))[:8]
    filename = f"{timestamp}_{spec_hash}.json"
    filepath = RUNS_DIR / filename

    run_data = {
        "timestamp": datetime.now().isoformat(),
        "spec_hash": spec_hash,
        "spec_preview": spec[:500] + "..." if len(spec) > 500 else spec,
        "spec_length": len(spec),
        "result": result.to_dict(),
    }

    _write_json_atomic(filepath, run_data)

    # Update index
    index_file = STATS_DIR / "runs_index.json"
    index = _load_json_safe(index_file)
    if not isinstance(index, dict):
        index = {"runs": []}

    raw_count = len(result.raw_concerns) if result.raw_concerns else len(result.concerns)
    index["runs"].append({
        "file": filename,
        "timestamp": run_data["timestamp"],
        "spec_hash": spec_hash,
        "raw_concerns": raw_count,
        "final_concerns": len(result.final_concerns),
        "adversary_model": result.adversary_model,
        "eval_model": result.eval_model,
        "total_cost": result.total_cost,
        "total_time": result.total_time,
    })

    index["runs"] = index["runs"][-100:]
    _write_json_atomic(index_file, index)

    return str(filepath)


def list_gauntlet_runs(limit: int = 10) -> str:
    """List recent gauntlet runs with summary stats."""
    index_file = STATS_DIR / "runs_index.json"

    index = _load_json_safe(index_file)
    if index is None:
        return "No gauntlet runs recorded yet."
    if not isinstance(index, dict):
        return "Error reading runs index."

    if not index.get("runs"):
        return "No gauntlet runs recorded yet."

    runs = index["runs"][-limit:][::-1]

    lines = [f"=== Recent Gauntlet Runs (last {len(runs)}) ===", ""]

    for run in runs:
        ts = run.get("timestamp", "unknown")[:19]
        raw = run.get("raw_concerns", "?")
        final = run.get("final_concerns", "?")
        cost = run.get("total_cost", 0)
        time_s = run.get("total_time", 0)

        lines.append(f"{ts}  [{run.get('spec_hash', '?')[:8]}]")
        lines.append(f"  Concerns: {raw} raw → {final} final")
        lines.append(f"  Time: {time_s:.1f}s  Cost: ${cost:.4f}")
        lines.append("")

    return "\n".join(lines)


def load_gauntlet_run(filename: str) -> Optional[dict]:
    """Load a specific gauntlet run by filename."""
    filepath = RUNS_DIR / filename
    run_data = _load_json_safe(filepath)
    if not isinstance(run_data, dict):
        return None
    return run_data


# =============================================================================
# CHECKPOINTS AND MANIFESTS
# =============================================================================


def save_checkpoint(
    path_or_key: str | Path,
    phase: str,
    data: Any,
    spec_hash: str,
    config_hash: str,
) -> str:
    """Persist a checkpoint envelope for a resumable gauntlet phase."""
    inferred_phase, path = _resolve_checkpoint_path(path_or_key, spec_hash)
    phase_name = phase or inferred_phase
    serialized = _serialize_dataclass(data)
    meta = CheckpointMeta(
        schema_version=CHECKPOINT_SCHEMA_VERSION,
        spec_hash=spec_hash,
        config_hash=config_hash,
        phase=phase_name,
        created_at=_utc_now_iso(),
        data_hash=_data_hash(serialized),
    )
    envelope = {
        "_meta": _serialize_dataclass(meta),
        "data": serialized,
    }
    _write_json_atomic(path, envelope)
    return str(path)


def save_partial_clustering(spec_hash: str, concerns: Any, config_hash: str) -> str:
    """Persist the Phase 3.5 clustering output for crash recovery."""
    return save_checkpoint(
        "clustered-concerns",
        CLUSTERING_PHASE,
        concerns,
        spec_hash,
        config_hash,
    )


def save_run_manifest(manifest: dict[str, Any], spec_hash: str) -> str:
    """Create a new run manifest file and return its path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"run-manifest-{spec_hash[:8]}-{timestamp}.json"
    path = format_path_safe(GAUNTLET_DIR, filename)
    manifest_data = {
        "spec_hash": spec_hash,
        "status": manifest.get("status", "running"),
        "created_at": manifest.get("created_at", _utc_now_iso()),
        "updated_at": _utc_now_iso(),
        "phases": manifest.get("phases", []),
    }
    for extra_key, value in manifest.items():
        if extra_key not in manifest_data:
            manifest_data[extra_key] = value
    _write_json_atomic(path, manifest_data)
    return str(path)


def update_run_manifest(
    manifest_path: Optional[str | Path],
    phase_metrics: PhaseMetrics | dict[str, Any],
) -> str:
    """Append phase metrics or update top-level manifest status."""
    phase_payload = _serialize_dataclass(phase_metrics)
    if manifest_path is None:
        spec_hash = phase_payload.get("spec_hash", "")
        manifest_path = save_run_manifest({}, spec_hash or "unknown")

    path = Path(manifest_path)
    manifest = _load_json_safe(path)
    if not isinstance(manifest, dict):
        manifest = {
            "spec_hash": phase_payload.get("spec_hash", ""),
            "status": "running",
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "phases": [],
        }

    manifest.setdefault("phases", [])
    manifest.setdefault("status", "running")
    if not manifest.get("spec_hash") and phase_payload.get("spec_hash"):
        manifest["spec_hash"] = phase_payload["spec_hash"]

    if "phase" in phase_payload:
        manifest["phases"].append(phase_payload)
    else:
        manifest.update(phase_payload)

    manifest["updated_at"] = _utc_now_iso()
    _write_json_atomic(path, manifest)
    return str(path)


def load_run_manifest(hash_prefix: Optional[str]) -> Optional[dict[str, Any]]:
    """Load the most recent run manifest matching a hash prefix."""
    if not GAUNTLET_DIR.exists():
        return None

    pattern = f"run-manifest-{hash_prefix}*.json" if hash_prefix else "run-manifest-*.json"
    matches = sorted(GAUNTLET_DIR.glob(pattern))
    if not matches:
        return None

    path = matches[-1]
    manifest = _load_json_safe(path)
    if manifest is None:
        return None
    if isinstance(manifest, list):
        manifest = {"spec_hash": hash_prefix or "", "phases": manifest}
    if not isinstance(manifest, dict):
        return None
    manifest.setdefault("phases", [])
    manifest["path"] = str(path)
    return manifest


def load_partial_run(
    spec_hash: str,
    config: Any,
    attack_models: Optional[list[str]] = None,
    eval_models: Optional[list[str]] = None,
    adversaries: Optional[list[str]] = None,
    flags: Optional[dict[str, Any]] = None,
) -> dict[str, dict[str, Any]]:
    """Load the resumable subset of a gauntlet run, discarding invalid files."""
    config_hash = get_config_hash(
        config,
        attack_models=attack_models,
        eval_models=eval_models,
        adversaries=adversaries,
        flags=flags,
    )
    partial: dict[str, dict[str, Any]] = {}

    concerns_path = format_path_safe(GAUNTLET_DIR, f"concerns-{spec_hash[:8]}.json")
    concerns_data = _load_checkpoint_envelope(
        concerns_path,
        spec_hash=spec_hash,
        config_hash=config_hash,
    )
    if isinstance(concerns_data, list):
        raw_path = format_path_safe(GAUNTLET_DIR, f"raw-responses-{spec_hash[:8]}.json")
        raw_responses = _load_checkpoint_envelope(
            raw_path,
            spec_hash=spec_hash,
            config_hash=config_hash,
            allow_plain_json=True,
        )
        if raw_responses is None:
            raw_responses = _load_json_safe(raw_path)
        partial["phase_1"] = {
            "concerns": [_deserialize_concern(item) for item in concerns_data],
            "timing": {},
            "raw_responses": raw_responses if isinstance(raw_responses, dict) else {},
        }

    clustered_path = format_path_safe(GAUNTLET_DIR, f"clustered-concerns-{spec_hash[:8]}.json")
    clustered_data = _load_checkpoint_envelope(
        clustered_path,
        spec_hash=spec_hash,
        config_hash=config_hash,
    )
    clustered_concerns: list[Concern] = []
    if isinstance(clustered_data, list):
        clustered_concerns = [_deserialize_concern(item) for item in clustered_data]
        partial["phase_3_5"] = {
            "clustered_concerns": clustered_concerns,
            "cluster_members": {},
        }
    elif isinstance(clustered_data, dict):
        clustered_concerns = [
            _deserialize_concern(item)
            for item in clustered_data.get("clustered_concerns", clustered_data.get("concerns", []))
        ]
        cluster_members = {
            rep_id: [_deserialize_concern(member) for member in members]
            for rep_id, members in clustered_data.get("cluster_members", {}).items()
        }
        partial["phase_3_5"] = {
            "clustered_concerns": clustered_concerns,
            "cluster_members": cluster_members,
        }

    evaluations_path = format_path_safe(GAUNTLET_DIR, f"evaluations-{spec_hash[:8]}.json")
    evaluations_data = _load_checkpoint_envelope(
        evaluations_path,
        spec_hash=spec_hash,
        config_hash=config_hash,
    )
    if isinstance(evaluations_data, list):
        evaluations = [_deserialize_evaluation(item) for item in evaluations_data]
        saved_concern_ids = {evaluation.concern.id for evaluation in evaluations}
        current_concern_ids = {concern.id for concern in clustered_concerns}
        if current_concern_ids and saved_concern_ids != current_concern_ids:
            _warn("Warning: evaluation checkpoint concern set changed — re-running evaluation")
        else:
            partial["phase_4"] = {
                "evaluations": evaluations,
                "saved_concern_ids": sorted(saved_concern_ids),
            }

    final_boss_path = format_path_safe(GAUNTLET_DIR, f"final-boss-{spec_hash[:8]}.json")
    final_boss_data = _load_checkpoint_envelope(
        final_boss_path,
        spec_hash=spec_hash,
        config_hash=config_hash,
    )
    if isinstance(final_boss_data, dict):
        partial["phase_7"] = {
            "final_boss_result": _deserialize_final_boss_result(final_boss_data)
        }

    return partial


# =============================================================================
# SPEC HASHING
# =============================================================================


def get_spec_hash(spec: str) -> str:
    """Get the full spec hash used for checkpointing and manifests."""
    return hashlib.sha256(spec.encode()).hexdigest()


# =============================================================================
# RESOLVED CONCERNS DATABASE
# =============================================================================

CONFIDENCE_ACCEPT_THRESHOLD = 0.7
CONFIDENCE_NOTE_THRESHOLD = 0.4
AGE_DECAY_HALFLIFE_DAYS = 14
SPEC_CHANGE_PENALTY = 0.7
USAGE_BOOST_PER_MATCH = 0.05
USAGE_BOOST_CAP = 0.3


def load_resolved_concerns() -> dict:
    """Load resolved concerns database."""
    data = _load_json_safe(RESOLVED_CONCERNS_FILE)
    if not isinstance(data, dict):
        return {"concerns": [], "last_updated": None}
    return data


def save_resolved_concerns(data: dict) -> None:
    """Save resolved concerns database."""
    data["last_updated"] = datetime.now().isoformat()
    _write_json_atomic(RESOLVED_CONCERNS_FILE, data)


def add_resolved_concern(
    pattern: str,
    explanation: str,
    adversary: str,
    spec_hash: Optional[str] = None,
    confidence: float = 0.9,
) -> None:
    """Add a resolved concern to the database."""
    data = load_resolved_concerns()
    data["concerns"].append({
        "id": str(uuid.uuid4()),
        "pattern": pattern,
        "explanation": explanation,
        "added_at": datetime.now().isoformat(),
        "adversary": adversary,
        "confidence": confidence,
        "spec_hash": spec_hash,
        "times_matched": 0,
        "last_matched": None,
        "verified_at": None,
    })
    save_resolved_concerns(data)


def calculate_explanation_confidence(
    explanation: dict,
    current_spec_hash: Optional[str] = None,
) -> tuple[float, str]:
    """Calculate current confidence in an explanation.

    Factors: age decay, spec change, usage boost, manual verification.
    """
    base_confidence = explanation.get("confidence", 0.9)
    added_at = explanation.get("added_at", "")
    verified_at = explanation.get("verified_at")
    spec_hash = explanation.get("spec_hash")
    times_matched = explanation.get("times_matched", 0)

    factors = []
    final_confidence = base_confidence

    reference_date = verified_at or added_at
    try:
        ref = datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
        now = datetime.now()
        if ref.tzinfo is not None:
            ref = ref.replace(tzinfo=None)
        age_days = (now - ref).days

        age_factor = math.pow(0.5, age_days / AGE_DECAY_HALFLIFE_DAYS)
        final_confidence *= age_factor

        if age_days > 30:
            factors.append(f"old ({age_days}d)")
        elif age_days > 14:
            factors.append(f"aging ({age_days}d)")
        elif verified_at:
            factors.append(f"verified {age_days}d ago")
    except (ValueError, TypeError):
        factors.append("invalid date")
        final_confidence *= 0.5

    if current_spec_hash and spec_hash and current_spec_hash != spec_hash:
        final_confidence *= SPEC_CHANGE_PENALTY
        factors.append("spec changed")

    if times_matched > 0:
        usage_boost = min(times_matched * USAGE_BOOST_PER_MATCH, USAGE_BOOST_CAP)
        final_confidence = min(final_confidence + usage_boost, 0.95)
        if times_matched >= 3:
            factors.append(f"validated {times_matched}x")

    reason = "; ".join(factors) if factors else "fresh"
    return round(min(final_confidence, 0.99), 3), reason


def record_explanation_match(explanation_id: str) -> None:
    """Record that an explanation was matched (for confidence boosting)."""
    data = load_resolved_concerns()
    for concern in data["concerns"]:
        if concern.get("id") == explanation_id:
            concern["times_matched"] = concern.get("times_matched", 0) + 1
            concern["last_matched"] = datetime.now().isoformat()
            break
    save_resolved_concerns(data)


def verify_explanation(explanation_id: str) -> None:
    """Manually mark an explanation as re-verified (resets age decay)."""
    data = load_resolved_concerns()
    for concern in data["concerns"]:
        if concern.get("id") == explanation_id:
            concern["verified_at"] = datetime.now().isoformat()
            break
    save_resolved_concerns(data)
