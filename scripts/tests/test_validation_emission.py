"""Compatibility collection path for validation_emission tests.

The validation-leg execution plan declares ``scripts/tests/test_validation_emission.py``.
The implementation test suite lives beside the skill module so project-wide pytest
discovery can use the configured ``pythonpath``. Re-export those tests here for
the declared per-card verify commands.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REAL_TEST = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "adversarial-spec"
    / "scripts"
    / "tests"
    / "test_validation_emission.py"
)
_SPEC = importlib.util.spec_from_file_location("_validation_emission_tests", _REAL_TEST)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"unable to load validation_emission tests from {_REAL_TEST}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

for _name, _value in vars(_MODULE).items():
    if _name == "pytestmark" or _name.startswith("test_") or _name == "ledger":
        globals()[_name] = _value
