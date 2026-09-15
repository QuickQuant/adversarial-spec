"""A.5 self-contained control, not product implementation.

No product/candidate/oracle imports. Small E-2 models validate the consumed
shape; adapter calibration additionally uses the exact frozen TMR schema.
The comparison sidecars are pure supplied facts, never live evidence claims.
"""
from __future__ import annotations

import copy
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TargetObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
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


class CodeRunEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
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
    live_or_induced: dict | None
    target_observation: TargetObservation | None = None


class TestMaturityRecord(BaseModel):
    # Only the consumed subset; exact-schema calibration prevents adapter drift.
    model_config = ConfigDict(extra="allow", strict=True)
    tmr_uid: str
    test_id: str
    target_binding: dict | None
    target_binding_status: Literal["bound", "legacy-unbound"]
    run_evidence: CodeRunEvidence | None


class RejectCode(StrEnum):
    PROOF_OUTCOME_MISMATCH = "PROOF_OUTCOME_MISMATCH"
    PROOF_CALLER_MISMATCH = "PROOF_CALLER_MISMATCH"
    PROOF_PATH_MISMATCH = "PROOF_PATH_MISMATCH"
    PROOF_AUTHORITY_ROLE_MISMATCH = "PROOF_AUTHORITY_ROLE_MISMATCH"
    PRODUCER_CONSUMER_CONTRACT_UNPROVEN = "PRODUCER_CONSUMER_CONTRACT_UNPROVEN"
    RUNTIME_IDENTITY_INCOMPLETE = "RUNTIME_IDENTITY_INCOMPLETE"
    PACKAGE_COMPONENT_UNPROVEN = "PACKAGE_COMPONENT_UNPROVEN"
    FIXTURE_PROVENANCE_CEILING = "FIXTURE_PROVENANCE_CEILING"
    TERMINAL_ENUM_UNCOVERED = "TERMINAL_ENUM_UNCOVERED"


EnforcementMode = Literal["legacy", "warn", "reject"]
FRESHNESS_WINDOW_SECONDS = 86400


def _utc(value):
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(parsed, datetime) or parsed.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed.astimezone(timezone.utc)


def is_receipt_fresh(receipt_captured_at, now, *, target_ref_at_capture, target_ref_now):
    return target_ref_at_capture == target_ref_now and (
        timedelta(0) <= _utc(now) - _utc(receipt_captured_at) <= timedelta(seconds=FRESHNESS_WINDOW_SECONDS)
    )


@dataclass(frozen=True)
class PromotionIssue:
    code: str
    tmr_uid: str
    message: str
    severity: str = "failing"
    expected: dict = field(default_factory=dict)
    observed: dict = field(default_factory=dict)
    evidence_class: str = "MISMATCH"


@dataclass(frozen=True)
class RejectionDiagnostic:
    code: str
    message: str
    test_id: str
    obligation_id: str
    expected: dict
    observed: dict
    evidence_class: str
    next_actor: str
    permitted_recovery: list[str]


@dataclass
class Phase8PromotionReport:
    requests: list = field(default_factory=list)
    issues: list[PromotionIssue] = field(default_factory=list)

    @property
    def can_close(self):
        return not any(i.severity in {"halt", "failing"} for i in self.issues)


def _issue(code, field_name, expected, observed, evidence_class="MISMATCH", *, severity="halt"):
    return PromotionIssue(
        str(code), "", f"Evidence for {field_name} cannot discharge the declared obligation: "
        f"expected {expected!r}; observed {observed!r}.", severity,
        {"field": field_name, "value": copy.deepcopy(expected)},
        {"field": field_name, "value": copy.deepcopy(observed)}, evidence_class,
    )


