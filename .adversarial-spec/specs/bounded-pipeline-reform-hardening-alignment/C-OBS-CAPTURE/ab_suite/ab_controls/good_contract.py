"""A.5 self-contained good control; no product or oracle imports.

The two small Pydantic models mirror the consumed E-31 surface. The suite also
calibrates this producer against the exact frozen schema in a temporary target.
This file is a control, not an implementation delivered to the live skill.
"""
from __future__ import annotations

import copy
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


StableId = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_-]{2,127}$")]
Sha256Hash = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class TargetObservation(StrictModel):
    runtime_receipt_id: str
    pid: int
    pid_start_time: str
    outcome_id: StableId
    caller_id: StableId
    path_id: StableId
    entrypoint_observed: str
    authority_ref_observed: StableId
    producer_contract_hash: Sha256Hash
    consumer_contract_hash: Sha256Hash
    terminal_state: str


class LiveOrInducedTechnique(StrictModel):
    kind: Literal["other"]
    detail: str


class CodeRunEvidence(StrictModel):
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
    target_observation: TargetObservation | None = None


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


@dataclass(frozen=True)
class RunExecution:
    exit_code: int
    started_at: str
    finished_at: str
    artifact_uri: str
    artifact_sha256: str
    live_or_induced: dict[str, str] | None = None
    target_observation: dict[str, Any] | None = None


def read_process_start_time(pid: int) -> str | None:
    if sys.platform != "linux" or type(pid) is not int or pid <= 0:
        return None
    try:
        # comm (field 2) can itself contain spaces and parentheses.
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        ticks = int(stat.rsplit(")", 1)[1].split()[19])
        clock_ticks = os.sysconf("SC_CLK_TCK")
        boot = next(
            int(line.split()[1])
            for line in Path("/proc/stat").read_text(encoding="utf-8").splitlines()
            if line.startswith("btime ")
        )
        return datetime.fromtimestamp(boot + ticks / clock_ticks, timezone.utc).isoformat()
    except (OSError, ValueError, IndexError, StopIteration, OverflowError):
        return None


def capture_run_evidence(
    request, *, runner, env, owner_written_result=None, owner_written_observation=None,
) -> dict[str, Any]:
    """Return the TargetObservationCapture dict shape fixed by this package."""
    ignored = owner_written_observation is not None
    ignored |= getattr(request, "target_observation", None) is not None
    record_evidence = getattr(request, "run_evidence", None)
    ignored |= isinstance(record_evidence, dict) and record_evidence.get("target_observation") is not None
    if isinstance(owner_written_result, dict):
        ignored |= owner_written_result.get("target_observation") is not None
    execution = runner(request)
    captured_at = datetime.now(timezone.utc).isoformat()
    raw = copy.deepcopy(execution.target_observation)
    capture = {
        "capture_state": "INCOMPLETE",
        "observation_source": "runner",
        "owner_observation_ignored": bool(ignored),
        "captured_at": captured_at,
        "target_ref": request.commit,
        "runtime_receipt": raw,
        "run_evidence": None,
        "issues": [],
    }

    def incomplete(field):
        capture["issues"].append({"code": "RUNTIME_IDENTITY_INCOMPLETE", "field": field})
        return capture

    if raw is None:
        return incomplete("runtime_receipt_id")
    binding = request.target_binding or {}
    for name in ("outcome_id", "caller_id", "path_id"):
        raw[name] = binding.get(name)
    if not raw.get("runtime_receipt_id"):
        return incomplete("runtime_receipt_id")
    if type(raw.get("pid")) is not int or raw["pid"] <= 0:
        return incomplete("pid")
    # Identity gaps must not acquire a pass just because the process exited 0.
    for name in (
        "runtime_receipt_id", "pid", "pid_start_time", "outcome_id", "caller_id",
        "path_id", "entrypoint_observed", "authority_ref_observed",
        "producer_contract_hash", "consumer_contract_hash", "terminal_state",
    ):
        if raw.get(name) is None or raw.get(name) == "":
            return incomplete(name)
    try:
        start = datetime.fromisoformat(raw["pid_start_time"].replace("Z", "+00:00"))
        if start.utcoffset() is None or start.utcoffset().total_seconds() != 0:
            return incomplete("pid_start_time")
    except (TypeError, ValueError, AttributeError):
        return incomplete("pid_start_time")
    if raw["terminal_state"] in {"partial", "timeout"}:
        return incomplete("terminal_state")
    try:
        observation = TargetObservation.model_validate(raw).model_dump(mode="json")
    except ValidationError as exc:
        return incomplete(str(exc.errors()[0]["loc"][0]))
    evidence = {
        "tier": "code", "command": request.command, "cwd": request.cwd,
        "repo": request.repo, "commit": request.commit,
        "started_at": execution.started_at, "finished_at": execution.finished_at,
        "exit": execution.exit_code,
        "result": "pass" if execution.exit_code == 0 else "fail", "env": env,
        "artifact_uri": execution.artifact_uri, "artifact_sha256": execution.artifact_sha256,
        "runner": "skill-runner", "live_or_induced": execution.live_or_induced,
        "target_observation": observation,
    }
    capture["run_evidence"] = CodeRunEvidence.model_validate(evidence).model_dump(mode="json")
    capture["capture_state"] = "COMPLETE"
    return capture


MODULE = SimpleNamespace(phase8_promotion=sys.modules[__name__], tmr_schema=sys.modules[__name__])
