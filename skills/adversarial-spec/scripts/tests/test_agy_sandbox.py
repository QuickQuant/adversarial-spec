"""Offline safety suite for the sandboxed Antigravity (agy) critic dispatch.

Contract: .adversarial-spec/specs/agy-tripwire-stop/tests-pseudo.md (v4). Test names cite TC ids.

Harness: real git repos under ~/.cache (never /tmp, which the sandbox masks), the real bwrap sandbox,
and the real dispatch/debate/gauntlet code. Only the critic is replaced: a scripted fake `agy` first on
PATH performs its side effects inside the sandbox, so every write is judged by the real kernel boundary.
Launches are counted by wrapping `subprocess.Popen` (every spawn primitive, `subprocess.run` included,
goes through it), with a monotonic launch time per agy launch.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_BASE = Path.home() / ".cache" / "advspec-agy-tests"
AGY_MODEL = "antigravity/gemini-3.8-flash-high"
AGY_MODEL_B = "antigravity/gemini-3.8-flash-medium"
STATE_DIRNAME = "adversarial-spec-agy"
OVERRIDE = ["--pipeline-card", "IntentionalOverride", "--override-reason",
            "offline agy safety suite: in-process debate.py run against a scripted fake critic"]

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="UNSUPPORTED: bwrap not found; sandbox cases cannot run on this host (TC-0.2 reports this)",
)

FAKE_AGY = r"""#!/usr/bin/env python3
import hashlib, json, os, re, subprocess, sys, time
sys.stderr.write("FAKE_AGY_STARTED\n")
sys.stderr.flush()
args = sys.argv[1:]
prompt = args[args.index("--prompt") + 1] if "--prompt" in args else ""
with open(BEHAVIOR_PATH) as fh:
    spec = json.load(fh)
plan = spec.get("default", {})
for rule in spec.get("rules", []):
    if rule["match"] in prompt:
        plan = rule
        break
out = []
for step in plan.get("steps", []):
    op = step["op"]
    if op == "write":
        path = step["path"]
        try:
            if os.path.dirname(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(step["data"].encode())
            out.append("wrote " + path)
        except OSError as exc:
            sys.stderr.write("write %s failed: %s\n" % (path, exc))
            out.append("blocked " + path)
    elif op == "sleep":
        time.sleep(step["seconds"])
    elif op == "write_prompt":
        m = re.search(r"absolute path (\S+) and", prompt)
        try:
            with open(m.group(1), "wb") as fh:
                fh.write(b"tampered")
            out.append("wrote prompt")
        except OSError as exc:
            sys.stderr.write("write prompt failed: %s\n" % exc)
            out.append("blocked prompt")
    elif op == "read_prompt":
        m = re.search(r"absolute path (\S+) and", prompt)
        data = open(m.group(1), "rb").read() if m else prompt.encode()
        out.append("prompt_sha=" + hashlib.sha256(data).hexdigest())
        out.append("prompt_path=" + (m.group(1) if m else "inline"))
    elif op == "run":
        try:
            r = subprocess.run(step["argv"], capture_output=True, text=True, timeout=20)
            out.append("run %s rc=%d" % (step["argv"][0], r.returncode))
        except (OSError, subprocess.SubprocessError) as exc:
            out.append("run %s rc=127 %s" % (step["argv"][0], type(exc).__name__))
    elif op == "env":
        out.append("env=" + json.dumps(sorted(os.environ)))
    elif op == "exists":
        out.append("exists %s=%s" % (step["path"], os.path.exists(step["path"])))
    elif op == "listdir":
        p = step["path"]
        out.append("listdir=" + json.dumps(sorted(os.listdir(p)) if os.path.isdir(p) else None))
print("\n".join(out + [plan.get("stdout", "fake critique [AGREE]")]))
sys.stdout.flush()
if plan.get("stderr"):
    sys.stderr.write(plan["stderr"] + "\n")
sys.exit(plan.get("exit", 0))
"""

FAKE_CLAUDE = r"""#!/usr/bin/env python3
import sys, time
sys.stdin.read()
time.sleep(float(open(DELAY_PATH).read() or "0"))
print("fake claude critique [AGREE]")
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@example.invalid")
    _git(path, "config", "user.name", "t")
    (path / "tracked.txt").write_text("base\n")
    (path / "other.txt").write_text("other\n")
    _git(path, "add", ".")
    _git(path, "commit", "-qm", "base")
    return path


def _common_dir(repo: Path) -> Path:
    raw = _git(repo, "rev-parse", "--git-common-dir").strip()
    p = Path(raw)
    return (p if p.is_absolute() else repo / p).resolve()


class Harness:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.bin = root / "bin"
        self.bin.mkdir(parents=True)
        self.behavior_path = root / "behavior.json"
        self.claude_delay = root / "claude-delay.txt"
        self.claude_delay.write_text("0")
        self.repo = _init_repo(root / "repo")
        self.base = root / "dispatch"
        self.launches: list[list[str]] = []
        self.launch_times: list[float] = []
        self.behave()
        agy = self.bin / "agy"
        agy.write_text(FAKE_AGY.replace("BEHAVIOR_PATH", repr(str(self.behavior_path))))
        agy.chmod(0o755)
        claude = self.bin / "claude"
        claude.write_text(FAKE_CLAUDE.replace("DELAY_PATH", repr(str(self.claude_delay))))
        claude.chmod(0o755)

    def behave(self, default: dict | None = None, rules: list[dict] | None = None) -> None:
        self.behavior_path.write_text(json.dumps({"default": default or {}, "rules": rules or []}))

    def state(self, repo: Path | None = None) -> Path:
        return _common_dir(repo or self.repo) / STATE_DIRNAME

    def incidents(self, repo: Path | None = None) -> list[dict]:
        found = []
        for f in sorted((self.state(repo) / "incidents").glob("*/incident.json")):
            data = json.loads(f.read_text())
            data["_dir"] = f.parent
            found.append(data)
        return found

    def windows(self, repo: Path | None = None) -> list[dict]:
        f = self.state(repo) / "windows.jsonl"
        return [json.loads(line) for line in f.read_text().splitlines()] if f.exists() else []

    @property
    def agy_launches(self) -> int:
        return len(self.launches)


def _is_agy_launch(argv) -> bool:
    if not isinstance(argv, (list, tuple)):
        return False
    return "--prompt" in argv and any(os.path.basename(str(a)) == "agy" for a in argv)


def _assert_fake_agy(harness: Harness) -> None:
    """TC-0.1 guard: every launch must resolve `agy` to the harness fake, never a real install."""
    found = shutil.which("agy")
    assert found == str(harness.bin / "agy"), f"fake-critic guard: agy resolves to {found}, not the fake"


@pytest.fixture
def h(monkeypatch):
    root = FIXTURE_BASE / uuid.uuid4().hex[:12]
    harness = Harness(root)
    monkeypatch.setenv("PATH", f"{harness.bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("ADVSPEC_AGY_DISPATCH_BASE", str(harness.base))
    _assert_fake_agy(harness)
    import models

    monkeypatch.setattr(models, "ANTIGRAVITY_AVAILABLE", True)
    monkeypatch.setattr(models, "CLAUDE_CLI_AVAILABLE", True)
    monkeypatch.setattr(models, "RETRY_BASE_DELAY", 0.0)
    try:
        import agy_sandbox
    except ImportError:
        agy_sandbox = None
    if agy_sandbox is not None:
        agy_sandbox._reset_process_state_for_tests()

    real_popen = subprocess.Popen

    class CountingPopen(real_popen):
        def __init__(self, *args, **kwargs):
            argv = args[0] if args else kwargs.get("args")
            if _is_agy_launch(argv):
                harness.launches.append(list(argv))
                harness.launch_times.append(time.monotonic())
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", CountingPopen)
    yield harness
    if agy_sandbox is not None:
        agy_sandbox._reset_process_state_for_tests()
    for dirpath, dirnames, _ in os.walk(root):  # R3 cases leave mode-000 dirs behind
        for name in dirnames:
            with contextlib.suppress(OSError):
                os.chmod(os.path.join(dirpath, name), 0o700)
    shutil.rmtree(root, ignore_errors=True)


def _dispatch(h: Harness, prompt: str = "review this spec", timeout: int = 30, cwd: Path | None = None):
    import models

    return models.call_antigravity_model(
        system_prompt="system", user_message=prompt, model=AGY_MODEL, timeout=timeout, cwd=str(cwd or h.repo)
    )


def _stop_type():
    import agy_sandbox

    return agy_sandbox.AgyStop


def _write_ws(path: str = "notes.md", data: str = "critic wrote this") -> dict:
    return {"op": "write", "path": path, "data": data}


def _run_debate(h: Harness, monkeypatch, capsys, extra: list[str], models_arg: str = AGY_MODEL,
                cwd: Path | None = None, round_cwd: Path | None = None) -> tuple[int, str]:
    import debate
    import session

    run_dir = cwd or h.repo
    monkeypatch.chdir(run_dir)
    monkeypatch.setattr(session, "CHECKPOINTS_DIR", run_dir / ".adversarial-spec-checkpoints")
    monkeypatch.setattr(session, "SESSION_STATE_PATH", run_dir / ".adversarial-spec" / "session-state.json")
    argv = ["debate.py", "critique", "--models", models_arg, "--timeout", "30", *OVERRIDE, *extra]
    if round_cwd is not None:
        argv += ["--cwd", str(round_cwd)]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(sys, "stdin", io.StringIO("# Spec\n\nA small spec for the offline safety suite.\n"))
    code = 0
    try:
        debate.main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, capsys.readouterr().err


# -- US-0 offline suite ------------------------------------------------------------------------


def test_suite_uses_fake_critic_only(h):
    """TC-0.0: a clean dispatch reaches the fake critic (never a real agy) and every launch is bwrap-wrapped."""
    text, _, _ = _dispatch(h)
    assert "fake critique" in text
    assert h.agy_launches == 1
    assert os.path.basename(h.launches[0][0]) == "bwrap"


def test_fake_guard_rejects_real_agy(h, monkeypatch):
    """TC-0.1 negative: an `agy` resolving anywhere but the harness fake trips the guard; paired: the fake passes."""
    _assert_fake_agy(h)
    impostor = h.root / "real-bin"
    impostor.mkdir()
    (impostor / "agy").write_text("#!/bin/sh\nexit 0\n")
    (impostor / "agy").chmod(0o755)
    monkeypatch.setenv("PATH", f"{impostor}{os.pathsep}{os.environ['PATH']}")
    with pytest.raises(AssertionError, match="fake-critic guard"):
        _assert_fake_agy(h)
    assert h.agy_launches == 0


def test_sandbox_unavailable_reported(h, monkeypatch):
    """TC-0.2: no bwrap on PATH -> AgyDispatchRefusedError naming the reason, zero launches; paired: bwrap -> None."""
    import agy_sandbox

    assert agy_sandbox.sandbox_unavailable_reason() is None
    agy_sandbox._reset_process_state_for_tests()
    state = h.state()
    monkeypatch.setenv("PATH", str(h.bin))
    with pytest.raises(agy_sandbox.AgyDispatchRefusedError, match="bwrap"):
        _dispatch(h)
    assert h.agy_launches == 0
    assert not state.exists()


# -- US-1 debate STOP is terminal ---------------------------------------------------------------


def test_debate_critic_write_stops_round(h, monkeypatch, capsys):
    """TC-1.0 + TC-9.1: workspace write -> exit 4, one launch, incident, no round artifacts, evidence named."""
    h.behave(default={"steps": [_write_ws()]})
    code, err = _run_debate(h, monkeypatch, capsys, ["--skip-preflight"])
    assert code == 4
    assert h.agy_launches == 1
    assert "Retrying" not in err
    [incident] = h.incidents()
    assert incident["kind"] == "critic"
    assert (incident["_dir"] / "workspace" / "notes.md").read_text() == "critic wrote this"
    assert (h.state() / "stop.json").exists()
    assert not list((h.repo / ".adversarial-spec-checkpoints").glob("*round-1.md"))
    assert not list((h.repo / ".adversarial-spec-checkpoints").glob("*critiques.json"))
    assert str(incident["_dir"]) in err and "critic" in err and "agy_sandbox.py clear" in err


def test_debate_clean_round_completes(h, monkeypatch, capsys):
    """TC-1.0 negative: clean critic -> exit 0, round checkpoint written, no stop state."""
    code, _ = _run_debate(h, monkeypatch, capsys, ["--skip-preflight"])
    assert code == 0
    assert list((h.repo / ".adversarial-spec-checkpoints").glob("*round-1.md"))
    assert h.incidents() == []
    assert not (h.state() / "stop.json").exists()


def test_nonmutation_failure_still_retried(h):
    """TC-1.1: rc!=0 without writes keeps bounded retry (MAX_RETRIES launches, error, no incident)."""
    import models

    h.behave(default={"exit": 3, "stdout": ""})
    resp = models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=30, cwd=str(h.repo))
    assert resp.error
    assert h.agy_launches == models.MAX_RETRIES
    assert h.incidents() == []


def test_critic_write_is_launched_once(h):
    """TC-1.1 pair: a workspace write is never retried (exactly one launch)."""
    import models

    h.behave(default={"steps": [_write_ws()], "exit": 3})
    with pytest.raises(_stop_type()):
        models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=30, cwd=str(h.repo))
    assert h.agy_launches == 1