def compare_target_observation(binding, observation, *, now, cutover_mode):
    if cutover_mode not in {"legacy", "warn", "reject"}:
        raise ValueError("unsupported enforcement mode")
    if cutover_mode == "legacy":
        return []
    severity = "warning" if cutover_mode == "warn" else "halt"
    issues = []

    def add(code, name, expected, actual, category="MISMATCH"):
        issues.append(_issue(code, name, expected, actual, category, severity=severity))

    def incomplete(name, actual=None, category="MISSING"):
        add(RejectCode.RUNTIME_IDENTITY_INCOMPLETE, name, "complete trusted runner evidence", actual, category)
        return issues

    if observation is None:
        return incomplete("target_observation")
    if observation.get("observation_source") != "runner":
        return incomplete("observation_source", observation.get("observation_source"), "UNSUPPORTED_ORIGIN")
    if observation.get("capture_state") != "COMPLETE":
        return incomplete("capture_state", observation.get("capture_state"))
    receipt = observation.get("runtime_receipt")
    evidence = observation.get("run_evidence")
    if not isinstance(receipt, dict) or not isinstance(evidence, dict):
        return incomplete("runtime_receipt")
    if receipt != evidence.get("target_observation"):
        return incomplete("run_evidence.target_observation", evidence.get("target_observation"), "UNSUPPORTED_ORIGIN")
    for key in TargetObservation.model_fields:
        if receipt.get(key) is None or receipt.get(key) == "":
            return incomplete(key)
    if type(receipt["pid"]) is not int or receipt["pid"] <= 0:
        return incomplete("pid", receipt["pid"])
    try:
        _utc(receipt["pid_start_time"])
        TargetObservation.model_validate(receipt)
    except (ValueError, TypeError):
        return incomplete("runtime_receipt", receipt)
    expected = binding.get("_comparison", {})
    actual = observation.get("_comparison", {})
    for key in ("caller_id_observed", "caller_kind_observed", "path_id_observed", "authority_role_observed"):
        if not actual.get(key):
            return incomplete(key)
    for name, value in (("captured_at", observation.get("captured_at")),
                        ("target_ref_at_capture", observation.get("target_ref")),
                        ("target_ref_now", expected.get("target_ref"))):
        if not value:
            return incomplete(name)
    try:
        fresh = is_receipt_fresh(observation["captured_at"], now,
                                 target_ref_at_capture=observation["target_ref"], target_ref_now=expected["target_ref"])
    except (ValueError, TypeError):
        return incomplete("captured_at", observation.get("captured_at"))
    if not fresh:
        add(RejectCode.RUNTIME_IDENTITY_INCOMPLETE, "receipt_freshness",
            {"target_ref": expected["target_ref"], "now": str(now)},
            {"target_ref": observation["target_ref"], "captured_at": observation["captured_at"]}, "STALE")
    comparisons = (
        (RejectCode.PROOF_OUTCOME_MISMATCH, "outcome_id", binding["outcome_id"], receipt["outcome_id"]),
        (RejectCode.PROOF_CALLER_MISMATCH, "caller", [binding["caller_id"], binding["caller_kind"]],
         [actual["caller_id_observed"], actual["caller_kind_observed"]]),
        (RejectCode.PROOF_PATH_MISMATCH, "path", [binding["path_id"], binding["entrypoint"]],
         [actual["path_id_observed"], receipt["entrypoint_observed"]]),
        (RejectCode.PROOF_AUTHORITY_ROLE_MISMATCH, "authority", [binding["authority_ref"], binding["authority_role"]],
         [receipt["authority_ref_observed"], actual["authority_role_observed"]]),
        (RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN, "contract_hashes",
         [binding["producer_contract"]["sha256"], binding["consumer_contract"]["sha256"]],
         [receipt["producer_contract_hash"], receipt["consumer_contract_hash"]]),
    )
    for code, name, desired, seen in comparisons:
        if desired != seen:
            add(code, name, desired, seen)
    if binding.get("runtime_chain_required"):
        for slot in binding["runtime_slots"]:
            desired = expected.get("runtime_slots", {}).get(slot, {})
            seen = actual.get("runtime_slots", {}).get(slot, {})
            chain = ("packaged_source", "activation_source", "running_source", "gateway_source")
            missing = [k for k in chain if not seen.get(k)]
            if not desired.get("intended_source") or missing:
                for code in (RejectCode.RUNTIME_IDENTITY_INCOMPLETE, RejectCode.PACKAGE_COMPONENT_UNPROVEN):
                    add(code, f"runtime_slots.{slot}", desired, seen, "MISSING")
                continue
            for key in ("pid", "pid_start_time"):
                if not desired.get(key) or not seen.get(key):
                    add(RejectCode.RUNTIME_IDENTITY_INCOMPLETE, f"runtime_slots.{slot}.{key}", desired.get(key), seen.get(key), "MISSING")
                elif desired[key] != seen[key] or (slot == binding["runtime_slots"][0] and receipt[key] != seen[key]):
                    add(RejectCode.RUNTIME_IDENTITY_INCOMPLETE, f"runtime_slots.{slot}.{key}", desired[key], seen[key], "STALE")
            for index, key in enumerate(chain):
                if seen[key] != desired["intended_source"]:
                    link = ("intended_source" if index == 0 else chain[index - 1]) + " -> " + key
                    for code in (RejectCode.RUNTIME_IDENTITY_INCOMPLETE, RejectCode.PACKAGE_COMPONENT_UNPROVEN):
                        add(code, f"runtime_slots.{slot}.{link}", desired["intended_source"], seen[key])
                    break
    terminal_issue = terminal_enum_coverage(binding, [receipt["terminal_state"]])
    if terminal_issue:
        issues.append(replace(terminal_issue, severity=severity))
    return issues


