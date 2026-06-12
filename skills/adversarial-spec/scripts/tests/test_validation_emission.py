"""Tests for validation_emission.py — the validation-leg production-line CLI.

Spec: .adversarial-spec/specs/validation-leg-process/spec-output.md §7 (stdout
envelope + exit-code contract), §10 (stable codes), §12 (markers). This file is
the suite the execution plan's per-card ``verify_commands`` select into with
``-k`` expressions; keep selector tokens (envelope, lock, corrupt, atomic,
hash, ...) in test names.

C-1.1 module-skeleton-envelope (TC-3.9 envelope subset): every invocation
prints exactly ONE stdout JSON envelope; warnings to stderr only (FM-5); exit
contract 0/2/3 wired at the CLI boundary; global issues carry row_id null;
JSON artifacts stamped with schema_version + module_version and UTC RFC3339-Z
timestamps (OP-3/OP-4, DD-6).

Run:
    uv run pytest skills/adversarial-spec/scripts/tests/test_validation_emission.py -q
"""

import hashlib
import json
import re

import pytest
from filelock import FileLock, Timeout
from validation_emission import (
    CONOPS_MAX_BYTES,
    ENVELOPE_STATUSES,
    EXIT_ENV,
    EXIT_ISSUES,
    EXIT_OK,
    HASH_PREFIX_LEN,
    JUSTIFICATION_MAX_BYTES,
    LEDGER_LOCK_TIMEOUT_S,
    LEDGER_MAX_BYTES,
    REPLY_MAX_BYTES,
    ROW_HASH_FIELDS,
    SCHEMA_VERSION,
    SUBCOMMANDS,
    LedgerBusyError,
    LedgerCorruptError,
    ValidationIssuesError,
    __version__,
    compute_conops_hash,
    compute_row_hash,
    compute_story_hashes,
    enforce_input_bounds,
    exit_code_for_status,
    find_duplicate_row_ids,
    find_duplicate_story_ids,
    hash_prefix,
    main,
    module_version,
    mutate_ledger,
    read_ledger,
    resolve_under_root,
    row_hash_for,
    stamp_artifact,
    utc_now,
)

pytestmark = pytest.mark.deterministic

ENVELOPE_KEYS = {"status", "code", "issues", "data"}
ISSUE_KEYS = {"code", "row_id", "detail"}
RFC3339_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def run_cli(capsys, argv):
    exit_code = main(argv)
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


def parse_single_envelope(stdout: str) -> dict:
    """The WHOLE stdout must be exactly one JSON envelope (FM-5)."""
    assert stdout.strip(), "stdout must carry the envelope"
    envelope = json.loads(stdout)  # raises if stdout has anything beyond one object
    assert isinstance(envelope, dict)
    assert set(envelope) == ENVELOPE_KEYS, f"envelope keys drifted: {set(envelope)}"
    assert envelope["status"] in ENVELOPE_STATUSES
    assert envelope["code"] is None or isinstance(envelope["code"], str)
    assert isinstance(envelope["issues"], list)
    for issue in envelope["issues"]:
        assert set(issue) == ISSUE_KEYS, f"issue keys drifted: {set(issue)}"
    assert isinstance(envelope["data"], dict)
    return envelope


# ── AC-1: argparse dispatch for all 13 subcommands ───────────────────────────


def test_envelope_subcommand_registry_is_the_13_from_spec_s7():
    assert len(SUBCOMMANDS) == 13
    assert list(SUBCOMMANDS) == sorted(set(SUBCOMMANDS)) or len(set(SUBCOMMANDS)) == 13
    expected = {
        "derive-conops", "normalize-rows", "check-rows", "record-evidence",
        "self-check", "assemble-digest", "record-send", "cancel-batch",
        "reset-failed", "supersede-row", "parse-reply",
        "emit-system-validation", "status",
    }
    assert set(SUBCOMMANDS) == expected


