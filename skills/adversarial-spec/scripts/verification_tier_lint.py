"""Verification-tier lint for tasks and golden cases manifest.json.

This script implements:
1. GoldenManifest and GoldenCase Pydantic V2 models.
2. Verification-tier linting of the execution plan.
3. Verification of judgment test cases (TC-6.0, TC-7.1, TC-3.1) in manifest.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, field_validator


# 1. Pydantic models for GoldenManifest and GoldenCase
class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    case_id: str
    fixture_path: str
    expected_findings: List[Dict[str, Any]]
    negatives: List[str]
    model: str
    model_settings: Dict[str, Any]
    threshold: float
    content_hash: str

    @field_validator("expected_findings")
    @classmethod
    def validate_non_empty_expected_findings(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not v:
            raise ValueError("expected_findings must be non-empty for judgment cases")
        for finding in v:
            if not isinstance(finding, dict):
                raise ValueError("Each finding must be a dictionary")
            if "finding_id" not in finding or not finding["finding_id"]:
                raise ValueError("Each finding must contain a non-empty finding_id")
            if "description" not in finding or not finding["description"]:
                raise ValueError("Each finding must contain a non-empty description")
        return v

    @field_validator("negatives")
    @classmethod
    def validate_non_empty_negatives(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("negatives must be non-empty for judgment cases")
        for item in v:
            if not item or not isinstance(item, str) or not item.strip():
                raise ValueError("Each negative must be a non-empty string")
        return v

    @field_validator("content_hash")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("content_hash must be a string")
        v_clean = v.strip().lower()
        if len(v_clean) != 64 or not all(c in "0123456789abcdef" for c in v_clean):
            raise ValueError("content_hash must be a valid 64-character SHA256 hex string")
        return v_clean



class GoldenManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    cases: List[GoldenCase]


# 2. Validation constants
VALID_TIERS = {"code", "prompt-doc", "llm-judgment"}
TIER_TO_MODES = {
    "code": {
        "automated-unit",
        "automated-integration",
        "automated-contract",
        "automated-component",
        "test-producer",
    },
    "prompt-doc": {
        "artifact-sync",
        "static-check",
        "manual-ux",
    },
    "llm-judgment": {
        "system-validation",
    },
}
EXEMPT_MODES = TIER_TO_MODES["prompt-doc"]
ALL_VALID_MODES = TIER_TO_MODES["code"] | TIER_TO_MODES["prompt-doc"] | TIER_TO_MODES["llm-judgment"]


class LintError(Exception):
    """Raised when plan or manifest lint validation fails."""
    pass


def compute_sha256(file_path: Path) -> str:
    """Computes the SHA256 hex digest of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def lint_plan(plan_data: Dict[str, Any]) -> None:
    """Lints the execution plan dictionary.

    - Every task must have a verification_tier ('code', 'prompt-doc', 'llm-judgment')
    - verification_mode must be consistent with verification_tier
    - reject 'golden-eval' mode completely
    - code-seam task (behavior_change = true) with an exempt mode must be flagged as an error
    """
    tasks = plan_data.get("tasks", [])
    if not isinstance(tasks, list):
        raise LintError("plan must contain a list of tasks under 'tasks'")

    for task in tasks:
        task_id = task.get("task_id", "unknown")

        # 1. Check verification_tier exists and is valid
        tier = task.get("verification_tier")
        if not tier:
            raise LintError(f"Task {task_id} is missing 'verification_tier'")
        if tier not in VALID_TIERS:
            raise LintError(f"Task {task_id} has invalid verification_tier: {tier!r}")

        # 2. Check verification_mode exists and is consistent
        mode = task.get("verification_mode")
        if not mode:
            raise LintError(f"Task {task_id} is missing 'verification_mode'")

        # Reject golden-eval mode
        if mode == "golden-eval":
            raise LintError(f"Task {task_id} uses forbidden 'golden-eval' mode")

        if mode not in ALL_VALID_MODES:
            raise LintError(f"Task {task_id} has invalid verification_mode: {mode!r}")

        expected_modes = TIER_TO_MODES[tier]
        if mode not in expected_modes:
            raise LintError(
                f"Task {task_id} has mismatch: tier {tier!r} is not consistent with mode {mode!r}"
            )

        # 3. Check code-seam behavior_change rule
        behavior_change = task.get("behavior_change", False)
        if behavior_change is True and mode in EXEMPT_MODES:
            raise LintError(
                f"Task {task_id} is a code-seam (behavior_change = true) but has an exempt mode {mode!r}"
            )


def lint_manifest_and_fixtures(manifest_path: Path) -> GoldenManifest:
    """Loads and validates manifest.json and its referenced fixtures.

    - The manifest must exist and conform to GoldenManifest schema.
    - Specifically TC-6.0, TC-7.1, TC-3.1 must be defined in the manifest.
    - Each referenced fixture_path must exist and its content_hash must match the actual SHA256 of the file.
    """
    if not manifest_path.exists():
        raise LintError(f"manifest.json not found at {manifest_path}")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise LintError(f"Failed to parse manifest.json as JSON: {e}")

    try:
        manifest = GoldenManifest.model_validate(data)
    except Exception as e:
        raise LintError(f"manifest.json fails schema validation: {e}")

    # Ensure TC-6.0, TC-7.1, TC-3.1 are present
    required_cases = {"TC-6.0", "TC-7.1", "TC-3.1"}
    manifest_cases = {case.case_id: case for case in manifest.cases}

    missing_cases = required_cases - set(manifest_cases.keys())
    if missing_cases:
        raise LintError(f"manifest.json is missing required judgment test cases: {missing_cases}")

    # Validate each case's fixture existence and SHA256 hash match
    for case in manifest.cases:
        # Resolve fixture_path relative to manifest parent directory
        fixture_file = manifest_path.parent / case.fixture_path
        if not fixture_file.exists():
            raise LintError(
                f"Fixture file not found for case {case.case_id} at: {fixture_file}"
            )

        # Verify hash matches
        actual_hash = compute_sha256(fixture_file)
        if actual_hash != case.content_hash:
            raise LintError(
                f"Hash mismatch for case {case.case_id} fixture: "
                f"expected {case.content_hash}, got {actual_hash}"
            )

    return manifest


def run_all_lint(plan_path: Path, manifest_path: Path) -> None:
    """Lints both the execution plan and the golden cases manifest."""
    if not plan_path.exists():
        raise LintError(f"Plan file not found at {plan_path}")
    try:
        plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise LintError(f"Failed to parse plan file as JSON: {e}")

    lint_plan(plan_data)
    lint_manifest_and_fixtures(manifest_path)


if __name__ == "__main__":
    import sys
    # Defaults
    workspace_root = Path(__file__).resolve().parents[3]
    plan_path = workspace_root / ".adversarial-spec/specs/liveness-gate-test-ladder/fizzy-plan.json"
    # Search for manifest in both locations to see what exists
    manifest_paths = [
        workspace_root / ".adversarial-spec/specs/liveness-gate-test-ladder/golden_cases/manifest.json",
        workspace_root / "golden_cases/manifest.json",
    ]

    # Try the first one that exists, or default to the spec-specific one
    manifest_path = manifest_paths[0]
    for p in manifest_paths:
        if p.exists():
            manifest_path = p
            break

    print(f"Linting plan: {plan_path}")
    print(f"Linting manifest: {manifest_path}")

    try:
        run_all_lint(plan_path, manifest_path)
        print("Lint passed successfully!")
        sys.exit(0)
    except LintError as e:
        print(f"Lint Error: {e}", file=sys.stderr)
        sys.exit(1)
