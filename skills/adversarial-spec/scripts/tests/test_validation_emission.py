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
    uv run pytest scripts/tests/test_validation_emission.py -q
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


def test_envelope_root_help_stays_inside_json_envelope(capsys):
    exit_code, out, err = run_cli(capsys, ["--help"])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_OK
    assert err == ""
    assert envelope["status"] == "ok"
    assert envelope["data"]["usage"] == "validation_emission.py <subcommand> [options]"
    assert envelope["data"]["subcommand"] is None


def test_envelope_subcommand_help_stays_inside_json_envelope(capsys):
    exit_code, out, err = run_cli(capsys, ["status", "--help"])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_OK
    assert err == ""
    assert envelope["status"] == "ok"
    assert envelope["data"]["usage"] == "validation_emission.py status [options]"
    assert envelope["data"]["subcommand"] == "status"


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


# ═══ C-2.1 derive-conops (TC-1.1, TC-1.2, TC-1.3, TC-G13) ═══════════════════


def _manifest(stories):
    return {
        "title": "Validation Demo",
        "session_id": "adv-spec-test",
        "milestones": [
            {
                "id": "M1",
                "name": "ConOps Derivation",
                "context": "Derive intent from the manifest.",
                "user_stories": [story["id"] for story in stories],
            }
        ],
        "user_stories": stories,
    }


def _write_manifest(tmp_path, manifest):
    roadmap = tmp_path / "roadmap"
    roadmap.mkdir()
    path = roadmap / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def test_conops_derivation_writes_every_story_heading_and_hashes(capsys, tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        _manifest(
            [
                {
                    "id": "US-0",
                    "title": "Bootstrap",
                    "story": "As a conductor, I want one entry point so that setup is repeatable.",
                },
                {
                    "id": "US-1",
                    "title": "Derive ConOps",
                    "story": "As a conductor, I want derived intent so that validation is fresh.",
                },
            ]
        ),
    )
    output = tmp_path / "roadmap" / "conops.md"

    exit_code, out, err = run_cli(capsys, ["derive-conops", str(manifest_path)])

    envelope = parse_single_envelope(out)
    conops = output.read_text(encoding="utf-8")
    assert exit_code == EXIT_OK
    assert err == ""
    assert envelope["status"] == "ok"
    assert re.search(r"^### US-0: Bootstrap$", conops, re.MULTILINE)
    assert re.search(r"^### US-1: Derive ConOps$", conops, re.MULTILINE)
    assert len(conops.encode("utf-8")) >= 50
    assert envelope["data"]["path"] == str(output)
    assert envelope["data"]["conops_hash"] == compute_conops_hash(
        conops.encode("utf-8")
    )
    assert set(envelope["data"]["story_hashes"]) == {"US-0", "US-1"}


def test_conops_derivation_rejects_stray_story_ids_before_write(capsys, tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        _manifest(
            [
                {
                    "id": "US-1",
                    "title": "No Phantom Stories",
                    "story": "As a conductor, I want no reference that replaces US-99.",
                }
            ]
        ),
    )
    output = tmp_path / "roadmap" / "conops.md"

    exit_code, out, _err = run_cli(capsys, ["derive-conops", str(manifest_path)])

    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert envelope["code"] == "STRAY_CONOPS_STORY_ID"
    assert "US-99" in envelope["issues"][0]["detail"]
    assert not output.exists()


def test_conops_derivation_rejects_duplicate_manifest_story_ids(capsys, tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        _manifest(
            [
                {"id": "US-1", "title": "One", "story": "As a user, I want one."},
                {"id": "US-1", "title": "Again", "story": "As a user, I want two."},
            ]
        ),
    )

    exit_code, out, _err = run_cli(capsys, ["derive-conops", str(manifest_path)])

    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert envelope["code"] == "DUPLICATE_STORY_ID"
    assert "US-1" in envelope["issues"][0]["detail"]


