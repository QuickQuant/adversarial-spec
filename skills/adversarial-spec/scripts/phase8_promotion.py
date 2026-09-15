"""Phase-8 pseudo-to-real promotion checks and run receipt capture."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

if __package__:
    from .tmr_schema import CodeRunEvidence, TargetObservation
else:
    from tmr_schema import CodeRunEvidence, TargetObservation

REAL_DATA_STRATEGIES = frozenset({"REAL-DATA", "REAL-DATA + PROPERTY"})
EXEMPT_VERIFICATION_MODES = frozenset({"artifact-sync", "static-check", "manual-ux"})
CRITICAL_NON_LIVE_ENVS = frozenset({"dev", "ci"})


@dataclass(frozen=True)
class PromotionIssue:
    code: str
    tmr_uid: str
    message: str
    severity: Literal["halt", "failing"] = "failing"


@dataclass(frozen=True)
class PromotionRequest:
    tmr_uid: str
    test_id: str
    user_story: str | list[str]
    command: str
    cwd: str
    repo: str
    commit: str
    accessors: list[str]
    negative_oracle_required: bool = True
    owner_authors_and_binds: bool = True
    target_binding: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "promotion_request",
            "tmr_uid": self.tmr_uid,
            "test_id": self.test_id,
            "user_story": self.user_story,
            "command": self.command,
            "cwd": self.cwd,
            "repo": self.repo,
            "commit": self.commit,
            "accessors": self.accessors,
            "negative_oracle_required": self.negative_oracle_required,
            "owner_authors_and_binds": self.owner_authors_and_binds,
            "target_binding": deepcopy(self.target_binding),
        }


@dataclass(frozen=True)
class RunExecution:
    exit_code: int
    started_at: str
    finished_at: str
    artifact_uri: str
    artifact_sha256: str
    live_or_induced: dict[str, str] | None = None
    target_observation: dict[str, Any] | None = None


@dataclass(frozen=True)
class Phase8PromotionReport:
    requests: list[PromotionRequest] = field(default_factory=list)
    issues: list[PromotionIssue] = field(default_factory=list)

    @property
    def can_close(self) -> bool:
        return not self.issues


CommandRunner = Callable[[PromotionRequest], RunExecution]


def build_promotion_requests(
    records: Sequence[Mapping[str, Any]],
    *,
    command_by_uid: Mapping[str, str],
    cwd: str,
    repo: str,
    commit: str,
) -> Phase8PromotionReport:
    requests: list[PromotionRequest] = []
    issues: list[PromotionIssue] = []
    for record in records:
        if not _requires_promotion(record):
            continue

        tmr_uid = str(record["tmr_uid"])
        accessors = _accessors(record)
        if not accessors or record.get("binding_status") != "bound":
            issues.append(
                PromotionIssue(
                    code="unbound_accessor_halt",
                    tmr_uid=tmr_uid,
                    message="promotion requires bound, named accessors before close",
                    severity="halt",
                )
            )
            continue

        command = command_by_uid.get(tmr_uid)
        if not command:
            issues.append(
                PromotionIssue(
                    code="promotion_command_missing",
                    tmr_uid=tmr_uid,
                    message="promotion_request requires a declared owner-repo command",
                    severity="halt",
                )
            )
            continue

        requests.append(
            PromotionRequest(
                tmr_uid=tmr_uid,
                test_id=str(record["test_id"]),
                user_story=record["user_story"],
                command=command,
                cwd=cwd,
                repo=repo,
                commit=commit,
                accessors=accessors,
                target_binding=deepcopy(record.get("target_binding")),
            )
        )
    return Phase8PromotionReport(requests=requests, issues=issues)


def read_process_start_time(pid: int) -> str | None:
    """Read a live Linux process's UTC start time; unavailable identity is null.

    Field 22 of /proc/PID/stat counts ticks since boot. Parse after the final
    parenthesis because the process name can itself contain spaces or ')'.
    Call while the child still exists; never substitute capture wall time.
    """
    if sys.platform != "linux" or type(pid) is not int or pid <= 0:
        return None
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        end_comm = stat.rfind(")")
        if end_comm < 0 or int(stat.split(" ", 1)[0]) != pid:
            return None
        ticks = int(stat[end_comm + 2 :].split()[19])
        hz = os.sysconf("SC_CLK_TCK")
        boot = next(
            int(line.split()[1])
            for line in Path("/proc/stat").read_text(encoding="utf-8").splitlines()
            if line.startswith("btime ")
        )
        if ticks < 0 or hz <= 0 or boot < 0:
            return None
        return datetime.fromtimestamp(boot + ticks / hz, timezone.utc).isoformat()
    except (OSError, ValueError, IndexError, OverflowError, StopIteration):
        return None


def _runtime_identity_issues(receipt: dict[str, Any] | None) -> list[dict[str, str]]:
    """Check capture completeness, then defer structural rules to E-31."""

    def incomplete(field: str) -> list[dict[str, str]]:
        return [{"code": "RUNTIME_IDENTITY_INCOMPLETE", "field": field}]

    if receipt is None:
        return incomplete("runtime_receipt_id")
    receipt_id = receipt.get("runtime_receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id.strip():
        return incomplete("runtime_receipt_id")
    pid = receipt.get("pid")
    if type(pid) is not int or pid <= 0:
        return incomplete("pid")
    try:
        start = datetime.fromisoformat(receipt.get("pid_start_time"))
        if start.utcoffset() is None or start.utcoffset().total_seconds() != 0:
            return incomplete("pid_start_time")
    except (TypeError, ValueError):
        return incomplete("pid_start_time")
    for field_name in (
        "entrypoint_observed",
        "authority_ref_observed",
        "terminal_state",
    ):
        value = receipt.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return incomplete(field_name)
    if receipt["terminal_state"] in {"partial", "timeout"}:
        return incomplete("terminal_state")
    try:
        TargetObservation.model_validate(receipt)
    except ValidationError as error:
        return [
            {"code": "RUNTIME_IDENTITY_INCOMPLETE", "field": str(issue["loc"][0])}
            for issue in error.errors()
        ]
    return []


def capture_run_evidence(
    request: PromotionRequest,
    *,
    runner: CommandRunner,
    env: Literal["live", "dev", "ci"],
    owner_written_result: str | Mapping[str, Any] | None = None,
    owner_written_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute once and return a detached TargetObservationCapture envelope.

    The callback owns measured fields and the receipt ID; the binding owns only
    intended outcome/caller/path labels. Owner observations cannot repair a
    runner receipt. Consumers must check COMPLETE before using run_evidence.
    Capture does not compare targets, reconcile custody, or decide freshness.
    """
    owner_observation_ignored = any(
        observation is not None
        for observation in (
            owner_written_observation,
            getattr(request, "target_observation", None),
            _get(getattr(request, "run_evidence", None), "target_observation"),
            _get(owner_written_result, "target_observation"),
        )
    )
    binding = deepcopy(request.target_binding)
    execution = runner(request)
    receipt = deepcopy(execution.target_observation)
    if isinstance(receipt, dict):
        # A receipt carries observations only. Exit status alone owns result.
        receipt.pop("result", None)
        for field_name in ("outcome_id", "caller_id", "path_id"):
            receipt[field_name] = _get(binding, field_name)
    else:
        receipt = None
    capture = {
        "capture_state": "INCOMPLETE",
        "observation_source": "runner",
        "owner_observation_ignored": owner_observation_ignored,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "target_ref": request.commit,
        "runtime_receipt": receipt,
        "run_evidence": None,
        "issues": _runtime_identity_issues(receipt),
    }
    if capture["issues"]:
        return capture

    result: Literal["pass", "fail"] = "pass" if execution.exit_code == 0 else "fail"
    evidence = CodeRunEvidence.model_validate(
        {
            "tier": "code",
            "command": request.command,
            "cwd": request.cwd,
            "repo": request.repo,
            "commit": request.commit,
            "started_at": execution.started_at,
            "finished_at": execution.finished_at,
            "exit": execution.exit_code,
            "result": result,
            "env": env,
            "artifact_uri": execution.artifact_uri,
            "artifact_sha256": execution.artifact_sha256,
            "runner": "skill-runner",
            "live_or_induced": execution.live_or_induced,
            "target_observation": receipt,
        }
    ).model_dump(mode="json")
    capture["capture_state"] = "COMPLETE"
    capture["run_evidence"] = evidence
    return capture


