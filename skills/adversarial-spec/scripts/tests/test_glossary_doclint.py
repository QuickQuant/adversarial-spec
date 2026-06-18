"""Doc lint for glossary and happy-path spine terminology."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DOCS = [
    ROOT / "CONTEXT.md",
    ROOT / "skills/adversarial-spec/reference/document-types.md",
    *sorted((ROOT / "docs/adr").glob("*.md")),
]
REQUIRED_CONTEXT_TERMS = (
    "Happy-Path Spine",
    "Test Maturity Record",
    "Maturity Ladder",
    "Liveness",
)
REQUIRED_ADR_TOKENS = (
    "Test Maturity Record",
    "Maturity Ladder",
    "Liveness",
    "happy-path spine",
    "Architecture Spine",
    "Fizzy persists/enforces",
)
MACHINE_TOKEN_RE = re.compile(
    r"`[^`]*(?:spine|SpineCoverageChecker)[^`]*`|SpineCoverageChecker"
)


def prose_without_machine_tokens(text: str) -> str:
    return MACHINE_TOKEN_RE.sub("", text)


def bare_spine_violations(path: Path) -> list[tuple[int, str]]:
    violations = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        prose = prose_without_machine_tokens(line)
        for match in re.finditer(r"\b[Ss]pine\b", prose):
            prefix = prose[max(0, match.start() - 18):match.start()].lower()
            if "happy-path " in prefix or "architecture " in prefix:
                continue
            violations.append((line_no, line))
    return violations


def test_tc_13_0_context_defines_test_ladder_terms():
    context = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
    for term in REQUIRED_CONTEXT_TERMS:
        assert f"**{term}**" in context


def test_tc_13_0_happy_path_spine_is_qualified_in_prose():
    failures = {
        str(path.relative_to(ROOT)): bare_spine_violations(path)
        for path in DOCS
        if bare_spine_violations(path)
    }
    assert failures == {}


def test_tc_13_0_document_types_has_extended_tmr_row():
    doc = (ROOT / "skills/adversarial-spec/reference/document-types.md").read_text(
        encoding="utf-8"
    )
    for token in (
        "tests-pseudo.md",
        "extended TMR row",
        "tmr_uid",
        "live_or_induced",
        "run_evidence",
        "tmr-registry.json",
    ):
        assert token in doc


def test_tc_13_0_adr_records_tmr_liveness_and_two_spec_split():
    adr = (ROOT / "docs/adr/0002-test-ladder-tmr-liveness-scope-split.md").read_text(
        encoding="utf-8"
    )
    for token in REQUIRED_ADR_TOKENS:
        assert token in adr
