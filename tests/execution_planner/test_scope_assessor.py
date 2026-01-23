"""
Test specifications for FR-2: Scope Assessment

The Scope Assessor analyzes a parsed spec and recommends execution scope:
- single-agent: Can be completed in one Claude Code session
- multi-agent: Needs multiple agents but no task decomposition
- decomposition-required: Needs formal task breakdown

Acceptance Criteria:
- Returns one of three scope recommendations
- Includes confidence level (low/medium/high)
- Explains main drivers: component count, integration points, risk factors, effort
- Fast-path: single-agent + high confidence allows skipping decomposition
- Uses LLM for analysis (Claude Code or configured model)

Edge Cases:
- Spec with single FR → likely single-agent
- Spec with 10+ FRs → likely decomposition-required
- Spec with many external integrations → increases scope
- Ambiguous specs → low confidence
"""

import pytest
import json

# These imports will fail until implementation exists
from execution_planner.scope_assessor import (
    ScopeAssessor,
    ScopeAssessment,
    ScopeRecommendation,
    ConfidenceLevel,
    ScopeAssessorError,
)
from execution_planner.spec_intake import SpecIntake


# Test fixtures - specs of varying complexity
SIMPLE_SPEC = """# Simple Feature

## Executive Summary
Add a button that logs "clicked" to console.

## User Stories
- **US-1**: As a user, I want to click a button so that I see a log message.

## Functional Requirements

### FR-1: Button Component
- Add a button labeled "Click Me"
- On click, log "clicked" to console

## Dependencies

### Required
- React
"""

MEDIUM_SPEC = """# Medium Feature

## Executive Summary
Add user authentication with login/logout.

## User Stories
- **US-1**: As a user, I want to log in so that I can access protected features.
- **US-2**: As a user, I want to log out so that my session ends.
- **US-3**: As a user, I want to see my profile so that I know I'm logged in.

## Functional Requirements

### FR-1: Login Form
- Email and password inputs
- Validation of inputs
- Submit to auth endpoint

### FR-2: Auth State Management
- Store auth token
- Provide auth context to app

### FR-3: Logout
- Clear auth token
- Redirect to login

### FR-4: Protected Routes
- Redirect unauthenticated users

## Dependencies

### Required
- React
- Auth library (e.g., next-auth)

## Risks and Mitigations

### R-1: Token Security (MEDIUM)
**Risk**: Token could be stolen from storage.
**Mitigations**: Use httpOnly cookies.
"""

COMPLEX_SPEC = """# Complex Feature

## Executive Summary
Build a real-time collaborative document editor with versioning, permissions, and export.

## User Stories
- **US-1**: As a user, I want to edit documents collaboratively.
- **US-2**: As a user, I want to see who else is editing.
- **US-3**: As a user, I want to see version history.
- **US-4**: As a user, I want to restore old versions.
- **US-5**: As a user, I want to control who can view/edit.
- **US-6**: As a user, I want to export to PDF.
- **US-7**: As a user, I want to export to Word.

## Functional Requirements

### FR-1: Document Editor Core
- Rich text editing
- Real-time sync

### FR-2: Presence System
- Show active cursors
- Show who is online

### FR-3: Operational Transform
- Conflict resolution
- Merge concurrent edits

### FR-4: Version Control
- Save versions on demand
- Auto-save versions periodically

### FR-5: Version History UI
- List all versions
- Preview versions
- Restore versions

### FR-6: Permissions System
- Owner, Editor, Viewer roles
- Invite via email
- Revoke access

### FR-7: Export to PDF
- Render document as PDF
- Preserve formatting

### FR-8: Export to Word
- Convert to .docx format
- Preserve formatting

### FR-9: Offline Support
- Queue changes when offline
- Sync when back online

### FR-10: Search
- Full-text search within documents
- Search across all documents

### FR-11: Comments
- Inline comments
- Comment threads

## Dependencies

### Required
- React
- WebSocket server
- OT library (Yjs or similar)
- PDF generation library
- DOCX generation library
- PostgreSQL

## Risks and Mitigations

### R-1: Data Conflicts (HIGH)
**Risk**: Concurrent edits could cause data loss.
**Mitigations**: Use proven OT/CRDT library.

### R-2: Performance (HIGH)
**Risk**: Real-time sync could be slow with large documents.
**Mitigations**: Implement chunked sync, lazy loading.

### R-3: Security (HIGH)
**Risk**: Unauthorized access to documents.
**Mitigations**: Row-level security, access tokens.
"""

AMBIGUOUS_SPEC = """# Vague Feature

## Summary
Make it better and faster.

## Requirements
- Improve performance
- Fix bugs
- Make it nicer
"""


class TestScopeRecommendation:
    """FR-2: Core scope recommendation functionality."""

    def test_returns_valid_scope_recommendation(self):
        """Should return one of: single-agent, multi-agent, decomposition-required."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.recommendation in [
            ScopeRecommendation.SINGLE_AGENT,
            ScopeRecommendation.MULTI_AGENT,
            ScopeRecommendation.DECOMPOSITION_REQUIRED,
        ]

    def test_returns_confidence_level(self):
        """Should include confidence: low, medium, or high."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.confidence in [
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        ]

    def test_explains_component_count(self):
        """Explanation should mention number of components/FRs."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.explanation is not None
        # Explanation should reference component/FR count
        assert "fr" in result.explanation.lower() or "component" in result.explanation.lower() or "requirement" in result.explanation.lower()

    def test_explains_integration_points(self):
        """Explanation should mention external integrations."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        # Should mention dependencies/integrations
        assert "integrat" in result.explanation.lower() or "dependenc" in result.explanation.lower()

    def test_explains_risk_factors(self):
        """Explanation should mention identified risks."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC)  # Has HIGH risks
        result = ScopeAssessor.assess(spec_doc)
        assert "risk" in result.explanation.lower()

    def test_explains_estimated_effort(self):
        """Explanation should include effort estimate (XS/S/M/L/XL)."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.effort_estimate in ["XS", "S", "M", "L", "XL"]


