"""depth-triage Stage 7 — v4 altitude mini-spec emission + producer self-check.

(Stage numbers here are depth-triage-overhaul roadmap milestones, NOT pipeline
Phases — this module implements roadmap Stage 7 but runs inside pipeline Phase 7.)

adversarial-spec is the EMITTER of the cross-repo ``fizzy-plan.json`` v3
(altitude) contract; fizzy-pipeline-mcp ENFORCES it; the fizzy backend LINKS it
(see the fizzy-pipeline-mcp repo:
``.adversarial-spec/designs/depth-triage-overhaul/60-cross-repo-contract.md``).

The Phase 7 emission is doc-driven (``phases/07-execution.md``), but the
machine-checkable SHAPE lives here so the producer can self-check WITHOUT the
live MCP. The :func:`self_check_plan` function mirrors the fizzy-pipeline-mcp
v4 ``_validate_plan`` altitude branch (depth-triage Stage 1, SHIPPED — live at
pipeline v5): obligation keys must equal :data:`ALTITUDE_OBLIGATIONS`, every
required binding carries a dotted-line ``plan_artifact`` + ``plan_hash``, and
the two ``realizes_refs`` invariants hold. A plan that passes the self-check is
shaped to pass the live validator — the dry-run/load symmetry that already
exists for v2. The self-check is now a fast offline pre-flight, not a stand-in
for the live dry-run.

v4 is VERIFICATION-ONLY: this emitter never writes a ``validation-ledger.json``,
never emits a ``system_validation`` binding, and adds no force/override/bypass
parameter.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

# ── Plan schema version (must match fizzy-pipeline-mcp V4_PLAN_SCHEMA_VERSION) ──
PLAN_SCHEMA_VERSION = 3

# ── Machine-extractable requirement-id convention ──────────────────
# 01-IMPLEMENTATION-PLAN.md §Stage7: ^[A-Z]+-R?\d+  (e.g. US-1, INV-3, SR-R12).
REQUIREMENT_ID_RE = re.compile(r"^[A-Z]+-R?\d+$")
# Same pattern, unanchored, for scanning ref lists.
_REQUIREMENT_ID_SCAN = re.compile(r"\b[A-Z]+-R?\d+\b")

# ── Altitude obligation table (MUST mirror pipeline.py ALTITUDE_OBLIGATIONS) ──
# C1: the right-arm verification obligation set is a pure function of altitude.
# Lower altitude = strictly fewer obligations, each non-empty (C5 floor).
ALTITUDE_OBLIGATIONS: dict[str, frozenset[str]] = {
    "component": frozenset({"component_verification"}),
    "subsystem": frozenset({"component_verification", "subsystem_verification"}),
    "system": frozenset(
        {"component_verification", "subsystem_verification", "system_verification"}
    ),
}
ALL_VV_KINDS = frozenset().union(*ALTITUDE_OBLIGATIONS.values())
ALTITUDE_RANK: dict[str, int] = {"component": 0, "subsystem": 1, "system": 2}

# v4 verification kind axis — only "verification". system_validation is a future
# migration and is NOT a valid v4 kind.
VV_KIND = "verification"

# The file the emitter deliberately does NOT write in v4 (verification-only).
VALIDATION_LEDGER_FILENAME = "validation-ledger.json"

# ── Requirement metadata field set (NASA Table 4.2-2) ──────────────
REQUIREMENT_METADATA_FIELDS: tuple[str, ...] = (
    "requirement_id",
    "rationale",
    "traced_from",
    "owner",
    "verification_method",
    "verification_level",
)

# ── Per-altitude mini-spec required-field tiers (strict superset chain) ──
# component subset subsystem subset system. Lower altitude = strictly fewer
# mandatory left-arm fields, but each retains its C1 floor obligation.
_FLOOR_FIELDS: tuple[str, ...] = (
    "task_id",
    "altitude",
    "title",
    "description",
    "effort",
    "strategy",
    "acceptance_criteria",
    "architecture_refs",
    "behavior_change",
    "verification_mode",
    "verification_scope",
    "spec_refs",
    "verification_binding",
)
_SUBSYSTEM_EXTRA: tuple[str, ...] = ("subsystem_spec_path", "decomposes_into")
_SYSTEM_EXTRA: tuple[str, ...] = (
    "system_spec_path",
    "conops_refs",
    "user_story_refs",
)


def altitude_spec_shape(altitude: str) -> dict[str, Any]:
    """Return the required-field profile for an altitude (C7 mini-spec shape).

    The tiers form a strict superset chain component ⊂ subsystem ⊂ system.
    """
    if altitude not in ALTITUDE_OBLIGATIONS:
        raise ValueError(f"unknown altitude: {altitude!r}")
    required = list(_FLOOR_FIELDS)
    if altitude in ("subsystem", "system"):
        required += list(_SUBSYSTEM_EXTRA)
    if altitude == "system":
        required += list(_SYSTEM_EXTRA)
    return {
        "altitude": altitude,
        "required_fields": tuple(dict.fromkeys(required)),  # de-dup, keep order
        "obligations": tuple(sorted(ALTITUDE_OBLIGATIONS[altitude])),
    }


def _sha256_prefix_bytes(data: bytes) -> str:
    """12-char sha256 prefix — the SAME primitive fizzy-pipeline-mcp's gate uses."""
    return hashlib.sha256(data).hexdigest()[:12]