def requires_target_binding(record):
    binding = record.get("target_binding") or {}
    return record.get("status", "active") == "active" and bool(
        record.get("spine") or record.get("critical_seam") or binding.get("runtime_chain_required")
    )


def classify_fixture_provenance(record):
    binding = record.get("target_binding") or {}
    entries = binding.get("fixture_provenance", [])
    if not entries:
        return None
    context = record.get("_comparison", {})
    if "real_producer_boundaries" not in context:
        raise ValueError("real_producer_boundaries comparison input is required")
    real_boundaries = set(context["real_producer_boundaries"])
    for entry in entries:
        if entry["kind"] not in {"none", "real-source", "recorded", "constructed", "stub", "mock"}:
            raise ValueError("invalid typed fixture provenance")
        if entry["boundary"] in real_boundaries and entry["kind"] not in {"none", "real-source"}:
            return _issue(RejectCode.FIXTURE_PROVENANCE_CEILING, entry["boundary"], "real-source", entry, "UNSUPPORTED_ORIGIN")
    return None


def _lint_boundary_mock(record):
    if "mock" in " ".join(str(value).lower() for value in record.values()):
        return PromotionIssue("boundary_mock_detected", str(record["tmr_uid"]),
                              "Text mentions mock; inspect typed provenance for the actual boundary classification.", "advisory")
    return None


def terminal_enum_coverage(binding, reachable_states):
    accepted = set(binding["terminal_oracle"]["accepted_states"])
    missing = sorted(set(reachable_states) - accepted)
    if not missing:
        return None
    issue = _issue(RejectCode.TERMINAL_ENUM_UNCOVERED, "terminal_oracle.accepted_states", sorted(accepted), sorted(set(reachable_states)))
    return replace(issue, observed={**issue.observed, "uncovered_states": missing})


