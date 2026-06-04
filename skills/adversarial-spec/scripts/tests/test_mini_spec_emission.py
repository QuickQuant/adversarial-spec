"""Tests for the Stage 7 v4 altitude mini-spec emitter + producer self-check.

Stage 7 (depth-triage-overhaul) makes adversarial-spec the EMITTER of the
cross-repo ``fizzy-plan.json`` v3 (altitude) contract. The emission itself is
doc-driven (Phase 7 prose the operator/LLM follows), but the machine-checkable
SHAPE — the per-altitude mini-spec field tiers, the requirement-id convention,
the v3 plan structure, and the producer self-check — lives in
``mini_spec_emission`` so it can be tested without the live MCP.

These tests assert the *static* emitter shape (the AC-5 fallback path): Stage 1
is committed on its own branch but is NOT installed on the running MCP, so the
dynamic ``pipeline_validate_plan`` dry-run is recorded as a blocker and the
emitter's own self-check stands in for it. The self-check mirrors the v4
``_validate_plan`` altitude branch (obligation keys == ALTITUDE_OBLIGATIONS,
dotted-line plan_artifact present, realizes_refs invariants), so a plan that
passes the self-check is shaped to pass the live validator once Stage 1 ships.

Run:
    uv run pytest skills/adversarial-spec/scripts/tests/test_mini_spec_emission.py -q
"""

import hashlib
import re

from mini_spec_emission import (
    ALTITUDE_OBLIGATIONS,
    REQUIREMENT_ID_RE,
    VALIDATION_LEDGER_FILENAME,
    altitude_spec_shape,
    emit_fizzy_plan,
    extract_requirement_ids,
    representative_tree,
    self_check_plan,
)

# ── TC-1: requirement-id convention is machine-extractable ──────────


def test_requirement_id_regex_matches_convention():
    # Convention from 01-IMPLEMENTATION-PLAN.md §Stage7: ^[A-Z]+-R?\d+
    assert REQUIREMENT_ID_RE.pattern == r"^[A-Z]+-R?\d+$"
    for good in ("US-1", "INV-3", "SR-R12", "REQ-007", "CONOPS-99"):
        assert REQUIREMENT_ID_RE.match(good), good
    for bad in ("us-1", "US1", "-1", "US-", "US_1", "1-US"):
        assert not REQUIREMENT_ID_RE.match(bad), bad


def test_tc1_emitted_requirement_ids_match_convention():
    plan = emit_fizzy_plan(representative_tree(), session_id="sess-s7")
    ids = extract_requirement_ids(plan)
    assert ids, "emitter must produce at least one requirement id"
    for rid in ids:
        assert REQUIREMENT_ID_RE.match(rid), f"emitted id {rid!r} violates convention"


def test_extract_requirement_ids_is_pure_extraction():
    # extract_requirement_ids must pull ids from conops/user_story/realizes refs,
    # not from free-text titles (so the convention stays machine-extractable).
    plan = emit_fizzy_plan(representative_tree(), session_id="sess-s7")
    ids = set(extract_requirement_ids(plan))
    # The representative tree's system node owns US-1 and US-2.
    assert {"US-1", "US-2"} <= ids


# ── TC-2: emitted plan is schema 3 and passes the self-check ────────


def test_tc2_emitted_plan_is_schema_3_and_self_checks():
    plan = emit_fizzy_plan(representative_tree(), session_id="sess-s7")
    assert plan["plan_schema_version"] == 3
    assert plan["session_id"] == "sess-s7"
    result = self_check_plan(plan)
    assert result["valid"] is True, result["issues"]


def test_self_check_catches_obligation_drift():
    # A self-check that mirrors the live validator must reject a component that
    # declares a system_verification binding (VV_ABOVE_ALTITUDE).
    tree = representative_tree()
    plan = emit_fizzy_plan(tree, session_id="sess-s7")
    comp = next(t for t in plan["tasks"] if t["altitude"] == "component")
    comp["verification_binding"]["system_verification"] = {
        "plan_artifact": "x.md", "plan_hash": "0", "kind": "verification",
    }
    result = self_check_plan(plan)
    assert result["valid"] is False
    assert "VV_ABOVE_ALTITUDE" in {i["code"] for i in result["issues"]}


def test_self_check_catches_orphan_realization():
    tree = representative_tree()
    plan = emit_fizzy_plan(tree, session_id="sess-s7")
    comp = next(t for t in plan["tasks"] if t["altitude"] == "component")
    comp["realizes_refs"] = ["US-99"]  # no ancestor owns US-99
    result = self_check_plan(plan)
    assert result["valid"] is False
    assert "ORPHAN_REALIZATION" in {i["code"] for i in result["issues"]}


# ── TC-3: subsystem + component mini-spec shapes for a tree ─────────


def test_tc3_subsystem_and_component_shapes_present():
    tree = representative_tree()
    plan = emit_fizzy_plan(tree, session_id="sess-s7")
    altitudes = {t["altitude"] for t in plan["tasks"]}
    assert {"system", "subsystem", "component"} <= altitudes


def test_mini_spec_shape_is_strict_superset_chain():
    comp = set(altitude_spec_shape("component")["required_fields"])
    sub = set(altitude_spec_shape("subsystem")["required_fields"])
    sys = set(altitude_spec_shape("system")["required_fields"])
    # component subset subsystem subset system (lighter but never empty).
    assert comp, "component shape must not be empty (C5 floor)"
    assert comp < sub < sys


def test_altitude_obligations_match_validator_contract():
    # Must mirror fizzy-pipeline-mcp ALTITUDE_OBLIGATIONS exactly (C1).
    assert ALTITUDE_OBLIGATIONS["component"] == frozenset({"component_verification"})
    assert ALTITUDE_OBLIGATIONS["subsystem"] == frozenset(
        {"component_verification", "subsystem_verification"}
    )
    assert ALTITUDE_OBLIGATIONS["system"] == frozenset(
        {"component_verification", "subsystem_verification", "system_verification"}
    )


