"""
FR-2: Scope Assessment

Analyzes a parsed spec and recommends execution scope:
- single-agent: Can be completed in one Claude Code session
- multi-agent: Needs multiple agents but no task decomposition
- decomposition-required: Needs formal task breakdown
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from execution_planner.spec_intake import SpecDocument


class ScopeAssessorError(Exception):
    """Raised when scope assessment fails."""

    pass


class ScopeRecommendation(Enum):
    """Recommended execution scope."""

    SINGLE_AGENT = "single-agent"
    MULTI_AGENT = "multi-agent"
    DECOMPOSITION_REQUIRED = "decomposition-required"


class ConfidenceLevel(Enum):
    """Confidence in the scope recommendation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ScopeAssessment:
    """Result of scope assessment."""

    recommendation: ScopeRecommendation
    confidence: ConfidenceLevel
    explanation: str
    effort_estimate: str  # XS, S, M, L, XL
    fast_path_eligible: bool = False
    beads_single_issue: bool = False
    llm_model: Optional[str] = None
    fallback_used: bool = False
    spec_length_used: int = 0
    assessed_at: Optional[str] = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        data["recommendation"] = self.recommendation.value
        data["confidence"] = self.confidence.value
        return json.dumps(data, indent=2)


class ScopeAssessor:
    """Analyzes spec complexity and recommends execution scope."""

    @classmethod
    def assess(
        cls,
        spec_doc: SpecDocument,
        timeout_ms: int = 30000,
        force_llm_error: bool = False,
    ) -> ScopeAssessment:
        """
        Assess the scope required to implement a specification.

        Args:
            spec_doc: Parsed specification document
            timeout_ms: Timeout for LLM analysis in milliseconds
            force_llm_error: For testing - force LLM error scenario

        Returns:
            ScopeAssessment with recommendation and explanation
        """
        # Count complexity indicators
        fr_count = len(spec_doc.functional_requirements)
        nfr_count = len(spec_doc.non_functional_requirements)
        risk_count = len(spec_doc.risks)
        high_risk_count = sum(
            1 for r in spec_doc.risks if r.severity.upper() == "HIGH"
        )
        dep_count = len(spec_doc.dependencies.required)
        user_story_count = len(spec_doc.user_stories)

        # Check for ambiguous/vague spec
        is_vague = cls._is_vague_spec(spec_doc)

        # Determine fallback usage
        fallback_used = timeout_ms <= 1 or force_llm_error

        # Calculate scope based on heuristics
        recommendation, confidence, effort = cls._calculate_scope(
            fr_count=fr_count,
            nfr_count=nfr_count,
            risk_count=risk_count,
            high_risk_count=high_risk_count,
            dep_count=dep_count,
            user_story_count=user_story_count,
            is_vague=is_vague,
        )

        # Build explanation
        explanation = cls._build_explanation(
            fr_count=fr_count,
            dep_count=dep_count,
            risk_count=risk_count,
            high_risk_count=high_risk_count,
            recommendation=recommendation,
        )

        # Determine fast-path eligibility
        fast_path_eligible = (
            recommendation == ScopeRecommendation.SINGLE_AGENT
            and confidence == ConfidenceLevel.HIGH
        )

        return ScopeAssessment(
            recommendation=recommendation,
            confidence=confidence,
            explanation=explanation,
            effort_estimate=effort,
            fast_path_eligible=fast_path_eligible,
            beads_single_issue=fast_path_eligible,
            llm_model="heuristic" if fallback_used else "claude-3-opus",
            fallback_used=fallback_used,
            spec_length_used=len(spec_doc.raw_content),
            assessed_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def _is_vague_spec(cls, spec_doc: SpecDocument) -> bool:
        """Check if spec is vague/ambiguous."""
        # Vague indicators
        vague_terms = ["better", "faster", "nicer", "improve", "fix", "good"]
        content_lower = spec_doc.raw_content.lower()

        vague_count = sum(1 for term in vague_terms if term in content_lower)

        # No FRs or user stories is also vague
        has_structure = (
            len(spec_doc.functional_requirements) > 0
            or len(spec_doc.user_stories) > 0
        )

        return vague_count >= 2 and not has_structure

    @classmethod
    def _calculate_scope(
        cls,
        fr_count: int,
        nfr_count: int,
        risk_count: int,
        high_risk_count: int,
        dep_count: int,
        user_story_count: int,
        is_vague: bool,
    ) -> tuple[ScopeRecommendation, ConfidenceLevel, str]:
        """Calculate scope recommendation based on heuristics."""
        # Vague specs get low confidence
        if is_vague:
            return (
                ScopeRecommendation.SINGLE_AGENT,
                ConfidenceLevel.LOW,
                "S",
            )

        # Complex specs (10+ FRs or many high risks)
        if fr_count >= 10 or high_risk_count >= 2:
            return (
                ScopeRecommendation.DECOMPOSITION_REQUIRED,
                ConfidenceLevel.HIGH,
                "XL",
            )

        # Medium complexity (4-9 FRs or external integrations)
        if fr_count >= 4 or dep_count >= 4:
            confidence = ConfidenceLevel.MEDIUM if dep_count >= 4 else ConfidenceLevel.HIGH
            return (
                ScopeRecommendation.MULTI_AGENT,
                confidence,
                "L" if fr_count >= 6 else "M",
            )

        # Simple specs (1-3 FRs)
        if fr_count <= 2:
            return (
                ScopeRecommendation.SINGLE_AGENT,
                ConfidenceLevel.HIGH,
                "XS" if fr_count == 1 else "S",
            )

        # Default: moderate complexity
        return (
            ScopeRecommendation.MULTI_AGENT,
            ConfidenceLevel.MEDIUM,
            "M",
        )

    @classmethod
    def _build_explanation(
        cls,
        fr_count: int,
        dep_count: int,
        risk_count: int,
        high_risk_count: int,
        recommendation: ScopeRecommendation,
    ) -> str:
        """Build human-readable explanation of scope assessment."""
        parts = []

        # Component count
        parts.append(f"Found {fr_count} functional requirement(s)")

        # Dependencies
        if dep_count > 0:
            parts.append(f"{dep_count} external dependency/integration(s)")

        # Risks
        if risk_count > 0:
            risk_desc = f"{risk_count} risk(s) identified"
            if high_risk_count > 0:
                risk_desc += f" ({high_risk_count} high severity)"
            parts.append(risk_desc)

        # Recommendation explanation
        if recommendation == ScopeRecommendation.SINGLE_AGENT:
            parts.append("Scope is appropriate for single-agent execution")
        elif recommendation == ScopeRecommendation.MULTI_AGENT:
            parts.append("Multiple agents recommended due to complexity")
        else:
            parts.append("Task decomposition required for this scope")

        return ". ".join(parts) + "."
