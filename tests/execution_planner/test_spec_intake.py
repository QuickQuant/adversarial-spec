"""
Test specifications for FR-1: Spec Intake

The Spec Intake module accepts finalized PRD, technical specification, or debug
investigation documents and extracts structured data for downstream processing.
"""

import pytest
from pathlib import Path

# These imports will fail until implementation exists
from execution_planner.spec_intake import SpecIntake, SpecDocument, SpecIntakeError


# Test fixtures
SAMPLE_PRD = """# My Test PRD

## Executive Summary

This is a test PRD for validating the spec intake module.

## Problem Statement

We need to test parsing.

## User Stories

### Scope Analysis
- **US-1**: As a user, I want feature A so that benefit X.
- **US-2**: As a user, I want feature B so that benefit Y.

## Functional Requirements

### FR-1: First Requirement
- Does thing one
- Does thing two

### FR-2: Second Requirement
- Does another thing

## Non-Functional Requirements

### NFR-1: Performance
- Should be fast

## Risks and Mitigations

### R-1: Some Risk (HIGH)
**Risk**: Something bad might happen.
**Mitigations**: Do something to prevent it.

## Decisions

1. **Decision one**: We chose A over B.
2. **Decision two**: We chose X over Y.

## Dependencies

### Required
- Python 3.10+
- Some library

### Optional
- Optional thing
"""

EMPTY_SPEC = ""
WHITESPACE_SPEC = "   \n\n   \t   \n"
UNICODE_SPEC = "# PRD: Ü니코드 テスト\n\nContent with émojis 🎉 and symbols ™®©"


class TestSpecIntakeParsing:
    """FR-1: Core parsing functionality."""

    def test_parses_prd_title(self):
        """Should extract document title from first H1 header."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert result.title == "My Test PRD"

    def test_parses_executive_summary(self):
        """Should extract executive summary section."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert result.executive_summary is not None
        assert "test PRD" in result.executive_summary

    def test_parses_user_stories(self):
        """Should extract all user stories with IDs (US-1, US-2, etc.)."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert len(result.user_stories) == 2
        assert result.user_stories[0].id == "US-1"
        assert result.user_stories[1].id == "US-2"

    def test_parses_functional_requirements(self):
        """Should extract all FRs with IDs and full content including sub-bullets."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert len(result.functional_requirements) == 2
        assert result.functional_requirements[0].id == "FR-1"
        assert "thing one" in result.functional_requirements[0].content

    def test_parses_non_functional_requirements(self):
        """Should extract all NFRs with IDs."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert len(result.non_functional_requirements) >= 1
        assert result.non_functional_requirements[0].id == "NFR-1"

    def test_parses_risks_and_mitigations(self):
        """Should extract risks with severity levels and mitigations."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert len(result.risks) >= 1
        assert result.risks[0].id == "R-1"
        assert result.risks[0].severity == "HIGH"
        assert result.risks[0].mitigation is not None

    def test_parses_decisions(self):
        """Should extract numbered decisions."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert len(result.decisions) == 2
        assert "Decision one" in result.decisions[0].title

    def test_parses_dependencies(self):
        """Should extract required and optional dependencies."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert "Python 3.10+" in result.dependencies.required
        assert len(result.dependencies.optional) >= 1


class TestSpecIntakeEdgeCases:
    """FR-1: Edge case handling."""

    def test_empty_spec_returns_error(self):
        """Empty file should return structured error, not crash."""
        with pytest.raises(SpecIntakeError) as exc_info:
            SpecIntake.parse(EMPTY_SPEC)
        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_only_spec_returns_error(self):
        """Whitespace-only file should return structured error."""
        with pytest.raises(SpecIntakeError) as exc_info:
            SpecIntake.parse(WHITESPACE_SPEC)
        assert "empty" in str(exc_info.value).lower()

    def test_missing_sections_noted_not_failed(self):
        """Missing optional sections should be noted but not fail parsing."""
        minimal_spec = "# Minimal PRD\n\nJust a title and some content."
        result = SpecIntake.parse(minimal_spec)
        assert result.title == "Minimal PRD"
        assert len(result.warnings) > 0  # Should note missing sections

    def test_unicode_content_preserved(self):
        """Unicode characters in spec should be preserved correctly."""
        result = SpecIntake.parse(UNICODE_SPEC)
        assert "Ü니코드" in result.title
        assert "🎉" in result.raw_content


class TestSpecIntakeOutput:
    """FR-1: Output structure validation."""

    def test_returns_spec_document_object(self):
        """Should return a SpecDocument dataclass/model."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert isinstance(result, SpecDocument)

    def test_spec_document_is_serializable(self):
        """SpecDocument should be JSON serializable for persistence."""
        import json
        result = SpecIntake.parse(SAMPLE_PRD)
        json_str = result.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["title"] == "My Test PRD"

    def test_spec_document_includes_metadata(self):
        """Should include source file path, parse timestamp, hash."""
        result = SpecIntake.parse(SAMPLE_PRD)
        assert result.parsed_at is not None
        assert result.content_hash is not None


class TestSpecIntakeRealWorld:
    """FR-1: Integration with real spec files."""

    def test_parses_execution_planner_prd(self):
        """Should successfully parse the execution planner PRD (spec-output.md)."""
        spec_path = Path(__file__).parent.parent.parent / "spec-output.md"
        if spec_path.exists():
            result = SpecIntake.parse_file(spec_path)
            assert result.title == "PRD: Execution Planning System"
            assert len(result.functional_requirements) >= 10

    def test_parse_file_handles_missing_file(self):
        """Should raise clear error for missing file."""
        with pytest.raises(SpecIntakeError) as exc_info:
            SpecIntake.parse_file(Path("/nonexistent/file.md"))
        assert "not found" in str(exc_info.value).lower()
