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

Evidence is never lost to a persistence failure: the process latches before any evidence I/O, a dispatch root
whose evidence or stop record could not be written is kept with a ``retained.json`` marker (stale cleanup skips
it), and a marker with ``stop_recorded: false`` blocks admission for its repository until an operator
``release``. The final admission check and the critic spawn run under the same lock that publishes a STOP, so
no critic starts after a STOP is published. Review dispositions: orchestration/review-codex-85da68f-dispositions.md.
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
import stat
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
RETAINED_MARKER = "retained.json"
RELEASED_MARKER = "released.json"
# A clean root is renamed to this prefix (outside the scanned DISPATCH_PREFIX glob) before it is deleted, so no
# scan ever sees a half-deleted root.
RECLAIM_PREFIX = ".reclaim-"
DISPATCH_INFO = "dispatch.json"
# DISPATCH_INFO renamed in place when a STOP could not be persisted: a rename allocates no data, so this flag
# survives the storage failure that lost stop.json and retained.json.
UNRECORDED_MARKER = "unrecorded-stop.json"
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
        evidence_root: Optional[Path] = None,
        provisional: bool = False,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.incident_id = incident_id
        self.incident_dir = incident_dir
        self.repo_root = repo_root
        self.record = record
        self.evidence_root = evidence_root  # retained dispatch root when the evidence lives there
        self.provisional = provisional  # latched before the incident was recorded; see resolve_stop()

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


def _set_latch(stop: AgyStop, *, replace: bool = False) -> None:
    global _LATCH
    with _PROCESS_LOCK:
        if _LATCH is None or replace:
            _LATCH = stop


def _latched() -> Optional[AgyStop]:
    with _PROCESS_LOCK:
        return _LATCH


def resolve_stop(stop: AgyStop) -> AgyStop:
    """The canonical STOP for this process: the latch, once recording finished, supersedes a ``latched`` copy,
    a provisional STOP, or a sibling's ``blocked`` refusal raised while another critic's incident was pending."""
    latch = _latched()
    return latch if latch is not None and not latch.provisional else stop


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


def _root_common_dir(root: Path) -> Optional[str]:
    """The repository (git common dir) a dispatch root belongs to, or ``None`` when unknown/unreadable."""
    info = None
    for name in (DISPATCH_INFO, UNRECORDED_MARKER):
        try:
            info = json.loads((root / name).read_text())
            break
        except (OSError, json.JSONDecodeError):
            continue
    value = info.get("common_dir") if isinstance(info, dict) else None
    return value if isinstance(value, str) else None


def _root_holds_evidence(root: Path) -> bool:
    """True when a dispatch root's workspace holds anything a critic could have left (or cannot be inspected)."""
    ws = root / "ws"
    if not os.path.lexists(ws):
        return False
    delta, errors = _workspace_delta(ws, check_mode=(root / DISPATCH_INFO).exists())
    # A clean sibling may delete its own root while this scan runs; a workspace that vanished held nothing.
    # (Evidence roots are never deleted: cleanup skips them and only an operator release frees them.)
    return bool(delta or errors) and os.path.lexists(ws)


