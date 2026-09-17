"""B-1: TMR obligation-identity fields, mirrored from the keystone contract.

The keystone (`Brainquarters/shared-context/test-maturity-record-schema.md`) is
the cross-repo source of record; this repo *mirrors* it. Three things have to
hold and each has a test here:

* AC-1 -- the keystone changed BEFORE this mirror, provably (commit order).
* AC-2 -- strict round-trip: a record carrying the six obligation fields
  validates, dumps, and re-validates to the same payload.
* AC-3 -- the obligation-identity projection is stable under evidence-field
  changes and unstable under obligation changes. That asymmetry is the whole
  mechanism: a standing waiver must survive evidence write-back and must die
  when what is being waived changes.

Covers TC-8.4's stale-revision / stale-policy-version / wrong-tier / wrong-env /
wrong-evidence-class binding elements at the schema layer, and resolves the 11
SCHEMA GAP carries in tests-spec.md.
"""

from __future__ import annotations

import copy
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from tmr_schema import (
    KEYSTONE_PROVENANCE,
    KEYSTONE_SCHEMA_SHA256,
    LIVENESS_TECHNIQUES,
    OBLIGATION_IDENTITY_FIELDS,
    REQUIRED_ENVIRONMENTS,
    REQUIRED_LIVENESS_CLASSES,
    REQUIRED_TIERS,
    RUN_ENVS,
    SchemaValidationError,
    assert_keystone_mirror_current,
    compute_tmr_record_hash,
    dump_tmr_record,
    keystone_path,
    schema_sha256,
    tmr_json_schema,
    validate_tmr_record,
    verify_tmr_record_hash,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

BASE_RECORD = {
    "tmr_uid": "01J0EXEMPLARULID00000000XY",
    "test_id": "TC-arm-fill-spine",
    "title": "Trader arms a pure pair; both legs fill; arb captured",
    "user_story": "US-2",
    "maturity": "acceptance",
    "data_strategy": "REAL-DATA",
    "spine": True,
    "verification_mode": "automated-integration",
    "verification_scope": "end-to-end",
    "altitude": "system",
    "tested_by": "both",
    "critical_seam": True,
    "criticality_source": "explicit",
    "binding_status": "unbound",
    "status": "active",
    "source_spec": "post-fable-hardening-skill",
    "live_or_induced": {"kind": "natural-wait"},
    "run_evidence": None,
    "obligation_revision": "3",
    "obligation_policy_version": "tmr-obligation.v2",
    "required_liveness_class": "natural-wait",
    "required_environment": "live",
    "required_tier": "code",
    "tmr_record_hash": None,
}

CODE_EVIDENCE = {
    "tier": "code",
    "command": "uv run pytest -q",
    "cwd": "/repo",
    "repo": "adversarial-spec",
    "commit": "b" * 40,
    "started_at": "2026-07-22T00:00:00Z",
    "finished_at": "2026-07-22T00:00:05Z",
    "exit": 0,
    "result": "pass",
    "env": "live",
    "artifact_uri": "file:///tmp/run.json",
    "artifact_sha256": "a" * 64,
    "runner": "skill-runner",
    "live_or_induced": {"kind": "natural-wait"},
}

# The six fields B-1 adds. The other four projection members predate this card
# and are required, so they have no null default to assert.
NEW_OBLIGATION_FIELDS = (
    "obligation_revision",
    "obligation_policy_version",
    "required_liveness_class",
    "required_environment",
    "required_tier",
    "tmr_record_hash",
)


def _record(**overrides):
    payload = copy.deepcopy(BASE_RECORD)
    payload.update(overrides)
    return validate_tmr_record(payload)


# --------------------------------------------------------------------------
# AC-1: keystone edited before the mirror, provably
# --------------------------------------------------------------------------


def test_keystone_provenance_is_recorded() -> None:
    assert KEYSTONE_PROVENANCE["commit"]
    assert KEYSTONE_PROVENANCE["committed_at"]
    datetime.fromisoformat(KEYSTONE_PROVENANCE["committed_at"])


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_keystone_commit_precedes_this_mirror() -> None:
    """The recorded keystone commit must exist and predate the mirror commit.

    Skipped only when the keystone repo is not checked out beside this one --
    the hermetic half of the tripwire (the pinned hash below) still runs.
    """
    keystone = keystone_path()
    if keystone is None or not keystone.is_file():
        pytest.skip("keystone repo not checked out beside this one")

    keystone_repo = keystone.parent.parent
    shown = _git(keystone_repo, "show", "-s", "--format=%cI", KEYSTONE_PROVENANCE["commit"])
    assert shown.returncode == 0, (
        f"recorded keystone commit {KEYSTONE_PROVENANCE['commit']} not found: {shown.stderr}"
    )
    recorded_at = datetime.fromisoformat(shown.stdout.strip())

    touched = _git(
        keystone_repo,
        "show",
        "--name-only",
        "--format=",
        KEYSTONE_PROVENANCE["commit"],
    )
    assert "test-maturity-record-schema.md" in touched.stdout, (
        "recorded keystone commit does not touch the keystone file"
    )

    mirror_rel = "skills/adversarial-spec/scripts/tmr_schema.py"
    dirty = _git(REPO_ROOT, "status", "--porcelain", "--", mirror_rel)
    if dirty.stdout.strip():
        pytest.skip("mirror has uncommitted edits; order is asserted once it lands")

    mirror = _git(REPO_ROOT, "log", "-1", "--format=%cI", "--", mirror_rel)
    if mirror.returncode != 0 or not mirror.stdout.strip():
        pytest.skip("mirror not committed yet; order is asserted once it lands")
    mirror_at = datetime.fromisoformat(mirror.stdout.strip())

    assert recorded_at <= mirror_at, (
        f"keystone-first violated: keystone {recorded_at} is newer than mirror {mirror_at}"
    )


# --------------------------------------------------------------------------
# Drift tripwire (TC-0.5 style)
# --------------------------------------------------------------------------


def test_mirror_matches_pinned_keystone_hash() -> None:
    """Hermetic half: the model's schema hash equals the pinned keystone value."""
    assert schema_sha256() == KEYSTONE_SCHEMA_SHA256


def test_keystone_file_pin_matches_the_mirror_constant() -> None:
    """Cross-repo half: the keystone's own pinned line agrees with our constant."""
    keystone = keystone_path()
    if keystone is None or not keystone.is_file():
        pytest.skip("keystone repo not checked out beside this one")
    assert_keystone_mirror_current()


# --------------------------------------------------------------------------
# Field domains are the keystone's existing enums, not new ones
# --------------------------------------------------------------------------


def test_required_liveness_class_shares_the_liveness_technique_enum() -> None:
    assert REQUIRED_LIVENESS_CLASSES == LIVENESS_TECHNIQUES


def test_required_environment_shares_the_run_evidence_env_enum() -> None:
    assert REQUIRED_ENVIRONMENTS == RUN_ENVS


def test_required_tier_covers_the_three_evidence_tiers() -> None:
    assert REQUIRED_TIERS == ("code", "system-validation", "judgment")


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("required_liveness_class", REQUIRED_LIVENESS_CLASSES),
        ("required_environment", REQUIRED_ENVIRONMENTS),
        ("required_tier", REQUIRED_TIERS),
    ],
)
def test_model_literal_matches_its_enum_tuple(field: str, expected: tuple) -> None:
    """The Literals are spelled out by hand; this is what stops them drifting."""
    variants = tmr_json_schema()["properties"][field]["anyOf"]
    enums = [variant["enum"] for variant in variants if "enum" in variant]
    assert enums == [list(expected)]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("required_liveness_class", "not-a-technique"),
        ("required_environment", "staging"),
        ("required_tier", "manual"),
    ],
)
def test_out_of_enum_requirement_is_rejected(field: str, value: str) -> None:
    with pytest.raises(SchemaValidationError):
        _record(**{field: value})