def test_stopped_round_quarantines_sibling_output(h, monkeypatch, capsys):
    """TC-1.2: a sibling still running when agy trips is quarantined, not saved as a partial checkpoint."""
    h.claude_delay.write_text("2")
    h.behave(default={"steps": [_write_ws()]})
    code, _ = _run_debate(h, monkeypatch, capsys, ["--skip-preflight"],
                          models_arg=f"{AGY_MODEL},claude-cli/claude-opus-5-5")
    assert code == 4
    [incident] = h.incidents()
    quarantined = list((incident["_dir"] / "quarantine").glob("*.json"))
    assert len(quarantined) == 1
    assert "fake claude critique" in quarantined[0].read_text()
    assert not list((h.repo / ".adversarial-spec-checkpoints").glob("*claude-cli*.json"))


def test_finished_sibling_keeps_partial_checkpoint(h, monkeypatch, capsys):
    """TC-1.2 pair: a sibling that finished before the trip keeps its partial checkpoint."""
    h.behave(default={"steps": [{"op": "sleep", "seconds": 2}, _write_ws()]})
    code, _ = _run_debate(h, monkeypatch, capsys, ["--skip-preflight"],
                          models_arg=f"{AGY_MODEL},claude-cli/claude-opus-5-5")
    assert code == 4
    assert list((h.repo / ".adversarial-spec-checkpoints").glob("*claude-cli*.json"))


def test_stop_escapes_generic_except(h):
    """TC-1.3: `except Exception` cannot absorb the STOP; the same wrapper does absorb ordinary failures."""
    h.behave(default={"exit": 2, "stdout": ""})
    absorbed = False
    try:
        _dispatch(h)
    except Exception:  # noqa: BLE001 - this is the generic handler under test
        absorbed = True
    assert absorbed
    h.behave(default={"steps": [_write_ws()]})
    with pytest.raises(_stop_type()):
        try:
            _dispatch(h)
        except Exception:  # noqa: BLE001
            pytest.fail("AgyStop was absorbed by a generic except Exception handler")


def test_stop_independent_of_message_text(h, monkeypatch):
    """TC-1.4: randomised STOP text -> same outcome; an ordinary error quoting the old token is retried."""
    import agy_sandbox
    import models

    monkeypatch.setattr(agy_sandbox, "STOP_MESSAGE_TEMPLATE", uuid.uuid4().hex + " {kind} {incident_dir}")
    h.behave(default={"steps": [_write_ws()]})
    with pytest.raises(agy_sandbox.AgyStop):
        models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=30, cwd=str(h.repo))
    assert h.agy_launches == 1
    agy_sandbox._reset_process_state_for_tests()
    shutil.rmtree(h.state())
    h.launches.clear()
    token = "AGY_MUTATION_DETECTED: STOP EVERYTHING"
    h.behave(default={"exit": 1, "stdout": "", "stderr": token})
    resp = models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=30, cwd=str(h.repo))
    assert resp.error and token in resp.error  # the ordinary exception really carries the old token
    assert h.agy_launches == models.MAX_RETRIES
    assert h.incidents() == []


def test_latch_blocks_later_dispatch_in_process(h):
    """TC-1.5: after a STOP the next call raises kind=latched with no launch; paired: no prior stop launches."""
    _dispatch(h)
    assert h.agy_launches == 1
    h.behave(default={"steps": [_write_ws()]})
    with pytest.raises(_stop_type()):
        _dispatch(h)
    h.behave(default={})
    with pytest.raises(_stop_type()) as info:
        _dispatch(h)
    assert info.value.kind == "latched"
    assert h.agy_launches == 2


# -- US-2 gauntlet ------------------------------------------------------------------------------


def _gauntlet_rules(writer_token: str, second_writer: str | None = None, sleep: float = 0.0) -> list[dict]:
    rules = [{"match": writer_token, "steps": [_write_ws("attack.md", "planted")], "stdout": "[]"}]
    if second_writer:
        rules.append({"match": second_writer, "steps": [{"op": "sleep", "seconds": sleep},
                                                        _write_ws("second.md", "planted")], "stdout": "[]"})
    return rules


