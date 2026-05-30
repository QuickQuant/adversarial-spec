"""Tests for the grouped markdown export (Layer A.3 + A.4).

Layer A.3: render concerns grouped by (adversary, source_model) as markdown.
Layer A.4: when every concern shares one severity, drop the per-row column
and record the constant value in the header.
"""

from gauntlet.core_types import Concern
from gauntlet.reporting import render_grouped_markdown_export


def _make(adversary: str, model: str, text: str, severity: str = "medium") -> Concern:
    return Concern(adversary=adversary, text=text, severity=severity, source_model=model)


def test_empty_concern_list_renders_safely():
    out = render_grouped_markdown_export([])
    assert out.startswith("# Gauntlet Concerns (grouped)")
    assert "(no concerns)" in out


def test_grouping_by_adversary_and_model():
    concerns = [
        _make("architect", "codex/gpt-5.5", "Concern A1"),
        _make("architect", "codex/gpt-5.5", "Concern A2"),
        _make("architect", "gemini-cli/gemini-3-flash-preview", "Concern B1"),
        _make("paranoid_security", "codex/gpt-5.5", "Concern C1"),
    ]
    out = render_grouped_markdown_export(concerns, spec_hash="abc12345")

    # Three section headers, one per (adversary, model) pair.
    assert "## architect / codex/gpt-5.5  (2 concerns)" in out
    assert "## architect / gemini-cli/gemini-3-flash-preview  (1 concerns)" in out
    assert "## paranoid_security / codex/gpt-5.5  (1 concerns)" in out

    # Header line includes the spec hash and counts.
    assert "Spec: abc12345" in out
    assert "Total: 4 concerns across 2 adversaries × 2 models" in out

    # Concerns are numbered 1..N within each group.
    arch_section_start = out.index("## architect / codex/gpt-5.5")
    arch_section_end = out.index("## architect / gemini-cli")
    arch_section = out[arch_section_start:arch_section_end]
    assert "1." in arch_section and "2." in arch_section
    # Numbering resets in the next group.
    paranoid_section = out[out.index("## paranoid_security"):]
    assert paranoid_section.count("1.") >= 1


def test_constant_severity_suppresses_column():
    """Layer A.4: every concern is medium → drop [M] from each line."""
    concerns = [
        _make("architect", "codex/gpt-5.5", "Concern A", severity="medium"),
        _make("architect", "codex/gpt-5.5", "Concern B", severity="medium"),
    ]
    out = render_grouped_markdown_export(concerns)

    assert "All concerns share severity=medium; column suppressed." in out
    # No [M] markers on the rows.
    assert "[M]" not in out
    assert "[H]" not in out
    assert "[L]" not in out
    assert "1. Concern A" in out
    assert "2. Concern B" in out


def test_varied_severity_emits_per_row_tag():
    """When severities vary, every row gets its [H]/[M]/[L] tag."""
    concerns = [
        _make("architect", "codex/gpt-5.5", "High concern", severity="high"),
        _make("architect", "codex/gpt-5.5", "Medium concern", severity="medium"),
        _make("architect", "codex/gpt-5.5", "Low concern", severity="low"),
    ]
    out = render_grouped_markdown_export(concerns)

    # Header note about constant severity should NOT appear.
    assert "column suppressed" not in out
    # Every row tagged.
    assert "1. [H] High concern" in out
    assert "2. [M] Medium concern" in out
    assert "3. [L] Low concern" in out


def test_unknown_severity_falls_back_to_bracketed_label():
    concerns = [_make("architect", "codex/gpt-5.5", "Weird", severity="unknown")]
    # Add a second concern with a different severity so the column is shown.
    concerns.append(_make("architect", "codex/gpt-5.5", "Normal", severity="medium"))
    out = render_grouped_markdown_export(concerns)
    assert "[unknown]" in out
    assert "[M]" in out


def test_missing_source_model_is_labeled():
    concerns = [Concern(adversary="architect", text="No model", source_model="")]
    out = render_grouped_markdown_export(concerns)
    assert "## architect / unknown-model  (1 concerns)" in out


def test_generated_at_appears_in_header_when_provided():
    out = render_grouped_markdown_export(
        [_make("architect", "codex/gpt-5.5", "Concern")],
        generated_at="2026-05-04T17:50:00Z",
        spec_hash="9ee43569",
    )
    assert "Generated: 2026-05-04T17:50:00Z" in out
    assert "Spec: 9ee43569" in out


def test_output_is_a_single_string():
    """Sanity: the function returns one string suitable for direct write to disk."""
    out = render_grouped_markdown_export(
        [_make("architect", "codex/gpt-5.5", "Concern")]
    )
    assert isinstance(out, str)
    assert out.endswith("\n") or "\n" in out