@pytest.mark.parametrize(
    "field", ["obligation_revision", "obligation_policy_version", "tmr_record_hash"]
)
def test_counters_and_versions_must_be_strings(field: str) -> None:
    """Spec 1 value normalization: counters/versions/hashes are never numbers."""
    with pytest.raises(SchemaValidationError):
        _record(**{field: 3})


@pytest.mark.parametrize("field", NEW_OBLIGATION_FIELDS)
def test_obligation_fields_default_to_null(field: str) -> None:
    """Optional + warn first (keystone decision 5): in-flight records still validate."""
    payload = {k: v for k, v in BASE_RECORD.items() if k not in NEW_OBLIGATION_FIELDS}
    record = validate_tmr_record(payload)
    assert dump_tmr_record(record)[field] is None


# --------------------------------------------------------------------------
# AC-2: strict round-trip
# --------------------------------------------------------------------------


def test_strict_round_trip_preserves_obligation_fields() -> None:
    record = _record()
    dumped = dump_tmr_record(record)
    for field in (
        "obligation_revision",
        "obligation_policy_version",
        "required_liveness_class",
        "required_environment",
        "required_tier",
        "tmr_record_hash",
    ):
        assert field in dumped
    assert dump_tmr_record(validate_tmr_record(dumped)) == dumped