# ── TC-4: dotted-line verification plan artifacts emitted ──────────


def test_tc4_dotted_line_plan_artifacts_emitted():
    plan = emit_fizzy_plan(representative_tree(), session_id="sess-s7")
    for task in plan["tasks"]:
        for kind, binding in task["verification_binding"].items():
            assert binding.get("plan_artifact"), f"{task['task_id']}/{kind} missing plan_artifact"
            assert binding.get("plan_hash"), f"{task['task_id']}/{kind} missing plan_hash"
            assert binding.get("kind") == "verification"
            # plan_hash is a 12-char sha256 prefix (same primitive the gate uses).
            assert re.fullmatch(r"[0-9a-f]{12}", binding["plan_hash"]), binding["plan_hash"]


def test_tc4_hashes_match_written_artifacts(tmp_path):
    plan = emit_fizzy_plan(
        representative_tree(),
        session_id="sess-s7",
        with_artifact_manifest=True,
        artifact_root=tmp_path,
    )

    for task in plan["tasks"]:
        definition_path = tmp_path / task["spec_refs"]["definition_artifact"]
        assert definition_path.is_file()
        assert task["spec_refs"]["definition_hash"] == hashlib.sha256(
            definition_path.read_bytes()
        ).hexdigest()[:12]

        for binding in task["verification_binding"].values():
            plan_path = tmp_path / binding["plan_artifact"]
            assert plan_path.is_file()
            assert binding["plan_hash"] == hashlib.sha256(
                plan_path.read_bytes()
            ).hexdigest()[:12]


def test_obligation_keys_exactly_match_altitude():
    plan = emit_fizzy_plan(representative_tree(), session_id="sess-s7")
    for task in plan["tasks"]:
        keys = set(task["verification_binding"])
        assert keys == set(ALTITUDE_OBLIGATIONS[task["altitude"]]), (
            f"{task['task_id']} binding keys {keys} != obligations for {task['altitude']}"
        )


# ── TC-5: no validation-ledger.json emitted (v4 verification-only) ──


def test_tc5_no_validation_ledger_emitted():
    plan = emit_fizzy_plan(representative_tree(), session_id="sess-s7")
    # No node carries a system_validation binding / validation ledger ref.
    for task in plan["tasks"]:
        assert "system_validation" not in task["verification_binding"]
        assert "validation_ledger_ref" not in task
    assert "validation_ledger_ref" not in plan
    # The emitter must declare the file it deliberately does NOT write.
    assert VALIDATION_LEDGER_FILENAME == "validation-ledger.json"
    artifacts = emit_fizzy_plan(
        representative_tree(), session_id="sess-s7", with_artifact_manifest=True
    )["_artifact_manifest"]
    assert VALIDATION_LEDGER_FILENAME not in artifacts


def test_artifact_manifest_includes_per_altitude_specs_and_conops():
    manifest = emit_fizzy_plan(
        representative_tree(), session_id="sess-s7", with_artifact_manifest=True
    )["_artifact_manifest"]
    joined = "\n".join(manifest)
    # per-altitude spec docs + dotted-line verification plan/procedure artifacts
    assert any("normative" in m or "system-spec" in m for m in manifest)
    assert any("subsystem" in m for m in manifest)
    assert any("component" in m for m in manifest)
    assert any("verification-plan" in m or "verification-procedure" in m for m in manifest)
    # Appx S ConOps outline emitted as a future-validation input.
    assert "conops" in joined.lower()


# ── requirement metadata (Table 4.2-2) + Appx C lint ───────────────


def test_requirement_metadata_table_4_2_2_fields():
    from mini_spec_emission import REQUIREMENT_METADATA_FIELDS

    # Table 4.2-2: Requirement ID, Rationale, Traced-from, Owner,
    # Verification method, Verification level.
    for field in ("requirement_id", "rationale", "traced_from", "owner",
                  "verification_method", "verification_level"):
        assert field in REQUIREMENT_METADATA_FIELDS


def test_appx_c_good_requirement_lint():
    from mini_spec_emission import lint_requirement_text

    # WHAT-not-HOW + shall/will/should discipline (Appx C.1/C.4).
    ok = lint_requirement_text("The system shall reject a malformed token with code 401.")
    assert ok["ok"] is True, ok

    # No normative keyword -> flagged.
    bad_kw = lint_requirement_text("The system rejects malformed tokens.")
    assert bad_kw["ok"] is False
    assert "missing_normative_keyword" in bad_kw["violations"]

    # Implementation detail (HOW) -> flagged WHAT-not-HOW.
    bad_how = lint_requirement_text(
        "The system shall use a regex in pipeline.py to parse the header."
    )
    assert bad_how["ok"] is False
    assert "describes_how_not_what" in bad_how["violations"]


def test_lint_rejects_empty_and_unverifiable():
    from mini_spec_emission import lint_requirement_text

    assert lint_requirement_text("")["ok"] is False
    # "should" is permitted (a goal), but the linter still records its tier.
    soft = lint_requirement_text("The UI should feel responsive.")
    assert soft["tier"] == "should"


# ── representative tree is internally consistent ───────────────────


def test_representative_tree_round_trips_through_self_check():
    plan = emit_fizzy_plan(representative_tree(), session_id="sess-rt")
    assert self_check_plan(plan)["valid"] is True


def test_emit_is_deterministic():
    a = emit_fizzy_plan(representative_tree(), session_id="sess-det")
    b = emit_fizzy_plan(representative_tree(), session_id="sess-det")
    import json
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
