"""Canonical gate-result envelope and exit-code map.

W0-3 introduces the shared result type. Later gates consume this module instead
of hand-rolling exit-code branches or overloading a bare integer.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

GATE_OUTCOMES = (
    "pass",
    "warn",
    "block",
    "schema_error",
    "orch_error",
    "setup_error",
)

EXIT_BY_OUTCOME: dict[str, int] = {
    "pass": 0,
    "warn": 0,
    "block": 2,
    "schema_error": 3,
    "orch_error": 4,
    "setup_error": 5,
}

MCP_ERROR_BY_OUTCOME: dict[str, str | None] = {
    "pass": None,
    "warn": None,
    "block": "GATE_BLOCKED",
    "schema_error": "GATE_SCHEMA_ERROR",
    "orch_error": "GATE_ORCH_ERROR",
    "setup_error": "GATE_SETUP_ERROR",
}

NON_OVERRIDABLE_OUTCOMES = frozenset({"schema_error", "setup_error", "orch_error"})


class GateFinding(BaseModel):
    """One structured finding emitted by a gate."""

    model_config = ConfigDict(extra="forbid", strict=True)

    code: str
    message: str
    severity: Literal["info", "warning", "blocking"]
    target: dict[str, Any] = Field(default_factory=dict)


class GateResult(BaseModel):
    """Normative gate envelope.

    ``outcome`` is the only result field. Do not add ``result``; that word is
    reserved for unrelated execution receipts such as ``run_evidence.result``.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    outcome: Literal[
        "pass", "warn", "block", "schema_error", "orch_error", "setup_error"
    ]
    findings: list[GateFinding] = Field(default_factory=list)
    override_eligible: bool = False

    @model_validator(mode="after")
    def enforce_override_contract(self) -> "GateResult":
        if self.outcome in NON_OVERRIDABLE_OUTCOMES and self.override_eligible:
            raise ValueError(f"{self.outcome} is not override-eligible")
        if self.outcome in {"pass", "warn"} and self.override_eligible:
            raise ValueError(f"{self.outcome} must not be override-eligible")
        return self

    def exit_code(self) -> int:
        return exit_code_for_outcome(self.outcome)

    def mcp_error_code(self) -> str | None:
        return mcp_error_for_outcome(self.outcome)

    def to_envelope(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=False)


def exit_code_for_outcome(outcome: str) -> int:
    try:
        return EXIT_BY_OUTCOME[outcome]
    except KeyError:
        raise ValueError(f"unknown gate outcome: {outcome!r}") from None


def mcp_error_for_outcome(outcome: str) -> str | None:
    try:
        return MCP_ERROR_BY_OUTCOME[outcome]
    except KeyError:
        raise ValueError(f"unknown gate outcome: {outcome!r}") from None


def pass_result(findings: list[GateFinding] | None = None) -> GateResult:
    return GateResult(outcome="pass", findings=findings or [], override_eligible=False)


def warn_result(findings: list[GateFinding]) -> GateResult:
    return GateResult(outcome="warn", findings=findings, override_eligible=False)


def coverage_block(findings: list[GateFinding]) -> GateResult:
    return GateResult(outcome="block", findings=findings, override_eligible=True)


def schema_error(findings: list[GateFinding]) -> GateResult:
    return GateResult(
        outcome="schema_error", findings=findings, override_eligible=False
    )


def orch_error(findings: list[GateFinding]) -> GateResult:
    return GateResult(outcome="orch_error", findings=findings, override_eligible=False)


def setup_error(findings: list[GateFinding]) -> GateResult:
    return GateResult(outcome="setup_error", findings=findings, override_eligible=False)
