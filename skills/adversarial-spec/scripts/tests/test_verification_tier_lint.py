"""Unit tests for verification-tier lint script.

Covers:
- TC-14.0 (validate manifest schema & parse)
- TC-14.1 (validate plan lint rules)
- TC-INV-018 (validate manifest existence and hash match for judgment tasks)
"""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError
from verification_tier_lint import (
    GoldenManifest,
    LintError,
    lint_manifest_and_fixtures,
    lint_plan,
)


def test_tc_14_0_manifest_schema():
    """TC-14.0: Validate manifest schema and parsing of GoldenManifest & GoldenCase."""
    # Valid manifest case
    valid_manifest = {
        "cases": [
            {
                "case_id": "TC-6.0",
                "fixture_path": "fixtures/tc_6_0_fixture.md",
                "expected_findings": [{"finding_id": "ERR_1", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {"temp": 0.0},
                "threshold": 0.8,
                "content_hash": "333eeb711cb55fe0e7e546ccb2b1a7375cad463e910fe35c13b088becbc4a359"
            }
        ]
    }
    manifest = GoldenManifest.model_validate(valid_manifest)
    assert len(manifest.cases) == 1
    assert manifest.cases[0].case_id == "TC-6.0"
    assert manifest.cases[0].fixture_path == "fixtures/tc_6_0_fixture.md"
    assert manifest.cases[0].expected_findings == [{"finding_id": "ERR_1", "description": "fail"}]
    assert manifest.cases[0].negatives == ["no err"]
    assert manifest.cases[0].model == "mock-model"
    assert manifest.cases[0].model_settings == {"temp": 0.0}
    assert manifest.cases[0].threshold == 0.8
    assert manifest.cases[0].content_hash == "333eeb711cb55fe0e7e546ccb2b1a7375cad463e910fe35c13b088becbc4a359"

    # Extra fields should be forbidden
    invalid_extra = {
        "cases": [
            {
                "case_id": "TC-6.0",
                "fixture_path": "fixtures/tc_6_0_fixture.md",
                "expected_findings": [{"finding_id": "ERR_1", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "333eeb711cb55fe0e7e546ccb2b1a7375cad463e910fe35c13b088becbc4a359",
                "extra_field": "forbidden"
            }
        ]
    }
    with pytest.raises(ValidationError):
        GoldenManifest.model_validate(invalid_extra)

    # Invalid content_hash format
    invalid_hash = {
        "cases": [
            {
                "case_id": "TC-6.0",
                "fixture_path": "fixtures/tc_6_0_fixture.md",
                "expected_findings": [{"finding_id": "ERR_1", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "not-a-sha256"
            }
        ]
    }
    with pytest.raises(ValidationError):
        GoldenManifest.model_validate(invalid_hash)

    # Empty expected_findings should raise ValidationError
    empty_findings = {
        "cases": [
            {
                "case_id": "TC-6.0",
                "fixture_path": "fixtures/tc_6_0_fixture.md",
                "expected_findings": [],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "333eeb711cb55fe0e7e546ccb2b1a7375cad463e910fe35c13b088becbc4a359"
            }
        ]
    }
    with pytest.raises(ValidationError):
        GoldenManifest.model_validate(empty_findings)

    # Empty negatives should raise ValidationError
    empty_negatives = {
        "cases": [
            {
                "case_id": "TC-6.0",
                "fixture_path": "fixtures/tc_6_0_fixture.md",
                "expected_findings": [{"finding_id": "ERR_1", "description": "fail"}],
                "negatives": [],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "333eeb711cb55fe0e7e546ccb2b1a7375cad463e910fe35c13b088becbc4a359"
            }
        ]
    }
    with pytest.raises(ValidationError):
        GoldenManifest.model_validate(empty_negatives)



def test_tc_14_1_plan_lint():
    """TC-14.1: Validate plan lint rules."""
    # Valid plan
    valid_plan = {
        "tasks": [
            {
                "task_id": "W0-1",
                "behavior_change": True,
                "verification_tier": "code",
                "verification_mode": "automated-contract"
            },
            {
                "task_id": "W1-0",
                "behavior_change": False,
                "verification_tier": "prompt-doc",
                "verification_mode": "static-check"
            }
        ]
    }
    lint_plan(valid_plan)  # should not raise

    # Missing verification_tier
    bad_plan_1 = {
        "tasks": [
            {
                "task_id": "W0-1",
                "verification_mode": "automated-contract"
            }
        ]
    }
    with pytest.raises(LintError, match="missing 'verification_tier'"):
        lint_plan(bad_plan_1)

    # Invalid verification_tier
    bad_plan_2 = {
        "tasks": [
            {
                "task_id": "W0-1",
                "verification_tier": "unknown-tier",
                "verification_mode": "automated-contract"
            }
        ]
    }
    with pytest.raises(LintError, match="invalid verification_tier"):
        lint_plan(bad_plan_2)

    # Mismatched verification_tier and verification_mode
    bad_plan_3 = {
        "tasks": [
            {
                "task_id": "W0-1",
                "verification_tier": "code",
                "verification_mode": "system-validation"  # system-validation requires llm-judgment
            }
        ]
    }
    with pytest.raises(LintError, match="has mismatch"):
        lint_plan(bad_plan_3)

    # Forbidden golden-eval verification_mode
    bad_plan_4 = {
        "tasks": [
            {
                "task_id": "W0-1",
                "verification_tier": "code",
                "verification_mode": "golden-eval"
            }
        ]
    }
    with pytest.raises(LintError, match="uses forbidden 'golden-eval' mode"):
        lint_plan(bad_plan_4)

    # Code-seam (behavior_change = True) with exempt mode (prompt-doc)
    bad_plan_5 = {
        "tasks": [
            {
                "task_id": "W0-1",
                "behavior_change": True,
                "verification_tier": "prompt-doc",
                "verification_mode": "static-check"
            }
        ]
    }
    with pytest.raises(LintError, match="is a code-seam .* but has an exempt mode"):
        lint_plan(bad_plan_5)


def test_tc_inv_018_manifest_validation(tmp_path):
    """TC-INV-018: Validate manifest existence and hash match for judgment tasks."""
    manifest_file = tmp_path / "manifest.json"

    # Missing manifest file
    with pytest.raises(LintError, match="manifest.json not found"):
        lint_manifest_and_fixtures(manifest_file)

    # Missing required judgment cases (e.g. missing TC-3.1)
    incomplete_manifest = {
        "cases": [
            {
                "case_id": "TC-6.0",
                "fixture_path": "fixtures/tc_6_0.md",
                "expected_findings": [{"finding_id": "ERR_1", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "333eeb711cb55fe0e7e546ccb2b1a7375cad463e910fe35c13b088becbc4a359"
            },
            {
                "case_id": "TC-7.1",
                "fixture_path": "fixtures/tc_7_1.md",
                "expected_findings": [{"finding_id": "ERR_2", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "03a9a9f9835c018cbc011db950361b40b300bf0c65067ea5f28df3f960f9f4c2"
            }
        ]
    }
    manifest_file.write_text(json.dumps(incomplete_manifest), encoding="utf-8")
    with pytest.raises(LintError, match="missing required judgment test cases"):
        lint_manifest_and_fixtures(manifest_file)

    # Missing fixture file
    complete_but_no_fixtures = {
        "cases": [
            {
                "case_id": "TC-6.0",
                "fixture_path": "fixtures/tc_6_0.md",
                "expected_findings": [{"finding_id": "ERR_1", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "333eeb711cb55fe0e7e546ccb2b1a7375cad463e910fe35c13b088becbc4a359"
            },
            {
                "case_id": "TC-7.1",
                "fixture_path": "fixtures/tc_7_1.md",
                "expected_findings": [{"finding_id": "ERR_2", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "03a9a9f9835c018cbc011db950361b40b300bf0c65067ea5f28df3f960f9f4c2"
            },
            {
                "case_id": "TC-3.1",
                "fixture_path": "fixtures/tc_3_1.md",
                "expected_findings": [{"finding_id": "ERR_3", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": "a692413fc261538d5d8a199ecc097901c564c2f8beba9e51573e02ab7c692c3d"
            }
        ]
    }
    manifest_file.write_text(json.dumps(complete_but_no_fixtures), encoding="utf-8")
    with pytest.raises(LintError, match="Fixture file not found"):
        lint_manifest_and_fixtures(manifest_file)

    # Create fixtures directory and files
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()

    f6 = fixtures_dir / "tc_6_0.md"
    f6.write_text("TC-6.0 content")

    f7 = fixtures_dir / "tc_7_1.md"
    f7.write_text("TC-7.1 content")

    f3 = fixtures_dir / "tc_3_1.md"
    f3.write_text("TC-3.1 content")

    # Hash mismatch (since we wrote "TC-6.0 content" which doesn't match the expected hash)
    with pytest.raises(LintError, match="Hash mismatch for case TC-6.0"):
        lint_manifest_and_fixtures(manifest_file)

    # Correct the hashes in manifest
    h6 = hashlib.sha256(b"TC-6.0 content").hexdigest()
    h7 = hashlib.sha256(b"TC-7.1 content").hexdigest()
    h3 = hashlib.sha256(b"TC-3.1 content").hexdigest()

    correct_manifest = {
        "cases": [
            {
                "case_id": "TC-6.0",
                "fixture_path": "fixtures/tc_6_0.md",
                "expected_findings": [{"finding_id": "ERR_1", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": h6
            },
            {
                "case_id": "TC-7.1",
                "fixture_path": "fixtures/tc_7_1.md",
                "expected_findings": [{"finding_id": "ERR_2", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": h7
            },
            {
                "case_id": "TC-3.1",
                "fixture_path": "fixtures/tc_3_1.md",
                "expected_findings": [{"finding_id": "ERR_3", "description": "fail"}],
                "negatives": ["no err"],
                "model": "mock-model",
                "model_settings": {},
                "threshold": 0.8,
                "content_hash": h3
            }
        ]
    }
    manifest_file.write_text(json.dumps(correct_manifest), encoding="utf-8")

    # Should pass now!
    res = lint_manifest_and_fixtures(manifest_file)
    assert len(res.cases) == 3