def test_conops_rederive_refuses_ledger_bound_overwrite_without_force(
    capsys, tmp_path
):
    manifest = _manifest(
        [
            {
                "id": "US-1",
                "title": "Fresh Intent",
                "story": "As a conductor, I want original intent.",
            }
        ]
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    output = tmp_path / "roadmap" / "conops.md"
    exit_code, out, _err = run_cli(capsys, ["derive-conops", str(manifest_path)])
    assert exit_code == EXIT_OK
    prior_hash = parse_single_envelope(out)["data"]["conops_hash"]
    prior_text = output.read_text(encoding="utf-8")
    (tmp_path / "validation-rows.json").write_text(
        json.dumps({"conops_hash": prior_hash, "rows": []}), encoding="utf-8"
    )
    manifest["user_stories"][0]["story"] = "As a conductor, I want edited intent."
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    exit_code, out, _err = run_cli(capsys, ["derive-conops", str(manifest_path)])
    envelope = parse_single_envelope(out)

    assert exit_code == EXIT_ISSUES
    assert envelope["code"] == "CONOPS_OVERWRITE_REQUIRES_FORCE"
    assert output.read_text(encoding="utf-8") == prior_text

    exit_code, out, _err = run_cli(
        capsys, ["derive-conops", str(manifest_path), "--force"]
    )
    envelope = parse_single_envelope(out)

    assert exit_code == EXIT_OK
    assert envelope["data"]["prior_conops_hash"] == prior_hash
    assert envelope["data"]["conops_hash"] != prior_hash
    assert "edited intent" in output.read_text(encoding="utf-8")


# ═══ C-4.4 emit-system-validation (TC-3.1, TC-3.3, TC-3.6, TC-3.8) ═══════════


@pytest.fixture
def emission_env(tmp_path):
    conops_path = tmp_path / "conops.md"
    conops_text = (
        "## User stories\n"
        "### US-1: First\n"
        "### US-2: Second\n"
    )
    conops_path.write_text(conops_text)
    story_hashes = compute_story_hashes(conops_text)

    ledger_path = tmp_path / "validation-rows.json"
    row = {
        "row_id": "r-US1-1",
        "conops_ref": "US-1",
        "scenario": "scenario 1",
        "oracle": "oracle 1",
        "evidence_type": "narrative",
        "story_hash": story_hashes["US-1"],
        "result": "pass",
        "judgment": {
            "judged_by": "jason",
            "judged_at": "2026-06-12T00:00:00Z",
            "digest_id": "d-1",
            "source": "terminal",
            "reply_ref": "transcript:123"
        }
    }
    # US-2 also needs a pass for coverage
    row2 = {
        "row_id": "r-US2-1",
        "conops_ref": "US-2",
        "scenario": "scenario 2",
        "oracle": "oracle 2",
        "evidence_type": "narrative",
        "story_hash": story_hashes["US-2"],
        "result": "pass",
        "judgment": {
            "judged_by": "jason",
            "judged_at": "2026-06-12T00:00:00Z",
            "digest_id": "d-1",
            "source": "terminal",
            "reply_ref": "transcript:123"
        }
    }
    ledger_path.write_text(json.dumps({"rows": [row, row2]}))

    ev_dir = tmp_path / "validation-evidence" / "r-US1-1"
    ev_dir.mkdir(parents=True)
    (ev_dir / "evidence.md").write_text("evidence 1")

    ev_dir2 = tmp_path / "validation-evidence" / "r-US2-1"
    ev_dir2.mkdir(parents=True)
    (ev_dir2 / "evidence.md").write_text("evidence 2")

    return tmp_path, ledger_path, conops_path


def test_emit_system_validation_success_projection(capsys, emission_env):
    tmp_path, ledger_path, conops_path = emission_env
    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_OK
    assert envelope["status"] == "ok"

    artifact_path = tmp_path / "system_validation.json"
    assert artifact_path.exists()
    artifact = json.loads(artifact_path.read_text())

    assert artifact["kind"] == "system-validation"
    assert len(artifact["conops_hash"]) == 12
    assert len(artifact["ledger_hash"]) == 64
    assert len(artifact["rows"]) == 2
    assert artifact["rows"][0]["result"] == "pass"
    assert artifact["rows"][0]["judged_by"] == "jason"
    assert artifact["rows"][0]["judged_at"] == "2026-06-12T00:00:00Z"
    assert artifact["rows"][0]["source"] == "terminal"
    assert artifact["rows"][0]["digest_id"] == "d-1"
    assert artifact["rows"][0]["reply_ref"] == "transcript:123"
    assert artifact["rows"][0]["evidence_ref"] == "validation-evidence/r-US1-1/evidence.md"
    assert "evidence_hash" in artifact["rows"][0]


def test_emit_system_validation_na_mapping_cb12(capsys, emission_env):
    tmp_path, ledger_path, conops_path = emission_env
    ledger = json.loads(ledger_path.read_text())
    ledger["rows"][0]["result"] = "na"
    # Still need US-1 pass for coverage, so let's add another row
    new_row = dict(ledger["rows"][0])
    new_row["row_id"] = "r-US1-2"
    new_row["result"] = "pass"
    ledger["rows"].append(new_row)
    ledger_path.write_text(json.dumps(ledger))

    # ensure evidence exists for r-US1-2
    ev_dir = tmp_path / "validation-evidence" / "r-US1-2"
    ev_dir.mkdir(parents=True)
    (ev_dir / "evidence.md").write_text("evidence 1-2")

    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    parse_single_envelope(out)
    assert exit_code == EXIT_OK

    artifact = json.loads((tmp_path / "system_validation.json").read_text())
    # r-US1-1 was na
    assert artifact["rows"][0]["result"] == "not-applicable"


def test_emit_system_validation_refuses_unjudged_failed(capsys, emission_env):
    _tmp_path, ledger_path, conops_path = emission_env
    ledger = json.loads(ledger_path.read_text())
    ledger["rows"][0]["result"] = None
    ledger_path.write_text(json.dumps(ledger))

    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == "UNJUDGED_ROW" for i in envelope["issues"])

    ledger["rows"][0]["result"] = "fail"
    ledger_path.write_text(json.dumps(ledger))
    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == "FAILED_ROW" for i in envelope["issues"])