def test_gauntlet_attack_stop_blocks_queued_siblings(h, monkeypatch):
    """TC-2.0: first agy attack writes -> queued pairs never launch; run_gauntlet marks agy_stop and exits 4."""
    from gauntlet import orchestrator, phase_1_attacks

    monkeypatch.chdir(h.repo)
    monkeypatch.setattr(phase_1_attacks, "get_rate_limit_config", lambda _m: (1, 1))
    h.behave(default={"stdout": "[]"}, rules=_gauntlet_rules("You see threats EVERYWHERE"))
    with pytest.raises(SystemExit) as info:
        orchestrator.run_gauntlet(
            "# Spec\n\nsmall spec", adversaries=["paranoid_security", "burned_oncall", "minimalist"],
            attack_models=[AGY_MODEL], eval_models=[AGY_MODEL_B], unattended=True, timeout=30,
        )
    assert info.value.code == 4
    assert h.agy_launches == 1
    manifests = list((h.repo / ".adversarial-spec-gauntlet").glob("run-manifest-*.json"))
    assert [json.loads(m.read_text()).get("status") for m in manifests] == ["agy_stop"]


def test_gauntlet_clean_agy_attacks_complete(h, monkeypatch):
    """TC-2.0 pair: clean agy attacks all launch and leave no stop state."""
    from gauntlet import phase_1_attacks
    from gauntlet.core_types import GauntletConfig

    monkeypatch.chdir(h.repo)
    monkeypatch.setattr(phase_1_attacks, "get_rate_limit_config", lambda _m: (3, 0))
    h.behave(default={"stdout": "[]"})
    phase_1_attacks.generate_attacks("# spec", ["paranoid_security", "burned_oncall", "minimalist"], [AGY_MODEL],
                                     GauntletConfig(timeout=30))
    assert h.agy_launches == 3
    assert h.incidents() == []


def test_running_sibling_finishes_and_is_inspected(h, monkeypatch):
    """TC-2.1: an already-running sibling is not signalled; its own late write becomes a second incident."""
    from gauntlet import phase_1_attacks
    from gauntlet.core_types import GauntletConfig

    monkeypatch.chdir(h.repo)
    monkeypatch.setattr(phase_1_attacks, "get_rate_limit_config", lambda _m: (3, 0))
    h.behave(default={"stdout": "[]", "steps": [{"op": "sleep", "seconds": 1.5}]},
             rules=_gauntlet_rules("You see threats EVERYWHERE", "You've been paged at 3am", sleep=1.5))
    with pytest.raises(_stop_type()):
        phase_1_attacks.generate_attacks("# spec", ["paranoid_security", "burned_oncall", "minimalist"],
                                         [AGY_MODEL], GauntletConfig(timeout=30))
    assert h.agy_launches == 3
    assert sorted(i["kind"] for i in h.incidents()) == ["critic", "critic"]


# -- US-3 preflight -----------------------------------------------------------------------------


def test_preflight_uses_round_cwd(h, monkeypatch, capsys):
    """TC-3.0: preflight write is filed under the --cwd repo (B), never the process repo (A)."""
    repo_b = _init_repo(h.root / "repo-b")
    h.behave(default={"steps": [_write_ws()]})
    code, _ = _run_debate(h, monkeypatch, capsys, [], round_cwd=repo_b)
    assert code == 4
    assert len(h.incidents(repo_b)) == 1 and h.incidents() == []
    assert h.agy_launches == 1


def test_preflight_without_cwd_uses_process_repo(h, monkeypatch, capsys):
    """TC-3.0 pair: without --cwd the preflight incident is filed under the process repo."""
    h.behave(default={"steps": [_write_ws()]})
    code, _ = _run_debate(h, monkeypatch, capsys, [])
    assert code == 4
    assert len(h.incidents()) == 1


def test_preflight_failure_without_write_is_ordinary(h, monkeypatch, capsys):
    """TC-3.1 pair: rc!=0 preflight with no write -> exit 2 'preflight failed', no incident."""
    h.behave(default={"exit": 1, "stdout": ""})
    code, err = _run_debate(h, monkeypatch, capsys, [])
    assert code == 2
    assert "preflight failed" in err
    assert h.incidents() == []


@pytest.mark.parametrize("extra", [[], ["--skip-preflight"]])
def test_blocked_repo_refuses_with_and_without_preflight(h, monkeypatch, capsys, extra):
    """TC-3.2/3.3: an uncleared stop in the repo -> exit 5 and zero launches, with or without preflight."""
    import agy_sandbox

    h.behave(default={"steps": [_write_ws()]})
    with pytest.raises(agy_sandbox.AgyStop):
        _dispatch(h)
    agy_sandbox._reset_process_state_for_tests()
    h.launches.clear()
    h.behave(default={})
    code, err = _run_debate(h, monkeypatch, capsys, extra)
    assert code == 5
    assert h.agy_launches == 0
    assert "stop.json" in err


def test_round_refuses_unavailable_agy_seat(h, monkeypatch, capsys):
    """TC-3.4: sandbox unavailable -> round refuses before ANY launch (exit 6, seat named)."""
    import agy_sandbox

    monkeypatch.setattr(agy_sandbox, "sandbox_unavailable_reason", lambda: "bwrap not found")
    code, err = _run_debate(h, monkeypatch, capsys, ["--skip-preflight"],
                            models_arg=f"{AGY_MODEL},claude-cli/claude-opus-5-5")
    assert code == 6
    assert AGY_MODEL in err and "bwrap not found" in err
    assert h.agy_launches == 0
    assert not (h.repo / ".adversarial-spec-checkpoints").exists()


def test_round_without_agy_seat_unaffected_by_sandbox(h, monkeypatch, capsys):
    """TC-3.4 pair: a round with no agy seat runs even when the sandbox is unavailable."""
    import agy_sandbox

    monkeypatch.setattr(agy_sandbox, "sandbox_unavailable_reason", lambda: "bwrap not found")
    code, _ = _run_debate(h, monkeypatch, capsys, ["--skip-preflight"], models_arg="claude-cli/claude-opus-5-5")
    assert code == 0


# -- US-4 durable stop, tamper detection --------------------------------------------------------


def _fresh_process_dispatch(h: Harness, repo: Path) -> subprocess.CompletedProcess:
    """Dispatch from a separate interpreter; it prints LAUNCHES=<n> counted at its own Popen."""
    code = (
        "import subprocess, sys\n"
        "launches = []\n"
        "class P(subprocess.Popen):\n"
        "    def __init__(self, *a, **k):\n"
        "        argv = a[0] if a else k.get('args')\n"
        "        if isinstance(argv, (list, tuple)) and '--prompt' in argv:\n"
        "            launches.append(argv)\n"
        "        super().__init__(*a, **k)\n"
        "subprocess.Popen = P\n"
        "import models, agy_sandbox\n"
        "models.ANTIGRAVITY_AVAILABLE = True\n"
        "try:\n"
        f"    models.call_antigravity_model('s', 'u', {AGY_MODEL!r}, timeout=30, cwd={str(repo)!r})\n"
        "    print('DISPATCHED')\n"
        "except agy_sandbox.AgyStop as e:\n"
        "    print('STOP', e.kind); print(e)\n"
        "finally:\n"
        "    print('LAUNCHES=%d' % len(launches))\n"
    )
    env = dict(os.environ, PYTHONPATH=str(SCRIPTS_DIR))
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)


def _clear(repo: Path, ids: list[str], operator: str = "jason") -> subprocess.CompletedProcess:
    argv = [sys.executable, str(SCRIPTS_DIR / "agy_sandbox.py"), "clear", "--repo", str(repo),
            "--operator", operator, "--reason", "reviewed incident evidence"]
    for i in ids:
        argv += ["--incident", i]
    return subprocess.run(argv, capture_output=True, text=True, timeout=60)


def _trip(h: Harness, repo: Path | None = None) -> dict:
    import agy_sandbox

    h.behave(default={"steps": [_write_ws()]})
    with pytest.raises(agy_sandbox.AgyStop):
        _dispatch(h, cwd=repo)
    agy_sandbox._reset_process_state_for_tests()
    h.behave(default={})
    return h.incidents(repo)[-1]


def test_fresh_process_blocked_until_clear(h):
    """TC-4.0 + TC-10.0: fresh process refused (names record+incident) until a logged clear; evidence kept."""
    incident = _trip(h)
    before = {str(p): p.read_bytes() for p in incident["_dir"].rglob("*") if p.is_file()}
    blocked = _fresh_process_dispatch(h, h.repo)
    assert "STOP blocked" in blocked.stdout, blocked.stderr
    assert "LAUNCHES=0" in blocked.stdout
    assert "stop.json" in blocked.stdout and incident["id"] in blocked.stdout
    cleared = _clear(h.repo, [incident["id"]])
    assert cleared.returncode == 0, cleared.stderr
    clears = [json.loads(x) for x in (h.state() / "clears.jsonl").read_text().splitlines()]
    assert clears[-1]["incidents"] == [incident["id"]] and clears[-1]["operator"] == "jason"
    assert not (h.state() / "stop.json").exists()
    after = {str(p): p.read_bytes() for p in incident["_dir"].rglob("*") if p.is_file()}
    assert before == after
    admitted = _fresh_process_dispatch(h, h.repo).stdout
    assert "DISPATCHED" in admitted and "LAUNCHES=1" in admitted


