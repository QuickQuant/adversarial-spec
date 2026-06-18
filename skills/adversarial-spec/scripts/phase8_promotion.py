"""Phase-8 pseudo-to-real promotion checks and run receipt capture."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

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
        }


@dataclass(frozen=True)
class RunExecution:
    exit_code: int
    started_at: str
    finished_at: str
    artifact_uri: str
    artifact_sha256: str
    live_or_induced: dict[str, str] | None = None


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
            )
        )
    return Phase8PromotionReport(requests=requests, issues=issues)


def capture_run_evidence(
    request: PromotionRequest,
    *,
    runner: CommandRunner,
    env: Literal["live", "dev", "ci"],
    owner_written_result: str | None = None,
) -> dict[str, Any]:
    """Run the declared command and build the only trusted code receipt.

    ``owner_written_result`` is accepted only to make the trust boundary explicit:
    the result always comes from the skill-runner process exit.
    """

    _ = owner_written_result
    execution = runner(request)
    result: Literal["pass", "fail"] = "pass" if execution.exit_code == 0 else "fail"
    return {
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
    }


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
