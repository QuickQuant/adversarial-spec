"""Phase-8 pseudo-to-real promotion checks and run receipt capture."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import ValidationError

if __package__:
    from .tmr_schema import CodeRunEvidence, TargetObservation
    from .gate_policy import RejectCode, is_receipt_fresh
else:
    from tmr_schema import CodeRunEvidence, TargetObservation
    from gate_policy import RejectCode, is_receipt_fresh

REAL_DATA_STRATEGIES = frozenset({"REAL-DATA", "REAL-DATA + PROPERTY"})
EXEMPT_VERIFICATION_MODES = frozenset({"artifact-sync", "static-check", "manual-ux"})
CRITICAL_NON_LIVE_ENVS = frozenset({"dev", "ci"})


@dataclass(frozen=True)
class PromotionIssue:
    code: str
    tmr_uid: str
    message: str
    severity: Literal["halt", "failing", "warning", "advisory"] | str = "failing"
    expected: dict[str, Any] = field(default_factory=dict)
    observed: dict[str, Any] = field(default_factory=dict)
    evidence_class: str = "MISMATCH"


@dataclass(frozen=True)
class RejectionDiagnostic:
    code: str
    message: str
    test_id: str
    obligation_id: str
    expected: dict[str, Any]
    observed: dict[str, Any]
    evidence_class: str
    next_actor: str
    permitted_recovery: list[str]


class TargetObservationCapture(TypedDict):
    """Runner capture envelope consumed by promotion (E-7) and custody reconcile (E-12).

    Synthesis (antigravity design point): a typed shape for consumers to import.
    """

    capture_state: Literal["COMPLETE", "INCOMPLETE"]
    observation_source: Literal["runner"]
    owner_observation_ignored: bool
    captured_at: str
    target_ref: str
    runtime_receipt: dict[str, Any] | None
    run_evidence: dict[str, Any] | None
    issues: list[dict[str, Any]]


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
        return not any(i.severity in {"halt", "failing"} for i in self.issues)


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
) -> TargetObservationCapture:
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
    capture: TargetObservationCapture = {
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


def _utc(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(parsed, datetime) or parsed.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed.astimezone(timezone.utc)


def _issue(
    code: RejectCode | str,
    field_name: str,
    expected: Any,
    observed: Any,
    evidence_class: str = "MISMATCH",
    *,
    severity: str = "halt",
) -> PromotionIssue:
    return PromotionIssue(
        str(code),
        "",
        f"Evidence for {field_name} cannot discharge the declared obligation: "
        f"expected {expected!r}; observed {observed!r}.",
        severity,
        {"field": field_name, "value": deepcopy(expected)},
        {"field": field_name, "value": deepcopy(observed)},
        evidence_class,
    )


def compare_target_observation(
    binding: Mapping[str, Any],
    observation: Mapping[str, Any] | None,
    *,
    now: datetime | str,
    cutover_mode: str,
) -> list[PromotionIssue]:
    if cutover_mode not in {"legacy", "warn", "reject"}:
        raise ValueError("unsupported enforcement mode")
    if cutover_mode == "legacy":
        return []
    severity = "warning" if cutover_mode == "warn" else "halt"
    issues: list[PromotionIssue] = []

    def add(
        code: RejectCode | str,
        name: str,
        expected: Any,
        actual: Any,
        category: str = "MISMATCH",
    ) -> None:
        issues.append(_issue(code, name, expected, actual, category, severity=severity))

    def incomplete(
        name: str, actual: Any = None, category: str = "MISSING"
    ) -> list[PromotionIssue]:
        add(
            RejectCode.RUNTIME_IDENTITY_INCOMPLETE,
            name,
            "complete trusted runner evidence",
            actual,
            category,
        )
        return issues

    if observation is None:
        return incomplete("target_observation")
    if observation.get("observation_source") != "runner":
        return incomplete(
            "observation_source",
            observation.get("observation_source"),
            "UNSUPPORTED_ORIGIN",
        )
    if observation.get("capture_state") != "COMPLETE":
        return incomplete("capture_state", observation.get("capture_state"))
    receipt = observation.get("runtime_receipt")
    evidence = observation.get("run_evidence")
    if not isinstance(receipt, dict) or not isinstance(evidence, dict):
        return incomplete("runtime_receipt")
    if receipt != evidence.get("target_observation"):
        return incomplete(
            "run_evidence.target_observation",
            evidence.get("target_observation"),
            "UNSUPPORTED_ORIGIN",
        )
    for key in TargetObservation.model_fields:
        if receipt.get(key) is None or receipt.get(key) == "":
            return incomplete(key)
    if type(receipt["pid"]) is not int or receipt["pid"] <= 0:
        return incomplete("pid", receipt["pid"])
    try:
        _utc(receipt["pid_start_time"])
        TargetObservation.model_validate(receipt)
    except (ValueError, TypeError, ValidationError):
        return incomplete("runtime_receipt", receipt)
    expected = binding.get("_comparison", {})
    actual = observation.get("_comparison", {})
    for key in (
        "caller_id_observed",
        "caller_kind_observed",
        "path_id_observed",
        "authority_role_observed",
    ):
        if not actual.get(key):
            return incomplete(key)
    for name, value in (
        ("captured_at", observation.get("captured_at")),
        ("target_ref_at_capture", observation.get("target_ref")),
        ("target_ref_now", expected.get("target_ref")),
    ):
        if not value:
            return incomplete(name)
    try:
        fresh = is_receipt_fresh(
            observation["captured_at"],
            now,
            target_ref_at_capture=observation["target_ref"],
            target_ref_now=expected["target_ref"],
        )
    except Exception:
        return incomplete("captured_at", observation.get("captured_at"))
    if not fresh:
        add(
            RejectCode.RUNTIME_IDENTITY_INCOMPLETE,
            "receipt_freshness",
            {"target_ref": expected["target_ref"], "now": str(now)},
            {
                "target_ref": observation["target_ref"],
                "captured_at": observation["captured_at"],
            },
            "STALE",
        )
    comparisons = (
        (
            RejectCode.PROOF_OUTCOME_MISMATCH,
            "outcome_id",
            binding["outcome_id"],
            receipt["outcome_id"],
        ),
        (
            RejectCode.PROOF_CALLER_MISMATCH,
            "caller",
            [binding["caller_id"], binding["caller_kind"]],
            [actual["caller_id_observed"], actual["caller_kind_observed"]],
        ),
        (
            RejectCode.PROOF_PATH_MISMATCH,
            "path",
            [binding["path_id"], binding["entrypoint"]],
            [actual["path_id_observed"], receipt["entrypoint_observed"]],
        ),
        (
            RejectCode.PROOF_AUTHORITY_ROLE_MISMATCH,
            "authority",
            [binding["authority_ref"], binding["authority_role"]],
            [receipt["authority_ref_observed"], actual["authority_role_observed"]],
        ),
        (
            RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN,
            "contract_hashes",
            [
                binding["producer_contract"]["sha256"],
                binding["consumer_contract"]["sha256"],
            ],
            [receipt["producer_contract_hash"], receipt["consumer_contract_hash"]],
        ),
    )
    for code, name, desired, seen in comparisons:
        if desired != seen:
            add(code, name, desired, seen)
    if binding.get("runtime_chain_required"):
        for slot in binding.get("runtime_slots", []):
            desired = expected.get("runtime_slots", {}).get(slot, {})
            seen = actual.get("runtime_slots", {}).get(slot, {})
            chain = (
                "packaged_source",
                "activation_source",
                "running_source",
                "gateway_source",
            )
            missing = [k for k in chain if not seen.get(k)]
            if not desired.get("intended_source") or missing:
                for code in (
                    RejectCode.RUNTIME_IDENTITY_INCOMPLETE,
                    RejectCode.PACKAGE_COMPONENT_UNPROVEN,
                ):
                    add(code, f"runtime_slots.{slot}", desired, seen, "MISSING")
                continue
            for key in ("pid", "pid_start_time"):
                if not desired.get(key) or not seen.get(key):
                    add(
                        RejectCode.RUNTIME_IDENTITY_INCOMPLETE,
                        f"runtime_slots.{slot}.{key}",
                        desired.get(key),
                        seen.get(key),
                        "MISSING",
                    )
                elif desired[key] != seen[key] or (
                    slot == binding["runtime_slots"][0] and receipt[key] != seen[key]
                ):
                    add(
                        RejectCode.RUNTIME_IDENTITY_INCOMPLETE,
                        f"runtime_slots.{slot}.{key}",
                        desired[key],
                        seen[key],
                        "STALE",
                    )
            for index, key in enumerate(chain):
                if seen[key] != desired["intended_source"]:
                    link = (
                        ("intended_source" if index == 0 else chain[index - 1])
                        + " -> "
                        + key
                    )
                    for code in (
                        RejectCode.RUNTIME_IDENTITY_INCOMPLETE,
                        RejectCode.PACKAGE_COMPONENT_UNPROVEN,
                    ):
                        add(
                            code,
                            f"runtime_slots.{slot}.{link}",
                            desired["intended_source"],
                            seen[key],
                        )
                    break
    terminal_issue = terminal_enum_coverage(binding, [receipt["terminal_state"]])
    if terminal_issue:
        issues.append(replace(terminal_issue, severity=severity))
    return issues


def requires_target_binding(record: Mapping[str, Any]) -> bool:
    binding = record.get("target_binding") or {}
    return record.get("status", "active") == "active" and bool(
        record.get("spine")
        or record.get("critical_seam")
        or binding.get("runtime_chain_required")
    )


def classify_fixture_provenance(record: Mapping[str, Any]) -> PromotionIssue | None:
    binding = record.get("target_binding") or {}
    entries = binding.get("fixture_provenance", [])
    if not entries:
        return None
    context = record.get("_comparison", {})
    if "real_producer_boundaries" not in context:
        raise ValueError("real_producer_boundaries comparison input is required")
    real_boundaries = set(context["real_producer_boundaries"])
    for entry in entries:
        if entry.get("kind") not in {
            "none",
            "real-source",
            "recorded",
            "constructed",
            "stub",
            "mock",
        }:
            raise ValueError("invalid typed fixture provenance")
        if entry.get("boundary") in real_boundaries and entry.get("kind") not in {
            "none",
            "real-source",
        }:
            return _issue(
                RejectCode.FIXTURE_PROVENANCE_CEILING,
                entry["boundary"],
                "real-source",
                entry,
                "UNSUPPORTED_ORIGIN",
            )
    return None


def terminal_enum_coverage(
    binding: Mapping[str, Any], reachable_states: Sequence[str]
) -> PromotionIssue | None:
    accepted = set(binding["terminal_oracle"]["accepted_states"])
    missing = sorted(set(reachable_states) - accepted)
    if not missing:
        return None
    issue = _issue(
        RejectCode.TERMINAL_ENUM_UNCOVERED,
        "terminal_oracle.accepted_states",
        sorted(accepted),
        sorted(set(reachable_states)),
    )
    return replace(issue, observed={**issue.observed, "uncovered_states": missing})


def diagnose(
    issue: PromotionIssue, record: Mapping[str, Any]
) -> RejectionDiagnostic:
    path = (record.get("target_binding") or {}).get("path_id", record["test_id"])
    recovery = {
        "PROOF_CALLER_MISMATCH": f"Re-run {path} with the bound caller and trusted runner observation.",
        "PROOF_PATH_MISMATCH": f"Re-run the intended path {path} and present the new runner receipt.",
        "PROOF_AUTHORITY_ROLE_MISMATCH": f"Re-run {path} through the declared authority and capture its role.",
        "RUNTIME_IDENTITY_INCOMPLETE": f"Obtain a complete fresh runtime join for {path} and re-run the intended target.",
        "PACKAGE_COMPONENT_UNPROVEN": f"Activate the declared package for every required process on {path}, then capture a fresh join.",
        "FIXTURE_PROVENANCE_CEILING": f"Re-run {path} with the real producer at the named boundary.",
        "TERMINAL_ENUM_UNCOVERED": f"Cover every named reachable state in the terminal oracle for {path}, then re-run.",
    }.get(
        issue.code,
        f"Re-run {path} with the declared outcome and exact producer/consumer contracts.",
    )
    return RejectionDiagnostic(
        code=issue.code,
        message=issue.message,
        test_id=str(record["test_id"]),
        obligation_id=str(record["tmr_uid"]),
        expected=deepcopy(issue.expected),
        observed=deepcopy(issue.observed),
        evidence_class=issue.evidence_class,
        next_actor="worker",
        permitted_recovery=[recovery],
    )


def evaluate_phase8_close(
    records: Sequence[Mapping[str, Any]],
    *,
    now: datetime | str | None = None,
    cutover_mode: str = "legacy",
    comparison_contexts: Mapping[str, Any] | None = None,
) -> Phase8PromotionReport:
    if cutover_mode not in {"legacy", "warn", "reject"}:
        raise ValueError("unsupported enforcement mode")
    contexts = comparison_contexts or {}
    issues: list[PromotionIssue] = []
    for record in records:
        uid = str(record["tmr_uid"])
        context = contexts.get(uid, {})
        capture = context.get("capture")
        evidence = capture.get("run_evidence") if capture else None
        if cutover_mode == "legacy" and not context:
            evidence = record.get("run_evidence")
        real = _is_real_critical_or_spine(record)
        local: list[PromotionIssue] = []
        if real:
            if not _accessors(record) or record.get("binding_status") != "bound":
                local.append(
                    PromotionIssue(
                        code="unbound_accessor_halt",
                        tmr_uid=uid,
                        message="Unbound accessors halt Phase 8 close.",
                        severity="halt",
                    )
                )
            if not _has_negative_oracle(record):
                local.append(
                    PromotionIssue(
                        code="negative_oracle_missing",
                        tmr_uid=uid,
                        message="REAL-DATA promotion requires a negative oracle.",
                        severity="failing",
                    )
                )
            if record.get("test_strategy") == "spike" or record.get(
                "verification_mode"
            ) in EXEMPT_VERIFICATION_MODES:
                local.append(
                    PromotionIssue(
                        code="spine_critical_exempt",
                        tmr_uid=uid,
                        message="Critical or spine tests cannot close as exempt.",
                        severity="failing",
                    )
                )
            if evidence:
                for condition, code in (
                    (evidence.get("result") != "pass", "run_evidence_not_green"),
                    (evidence.get("runner") != "skill-runner", "untrusted_run_evidence"),
                    (
                        evidence.get("env") in CRITICAL_NON_LIVE_ENVS
                        and not evidence.get("live_or_induced"),
                        "real_pass_technique_missing",
                    ),
                ):
                    if condition:
                        local.append(
                            PromotionIssue(
                                code=code,
                                tmr_uid=uid,
                                message="Existing runner evidence requirements are not satisfied.",
                                severity="failing",
                            )
                        )
            elif cutover_mode == "legacy":
                local.append(
                    PromotionIssue(
                        code="run_evidence_missing",
                        tmr_uid=uid,
                        message="Required run evidence is absent.",
                        severity="failing",
                    )
                )
            lint = _lint_boundary_mock(record)
            if lint:
                local.append(lint)
        if requires_target_binding(record) and cutover_mode != "legacy":
            binding = {
                **(record.get("target_binding") or {}),
                "_comparison": context.get("expected", {}),
            }
            observation = (
                None
                if capture is None
                else {**capture, "_comparison": context.get("observed", {})}
            )
            local.extend(
                compare_target_observation(
                    binding, observation, now=now, cutover_mode=cutover_mode
                )
            )
            fixture = classify_fixture_provenance(
                {**record, "_comparison": context.get("expected", {})}
            )
            terminal = (
                terminal_enum_coverage(
                    binding, context.get("reachable_states", [])
                )
                if binding.get("terminal_oracle")
                else None
            )
            for issue in (fixture, terminal):
                if issue:
                    local.append(
                        replace(
                            issue,
                            severity="warning" if cutover_mode == "warn" else "halt",
                        )
                    )
        issues.extend(replace(issue, tmr_uid=uid) for issue in local)
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
        message="Text mentions mock; inspect typed provenance for the actual boundary classification.",
        severity="advisory",
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
