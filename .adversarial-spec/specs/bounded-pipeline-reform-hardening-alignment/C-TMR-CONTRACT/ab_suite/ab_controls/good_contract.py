"""Known-good control (A.5): a minimal self-contained implementation of the six
C-TMR-CONTRACT surfaces. It is NOT the product; it validates the oracle: the suite
must PASS 6/6 here. It builds its own tiny keystone + machine schema in a temp
dir so O-5/O-6 can be exercised without touching the repo.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Literal

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

STABLE = r"^[A-Z][A-Z0-9_-]{2,127}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ContractRef(Strict):
    owner: str
    name: str
    version: str
    source_ref: str
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class TerminalOracle(Strict):
    accepted_states: list[str]
    reconciliation_authority: str


class FixtureProvenance(Strict):
    boundary: str
    kind: Literal["none", "real-source", "recorded", "constructed", "stub", "mock"]
    source: str
    claim_ceiling: str


class TargetProofBinding(Strict):
    binding_version: Literal[1]
    outcome_id: str = Field(pattern=STABLE)
    caller_id: str = Field(pattern=STABLE)
    caller_kind: Literal["product", "operator", "system", "harness"]
    path_id: str = Field(pattern=STABLE)
    entrypoint: str
    authority_ref: str = Field(pattern=STABLE)
    authority_role: Literal["authoritative", "projection", "legacy", "emergency", "retiring", "dead"]
    caller_equivalence_ref: str | None = None
    producer_contract: ContractRef | None = None
    consumer_contract: ContractRef | None = None
    runtime_chain_required: bool | None = None
    runtime_slots: list[str] = Field(default_factory=list)
    terminal_oracle: TerminalOracle | None = None
    negative_oracle_ref: str | None = None
    equivalence_group: str | None = None
    predecessor_path_ids: list[str] = Field(default_factory=list)
    fixture_provenance: list[FixtureProvenance] = Field(default_factory=list)


CONCRETE_REQUIRED = ("producer_contract", "consumer_contract", "runtime_chain_required", "terminal_oracle", "negative_oracle_ref", "equivalence_group")


class TargetObservation(Strict):
    runtime_receipt_id: str
    pid: int
    pid_start_time: str
    outcome_id: str
    caller_id: str
    path_id: str
    entrypoint_observed: str
    authority_ref_observed: str
    producer_contract_hash: str
    consumer_contract_hash: str
    terminal_state: str


class LiveOrInduced(Strict):
    kind: str
    detail: str | None = None


class CodeRunEvidence(Strict):
    tier: Literal["code"]
    command: str
    cwd: str
    repo: str
    commit: str
    started_at: str
    finished_at: str
    exit: int
    result: Literal["pass", "fail"]
    env: Literal["live", "dev", "ci"]
    artifact_uri: str
    artifact_sha256: str
    runner: str
    live_or_induced: LiveOrInduced | None
    target_observation: TargetObservation | None = None


class TestMaturityRecord(Strict):
    tmr_uid: str
    test_id: str
    title: str
    user_story: str | list[str]
    maturity: Literal["nl", "acceptance", "concrete"]
    data_strategy: str
    spine: bool
    verification_mode: str
    verification_scope: str
    altitude: str
    tested_by: str
    critical_seam: bool | None
    criticality_source: str
    binding_status: str
    status: str
    source_spec: str
    live_or_induced: LiveOrInduced | None
    run_evidence: CodeRunEvidence | None
    target_binding: TargetProofBinding | None = None
    # Derived, but accepted on input so a dump re-validates; a stored value that
    # disagrees with the binding is a schema error, never a newer truth.
    target_binding_status: Literal["bound", "legacy-unbound"] | None = None

    @model_validator(mode="after")
    def _ladder(self):
        if self.maturity == "concrete" and self.target_binding is not None:
            for f in CONCRETE_REQUIRED:
                if getattr(self.target_binding, f) is None:
                    raise ValueError(f"target_binding.{f} is required at maturity concrete")
        derived = "bound" if self.target_binding is not None else "legacy-unbound"
        if self.target_binding_status not in (None, derived):
            raise ValueError(f"target_binding_status {self.target_binding_status!r} disagrees with the binding ({derived})")
        object.__setattr__(self, "target_binding_status", derived)
        return self


class SchemaValidationError(ValueError):
    def __init__(self, field: str, detail: str):
        self.code, self.field, self.detail = "schema_error", field, detail
        super().__init__(f"schema_error: {field}: {detail}")


def validate_tmr_record(payload: dict[str, Any]) -> TestMaturityRecord:
    try:
        return TestMaturityRecord.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise SchemaValidationError(".".join(str(x) for x in first.get("loc", ())) or "record", str(first.get("msg"))) from None


def dump_tmr_record(rec: TestMaturityRecord) -> dict[str, Any]:
    return rec.model_dump(mode="json", exclude_none=False)


OBLIGATION_IDENTITY_FIELDS = frozenset({"tmr_uid", "test_id", "user_story", "critical_seam", "criticality_source", "target_binding"})


def compute_tmr_record_hash(rec: TestMaturityRecord) -> str:
    proj = {f: (rec.target_binding.model_dump(mode="json") if f == "target_binding" and rec.target_binding else getattr(rec, f)) for f in sorted(OBLIGATION_IDENTITY_FIELDS)}
    return "sha256:" + hashlib.sha256(rfc8785.dumps(proj)).hexdigest()


def tmr_json_schema(*, include_generated_comment: bool = False) -> dict[str, Any]:
    s = TestMaturityRecord.model_json_schema(mode="validation")
    if include_generated_comment:
        s["$comment"] = f"generated-from:{schema_sha256()}"
    return s


def schema_sha256() -> str:
    return "sha256:" + hashlib.sha256(json.dumps(tmr_json_schema(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


KEYSTONE_SCHEMA_SHA256 = schema_sha256()
_RE = re.compile(r"schema_sha256:\s*(sha256:[0-9a-f]{64})")


def schema_snapshot_hash(text: str) -> str | None:
    m = _RE.search(text)
    return m.group(1) if m else None


# --- self-contained target root so O-5/O-6 file checks can pass under the control ---
_root = Path(tempfile.mkdtemp(prefix="ab-good-"))
(_root / "skills/adversarial-spec/reference").mkdir(parents=True)
(_root / "skills/adversarial-spec/reference/test-maturity-record.schema.json").write_text(json.dumps(tmr_json_schema(include_generated_comment=True), indent=2, sort_keys=True))
(_root / "skills/adversarial-spec/reference/contract-ownership.json").write_text(json.dumps({"contracts": [
    {"contract": "tmr-keystone", "owner": "Brainquarters", "consumers": [{"name": "adversarial-spec", "scope": "mirror + regenerate + sha tripwire"}, {"name": "fizzy-pipeline-mcp", "scope": "plan/metadata contracts only; no TMR execution logic"}]},
    {"contract": "plan-schema", "owner": "fizzy-pipeline-mcp", "consumers": [{"name": "adversarial-spec", "scope": "emit + self-check with mirrored codes"}]},
    {"contract": "card-metadata", "owner": "fizzy-pipeline-mcp", "consumers": [{"name": "adversarial-spec", "scope": "read created_at + pipeline_version for the fence"}]},
]}))
_ks = _root.parent / "Brainquarters" / "shared-context"
_ks.mkdir(parents=True, exist_ok=True)
(_ks / "test-maturity-record-schema.md").write_text("# keystone (control)\n> schema_sha256: sha256:" + "0" * 64 + "\n")
_leaf = _root / "leaf"
_leaf.mkdir(parents=True, exist_ok=True)
os.environ["AB_LEAF_DIR"] = str(_leaf)
_patch = (
    "--- a/shared-context/test-maturity-record-schema.md\n+++ b/shared-context/test-maturity-record-schema.md\n@@ -1,2 +1,3 @@\n # keystone (control)\n"
    f"-> schema_sha256: sha256:{'0' * 64}\n+> schema_sha256: {KEYSTONE_SCHEMA_SHA256}\n+> fields: target_binding, target_observation\n"
)
(_leaf / "keystone-patch.diff").write_text(_patch)
os.environ["TMR_KEYSTONE_PATH"] = str(_ks / "test-maturity-record-schema.md")
os.environ["AB_TARGET_ROOT"] = str(_root)
