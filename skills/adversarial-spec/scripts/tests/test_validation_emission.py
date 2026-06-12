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

import json
import re

import pytest
from filelock import FileLock, Timeout
from validation_emission import (
    ENVELOPE_STATUSES,
    EXIT_ENV,
    EXIT_ISSUES,
    EXIT_OK,
    LEDGER_LOCK_TIMEOUT_S,
    SCHEMA_VERSION,
    SUBCOMMANDS,
    LedgerBusyError,
    LedgerCorruptError,
    __version__,
    exit_code_for_status,
    main,
    module_version,
    mutate_ledger,
    read_ledger,
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