def test_clear_with_wrong_incident_refused(h):
    """TC-10.1: a clear naming a missing/extra id is refused and changes nothing."""
    incident = _trip(h)
    refused = _clear(h.repo, [incident["id"], "not-an-incident"])
    assert refused.returncode != 0
    assert incident["id"] in refused.stderr
    assert (h.state() / "stop.json").exists()
    assert not (h.state() / "clears.jsonl").exists()


def test_other_repo_not_blocked(h):
    """TC-4.1: a stop in repo A does not block repo B."""
    _trip(h)
    repo_b = _init_repo(h.root / "repo-b")
    out = _fresh_process_dispatch(h, repo_b).stdout
    assert "DISPATCHED" in out and "LAUNCHES=1" in out
    assert "STOP blocked" in _fresh_process_dispatch(h, h.repo).stdout


def test_state_outside_every_worktree_and_linked_worktree_blocked(h):
    """TC-4.2 + TC-4.6: state lives in the git common dir, invisible to status; a linked worktree is blocked."""
    w2 = h.root / "w2"
    _git(h.repo, "worktree", "add", "-q", str(w2))
    _trip(h)
    assert h.state().is_relative_to(_common_dir(h.repo))
    for tree in (h.repo, w2):
        assert STATE_DIRNAME not in _git(tree, "status", "--porcelain", "--untracked-files=all")
    out = _fresh_process_dispatch(h, w2).stdout
    assert "STOP blocked" in out and "LAUNCHES=0" in out


def test_corrupt_record_fails_closed(h):
    """TC-4.3: an unparseable stop.json refuses dispatch and names the path."""
    _trip(h)
    (h.state() / "stop.json").write_text("{not json")
    out = _fresh_process_dispatch(h, h.repo).stdout
    assert "STOP blocked" in out and "stop.json" in out and "LAUNCHES=0" in out


def test_stop_between_prepare_and_launch_blocks(h, monkeypatch):
    """TC-4.7: a stop recorded after workspace preparation but before launch -> zero launches."""
    import agy_sandbox

    real_prepare = agy_sandbox._prepare_dispatch_root

    def prepare_then_other_process_stops(*args, **kwargs):
        layout = real_prepare(*args, **kwargs)
        agy_sandbox.record_incident(h.repo, kind="critic", model="other-process", stdout="", stderr="")
        return layout

    monkeypatch.setattr(agy_sandbox, "_prepare_dispatch_root", prepare_then_other_process_stops)
    with pytest.raises(agy_sandbox.AgyStop) as info:
        _dispatch(h)
    assert info.value.kind == "blocked"
    assert h.agy_launches == 0


def test_deleted_record_without_clear_is_tamper_stop(h):
    """TC-10.3: incident present, stop.json deleted without a logged clear -> tamper STOP, record re-created."""
    import agy_sandbox

    _trip(h)
    (h.state() / "stop.json").unlink()
    with pytest.raises(agy_sandbox.AgyStop) as info:
        _dispatch(h)
    assert info.value.kind == "tamper"
    assert (h.state() / "stop.json").exists()
    assert h.agy_launches == 1


def test_deleted_record_after_clear_admits(h):
    """TC-10.3 pair: after a logged clear the same no-record state admits dispatch."""
    incident = _trip(h)
    assert _clear(h.repo, [incident["id"]]).returncode == 0
    _dispatch(h)
    assert h.agy_launches == 2


# -- US-5 co-tenant writes ----------------------------------------------------------------------


def test_cotenant_write_preserved_and_logged(h):
    """TC-5.0: incident replay - a non-critic write mid-window keeps its bytes, is logged co_tenant, never halts."""
    (h.repo / "tracked.txt").write_text("dirty before window\n")
    (h.repo / "other.txt").write_text("dirty, will be deleted\n")
    (h.repo / "untracked.md").write_text("another session's work\n")
    h.behave(default={"steps": [{"op": "sleep", "seconds": 2}]})
    critique = "x" * 2519

    def cotenant():
        time.sleep(0.7)
        (h.repo / "roadmap-debate-r1-claude.md").write_text(critique)
        (h.repo / "tracked.txt").write_text("edited by orchestrator\n")
        (h.repo / "other.txt").unlink()

    writer = threading.Thread(target=cotenant)
    writer.start()
    text, _, _ = _dispatch(h)
    writer.join()
    assert "fake critique" in text
    assert (h.repo / "roadmap-debate-r1-claude.md").read_text() == critique
    assert (h.repo / "tracked.txt").read_text() == "edited by orchestrator\n"
    assert not (h.repo / "other.txt").exists()
    assert (h.repo / "untracked.md").read_text() == "another session's work\n"
    assert h.incidents() == [] and not (h.state() / "stop.json").exists()
    [window] = h.windows()
    assert sorted(window["co_tenant"]) == ["other.txt", "roadmap-debate-r1-claude.md", "tracked.txt"]


def test_partial_checkpoint_is_cotenant(h, monkeypatch):
    """TC-5.1: the partial-result writer saving into the repo mid-window does not halt."""
    import models
    import session

    monkeypatch.setattr(session, "CHECKPOINTS_DIR", h.repo / ".adversarial-spec-checkpoints")
    h.behave(default={"steps": [{"op": "sleep", "seconds": 1.5}]})

    def save_partial():
        time.sleep(0.5)
        result = models.ModelResponse(model="codex/x", response="r", agreed=False, spec=None)
        models._save_partial_result(result, 1, "sess")

    t = threading.Thread(target=save_partial)
    t.start()
    _dispatch(h)
    t.join()
    assert list((h.repo / ".adversarial-spec-checkpoints").glob("sess-round-1-*.json"))
    assert h.incidents() == []


# -- US-6 critic write captured, workspace discarded --------------------------------------------


def test_workspace_write_captured_and_discarded(h):
    """TC-6.0: created file + nested file captured byte-exact, streams captured, dispatch root removed."""
    import agy_sandbox

    h.behave(default={"steps": [_write_ws("a.txt", "alpha"), _write_ws("sub/dir/b.txt", "beta")]})
    with pytest.raises(agy_sandbox.AgyStop) as info:
        _dispatch(h)
    assert info.value.kind == "critic"
    [incident] = h.incidents()
    ws = incident["_dir"] / "workspace"
    assert (ws / "a.txt").read_text() == "alpha"
    assert (ws / "sub/dir/b.txt").read_text() == "beta"
    assert sorted(incident["paths"]) == ["a.txt", "sub/dir/b.txt"]
    assert "FAKE_AGY_STARTED" in (incident["_dir"] / "agy-stderr.txt").read_text()
    assert "wrote a.txt" in (incident["_dir"] / "agy-stdout.txt").read_text()
    assert list(h.base.glob("agy-dispatch-*")) == []


def test_repo_write_attempt_blocked_and_logged(h):
    """TC-6.1: abs-path write into the repo fails at the kernel; no halt; blocked attempt logged."""
    target = h.repo / "tracked.txt"
    h.behave(default={"steps": [{"op": "write", "path": str(target), "data": "evil"}]})
    text, _, _ = _dispatch(h)
    assert "blocked " + str(target) in text
    assert target.read_text() == "base\n"
    assert h.incidents() == []
    [window] = h.windows()
    assert any("Read-only file system" in line for line in window["blocked_write_attempts"])


def test_timeout_after_write_is_stop(h):
    """TC-6.2: write then hang past the timeout -> STOP (not a timeout error), one launch, no leftover process."""
    import agy_sandbox
    import models

    h.behave(default={"steps": [_write_ws(), {"op": "sleep", "seconds": 60}]})
    with pytest.raises(agy_sandbox.AgyStop):
        models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=2, cwd=str(h.repo))
    assert h.agy_launches == 1
    time.sleep(0.5)
    leftovers = [p for p in Path("/proc").glob("[0-9]*/cmdline")
                 if str(h.bin) in p.read_bytes().decode(errors="ignore")]
    assert leftovers == []


def test_clean_timeout_is_retried(h):
    """TC-6.2 negative: hang without writing -> ordinary timeout error, MAX_RETRIES launches, no incident."""
    import models

    h.behave(default={"steps": [{"op": "sleep", "seconds": 60}]})
    resp = models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=1, cwd=str(h.repo))
    assert resp.error and "timed out" in resp.error
    assert h.agy_launches == models.MAX_RETRIES
    assert h.incidents() == []