def _evidence_roots(common_dir: Path) -> list[Path]:
    """Dispatch roots holding critic evidence with no durable STOP for ``common_dir`` (fail closed on doubt).

    Blocking: a retention marker with ``stop_recorded`` not true (or unreadable), and any unreleased root whose
    workspace holds evidence but carries no marker at all (the marker itself could not be written). A root that
    cannot be attributed to a repository blocks every repository.
    """
    base = _dispatch_base()
    if not base.is_dir():
        return []
    found = []
    for root in sorted(base.glob(f"{DISPATCH_PREFIX}*")):
        if (root / RELEASED_MARKER).exists():
            continue
        if (root / UNRECORDED_MARKER).exists():
            owner = _root_common_dir(root)
            if (owner is None or owner == str(common_dir)) and os.path.lexists(root):
                found.append(root)
            continue
        marker_path = root / RETAINED_MARKER
        if marker_path.exists():
            try:
                marker = json.loads(marker_path.read_text())
            except (OSError, json.JSONDecodeError):
                if os.path.lexists(root):  # a root released and reclaimed mid-scan is not evidence
                    found.append(root)
                continue
            if not isinstance(marker, dict) or (marker.get("stop_recorded") is False and
                                                marker.get("common_dir") in (None, str(common_dir))):
                found.append(root)
            continue
        if _root_holds_evidence(root):
            owner = _root_common_dir(root)
            # Unknown ownership blocks every repository, but only for a root that still exists.
            if (owner is None or owner == str(common_dir)) and os.path.lexists(root):
                found.append(root)
    return found


def _admit(repo_root: Path, common_dir: Path, *, held: bool = False) -> None:
    """Refuse (``AgyStop``) while the repository has an uncleared STOP; detect record tampering.

    ``held``: the caller already holds the stop-state lock (final pre-launch check).
    """
    state = common_dir / STATE_DIRNAME
    unrecorded = _evidence_roots(common_dir)
    if unrecorded:
        roots = ", ".join(str(r) for r in unrecorded)
        summary = (f"critic evidence without a durable STOP record is retained at {roots}. After review release "
                   f"each root: python3 {Path(__file__).resolve()} release --root <root> "
                   "--operator <name> --reason '<what you reviewed>'")
        raise AgyStop("blocked", _stop_message("blocked", summary, repo_root, state, unrecorded[0], []),
                      repo_root=repo_root, record=unrecorded[0] / RETAINED_MARKER, evidence_root=unrecorded[0])
    if not state.exists():
        return
    with contextlib.nullcontext() if held else _locked(state):
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


@dataclass
class IncidentRecord:
    incident_id: str
    incident_dir: Optional[Path]
    complete: bool
    errors: list[str]
    stop_recorded: bool


def _write_stream(path: Path, data) -> None:
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data or "")


def record_incident(
    cwd: str | Path,
    *,
    kind: str,
    model: str,
    stdout,
    stderr,
    workspace: Optional[Path] = None,
    paths: Optional[list[str]] = None,
    note: str = "",
) -> IncidentRecord:
    """Persist an incident plus the stop record; never raises ``OSError`` (failures land in ``errors``).

    ``stdout``/``stderr`` may be raw bytes (kept byte-exact) or text. ``incident_dir`` is ``None`` when the
    incident directory could not be created; ``stop_recorded`` is False when ``stop.json`` was not written.
    """
    repo_root, common = _git_paths(cwd)
    state = common / STATE_DIRNAME
    paths = sorted(paths or [])
    errors: list[str] = []
    incident_id = f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{kind}-{secrets.token_hex(3)}"
    incident_dir: Optional[Path] = state / "incidents" / incident_id
    stop_recorded = False
    with contextlib.ExitStack() as stack:
        try:
            stack.enter_context(_locked(state))
        except OSError as exc:
            errors.append(f"stop-state lock unavailable: {exc}")
        meta = {"id": incident_id, "kind": kind, "model": model, "time": _now(), "repo_root": str(repo_root),
                "paths": paths, "note": note, "evidence": "pending"}
        try:
            incident_dir.mkdir(parents=True)
            _write_json(incident_dir / "incident.json", meta)
        except OSError as exc:
            errors.append(f"incident not recorded: {exc}")
            incident_dir = None
        if incident_dir is not None:
            try:
                _write_stream(incident_dir / "agy-stdout.txt", stdout)
                _write_stream(incident_dir / "agy-stderr.txt", stderr)
                if workspace is not None and paths:
                    _capture_workspace(workspace, incident_dir / "workspace", paths)
                meta["evidence"] = "complete"
            except OSError as exc:
                errors.append(f"evidence incomplete: {exc}")
                meta["evidence"] = f"incomplete: {exc}"
            try:
                _write_json(incident_dir / "incident.json", meta)
            except OSError as exc:
                errors.append(f"incident metadata not finalized: {exc}")
        try:
            record = state / "stop.json"
            existing: list[str] = []
            with contextlib.suppress(OSError, json.JSONDecodeError, AttributeError):
                existing = list(json.loads(record.read_text()).get("incidents", []))
            listed = {incident_id} if incident_dir is not None else set()
            _write_json(record, {"incidents": sorted(set(existing) | listed), "latest": incident_id,
                                 "kind": kind, "updated_at": _now(),
                                 **({} if incident_dir is not None else {"unrecorded_incident": incident_id})})
            stop_recorded = True
        except OSError as exc:
            errors.append(f"stop record not written: {exc}")
    return IncidentRecord(incident_id, incident_dir, not errors, errors, stop_recorded)