def _write_artifact(artifact_root: Path | None, relpath: str, content: str) -> str:
    data = content.encode("utf-8")
    if artifact_root is not None:
        target = artifact_root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        data = target.read_bytes()
    return _sha256_prefix_bytes(data)


# ── Appx C good-requirement lint ───────────────────────────────────
_NORMATIVE_TIERS = {"shall": "shall", "will": "will", "should": "should"}
# Editorial "HOW" markers: implementation files / mechanisms named in the text.
_HOW_MARKERS = re.compile(
    r"\b(?:using|use|via|by calling|regex|loop|class|function|"
    r"\w+\.py|\w+\.rb|\w+\.js)\b",
    re.IGNORECASE,
)


def lint_requirement_text(text: str) -> dict[str, Any]:
    """Appx C.1/C.4 producer-side lint of a single requirement statement.

    Checks term discipline (shall/will/should), WHAT-not-HOW, and non-empty.
    Returns ``{ok, tier, violations}``. Advisory-by-design: the producer fixes
    flagged requirements before emission; nothing here blocks at runtime.
    """
    violations: list[str] = []
    stripped = (text or "").strip()
    if not stripped:
        return {"ok": False, "tier": None, "violations": ["empty"]}

    lowered = stripped.lower()
    tier: str | None = None
    for kw, name in _NORMATIVE_TIERS.items():
        if re.search(rf"\b{kw}\b", lowered):
            tier = name
            break
    if tier is None:
        violations.append("missing_normative_keyword")

    if _HOW_MARKERS.search(stripped):
        violations.append("describes_how_not_what")

    # Appx C.3 verifiability: a requirement must state an observable condition.
    if not re.search(r"[.!?]$", stripped):
        violations.append("not_a_complete_statement")

    return {"ok": not violations, "tier": tier, "violations": violations}


# ── representative altitude tree (used by tests + the doc worked example) ──


def representative_tree() -> dict[str, Any]:
    """A minimal, internally-consistent system→subsystem→component tree.

    Mirrors 60-cross-repo-contract.md §8's worked example shape. The emitter
    turns this into a v3 ``fizzy-plan.json``; the self-check accepts it.
    """
    return {
        "system": {
            "task_id": "SYS",
            "title": "Altitude V-model enforcement",
            "description": "The system shall enforce level-matched V&V across the tree.",
            "effort": "L",
            "conops_refs": ["US-1", "US-2"],
            "user_story_refs": ["US-1", "US-2"],
            "children": [
                {
                    "task_id": "SS-1",
                    "title": "Validate-plan altitude branch",
                    "description": "The subsystem shall validate altitude trees.",
                    "effort": "M",
                    "realizes_refs": ["US-1", "US-2"],
                    "children": [
                        {
                            "task_id": "C-1",
                            "title": "Per-node obligation check",
                            "description": "The component shall reject above-altitude bindings.",
                            "effort": "S",
                            "realizes_refs": ["US-1"],
                        },
                        {
                            "task_id": "C-2",
                            "title": "Realizes-refs invariants",
                            "description": "The component shall reject orphan realizations.",
                            "effort": "S",
                            "realizes_refs": ["US-2"],
                        },
                    ],
                }
            ],
        }
    }


