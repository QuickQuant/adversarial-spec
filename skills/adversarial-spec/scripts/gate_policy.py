"""Shared reject vocabulary, rollout fence, and receipt freshness policy.

These pure policies consume caller-supplied metadata and identities. Consumers
own gate application, card reads, resolved target hashes, and process evidence.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from enum import StrEnum, unique
from types import MappingProxyType
from typing import Literal


@unique
class RejectCode(StrEnum):
    """The 22 reject codes from hardening packet 03, section 5."""

    TMR_TARGET_BINDING_REQUIRED = "TMR_TARGET_BINDING_REQUIRED"
    TMR_NEGATIVE_ORACLE_SCHEMA_DRIFT = "TMR_NEGATIVE_ORACLE_SCHEMA_DRIFT"
    PROOF_OUTCOME_MISMATCH = "PROOF_OUTCOME_MISMATCH"
    PROOF_CALLER_MISMATCH = "PROOF_CALLER_MISMATCH"
    PROOF_PATH_MISMATCH = "PROOF_PATH_MISMATCH"
    PROOF_PATH_UNCENSUSED = "PROOF_PATH_UNCENSUSED"
    PROOF_AUTHORITY_ROLE_MISMATCH = "PROOF_AUTHORITY_ROLE_MISMATCH"
    PRODUCER_CONSUMER_CONTRACT_UNPROVEN = "PRODUCER_CONSUMER_CONTRACT_UNPROVEN"
    FIXTURE_PROVENANCE_CEILING = "FIXTURE_PROVENANCE_CEILING"
    CONTRACT_ASSERTION_WIDER_THAN_SCHEMA = "CONTRACT_ASSERTION_WIDER_THAN_SCHEMA"
    CONTRADICTORY_IDENTITY_UNTESTED = "CONTRADICTORY_IDENTITY_UNTESTED"
    RUNTIME_IDENTITY_INCOMPLETE = "RUNTIME_IDENTITY_INCOMPLETE"
    PACKAGE_COMPONENT_UNPROVEN = "PACKAGE_COMPONENT_UNPROVEN"
    PLAN_SCHEMA_VERSION_TYPE_INVALID = "PLAN_SCHEMA_VERSION_TYPE_INVALID"
    VALIDATE_LOAD_CLASSIFICATION_DIVERGENCE = "VALIDATE_LOAD_CLASSIFICATION_DIVERGENCE"
    SCHEDULE_POSTCONDITION_FAILED = "SCHEDULE_POSTCONDITION_FAILED"
    TERMINAL_ENUM_UNCOVERED = "TERMINAL_ENUM_UNCOVERED"
    PREDECESSOR_NEGATIVE_PROOF_MISSING = "PREDECESSOR_NEGATIVE_PROOF_MISSING"
    CUSTODY_ENTRY_MISSING = "CUSTODY_ENTRY_MISSING"
    CUSTODY_DISPOSITION_INCOMPLETE = "CUSTODY_DISPOSITION_INCOMPLETE"
    CUSTODY_DESTRUCTIVE_PREVIEW_INCOMPLETE = "CUSTODY_DESTRUCTIVE_PREVIEW_INCOMPLETE"
    CUSTODY_BUDGET_BREACH = "CUSTODY_BUDGET_BREACH"


# Keep the packet vocabulary independent of the live enum: deriving this from
# RejectCode would conceal a missing member from the drift self-check.
_REJECT_CONDITIONS: Mapping[str, str] = MappingProxyType(
    {
        "TMR_TARGET_BINDING_REQUIRED": "load-bearing TMR lacks target binding",
        "TMR_NEGATIVE_ORACLE_SCHEMA_DRIFT": "promoter expects an oracle field canonical TMR cannot represent",
        "PROOF_OUTCOME_MISMATCH": "receipt outcome differs from obligation",
        "PROOF_CALLER_MISMATCH": "observed caller differs from intended caller; no equivalence proof",
        "PROOF_PATH_MISMATCH": "observed route/entrypoint differs from binding",
        "PROOF_PATH_UNCENSUSED": "observed or planned effect path absent from authority census",
        "PROOF_AUTHORITY_ROLE_MISMATCH": "legacy/emergency/dead path attempts authoritative discharge",
        "PRODUCER_CONSUMER_CONTRACT_UNPROVEN": "actual producer output was not parsed by exact consumer contract",
        "FIXTURE_PROVENANCE_CEILING": (
            "typed `fixture_provenance` shows a constructed/recorded/stub producer "
            "at a boundary the obligation binds to a real producer; evidence cannot "
            "rise above fixture level regardless of lexical content "
            "(added 2026-09-14, review F-02 adjacent)"
        ),
        "CONTRACT_ASSERTION_WIDER_THAN_SCHEMA": "test oracle accepts values canonical consumer rejects",
        "CONTRADICTORY_IDENTITY_UNTESTED": "multiple plausible identity fields lack conflict case",
        "RUNTIME_IDENTITY_INCOMPLETE": "any required source→artifact→activation→process link absent",
        "PACKAGE_COMPONENT_UNPROVEN": "shipped process omitted from package parity receipt",
        "PLAN_SCHEMA_VERSION_TYPE_INVALID": "present discriminator is not supported integer",
        "VALIDATE_LOAD_CLASSIFICATION_DIVERGENCE": "validate/load classify same plan differently",
        "SCHEDULE_POSTCONDITION_FAILED": "emitted/load schedule or readiness differs from plan graph",
        "TERMINAL_ENUM_UNCOVERED": "reachable terminal state absent from runner/test matrix",
        "PREDECESSOR_NEGATIVE_PROOF_MISSING": "changed authority lacks old-path absence/compatibility evidence",
        "CUSTODY_ENTRY_MISSING": "pipeline-owned temporary authority lacks item row",
        "CUSTODY_DISPOSITION_INCOMPLETE": "in-scope item lacks terminal evidence",
        "CUSTODY_DESTRUCTIVE_PREVIEW_INCOMPLETE": "removal preview lacks content/runtime/recovery/authorization evidence",
        "CUSTODY_BUDGET_BREACH": (
            "new pipeline-owned creation would exceed the custody budget and no "
            "operator exception line exists; blocks the creation only, never "
            "authorizes cleanup (added 2026-09-14, review F-02)"
        ),
    }
)

EnforcementMode = Literal["legacy", "warn", "reject"]
FRESHNESS_WINDOW_SECONDS = 86400


class GatePolicyError(ValueError):
    """A catalogued policy rejection with the offending field and detail."""

    def __init__(self, code: RejectCode, field: str, detail: str) -> None:
        self.code = RejectCode(code)
        self.field = field
        self.detail = detail
        super().__init__(f"{self.code}: {field}: {detail}")


def catalog() -> tuple[RejectCode, ...]:
    """Return each typed code once, in packet order."""
    return tuple(RejectCode)


def describe(code: RejectCode | str) -> str:
    """Return the verbatim packet condition; unknown codes raise ValueError."""
    return _REJECT_CONDITIONS[RejectCode(code).value]


def _as_utc(value: object, *, field: str, allow_datetime: bool = False) -> datetime:
    """Validate timezone awareness before normalizing an input to UTC."""
    try:
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value)
        elif allow_datetime and isinstance(value, datetime):
            parsed = value
        else:
            raise ValueError("expected a timezone-aware ISO-8601 timestamp")
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise GatePolicyError(
            RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN, field, str(exc)
        ) from exc


def resolve_enforcement_mode(
    card_metadata: Mapping[str, object], *, cutover: str
) -> EnforcementMode:
    """Resolve RB-1 using an explicit cutoff and validated card metadata.

    Absent version metadata selects legacy mode. Every present version must be
    an exact integer and have a valid creation timestamp. Versions below 6 and
    cards created before cutover warn; all other valid cards select rejection.
    Binding validity is evaluated by the consumer after choosing this mode.
    """
    cutoff = _as_utc(cutover, field="cutover")
    if not isinstance(card_metadata, Mapping):
        raise GatePolicyError(
            RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN,
            "card_metadata",
            "expected a readable mapping",
        )
    try:
        # Snapshot once so a failed metadata read cannot masquerade as absence.
        metadata = dict(card_metadata)
    except Exception as exc:
        raise GatePolicyError(
            RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN,
            "card_metadata",
            f"cannot read metadata: {exc}",
        ) from exc

    if "pipeline_version" not in metadata:
        if "created_at" in metadata:
            _as_utc(metadata["created_at"], field="created_at")
        return "legacy"

    version = metadata["pipeline_version"]
    if type(version) is not int:
        raise GatePolicyError(
            RejectCode.PLAN_SCHEMA_VERSION_TYPE_INVALID,
            "pipeline_version",
            "expected an integer (booleans and coercible values are invalid)",
        )
    created_at = _as_utc(metadata.get("created_at"), field="created_at")
    if version >= 6 and created_at >= cutoff:
        return "reject"
    return "warn"


def is_receipt_fresh(
    receipt_captured_at: datetime | str,
    now: datetime | str,
    *,
    target_ref_at_capture: str,
    target_ref_now: str,
) -> bool:
    """Accept ages from zero through 24 hours only for identical targets.

    Target strings are opaque resolved identities supplied by the caller.
    A changed ref/hash invalidates immediately. Invalid timestamps raise
    GatePolicyError; freshness alone does not establish process continuity.
    """
    if target_ref_at_capture != target_ref_now:
        return False
    captured = _as_utc(
        receipt_captured_at, field="receipt_captured_at", allow_datetime=True
    )
    current = _as_utc(now, field="now", allow_datetime=True)
    return (
        timedelta(0)
        <= current - captured
        <= timedelta(seconds=FRESHNESS_WINDOW_SECONDS)
    )


def self_check_emitted_codes(emitted_codes: Iterable[str]) -> None:
    """Reject loss of an emitted section-5 member; ignore other vocabularies."""
    for code in emitted_codes:
        if code not in _REJECT_CONDITIONS:
            continue
        member = RejectCode.__members__.get(code)
        if member is None or member.name != code or member.value != code:
            raise GatePolicyError(
                RejectCode.TERMINAL_ENUM_UNCOVERED,
                "RejectCode",
                f"emitted packet code {code!r} is missing its exact enum member",
            )
