#!/usr/bin/env python3
"""Sandboxed Antigravity (``agy``) critic dispatch and its terminal STOP contract.

Every agy launch, preflight included, runs inside a bubblewrap sandbox. The whole filesystem is bound
read-only; the only writable surface is a fresh per-dispatch workspace outside every repository. The
prompt and inputs are bound read-only into that workspace. Host service sockets are masked (herdr,
``/run/user/<uid>``, ``/tmp``) and the environment is an allowlist. agy's own ``--sandbox`` flag is not an
isolation boundary (2026-07-19/20 incidents), so this module never falls back to an unsandboxed launch.

Attribution is structural, not timing-based:

* a write retained in the critic workspace is a critic mutation -> ``AgyStop(kind="critic")``;
* evidence that the boundary itself failed (the in-sandbox write probe succeeds, or the read-only
  sentinel changes) -> ``AgyStop(kind="boundary_failure")``;
* a change in the watched repository during the window belongs to a co-tenant: it is logged to
  ``windows.jsonl`` and never reverted, blamed on the critic, or halting;
* write attempts the kernel blocked (visible in agy stderr) are logged, not halting.

A STOP is terminal. ``AgyStop`` derives from ``BaseException`` so no ``except Exception`` handler can
absorb or retry it. It latches the process, and a durable record in the repository's git common dir
blocks every worktree of that repository in any later process until a logged operator clear. Incident
directories are the authority: a missing ``stop.json`` with an uncleared incident is a ``tamper`` STOP.

Refusals (``AgyDispatchRefusedError``: sandbox unavailable, bwrap setup failure, no git repository) launch
no critic and write no durable record. Operator rulings: orchestration/redirect-focused-fix-2026-09-24.md.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

STATE_DIRNAME = "adversarial-spec-agy"
DISPATCH_BASE_ENV = "ADVSPEC_AGY_DISPATCH_BASE"
DISPATCH_PREFIX = "agy-dispatch-"
INLINE_PROMPT_MAX = 100_000  # argv headroom under Linux MAX_ARG_STRLEN (131072) for one string
BOUNDARY_PROBE_ENABLED = True
READY_MARKER = "ADVSPEC_SANDBOX_READY"
PROBE_MARKER = "ADVSPEC_BOUNDARY_PROBE_WRITABLE"
PROBE_EXIT = 97

# agy reads an oversized prompt from a file; the path must be absolute and the model must use its
# built-in viewer (a terminal `cat` is in the auto-denied "command" permission class).
POINTER_PROMPT_TMPL = (
    "Using your built-in file viewing tool (never a terminal command), read the file at the absolute "
    "path {prompt_path} and follow the instructions embedded in it exactly. It contains your full system "
    "instructions and task. Write your ENTIRE response to stdout as your final response text; do not "
    "write any files and do not read anything else."
)

ENV_ALLOWLIST = (
    "HOME", "USER", "LOGNAME", "PATH", "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "TZ", "TERM",
    "http_proxy", "https_proxy", "no_proxy", "all_proxy",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS",
)
# Operator ruling R2-1: config dirs are read-only; these agy runtime paths are throwaway per dispatch.
GEMINI_CLI_THROWAWAY_DIRS = (
    "brain", "conversations", "log", "cache", "scratch", "presence", "crashes", "annotations",
    "implicit", "knowledge",
)
GEMINI_CLI_THROWAWAY_FILES = ("history.jsonl", "conversation_summaries.db")
HIDDEN_HOME_DIRS = (".gemini/antigravity-browser-profile",)
SOCKET_HOME_DIRS = (".config/herdr",)

STOP_MESSAGE_TEMPLATE = (
    "AGY_STOP [{kind}]: {summary}\n"
    "  Evidence: {incident_dir}\n"
    "  Stop record: {record}\n"
    "  No Antigravity dispatch will run in this repository (any worktree, any process) until the operator\n"
    "  reviews the evidence and clears it:\n"
    "    {clear_cmd}\n"
    "  Do not retry, re-run the round, or substitute another critic. Report this STOP and halt."
)

_BLOCKED_WRITE_RE = re.compile(r"read-only file system|\bEROFS\b", re.IGNORECASE)
_LAUNCHER = r"""
S="$1"; R="$2"; N="$3"; P="$4"; shift 4
if [ "$P" = 1 ]; then
  if ( : >> "$S" ) 2>/dev/null; then echo "ADVSPEC_BOUNDARY_PROBE_WRITABLE sentinel" >&2; exit 97; fi
  if ( : >> "$R/.advspec-boundary-probe-$N" ) 2>/dev/null; then
    rm -f "$R/.advspec-boundary-probe-$N"
    echo "ADVSPEC_BOUNDARY_PROBE_WRITABLE repo" >&2
    exit 97
  fi
