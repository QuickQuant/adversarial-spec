"""Known-bad control (A.5): the frozen pre-reform contract at commit b544a00.

The module is extracted read-only with ``git show`` into a temp dir and loaded
under its own name; nothing in the working tree is touched. The suite must
FAIL every obligation here. The suite consumes ``MODULE``.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

FROZEN_COMMIT = "b544a00"
_root = Path(os.environ.get("AB_TARGET_ROOT") or os.getcwd()).resolve()
_tmp = Path(tempfile.mkdtemp(prefix="ab-bad-"))
_rel = "skills/adversarial-spec/scripts/tmr_schema.py"
_src = subprocess.run(["git", "-C", str(_root), "show", f"{FROZEN_COMMIT}:{_rel}"], capture_output=True, text=True, check=True).stdout
_path = _tmp / "tmr_schema.py"
_path.write_text(_src, encoding="utf-8")
sys.path.insert(0, str(_tmp))
_spec = importlib.util.spec_from_file_location("tmr_schema", _path)
MODULE = importlib.util.module_from_spec(_spec)
sys.modules["tmr_schema"] = MODULE
_spec.loader.exec_module(MODULE)