_SPEC_DOC = {
    "system": "system-spec.md",
    "subsystem": "subsystem-spec.md",
    "component": "normative.md",
}
_PLAN_DOC = {
    "component_verification": "component-verification-procedure.md",
    "subsystem_verification": "subsystem-verification-plan.md",
    "system_verification": "system-verification-plan.md",
}


def _binding(slug: str, tid: str, kind: str, artifact_root: Path | None) -> dict[str, Any]:
    plan_artifact = f".adversarial-spec/specs/{slug}/{tid}/{_PLAN_DOC[kind]}"
    plan_content = (
        f"# {tid} {kind.replace('_', ' ').title()}\n\n"
        f"Dotted-line verification plan/procedure for `{tid}`.\n"
        f"Verification kind: `{kind}`.\n"
    )
    return {
        "plan_artifact": plan_artifact,
        "plan_hash": _write_artifact(artifact_root, plan_artifact, plan_content),
        "artifact": f"tests/test_{tid.lower()}.py",
        "kind": VV_KIND,
        "verify_commands": [f"uv run pytest tests/test_{tid.lower()}.py -q"],
    }


def _spec_refs(
    slug: str,
    tid: str,
    altitude: str,
    node: dict[str, Any],
    artifact_root: Path | None,
) -> dict[str, Any]:
    definition_artifact = f".adversarial-spec/specs/{slug}/{tid}/{_SPEC_DOC[altitude]}"
    definition_content = (
        f"# {tid} {altitude.title()} Mini-Spec\n\n"
        f"Title: {node['title']}\n\n"
        f"{node['description']}\n"
    )
    return {
        "definition_artifact": definition_artifact,
        "definition_hash": _write_artifact(artifact_root, definition_artifact, definition_content),
    }


def _emit_node(
    node: dict[str, Any],
    altitude: str,
    parent: str | None,
    slug: str,
    *,
    out: list[dict[str, Any]],
    artifacts: list[str],
    artifact_root: Path | None,
) -> None:
    tid = node["task_id"]
    children = node.get("children", [])
    obligations = sorted(ALTITUDE_OBLIGATIONS[altitude])

    binding = {kind: _binding(slug, tid, kind, artifact_root) for kind in obligations}
    spec_refs = _spec_refs(slug, tid, altitude, node, artifact_root)

    task: dict[str, Any] = {
        "task_id": tid,
        "altitude": altitude,
        "parent": parent,
        "decomposes_into": [c["task_id"] for c in children],
        "title": node["title"],
        "description": node["description"],
        "effort": node.get("effort", "M"),
        "strategy": node.get("strategy", "test-first"),
        "depends_on": node.get("depends_on", []),
        "acceptance_criteria": node.get(
            "acceptance_criteria", [node["description"]]
        ),
        "architecture_refs": node.get("architecture_refs", [".architecture/INDEX.md"]),
        "behavior_change": node.get("behavior_change", True),
        "verification_mode": node.get(
            "verification_mode",
            "automated-unit" if altitude == "component" else "automated-integration",
        ),
        "verification_scope": node.get(
            "verification_scope", "targeted" if altitude == "component" else "full-suite"
        ),
        "implementation_status": node.get("implementation_status", "greenfield"),
        "spec_refs": spec_refs,
        "verification_binding": binding,
        # NASA Table 4.2-2 requirement metadata (per-node record).
        "requirement_metadata": {
            "requirement_id": _node_requirement_id(tid),
            "rationale": node.get("rationale", "derived from parent decomposition"),
            "traced_from": parent,
            "owner": node.get("owner", "spec-producer"),
            "verification_method": "test",
            "verification_level": altitude,
        },
    }
    if altitude == "system":
        task["system_spec_path"] = spec_refs["definition_artifact"]
        task["conops_refs"] = node.get("conops_refs", [])
        task["user_story_refs"] = node.get("user_story_refs", [])
    if altitude == "subsystem":
        task["subsystem_spec_path"] = spec_refs["definition_artifact"]
    if parent is not None:
        task["realizes_refs"] = node.get("realizes_refs", [])

    out.append(task)
    artifacts.append(spec_refs["definition_artifact"])
    for kind in obligations:
        artifacts.append(binding[kind]["plan_artifact"])

    child_altitude = _child_altitude(altitude)
    for child in children:
        _emit_node(
            child, child_altitude, tid, slug,
            out=out, artifacts=artifacts, artifact_root=artifact_root,
        )