@pytest.mark.parametrize("subcommand", sorted({
    "derive-conops", "normalize-rows", "check-rows", "record-evidence",
    "self-check", "assemble-digest", "record-send", "cancel-batch",
    "reset-failed", "supersede-row", "parse-reply",
    "emit-system-validation", "status",
}))
def test_envelope_every_subcommand_dispatches_with_contract(capsys, subcommand):
    """Bare invocation of EVERY subcommand yields one envelope + a contract exit.

    Stays valid as real handlers land: a handler missing required inputs must
    answer with an exit-2 issues envelope, never a traceback or bare usage text.
    """
    exit_code, out, _err = run_cli(capsys, [subcommand])
    envelope = parse_single_envelope(out)
    assert exit_code in (EXIT_OK, EXIT_ISSUES, EXIT_ENV)
    assert exit_code == exit_code_for_status(envelope["status"])


def test_envelope_unknown_subcommand_exit2(capsys):
    exit_code, out, _err = run_cli(capsys, ["frobnicate"])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert envelope["status"] == "issues"
    assert envelope["code"] == "UNKNOWN_SUBCOMMAND"
    assert envelope["issues"], "unknown subcommand must carry an issue entry"


def test_envelope_missing_subcommand_exit2(capsys):
    exit_code, out, _err = run_cli(capsys, [])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert envelope["status"] == "issues"


# ── AC-2: exactly one stdout JSON envelope; warnings to stderr only (FM-5) ───


def test_envelope_stdout_is_single_line_json(capsys):
    _exit_code, out, _err = run_cli(capsys, ["status"])
    assert len(out.strip().splitlines()) == 1, "stdout must be exactly one envelope line"
    parse_single_envelope(out)


def test_envelope_diagnostics_go_to_stderr_not_stdout(capsys):
    # Unrecognized extras are tolerated by the skeleton with a stderr warning;
    # stdout must remain a single parseable envelope.
    _exit_code, out, err = run_cli(capsys, ["status", "--no-such-flag"])
    parse_single_envelope(out)
    assert "--no-such-flag" in err, "diagnostic about ignored args belongs on stderr"


# ── AC-3: exit-code contract 0/2/3 at the CLI boundary; global row_id null ──


def test_envelope_exit_code_contract_mapping():
    assert exit_code_for_status("ok") == EXIT_OK == 0
    assert exit_code_for_status("issues") == EXIT_ISSUES == 2
    assert exit_code_for_status("reprompt") == EXIT_ISSUES == 2
    assert exit_code_for_status("error") == EXIT_ENV == 3
    with pytest.raises(ValueError):
        exit_code_for_status("nonsense")


def test_envelope_global_issues_carry_row_id_null(capsys):
    _exit_code, out, _err = run_cli(capsys, ["frobnicate"])
    envelope = parse_single_envelope(out)
    for issue in envelope["issues"]:
        assert issue["row_id"] is None, "global (non-row) issues must carry row_id null"


# ── AC-4: schema_version + module_version stamping; UTC RFC3339 Z (OP-3/4) ──


def test_envelope_artifact_stamp_fields():
    artifact = {"kind": "system_validation", "rows": []}
    stamped = stamp_artifact(artifact)
    assert stamped["schema_version"] == SCHEMA_VERSION
    assert stamped["module_version"] == module_version()
    assert RFC3339_Z.match(stamped["generated_at"])
    assert stamped["kind"] == "system_validation" and stamped["rows"] == []
    assert "schema_version" not in artifact, "stamping must not mutate the input"


def test_envelope_module_version_is_version_plus_git_short_hash():
    version = module_version()
    assert re.fullmatch(
        rf"{re.escape(__version__)}\+([0-9a-f]{{4,40}}|unknown)", version
    ), version


def test_envelope_timestamps_utc_rfc3339_z():
    now = utc_now()
    assert RFC3339_Z.match(now), now


# ═══ C-1.2 lock-atomic-corrupt (TC-3.9) ══════════════════════════════════════


@pytest.fixture
def ledger(tmp_path):
    path = tmp_path / "validation-rows.json"
    path.write_text(json.dumps({"rows": [{"row_id": "r-US1-1"}]}, indent=2) + "\n")
    return path


# ── AC-1: FileLock 10s timeout → LEDGER_BUSY (exit 3) ────────────────────────


