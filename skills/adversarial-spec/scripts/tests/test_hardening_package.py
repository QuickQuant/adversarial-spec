"""W0-1: hardening package scaffold + Python 3.14 floor (TC-0.0, toolchain half).

Three acceptance criteria are covered here:

* AC-1 -- the ``hardening`` package imports cleanly on 3.14, and does not import
  upward from ``gauntlet`` (no app -> app).
* AC-2 -- ``uv run adversarial-spec --help`` still works, i.e. the root
  ``adversarial_spec`` symlink bridge to ``skills/adversarial-spec/scripts``
  survived the floor bump.
* AC-3 -- the wheel builds and installs into an EMPTY 3.14 environment. This is
  the criterion the repo checkout cannot fake: running from the source tree
  puts ``scripts/`` on ``sys.path`` and resolves the symlink, so a packaging
  defect stays invisible until something installs the wheel elsewhere.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
HARDENING_DIR = REPO_ROOT / "skills" / "adversarial-spec" / "scripts" / "hardening"
PYPROJECT = REPO_ROOT / "pyproject.toml"
SKILL_PYPROJECT = REPO_ROOT / "skills" / "adversarial-spec" / "pyproject.toml"

# The component tree from target-architecture.md "Package and Component
# Boundaries". A module missing here means the scaffold drifted from the
# architecture; a module present on disk but absent here means someone added a
# file the plan does not list (structural conformance).
EXPECTED_MODULES = (
    "artifacts",
    "authorization_set",
    "canonical_sets",
    "cli_boundary",
    "journal",
    "local_capabilities",
    "operation_journal",
    "predicates",
    "receipts",
    "remote_authority",
    "state_store",
    "tmr_registry_writer",
    "trust_policy",
)

PINNED_DEPENDENCIES = {
    "rfc8785": "0.1.4",
    "cryptography": "49.0.0",
}

MIN_PYTHON = (3, 14)


def _pyproject(path: Path = PYPROJECT) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


# --------------------------------------------------------------------------
# AC-1: package imports cleanly, layout matches the architecture, no app -> app
# --------------------------------------------------------------------------


def test_running_interpreter_meets_floor() -> None:
    assert sys.version_info[:2] >= MIN_PYTHON, (
        f"tests must run on >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}; "
        f"got {sys.version.split()[0]}"
    )


@pytest.mark.parametrize("path", [PYPROJECT, SKILL_PYPROJECT])
def test_requires_python_floor_declared(path: Path) -> None:
    """Both project files declare the floor; one left behind is silent drift."""
    assert _pyproject(path)["project"]["requires-python"] == ">=3.14"


def test_package_layout_matches_architecture() -> None:
    on_disk = {p.stem for p in HARDENING_DIR.glob("*.py")} - {"__init__"}
    assert on_disk == set(EXPECTED_MODULES), (
        "hardening/ drifted from the target-architecture component tree; "
        "update the execution plan before adding or removing a module"
    )
    assert (HARDENING_DIR / "reconcile" / "__init__.py").is_file()


@pytest.mark.parametrize("module", EXPECTED_MODULES)
def test_module_imports_cleanly(module: str) -> None:
    importlib.import_module(f"hardening.{module}")


def test_reconcile_registry_imports_cleanly() -> None:
    importlib.import_module("hardening.reconcile")


def test_no_upward_import_from_gauntlet() -> None:
    """The hardening package must not depend on the gauntlet application."""
    offenders = []
    for path in sorted(HARDENING_DIR.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("import gauntlet", "from gauntlet")):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {stripped}")
    assert not offenders, "hardening must not import upward from gauntlet: " + "; ".join(
        offenders
    )


# --------------------------------------------------------------------------
# Dependency pins from the architecture's Dependency Decision
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "version"), sorted(PINNED_DEPENDENCIES.items()))
def test_dependency_is_pinned(name: str, version: str) -> None:
    declared = _pyproject()["project"]["dependencies"]
    assert f"{name}=={version}" in declared


@pytest.mark.parametrize("name", sorted(PINNED_DEPENDENCIES))
def test_pinned_dependency_is_importable(name: str) -> None:
    importlib.import_module(name)


# --------------------------------------------------------------------------
# AC-2: symlink bridge preserved
# --------------------------------------------------------------------------


def _uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("uv is required to run this project's toolchain tests")
    return uv


def test_console_script_still_resolves_through_symlink_bridge() -> None:
    result = subprocess.run(
        [_uv(), "run", "adversarial-spec", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    assert "adversarial-spec" in result.stdout


# --------------------------------------------------------------------------
# AC-3: clean-env wheel install
# --------------------------------------------------------------------------


def test_wheel_installs_into_empty_environment(tmp_path: Path) -> None:
    """Build the wheel and import it from a venv that has never seen the repo.

    ``cwd`` is the tmp dir throughout, so neither the root ``adversarial_spec``
    symlink nor the pytest ``pythonpath`` entry can mask a packaging defect.
    """
    uv = _uv()
    dist = tmp_path / "dist"

    build = subprocess.run(
        [uv, "build", "--wheel", "-o", str(dist)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, build.stderr

    wheels = list(dist.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"

    venv = tmp_path / "venv"
    created = subprocess.run(
        [uv, "venv", "--python", "3.14", str(venv)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert created.returncode == 0, created.stderr

    installed = subprocess.run(
        [uv, "pip", "install", "--python", str(venv / "bin" / "python"), str(wheels[0])],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert installed.returncode == 0, installed.stderr

    imported = subprocess.run(
        [
            str(venv / "bin" / "python"),
            "-c",
            "import adversarial_spec.hardening as h; "
            "import adversarial_spec.hardening.reconcile; "
            "print(h.__file__)",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert imported.returncode == 0, imported.stderr
    assert str(venv) in imported.stdout, (
        "import resolved outside the clean venv -- the repo checkout leaked in"
    )

    for module in EXPECTED_MODULES:
        submodule = subprocess.run(
            [
                str(venv / "bin" / "python"),
                "-c",
                f"import adversarial_spec.hardening.{module}",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert submodule.returncode == 0, f"{module}: {submodule.stderr}"