def test_clean_dispatch_returns_response(h):
    """TC-6.3: clean run returns the response, leaves no dispatch root and no stop state."""
    text, _, _ = _dispatch(h)
    assert "fake critique" in text
    assert list(h.base.glob("agy-dispatch-*")) == []
    assert h.incidents() == []


def test_evidence_failure_keeps_workspace_and_stops(h, monkeypatch):
    """TC-6.4: incident evidence unwritable -> STOP still raised ('evidence incomplete'), workspace kept."""
    import agy_sandbox

    def failing_capture(*_a, **_k):
        raise OSError("evidence disk full")

    monkeypatch.setattr(agy_sandbox, "_capture_workspace", failing_capture)
    h.behave(default={"steps": [_write_ws()]})
    with pytest.raises(agy_sandbox.AgyStop) as info:
        _dispatch(h)
    assert "evidence incomplete" in str(info.value)
    kept = list(h.base.glob("agy-dispatch-*"))
    assert len(kept) == 1 and (kept[0] / "ws" / "notes.md").read_text() == "critic wrote this"
    assert json.loads((kept[0] / "retained.json").read_text())["reason"]


# -- US-7 boundary failure vs refusal -----------------------------------------------------------


def test_every_launch_is_sandboxed(h):
    """TC-7.0: each launch runs under bwrap with the load-bearing flags."""
    _dispatch(h)
    argv = h.launches[0]
    assert os.path.basename(argv[0]) == "bwrap"
    for flag in ("--clearenv", "--unshare-pid", "--die-with-parent", "--new-session"):
        assert flag in argv
    i = argv.index("--ro-bind")
    assert argv[i + 1:i + 3] == ["/", "/"]


def test_bwrap_setup_failure_is_refusal_only(h, monkeypatch):
    """TC-7.1: a bind source that does not exist -> refusal, no incident, no record, no retry."""
    import agy_sandbox
    import models

    real_build = agy_sandbox.build_bwrap_argv

    def broken(*args, **kwargs):
        argv = real_build(*args, **kwargs)
        return argv[:1] + ["--ro-bind", str(h.root / "does-not-exist"), "/nonexistent-mount"] + argv[1:]

    monkeypatch.setattr(agy_sandbox, "build_bwrap_argv", broken)
    with pytest.raises(agy_sandbox.AgyDispatchRefusedError, match="sandbox setup failed"):
        models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=30, cwd=str(h.repo))
    assert h.agy_launches == 1
    assert h.incidents() == [] and not (h.state() / "stop.json").exists()


def test_probe_write_success_is_boundary_stop(h, monkeypatch):
    """TC-7.2: broken profile makes the repo writable -> probe succeeds, critic never starts, boundary STOP."""
    import agy_sandbox

    real_build = agy_sandbox.build_bwrap_argv

    def repo_writable(*args, **kwargs):
        argv = real_build(*args, **kwargs)
        i = argv.index("--ro-bind")
        return argv[:i + 3] + ["--bind", str(h.repo), str(h.repo)] + argv[i + 3:]

    monkeypatch.setattr(agy_sandbox, "build_bwrap_argv", repo_writable)
    with pytest.raises(agy_sandbox.AgyStop) as info:
        _dispatch(h)
    assert info.value.kind == "boundary_failure"
    [incident] = h.incidents()
    assert "FAKE_AGY_STARTED" not in (incident["_dir"] / "agy-stderr.txt").read_text()
    assert not list(h.repo.glob(".advspec-boundary-probe-*"))
    assert (h.state() / "stop.json").exists()


def test_correct_profile_probe_fails_and_critic_starts(h):
    """TC-7.2 pair: correct profile -> probe blocked, critic starts, no boundary incident."""
    h.behave(default={"steps": [{"op": "exists", "path": "."}]})
    text, _, _ = _dispatch(h)
    assert "exists .=True" in text and h.incidents() == []


def test_sentinel_change_is_boundary_stop(h, monkeypatch):
    """TC-7.3: broken profile binds the sentinel writable and the critic changes it -> boundary_failure."""
    import agy_sandbox

    real_build = agy_sandbox.build_bwrap_argv
    real_prepare = agy_sandbox._prepare_dispatch_root

    def sentinel_writable(layout, *args, **kwargs):
        return real_build(layout, *args, **kwargs) + ["--bind", str(layout.sentinel), str(layout.sentinel)]

    def prepare(*args, **kwargs):
        layout = real_prepare(*args, **kwargs)
        h.behave(default={"steps": [{"op": "write", "path": str(layout.sentinel), "data": "changed"}]})
        return layout

    monkeypatch.setattr(agy_sandbox, "build_bwrap_argv", sentinel_writable)
    monkeypatch.setattr(agy_sandbox, "BOUNDARY_PROBE_ENABLED", False)
    monkeypatch.setattr(agy_sandbox, "_prepare_dispatch_root", prepare)
    with pytest.raises(agy_sandbox.AgyStop) as info:
        _dispatch(h)
    assert info.value.kind == "boundary_failure"


# -- US-11 inputs, siblings, config dirs --------------------------------------------------------


def test_prompt_bound_readonly_in_workspace(h, monkeypatch):
    """TC-11.0: pointer prompt read from <ws>/inputs/prompt.md (sha matches); modifying it fails; repo untouched."""
    import agy_sandbox
    import models

    monkeypatch.setattr(agy_sandbox, "INLINE_PROMPT_MAX", 10)
    h.behave(default={"steps": [{"op": "read_prompt"}]})
    text, _, _ = _dispatch(h, prompt="payload for the pointer transport")
    expected = models.build_antigravity_prompt("system", "payload for the pointer transport")
    assert f"prompt_sha={hashlib.sha256(expected.encode()).hexdigest()}" in text
    path = next(line.split("=", 1)[1] for line in text.splitlines() if line.startswith("prompt_path="))
    assert path.endswith("/ws/inputs/prompt.md")
    h.behave(default={"steps": [{"op": "write_prompt"}, {"op": "read_prompt"}]})
    blocked, _, _ = _dispatch(h, prompt="payload for the pointer transport")
    assert "blocked prompt" in blocked
    assert f"prompt_sha={hashlib.sha256(expected.encode()).hexdigest()}" in blocked
    assert _git(h.repo, "status", "--porcelain", "--untracked-files=all") == ""


def test_oversized_prompt_never_in_repo(h, monkeypatch):
    """TC-11.1 [BVA]: len == inline max -> inline; len == max+1 -> pointer file in the dispatch root; repo clean."""
    import agy_sandbox
    import models

    h.behave(default={"steps": [{"op": "read_prompt"}]})
    base_len = len(models.build_antigravity_prompt("system", "").encode())
    monkeypatch.setattr(agy_sandbox, "INLINE_PROMPT_MAX", base_len + 5)
    inline, _, _ = _dispatch(h, prompt="a" * 5)
    assert "prompt_path=inline" in inline
    pointer, _, _ = _dispatch(h, prompt="a" * 6)
    assert "/ws/inputs/prompt.md" in pointer
    assert _git(h.repo, "status", "--porcelain", "--untracked-files=all") == ""
    assert list(h.base.glob("agy-dispatch-*")) == []


def test_siblings_cannot_see_each_other(h):
    """TC-11.2: the dispatch base is masked, so a critic sees no other dispatch root."""
    other = h.base / "agy-dispatch-other"
    (other / "ws").mkdir(parents=True)
    (other / "owner.pid").write_text(str(os.getpid()))
    h.behave(default={"steps": [{"op": "listdir", "path": str(h.base)}]})
    text, _, _ = _dispatch(h)
    listing = json.loads(next(x for x in text.splitlines() if x.startswith("listdir=")).split("=", 1)[1])
    assert "agy-dispatch-other" not in (listing or [])
    assert other.exists()


def test_leftover_dead_dispatch_roots_cleaned(h):
    """R2-4: the next dispatch removes roots whose owner process is gone; live owners are kept."""
    dead = h.base / "agy-dispatch-dead"
    (dead / "ws").mkdir(parents=True)
    (dead / "owner.pid").write_text("999999999")
    live = h.base / "agy-dispatch-live"
    (live / "ws").mkdir(parents=True)
    (live / "owner.pid").write_text(str(os.getpid()))
    _dispatch(h)
    assert not dead.exists() and live.exists()


# Operator ruling R2-1, spelled out literally so a path dropped from the module constants fails here.
REQUIRED_THROWAWAY_DIRS = ("brain", "conversations", "log", "cache", "scratch", "presence", "crashes",
                           "annotations", "implicit", "knowledge")
