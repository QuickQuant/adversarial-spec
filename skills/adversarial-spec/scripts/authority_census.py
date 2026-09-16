"""Authority Census: Structural trigger evaluation, authority-paths.json authoring/validation, discovery scope, fingerprint hash (C-CENSUS #21550).

Implements Phase 4 authority-path census for all callable paths producing
external outcomes, enforcing coexistence policies and predecessor retirement.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import jsonschema

if __package__:
    from .gate_policy import RejectCode
else:
    from gate_policy import RejectCode

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "reference" / "authority-paths.schema.json"
)

STABLE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]{2,127}$")
VALID_STRUCTURAL_REASONS = frozenset({
    "equivalent_effect_paths",
    "separate_runtime",
    "authority_role_change",
})
VALID_CALLER_KINDS = frozenset({"product", "operator", "system", "harness", "unknown"})
VALID_ROLES = frozenset({
    "authoritative",
    "projection",
    "legacy",
    "emergency",
    "retiring",
    "dead",
})
VALID_DISPOSITIONS = frozenset({"retained", "retired", "removed", "not_applicable"})


@dataclass(frozen=True)
class CensusIssue:
    """An issue detected during authority census validation."""

    code: str
    path_id: str | None
    message: str
    severity: Literal["halt", "failing", "warning", "advisory"] = "failing"
    expected: dict[str, Any] = field(default_factory=dict)
    observed: dict[str, Any] = field(default_factory=dict)
    evidence_class: str = "MISMATCH"


def evaluate_structural_trigger(
    equivalent_effect_paths_count: int = 1,
    separate_runtime: bool = False,
    authority_role_change: bool = False,
    rationale: str = "",
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate whether an authority census is required by structural facts.

    Triggered when:
    - More than one equivalent effect path exists (> 1)
    - A separate runtime slot is deployed
    - An authority role change / migration is planned

    Returns a trigger dictionary conforming to authority-paths.schema.json.
    """
    reasons: list[str] = []
    if equivalent_effect_paths_count > 1:
        reasons.append("equivalent_effect_paths")
    if separate_runtime:
        reasons.append("separate_runtime")
    if authority_role_change:
        reasons.append("authority_role_change")

    triggered = len(reasons) > 0
    now_iso = (evaluated_at or datetime.now(UTC)).isoformat().replace("+00:00", "Z")

    result: dict[str, Any] = {
        "triggered": triggered,
        "structural_reasons": sorted(reasons),
        "evaluated_at": now_iso,
    }
    if rationale:
        result["rationale"] = rationale
    return result


