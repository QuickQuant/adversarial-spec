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
from validation_emission import (
    ENVELOPE_STATUSES,
    EXIT_ENV,
    EXIT_ISSUES,
    EXIT_OK,
    SCHEMA_VERSION,
    SUBCOMMANDS,
    __version__,
    exit_code_for_status,
    main,
    module_version,
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