def test_lock_default_timeout_constant_is_10s():
    assert LEDGER_LOCK_TIMEOUT_S == 10.0


def test_lock_contention_raises_ledger_busy(ledger):
    competitor = FileLock(f"{ledger}.lock")
    with competitor:
        with pytest.raises(LedgerBusyError) as exc_info:
            mutate_ledger(ledger, lambda data: data, timeout_s=0.2)
    err = exc_info.value
    assert err.lock_age_s is None or err.lock_age_s >= 0
    assert str(err), "LedgerBusyError must render a human-readable detail"
    # the contended mutation must not have touched the ledger
    assert json.loads(ledger.read_text())["rows"][0]["row_id"] == "r-US1-1"


def test_lock_busy_maps_to_exit3_envelope_at_boundary(capsys, monkeypatch, tmp_path):
    import validation_emission as ve

    def boom(_args):
        raise LedgerBusyError(tmp_path / "validation-rows.json.lock", 4242, 12.5)

    monkeypatch.setitem(ve.HANDLERS, "status", boom)
    exit_code = main(["status"])
    out = capsys.readouterr().out
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ENV
    assert envelope["status"] == "error"
    assert envelope["code"] == "LEDGER_BUSY"
    assert "4242" in envelope["issues"][0]["detail"], "owner pid surfaces when readable"


def test_lock_held_for_entire_mutation_single_helper(ledger):
    """AC-4: the single mutation helper holds the lock around read+mutate+write."""

    def mutator(data):
        with pytest.raises(Timeout):
            FileLock(f"{ledger}.lock").acquire(timeout=0.05)
        data["rows"].append({"row_id": "r-US1-2"})
        return data

    mutated = mutate_ledger(ledger, mutator, timeout_s=1.0)
    assert [r["row_id"] for r in mutated["rows"]] == ["r-US1-1", "r-US1-2"]
    # lock released afterwards: immediate re-acquire must succeed
    FileLock(f"{ledger}.lock").acquire(timeout=0.05).lock.release()


def test_lock_not_created_by_read_only_path(ledger):
    """AC-4: read-only access has no write path — not even a lock file."""
    data = read_ledger(ledger)
    assert data["rows"][0]["row_id"] == "r-US1-1"
    assert not (ledger.parent / f"{ledger.name}.lock").exists()


# ── AC-2: atomic tmp+rename inside the lock; crash leaves prior intact ───────


def test_atomic_mutation_persists_and_leaves_no_tmp_litter(ledger):
    mutate_ledger(ledger, lambda data: {**data, "rows": []}, timeout_s=1.0)
    assert json.loads(ledger.read_text())["rows"] == []
    assert not list(ledger.parent.glob("*.tmp")), "no .tmp litter after success"


def test_atomic_crash_mid_mutation_leaves_prior_ledger_intact(ledger):
    """TC-3.9c: a mutator crash must not corrupt or alter the ledger."""
    before = ledger.read_text()

    def exploding_mutator(data):
        data["rows"] = "garbage-in-flight"
        raise RuntimeError("simulated crash mid-mutation")

    with pytest.raises(RuntimeError):
        mutate_ledger(ledger, exploding_mutator, timeout_s=1.0)
    assert ledger.read_text() == before, "prior ledger must remain intact"
    assert not list(ledger.parent.glob("*.tmp")), "no .tmp litter after crash"
    # lock must be released after the crash: a fresh mutation succeeds
    mutate_ledger(ledger, lambda data: data, timeout_s=0.5)


# ── AC-3: malformed ledger → quarantine copy first, LEDGER_CORRUPT, no repair ─


def test_corrupt_ledger_quarantined_and_never_auto_repaired(tmp_path):
    ledger_path = tmp_path / "validation-rows.json"
    corrupt_bytes = b'{"rows": [TRUNCATED'
    ledger_path.write_bytes(corrupt_bytes)

    with pytest.raises(LedgerCorruptError) as exc_info:
        read_ledger(ledger_path)

    quarantines = sorted(tmp_path.glob("validation-rows.json.corrupt-*"))
    assert len(quarantines) == 1, "corrupt bytes must be copied aside FIRST"
    assert quarantines[0].read_bytes() == corrupt_bytes
    assert exc_info.value.quarantine_path == quarantines[0]
    assert ledger_path.read_bytes() == corrupt_bytes, "never auto-repaired"


