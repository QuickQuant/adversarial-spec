"""
FR-1: Spec Intake

Parses finalized PRD, technical specification, or debug investigation documents
and extracts structured data for downstream processing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class SpecIntakeError(Exception):
    """Raised when spec parsing fails."""

    pass


@dataclass
class UserStory:
    """A user story from the spec (US-1, US-2, etc.)."""

    id: str
    content: str


@dataclass
class FunctionalRequirement:
    """A functional requirement from the spec (FR-1, FR-2, etc.)."""

    id: str
    title: str
    content: str


@dataclass
class NonFunctionalRequirement:
    """A non-functional requirement from the spec (NFR-1, NFR-2, etc.)."""

    id: str
    title: str
    content: str


@dataclass
class Risk:
    """A risk item from the spec (R-1, R-2, etc.)."""

    id: str
    title: str
    severity: str  # HIGH, MEDIUM, LOW
    description: str
    mitigation: Optional[str] = None


@dataclass
class Decision:
    """A decision recorded in the spec."""

    title: str
    content: str


@dataclass
class Dependencies:
    """Dependencies section from the spec."""

    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)


@dataclass
class SpecDocument:
    """Parsed specification document with all extracted components."""

    title: str
    raw_content: str
    executive_summary: Optional[str] = None
    problem_statement: Optional[str] = None
    user_stories: list[UserStory] = field(default_factory=list)
    functional_requirements: list[FunctionalRequirement] = field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirement] = field(
        default_factory=list
    )
    risks: list[Risk] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    dependencies: Dependencies = field(default_factory=Dependencies)
    warnings: list[str] = field(default_factory=list)
    parsed_at: Optional[str] = None
    content_hash: Optional[str] = None
    source_path: Optional[str] = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        return json.dumps(data, indent=2, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> SpecDocument:
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        # Reconstruct nested dataclasses
        data["user_stories"] = [UserStory(**us) for us in data.get("user_stories", [])]
        data["functional_requirements"] = [
            FunctionalRequirement(**fr) for fr in data.get("functional_requirements", [])
        ]
        data["non_functional_requirements"] = [
            NonFunctionalRequirement(**nfr)
            for nfr in data.get("non_functional_requirements", [])
        ]
        data["risks"] = [Risk(**r) for r in data.get("risks", [])]
        data["decisions"] = [Decision(**d) for d in data.get("decisions", [])]
        data["dependencies"] = Dependencies(**data.get("dependencies", {}))
        return cls(**data)


class SpecIntake:
    """Parser for PRD and specification documents."""

    @classmethod
    def parse(cls, content: str) -> SpecDocument:
        """
        Parse a markdown specification document.

        Args:
            content: Raw markdown content of the spec

        Returns:
            SpecDocument with extracted components

        Raises:
            SpecIntakeError: If content is empty or unparseable
        """
        # Validate content
        if not content or not content.strip():
            raise SpecIntakeError("Specification content is empty")

        # Extract title from first H1
        title = cls._extract_title(content)
        if not title:
            title = "Untitled Specification"

        # Create document
        doc = SpecDocument(
            title=title,
            raw_content=content,
            parsed_at=datetime.now(timezone.utc).isoformat(),
            content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
        )

        # Extract sections
        doc.executive_summary = cls._extract_section(
            content, ["Executive Summary", "Summary", "Overview"]
        )
        doc.problem_statement = cls._extract_section(
            content, ["Problem Statement", "Problem", "Background"]
        )
        doc.user_stories = cls._extract_user_stories(content)
        doc.functional_requirements = cls._extract_functional_requirements(content)
        doc.non_functional_requirements = cls._extract_non_functional_requirements(
            content
        )
        doc.risks = cls._extract_risks(content)
        doc.decisions = cls._extract_decisions(content)
        doc.dependencies = cls._extract_dependencies(content)

        # Add warnings for missing sections
        doc.warnings = cls._check_missing_sections(doc)

        return doc

    @classmethod
    def parse_file(cls, path: Path) -> SpecDocument:
        """
        Parse a specification file.

        Args:
            path: Path to the markdown file

        Returns:
            SpecDocument with extracted components

        Raises:
            SpecIntakeError: If file not found or unparseable
        """
        if not path.exists():
            raise SpecIntakeError(f"Specification file not found: {path}")

        content = path.read_text(encoding="utf-8")
        doc = cls.parse(content)
        doc.source_path = str(path)
        return doc

    @classmethod
    def _extract_title(cls, content: str) -> Optional[str]:
        """Extract title from first H1 header."""
        # Match # Title (captures entire title including any prefix like "PRD:")
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def _extract_section(
        cls, content: str, section_names: list[str]
    ) -> Optional[str]:
        """Extract content of a named section."""
        for name in section_names:
            # Match ## Section Name and capture until next H2 (## not ###) or end
            pattern = rf"##\s+{re.escape(name)}\s*\n(.*?)(?=\n##[^#]|\Z)"
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def _extract_user_stories(cls, content: str) -> list[UserStory]:
        """Extract user stories (US-1, US-2, etc.)."""
        stories = []
        # Match patterns like:
        # - **US-1**: As a user...
        # * **US-1**: As a user...
        pattern = r"[-*]\s+\*\*?(US-\d+)\*?\*?:\s*(.+?)(?=\n[-*]|\n\n|\n##|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            stories.append(
                UserStory(id=match.group(1), content=match.group(2).strip())
            )
        return stories

    @classmethod
    def _extract_functional_requirements(
        cls, content: str
    ) -> list[FunctionalRequirement]:
        """Extract functional requirements (FR-1, FR-2, etc.)."""
        requirements = []
        # Match patterns like:
        # ### FR-1: Title
        # - content
        pattern = r"###\s+(FR-\d+):\s*(.+?)\n(.*?)(?=\n###|\n##[^#]|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            requirements.append(
                FunctionalRequirement(
                    id=match.group(1),
                    title=match.group(2).strip(),
                    content=match.group(3).strip(),
                )
            )
        return requirements

    @classmethod
    def _extract_non_functional_requirements(
        cls, content: str
    ) -> list[NonFunctionalRequirement]:
        """Extract non-functional requirements (NFR-1, NFR-2, etc.)."""
        requirements = []
        # Match patterns like:
        # ### NFR-1: Title
        # - content
        pattern = r"###\s+(NFR-\d+):\s*(.+?)\n(.*?)(?=\n###|\n##[^#]|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            requirements.append(
                NonFunctionalRequirement(
                    id=match.group(1),
                    title=match.group(2).strip(),
                    content=match.group(3).strip(),
                )
            )
        return requirements

    @classmethod
    def _extract_risks(cls, content: str) -> list[Risk]:
        """Extract risks with severity levels (R-1, R-2, etc.)."""
        risks = []
        # Match patterns like:
        # ### R-1: Some Risk (HIGH)
        # **Risk**: Description
        # **Mitigations**: How to prevent
        pattern = r"###\s+(R-\d+):\s*(.+?)\s*\((\w+)\)\s*\n(.*?)(?=\n###|\n##[^#]|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            risk_content = match.group(4)
            # Extract description and mitigation
            desc_match = re.search(
                r"\*\*Risk\*\*:\s*(.+?)(?=\n\*\*|\Z)", risk_content, re.DOTALL
            )
            mit_match = re.search(
                r"\*\*Mitigations?\*\*:\s*(.+?)(?=\n\*\*|\Z)", risk_content, re.DOTALL
            )

            risks.append(
                Risk(
                    id=match.group(1),
                    title=match.group(2).strip(),
                    severity=match.group(3).upper(),
                    description=desc_match.group(1).strip() if desc_match else "",
                    mitigation=mit_match.group(1).strip() if mit_match else None,
                )
            )
        return risks

    @classmethod
    def _extract_decisions(cls, content: str) -> list[Decision]:
        """Extract numbered decisions."""
        decisions = []
        # Match patterns like:
        # 1. **Decision title**: content
        pattern = r"\d+\.\s+\*\*(.+?)\*\*:\s*(.+?)(?=\n\d+\.|\n\n|\n##|\Z)"
        # Find the Decisions section first
        decisions_section = cls._extract_section(content, ["Decisions", "Key Decisions"])
        if decisions_section:
            for match in re.finditer(pattern, decisions_section, re.DOTALL):
                decisions.append(
                    Decision(title=match.group(1).strip(), content=match.group(2).strip())
                )
        return decisions

    @classmethod
    def _extract_dependencies(cls, content: str) -> Dependencies:
        """Extract required and optional dependencies."""
        deps = Dependencies()

        # Find Dependencies section
        deps_section = cls._extract_section(content, ["Dependencies"])
        if not deps_section:
            return deps

        # Extract Required subsection
        req_match = re.search(
            r"###\s+Required\s*\n(.*?)(?=\n###|\Z)", deps_section, re.DOTALL
        )
        if req_match:
            for line in req_match.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    deps.required.append(line[1:].strip())

        # Extract Optional subsection
        opt_match = re.search(
            r"###\s+Optional\s*\n(.*?)(?=\n###|\Z)", deps_section, re.DOTALL
        )
        if opt_match:
            for line in opt_match.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    deps.optional.append(line[1:].strip())

        return deps

    @classmethod
    def _check_missing_sections(cls, doc: SpecDocument) -> list[str]:
        """Check for missing recommended sections and return warnings."""
        warnings = []

        if not doc.executive_summary:
            warnings.append("Missing Executive Summary section")
        if not doc.user_stories:
            warnings.append("No user stories found (US-N format)")
        if not doc.functional_requirements:
            warnings.append("No functional requirements found (FR-N format)")

        return warnings