fi
echo "ADVSPEC_SANDBOX_READY $N" >&2
exec "$@"
"""


class AgyStop(BaseException):
    """Terminal Antigravity STOP. Never retried; not absorbable by ``except Exception``.

    ``kind``: ``critic`` | ``boundary_failure`` | ``tamper`` (new incident this process),
    ``blocked`` (a prior uncleared STOP exists), ``latched`` (this process already stopped).
    """

    def __init__(
        self,
        kind: str,
        message: str,
        *,
        incident_id: Optional[str] = None,
        incident_dir: Optional[Path] = None,
        repo_root: Optional[Path] = None,
        record: Optional[Path] = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.incident_id = incident_id
        self.incident_dir = incident_dir
        self.repo_root = repo_root
        self.record = record

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else self.kind


class AgyDispatchRefusedError(RuntimeError):
    """The dispatch was refused before any critic started. No durable record; never retried."""


class ClearRefusedError(RuntimeError):
    """An operator clear did not match the uncleared incident set."""


@dataclass
class DispatchLayout:
    base: Path
    root: Path
    ws: Path
    inputs: Path
    ws_inputs: Path
    prompt_file: Path
    sentinel: Path
    sentinel_bytes: bytes
    throwaway: Path
    nonce: str


_PROCESS_LOCK = threading.Lock()
_LATCH: Optional[AgyStop] = None
_AVAILABILITY: dict[str, Optional[str]] = {}


def _reset_process_state_for_tests() -> None:
    """Forget the in-process latch and availability cache (simulates a fresh process)."""
    global _LATCH
    with _PROCESS_LOCK:
        _LATCH = None
        _AVAILABILITY.clear()


def _set_latch(stop: AgyStop) -> None:
    global _LATCH
    with _PROCESS_LOCK:
        if _LATCH is None:
            _LATCH = stop


def _latched() -> Optional[AgyStop]:
    with _PROCESS_LOCK:
        return _LATCH


# ── environment and repository discovery ───────────────────────────────────────────────────────


def sandbox_unavailable_reason() -> Optional[str]:
    """Return why the sandbox cannot run on this host, or ``None`` when it can."""
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        return "bwrap not found on PATH (install bubblewrap); agy dispatch refuses without a sandbox"
    with _PROCESS_LOCK:
        if bwrap in _AVAILABILITY:
            return _AVAILABILITY[bwrap]
    probe = subprocess.run(
        [bwrap, "--ro-bind", "/", "/", "--unshare-pid", "--die-with-parent", "true"],
        capture_output=True, text=True, timeout=30,
    )
    reason = None
    if probe.returncode != 0:
        detail = (probe.stderr or "").strip()[:300]
        reason = f"bwrap cannot create a sandbox (unprivileged user namespaces unavailable?): {detail}"
    with _PROCESS_LOCK:
        _AVAILABILITY[bwrap] = reason
    return reason


def _git_paths(cwd: Optional[str | Path]) -> tuple[Path, Path]:
    where = str(cwd) if cwd else os.getcwd()
    proc = subprocess.run(
        ["git", "-C", where, "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir"],
        capture_output=True, text=True,
    )
    lines = proc.stdout.strip().splitlines()
    if proc.returncode != 0 or len(lines) != 2:
        raise AgyDispatchRefusedError(
            f"agy dispatch refused: {where} is not inside a git repository; the per-repository stop "
            "record needs one"
        )
    return Path(lines[0]), Path(lines[1])


def stop_state_dir(cwd: Optional[str | Path]) -> Path:
    """Stop-state directory for the repository containing ``cwd`` (shared by all its worktrees)."""
    return _git_paths(cwd)[1] / STATE_DIRNAME


def _dispatch_base() -> Path:
    override = os.environ.get(DISPATCH_BASE_ENV)
    return Path(override) if override else Path.home() / ".cache" / "adversarial-spec" / "agy-dispatch"


# ── durable stop state ─────────────────────────────────────────────────────────────────────────


@contextlib.contextmanager
def _locked(state: Path) -> Iterator[None]:
    state.mkdir(parents=True, exist_ok=True)
    with open(state / "lock", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _incident_ids(state: Path) -> list[str]:
    root = state / "incidents"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "incident.json").is_file())


def _cleared_ids(state: Path) -> set[str]:
    cleared: set[str] = set()
    log = state / "clears.jsonl"
    if not log.exists():
        return cleared
    for line in log.read_text().splitlines():
        try:
            cleared.update(json.loads(line).get("incidents", []))
        except (json.JSONDecodeError, AttributeError):
            continue  # an unreadable clear entry clears nothing (fail closed)
    return cleared


def _uncleared(state: Path) -> list[str]:
    cleared = _cleared_ids(state)
    return [i for i in _incident_ids(state) if i not in cleared]


def _clear_command(repo_root: Path, ids: list[str]) -> str:
    script = Path(__file__).resolve()
    incidents = " ".join(f"--incident {i}" for i in ids) or "--incident <id>"
    return (f"python3 {script} clear --repo {repo_root} {incidents} "
            "--operator <name> --reason '<what you reviewed>'")


def _stop_message(kind: str, summary: str, repo_root: Path, state: Path, incident_dir, ids: list[str]) -> str:
    return STOP_MESSAGE_TEMPLATE.format(
        kind=kind,
        summary=summary,
        incident_dir=incident_dir if incident_dir else state / "incidents",
        record=state / "stop.json",
        clear_cmd=_clear_command(repo_root, ids),
    )


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)


def _admit(repo_root: Path, common_dir: Path) -> None:
    """Refuse (``AgyStop``) while the repository has an uncleared STOP; detect record tampering."""
    state = common_dir / STATE_DIRNAME
    if not state.exists():
        return
    with _locked(state):
        record = state / "stop.json"
        uncleared = _uncleared(state)
        if record.exists():
            try:
                json.loads(record.read_text())
                summary = f"prior STOP in this repository; uncleared incident(s): {', '.join(uncleared) or 'none'}"
            except (OSError, json.JSONDecodeError) as exc:
                summary = f"stop record {record} is unreadable ({exc}); refusing (fail closed)"
            raise AgyStop("blocked", _stop_message("blocked", summary, repo_root, state, None, uncleared),
                          repo_root=repo_root, record=record)
        if uncleared:
            _write_json(record, {"incidents": uncleared, "kind": "tamper", "recreated_at": _now(),
                                 "note": "stop record was missing without a logged clear"})
            summary = (f"stop record was deleted without a logged operator clear; uncleared incident(s): "
                       f"{', '.join(uncleared)}")
            raise AgyStop("tamper", _stop_message("tamper", summary, repo_root, state, None, uncleared),
                          repo_root=repo_root, record=record)


def check_admission(cwd: Optional[str | Path]) -> None:
    """Public pre-round check: raise ``AgyStop`` if the repository at ``cwd`` is stopped."""
    stop = _latched()
    if stop is not None:
        raise _latched_stop(stop)
    repo_root, common = _git_paths(cwd)
    try:
        _admit(repo_root, common)
    except AgyStop as stop:
        _set_latch(stop)
        raise


def _capture_workspace(ws: Path, dest: Path, paths: list[str]) -> None:
    for rel in paths:
        src = ws / rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            target.with_name(target.name + ".symlink").write_text(os.readlink(src))
        elif src.is_file():
            shutil.copyfile(src, target)
        elif src.is_dir():
            target.mkdir(exist_ok=True)


def record_incident(
    cwd: str | Path,
    *,
    kind: str,
    model: str,
    stdout: str,
    stderr: str,
    workspace: Optional[Path] = None,
    paths: Optional[list[str]] = None,
    note: str = "",
) -> tuple[str, Path, bool, list[str]]:
    """Persist an incident plus the stop record. Returns (id, dir, evidence_complete, errors)."""
    repo_root, common = _git_paths(cwd)
    state = common / STATE_DIRNAME
    paths = sorted(paths or [])
    errors: list[str] = []
    with _locked(state):
        incident_id = f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{kind}-{secrets.token_hex(3)}"
        incident_dir = state / "incidents" / incident_id
        incident_dir.mkdir(parents=True)
        meta = {"id": incident_id, "kind": kind, "model": model, "time": _now(), "repo_root": str(repo_root),
                "paths": paths, "note": note, "evidence": "pending"}
        _write_json(incident_dir / "incident.json", meta)
        try:
            (incident_dir / "agy-stdout.txt").write_text(stdout or "")
            (incident_dir / "agy-stderr.txt").write_text(stderr or "")
            if workspace is not None and paths:
                _capture_workspace(workspace, incident_dir / "workspace", paths)
            meta["evidence"] = "complete"
        except OSError as exc:
            errors.append(f"evidence incomplete: {exc}")
            meta["evidence"] = f"incomplete: {exc}"
        with contextlib.suppress(OSError):
            _write_json(incident_dir / "incident.json", meta)
        try:
            record = state / "stop.json"
            existing: list[str] = []
            with contextlib.suppress(OSError, json.JSONDecodeError, AttributeError):
                existing = list(json.loads(record.read_text()).get("incidents", []))
            _write_json(record, {"incidents": sorted(set(existing) | {incident_id}), "latest": incident_id,
                                 "kind": kind, "updated_at": _now()})
        except OSError as exc:
            errors.append(f"stop record not written: {exc}")
    return incident_id, incident_dir, not errors, errors


def quarantine_result(stop: AgyStop, name: str, payload: dict) -> None:
    """Keep a sibling result that finished after a STOP as evidence; it is never synthesized."""
    base = stop.incident_dir
    if base is None:
        return
    target = Path(base) / "quarantine"
    with contextlib.suppress(OSError):
        target.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        (target / f"{safe}.json").write_text(json.dumps(payload, indent=2))


def clear_stop(cwd: str | Path, incident_ids: list[str], operator: str, reason: str) -> dict:
    """Operator clear: must name exactly the uncleared incident set. Evidence is never deleted."""
    repo_root, common = _git_paths(cwd)
    state = common / STATE_DIRNAME
    if not operator.strip() or not reason.strip():
        raise ClearRefusedError("clear requires --operator and a non-empty --reason")
    with _locked(state):
        uncleared = _uncleared(state)
        if sorted(set(incident_ids)) != uncleared:
            raise ClearRefusedError(
                f"clear must name exactly the uncleared incident set {uncleared}; got {sorted(set(incident_ids))}"
            )
        entry = {"time": _now(), "incidents": uncleared, "operator": operator.strip(), "reason": reason.strip(),
                 "repo_root": str(repo_root)}
        with open(state / "clears.jsonl", "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        (state / "stop.json").unlink(missing_ok=True)
    return entry


# ── dispatch ───────────────────────────────────────────────────────────────────────────────────


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _cleanup_stale_roots(base: Path) -> None:
    """Remove dispatch roots left by dead processes (operator ruling R2-4: best effort)."""
    if not base.is_dir():
        return
    for root in base.glob(f"{DISPATCH_PREFIX}*"):
        try:
            pid = int((root / "owner.pid").read_text().strip())
        except (OSError, ValueError):
            if time.time() - root.stat().st_mtime < 86400:
                continue
            pid = -1
        if pid <= 0 or not _pid_alive(pid):
            shutil.rmtree(root, ignore_errors=True)


def _prepare_dispatch_root(base: Path, full_prompt: str) -> DispatchLayout:
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = Path(tempfile.mkdtemp(prefix=DISPATCH_PREFIX, dir=base))
    (root / "owner.pid").write_text(str(os.getpid()))
    ws = root / "ws"
    inputs = root / "inputs"
    ws_inputs = ws / "inputs"
    throwaway = root / "throwaway"
    for d in (ws, inputs, ws_inputs, throwaway):
        d.mkdir(mode=0o700)
    prompt_file = inputs / "prompt.md"
    prompt_file.write_text(full_prompt, encoding="utf-8")
    sentinel = root / "sentinel"
    sentinel_bytes = secrets.token_bytes(32)
    sentinel.write_bytes(sentinel_bytes)
    return DispatchLayout(base=base, root=root, ws=ws, inputs=inputs, ws_inputs=ws_inputs,
                          prompt_file=ws_inputs / "prompt.md", sentinel=sentinel, sentinel_bytes=sentinel_bytes,
                          throwaway=throwaway, nonce=secrets.token_hex(8))


def build_bwrap_argv(layout: DispatchLayout, repo_root: Path) -> list[str]:
    """bwrap options (without the command). Everything read-only except the dispatch workspace."""
    home = Path.home()
    argv = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
            "--unshare-pid", "--unshare-ipc", "--die-with-parent", "--new-session", "--clearenv"]
    for key in ENV_ALLOWLIST:
        if key in os.environ:
            argv += ["--setenv", key, os.environ[key]]
    argv += ["--setenv", "TMPDIR", "/tmp"]
    run_user = Path(f"/run/user/{os.getuid()}")
    masks = [run_user] + [home / rel for rel in SOCKET_HOME_DIRS + HIDDEN_HOME_DIRS]
    cli = home / ".gemini" / "antigravity-cli"
    masks += [cli / d for d in GEMINI_CLI_THROWAWAY_DIRS]
    for path in masks:
        if path.is_dir() and not path.is_symlink():
            argv += ["--tmpfs", str(path)]
    for name in GEMINI_CLI_THROWAWAY_FILES:
        target = cli / name
        if target.is_file() and not target.is_symlink():
            scratch = layout.throwaway / name
            scratch.write_bytes(b"")
            argv += ["--bind", str(scratch), str(target)]
    argv += ["--tmpfs", str(layout.base)]
    argv += ["--bind", str(layout.ws), str(layout.ws)]
    argv += ["--ro-bind", str(layout.inputs), str(layout.ws_inputs)]
    argv += ["--ro-bind", str(layout.sentinel), str(layout.sentinel)]
    argv += ["--chdir", str(layout.ws)]
    return argv


def _workspace_delta(layout: DispatchLayout) -> list[str]:
    delta: list[str] = []
    for dirpath, dirnames, filenames in os.walk(layout.ws, followlinks=False):
        current = Path(dirpath)
        rel_dir = current.relative_to(layout.ws)
        for name in filenames:
            delta.append(str(rel_dir / name) if str(rel_dir) != "." else name)
        for name in list(dirnames):
            full = current / name
            rel = full.relative_to(layout.ws)
            if full.is_symlink():
                delta.append(str(rel))
                dirnames.remove(name)
            elif full == layout.ws_inputs:
                if any(full.iterdir()):
                    delta.append(str(rel))
            elif not any(full.iterdir()):
                delta.append(str(rel))
    return sorted(delta)


def _porcelain_state(repo_root: Path) -> dict[str, Optional[tuple[int, int]]]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True,
    )
    fields = proc.stdout.decode(errors="surrogateescape").split("\0")
    paths: set[str] = set()
    i = 0
    while i < len(fields):
        field = fields[i]
        if field:
            paths.add(field[3:])
            if field[0] in "RC":
                i += 1
                if i < len(fields) and fields[i]:
                    paths.add(fields[i])
        i += 1
    state: dict[str, Optional[tuple[int, int]]] = {}
    for rel in paths:
        try:
            st = os.lstat(repo_root / rel)
            state[rel] = (st.st_size, st.st_mtime_ns)
        except OSError:
            state[rel] = None
    return state


def _cotenant_delta(before: dict, after: dict) -> list[str]:
    changed = []
    for rel in set(before) | set(after):
        if before.get(rel, "absent") != after.get(rel, "absent"):
            changed.append(rel)
    return sorted(changed)


def _log_window(common: Path, entry: dict) -> None:
    state = common / STATE_DIRNAME
    with contextlib.suppress(OSError), _locked(state):
        with open(state / "windows.jsonl", "a") as fh:
            fh.write(json.dumps(entry) + "\n")


def _latched_stop(original: AgyStop) -> AgyStop:
    message = (f"AGY_STOP [latched]: this process already stopped ({original.kind}); no further Antigravity "
               f"dispatch will start in it.\n{original}")
    return AgyStop("latched", message, incident_id=original.incident_id, incident_dir=original.incident_dir,
                   repo_root=original.repo_root, record=original.record)


def _decode(stream) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode(errors="replace")
    return stream


def _strip_markers(stderr: str) -> str:
    return "\n".join(
        line for line in stderr.splitlines() if not line.startswith((READY_MARKER, PROBE_MARKER))
    )


def run_agy_dispatch(
    *,
    model: str,
    agy_model: str,
    full_prompt: str,
    timeout: int,
    cwd: Optional[str | Path],
) -> subprocess.CompletedProcess:
    """Run one agy critic inside the sandbox.

    Returns the CompletedProcess (stderr stripped of launcher markers; rc may be non-zero).
    Raises ``AgyStop`` (terminal), ``AgyDispatchRefusedError`` (nothing ran), or ``RuntimeError`` on a clean
    timeout (retryable).
    """
    latched = _latched()
    if latched is not None:
        raise _latched_stop(latched)
    reason = sandbox_unavailable_reason()
    if reason is not None:
        raise AgyDispatchRefusedError(f"agy dispatch refused: {reason}")
    repo_root, common = _git_paths(cwd)
    base = _dispatch_base().resolve()
    if base == repo_root or repo_root in base.parents:
        raise AgyDispatchRefusedError(f"agy dispatch refused: dispatch base {base} is inside repository {repo_root}")
    try:
        _admit(repo_root, common)
    except AgyStop as stop:
        _set_latch(stop)
        raise
    _cleanup_stale_roots(base)
    layout = _prepare_dispatch_root(base, full_prompt)
    keep_root = False
    try:
        if len(full_prompt.encode("utf-8")) > INLINE_PROMPT_MAX:
            prompt_arg = POINTER_PROMPT_TMPL.format(prompt_path=layout.prompt_file)
        else:
            prompt_arg = full_prompt
        agy_args = ["agy", "--model", agy_model, "--mode", "plan", "--sandbox",
                    "--print-timeout", f"{timeout}s", "--prompt", prompt_arg]
        launcher = ["/bin/sh", "-c", _LAUNCHER, "advspec-agy-launcher", str(layout.sentinel), str(repo_root),
                    layout.nonce, "1" if BOUNDARY_PROBE_ENABLED else "0"]
        argv = build_bwrap_argv(layout, repo_root) + launcher + agy_args
        try:  # re-check immediately before launch: a STOP made durable meanwhile blocks this launch
            _admit(repo_root, common)
        except AgyStop as stop:
            _set_latch(stop)
            raise
        before = _porcelain_state(repo_root)
        timed_out = False
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            stdout, raw_stderr, rc = result.stdout or "", result.stderr or "", result.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout, raw_stderr, rc = _decode(exc.stdout), _decode(exc.stderr), -9
        after = _porcelain_state(repo_root)
        stderr = _strip_markers(raw_stderr)
        ready = f"{READY_MARKER} {layout.nonce}" in raw_stderr
        probe_failed = PROBE_MARKER in raw_stderr
        try:
            sentinel_changed = layout.sentinel.read_bytes() != layout.sentinel_bytes
        except OSError:
            sentinel_changed = True
        delta = _workspace_delta(layout)

        kind = None
        if probe_failed or sentinel_changed:
            kind = "boundary_failure"
            note = "in-sandbox write probe succeeded" if probe_failed else "read-only sentinel changed"
        elif delta:
            kind = "critic"
            note = "critic wrote into its dispatch workspace"
        if kind is not None:
            incident_id, incident_dir, complete, errors = record_incident(
                repo_root, kind=kind, model=model, stdout=stdout, stderr=raw_stderr,
                workspace=layout.ws, paths=delta, note=note,
            )
            keep_root = not complete
            summary = f"{note}; {len(delta)} workspace path(s)"
            if errors:
                summary += "; " + "; ".join(errors) + f"; workspace kept at {layout.ws}"
            state = common / STATE_DIRNAME
            stop = AgyStop(kind, _stop_message(kind, summary, repo_root, state, incident_dir, [incident_id]),
                           incident_id=incident_id, incident_dir=incident_dir, repo_root=repo_root,
                           record=state / "stop.json")
            _set_latch(stop)
            raise stop

        blocked = [line for line in stderr.splitlines() if _BLOCKED_WRITE_RE.search(line)]
        cotenant = _cotenant_delta(before, after)
        if blocked or cotenant:
            _log_window(common, {"time": _now(), "model": model, "co_tenant": cotenant,
                                 "blocked_write_attempts": blocked})
            if blocked:
                print(f"Warning: {model} attempted {len(blocked)} blocked write(s); logged in "
                      f"{common / STATE_DIRNAME / 'windows.jsonl'}", file=sys.stderr)
        if timed_out:
            raise RuntimeError(f"Antigravity CLI timed out after {timeout}s")
        if not ready:
            raise AgyDispatchRefusedError(
                f"agy dispatch refused: sandbox setup failed (rc={rc}): {stderr.strip()[:500]}"
            )
        return subprocess.CompletedProcess(argv, rc, stdout, stderr)
    finally:
        if not keep_root:
            shutil.rmtree(layout.root, ignore_errors=True)


# ── operator CLI ───────────────────────────────────────────────────────────────────────────────


def _main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Antigravity stop-state operator tools")
    sub = parser.add_subparsers(dest="action", required=True)
    status = sub.add_parser("status", help="show uncleared incidents for a repository")
    status.add_argument("--repo", default=".")
    clear = sub.add_parser("clear", help="clear the STOP after reviewing every uncleared incident")
    clear.add_argument("--repo", default=".")
    clear.add_argument("--incident", action="append", default=[], help="repeat for every uncleared incident")
    clear.add_argument("--operator", required=True)
    clear.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "status":
            state = stop_state_dir(args.repo)
            record = state / "stop.json"
            print(json.dumps({"state_dir": str(state), "stop_record_present": record.exists(),
                              "uncleared": _uncleared(state) if state.exists() else []}, indent=2))
            return 0
        entry = clear_stop(args.repo, args.incident, args.operator, args.reason)
        print(json.dumps(entry, indent=2))
        return 0
    except (ClearRefusedError, AgyDispatchRefusedError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_main())