def test_corrupt_ledger_during_mutation_quarantines_without_writing(tmp_path):
    ledger_path = tmp_path / "validation-rows.json"
    corrupt_bytes = b"not json at all"
    ledger_path.write_bytes(corrupt_bytes)

    with pytest.raises(LedgerCorruptError):
        mutate_ledger(ledger_path, lambda data: data, timeout_s=0.5)
    assert ledger_path.read_bytes() == corrupt_bytes
    assert list(tmp_path.glob("validation-rows.json.corrupt-*"))
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_maps_to_exit3_envelope_at_boundary(capsys, monkeypatch, tmp_path):
    import validation_emission as ve

    ledger_path = tmp_path / "validation-rows.json"
    quarantine = tmp_path / "validation-rows.json.corrupt-20260612T000000Z"

    def boom(_args):
        raise LedgerCorruptError(ledger_path, quarantine)

    monkeypatch.setitem(ve.HANDLERS, "status", boom)
    exit_code = main(["status"])
    out = capsys.readouterr().out
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ENV
    assert envelope["status"] == "error"
    assert envelope["code"] == "LEDGER_CORRUPT"
    assert "corrupt-20260612T000000Z" in envelope["issues"][0]["detail"]


# ═══ C-1.3 hash-canonicalization (TC-2.6) ════════════════════════════════════


ROW = {
    "conops_ref": "US-3",
    "scenario": "Jason opens the digest on mobile and judges every row in one sitting.",
    "oracle": "Jason passes this row iff the digest is judgeable without a laptop demonstrates the one-sitting intent from US-3.",
    "evidence_type": "agent-walkthrough-transcript",
    "evidence_rationale": "workflow is conversational; a transcript shows the journey",
    "test_targets": [],
}

CONOPS = (
    "# ConOps: Validation-Leg Production Process\n"
    "## Operational narrative\n"
    "The conductor drafts rows; Jason judges from a digest.\n"
    "## User stories (intent register)\n"
    "### US-0: Bootstrap\n"
    "AS A conductor I WANT a documented entry path SO THAT I can start cold.\n"
    "### US-1: Derive ConOps\n"
    "AS A conductor I WANT a derived ConOps SO THAT intent is registered.\n"
    "### US-2: Late binding\n"
    "AS A conductor I WANT hash binding SO THAT drift is detected.\n"
)


# ── AC-1: pinned canonicalization — NFC, json.dumps list form, full 64-hex ──