def evaluate_phase8_close(records: Sequence[Mapping[str, Any]]) -> Phase8PromotionReport:
    issues: list[PromotionIssue] = []
    for record in records:
        if not _is_real_critical_or_spine(record):
            continue
        tmr_uid = str(record["tmr_uid"])
        run_evidence = record.get("run_evidence")

        if record.get("test_strategy") == "spike" or record.get(
            "verification_mode"
        ) in EXEMPT_VERIFICATION_MODES:
            issues.append(
                PromotionIssue(
                    code="spine_critical_exempt",
                    tmr_uid=tmr_uid,
                    message="spine or critical-seam REAL-DATA tests may not close as spike/exempt",
                )
            )

        if not _accessors(record) or record.get("binding_status") != "bound":
            issues.append(
                PromotionIssue(
                    code="unbound_accessor_halt",
                    tmr_uid=tmr_uid,
                    message="unbound accessors halt Phase-8 close",
                    severity="halt",
                )
            )

        if not _has_negative_oracle(record):
            issues.append(
                PromotionIssue(
                    code="negative_oracle_missing",
                    tmr_uid=tmr_uid,
                    message="REAL-DATA promotion requires a negative oracle",
                )
            )

        if run_evidence is None:
            issues.append(
                PromotionIssue(
                    code="run_evidence_missing",
                    tmr_uid=tmr_uid,
                    message="declared REAL-DATA critical/spine test has never been run",
                )
            )
            continue

        if _get(run_evidence, "result") != "pass":
            issues.append(
                PromotionIssue(
                    code="run_evidence_not_green",
                    tmr_uid=tmr_uid,
                    message="Phase-8 close requires a green skill-runner receipt",
                )
            )
        if _get(run_evidence, "runner") != "skill-runner":
            issues.append(
                PromotionIssue(
                    code="untrusted_run_evidence",
                    tmr_uid=tmr_uid,
                    message="owner-written results are not trusted as run evidence",
                )
            )
        if _get(run_evidence, "env") in CRITICAL_NON_LIVE_ENVS and _get(
            run_evidence, "live_or_induced"
        ) is None:
            issues.append(
                PromotionIssue(
                    code="real_pass_technique_missing",
                    tmr_uid=tmr_uid,
                    message="dev/ci critical-seam pass must record live_or_induced technique",
                )
            )

        mock_issue = _lint_boundary_mock(record)
        if mock_issue:
            issues.append(mock_issue)
    return Phase8PromotionReport(issues=issues)


def _requires_promotion(record: Mapping[str, Any]) -> bool:
    return _is_real_critical_or_spine(record) and record.get("run_evidence") is None


def _is_real_critical_or_spine(record: Mapping[str, Any]) -> bool:
    return record.get("data_strategy") in REAL_DATA_STRATEGIES and (
        record.get("critical_seam") is True or record.get("spine") is True
    )


def _has_negative_oracle(record: Mapping[str, Any]) -> bool:
    return record.get("negative_oracle") is True or record.get(
        "negative_oracle_ref"
    ) not in (None, "")


def _lint_boundary_mock(record: Mapping[str, Any]) -> PromotionIssue | None:
    text = " ".join(str(value).lower() for value in record.values())
    if "mock" not in text:
        return None
    return PromotionIssue(
        code="boundary_mock_detected",
        tmr_uid=str(record["tmr_uid"]),
        message="boundary mock detected in promoted REAL-DATA critical/spine test",
        severity="halt",
    )


def _accessors(record: Mapping[str, Any]) -> list[str]:
    accessors = record.get("accessors", [])
    if not isinstance(accessors, list):
        return []
    return [str(accessor) for accessor in accessors if str(accessor).strip()]


def _get(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)