def quarantine_result(stop: AgyStop, name: str, payload: dict) -> None:
    """Keep a sibling result that finished after a STOP as evidence; it is never synthesized."""
    base = stop.incident_dir or stop.evidence_root
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    try:
        if base is None:
            raise OSError("no evidence destination for this STOP")
        target = Path(base) / "quarantine"
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{safe}.json").write_text(json.dumps(payload, indent=2))
    except OSError as exc:  # never drop it silently: the operator transcript is the last resort
        print(f"Warning: could not quarantine {name} ({exc}); payload follows:\n{json.dumps(payload)}",
              file=sys.stderr)


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


def _reclaim_root(root: Path) -> None:
    """Delete a clean dispatch root without ever exposing it half-deleted to a scan.

    The root is first renamed atomically, within the dispatch base, out of the ``agy-dispatch-*`` glob. If the
    rename fails, the root stays in place whole (the next stale cleanup retries); it is never partially deleted.
    """
    target = root.with_name(f"{RECLAIM_PREFIX}{root.name}-{os.getpid()}")
    try:
        os.rename(root, target)
    except OSError:
        return
    shutil.rmtree(target, ignore_errors=True)


def _cleanup_stale_roots(base: Path) -> None:
    """Remove dispatch roots left by dead processes (operator ruling R2-4: best effort)."""
    if not base.is_dir():
        return
    for root in base.glob(f"{DISPATCH_PREFIX}*"):
        if not (root / RELEASED_MARKER).exists():
            # Evidence is never reclaimed until an operator release: a retained root, or any root whose workspace
            # holds something a critic left (its STOP may not have persisted).
            if ((root / RETAINED_MARKER).exists() or (root / UNRECORDED_MARKER).exists()
                    or _root_holds_evidence(root)):
                continue
        try:
            pid = int((root / "owner.pid").read_text().strip())
        except (OSError, ValueError):
            try:
                if time.time() - root.stat().st_mtime < 86400:
                    continue
            except OSError:
                continue  # reclaimed by another process meanwhile
            pid = -1
        if pid <= 0 or not _pid_alive(pid):
            _reclaim_root(root)
    # Renamed roots whose deleting process died mid-rmtree (the name ends with that process's pid).
    for leftover in base.glob(f"{RECLAIM_PREFIX}*"):
        try:
            owner = int(leftover.name.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            owner = -1
        if owner <= 0 or not _pid_alive(owner):
            shutil.rmtree(leftover, ignore_errors=True)


def _prepare_dispatch_root(base: Path, full_prompt: str, common: Optional[Path] = None) -> DispatchLayout:
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = Path(tempfile.mkdtemp(prefix=DISPATCH_PREFIX, dir=base))
    (root / "owner.pid").write_text(str(os.getpid()))
    # Written before launch, so a root always names its repository even if nothing can be written at STOP time.
    (root / DISPATCH_INFO).write_text(json.dumps({"common_dir": str(common) if common else None,
                                                  "owner_pid": os.getpid(), "created": _now()}))
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


def _mask_target(path: Path, *, want_dir: bool) -> Optional[Path]:
    """Resolve a mask path through symlinks; ``None`` when nothing is reachable there.

    A symlinked mask is applied to its resolved target, which hides it under every alias. A target of the wrong
    type cannot be masked safely, so the dispatch is refused rather than launched with the path exposed.
    """
    if not os.path.lexists(path):
        return None
    resolved = path.resolve()
    if not resolved.exists():
        return None  # dangling symlink: nothing behind it to expose
    if resolved.is_dir() if want_dir else resolved.is_file():
        return resolved
    kind = "directory" if want_dir else "regular file"
    raise AgyDispatchRefusedError(
        f"agy dispatch refused: masked path {path} resolves to {resolved}, which is not a {kind}; "
        "it cannot be masked safely"
    )


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
        target = _mask_target(path, want_dir=True)
        if target is not None:
            argv += ["--tmpfs", str(target)]
    for name in GEMINI_CLI_THROWAWAY_FILES:
        target = _mask_target(cli / name, want_dir=False)
        if target is not None:
            scratch = layout.throwaway / name
            scratch.write_bytes(b"")
            argv += ["--bind", str(scratch), str(target)]
    argv += ["--tmpfs", str(layout.base)]
    argv += ["--bind", str(layout.ws), str(layout.ws)]
    argv += ["--ro-bind", str(layout.inputs), str(layout.ws_inputs)]
    argv += ["--ro-bind", str(layout.sentinel), str(layout.sentinel)]
    argv += ["--chdir", str(layout.ws)]
    return argv


def _workspace_delta(ws: Path, *, check_mode: bool = True) -> tuple[list[str], list[str]]:
    """Paths a critic left in workspace ``ws``, plus inspection failures (each one is terminal).

    ``check_mode``: the root was created by this module (mode 0700), so any other mode is a critic change.
    """
    ws_inputs = ws / "inputs"
    delta: list[str] = []
    errors: list[str] = []
    try:
        st = os.lstat(ws)
        if not stat.S_ISDIR(st.st_mode) or (check_mode and stat.S_IMODE(st.st_mode) != 0o700):
            errors.append(f"workspace root metadata changed (mode {oct(st.st_mode)})")
    except OSError as exc:
        errors.append(f"workspace root unreadable: {exc}")
    for dirpath, dirnames, filenames in os.walk(ws, followlinks=False,
                                                 onerror=lambda exc: errors.append(f"walk failed: {exc}")):
        current = Path(dirpath)
        rel_dir = current.relative_to(ws)
        for name in filenames:
            delta.append(str(rel_dir / name) if str(rel_dir) != "." else name)
        for name in list(dirnames):
            full = current / name
            rel = full.relative_to(ws)
            try:
                if full.is_symlink():
                    delta.append(str(rel))
                    dirnames.remove(name)
                elif full == ws_inputs:
                    if any(full.iterdir()):
                        delta.append(str(rel))
                elif not any(full.iterdir()):
                    delta.append(str(rel))
            except OSError as exc:
                errors.append(f"cannot inspect {rel}: {exc}")
                delta.append(str(rel))
    return sorted(delta), errors


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
                   repo_root=original.repo_root, record=original.record, evidence_root=original.evidence_root,
                   provisional=original.provisional)


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
    try:
        layout = _prepare_dispatch_root(base, full_prompt, common)
    except OSError as exc:
        raise AgyDispatchRefusedError(f"agy dispatch refused: dispatch root could not be prepared: {exc}")
    keep_reason: Optional[str] = None
    stop_recorded = True
    incident_id: Optional[str] = None
    state = common / STATE_DIRNAME
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
        before = _porcelain_state(repo_root)
        # The final admission check and the spawn hold the lock that publishes a STOP: a STOP published by a
        # sibling or another process either precedes this check (no launch) or follows the spawn.
        try:
            with _locked(state):
                try:
                    _admit(repo_root, common, held=True)
                except AgyStop as stop:
                    _set_latch(stop)
                    raise
                try:
                    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except OSError as exc:
                    raise AgyDispatchRefusedError(f"agy dispatch refused: sandbox launcher did not start: {exc}")
        except OSError as exc:
            raise AgyDispatchRefusedError(f"agy dispatch refused: stop state {state} is unusable: {exc}")
        timed_out = False
        interrupted: Optional[BaseException] = None
        try:
            out_b, err_b = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            out_b, err_b = proc.communicate()
        except BaseException as exc:  # inspection must still run before this propagates
            interrupted = exc
            proc.kill()
            try:
                out_b, err_b = proc.communicate(timeout=10)
            except BaseException:
                out_b, err_b = b"", b""
        rc = -9 if timed_out else proc.returncode
        out_b, err_b = out_b or b"", err_b or b""
        stdout = out_b.decode("utf-8", errors="replace")
        raw_stderr = err_b.decode("utf-8", errors="replace")
        after = _porcelain_state(repo_root)
        stderr = _strip_markers(raw_stderr)
        ready = f"{READY_MARKER} {layout.nonce}" in raw_stderr
        probe_failed = PROBE_MARKER in raw_stderr
        try:
            sentinel_changed = layout.sentinel.read_bytes() != layout.sentinel_bytes
        except OSError:
            sentinel_changed = True
        delta, inspect_errors = _workspace_delta(layout.ws)

        kind = None
        if probe_failed or sentinel_changed:
            kind = "boundary_failure"
            note = "in-sandbox write probe succeeded" if probe_failed else "read-only sentinel changed"
        elif delta or inspect_errors:
            kind = "critic"
            note = "critic wrote into its dispatch workspace"
            if inspect_errors:
                note += " (workspace not fully inspectable: " + "; ".join(inspect_errors) + ")"
        if kind is not None:
            # Latch and retain BEFORE any evidence I/O: a persistence failure can never reach a retry or
            # delete the only copy of the evidence.
            keep_reason = "incident evidence being recorded"
            _set_latch(AgyStop(kind, f"AGY_STOP [{kind}]: {note}; evidence being recorded at {layout.root}",
                               repo_root=repo_root, evidence_root=layout.root, provisional=True))
            try:
                rec = record_incident(repo_root, kind=kind, model=model, stdout=out_b, stderr=err_b,
                                      workspace=layout.ws, paths=delta, note=note)
                incident_id, incident_dir, errors, stop_recorded = (rec.incident_id, rec.incident_dir,
                                                                     rec.errors, rec.stop_recorded)
            except Exception as exc:  # noqa: BLE001 - any failure here must still end in the STOP below
                incident_dir, errors, stop_recorded = None, [f"incident not recorded: {exc}"], False
            if inspect_errors:
                errors = errors + ["workspace uninspectable: evidence left in place"]
            keep_reason = "; ".join(errors) if errors else None
            summary = f"{note}; {len(delta)} workspace path(s)"
            if errors:
                summary += "; " + "; ".join(errors) + f"; workspace kept at {layout.ws}"
            ids = [incident_id] if incident_dir is not None and incident_id else []
            stop = AgyStop(kind, _stop_message(kind, summary, repo_root, state, incident_dir or layout.root, ids),
                           incident_id=incident_id, incident_dir=incident_dir, repo_root=repo_root,
                           record=state / "stop.json", evidence_root=layout.root if keep_reason else None)
            _set_latch(stop, replace=True)
            raise stop

        blocked = [line for line in stderr.splitlines() if _BLOCKED_WRITE_RE.search(line)]
        cotenant = _cotenant_delta(before, after)
        if blocked or cotenant:
            _log_window(common, {"time": _now(), "model": model, "co_tenant": cotenant,
                                 "blocked_write_attempts": blocked})
            if blocked:
                print(f"Warning: {model} attempted {len(blocked)} blocked write(s); logged in "
                      f"{common / STATE_DIRNAME / 'windows.jsonl'}", file=sys.stderr)
        if interrupted is not None:
            raise interrupted
        if not ready:
            detail = " (timed out before the sandbox was ready)" if timed_out else ""
            raise AgyDispatchRefusedError(
                f"agy dispatch refused: sandbox setup failed{detail} (rc={rc}): {stderr.strip()[:500]}"
            )
        if timed_out:
            raise RuntimeError(f"Antigravity CLI timed out after {timeout}s")
        return subprocess.CompletedProcess(argv, rc, stdout, stderr)
    finally:
        if keep_reason is None:
            _reclaim_root(layout.root)
        else:
            _retain(layout, keep_reason, common=common, stop_recorded=stop_recorded, incident_id=incident_id)