def test_row_hash_canonicalization_pinned_to_spec_algorithm():
    import json as json_mod
    import unicodedata

    expected_payload = json_mod.dumps(
        [
            unicodedata.normalize("NFC", ROW["conops_ref"]),
            unicodedata.normalize("NFC", ROW["scenario"]),
            unicodedata.normalize("NFC", ROW["oracle"]),
            unicodedata.normalize("NFC", ROW["evidence_type"]),
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    expected = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
    actual = compute_row_hash(
        ROW["conops_ref"], ROW["scenario"], ROW["oracle"], ROW["evidence_type"]
    )
    assert actual == expected
    assert len(actual) == 64 and re.fullmatch(r"[0-9a-f]{64}", actual)


def test_row_hash_nfc_normalization_unifies_equivalent_unicode():
    composed = "café closes"  # é as single codepoint
    decomposed = "café closes"  # e + combining acute
    h1 = compute_row_hash("US-1", composed, "oracle text", "screenshot")
    h2 = compute_row_hash("US-1", decomposed, "oracle text", "screenshot")
    assert h1 == h2


# ── AC-2: rationale/test_targets excluded; the 4 inputs each move the hash ──


def test_row_hash_excludes_rationale_and_test_targets():
    base = row_hash_for(ROW)
    relabeled = {
        **ROW,
        "evidence_rationale": "completely different rationale",
        "test_targets": ["scripts/tests/test_validation_emission.py::test_x"],
    }
    assert row_hash_for(relabeled) == base, "TC-2.6: excluded fields must not move the hash"


@pytest.mark.parametrize("moving_field", list(ROW_HASH_FIELDS))
def test_row_hash_changes_when_canonical_field_changes(moving_field):
    base = row_hash_for(ROW)
    altered = {**ROW, moving_field: ROW[moving_field] + " CHANGED"}
    assert row_hash_for(altered) != base, f"{moving_field} must move the hash"


def test_row_hash_for_missing_field_raises():
    incomplete = {k: v for k, v in ROW.items() if k != "oracle"}
    with pytest.raises(ValueError, match="oracle"):
        row_hash_for(incomplete)


# ── AC-3: conops_hash over bytes; story_hashes per-section; 12-hex boundary ──


def test_conops_hash_is_sha256_of_file_bytes():
    raw = CONOPS.encode("utf-8")
    assert compute_conops_hash(raw) == hashlib.sha256(raw).hexdigest()


def test_story_hashes_cover_each_us_section():
    hashes = compute_story_hashes(CONOPS)
    assert set(hashes) == {"US-0", "US-1", "US-2"}
    # pinned slice semantics: heading line through the next US heading (or EOF)
    us0_section = CONOPS[CONOPS.index("### US-0") : CONOPS.index("### US-1")]
    assert hashes["US-0"] == hashlib.sha256(us0_section.encode("utf-8")).hexdigest()
    us2_section = CONOPS[CONOPS.index("### US-2") :]
    assert hashes["US-2"] == hashlib.sha256(us2_section.encode("utf-8")).hexdigest()


def test_story_hashes_editing_one_story_moves_only_that_hash():
    before = compute_story_hashes(CONOPS)
    edited = CONOPS.replace(
        "AS A conductor I WANT a derived ConOps SO THAT intent is registered.",
        "AS A conductor I WANT a derived ConOps SO THAT intent is REGISTERED LATE.",
    )
    after = compute_story_hashes(edited)
    assert after["US-1"] != before["US-1"], "edited story must move its hash (FM-3)"
    assert after["US-0"] == before["US-0"]
    assert after["US-2"] == before["US-2"]


def test_hash_prefix_boundary_enforces_minimum_12(capsys):
    full = hashlib.sha256(b"x").hexdigest()
    assert hash_prefix(full) == full[:12]
    assert hash_prefix(full, 16) == full[:16]
    with pytest.raises(ValueError):
        hash_prefix(full, 11)  # SEC-8: prefixes <12 are rejected
    with pytest.raises(ValueError):
        hash_prefix("not-a-hash")


# ── AC-4: lengths/constants pinned ───────────────────────────────────────────


def test_hash_constants_pinned():
    assert HASH_PREFIX_LEN == 12
    assert ROW_HASH_FIELDS == ("conops_ref", "scenario", "oracle", "evidence_type")
    assert len(compute_conops_hash(b"")) == 64


# ═══ C-1.4 path-containment-bounds (TC-1.4, TC-2.6) ══════════════════════════


# ── AC-1: artifact paths resolved under spec root via realpath (SEC-9) ───────


def test_path_containment_resolves_relative_candidate_under_root(tmp_path):
    (tmp_path / "validation-evidence").mkdir()
    resolved = resolve_under_root(tmp_path, "validation-evidence/r-US1-1/evidence.md")
    assert resolved == tmp_path.resolve() / "validation-evidence/r-US1-1/evidence.md"


def test_path_containment_rejects_dotdot_escape(tmp_path):
    with pytest.raises(ValidationIssuesError) as exc_info:
        resolve_under_root(tmp_path, "../outside/evidence.md")
    assert exc_info.value.code == "PATH_OUTSIDE_ROOT"


def test_path_containment_rejects_absolute_path_outside_root(tmp_path):
    with pytest.raises(ValidationIssuesError):
        resolve_under_root(tmp_path, "/etc/passwd")
    # absolute path INSIDE the root is fine
    inside = tmp_path / "conops.md"
    assert resolve_under_root(tmp_path, str(inside)) == inside.resolve()


def test_path_containment_rejects_symlink_escape(tmp_path):
    root = tmp_path / "spec-root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.md").write_text("secret")
    (root / "sneaky").symlink_to(outside)
    with pytest.raises(ValidationIssuesError) as exc_info:
        resolve_under_root(root, "sneaky/secret.md")
    assert exc_info.value.code == "PATH_OUTSIDE_ROOT"


def test_path_outside_root_maps_to_exit2_envelope_at_boundary(capsys, monkeypatch, tmp_path):
    import validation_emission as ve

    def boom(_args):
        resolve_under_root(tmp_path, "../escape.md")
        raise AssertionError("unreachable")

    monkeypatch.setitem(ve.HANDLERS, "status", boom)
    exit_code = main(["status"])
    envelope = parse_single_envelope(capsys.readouterr().out)
    assert exit_code == EXIT_ISSUES
    assert envelope["status"] == "issues"
    assert envelope["code"] == "PATH_OUTSIDE_ROOT"


# ── AC-2: input byte budgets → structured exit 2 (SEC-10) ────────────────────


def test_bounds_constants_pinned():
    assert REPLY_MAX_BYTES == 16 * 1024
    assert JUSTIFICATION_MAX_BYTES == 2 * 1024
    assert LEDGER_MAX_BYTES == 5 * 1024 * 1024
    assert CONOPS_MAX_BYTES == 1024 * 1024


@pytest.mark.parametrize(
    ("kind", "limit"),
    [("reply", 16 * 1024), ("justification", 2 * 1024),
     ("ledger", 5 * 1024 * 1024), ("conops", 1024 * 1024)],
)
def test_bounds_at_limit_pass_and_over_limit_reject(kind, limit):
    enforce_input_bounds(kind, b"x" * limit)  # exactly at the limit: fine
    with pytest.raises(ValidationIssuesError) as exc_info:
        enforce_input_bounds(kind, b"x" * (limit + 1))
    err = exc_info.value
    assert err.code == "INPUT_BOUNDS_EXCEEDED"
    assert kind in err.issues[0]["detail"]
    assert str(limit) in err.issues[0]["detail"]


def test_bounds_measure_utf8_bytes_not_characters():
    # 1024 four-byte emoji = 4096 bytes > 2KB justification budget
    with pytest.raises(ValidationIssuesError):
        enforce_input_bounds("justification", "🥊" * 1024)


def test_bounds_unknown_kind_is_a_programming_error():
    with pytest.raises(ValueError):
        enforce_input_bounds("novel-kind", b"x")


def test_bounds_exceeded_maps_to_exit2_envelope_at_boundary(capsys, monkeypatch):
    import validation_emission as ve

    def boom(_args):
        enforce_input_bounds("reply", b"x" * (REPLY_MAX_BYTES + 1))
        raise AssertionError("unreachable")

    monkeypatch.setitem(ve.HANDLERS, "status", boom)
    exit_code = main(["status"])
    envelope = parse_single_envelope(capsys.readouterr().out)
    assert exit_code == EXIT_ISSUES
    assert envelope["code"] == "INPUT_BOUNDS_EXCEEDED"


# ── AC-3: row_id global uniqueness incl. superseded; dup story ids exit 2 ────


def test_row_id_uniqueness_bounds_include_superseded_snapshots():
    ledger = {
        "rows": [{"row_id": "r-US1-1"}, {"row_id": "r-US1-2"}],
        "superseded": [{"row_snapshot": {"row_id": "r-US1-1"}}],
    }
    assert find_duplicate_row_ids(ledger) == ["r-US1-1"]


def test_row_id_uniqueness_bounds_clean_ledger_has_no_duplicates():
    ledger = {
        "rows": [{"row_id": "r-US1-2"}],
        "superseded": [{"row_snapshot": {"row_id": "r-US1-1"}}],
    }
    assert find_duplicate_row_ids(ledger) == []


def test_duplicate_story_ids_rejected_bounds():
    # duplicates reported in the order the duplication is DETECTED
    assert find_duplicate_story_ids(["US-0", "US-1", "US-1", "US-2", "US-0"]) == [
        "US-1",
        "US-0",
    ]
    assert find_duplicate_story_ids(["US-0", "US-1"]) == []