def test_emit_system_validation_refuses_provenance_missing_inv1(capsys, emission_env):
    _tmp_path, ledger_path, conops_path = emission_env
    ledger = json.loads(ledger_path.read_text())
    ledger["rows"][0]["judgment"] = None
    ledger_path.write_text(json.dumps(ledger))

    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == "PROVENANCE_MISSING" for i in envelope["issues"])


def test_emit_system_validation_refuses_provenance_missing_fields_ac2(capsys, emission_env):
    _tmp_path, ledger_path, conops_path = emission_env
    ledger = json.loads(ledger_path.read_text())
    # Truthy but missing required fields (AC-2)
    ledger["rows"][0]["judgment"] = {"judged_by": "jason"}
    ledger_path.write_text(json.dumps(ledger))

    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    issue = next(i for i in envelope["issues"] if i["code"] == "PROVENANCE_MISSING")
    assert "missing required fields" in issue["detail"]
    assert "judged_at" in issue["detail"]
    assert "source" in issue["detail"]
    assert "digest_id" in issue["detail"]
    assert "reply_ref" in issue["detail"]


def test_emit_system_validation_refuses_stale_conops_fm3(capsys, emission_env):
    _tmp_path, ledger_path, conops_path = emission_env
    # Change conops without updating ledger story_hash
    conops_text = conops_path.read_text()
    conops_path.write_text(conops_text + "\n### US-3: Added")

    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    # Both US-1/US-2 are now stale because compute_story_hashes for US-2
    # might include US-3 section if US-2 was last.
    # Actually US-1 should be same, US-2 changed if it's now followed by US-3.
    assert any(i["code"] == "STALE_STORY_HASH" for i in envelope["issues"])


