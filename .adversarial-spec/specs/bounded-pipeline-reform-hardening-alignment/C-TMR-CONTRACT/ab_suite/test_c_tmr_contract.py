"""A/B suite for leaf C-TMR-CONTRACT (v6 bounded pipeline).

Runs unmodified against any target tree (E.4):
  AB_TARGET_ROOT=<repo or worktree root>   default: current working directory
  AB_CONTROL=good|bad                       oracle controls (A.5); unset = target X

One primary test per obligation (|T| = |O| = 6). Every assertion names the
obligation it falsifies so a red run has a stable fingerprint.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SUITE_DIR = Path(__file__).resolve().parent
CONTROL = os.environ.get("AB_CONTROL")
_INITIAL_TARGET_ROOT = Path(os.environ.get("AB_TARGET_ROOT") or os.getcwd()).resolve()


def _target_root() -> Path:
    # Read at call time: the good control re-points the root at import.
    return Path(os.environ.get("AB_TARGET_ROOT") or os.getcwd()).resolve()


def _keystone() -> Path:
    return Path(os.environ.get("TMR_KEYSTONE_PATH") or (_target_root().parent / "Brainquarters" / "shared-context" / "test-maturity-record-schema.md"))


def _leaf_dir() -> Path:
    return Path(os.environ["AB_LEAF_DIR"]) if os.environ.get("AB_LEAF_DIR") else SUITE_DIR.parent


def _load_contract():
    if CONTROL == "good":
        sys.path.insert(0, str(SUITE_DIR / "ab_controls"))
        import good_contract as c  # noqa: WPS433
        return c
    if CONTROL == "bad":
        sys.path.insert(0, str(SUITE_DIR / "ab_controls"))
        import bad_contract  # noqa: WPS433
        return bad_contract.MODULE
    scripts = _INITIAL_TARGET_ROOT / "skills" / "adversarial-spec" / "scripts"
    sys.path.insert(0, str(scripts))
    import tmr_schema as c  # noqa: WPS433
    return c


C = _load_contract()

BINDING_CORE = {
    "binding_version": 1,
    "outcome_id": "OUT-FLATTEN-HELD-POSITION",
    "caller_id": "CALLER-PORTFOLIO-FLATTEN-UI",
    "caller_kind": "product",
    "path_id": "PATH-FLATTEN-V3",
    "entrypoint": "POST /flatten/confirm",
    "authority_ref": "AUTH-FLATTEN-V3",
    "authority_role": "authoritative",
}
CONTRACT_REF = {"owner": "gateway", "name": "flatten-envelope", "version": "3", "source_ref": "gateway/schema/flatten.json", "sha256": "sha256:" + "a" * 64}
BINDING_FULL = {
    **BINDING_CORE,
    "caller_equivalence_ref": None,
    "producer_contract": CONTRACT_REF,
    "consumer_contract": {**CONTRACT_REF, "owner": "frontend", "name": "flatten-parser", "sha256": "sha256:" + "b" * 64},
    "runtime_chain_required": True,
    "runtime_slots": ["SLOT-GATEWAY"],
    "terminal_oracle": {"accepted_states": ["completed", "partial"], "reconciliation_authority": "ledger"},
    "negative_oracle_ref": "TC-11.0-neg",
    "equivalence_group": "EQ-FLATTEN",
    "predecessor_path_ids": ["PATH-EXIT-V2"],
    "fixture_provenance": [],
}
RECEIPT = {
    "tier": "code", "command": "uv run pytest tests/test_gateway.py -q", "cwd": "/repo", "repo": "owner-repo", "commit": "abcdef1",
    "started_at": "2026-09-15T00:00:00Z", "finished_at": "2026-09-15T00:00:02Z", "exit": 0, "result": "pass", "env": "live",
    "artifact_uri": "artifacts/gateway.json", "artifact_sha256": "a" * 64, "runner": "skill-runner", "live_or_induced": {"kind": "natural-wait"},
}
OBSERVATION = {
    "runtime_receipt_id": "RUN-GATEWAY-0001", "pid": 4242, "pid_start_time": "2026-09-15T00:00:00Z",
    "outcome_id": "OUT-FLATTEN-HELD-POSITION", "caller_id": "CALLER-PORTFOLIO-FLATTEN-UI", "path_id": "PATH-FLATTEN-V3",
    "entrypoint_observed": "POST /flatten/confirm", "authority_ref_observed": "AUTH-FLATTEN-V3",
    "producer_contract_hash": "sha256:" + "a" * 64, "consumer_contract_hash": "sha256:" + "b" * 64, "terminal_state": "completed",
}


def record(maturity="acceptance", **over):
    payload = {
        "tmr_uid": "01J0CONTRACTLEAF0000000001", "test_id": "TC-1.0", "title": "bound spine", "user_story": "US-1",
        "maturity": maturity, "data_strategy": "REAL-DATA", "spine": True, "verification_mode": "automated-contract",
        "verification_scope": "targeted", "altitude": "system", "tested_by": "llm", "critical_seam": True,
        "criticality_source": "explicit", "binding_status": "bound", "status": "active", "source_spec": "tests-pseudo.md",
        "live_or_induced": {"kind": "natural-wait"}, "run_evidence": RECEIPT if maturity == "concrete" else None,
    }
    payload.update(over)
    return payload


def _validate(payload):
    return C.validate_tmr_record(copy.deepcopy(payload))


def _dump(rec):
    return C.dump_tmr_record(rec)


def test_o1_target_binding_round_trip():
    rec = _validate(record(target_binding=BINDING_FULL))
    dumped = _dump(rec)
    assert dumped["target_binding"]["binding_version"] == 1, "O-1: binding_version const"
    assert _dump(_validate(dumped)) == dumped, "O-1: validate→dump→reload must be byte-equal"
    with pytest.raises(C.SchemaValidationError):
        _validate(record(target_binding={**BINDING_FULL, "unexpected": 1}))
    with pytest.raises(C.SchemaValidationError):
        _validate(record(target_binding={**BINDING_FULL, "outcome_id": "bad id"}))


def test_o2_progressive_population_and_legacy_unbound():
    nl = _validate(record(maturity="nl", target_binding=BINDING_CORE))
    d = _dump(nl)["target_binding"]
    assert d["predecessor_path_ids"] == [] and d["fixture_provenance"] == [] and d["runtime_slots"] == [], "O-2: list fields default to []"
    with pytest.raises(C.SchemaValidationError) as exc:
        _validate(record(maturity="concrete", target_binding=BINDING_CORE))
    assert "terminal_oracle" in str(exc.value) or "producer_contract" in str(exc.value), "O-2: concrete names the missing field"
    _validate(record(maturity="concrete", target_binding=BINDING_FULL))
    legacy = _dump(_validate(record()))
    assert legacy["target_binding"] is None and legacy["target_binding_status"] == "legacy-unbound", "O-2: legacy record visibly unbound"


def test_o3_hash_projection_expected_in_observed_out():
    assert "target_binding" in C.OBLIGATION_IDENTITY_FIELDS, "O-3: target_binding joins the projection"
    base = C.compute_tmr_record_hash(_validate(record(maturity="concrete", target_binding=BINDING_FULL)))
    for field, value in [("path_id", "PATH-EXIT-V2"), ("caller_kind", "harness"), ("authority_role", "legacy"),
                         ("predecessor_path_ids", []), ("runtime_chain_required", False)]:
        mutated = C.compute_tmr_record_hash(_validate(record(maturity="concrete", target_binding={**BINDING_FULL, field: value})))
        assert mutated != base, f"O-3: expected field {field} must change the hash"
    observed = C.compute_tmr_record_hash(_validate(record(maturity="concrete", target_binding=BINDING_FULL,
                                                          run_evidence={**RECEIPT, "target_observation": OBSERVATION, "artifact_uri": "artifacts/other.json"})))
    assert observed == base, "O-3: observation/evidence changes must not change the hash"


def test_o4_code_run_evidence_target_observation():
    rec = _validate(record(maturity="concrete", target_binding=BINDING_FULL, run_evidence={**RECEIPT, "target_observation": OBSERVATION}))
    obs = _dump(rec)["run_evidence"]["target_observation"]
    assert obs["runtime_receipt_id"] == "RUN-GATEWAY-0001" and obs["pid"] == 4242, "O-4: observation round-trips"
    with pytest.raises(C.SchemaValidationError):
        _validate(record(maturity="concrete", target_binding=BINDING_FULL, run_evidence={**RECEIPT, "target_observation": {**OBSERVATION, "pid": "4242"}}))
    with pytest.raises(C.SchemaValidationError):
        _validate(record(maturity="concrete", target_binding=BINDING_FULL, run_evidence={**RECEIPT, "target_observation": {**OBSERVATION, "owner_note": "x"}}))
    plain = _dump(_validate(record(maturity="concrete", run_evidence=RECEIPT)))
    assert plain["run_evidence"]["target_observation"] is None, "O-4: observation optional, defaults null"


def test_o5_keystone_first_packaging():
    assert C.KEYSTONE_SCHEMA_SHA256 == C.schema_sha256(), "O-5: constant re-pinned to the new schema"
    published = json.loads((_target_root() / "skills/adversarial-spec/reference/test-maturity-record.schema.json").read_text())
    assert published == C.tmr_json_schema(include_generated_comment=True), "O-5: machine schema regenerated"
    patch = _leaf_dir() / "keystone-patch.diff"
    assert patch.is_file() and _keystone().is_file(), "O-5: keystone-patch.diff shipped beside the leaf"
    with tempfile.TemporaryDirectory() as td:
        ks = Path(td) / "shared-context" / "test-maturity-record-schema.md"
        ks.parent.mkdir(parents=True)
        ks.write_text(_keystone().read_text(encoding="utf-8"), encoding="utf-8")
        run = subprocess.run(["git", "apply", "--unsafe-paths", "--directory", td, str(patch)], capture_output=True, text=True)
        assert run.returncode == 0, f"O-5: patch must apply cleanly to the canonical keystone: {run.stderr}"
        text = ks.read_text(encoding="utf-8")
    assert C.schema_snapshot_hash(text) == C.schema_sha256(), "O-5: patched keystone pins the new sha"
    assert "target_binding" in text and "target_observation" in text, "O-5: keystone documents both fields"


def test_o6_contract_ownership_record():
    path = _target_root() / "skills/adversarial-spec/reference/contract-ownership.json"
    assert path.is_file(), "O-6: contract-ownership.json exists"
    rec = json.loads(path.read_text())
    contracts = {c["contract"]: c for c in rec["contracts"]}
    assert contracts["tmr-keystone"]["owner"] == "Brainquarters", "O-6: keystone owner"
    assert contracts["plan-schema"]["owner"] == "fizzy-pipeline-mcp" and contracts["card-metadata"]["owner"] == "fizzy-pipeline-mcp", "O-6: Fizzy owns plan + metadata"
    for c in rec["contracts"]:
        assert c["owner"] in {"Brainquarters", "adversarial-spec", "fizzy-pipeline-mcp"}, "O-6: owner enum"
        assert c["consumers"] and all("scope" in x and "name" in x for x in c["consumers"]), "O-6: every consumer names its validation scope"
    fizzy = [x for x in contracts["tmr-keystone"]["consumers"] if x["name"] == "fizzy-pipeline-mcp"]
    assert fizzy and "plan" in fizzy[0]["scope"].lower(), "O-6: Fizzy's TMR scope is plan/metadata only (OQ-4)"