def _node_requirement_id(tid: str) -> str:
    """Derive a convention-compliant requirement id from a task id."""
    m = re.match(r"^([A-Za-z]+)\D*(\d+)?", tid)
    prefix = (m.group(1).upper() if m else "REQ")
    num = (m.group(2) if (m and m.group(2)) else "1")
    return f"{prefix}-{num}"


def _child_altitude(parent_altitude: str) -> str:
    if parent_altitude == "system":
        return "subsystem"
    return "component"


def emit_fizzy_plan(
    tree: dict[str, Any],
    *,
    session_id: str,
    slug: str = "altitude-demo",
    with_artifact_manifest: bool = False,
    artifact_root: str | Path | None = None,
) -> dict[str, Any]:
    """Emit a v3 (altitude) ``fizzy-plan.json`` dict from a tree.

    The root of *tree* is the system node. Every non-root node is given a
    ``parent`` of strictly higher altitude, ``decomposes_into``, ``spec_refs``
    with a re-derivable ``definition_hash``, and a ``verification_binding`` with
    EXACTLY the obligation keys for its altitude (each with a dotted-line
    ``plan_artifact`` + ``plan_hash``). No ``validation-ledger.json`` is emitted.

    When *artifact_root* is supplied, the helper writes the emitted spec and
    dotted-line artifacts to disk before hashing them. When omitted, it hashes
    the same deterministic bytes it would write.

    When *with_artifact_manifest* is True, the returned dict carries an extra
    ``_artifact_manifest`` listing every per-altitude spec doc + dotted-line
    verification plan/procedure artifact + the Appx S ConOps outline the
    producer must write to disk. (The manifest is metadata, not part of the
    contract loaded by ``pipeline_load``.)
    """
    root = tree["system"]
    tasks: list[dict[str, Any]] = []
    artifacts: list[str] = []
    artifact_root_path = Path(artifact_root) if artifact_root is not None else None
    _emit_node(
        root, "system", None, slug, out=tasks, artifacts=artifacts,
        artifact_root=artifact_root_path,
    )

    plan: dict[str, Any] = {
        "plan_schema_version": PLAN_SCHEMA_VERSION,
        "session_id": session_id,
        "tasks": tasks,
    }
    if with_artifact_manifest:
        # Appx S ConOps annotated outline — emitted as a FUTURE-validation input,
        # never a v4 requirement and never a validation ledger.
        conops = f".adversarial-spec/specs/{slug}/conops-outline.md"
        _write_artifact(
            artifact_root_path,
            conops,
            "# Concept of Operations Outline\n\nFuture system-validation input.\n",
        )
        plan["_artifact_manifest"] = [*artifacts, conops]
    return plan


# ── producer self-check (mirrors fizzy-pipeline-mcp v4 _validate_plan) ──


