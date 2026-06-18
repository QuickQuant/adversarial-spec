"""Parallel guardrail orchestration for debate checkpoint checks."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

GUARDRAIL_ORDER = (
    "CONS",
    "SCOPE",
    "TRACE",
    "CANON",
    "TCOV",
)

Action = Literal["critique", "gauntlet"]
Severity = Literal["blocking", "warning"]


class GuardrailTransientError(RuntimeError):
    """A transport-level error worth retrying before ORCH synthesis."""


@dataclass(frozen=True)
class GuardrailPayload:
    guardrail: str
    persona_prompt: str
    content_bundle: dict[str, str]
    text_diff: str
    tmr_semantic_delta: dict[str, object]


@dataclass(frozen=True)
class StructuredFinding:
    guardrail: str
    code: str
    message: str
    target_type: Literal["test", "user_story", "tmr", "section", "orch"]
    target_id: str
    severity: Severity
    changes_tmr_field: bool = False
    tmr_uid: str | None = None
    field: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "guardrail": self.guardrail,
            "code": self.code,
            "message": self.message,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "severity": self.severity,
            "changes_tmr_field": self.changes_tmr_field,
            "tmr_uid": self.tmr_uid,
            "field": self.field,
        }


@dataclass(frozen=True)
class GuardrailResult:
    guardrail: str
    findings: list[StructuredFinding] = field(default_factory=list)
    attempts: int = 1
    orch_error: str | None = None

    @property
    def passed(self) -> bool:
        return self.orch_error is None and not self.findings

    def to_dict(self) -> dict[str, object]:
        return {
            "guardrail": self.guardrail,
            "passed": self.passed,
            "attempts": self.attempts,
            "orch_error": self.orch_error,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class GuardrailAggregate:
    action: Action
    results: dict[str, GuardrailResult]

    @property
    def findings(self) -> list[StructuredFinding]:
        merged: list[StructuredFinding] = []
        for guardrail in GUARDRAIL_ORDER:
            merged.extend(self.results[guardrail].findings)
        return merged

    @property
    def outcome(self) -> Literal["pass", "warn", "block"]:
        if not self.findings:
            return "pass"
        if self.action == "gauntlet" and any(
            finding.severity == "blocking" for finding in self.findings
        ):
            return "block"
        return "warn"

    def journalable_findings(self) -> list[StructuredFinding]:
        return [
            finding
            for finding in self.findings
            if finding.changes_tmr_field and finding.tmr_uid and finding.field
        ]

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "outcome": self.outcome,
            "results": {
                guardrail: self.results[guardrail].to_dict()
                for guardrail in GUARDRAIL_ORDER
            },
            "findings": [finding.to_dict() for finding in self.findings],
        }


GuardrailDispatch = Callable[[GuardrailPayload], GuardrailResult]


class GuardrailOrchestrator:
    """Run each checkpoint guardrail as a separate retrying subagent call."""

    def __init__(
        self,
        dispatch: GuardrailDispatch,
        *,
        max_retries: int = 2,
        backoff_seconds: float = 0.1,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._dispatch = dispatch
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleeper

    def run(
        self,
        *,
        action: Action,
        persona_prompts: dict[str, str],
        content_bundle: dict[str, str],
        text_diff: str,
        tmr_semantic_delta: dict[str, object],
    ) -> GuardrailAggregate:
        with ThreadPoolExecutor(max_workers=len(GUARDRAIL_ORDER)) as pool:
            futures = {
                pool.submit(
                    self._run_one,
                    guardrail,
                    action,
                    GuardrailPayload(
                        guardrail=guardrail,
                        persona_prompt=persona_prompts[guardrail],
                        content_bundle=dict(content_bundle),
                        text_diff=text_diff,
                        tmr_semantic_delta=dict(tmr_semantic_delta),
                    ),
                ): guardrail
                for guardrail in GUARDRAIL_ORDER
            }
            results = {
                guardrail: future.result()
                for future, guardrail in ((f, futures[f]) for f in as_completed(futures))
            }

        return GuardrailAggregate(action=action, results=results)

    def _run_one(
        self,
        guardrail: str,
        action: Action,
        payload: GuardrailPayload,
    ) -> GuardrailResult:
        attempts = 0
        while attempts <= self._max_retries:
            attempts += 1
            try:
                result = self._dispatch(payload)
                return GuardrailResult(
                    guardrail=guardrail,
                    findings=result.findings,
                    attempts=attempts,
                    orch_error=result.orch_error,
                )
            except GuardrailTransientError:
                if attempts > self._max_retries:
                    return self._orch_result(guardrail, action, attempts, "transient")
                self._sleep(self._backoff_seconds * attempts)
            except Exception as exc:
                return self._orch_result(guardrail, action, attempts, str(exc))

        return self._orch_result(guardrail, action, attempts, "exhausted")

    @staticmethod
    def _orch_result(
        guardrail: str,
        action: Action,
        attempts: int,
        error: str,
    ) -> GuardrailResult:
        severity: Severity = "blocking" if action == "gauntlet" else "warning"
        finding = StructuredFinding(
            guardrail=guardrail,
            code="ORCH",
            message=f"{guardrail} guardrail subagent failed: {error}",
            target_type="orch",
            target_id=guardrail,
            severity=severity,
        )
        return GuardrailResult(
            guardrail=guardrail,
            findings=[finding],
            attempts=attempts,
            orch_error=error,
        )


def persist_round_results(path: Path, aggregate: GuardrailAggregate) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(aggregate.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
