"""C-OBS-CAPTURE A/B oracle: |T| = |O| = 7, no parametrized expansion.

AB_TARGET_ROOT selects candidate code; AB_CONTROL=good|bad calibrates controls.
All child processes and temporary files belong to this leaf. No network, live
skill, git executable, main-worktree fallback, or platform skips.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import queue
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from functools import cache
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

SUITE_DIR = Path(__file__).resolve().parent
IDENTITY_FIELDS = ("outcome_id", "caller_id", "path_id")
HASH_PRODUCER = "sha256:" + hashlib.sha256(b"child-stdout-v1").hexdigest()
HASH_CONSUMER = "sha256:" + hashlib.sha256(b"child-json-v1").hexdigest()
CHILD_CODE = """
import hashlib, json, os, sys
print(json.dumps({
    "pid": os.getpid(), "cwd": os.getcwd(), "nonce": os.environ["AB_CAPTURE_NONCE"],
    "entrypoint_observed": os.path.realpath(sys.executable) + ":-c",
    "authority_ref_observed": "AUTH-CHILD",
    "producer_contract_hash": "sha256:" + hashlib.sha256(b"child-stdout-v1").hexdigest(),
    "consumer_contract_hash": "sha256:" + hashlib.sha256(b"child-json-v1").hexdigest(),
    "terminal_state": "completed" if os.environ["AB_CAPTURE_EXIT"] == "0" else "rejected",
}), flush=True)
input()
sys.exit(int(os.environ["AB_CAPTURE_EXIT"]))
"""


def _module(name, path):
    if not path.is_file():
        raise ModuleNotFoundError(f"AB target module missing: {path}", name=name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@cache
def _contract():
    control = os.environ.get("AB_CONTROL")
    if control in {"good", "bad"}:
        contract = _module(f"_ab_obs_{control}", SUITE_DIR / "ab_controls" / f"{control}_contract.py").MODULE
    else:
        if control:
            raise ValueError(f"Unknown AB_CONTROL: {control!r}")
        if not os.environ.get("AB_TARGET_ROOT"):
            raise ValueError("Set AB_TARGET_ROOT to the candidate checkout; no main-tree fallback")
        scripts = Path(os.environ["AB_TARGET_ROOT"]).resolve() / "skills/adversarial-spec/scripts"
        package = ModuleType("_ab_obs_candidate")
        package.__path__ = [str(scripts)]
        sys.modules[package.__name__] = package
        # Explicit schema path prevents a preloaded/main-tree schema satisfying E-31.
        schema = _module(f"{package.__name__}.tmr_schema", scripts / "tmr_schema.py")
        sys.modules["tmr_schema"] = schema
        sys.path.insert(0, str(scripts))
        promotion = _module(f"{package.__name__}.phase8_promotion", scripts / "phase8_promotion.py")
        contract = SimpleNamespace(phase8_promotion=promotion, tmr_schema=schema)
    supports_observation = "target_observation" in contract.phase8_promotion.RunExecution.__dataclass_fields__
    assert supports_observation, (
        "C-OBS-CAPTURE missing runner-produced RunExecution.target_observation"
    )
    return contract


@pytest.fixture
def workspace():
    with tempfile.TemporaryDirectory(prefix=".ab-obs-run-", dir=SUITE_DIR) as directory:
        yield Path(directory)


def _utc(value):
    assert isinstance(value, str) and value
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0
    return parsed


def _proc_reference(pid, *, self_path=False):
    """Independent host oracle: field 22 after comm, divided by CLK_TCK + btime."""
    if sys.platform != "linux":
        return None
    path = Path("/proc/self/stat") if self_path else Path(f"/proc/{pid}/stat")
    try:
        stat = path.read_text(encoding="utf-8")
        assert int(stat.split(" ", 1)[0]) == pid
        # Index 19 in fields 3..52 is absolute field 22, starttime.
        ticks = int(stat[stat.rfind(")") + 2:].split()[19])
        hz = os.sysconf("SC_CLK_TCK")
        boot_rows = [line for line in Path("/proc/stat").read_text().splitlines() if line.startswith("btime ")]
        boot = int(boot_rows[0].split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return boot + ticks / hz, 1 / hz


def _request(api, workspace, *, suffix="ONE"):
    binding = {
        "binding_version": 1, "outcome_id": f"OUTCOME-{suffix}",
        "caller_id": f"CALLER-{suffix}", "caller_kind": "harness",
        "path_id": f"PATH-{suffix}",
        "entrypoint": str(Path(sys.executable).resolve()) + ":-c",
        "authority_ref": "AUTH-CHILD", "authority_role": "authoritative",
        "producer_contract": {"owner": "suite", "name": "stdout", "version": "1", "source_ref": "local-child", "sha256": HASH_PRODUCER},
        "consumer_contract": {"owner": "suite", "name": "json", "version": "1", "source_ref": "local-child", "sha256": HASH_CONSUMER},
        "runtime_chain_required": True, "runtime_slots": ["PROC-CHILD"],
        "terminal_oracle": {"accepted_states": ["completed", "rejected"], "reconciliation_authority": "suite"},
    }
    return api.PromotionRequest(
        tmr_uid=f"TMR-CAPTURE-{suffix}", test_id="TC-5.0", user_story="US-5",
        command=shlex.join([sys.executable, "-B", "-c", CHILD_CODE]),
        cwd=str(workspace), repo="local-ab-proof",
        commit="36dafdd02b467800148b85704b33bcbe15d01979" if suffix == "ONE" else "94d5dafceb62e2bdc2ba64607eea6678df4665df",
        accessors=["phase8_promotion.capture_run_evidence"], target_binding=binding,
    )


def _runner(api, workspace, calls, *, exit_code=0, alter=None):
    """Trusted callback executes the exact request and samples its live child.

    Only alter= cases induce a partial transport receipt; command/PID/procfs
    remain real. Owner data never reaches the receipt construction below.
    """
    def run(request):
        started = datetime.now(timezone.utc).isoformat()
        nonce = uuid.uuid4().hex
        child_env = {"AB_CAPTURE_NONCE": nonce, "AB_CAPTURE_EXIT": str(exit_code)}
        if "SystemRoot" in os.environ:
            child_env["SystemRoot"] = os.environ["SystemRoot"]
        with subprocess.Popen(
            shlex.split(request.command), cwd=request.cwd, env=child_env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ) as process:
            try:
                lines = queue.Queue()
                reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
                reader.start()
                line = lines.get(timeout=10)
                reader.join(timeout=1)
                observed = json.loads(line)
                assert observed["pid"] == process.pid
                assert observed["cwd"] == str(workspace)
                assert observed["nonce"] == nonce
                reference = _proc_reference(process.pid)
                start_time = api.read_process_start_time(process.pid)
                if reference is None:
                    assert start_time is None
                else:
                    assert abs(_utc(start_time).timestamp() - reference[0]) <= reference[1]
                _, stderr = process.communicate("\n", timeout=10)
                assert stderr == "" and process.returncode == exit_code
            finally:
                if process.poll() is None:
                    process.kill()  # This exact child only; no global process cleanup.
                    process.communicate(timeout=10)
        artifact = workspace / f"{nonce}.json"
        artifact.write_text(line, encoding="utf-8")
        observation = {
            "runtime_receipt_id": "runner-" + uuid.uuid4().hex,
            "pid": observed["pid"], "pid_start_time": start_time,
            **{key: request.target_binding[key] for key in IDENTITY_FIELDS},
            **{key: observed[key] for key in (
                "entrypoint_observed", "authority_ref_observed", "producer_contract_hash",
                "consumer_contract_hash", "terminal_state",
            )},
        }
        supplied = alter(copy.deepcopy(observation)) if alter is not None else observation
        execution = api.RunExecution(
            exit_code=process.returncode, started_at=started,
            finished_at=datetime.now(timezone.utc).isoformat(),
            artifact_uri=artifact.as_uri(),
            artifact_sha256="sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest(),
            live_or_induced={"kind": "other", "detail": "real local Python child; procfs sampled before stdin release"},
            target_observation=supplied,
        )
        calls.append({"request": request, "execution": execution, "observed": observation, "reference": reference, "artifact": artifact})
        return execution
    return run


def _incomplete(capture, *, field):
    assert capture["capture_state"] == "INCOMPLETE"
    assert capture["observation_source"] == "runner"
    assert capture["run_evidence"] is None, "absent/partial E-12 receipts carry no result"
    assert "result" not in capture
    receipt = capture["runtime_receipt"]
    assert receipt is None or "result" not in receipt
    assert any(issue["code"] == "RUNTIME_IDENTITY_INCOMPLETE" and issue["field"] == field for issue in capture["issues"])


def _assert_execution(contract, capture, call, request, *, result, ignored=False):
    assert capture["owner_observation_ignored"] is ignored
    assert capture["observation_source"] == "runner"
    assert capture["target_ref"] == request.commit
    assert _utc(capture["captured_at"]) >= _utc(call["execution"].finished_at)
    expected = copy.deepcopy(call["execution"].target_observation)
    expected.update({key: request.target_binding[key] for key in IDENTITY_FIELDS})
    assert capture["runtime_receipt"] == expected
    if call["reference"] is None:
        assert capture["runtime_receipt"]["pid_start_time"] is None
        _incomplete(capture, field="pid_start_time")
        return
    assert capture["capture_state"] == "COMPLETE" and capture["issues"] == []
    evidence = capture["run_evidence"]
    schema = contract.tmr_schema
    parsed = schema.CodeRunEvidence.model_validate(evidence)
    assert parsed.target_observation is not None
    assert schema.TargetObservation.model_validate(expected).model_dump(mode="json") == evidence["target_observation"]
    assert parsed.model_dump(mode="json") == evidence
    assert evidence["target_observation"] == expected
    assert evidence["result"] == result
    assert evidence["exit"] == call["execution"].exit_code
    assert evidence["command"] == request.command and evidence["cwd"] == request.cwd
    assert evidence["repo"] == request.repo and evidence["commit"] == request.commit
    assert evidence["env"] == "ci" and evidence["runner"] == "skill-runner"
    for field in ("started_at", "finished_at", "artifact_uri", "artifact_sha256", "live_or_induced"):
        assert evidence[field] == getattr(call["execution"], field)
    assert evidence["artifact_sha256"] == "sha256:" + hashlib.sha256(call["artifact"].read_bytes()).hexdigest()


def test_o1_real_command_populates_schema_valid_runner_evidence(workspace):
    contract = _contract()
    api = contract.phase8_promotion
    request = _request(api, workspace)
    calls = []
    before = datetime.now(timezone.utc)
    capture = api.capture_run_evidence(request, runner=_runner(api, workspace, calls), env="ci")
    after = datetime.now(timezone.utc)
    assert len(calls) == 1 and calls[0]["request"] is request
    assert before <= _utc(capture["captured_at"]) <= after
    _assert_execution(contract, capture, calls[0], request, result="pass")


def test_o2_owner_observations_and_results_cannot_override_runner(workspace):
    contract = _contract()
    api = contract.phase8_promotion
    for channel in ("record", "argument", "owner_written_result"):
        for exit_code, owner_result in ((0, "fail"), (7, "pass")):
            request = _request(api, workspace)
            forged = {
                "runtime_receipt_id": "owner-forged", "pid": os.getpid(),
                "pid_start_time": "2000-01-01T00:00:00Z", "observation_source": "runner",
                **{key: "OWNER-FORGED" for key in IDENTITY_FIELDS},
                "entrypoint_observed": "owner.py", "authority_ref_observed": "AUTH-OWNER",
                "producer_contract_hash": "sha256:" + "a" * 64,
                "consumer_contract_hash": "sha256:" + "b" * 64, "terminal_state": "completed",
            }
            original = copy.deepcopy(forged)
            kwargs = {"owner_written_result": owner_result}
            if channel == "record":
                request = SimpleNamespace(**asdict(request), target_observation=forged, run_evidence={"target_observation": forged, "result": owner_result})
            elif channel == "argument":
                kwargs["owner_written_observation"] = forged
            else:
                kwargs["owner_written_result"] = {"result": owner_result, "target_observation": forged}
            calls = []
            capture = api.capture_run_evidence(request, runner=_runner(api, workspace, calls, exit_code=exit_code), env="ci", **kwargs)
            assert len(calls) == 1 and forged == original
            _assert_execution(contract, capture, calls[0], request, result="pass" if exit_code == 0 else "fail", ignored=True)
            snapshot = copy.deepcopy(capture)
            calls[0]["execution"].target_observation["runtime_receipt_id"] = "mutated-after-return"
            forged["pid"] = -1
            assert capture == snapshot, "capture must detach its receipt from mutable caller/callback inputs"


def test_o3_missing_runner_receipt_discards_owner_observation(workspace):
    contract = _contract()
    api = contract.phase8_promotion
    request = _request(api, workspace)
    owner = {"pid": os.getpid(), "terminal_state": "completed", "observation_source": "runner"}
    record = SimpleNamespace(**asdict(request), run_evidence={"target_observation": owner, "result": "pass"})
    for alter in (
        lambda observation: None,
        lambda observation: {key: value for key, value in observation.items() if key != "runtime_receipt_id"},
        lambda observation: {**observation, "runtime_receipt_id": None},
        lambda observation: {**observation, "runtime_receipt_id": ""},
    ):
        calls = []
        capture = api.capture_run_evidence(record, runner=_runner(api, workspace, calls, alter=alter), env="ci", owner_written_result="pass")
        assert len(calls) == 1 and capture["owner_observation_ignored"] is True
        _incomplete(capture, field="runtime_receipt_id")
        assert capture["runtime_receipt"] is None or not capture["runtime_receipt"].get("runtime_receipt_id")
    # Even an owner-supplied receipt ID must not repair a missing runner receipt.
    owner["runtime_receipt_id"] = "owner-forged"
    capture = api.capture_run_evidence(record, runner=_runner(api, workspace, [], alter=lambda observation: None), env="ci")
    _incomplete(capture, field="runtime_receipt_id")
    assert capture["runtime_receipt"] is None
    calls = []
    rerun = api.capture_run_evidence(record, runner=_runner(api, workspace, calls), env="ci")
    _assert_execution(contract, rerun, calls[0], record, result="pass", ignored=True)
    assert rerun["runtime_receipt"]["runtime_receipt_id"] != owner["runtime_receipt_id"]


def test_o4_process_start_time_matches_real_procfs_conversion(workspace):
    contract = _contract()
    api = contract.phase8_promotion
    pid = os.getpid()
    reference = _proc_reference(pid, self_path=True)
    actual = api.read_process_start_time(pid)
    if reference is not None:
        assert abs(_utc(actual).timestamp() - reference[0]) <= reference[1]
        assert _utc(actual) <= datetime.now(timezone.utc)
    else:
        assert actual is None
        calls = []
        capture = api.capture_run_evidence(_request(api, workspace), runner=_runner(api, workspace, calls), env="ci")
        assert capture["runtime_receipt"]["pid_start_time"] is None
        _incomplete(capture, field="pid_start_time")


def test_o5_restarted_real_process_gets_new_start_time_and_receipt(workspace):
    contract = _contract()
    api = contract.phase8_promotion
    request = _request(api, workspace)
    calls, captures = [], []
    for index in range(2):
        if index:
            hz = os.sysconf("SC_CLK_TCK") if sys.platform == "linux" else 100
            time.sleep(max(2 / hz, 0.03))
        captures.append(api.capture_run_evidence(request, runner=_runner(api, workspace, calls), env="ci"))
        _assert_execution(contract, captures[-1], calls[-1], request, result="pass")
    first, second = [capture["runtime_receipt"] for capture in captures]
    assert first["runtime_receipt_id"] != second["runtime_receipt_id"]
    assert first["pid"] == calls[0]["observed"]["pid"] and second["pid"] == calls[1]["observed"]["pid"]
    if all(call["reference"] is not None for call in calls):
        assert _utc(second["pid_start_time"]) > _utc(first["pid_start_time"])
        assert (first["pid"], first["pid_start_time"]) != (second["pid"], second["pid_start_time"])
    else:
        for capture, call in zip(captures, calls, strict=True):
            if call["reference"] is None:
                _incomplete(capture, field="pid_start_time")


def test_o6_unavailable_or_partial_identity_carries_no_result(workspace, monkeypatch):
    contract = _contract()
    api = contract.phase8_promotion
    # Exercise the actual branch on non-Linux; induce that branch on Linux too.
    with monkeypatch.context() as patch:
        patch.setattr(sys, "platform", "darwin")
        assert api.read_process_start_time(os.getpid()) is None
        capture = api.capture_run_evidence(_request(api, workspace), runner=_runner(api, workspace, []), env="ci")
        assert capture["runtime_receipt"]["pid_start_time"] is None
        _incomplete(capture, field="pid_start_time")
    assert api.read_process_start_time(0) is None
    assert api.read_process_start_time(-1) is None
    assert api.read_process_start_time(2**62) is None
    rows = (
        ("pid", None), ("pid", True), ("pid", -1), ("pid_start_time", None),
        ("pid_start_time", "bad-time"), ("pid_start_time", "2026-09-15T12:00:00"),
        ("entrypoint_observed", ""), ("authority_ref_observed", None),
        ("producer_contract_hash", "not-a-hash"), ("consumer_contract_hash", "not-a-hash"),
        ("terminal_state", None), ("terminal_state", "partial"), ("terminal_state", "timeout"),
    )
    for field, value in rows:
        calls = []
        capture = api.capture_run_evidence(
            _request(api, workspace), env="ci", owner_written_result="pass",
            runner=_runner(api, workspace, calls, alter=lambda observation: {**observation, field: value}),
        )
        # On hosts lacking procfs, that real identity gap may precede later gaps.
        expected_field = "pid_start_time" if calls[0]["reference"] is None and field != "pid" else field
        _incomplete(capture, field=expected_field)
        assert capture["runtime_receipt"][field] == value


def test_o7_binding_labels_and_actual_runner_reports_keep_their_provenance(workspace):
    contract = _contract()
    api = contract.phase8_promotion
    for suffix in ("ONE", "TWO"):
        request = _request(api, workspace, suffix=suffix)
        request.target_binding.update({"entrypoint": "bound-but-not-executed.py", "authority_ref": "AUTH-EXPECTED"})
        request.target_binding["producer_contract"]["sha256"] = "sha256:" + "a" * 64
        request.target_binding["consumer_contract"]["sha256"] = "sha256:" + "b" * 64
        # The three intended labels come from this binding, even if the callback
        # also supplies stale labels. Actual entrypoint/authority/hash reports do not.
        calls = []
        capture = api.capture_run_evidence(
            request, env="ci",
            runner=_runner(api, workspace, calls, alter=lambda observation: {**observation, **{key: "STALE-LABEL" for key in IDENTITY_FIELDS}}),
        )
        _assert_execution(contract, capture, calls[0], request, result="pass")
        observation = capture["runtime_receipt"]
        assert {key: observation[key] for key in IDENTITY_FIELDS} == {key: request.target_binding[key] for key in IDENTITY_FIELDS}
        assert observation["entrypoint_observed"] == str(Path(sys.executable).resolve()) + ":-c"
        assert observation["authority_ref_observed"] == "AUTH-CHILD"
        assert observation["producer_contract_hash"] == HASH_PRODUCER
        assert observation["consumer_contract_hash"] == HASH_CONSUMER
        assert observation["terminal_state"] == "completed"
        assert not any(issue["code"].startswith("PROOF_") for issue in capture["issues"])