REQUIRED_THROWAWAY_FILES = ("history.jsonl", "conversation_summaries.db")


def test_config_dirs_readonly_and_throwaway(h, monkeypatch):
    """TC-11.3: config files read-only, named antigravity-cli paths throwaway, browser profile hidden."""
    home = h.root / "home"
    cli = home / ".gemini" / "antigravity-cli"
    profile = home / ".gemini" / "antigravity-browser-profile"
    for d in [cli / name for name in REQUIRED_THROWAWAY_DIRS] + [profile]:
        d.mkdir(parents=True)
    (home / ".gemini" / "antigravity-browser-profile" / "Cookies").write_text("secret")
    for name, data in (("settings.json", "{}"), ("antigravity-oauth-token", "tok"), ("mcp_config.json", "{}")):
        (cli / name).write_text(data)
    for name in REQUIRED_THROWAWAY_FILES:
        (cli / name).write_text("h\n")
    (home / ".gemini" / "settings.json").write_text("{}")
    (home / ".antigravity").mkdir()
    (home / ".antigravity" / "argv.json").write_text("{}")
    monkeypatch.setenv("HOME", str(home))
    ro = [cli / "settings.json", cli / "antigravity-oauth-token", cli / "mcp_config.json",
          home / ".gemini" / "settings.json", home / ".antigravity" / "argv.json"]
    tw = [cli / name / "planted" for name in REQUIRED_THROWAWAY_DIRS] + [cli / n for n in REQUIRED_THROWAWAY_FILES]
    steps = [{"op": "write", "path": str(p), "data": "w"} for p in ro + tw]
    steps.append({"op": "listdir", "path": str(home / ".gemini" / "antigravity-browser-profile")})
    h.behave(default={"steps": steps})
    text, _, _ = _dispatch(h)
    for p in ro:
        assert f"blocked {p}" in text
    for p in tw:
        assert f"wrote {p}" in text
    assert "listdir=[]" in text
    for name in REQUIRED_THROWAWAY_DIRS:
        assert not (cli / name / "planted").exists(), name
    for name in REQUIRED_THROWAWAY_FILES:
        assert (cli / name).read_text() == "h\n", name
    assert h.incidents() == []


# -- US-12 host sockets -------------------------------------------------------------------------

PROBES = {
    "herdr": ["herdr", "agent", "list"],
    "ssh-agent": ["ssh-add", "-l"],
    "dbus": ["busctl", "--user", "list"],
}
# Same sockets addressed by explicit path, so masking is proven independently of the env allowlist.
if os.environ.get("SSH_AUTH_SOCK"):
    PROBES["ssh-agent-by-path"] = ["env", f"SSH_AUTH_SOCK={os.environ['SSH_AUTH_SOCK']}", "ssh-add", "-l"]
if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
    PROBES["dbus-by-path"] = ["busctl", f"--address={os.environ['DBUS_SESSION_BUS_ADDRESS']}", "list"]


def _unmasked_probe(argv: list[str]) -> int:
    wrapped = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", *argv]
    return subprocess.run(wrapped, capture_output=True, text=True, timeout=30).returncode


@pytest.mark.parametrize("name", sorted(PROBES))
def test_host_socket_unreachable_in_sandbox(h, name):
    """TC-12.0/1/2: each socket probe fails inside the dispatch sandbox and succeeds unmasked (paired oracle)."""
    argv = PROBES[name]
    if shutil.which(argv[0]) is None or _unmasked_probe(argv) != 0:
        pytest.skip(f"UNVERIFIABLE on this host: unmasked {name} probe unreachable, masking cannot be shown")
    h.behave(default={"steps": [{"op": "run", "argv": argv}]})
    text, _, _ = _dispatch(h)
    line = next(x for x in text.splitlines() if x.startswith(f"run {argv[0]} rc="))
    assert not line.startswith(f"run {argv[0]} rc=0"), line


def test_env_is_allowlist(h, monkeypatch):
    """TC-12.3: the critic's environment is an allowlist: no socket/herdr/runtime variables survive."""
    monkeypatch.setenv("SSH_AUTH_SOCK", "/run/user/1000/keyring/ssh")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
    monkeypatch.setenv("HERDR_SOCKET_PATH", "/home/x/.config/herdr/herdr.sock")
    monkeypatch.setenv("HERDR_PANE", "p1")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    h.behave(default={"steps": [{"op": "env"}]})
    text, _, _ = _dispatch(h)
    names = json.loads(next(x for x in text.splitlines() if x.startswith("env=")).split("=", 1)[1])
    assert "HOME" in names and "PATH" in names
    leaked = [n for n in names if n in {"SSH_AUTH_SOCK", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR"}
              or n.startswith("HERDR_")]
    assert leaked == []


# -- Review of 85da68f: regressions R1-R9 (orchestration/review-codex-85da68f.md) ------------------------


def _custom_agy(h: Harness, body: str) -> None:
    """Replace the fake critic with a one-off script (still the harness fake: same path, still sandboxed)."""
    agy = h.bin / "agy"
    agy.write_text("#!/usr/bin/env python3\n" + body)
    agy.chmod(0o755)
    _assert_fake_agy(h)


@pytest.mark.parametrize("failure", ["incident_dir", "incident_meta", "all_state_writes"])
def test_evidence_persistence_failure_is_terminal(h, monkeypatch, failure):
    """R1: incident-dir creation / initial metadata / every state write failing after a critic write -> AgyStop
    (never the generic retry), one launch, workspace kept with a retention marker, and a fresh process is still
    blocked. Paired: TC-6.3, a clean dispatch leaves no root and no stop state."""
    import agy_sandbox
    import models

    if failure == "incident_dir":
        h.state().mkdir(parents=True, exist_ok=True)
        (h.state() / "incidents").write_text("not a directory")
    else:
        real_write = agy_sandbox._write_json

        def failing_write(path, data):
            if failure == "all_state_writes" or path.name == "incident.json":
                raise OSError("evidence disk full")
            return real_write(path, data)

        monkeypatch.setattr(agy_sandbox, "_write_json", failing_write)
    h.behave(default={"steps": [_write_ws()]})
    with pytest.raises(agy_sandbox.AgyStop) as info:
        models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=30, cwd=str(h.repo))
    assert info.value.kind == "critic"
    assert h.agy_launches == 1
    [kept] = list(h.base.glob("agy-dispatch-*"))
    assert (kept / "ws" / "notes.md").read_text() == "critic wrote this"
    assert json.loads((kept / "retained.json").read_text())["reason"]
    blocked = _fresh_process_dispatch(h, h.repo).stdout
    assert "STOP blocked" in blocked and "LAUNCHES=0" in blocked


def test_undecodable_output_still_inspected(h):
    """R2: invalid UTF-8 on stdout/stderr never skips inspection: with a workspace write -> one-launch STOP whose
    evidence keeps the raw bytes; paired: the same undecodable output without a write returns normally."""
    import agy_sandbox
    import models

    emit = ('import sys\n'
            'sys.stdout.buffer.write(b"critique \\xff\\xfe [AGREE]\\n")\n'
            'sys.stderr.buffer.write(b"\\xc3\\x28 bad stderr\\n")\n')
    _custom_agy(h, emit)
    text, _, _ = _dispatch(h)
    assert "critique" in text and "[AGREE]" in text
    assert h.incidents() == []
    _custom_agy(h, 'open("notes.md", "w").write("critic wrote this")\n' + emit)
    with pytest.raises(agy_sandbox.AgyStop) as info:
        models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=30, cwd=str(h.repo))
    assert info.value.kind == "critic"
    assert h.agy_launches == 2
    [incident] = h.incidents()
    assert b"\xff\xfe" in (incident["_dir"] / "agy-stdout.txt").read_bytes()
    assert (incident["_dir"] / "workspace" / "notes.md").read_text() == "critic wrote this"


def test_uninspectable_workspace_is_terminal(h):
    """R3: a critic that writes then makes its workspace root unreadable -> STOP (never an empty delta), root kept
    with a retention marker; paired: a read-only critic in the same harness returns normally."""
    import agy_sandbox

    _custom_agy(h, 'print("only read [AGREE]")\n')
    text, _, _ = _dispatch(h)
    assert "only read" in text and h.incidents() == []
    _custom_agy(h, 'import os\nopen("notes.md", "w").write("hidden")\nos.chmod(".", 0)\nprint("done [AGREE]")\n')
    with pytest.raises(agy_sandbox.AgyStop) as info:
        _dispatch(h)
    assert info.value.kind == "critic"
    [kept] = list(h.base.glob("agy-dispatch-*"))
    assert json.loads((kept / "retained.json").read_text())["reason"]
    (kept / "ws").chmod(0o700)
    assert (kept / "ws" / "notes.md").read_text() == "hidden"