def _retain(layout: DispatchLayout, reason: str, *, common: Path, stop_recorded: bool,
            incident_id: Optional[str]) -> None:
    """Mark a dispatch root as operator evidence: stale cleanup skips it; an unrecorded STOP blocks admission."""
    if not stop_recorded:
        with contextlib.suppress(OSError):  # first: the allocation-free flag that blocks and retains this root
            os.replace(layout.root / DISPATCH_INFO, layout.root / UNRECORDED_MARKER)
    marker = {"reason": reason, "time": _now(), "common_dir": str(common), "stop_recorded": stop_recorded,
              "incident_id": incident_id, "owner_pid": os.getpid()}
    try:
        (layout.root / RETAINED_MARKER).write_text(json.dumps(marker, indent=2) + "\n")
    except OSError as exc:
        print(f"Warning: could not mark retained evidence at {layout.root}: {exc}", file=sys.stderr)


def release_retained(root: str | Path, operator: str, reason: str) -> dict:
    """Operator release of a retained dispatch root (marker or bare evidence): logged, then reclaimable."""
    root = Path(root)
    if not operator.strip() or not reason.strip():
        raise ClearRefusedError("release requires --operator and a non-empty --reason")
    if not root.name.startswith(DISPATCH_PREFIX) or not root.is_dir():
        raise ClearRefusedError(f"{root} is not an agy dispatch root")
    marker_path = root / RETAINED_MARKER
    marker: object = None
    if marker_path.exists():
        try:
            marker = json.loads(marker_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            marker = f"unreadable: {exc}"
    common = marker.get("common_dir") if isinstance(marker, dict) else _root_common_dir(root)
    entry = {"time": _now(), "operator": operator.strip(), "reason": reason.strip(), "marker": marker,
             "released_root": str(root)}
    (root / RELEASED_MARKER).write_text(json.dumps(entry, indent=2) + "\n")
    marker_path.unlink(missing_ok=True)
    if common:
        with contextlib.suppress(OSError):
            state = Path(common) / STATE_DIRNAME
            with _locked(state), open(state / "clears.jsonl", "a") as fh:
                fh.write(json.dumps({**entry, "incidents": []}) + "\n")
    return entry


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
    release = sub.add_parser("release", help="release a retained dispatch root after reviewing its evidence")
    release.add_argument("--root", required=True)
    release.add_argument("--operator", required=True)
    release.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "status":
            state = stop_state_dir(args.repo)
            record = state / "stop.json"
            print(json.dumps({"state_dir": str(state), "stop_record_present": record.exists(),
                              "uncleared": _uncleared(state) if state.exists() else []}, indent=2))
            return 0
        if args.action == "release":
            entry = release_retained(args.root, args.operator, args.reason)
        else:
            entry = clear_stop(args.repo, args.incident, args.operator, args.reason)
        print(json.dumps(entry, indent=2))
        return 0
    except (ClearRefusedError, AgyDispatchRefusedError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_main())