def test_unknown_obligation_field_is_still_forbidden() -> None:
    with pytest.raises(SchemaValidationError):
        _record(obligation_policy=" typo of obligation_policy_version")


# --------------------------------------------------------------------------
# AC-3: projection stability
# --------------------------------------------------------------------------


EVIDENCE_MUTATIONS = [
    ("binding_status", "bound"),
    ("run_evidence", CODE_EVIDENCE),
    ("title", "a retitled test"),
    ("accessors", ["arm_algo", "legs_of"]),
    ("verification_scope", "targeted"),
]

IDENTITY_MUTATIONS = [
    ("test_id", "TC-arm-fill-spine-renamed"),
    ("user_story", "US-9"),
    ("criticality_source", "architecture_link"),
    ("obligation_revision", "4"),
    ("obligation_policy_version", "tmr-obligation.v3"),
    ("required_liveness_class", "clock-stub"),
    ("required_environment", "dev"),
    ("required_tier", "judgment"),
]


@pytest.mark.parametrize(("field", "value"), EVIDENCE_MUTATIONS)
def test_projection_survives_evidence_change(field: str, value: object) -> None:
    """A standing waiver must survive evidence write-back."""
    extra = {}
    if field == "run_evidence":
        # Evidence only lands on a concrete, bound record -- promote alongside it
        # so the mutation is the realistic write-back, not a schema-invalid poke.
        extra = {"maturity": "concrete", "binding_status": "bound"}
    before = compute_tmr_record_hash(_record())
    after = compute_tmr_record_hash(_record(**{field: value}, **extra))
    assert before == after, f"{field} leaked into the obligation-identity projection"


def test_projection_survives_full_promotion_to_concrete() -> None:
    """maturity + binding_status + run_evidence all change; the obligation does not."""
    before = compute_tmr_record_hash(_record())
    after = compute_tmr_record_hash(
        _record(maturity="concrete", binding_status="bound", run_evidence=CODE_EVIDENCE)
    )
    assert before == after


@pytest.mark.parametrize(("field", "value"), IDENTITY_MUTATIONS)
def test_projection_changes_when_the_obligation_changes(field: str, value: object) -> None:
    """Changing what is being waived must invalidate the waiver."""
    before = compute_tmr_record_hash(_record())
    after = compute_tmr_record_hash(_record(**{field: value}))
    assert before != after, f"{field} is missing from the obligation-identity projection"


def test_projection_field_set_is_exactly_the_keystone_ten() -> None:
    assert OBLIGATION_IDENTITY_FIELDS == frozenset(
        {
            "tmr_uid",
            "test_id",
            "user_story",
            "critical_seam",
            "criticality_source",
            "obligation_revision",
            "obligation_policy_version",
            "required_liveness_class",
            "required_environment",
            "required_tier",
            "target_binding",
        }
    )
    assert "tmr_record_hash" not in OBLIGATION_IDENTITY_FIELDS
    assert "run_evidence" not in OBLIGATION_IDENTITY_FIELDS


def test_hash_is_deterministic_across_key_order() -> None:
    shuffled = dict(reversed(list(BASE_RECORD.items())))
    assert compute_tmr_record_hash(validate_tmr_record(shuffled)) == compute_tmr_record_hash(
        _record()
    )


def test_stored_hash_is_never_trusted_over_the_projection() -> None:
    record = _record(tmr_record_hash="sha256:" + "0" * 64)
    with pytest.raises(SchemaValidationError) as excinfo:
        verify_tmr_record_hash(record)
    assert excinfo.value.field == "tmr_record_hash"


def test_matching_stored_hash_verifies() -> None:
    computed = compute_tmr_record_hash(_record())
    verify_tmr_record_hash(_record(tmr_record_hash=computed))


def test_absent_stored_hash_is_not_a_mismatch() -> None:
    """A record that has not been stamped yet is unstamped, not corrupt."""
    verify_tmr_record_hash(_record(tmr_record_hash=None))