class TestScopeHeuristics:
    """FR-2: Scope determination logic."""

    def test_single_fr_recommends_single_agent(self):
        """Spec with 1-2 simple FRs should recommend single-agent."""
        spec_doc = SpecIntake.parse(SIMPLE_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.recommendation == ScopeRecommendation.SINGLE_AGENT

    def test_many_frs_recommends_decomposition(self):
        """Spec with 10+ FRs should recommend decomposition-required."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC)  # Has 11 FRs
        result = ScopeAssessor.assess(spec_doc)
        assert result.recommendation == ScopeRecommendation.DECOMPOSITION_REQUIRED

    def test_external_integrations_increase_scope(self):
        """Multiple external dependencies should push toward multi-agent."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC)  # Has 6 external deps
        result = ScopeAssessor.assess(spec_doc)
        # Should not be single-agent due to integration complexity
        assert result.recommendation != ScopeRecommendation.SINGLE_AGENT

    def test_high_risk_items_increase_scope(self):
        """High-risk items should push toward more structured execution."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC)  # Has HIGH risks
        result = ScopeAssessor.assess(spec_doc)
        # High risk should push toward decomposition
        assert result.recommendation == ScopeRecommendation.DECOMPOSITION_REQUIRED

    def test_simple_spec_high_confidence(self):
        """Clear simple specs should have high confidence."""
        spec_doc = SpecIntake.parse(SIMPLE_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.confidence == ConfidenceLevel.HIGH

    def test_ambiguous_spec_low_confidence(self):
        """Specs with unclear requirements should have low confidence."""
        spec_doc = SpecIntake.parse(AMBIGUOUS_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.confidence == ConfidenceLevel.LOW


class TestFastPath:
    """FR-2: Fast-path for simple specs."""

    def test_fast_path_eligible_when_single_agent_high_confidence(self):
        """single-agent + high confidence should flag fast_path_eligible=True."""
        spec_doc = SpecIntake.parse(SIMPLE_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.recommendation == ScopeRecommendation.SINGLE_AGENT
        assert result.confidence == ConfidenceLevel.HIGH
        assert result.fast_path_eligible is True

    def test_fast_path_not_eligible_when_low_confidence(self):
        """single-agent + low confidence should NOT be fast-path eligible."""
        spec_doc = SpecIntake.parse(AMBIGUOUS_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        # Even if single-agent, low confidence disqualifies fast-path
        if result.recommendation == ScopeRecommendation.SINGLE_AGENT:
            assert result.fast_path_eligible is False

    def test_fast_path_not_eligible_for_multi_agent(self):
        """multi-agent should never be fast-path eligible."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        if result.recommendation != ScopeRecommendation.SINGLE_AGENT:
            assert result.fast_path_eligible is False

    def test_fast_path_creates_single_beads_issue(self):
        """Fast-path should still create one beads issue for tracking."""
        spec_doc = SpecIntake.parse(SIMPLE_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.fast_path_eligible is True
        # Should include note about beads issue creation
        assert result.beads_single_issue is True


class TestScopeAssessorLLM:
    """FR-2: LLM integration for scope assessment."""

    def test_uses_configured_llm(self):
        """Should use Claude Code or configured LLM for analysis."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        # Mock/verify LLM was called
        result = ScopeAssessor.assess(spec_doc)
        assert result.llm_model is not None  # Should report which model was used

    def test_handles_llm_timeout(self):
        """Should handle LLM timeout gracefully with fallback."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        # Force timeout scenario - should fall back to heuristic-only assessment
        result = ScopeAssessor.assess(spec_doc, timeout_ms=1)
        assert result is not None  # Should not crash
        assert result.fallback_used is True

    def test_handles_llm_error(self):
        """Should handle LLM errors with sensible default."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        # Force error scenario
        result = ScopeAssessor.assess(spec_doc, force_llm_error=True)
        assert result is not None
        assert result.fallback_used is True

    def test_prompt_includes_full_spec(self):
        """LLM prompt should include the full spec (no trimming)."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC)
        # The assessor should not trim the spec
        result = ScopeAssessor.assess(spec_doc)
        # Verify the spec was not truncated in the assessment
        assert result.spec_length_used == len(COMPLEX_SPEC)


class TestScopeAssessorOutput:
    """FR-2: Output structure validation."""

    def test_returns_scope_assessment_object(self):
        """Should return a ScopeAssessment dataclass/model."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert isinstance(result, ScopeAssessment)

    def test_scope_assessment_is_serializable(self):
        """ScopeAssessment should be JSON serializable."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        json_str = result.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert "recommendation" in parsed
        assert "confidence" in parsed

    def test_assessment_includes_timestamp(self):
        """Should include when assessment was made."""
        spec_doc = SpecIntake.parse(MEDIUM_SPEC)
        result = ScopeAssessor.assess(spec_doc)
        assert result.assessed_at is not None