def test_stop_published_at_final_admission_cannot_precede_launch(h, monkeypatch):
    """R4: a STOP published by another writer right after the final admission check lands AFTER this launch
    started (admission and spawn are serialized against publication); paired: TC-4.7, a STOP published before the
    final check yields zero launches."""
    import agy_sandbox

    real_admit = agy_sandbox._admit
    calls: list[int] = []
    published: dict = {}

    def admit_then_race(*args, **kwargs):
        real_admit(*args, **kwargs)
        calls.append(1)
        if len(calls) == 2:  # the final pre-launch admission
            def publish():
                agy_sandbox.record_incident(h.repo, kind="critic", model="sibling", stdout="", stderr="")
                published["t"] = time.monotonic()

            thread = threading.Thread(target=publish)
            thread.start()
            published["thread"] = thread
            time.sleep(0.5)

    monkeypatch.setattr(agy_sandbox, "_admit", admit_then_race)
    _dispatch(h)
    published["thread"].join(timeout=30)
    assert h.agy_launches == 1
    assert "t" in published
    assert h.launch_times[0] < published["t"]


def test_gauntlet_prior_stop_refused_before_any_progress(h, monkeypatch):
    """R5: a stopped repo + an agy seat anywhere in the roster -> exit 5 before prompt loading, gauntlet dir
    creation, or any launch; paired: the same stopped repo with no agy seat proceeds past readiness."""
    from gauntlet import orchestrator

    _trip(h)
    h.launches.clear()
    monkeypatch.chdir(h.repo)
    reached: list[int] = []

    def sentinel(*_a, **_k):
        reached.append(1)
        raise RuntimeError("REACHED_PROMPT_LOADING")

    monkeypatch.setattr(orchestrator, "_load_approved_prompts", sentinel)
    with pytest.raises(SystemExit) as info:
        orchestrator.run_gauntlet("# Spec\n\nsmall spec", adversaries=["minimalist"],
                                  attack_models=["claude-cli/claude-opus-5-5"], eval_models=[AGY_MODEL],
                                  unattended=False, timeout=30)
    assert info.value.code == 5
    assert reached == [] and h.agy_launches == 0
    assert not (h.repo / ".adversarial-spec-gauntlet").exists()
    with pytest.raises(RuntimeError, match="REACHED_PROMPT_LOADING"):
        orchestrator.run_gauntlet("# Spec\n\nsmall spec", adversaries=["minimalist"],
                                  attack_models=["claude-cli/claude-opus-5-5"],
                                  eval_models=["claude-cli/claude-opus-5-5"], unattended=False, timeout=30)
    assert reached == [1]


def test_symlinked_mask_targets_are_masked(h, monkeypatch):
    """R6: herdr dir, browser profile, knowledge dir and history file reached through symlinks are masked /
    throwaway exactly like regular paths (by alias and by target); paired: an unmasked symlinked dir stays
    readable, so the empty listings prove masking rather than broken symlinks."""
    home = h.root / "home"
    cli = home / ".gemini" / "antigravity-cli"
    cli.mkdir(parents=True)
    (home / ".config").mkdir()
    targets = {}
    for name, content in (("real-herdr", "herdr.sock.marker"), ("real-profile", "Cookies"),
                          ("real-knowledge", None), ("real-notes", "note.txt")):
        d = home / name
        d.mkdir()
        if content:
            (d / content).write_text("x")
        targets[name] = d
    (home / ".config" / "herdr").symlink_to(targets["real-herdr"])
    (home / ".gemini" / "antigravity-browser-profile").symlink_to(targets["real-profile"])
    (cli / "knowledge").symlink_to(targets["real-knowledge"])
    real_history = home / "real-history.jsonl"
    real_history.write_text("h\n")
    (cli / "history.jsonl").symlink_to(real_history)
    (home / "linked-notes").symlink_to(targets["real-notes"])
    monkeypatch.setenv("HOME", str(home))
    listed = [home / ".config" / "herdr", targets["real-herdr"], home / ".gemini" / "antigravity-browser-profile",
              targets["real-profile"], home / "linked-notes"]
    steps = [{"op": "listdir", "path": str(p)} for p in listed]
    steps += [{"op": "write", "path": str(cli / "knowledge" / "planted"), "data": "w"},
              {"op": "write", "path": str(cli / "history.jsonl"), "data": "w"}]
    h.behave(default={"steps": steps})
    text, _, _ = _dispatch(h)
    listings = [x for x in text.splitlines() if x.startswith("listdir=")]
    assert listings == ["listdir=[]"] * 4 + ['listdir=["note.txt"]']
    assert f"wrote {cli / 'knowledge' / 'planted'}" in text and f"wrote {cli / 'history.jsonl'}" in text
    assert not (targets["real-knowledge"] / "planted").exists()
    assert real_history.read_text() == "h\n"
    assert h.incidents() == []


def test_retained_evidence_root_survives_cleanup(h):
    """R7: a dead-owner dispatch root carrying a retention marker is not reclaimed by stale cleanup; paired: a
    dead-owner root without the marker is."""
    retained = h.base / "agy-dispatch-retained"
    plain = h.base / "agy-dispatch-plain"
    for root in (retained, plain):
        (root / "ws").mkdir(parents=True)
        (root / "owner.pid").write_text("999999999")
    (retained / "retained.json").write_text(json.dumps({"reason": "evidence incomplete"}))
    _dispatch(h)
    assert retained.exists() and (retained / "retained.json").exists()
    assert not plain.exists()


def test_dispatch_time_refusal_refuses_round(h, monkeypatch, capsys):
    """R8: with preflight skipped, a sandbox refusal at dispatch time refuses the round (exit 6): no round
    checkpoint, no STOP state; paired: the same roster with a working sandbox completes the round."""
    import agy_sandbox

    real_build = agy_sandbox.build_bwrap_argv

    def broken(*args, **kwargs):
        argv = real_build(*args, **kwargs)
        return argv[:1] + ["--ro-bind", str(h.root / "does-not-exist"), "/nonexistent-mount"] + argv[1:]

    monkeypatch.setattr(agy_sandbox, "build_bwrap_argv", broken)
    roster = f"{AGY_MODEL},claude-cli/claude-opus-5-5"
    code, err = _run_debate(h, monkeypatch, capsys, ["--skip-preflight"], models_arg=roster)
    assert code == 6
    assert "sandbox setup failed" in err
    assert not list((h.repo / ".adversarial-spec-checkpoints").glob("*round-*.md"))
    assert h.incidents() == [] and not (h.state() / "stop.json").exists()
    monkeypatch.setattr(agy_sandbox, "build_bwrap_argv", real_build)
    code, _ = _run_debate(h, monkeypatch, capsys, ["--skip-preflight"], models_arg=roster)
    assert code == 0
    assert list((h.repo / ".adversarial-spec-checkpoints").glob("*round-*.md"))


def test_setup_timeout_before_ready_is_refusal(h, monkeypatch):
    """Review item 4: a sandbox that never reaches READY before the timeout is a refusal (one launch, no retry, no
    STOP); paired: TC-6.2 negative, a ready critic that hangs is an ordinary retried timeout."""
    import agy_sandbox
    import models

    monkeypatch.setattr(agy_sandbox, "_LAUNCHER", "sleep 30\n" + agy_sandbox._LAUNCHER)
    with pytest.raises(agy_sandbox.AgyDispatchRefusedError, match="sandbox setup"):
        models.call_single_model(AGY_MODEL, "# spec", 1, "spec", timeout=2, cwd=str(h.repo))
    assert h.agy_launches == 1
    assert h.incidents() == [] and not (h.state() / "stop.json").exists()


# -- Re-review of 4c1e099: N1, N2, gauntlet refusal (orchestration/review-codex-4c1e099.md) ------------


def test_unpersisted_stop_blocks_and_evidence_is_never_reclaimed(h, monkeypatch):
    """N1: STOP state AND retention marker both unwritable after a critic write -> STOP, workspace kept, a fresh
    process is refused with zero launches, and stale cleanup never reclaims that evidence even once its owner is
    dead. Paired: a dead-owner root with an empty workspace in the same base is reclaimed."""
    import agy_sandbox

    real_write_text = Path.write_text

    def fail_state(*_a, **_k):
        raise OSError("induced ENOSPC in STOP state")

    def fail_marker(path, *args, **kwargs):
        if path.name == agy_sandbox.RETAINED_MARKER:
            raise OSError("induced ENOSPC in retention marker")
        return real_write_text(path, *args, **kwargs)

    h.behave(default={"steps": [_write_ws()]})
    with monkeypatch.context() as m:
        m.setattr(agy_sandbox, "_write_json", fail_state)
        m.setattr(Path, "write_text", fail_marker)
        with pytest.raises(agy_sandbox.AgyStop) as info:
            _dispatch(h)
    assert info.value.kind == "critic"
    [root] = list(h.base.glob("agy-dispatch-*"))
    assert (root / "ws" / "notes.md").read_text() == "critic wrote this"
    assert not (root / agy_sandbox.RETAINED_MARKER).exists()
    blocked = _fresh_process_dispatch(h, h.repo).stdout
    assert "STOP blocked" in blocked and "LAUNCHES=0" in blocked
    (root / "owner.pid").write_text("999999999")
    empty = h.base / "agy-dispatch-empty-dead"
    (empty / "ws").mkdir(parents=True)
    (empty / "owner.pid").write_text("999999999")
    agy_sandbox._cleanup_stale_roots(h.base)
    assert (root / "ws" / "notes.md").read_text() == "critic wrote this"
    assert not empty.exists()