def diagnose(issue, record):
    path = (record.get("target_binding") or {}).get("path_id", record["test_id"])
    recovery = {
        "PROOF_CALLER_MISMATCH": f"Re-run {path} with the bound caller and trusted runner observation.",
        "PROOF_PATH_MISMATCH": f"Re-run the intended path {path} and present the new runner receipt.",
        "PROOF_AUTHORITY_ROLE_MISMATCH": f"Re-run {path} through the declared authority and capture its role.",
        "RUNTIME_IDENTITY_INCOMPLETE": f"Obtain a complete fresh runtime join for {path} and re-run the intended target.",
        "PACKAGE_COMPONENT_UNPROVEN": f"Activate the declared package for every required process on {path}, then capture a fresh join.",
        "FIXTURE_PROVENANCE_CEILING": f"Re-run {path} with the real producer at the named boundary.",
        "TERMINAL_ENUM_UNCOVERED": f"Cover every named reachable state in the terminal oracle for {path}, then re-run.",
    }.get(issue.code, f"Re-run {path} with the declared outcome and exact producer/consumer contracts.")
    return RejectionDiagnostic(issue.code, issue.message, record["test_id"], record["tmr_uid"],
                               copy.deepcopy(issue.expected), copy.deepcopy(issue.observed),
                               issue.evidence_class, "worker", [recovery])


def evaluate_phase8_close(records, *, now=None, cutover_mode="legacy", comparison_contexts=None):
    if cutover_mode not in {"legacy", "warn", "reject"}:
        raise ValueError("unsupported enforcement mode")
    contexts = comparison_contexts or {}
    issues = []
    for record in records:
        uid = str(record["tmr_uid"])
        context = contexts.get(uid, {})
        capture = context.get("capture")
        evidence = capture.get("run_evidence") if capture else None
        if cutover_mode == "legacy" and not context:
            evidence = record.get("run_evidence")
        real = record.get("data_strategy") in {"REAL-DATA", "REAL-DATA + PROPERTY"} and (
            record.get("spine") or record.get("critical_seam")
        )
        local = []
        if real:
            if not record.get("accessors") or record.get("binding_status") != "bound":
                local.append(PromotionIssue("unbound_accessor_halt", uid, "Unbound accessors halt Phase 8 close.", "halt"))
            if record.get("negative_oracle") is not True and not record.get("negative_oracle_ref"):
                local.append(PromotionIssue("negative_oracle_missing", uid, "REAL-DATA promotion requires a negative oracle."))
            if record.get("test_strategy") == "spike" or record.get("verification_mode") in {"artifact-sync", "static-check", "manual-ux"}:
                local.append(PromotionIssue("spine_critical_exempt", uid, "Critical or spine tests cannot close as exempt."))
            if evidence:
                for condition, code in (
                    (evidence.get("result") != "pass", "run_evidence_not_green"),
                    (evidence.get("runner") != "skill-runner", "untrusted_run_evidence"),
                    (evidence.get("env") in {"dev", "ci"} and not evidence.get("live_or_induced"), "real_pass_technique_missing"),
                ):
                    if condition:
                        local.append(PromotionIssue(code, uid, "Existing runner evidence requirements are not satisfied."))
            elif cutover_mode == "legacy":
                local.append(PromotionIssue("run_evidence_missing", uid, "Required run evidence is absent."))
            lint = _lint_boundary_mock(record)
            if lint:
                local.append(lint)
        if requires_target_binding(record) and cutover_mode != "legacy":
            binding = {**(record.get("target_binding") or {}), "_comparison": context.get("expected", {})}
            observation = None if capture is None else {**capture, "_comparison": context.get("observed", {})}
            local.extend(compare_target_observation(binding, observation, now=now, cutover_mode=cutover_mode))
            fixture = classify_fixture_provenance({**record, "_comparison": context.get("expected", {})})
            terminal = terminal_enum_coverage(binding, context.get("reachable_states", [])) if binding.get("terminal_oracle") else None
            for issue in (fixture, terminal):
                if issue:
                    local.append(replace(issue, severity="warning" if cutover_mode == "warn" else "halt"))
        issues.extend(replace(issue, tmr_uid=uid) for issue in local)
    return Phase8PromotionReport(issues=issues)


MODULE = SimpleNamespace(phase8_promotion=sys.modules[__name__], tmr_schema=sys.modules[__name__],
                         gate_policy=sys.modules[__name__])