def self_check_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate a v3 plan's altitude shape WITHOUT the live MCP.

    Mirrors the fizzy-pipeline-mcp depth-triage Stage 1 ``_validate_plan``
    altitude branch (shipped — live at pipeline v5) so a plan that self-checks
    clean is shaped to pass ``pipeline_validate_plan``. Returns
    ``{valid, issues}``; ``issues`` entries carry the SAME reject codes the
    live validator emits.
    """
    issues: list[dict[str, Any]] = []
    tasks = plan.get("tasks", [])
    by_id = {t.get("task_id"): t for t in tasks}

    if plan.get("plan_schema_version") != PLAN_SCHEMA_VERSION:
        issues.append({"code": "WRONG_SCHEMA_VERSION", "task_id": "<plan>"})

    roots = [t for t in tasks if not t.get("parent")]
    if not roots:
        issues.append({"code": "NO_ROOT", "task_id": "<plan>"})
    elif len(roots) > 1:
        issues.append({"code": "MULTIPLE_ROOTS", "task_id": "<plan>"})
    elif roots[0].get("altitude") != "system" and len(tasks) > 1:
        issues.append({"code": "ROOT_NOT_SYSTEM", "task_id": roots[0].get("task_id")})

    for task in tasks:
        tid = task.get("task_id")
        altitude = task.get("altitude")
        if altitude not in ALTITUDE_OBLIGATIONS:
            issues.append({"code": "INVALID_ALTITUDE", "task_id": tid})
            continue

        binding = task.get("verification_binding") or {}
        obligated = ALTITUDE_OBLIGATIONS[altitude]
        present = set(binding)
        for missing in sorted(obligated - present):
            issues.append({"code": "MISSING_LEVEL_VV", "task_id": tid, "field": missing})
        for extra in sorted(present - ALL_VV_KINDS):
            issues.append({"code": "UNKNOWN_VV_BINDING", "task_id": tid, "field": extra})
        for above in sorted((present & ALL_VV_KINDS) - obligated):
            issues.append({"code": "VV_ABOVE_ALTITUDE", "task_id": tid, "field": above})

        for kind in sorted(obligated & present):
            spec = binding.get(kind) or {}
            if spec.get("kind") != VV_KIND:
                issues.append({"code": "VV_KIND_MISMATCH", "task_id": tid, "field": kind})
            if not spec.get("plan_artifact"):
                issues.append({"code": "MISSING_VV_PLAN_ARTIFACT", "task_id": tid, "field": kind})
            if not spec.get("plan_hash"):
                issues.append({"code": "MISSING_VV_PLAN_HASH", "task_id": tid, "field": kind})

        # parent / altitude inversion
        parent = task.get("parent")
        if parent is not None:
            pnode = by_id.get(parent)
            if pnode is None:
                issues.append({"code": "MISSING_PARENT", "task_id": tid})
            else:
                pa, ca = pnode.get("altitude"), altitude
                if pa in ALTITUDE_RANK and ca in ALTITUDE_RANK and ALTITUDE_RANK[pa] <= ALTITUDE_RANK[ca]:
                    issues.append({"code": "ALTITUDE_INVERSION", "task_id": tid})

    # realizes_refs invariants
    def _ancestor_stories(t: dict[str, Any]) -> set[str]:
        owned: set[str] = set()
        cur = by_id.get(t.get("parent"))
        seen: set[str] = set()
        while cur is not None and cur.get("task_id") not in seen:
            seen.add(cur.get("task_id"))
            owned |= set(cur.get("conops_refs") or [])
            owned |= set(cur.get("user_story_refs") or [])
            cur = by_id.get(cur.get("parent"))
        return owned

    all_realized: set[str] = set()
    for task in tasks:
        all_realized |= set(task.get("realizes_refs") or [])

    for task in tasks:
        if task.get("parent") is None:
            continue
        realized = set(task.get("realizes_refs") or [])
        orphans = sorted(realized - _ancestor_stories(task))
        if orphans:
            issues.append({"code": "ORPHAN_REALIZATION", "task_id": task.get("task_id"), "detail": orphans})

    for task in tasks:
        if task.get("altitude") != "system":
            continue
        owned = set(task.get("conops_refs") or []) | set(task.get("user_story_refs") or [])
        undecomposed = sorted(owned - all_realized)
        if undecomposed:
            issues.append({"code": "UNDECOMPOSED_REQUIREMENT", "task_id": task.get("task_id"), "detail": undecomposed})

    return {"valid": not issues, "issues": issues}


def extract_requirement_ids(plan: dict[str, Any]) -> list[str]:
    """Pull every convention-compliant requirement id from a plan's ref fields.

    Extraction is from structured ref lists (conops/user_story/realizes refs),
    NOT free-text titles — the convention is what makes ids machine-extractable.
    Stable first-seen order.
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for task in plan.get("tasks", []):
        for field in ("conops_refs", "user_story_refs", "realizes_refs"):
            for ref in task.get(field) or []:
                for rid in _REQUIREMENT_ID_SCAN.findall(str(ref)):
                    if rid not in seen_set:
                        seen_set.add(rid)
                        seen.append(rid)
    return seen