def test_provisional_stop_resolves_to_incident_and_keeps_late_sibling_output(h, monkeypatch):
    """N2: a queued agy seat that hits the provisional latch while the writer's incident is still being recorded
    must not become the round's STOP: the raised STOP names the recorded incident and a late sibling's output is
    quarantined there, never dropped. Paired: TC-1.2 (no race) quarantines as before."""
    import agy_sandbox
    import models

    recording = threading.Event()
    second_stopped = threading.Event()
    real_record = agy_sandbox.record_incident
    real_call = models.call_single_model

    def slow_record(*args, **kwargs):
        recording.set()
        assert second_stopped.wait(10)
        time.sleep(0.2)
        return real_record(*args, **kwargs)

    def ordered_call(model, *args, **kwargs):
        if model == AGY_MODEL_B:
            assert recording.wait(10)
            try:
                return real_call(model, *args, **kwargs)
            finally:
                second_stopped.set()
        return real_call(model, *args, **kwargs)

    monkeypatch.setattr(agy_sandbox, "record_incident", slow_record)
    monkeypatch.setattr(models, "call_single_model", ordered_call)
    h.behave(default={"steps": [_write_ws()]})
    h.claude_delay.write_text("1")
    with pytest.raises(agy_sandbox.AgyStop) as info:
        models.call_models_parallel([AGY_MODEL, AGY_MODEL_B, "claude-cli/claude-opus-5-5"],
                                    "# spec", 1, "spec", timeout=30, cwd=str(h.repo))
    [incident] = h.incidents()
    assert info.value.kind == "critic"
    assert info.value.incident_dir == incident["_dir"]
    quarantined = list((incident["_dir"] / "quarantine").glob("*.json"))
    assert len(quarantined) == 1 and "fake claude critique" in quarantined[0].read_text()
    assert h.agy_launches == 1


def _gauntlet_callers():
    from gauntlet import phase_1_attacks as p1
    from gauntlet import phase_2_synthesis as p2
    from gauntlet import phase_3_filtering as p3
    from gauntlet import phase_4_evaluation as p4
    from gauntlet import phase_5_rebuttals as p5
    from gauntlet import phase_6_adjudication as p6
    from gauntlet import phase_7_final_boss as p7
    from gauntlet.core_types import Concern, Evaluation, GauntletConfig, Rebuttal

    cfg = GauntletConfig(timeout=30)
    concern = Concern(adversary="minimalist", text="The spec never bounds the retry budget of the critic dispatch.")
    dismissed = Evaluation(concern=concern, verdict="dismissed", reasoning="covered in section 4")
    sustained = Rebuttal(evaluation=dismissed, response="CHALLENGED: section 4 does not bound it", sustained=True)
    return {
        "phase_1_attacks": (p1, lambda: p1.generate_attacks("# spec", ["minimalist"], [AGY_MODEL], cfg)),
        "phase_2_synthesis": (p2, lambda: p2.generate_big_picture_synthesis([concern], AGY_MODEL, cfg)),
        "phase_3_filtering": (p3, lambda: p3.find_matching_explanation(concern.text, "minimalist", AGY_MODEL,
                                                                        None, cfg)),
        "phase_4_evaluation": (p4, lambda: p4.evaluate_concerns("# spec", [concern], AGY_MODEL, cfg)),
        "phase_4_multi_model": (p4, lambda: p4.evaluate_concerns_multi_model("# spec", [concern],
                                                                              [AGY_MODEL, AGY_MODEL_B], cfg)),
        "phase_5_rebuttals": (p5, lambda: p5.run_rebuttals([dismissed], AGY_MODEL, cfg)),
        "phase_6_adjudication": (p6, lambda: p6.final_adjudication("# spec", [sustained], AGY_MODEL, cfg)),
        "phase_7_final_boss": (p7, lambda: p7.run_final_boss_review("# spec", "summary", [concern], [dismissed],
                                                                     cfg)),
    }


@pytest.mark.parametrize("caller", ["phase_1_attacks", "phase_2_synthesis", "phase_3_filtering",
                                    "phase_4_evaluation", "phase_4_multi_model", "phase_5_rebuttals",
                                    "phase_6_adjudication", "phase_7_final_boss"])
def test_every_gauntlet_caller_propagates_refusal(monkeypatch, caller):
    """Gauntlet refusal residue: a typed agy refusal escapes every gauntlet model caller (it is never converted
    into an empty or fallback result); paired: an ordinary transient failure is still absorbed by that caller."""
    import agy_sandbox

    module, invoke = _gauntlet_callers()[caller]
    if caller == "phase_3_filtering":
        monkeypatch.setattr(module, "load_resolved_concerns", lambda: {"concerns": [
            {"adversary": "minimalist", "pattern": "retry budget", "explanation": "bounded in section 4"}]})
        monkeypatch.setattr(module, "calculate_explanation_confidence", lambda *_a, **_k: (1.0, "offline"))
    if caller == "phase_7_final_boss":
        monkeypatch.setattr(module, "select_eval_model", lambda: AGY_MODEL)

    def refuse(*_a, **_k):
        raise agy_sandbox.AgyDispatchRefusedError("agy dispatch refused: sandbox setup failed (rc=1): induced")

    def ordinary(*_a, **_k):
        raise RuntimeError("ordinary transient failure")

    monkeypatch.setattr(module, "call_model", refuse)
    with pytest.raises(agy_sandbox.AgyDispatchRefusedError):
        invoke()
    monkeypatch.setattr(module, "call_model", ordinary)
    invoke()


def test_gauntlet_dispatch_refusal_refuses_run(h, monkeypatch):
    """Gauntlet refusal residue, end to end: a sandbox refusal at attack dispatch exits 6 with the manifest marked
    agy_refused, before the phase-1 checkpoint, with one launch and no STOP state; paired: the same run with a
    working sandbox reaches the phase-1 checkpoint."""
    import agy_sandbox
    from gauntlet import orchestrator, persistence

    monkeypatch.chdir(h.repo)
    for name, rel in (("STATS_DIR", "stats"), ("STATS_FILE", "stats/adversary_stats.json"),
                      ("RUNS_DIR", "stats/runs"), ("MEDALS_DIR", "stats/medals"),
                      ("RESOLVED_CONCERNS_FILE", "stats/resolved_concerns.json")):
        monkeypatch.setattr(persistence, name, h.root / rel)
    reached: list[str] = []

    def checkpoint_sentinel(*args, **_kwargs):
        reached.append(str(args[1]) if len(args) > 1 else "?")
        raise RuntimeError("REACHED_PHASE_1_CHECKPOINT")

    monkeypatch.setattr(orchestrator, "save_checkpoint", checkpoint_sentinel)
    real_build = agy_sandbox.build_bwrap_argv

    def broken(*args, **kwargs):
        argv = real_build(*args, **kwargs)
        return argv[:1] + ["--ro-bind", str(h.root / "does-not-exist"), "/nonexistent-mount"] + argv[1:]

    monkeypatch.setattr(agy_sandbox, "build_bwrap_argv", broken)
    run = dict(adversaries=["minimalist"], attack_models=[AGY_MODEL], eval_models=[AGY_MODEL], unattended=True,
               timeout=30)
    with pytest.raises(SystemExit) as info:
        orchestrator.run_gauntlet("# Spec\n\nsmall spec", **run)
    assert info.value.code == 6
    assert reached == [] and h.agy_launches == 1
    manifests = list((h.repo / ".adversarial-spec-gauntlet").glob("run-manifest-*.json"))
    assert [json.loads(m.read_text()).get("status") for m in manifests] == ["agy_refused"]
    assert h.incidents() == [] and not (h.state() / "stop.json").exists()
    monkeypatch.setattr(agy_sandbox, "build_bwrap_argv", real_build)
    h.behave(default={"stdout": "[]"})
    with pytest.raises(RuntimeError, match="REACHED_PHASE_1_CHECKPOINT"):
        orchestrator.run_gauntlet("# Spec\n\nsmall spec", **run)
    assert reached == ["phase_1"]