def author_authority_census(
    trigger: Mapping[str, Any],
    outcome_classes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Construct an authority-paths document from trigger evaluation and outcome classes."""
    return {
        "schema_version": 1,
        "trigger": dict(trigger),
        "outcome_classes": [dict(c) for c in outcome_classes],
    }


def compute_census_fingerprint(census: Mapping[str, Any]) -> str:
    """Compute deterministic SHA-256 fingerprint over structural census contents.

    Excludes transient fields like evaluated_at and rationale.
    """
    structural = copy.deepcopy(dict(census))
    if "trigger" in structural and isinstance(structural["trigger"], dict):
        structural["trigger"] = {
            "triggered": structural["trigger"].get("triggered"),
            "structural_reasons": sorted(structural["trigger"].get("structural_reasons", [])),
        }
    canonical_json = json.dumps(structural, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical_json).hexdigest()}"


def _get_json_schema() -> dict[str, Any]:
    """Load the authority-paths JSON schema."""
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Authority paths schema missing: {SCHEMA_PATH}")
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_authority_paths(census: Mapping[str, Any]) -> list[CensusIssue]:
    """Validate an authority-paths document against schema and semantic policies.

    Checks:
    1. Structural JSON Schema conformance
    2. Stable ID conventions for outcomes, paths, callers, and authorities
    3. Path ID uniqueness across entire document
    4. Coexistence policy: multiple authoritative paths require compatibility_window
    5. Predecessor retirement: superseded paths require negative probes & retirement disposition
    6. Caller validity
    """
    issues: list[CensusIssue] = []

    # 1. JSON Schema validation
    try:
        schema = _get_json_schema()
        validator = jsonschema.Draft202012Validator(schema)
        schema_errors = list(validator.iter_errors(census))
        for err in schema_errors:
            issues.append(
                CensusIssue(
                    code="SCHEMA_VALIDATION_ERROR",
                    path_id=None,
                    message=f"Schema validation error at {err.json_path}: {err.message}",
                    severity="halt",
                    observed={"path": err.json_path, "message": err.message},
                )
            )
        if issues:
            return issues
    except Exception as exc:
        return [
            CensusIssue(
                code="SCHEMA_LOAD_ERROR",
                path_id=None,
                message=f"Failed to load or execute schema validation: {exc}",
                severity="halt",
            )
        ]

    trigger = census.get("trigger", {})
    outcome_classes = census.get("outcome_classes", [])
    all_path_ids: set[str] = set()

    for outcome in outcome_classes:
        outcome_id = outcome.get("outcome_id", "")
        if not STABLE_ID_PATTERN.match(outcome_id):
            issues.append(
                CensusIssue(
                    code="INVALID_STABLE_ID",
                    path_id=None,
                    message=f"Outcome ID {outcome_id!r} does not match stableId pattern",
                    severity="failing",
                    observed={"outcome_id": outcome_id},
                )
            )

        paths = outcome.get("paths", [])
        authoritative_targets: list[dict[str, Any]] = []
        authoritative_current: list[dict[str, Any]] = []

        for p in paths:
            path_id = p.get("path_id", "")
            if not STABLE_ID_PATTERN.match(path_id):
                issues.append(
                    CensusIssue(
                        code="INVALID_STABLE_ID",
                        path_id=path_id,
                        message=f"Path ID {path_id!r} does not match stableId pattern",
                        severity="failing",
                        observed={"path_id": path_id},
                    )
                )

            if path_id in all_path_ids:
                issues.append(
                    CensusIssue(
                        code="DUPLICATE_PATH_ID",
                        path_id=path_id,
                        message=f"Duplicate path_id {path_id!r} across census",
                        severity="halt",
                        observed={"path_id": path_id},
                    )
                )
            all_path_ids.add(path_id)

            # Check authority_ref
            auth_ref = p.get("authority_ref", "")
            if not STABLE_ID_PATTERN.match(auth_ref):
                issues.append(
                    CensusIssue(
                        code="INVALID_STABLE_ID",
                        path_id=path_id,
                        message=f"Authority ref {auth_ref!r} does not match stableId pattern",
                        severity="failing",
                        observed={"authority_ref": auth_ref},
                    )
                )

            # Check callers
            callers = p.get("callers", [])
            for c in callers:
                c_id = c.get("caller_id", "")
                if not STABLE_ID_PATTERN.match(c_id):
                    issues.append(
                        CensusIssue(
                            code="INVALID_STABLE_ID",
                            path_id=path_id,
                            message=f"Caller ID {c_id!r} does not match stableId pattern",
                            severity="failing",
                            observed={"caller_id": c_id},
                        )
                    )

            target_role = p.get("target_role")
            current_role = p.get("current_role")

            if target_role == "authoritative":
                authoritative_targets.append(p)
            if current_role == "authoritative":
                authoritative_current.append(p)

            # Predecessor negative probe & retirement check
            supersedes = p.get("supersedes", [])
            if supersedes:
                # Successor replacing older paths must have negative probes for predecessors
                neg_probe = p.get("negative_probe_ref")
                if not neg_probe:
                    issues.append(
                        CensusIssue(
                            code=RejectCode.PREDECESSOR_NEGATIVE_PROOF_MISSING.value,
                            path_id=path_id,
                            message=(
                                f"Path {path_id} supersedes {supersedes} but lacks a "
                                "negative_probe_ref proving predecessor retirement"
                            ),
                            severity="failing",
                            expected={"negative_probe_ref": "present"},
                            observed={"negative_probe_ref": None},
                        )
                    )

            # If path itself is retiring or dead, must have retirement disposition
            if target_role in {"retiring", "dead", "legacy"}:
                disp = p.get("target_disposition")
                if disp not in {"retired", "removed"}:
                    issues.append(
                        CensusIssue(
                            code="RETIRED_PATH_DISPOSITION_INVALID",
                            path_id=path_id,
                            message=f"Path {path_id} in {target_role} role requires retired/removed disposition",
                            severity="failing",
                            observed={"target_disposition": disp},
                        )
                    )

        # Coexistence policy rule: Multiple authoritative paths in same outcome class
        # require explicit compatibility window
        if len(authoritative_targets) > 1:
            for p in authoritative_targets:
                compat = p.get("compatibility_window")
                if not compat:
                    issues.append(
                        CensusIssue(
                            code=RejectCode.PROOF_PATH_UNCENSUSED.value,
                            path_id=p.get("path_id"),
                            message=(
                                f"Multiple authoritative target paths exist for outcome {outcome_id} "
                                f"without compatibility_window policy on path {p.get('path_id')}"
                            ),
                            severity="failing",
                            expected={"compatibility_window": "configured"},
                            observed={"compatibility_window": None},
                        )
                    )

        if len(authoritative_current) > 1 and len(authoritative_targets) > 1:
            # Check if predecessor negative proof is missing across the coexistence set
            has_negative_proof = any(p.get("negative_probe_ref") for p in paths)
            if not has_negative_proof:
                issues.append(
                    CensusIssue(
                        code=RejectCode.PREDECESSOR_NEGATIVE_PROOF_MISSING.value,
                        path_id=None,
                        message=(
                            f"Equivalent authoritative paths in outcome {outcome_id} "
                            "lack predecessor negative proof / retirement probe"
                        ),
                        severity="failing",
                        expected={"negative_probe_ref": "present"},
                        observed={"negative_probe_ref": None},
                    )
                )

    return issues


def discover_effect_paths(
    bindings_or_tmrs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Discover outcome classes and callable effect paths from TMR records or bindings."""
    by_outcome: dict[str, list[dict[str, Any]]] = {}

    for item in bindings_or_tmrs:
        binding = item.get("target_binding") if "target_binding" in item else item
        if not binding or not isinstance(binding, dict):
            continue

        outcome_id = binding.get("outcome_id")
        path_id = binding.get("path_id")
        if not outcome_id or not path_id:
            continue

        caller_id = binding.get("caller_id", f"CALLER-{path_id}")
        caller_kind = binding.get("caller_kind", "product")
        authority_role = binding.get("authority_role", "authoritative")
        authority_ref = binding.get("authority_ref", f"AUTH-{path_id}")
        entrypoint = binding.get("entrypoint", f"/{path_id.lower()}")

        predicates = {
            "source": {"state": "observed", "evidence_ref": f"ref:{path_id}:source"},
            "integration": {"state": "observed", "evidence_ref": f"ref:{path_id}:integration"},
            "artifact": {"state": "observed", "evidence_ref": f"ref:{path_id}:artifact"},
            "activation": {"state": "observed", "evidence_ref": f"ref:{path_id}:activation"},
            "running": {"state": "observed", "evidence_ref": f"ref:{path_id}:running"},
            "live_acceptance": {"state": "observed", "evidence_ref": f"ref:{path_id}:live"},
            "retirement": {"state": "not_applicable", "reason": "active path"},
        }

        path_entry: dict[str, Any] = {
            "path_id": path_id,
            "operation": f"op_{path_id.lower()}",
            "component": "pipeline_component",
            "concrete_entrypoint": entrypoint,
            "callers": [
                {
                    "caller_id": caller_id,
                    "kind": caller_kind,
                    "evidence_ref": f"evidence:{caller_id}",
                }
            ],
            "current_role": authority_role,
            "target_role": authority_role,
            "authority_ref": authority_ref,
            "gate_manifest": ["GATE-CONVERGENCE", "GATE-FRESHNESS"],
            "contract_owner_version": "1.0",
            "deployment_slot": "SLOT-PRIMARY",
            "supersedes": binding.get("predecessor_path_ids", []),
            "compatibility_window": None,
            "target_disposition": "retained",
            "negative_probe_ref": binding.get("negative_oracle_ref"),
            "claim_predicates": predicates,
        }

        by_outcome.setdefault(outcome_id, []).append(path_entry)

    outcome_classes: list[dict[str, Any]] = []
    for outcome_id, paths in sorted(by_outcome.items()):
        outcome_classes.append({
            "outcome_id": outcome_id,
            "description": f"Outcome class for {outcome_id}",
            "paths": paths,
        })

    return outcome_classes
