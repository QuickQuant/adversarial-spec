"""A.5 known-bad: exact integration 36dafdd, no target_observation capture.

No git process. Verify and extract commit/tree/blob objects into this leaf.
Loose storage is required; missing/packed/corrupt objects are SETUP errors,
never legitimate red evidence. MODULE exports the actual frozen modules.
"""
from __future__ import annotations

import atexit
import hashlib
import importlib.util
import os
import sys
import tempfile
import zlib
from pathlib import Path
from types import ModuleType, SimpleNamespace

FROZEN_COMMIT = "36dafdd02b467800148b85704b33bcbe15d01979"
FROZEN_BLOBS = {
    "phase8_promotion": "10ec2fb707858af507e32c5c1cb2e39ae67d4a8c",
    "tmr_schema": "02bd5d7b138d119986438eaefb4c713df9a73193",
}
if not os.environ.get("AB_TARGET_ROOT"):
    raise ValueError("Frozen control SETUP: set AB_TARGET_ROOT to a repository containing 36dafdd")
_root = Path(os.environ["AB_TARGET_ROOT"]).resolve()
_gitdir = _root / ".git"
if _gitdir.is_file():
    _pointer = _gitdir.read_text(encoding="utf-8").strip()
    if not _pointer.startswith("gitdir: "):
        raise RuntimeError("Frozen control SETUP: invalid .git pointer")
    _gitdir = (_root / _pointer.removeprefix("gitdir: ")).resolve()
if (_gitdir / "commondir").is_file():
    _gitdir = (_gitdir / (_gitdir / "commondir").read_text(encoding="utf-8").strip()).resolve()


def _object(oid, kind):
    try:
        raw = zlib.decompress((_gitdir / "objects" / oid[:2] / oid[2:]).read_bytes())
        header, body = raw.split(b"\0", 1)
    except (OSError, zlib.error, ValueError) as exc:
        raise RuntimeError(f"Frozen control SETUP: unavailable loose object {oid}: {exc}") from exc
    if header != f"{kind} {len(body)}".encode() or hashlib.sha1(raw).hexdigest() != oid:
        raise RuntimeError(f"Frozen control SETUP: invalid {kind} object {oid}")
    return body


def _tree(oid):
    data = _object(oid, "tree")
    entries = {}
    while data:
        header, data = data.split(b"\0", 1)
        mode, name = header.split(b" ", 1)
        entries[name.decode()] = (mode.decode(), data[:20].hex())
        data = data[20:]
    return entries


_commit = _object(FROZEN_COMMIT, "commit")
_tree_oid = _commit.splitlines()[0].removeprefix(b"tree ").decode()
for _directory in ("skills", "adversarial-spec", "scripts"):
    _mode, _tree_oid = _tree(_tree_oid)[_directory]
    if _mode != "40000":
        raise RuntimeError("Frozen control SETUP: scripts path is not a directory")
_entries = _tree(_tree_oid)
_temporary = tempfile.TemporaryDirectory(prefix=".ab-obs-bad-", dir=Path(__file__).resolve().parents[1])
atexit.register(_temporary.cleanup)
_scripts = Path(_temporary.name) / "skills/adversarial-spec/scripts"
_scripts.mkdir(parents=True)
for _name, _expected in FROZEN_BLOBS.items():
    _mode, _oid = _entries[f"{_name}.py"]
    if _mode not in {"100644", "100755"} or _oid != _expected:
        raise RuntimeError(f"Frozen control SETUP: unexpected source blob {_name}")
    (_scripts / f"{_name}.py").write_bytes(_object(_oid, "blob"))

_package = ModuleType("_ab_obs_frozen")
_package.__path__ = [str(_scripts)]
sys.modules[_package.__name__] = _package


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{_package.__name__}.{name}", _scripts / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = SimpleNamespace(tmr_schema=_load("tmr_schema"), phase8_promotion=_load("phase8_promotion"))