def test_emit_system_validation_refuses_unvalidated_story_tc36(capsys, emission_env):
    _tmp_path, ledger_path, conops_path = emission_env
    ledger = json.loads(ledger_path.read_text())
    # US-2 row becomes NA -> US-2 has no pass row
    ledger["rows"][1]["result"] = "na"
    ledger_path.write_text(json.dumps(ledger))

    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == "UNVALIDATED_USER_STORY" for i in envelope["issues"])


def test_emit_system_validation_skips_superseded_rows_inv10(capsys, emission_env):
    """Active-row predicate (spec §6.2): a row left in rows[] whose row_id
    appears in superseded[].row_snapshot.row_id is INACTIVE — it must neither
    block emission (even unjudged) nor appear in the projection (INV-10), and
    it must not satisfy coverage (INV-7)."""
    tmp_path, ledger_path, conops_path = emission_env
    ledger = json.loads(ledger_path.read_text())

    # An unjudged superseded row: must not block emission or project.
    stale_row = dict(ledger["rows"][0])
    stale_row["row_id"] = "r-US1-9"
    stale_row["result"] = None
    stale_row["judgment"] = None
    ledger["rows"].append(stale_row)
    ledger["superseded"] = [{
        "row_snapshot": {"row_id": "r-US1-9"},
        "reason": "duplicate coverage",
        "approver": "jason",
        "approval_ref": "decision:2026-06-12T00:00:00Z",
        "approved_at": "2026-06-12T00:00:00Z",
        "replacement_row_id": "r-US1-1",
    }]
    ledger_path.write_text(json.dumps(ledger))

    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    parse_single_envelope(out)
    assert exit_code == EXIT_OK

    artifact = json.loads((tmp_path / "system_validation.json").read_text())
    assert [r["row_id"] for r in artifact["rows"]] == ["r-US1-1", "r-US2-1"]

    # A superseded PASS row must not satisfy coverage: retire US-2's only row.
    ledger["superseded"].append({
        "row_snapshot": {"row_id": "r-US2-1"},
        "reason": "post-judgment retirement",
        "approver": "jason",
        "approval_ref": "decision:2026-06-12T00:00:01Z",
        "approved_at": "2026-06-12T00:00:01Z",
        "replacement_row_id": "r-US2-2",
    })
    ledger_path.write_text(json.dumps(ledger))

    exit_code, out, _err = run_cli(capsys, [
        "emit-system-validation", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(
        i["code"] == "UNVALIDATED_USER_STORY" and "US-2" in i["detail"]
        for i in envelope["issues"]
    )


# ═══ C-2.3 check-rows (TC-2.3, INV-6, INV-11, CB-10) ══════════════════════════


@pytest.fixture
def check_env(tmp_path):
    conops_path = tmp_path / "conops.md"
    conops_text = (
        "## User stories\n"
        "### US-1: First\n"
        "### US-2: Second\n"
    )
    conops_path.write_text(conops_text)

    ledger_path = tmp_path / "validation-rows.json"
    row = {
        "row_id": "r-US1-1",
        "conops_ref": "US-1",
        "scenario": "scenario 1",
        "oracle": "Jason passes iff US-1 works as intended.",  # Issues: banned phrase, but has iff and US-1
        "evidence_type": "narrative",
        "test_targets": ["t1"],
    }
    row2 = {
        "row_id": "r-US2-1",
        "conops_ref": "US-2",
        "scenario": "scenario 2",
        "oracle": "Success iff US-2 is cool.",  # Issues: vague terminal, but has iff and US-2
        "evidence_type": "narrative",
        "test_targets": ["t2"],
    }
    ledger_path.write_text(json.dumps({"rows": [row, row2]}))

    v_ledger_path = tmp_path / "verification-rows.json"
    v_ledger_path.write_text(
        json.dumps({"rows": [{"requirement_id": "req-1", "test_targets": ["t1"]}]})
    )

    return tmp_path, ledger_path, conops_path, v_ledger_path


def test_check_rows_detects_oracle_lint_issues(capsys, check_env):
    tmp_path, ledger_path, conops_path, _ = check_env
    exit_code, out, _err = run_cli(
        capsys, ["check-rows", str(ledger_path), "--conops", str(conops_path)]
    )
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert envelope["status"] == "issues"

    codes = [i["code"] for i in envelope["issues"]]
    assert "BANNED_ORACLE_PHRASE" in codes  # "works as intended"
    assert "VAGUE_ORACLE" in codes  # "Success" in short oracle


def test_check_rows_detects_missing_iff_and_story_ref(capsys, tmp_path):
    conops_path = tmp_path / "conops.md"
    conops_path.write_text("### US-1: First")

    ledger_path = tmp_path / "validation-rows.json"
    row = {
        "row_id": "r-1",
        "conops_ref": "US-1",
        "scenario": "s",
        "oracle": "It just works.",  # No iff, no US-1
        "evidence_type": "n",
    }
    ledger_path.write_text(json.dumps({"rows": [row]}))

    exit_code, out, _err = run_cli(
        capsys, ["check-rows", str(ledger_path), "--conops", str(conops_path)]
    )
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    codes = [i["code"] for i in envelope["issues"]]
    assert "ORACLE_MISSING_IFF" in codes
    assert "ORACLE_MISSING_STORY_REF" in codes


def test_check_rows_detects_incomplete_coverage(capsys, tmp_path):
    conops_path = tmp_path / "conops.md"
    conops_path.write_text("### US-1: First\n### US-2: Second")

    ledger_path = tmp_path / "validation-rows.json"
    # A fully valid row covering US-1 only — US-2 stays uncovered, so the ONLY
    # issue is coverage. Draft mode relaxes coverage alone (spec §7); an
    # invalid row would keep exit 2 in draft mode by design.
    scenario = (
        "Jason runs check-rows on the drafted ledger and reads the envelope"
        " to confirm coverage state before committing."
    )
    oracle = (
        "Jason passes this row iff the check-rows envelope demonstrates the"
        " coverage-gate intent from US-1."
    )
    row = {
        "row_id": "r-US1-1",
        "conops_ref": "US-1",
        "scenario": scenario,
        "oracle": oracle,
        "evidence_type": "narrative",
        "evidence_rationale": "narrative is sufficient for a CLI envelope check",
        "row_hash": compute_row_hash("US-1", scenario, oracle, "narrative"),
    }
    ledger_path.write_text(json.dumps({"rows": [row]}))

    # Normal mode: error
    exit_code, out, _err = run_cli(
        capsys, ["check-rows", str(ledger_path), "--conops", str(conops_path)]
    )
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    codes = [i["code"] for i in envelope["issues"]]
    assert codes == ["INCOMPLETE_COVERAGE"]

    # Draft mode: advisory (status ok)
    exit_code, out, _err = run_cli(
        capsys,
        ["check-rows", str(ledger_path), "--conops", str(conops_path), "--draft"],
    )
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_OK
    codes = [i["code"] for i in envelope["issues"]]
    assert codes == ["INCOMPLETE_COVERAGE_ADVISORY"]


def test_check_rows_detects_relabeled_verification(capsys, check_env):
    tmp_path, ledger_path, conops_path, v_ledger_path = check_env
    # r-US1-1 has test_targets ["t1"], which is in v_ledger_path

    exit_code, out, _err = run_cli(
        capsys,
        [
            "check-rows",
            str(ledger_path),
            "--conops",
            str(conops_path),
            "--verification-ledger",
            str(v_ledger_path),
        ],
    )
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == "RELABELED_VERIFICATION" for i in envelope["issues"])

    # Fixed with rationale
    ledger = json.loads(ledger_path.read_text())
    ledger["rows"][0]["evidence_rationale"] = "Validating same target with human eyes."
    ledger_path.write_text(json.dumps(ledger))

    exit_code, out, _err = run_cli(
        capsys,
        [
            "check-rows",
            str(ledger_path),
            "--conops",
            str(conops_path),
            "--verification-ledger",
            str(v_ledger_path),
        ],
    )
    envelope = parse_single_envelope(out)
    # Still has oracle lint issues, but RELABELED_VERIFICATION should be gone.
    assert not any(i["code"] == "RELABELED_VERIFICATION" for i in envelope["issues"])


# ═══ C-3.1 record-evidence (TC-3.1, FM-2, INV-9, INV-12) ══════════════════════


@pytest.fixture
def evidence_env(tmp_path):
    conops_path = tmp_path / "conops.md"
    conops_text = (
        "## User stories\n"
        "### US-1: First\n"
    )
    conops_path.write_text(conops_text)

    ledger_path = tmp_path / "validation-rows.json"
    row = {
        "row_id": "r-US1-1",
        "conops_ref": "US-1",
        "scenario": "scenario 1",
        "oracle": "Jason passes iff US-1 works.",
        "evidence_type": "narrative",
    }
    ledger_path.write_text(json.dumps({"rows": [row]}))

    return tmp_path, ledger_path, conops_path


def test_record_evidence_scaffolds_file_and_mutates_ledger(capsys, evidence_env):
    tmp_path, ledger_path, conops_path = evidence_env

    exit_code, out, _err = run_cli(capsys, [
        "record-evidence", str(ledger_path),
        "--row", "r-US1-1",
        "--summary", "Summary of evidence",
        "--conops", str(conops_path),
        "--commit", "abc1234"
    ])

    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_OK
    assert envelope["status"] == "ok"

    # Check ledger mutation
    ledger = json.loads(ledger_path.read_text())
    row = ledger["rows"][0]
    assert row["evidence_summary"] == "Summary of evidence"
    assert "row_hash" in row
    assert "story_hash" in row

    # Check evidence scaffolding
    ev_path = tmp_path / "validation-evidence" / "r-US1-1" / "evidence.md"
    assert ev_path.exists()
    content = ev_path.read_text()
    assert "row_id: r-US1-1" in content
    assert f"row_hash: {row['row_hash']}" in content
    assert f"story_hash: {row['story_hash']}" in content
    assert "commit: abc1234" in content
    assert "worktree_clean: " in content

    # Check FM-2 order (partial check)
    lines = content.strip().splitlines()
    assert lines[0] == "---"
    assert lines[1] == "row_id: r-US1-1"
    assert lines[2].startswith("row_hash: ")


def test_record_evidence_validates_existing_file_hashes(capsys, evidence_env):
    tmp_path, ledger_path, conops_path = evidence_env

    # First call: scaffold
    run_cli(capsys, [
        "record-evidence", str(ledger_path),
        "--row", "r-US1-1",
        "--summary", "Summary 1",
        "--conops", str(conops_path)
    ])

    # Second call: valid re-invocation
    exit_code, out, _err = run_cli(capsys, [
        "record-evidence", str(ledger_path),
        "--row", "r-US1-1",
        "--summary", "Summary 2",
        "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_OK

    # Modify ledger (change scenario) -> row_hash changes
    ledger = json.loads(ledger_path.read_text())
    ledger["rows"][0]["scenario"] = "changed scenario"
    ledger_path.write_text(json.dumps(ledger))

    # Third call: hash mismatch (INV-12)
    exit_code, out, _err = run_cli(capsys, [
        "record-evidence", str(ledger_path),
        "--row", "r-US1-1",
        "--summary", "Summary 3",
        "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == "EVIDENCE_HASH_MISMATCH" for i in envelope["issues"])


def test_record_evidence_detects_malformed_front_matter(capsys, evidence_env):
    tmp_path, ledger_path, conops_path = evidence_env

    ev_dir = tmp_path / "validation-evidence" / "r-US1-1"
    ev_dir.mkdir(parents=True)
    ev_path = ev_dir / "evidence.md"
    ev_path.write_text("No front matter here")

    exit_code, out, _err = run_cli(capsys, [
        "record-evidence", str(ledger_path),
        "--row", "r-US1-1",
        "--summary", "Summary",
        "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == "EVIDENCE_MALFORMED" for i in envelope["issues"])


# ═══ C-2.2 normalize-rows (TC-2.2, CB-7) ══════════════════════════════════════


def test_normalize_rows_stamps_hashes(capsys, evidence_env):
    tmp_path, ledger_path, conops_path = evidence_env

    exit_code, out, _err = run_cli(capsys, [
        "normalize-rows", str(ledger_path), "--conops", str(conops_path)
    ])

    parse_single_envelope(out)
    assert exit_code == EXIT_OK

    ledger = json.loads(ledger_path.read_text())
    row = ledger["rows"][0]
    assert "row_hash" in row
    assert "story_hash" in row
    assert ledger["conops_hash"] == compute_conops_hash(conops_path.read_bytes())


def test_normalize_rows_stamps_ledger_schema_fields(capsys, evidence_env):
    """AC-2 stamping half: ledger header carries schema_version,
    module_version, kind, conops_hash, story_hashes after normalize."""
    _tmp_path, ledger_path, conops_path = evidence_env
    exit_code, out, _err = run_cli(capsys, [
        "normalize-rows", str(ledger_path), "--conops", str(conops_path)
    ])
    parse_single_envelope(out)
    assert exit_code == EXIT_OK

    ledger = json.loads(ledger_path.read_text())
    assert ledger["kind"] == "validation-rows-ledger"
    assert ledger["schema_version"] == SCHEMA_VERSION
    assert ledger["module_version"] == module_version()
    assert ledger["story_hashes"] == compute_story_hashes(
        conops_path.read_text(encoding="utf-8")
    )
    # Stamped row_hash matches the pinned canonicalization (TC-G11)
    row = ledger["rows"][0]
    assert row["row_hash"] == compute_row_hash(
        row["conops_ref"], row["scenario"], row["oracle"], row["evidence_type"]
    )


def _normalize_reject_env(tmp_path, rows, superseded=None):
    conops_path = tmp_path / "conops.md"
    conops_path.write_text("## User stories\n### US-1: First\n### US-2: Second\n")
    ledger_path = tmp_path / "validation-rows.json"
    ledger = {"rows": rows}
    if superseded is not None:
        ledger["superseded"] = superseded
    ledger_path.write_text(json.dumps(ledger))
    return ledger_path, conops_path


def _draft_row(row_id, conops_ref="US-1"):
    return {
        "row_id": row_id,
        "conops_ref": conops_ref,
        "scenario": "scenario text",
        "oracle": "Jason passes iff outcome demonstrates US intent.",
        "evidence_type": "narrative",
    }


@pytest.mark.parametrize(
    ("rows", "superseded", "code"),
    [
        # AC-2: row_id format r-US<n>-<k>
        ([_draft_row("r-1")], None, "INVALID_ROW_ID"),
        # AC-2: global uniqueness within rows[]
        ([_draft_row("r-US1-1"), _draft_row("r-US1-1")], None, "DUPLICATE_ROW_ID"),
        # AC-2: global uniqueness includes superseded snapshots (spec §3)
        (
            [_draft_row("r-US1-1")],
            [{"row_snapshot": {"row_id": "r-US1-1"}}],
            "DUPLICATE_ROW_ID",
        ),
        # AC-2: story-prefix match — row_id story number vs conops_ref
        ([_draft_row("r-US2-1", conops_ref="US-1")], None, "ROW_ID_STORY_MISMATCH"),
        # Fail-fast: conops_ref not present in conops.md (no silent skip)
        ([_draft_row("r-US9-1", conops_ref="US-9")], None, "UNKNOWN_CONOPS_REF"),
    ],
)
def test_normalize_rows_rejects_invalid_rows(capsys, tmp_path, rows, superseded, code):
    """AC-2 validation half: invalid rows produce an issues envelope (exit 2)
    and the ledger file is NOT mutated (mutate_ledger aborts before write)."""
    ledger_path, conops_path = _normalize_reject_env(tmp_path, rows, superseded)
    before = ledger_path.read_bytes()

    exit_code, out, _err = run_cli(capsys, [
        "normalize-rows", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == code for i in envelope["issues"]), envelope["issues"]
    assert ledger_path.read_bytes() == before


def test_normalize_rows_handwritten_hash_flagged_by_check_rows_tcg11(capsys, tmp_path):
    """TC-G11 second half: a conductor hand-writing a (wrong) row_hash is
    caught by check-rows as a structured issue — the module is the sole hex
    producer (CB-7)."""
    ledger_path, conops_path = _normalize_reject_env(
        tmp_path, [_draft_row("r-US1-1"), _draft_row("r-US2-1", conops_ref="US-2")]
    )
    exit_code, out, _err = run_cli(capsys, [
        "normalize-rows", str(ledger_path), "--conops", str(conops_path)
    ])
    assert exit_code == EXIT_OK

    ledger = json.loads(ledger_path.read_text())
    ledger["rows"][0]["row_hash"] = "ab" * 32  # hand-written, wrong
    ledger_path.write_text(json.dumps(ledger))

    exit_code, out, _err = run_cli(capsys, [
        "check-rows", str(ledger_path), "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(
        i["code"] == "ROW_HASH_MISMATCH" and i["row_id"] == "r-US1-1"
        for i in envelope["issues"]
    )


def test_record_evidence_per_story_invalidation_fm3(capsys, tmp_path):
    conops_path = tmp_path / "conops.md"
    conops_text = (
        "## User stories\n"
        "### US-1: First\n"
        "### US-2: Second\n"
    )
    conops_path.write_text(conops_text)

    ledger_path = tmp_path / "validation-rows.json"
    rows = [
        {"row_id": "r-US1-1", "conops_ref": "US-1", "scenario": "s1", "oracle": "o1", "evidence_type": "n"},
        {"row_id": "r-US2-1", "conops_ref": "US-2", "scenario": "s2", "oracle": "o2", "evidence_type": "n"},
    ]
    ledger_path.write_text(json.dumps({"rows": rows}))

    # Scaffold both
    for rid in ["r-US1-1", "r-US2-1"]:
        run_cli(capsys, [
            "record-evidence", str(ledger_path), "--row", rid,
            "--summary", "Summary", "--conops", str(conops_path)
        ])

    # Edit US-1 in ConOps
    new_conops_text = conops_text.replace("### US-1: First", "### US-1: First (EDITED)")
    conops_path.write_text(new_conops_text)

    # US-1 should be invalidated
    exit_code, out, _err = run_cli(capsys, [
        "record-evidence", str(ledger_path), "--row", "r-US1-1",
        "--summary", "Summary", "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_ISSUES
    assert any(i["code"] == "EVIDENCE_HASH_MISMATCH" for i in envelope["issues"])
    assert "story_hash mismatch" in str(envelope["issues"])

    # US-2 should still be valid (FM-3)
    exit_code, out, _err = run_cli(capsys, [
        "record-evidence", str(ledger_path), "--row", "r-US2-1",
        "--summary", "Summary", "--conops", str(conops_path)
    ])
    envelope = parse_single_envelope(out)
    assert exit_code == EXIT_OK
