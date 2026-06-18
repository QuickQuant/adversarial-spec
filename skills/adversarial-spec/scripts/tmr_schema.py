"""TMR keystone schema contract for the liveness-gate work.

This module is intentionally standalone: W0-1 publishes the machine-readable
shape and a strict validator, while later tasks layer registry loading,
duplicate-key detection, and gate orchestration on top.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    model_validator,
)

CONTRACT_VERSION = "tmr.v1"

MATURITY_VALUES = ("nl", "acceptance", "concrete")
DATA_STRATEGIES = (
    "REAL-DATA",
    "REAL-DATA + PROPERTY",
    "SYNTHETIC",
    "MOCK",
    "MOCK-EXTERNAL",
    "FRONTEND",
    "STATIC",
)
LIVENESS_TECHNIQUES = (
    "natural-wait",
    "toxiproxy:corrupt",
    "toxiproxy:drop",
    "tc-netem:latency",
    "tc-netem:partition",
    "external-kill",
    "clock-stub",
    "state-injection",
    "other",
)
VERIFICATION_MODES = (
    "automated-unit",
    "automated-integration",
    "automated-contract",
    "automated-component",
    "test-producer",
    "artifact-sync",
    "static-check",
    "manual-ux",
    "system-validation",
)
CODE_VERIFICATION_MODES = frozenset(
    mode for mode in VERIFICATION_MODES if mode.startswith("automated-")
) | {"test-producer"}
EXEMPT_VERIFICATION_MODES = frozenset(
    {"artifact-sync", "static-check", "manual-ux"}
)
VERIFICATION_SCOPES = ("targeted", "full-suite", "static", "manual", "end-to-end")
ALTITUDES = ("component", "subsystem", "system")
TESTED_BY_VALUES = ("llm", "user", "both")
BINDING_STATUS_VALUES = ("unbound", "bound")
TMR_STATUS_VALUES = ("active", "tombstoned")
CRITICALITY_SOURCES = ("explicit", "architecture_link", "unknown")
RUN_RESULTS = ("pass", "fail")
RUN_ENVS = ("live", "dev", "ci")

REAL_DATA_STRATEGIES = frozenset({"REAL-DATA", "REAL-DATA + PROPERTY"})
DETAIL_REQUIRED_LIVENESS = frozenset({"other", "state-injection"})

SCHEMA_HASH_RE = re.compile(r"schema_sha256:\s*(sha256:[0-9a-f]{64})")
GENERATED_FROM_RE = re.compile(r"generated-from:\s*(sha256:[0-9a-f]{64})")
COPY_MARKERS = (
    "Schema: Test Maturity Record",
    "Test Maturity Record + Guardrail Findings + Provenance Ledger",
)


class StrictSchemaModel(BaseModel):
    """Base for every machine-schema object in this contract."""

    model_config = ConfigDict(extra="forbid", strict=True)


class LiveOrInducedTechnique(StrictSchemaModel):
    """Tagged object form of ``live_or_induced``.

    JSON null is represented by Python ``None`` at the TMR field. A present
    object must have a non-null kind; ``other`` and ``state-injection`` are
    useful only with a concrete detail.
    """

    kind: Literal[
        "natural-wait",
        "toxiproxy:corrupt",
        "toxiproxy:drop",
        "tc-netem:latency",
        "tc-netem:partition",
        "external-kill",
        "clock-stub",
        "state-injection",
        "other",
    ]
    detail: str | None = None

    @model_validator(mode="after")
    def require_detail_for_constructible_escape(self) -> "LiveOrInducedTechnique":
        if self.kind in DETAIL_REQUIRED_LIVENESS and not _non_empty(self.detail):
            raise ValueError(
                f"live_or_induced.detail is required when kind={self.kind!r}"
            )
        return self


class CodeRunEvidence(StrictSchemaModel):
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
    live_or_induced: LiveOrInducedTechnique | None


class SystemValidationRunEvidence(StrictSchemaModel):
    tier: Literal["system-validation"]
    transcript_uri: str
    transcript_sha256: str
    model: str
    model_settings: dict[str, Any]
    prompt_sha256: str
    corpus_id: str
    run_id: str
    result: Literal["pass", "fail"]
    runner: str
    captured_at: str


class JudgmentRunEvidence(StrictSchemaModel):
    tier: Literal["judgment"]
    golden_manifest_id: str
    golden_manifest_sha256: str
    model: str
    model_settings: dict[str, Any]
    score: float
    threshold: float
    per_case_results: list[dict[str, Any]]
    result: Literal["pass", "fail"]
    runner: str
    captured_at: str


RunEvidence = Annotated[
    Union[CodeRunEvidence, SystemValidationRunEvidence, JudgmentRunEvidence],
    Field(discriminator="tier"),
]


class TestMaturityRecord(StrictSchemaModel):
    """One TMR record in ``tmr-registry.json``."""

    tmr_uid: str
    test_id: str
    title: str
    user_story: str | list[str]
    maturity: Literal["nl", "acceptance", "concrete"]
    data_strategy: Literal[
        "REAL-DATA",
        "REAL-DATA + PROPERTY",
        "SYNTHETIC",
        "MOCK",
        "MOCK-EXTERNAL",
        "FRONTEND",
        "STATIC",
    ]
    spine: bool
    verification_mode: Literal[
        "automated-unit",
        "automated-integration",
        "automated-contract",
        "automated-component",
        "test-producer",
        "artifact-sync",
        "static-check",
        "manual-ux",
        "system-validation",
    ]
    verification_scope: Literal[
        "targeted", "full-suite", "static", "manual", "end-to-end"
    ]
    altitude: Literal["component", "subsystem", "system"]
    tested_by: Literal["llm", "user", "both"]
    critical_seam: bool | None
    criticality_source: Literal["explicit", "architecture_link", "unknown"]
    binding_status: Literal["unbound", "bound"]
    status: Literal["active", "tombstoned"]
    source_spec: str

    live_or_induced: LiveOrInducedTechnique | None
    run_evidence: RunEvidence | None

    why_impossible_to_reproduce_live: str | None = None
    technical_constraint: str | None = None
    also_covers: list[str] = Field(default_factory=list)
    accessors: list[str] = Field(default_factory=list)
    architecture_link: list[str] = Field(default_factory=list)
    spine_steps: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    tombstoned_at: str | None = None
    spine_of: str | None = None
    spine_step_ref: str | None = None

    _classified: bool = PrivateAttr(default=False)

    def __getattribute__(self, name: str) -> Any:
        if name in ("critical_seam", "criticality_source", "architecture_link"):
            frame = sys._getframe(1)
            is_allowed = False
            while frame:
                filename = frame.f_code.co_filename
                basename = os.path.basename(filename)
                if (
                    basename == "criticality_classifier.py"
                    or basename == "tmr_schema.py"
                    or "pydantic" in filename
                ):
                    is_allowed = True
                    break
                frame = frame.f_back

            if not is_allowed:
                if name == "architecture_link":
                    raise ValueError(
                        "Access to 'architecture_link' is restricted to CriticalityClassifier."
                    )

                try:
                    pydantic_private = object.__getattribute__(self, "__pydantic_private__")
                    classified_val = pydantic_private.get("_classified", False) if pydantic_private else False
                except AttributeError:
                    classified_val = False

                if not classified_val:
                    raise ValueError(
                        f"Access to field {name!r} is rejected because the record has not been classified. "
                        "You must run CriticalityClassifier on the record first."
                    )
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("critical_seam", "criticality_source"):
            frame = sys._getframe(1)
            is_allowed = False
            while frame:
                filename = frame.f_code.co_filename
                basename = os.path.basename(filename)
                if (
                    basename == "criticality_classifier.py"
                    or basename == "tmr_schema.py"
                    or "pydantic" in filename
                ):
                    is_allowed = True
                    break
                frame = frame.f_back
            if not is_allowed:
                raise ValueError(f"Only CriticalityClassifier can write to/update field {name!r}.")
        super().__setattr__(name, value)

    @model_validator(mode="after")
    def enforce_conditional_contract(self) -> "TestMaturityRecord":
        if self.status == "tombstoned" and not _non_empty(self.tombstoned_at):
            raise ValueError("tombstoned_at is required when status=tombstoned")
        if self.status == "active" and self.tombstoned_at is not None:
            raise ValueError("tombstoned_at must be null when status=active")

        needs_impossibility = (
            self.data_strategy not in REAL_DATA_STRATEGIES
            and self.critical_seam is True
        ) or (self.data_strategy == "MOCK" and self.live_or_induced is None)
        if needs_impossibility and not _non_empty(
            self.why_impossible_to_reproduce_live
        ):
            raise ValueError(
                "why_impossible_to_reproduce_live is required for non-real "
                "critical seams and justified MOCK records"
            )
        if (
            self.data_strategy == "MOCK"
            and self.live_or_induced is None
            and not _non_empty(self.technical_constraint)
        ):
            raise ValueError(
                "technical_constraint is required when data_strategy=MOCK "
                "and live_or_induced=null"
            )

        self._enforce_run_evidence_compatibility()
        return self

    def _enforce_run_evidence_compatibility(self) -> None:
        if self.run_evidence is None:
            if self.verification_mode in EXEMPT_VERIFICATION_MODES:
                return
            if self.maturity in {"nl", "acceptance"}:
                return
            raise ValueError(
                "run_evidence is required for concrete non-exempt TMR records"
            )

        tier = self.run_evidence.tier
        if self.verification_mode in EXEMPT_VERIFICATION_MODES:
            raise ValueError(
                f"verification_mode={self.verification_mode!r} requires "
                "run_evidence=null"
            )
        if self.verification_mode in CODE_VERIFICATION_MODES and tier != "code":
            raise ValueError(
                f"verification_mode={self.verification_mode!r} requires "
                "run_evidence.tier='code'"
            )
        if self.verification_mode == "system-validation" and tier not in {
            "system-validation",
            "judgment",
        }:
            raise ValueError(
                "verification_mode='system-validation' requires "
                "run_evidence.tier of 'system-validation' or 'judgment'"
            )


class SchemaValidationError(ValueError):
    """Named contract rejection used by skill and Fizzy mirror tests."""

    def __init__(self, field: str, detail: str) -> None:
        self.code = "schema_error"
        self.field = field
        self.detail = detail
        super().__init__(f"{self.code}: {field}: {detail}")


@dataclass(frozen=True)
class TmrSchemaCopyFinding:
    path: Path
    code: Literal[
        "tmr_schema_copy_unallowlisted", "tmr_schema_copy_stale_generated_from"
    ]
    detail: str


class SchemaSnapshotDriftError(ValueError):
    """Raised when a prose snapshot hash no longer matches the JSON Schema."""

    def __init__(self, expected: str, actual: str | None) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"schema_sha256 snapshot drift: expected {expected}, found {actual}"
        )


def validate_tmr_record(payload: dict[str, Any]) -> TestMaturityRecord:
    """Validate one TMR payload and translate Pydantic errors to schema_error."""

    try:
        return TestMaturityRecord.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = _loc_to_field(first.get("loc", ()))
        detail = str(first.get("msg") or exc)
        raise SchemaValidationError(field, detail) from None


def dump_tmr_record(record: TestMaturityRecord) -> dict[str, Any]:
    """Field-preserving JSON dump used by contract round-trip tests."""

    return record.model_dump(mode="json", exclude_none=False)


def tmr_json_schema(*, include_generated_comment: bool = False) -> dict[str, Any]:
    """Return the canonical JSON Schema for one TMR record."""

    schema = TestMaturityRecord.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://brainquarters.local/schemas/test-maturity-record.schema.json"
    schema["x-contract-version"] = CONTRACT_VERSION
    if include_generated_comment:
        schema["$comment"] = f"generated-from:{schema_sha256()}"
    return schema


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def schema_sha256() -> str:
    """Hash of the canonical JSON Schema payload, excluding generated comments."""

    digest = hashlib.sha256(canonical_json(tmr_json_schema()).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def schema_snapshot_hash(text: str) -> str | None:
    match = SCHEMA_HASH_RE.search(text)
    return match.group(1) if match else None


def assert_schema_snapshot_current(text: str) -> None:
    expected = schema_sha256()
    actual = schema_snapshot_hash(text)
    if actual != expected:
        raise SchemaSnapshotDriftError(expected, actual)


def lint_tmr_schema_copies(
    roots: list[Path],
    *,
    canonical_path: Path,
    canonical_sha256: str | None = None,
) -> list[TmrSchemaCopyFinding]:
    """Find unallowlisted prose copies of the TMR keystone.

    This is fail-first linting only. It reports findings and never deletes or
    rewrites any file.
    """

    canonical_sha256 = canonical_sha256 or schema_sha256()
    canonical_real = canonical_path.resolve()
    findings: list[TmrSchemaCopyFinding] = []
    for root in roots:
        for path in _walk_text_files(root):
            if path.resolve() == canonical_real:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if not _looks_like_tmr_schema_copy(text):
                continue
            generated_from = _generated_from_hash(text)
            if generated_from == canonical_sha256:
                continue
            if generated_from is None:
                findings.append(
                    TmrSchemaCopyFinding(
                        path=path,
                        code="tmr_schema_copy_unallowlisted",
                        detail=(
                            "TMR schema copy lacks generated-from:"
                            f"{canonical_sha256}"
                        ),
                    )
                )
            else:
                findings.append(
                    TmrSchemaCopyFinding(
                        path=path,
                        code="tmr_schema_copy_stale_generated_from",
                        detail=(
                            f"TMR schema copy generated-from:{generated_from} "
                            f"does not match {canonical_sha256}"
                        ),
                    )
                )
    return findings


def _non_empty(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _loc_to_field(loc: Any) -> str:
    if not loc:
        return "<record>"
    parts: list[str] = []
    for part in loc:
        if isinstance(part, str):
            parts.append(part)
        else:
            parts.append(str(part))
    return ".".join(parts)


def _walk_text_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    skipped_dirs = {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache"}
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in skipped_dirs for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json", ".jsonl"}:
            files.append(path)
    return files


def _looks_like_tmr_schema_copy(text: str) -> bool:
    if "tmr_uid" not in text or "live_or_induced" not in text:
        return False
    return any(marker in text for marker in COPY_MARKERS)


def _generated_from_hash(text: str) -> str | None:
    match = GENERATED_FROM_RE.search(text)
    return match.group(1) if match else None
