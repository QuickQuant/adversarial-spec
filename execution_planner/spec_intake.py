"""
FR-1: Spec Intake

Parses finalized PRD, technical specification, or debug investigation documents
and extracts structured data for downstream processing.

Supports both PRD format (user stories, FRs, NFRs) and Tech Spec format
(goals, data models, APIs, scheduled functions).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class SpecIntakeError(Exception):
    """Raised when spec parsing fails."""

    pass


class DocType(Enum):
    """Type of specification document."""

    PRD = "prd"
    TECH_SPEC = "tech_spec"
    UNKNOWN = "unknown"


# =============================================================================
# PRD-specific dataclasses
# =============================================================================


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


# =============================================================================
# Tech Spec-specific dataclasses
# =============================================================================


@dataclass
class Goal:
    """A goal or non-goal from a tech spec."""

    description: str
    is_goal: bool = True  # False for non-goals


@dataclass
class DataModel:
    """A data model / schema definition from a tech spec."""

    id: str  # e.g., "4.1", "orders"
    name: str  # e.g., "OrderRecord", "order_queue"
    definition: str  # The TypeScript/code block
    section_ref: str  # e.g., "Section 4.1"
    indexes: list[str] = field(default_factory=list)


@dataclass
class APIEndpoint:
    """An API endpoint definition from a tech spec."""

    id: str  # e.g., "6.1", "orders:placeDma"
    name: str  # e.g., "orders:placeDma"
    request_schema: Optional[str] = None
    response_schema: Optional[str] = None
    description: str = ""
    section_ref: str = ""
    flow_steps: list[str] = field(default_factory=list)


@dataclass
class ScheduledFunction:
    """A scheduled function / cron job from a tech spec."""

    name: str
    frequency: str  # e.g., "30s", "every 60s"
    purpose: str
    section_ref: str = ""


@dataclass
class ErrorCode:
    """An error code definition from a tech spec."""

    code: str  # e.g., "ERR_BALANCE_INSUFFICIENT"
    description: str


@dataclass
class PerformanceSLA:
    """A performance SLA from a tech spec."""

    metric: str
    target: str


@dataclass
class GauntletDecision:
    """A decision from gauntlet review in a tech spec."""

    concern: str
    decision: str


@dataclass
class TechSpecSection:
    """A generic section from a tech spec for reference."""

    number: str  # e.g., "4.3", "8"
    title: str
    content: str
    subsections: list["TechSpecSection"] = field(default_factory=list)


@dataclass
class SpecDocument:
    """Parsed specification document with all extracted components.

    Supports both PRD format and Tech Spec format. The doc_type field indicates
    which format was detected, and the appropriate fields will be populated.
    """

    title: str
    raw_content: str
    doc_type: DocType = DocType.UNKNOWN

    # PRD-specific fields
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

    # Tech Spec-specific fields
    overview: Optional[str] = None
    goals: list[Goal] = field(default_factory=list)
    non_goals: list[Goal] = field(default_factory=list)
    architecture: Optional[str] = None
    data_models: list[DataModel] = field(default_factory=list)
    api_endpoints: list[APIEndpoint] = field(default_factory=list)
    scheduled_functions: list[ScheduledFunction] = field(default_factory=list)
    error_codes: list[ErrorCode] = field(default_factory=list)
    performance_slas: list[PerformanceSLA] = field(default_factory=list)
    gauntlet_decisions: list[GauntletDecision] = field(default_factory=list)
    sections: list[TechSpecSection] = field(default_factory=list)

    # Common fields
    warnings: list[str] = field(default_factory=list)
    parsed_at: Optional[str] = None
    content_hash: Optional[str] = None
    source_path: Optional[str] = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        # Convert DocType enum to string
        data["doc_type"] = self.doc_type.value
        return json.dumps(data, indent=2, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> SpecDocument:
        """Deserialize from JSON string."""
        data = json.loads(json_str)

        # Convert doc_type string to enum
        data["doc_type"] = DocType(data.get("doc_type", "unknown"))

        # Reconstruct PRD dataclasses
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

        # Reconstruct Tech Spec dataclasses
        data["goals"] = [Goal(**g) for g in data.get("goals", [])]
        data["non_goals"] = [Goal(**g) for g in data.get("non_goals", [])]
        data["data_models"] = [DataModel(**dm) for dm in data.get("data_models", [])]
        data["api_endpoints"] = [APIEndpoint(**ep) for ep in data.get("api_endpoints", [])]
        data["scheduled_functions"] = [
            ScheduledFunction(**sf) for sf in data.get("scheduled_functions", [])
        ]
        data["error_codes"] = [ErrorCode(**ec) for ec in data.get("error_codes", [])]
        data["performance_slas"] = [
            PerformanceSLA(**ps) for ps in data.get("performance_slas", [])
        ]
        data["gauntlet_decisions"] = [
            GauntletDecision(**gd) for gd in data.get("gauntlet_decisions", [])
        ]
        data["sections"] = [
            TechSpecSection(**s) for s in data.get("sections", [])
        ]

        return cls(**data)

    def get_section_by_number(self, number: str) -> Optional[TechSpecSection]:
        """Find a section by its number (e.g., '4.3')."""
        for section in self.sections:
            if section.number == number:
                return section
            for subsection in section.subsections:
                if subsection.number == number:
                    return subsection
        return None

    def is_prd(self) -> bool:
        """Check if this is a PRD document."""
        return self.doc_type == DocType.PRD

    def is_tech_spec(self) -> bool:
        """Check if this is a tech spec document."""
        return self.doc_type == DocType.TECH_SPEC


class SpecIntake:
    """Parser for PRD and specification documents.

    Supports both PRD format (user stories, FRs, NFRs) and Tech Spec format
    (goals, data models, APIs, scheduled functions).
    """

    # Indicators for PRD format
    PRD_INDICATORS = [
        r"user\s*stor(?:y|ies)",
        r"FR-\d+",
        r"functional\s*requirements?",
        r"NFR-\d+",
        r"non-functional\s*requirements?",
        r"target\s*users?.*personas?",
        r"success\s*metrics?",
    ]

    # Indicators for Tech Spec format
    TECH_SPEC_INDICATORS = [
        r"##\s*\d+\.\s+",  # Numbered sections like "## 4. Database Schema"
        r"```typescript",
        r"interface\s+\w+\s*\{",
        r"API\s*Design",
        r"Data\s*Model",
        r"Performance\s*SLA",
        r"Scheduled\s*Function",
        r"Goals?\s*(?:and|\/)\s*Non-Goals?",
    ]

    @classmethod
    def parse(cls, content: str) -> SpecDocument:
        """
        Parse a markdown specification document.

        Automatically detects whether this is a PRD or Tech Spec and parses
        accordingly.

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

        # Detect document type
        doc_type = cls._detect_doc_type(content)

        # Create document
        doc = SpecDocument(
            title=title,
            raw_content=content,
            doc_type=doc_type,
            parsed_at=datetime.now(timezone.utc).isoformat(),
            content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
        )

        # Parse based on document type
        if doc_type == DocType.PRD:
            cls._parse_prd(doc, content)
        elif doc_type == DocType.TECH_SPEC:
            cls._parse_tech_spec(doc, content)
        else:
            # Try both and see what we get
            cls._parse_prd(doc, content)
            cls._parse_tech_spec(doc, content)

        # Add warnings for missing sections
        doc.warnings = cls._check_missing_sections(doc)

        return doc

    @classmethod
    def _detect_doc_type(cls, content: str) -> DocType:
        """Detect whether this is a PRD or Tech Spec."""
        content_lower = content.lower()

        prd_score = 0
        for pattern in cls.PRD_INDICATORS:
            if re.search(pattern, content, re.IGNORECASE):
                prd_score += 1

        tech_score = 0
        for pattern in cls.TECH_SPEC_INDICATORS:
            if re.search(pattern, content, re.IGNORECASE):
                tech_score += 1

        # Also check for explicit markers
        if "prd" in content_lower[:500] or "product requirements" in content_lower[:500]:
            prd_score += 2
        if "technical specification" in content_lower[:500] or "tech spec" in content_lower[:500]:
            tech_score += 2

        if prd_score > tech_score:
            return DocType.PRD
        elif tech_score > prd_score:
            return DocType.TECH_SPEC
        else:
            return DocType.UNKNOWN

    @classmethod
    def _parse_prd(cls, doc: SpecDocument, content: str) -> None:
        """Parse PRD-specific sections."""
        doc.executive_summary = cls._extract_section(
            content, ["Executive Summary", "Summary"]
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

    @classmethod
    def _parse_tech_spec(cls, doc: SpecDocument, content: str) -> None:
        """Parse Tech Spec-specific sections."""
        # Try extracting numbered sections first (e.g., "## 1. Overview / Context")
        doc.overview = cls._extract_numbered_section(content, 1)
        if not doc.overview:
            doc.overview = cls._extract_section(
                content, ["Overview", "Overview / Context", "Context"]
            )
        doc.goals, doc.non_goals = cls._extract_goals(content)
        doc.architecture = cls._extract_section(
            content, ["Architecture", "System Architecture"]
        )
        doc.data_models = cls._extract_data_models(content)
        doc.api_endpoints = cls._extract_api_endpoints(content)
        doc.scheduled_functions = cls._extract_scheduled_functions(content)
        doc.error_codes = cls._extract_error_codes(content)
        doc.performance_slas = cls._extract_performance_slas(content)
        doc.gauntlet_decisions = cls._extract_gauntlet_decisions(content)
        doc.sections = cls._extract_all_sections(content)

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
    def _extract_numbered_section(cls, content: str, section_num: int) -> Optional[str]:
        """Extract content of a numbered section (e.g., ## 1. Title)."""
        pattern = rf"##\s+{section_num}\.?\s+[^\n]+\n(.*?)(?=\n##[^#]|\Z)"
        match = re.search(pattern, content, re.DOTALL)
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

        if doc.doc_type == DocType.PRD:
            if not doc.executive_summary:
                warnings.append("Missing Executive Summary section")
            if not doc.user_stories:
                warnings.append("No user stories found (US-N format)")
            if not doc.functional_requirements:
                warnings.append("No functional requirements found (FR-N format)")
        elif doc.doc_type == DocType.TECH_SPEC:
            if not doc.overview:
                warnings.append("Missing Overview section")
            if not doc.goals:
                warnings.append("No goals found")
            if not doc.data_models:
                warnings.append("No data models found")
        else:
            # Unknown type - check for either format
            if not doc.executive_summary and not doc.overview:
                warnings.append("Missing Overview/Executive Summary section")

        return warnings

    # =========================================================================
    # Tech Spec parsing methods
    # =========================================================================

    @classmethod
    def _extract_goals(cls, content: str) -> tuple[list[Goal], list[Goal]]:
        """Extract goals and non-goals from a tech spec."""
        goals = []
        non_goals = []

        # Try numbered section first (e.g., "## 2. Goals and Non-Goals")
        goals_section = cls._extract_numbered_section(content, 2)
        if not goals_section:
            # Fall back to named section
            goals_section = cls._extract_section(
                content, ["Goals and Non-Goals", "Goals / Non-Goals", "Goals"]
            )
        if not goals_section:
            return goals, non_goals

        # Look for ### Goals subsection
        goals_match = re.search(
            r"###\s+Goals?\s*\n(.*?)(?=\n###|\n##|\Z)", goals_section, re.DOTALL
        )
        if goals_match:
            for line in goals_match.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    goals.append(Goal(description=line[1:].strip(), is_goal=True))

        # Look for ### Non-Goals subsection
        non_goals_match = re.search(
            r"###\s+Non-Goals?\s*\n(.*?)(?=\n###|\n##|\Z)", goals_section, re.DOTALL
        )
        if non_goals_match:
            for line in non_goals_match.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    non_goals.append(Goal(description=line[1:].strip(), is_goal=False))

        # If no subsections, treat bullets in the section as goals
        if not goals and not non_goals:
            for line in goals_section.strip().split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    goals.append(Goal(description=line[1:].strip(), is_goal=True))

        return goals, non_goals

    @classmethod
    def _extract_data_models(cls, content: str) -> list[DataModel]:
        """Extract data models / schema definitions from a tech spec."""
        models = []

        # Find sections with numbered subsections like "### 4.1 orders"
        pattern = r"###\s+(\d+\.\d+)\s+(\w+)\s*\n(.*?)(?=\n###|\n##[^#]|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            section_num = match.group(1)
            name = match.group(2)
            section_content = match.group(3)

            # Look for TypeScript interface or code block
            code_match = re.search(
                r"```(?:typescript|ts)?\n(.*?)```", section_content, re.DOTALL
            )
            definition = code_match.group(1).strip() if code_match else ""

            # Look for indexes
            indexes = []
            indexes_match = re.search(
                r"\*\*Indexes?:?\*\*\s*\n```(?:typescript|ts)?\n(.*?)```",
                section_content,
                re.DOTALL,
            )
            if indexes_match:
                for line in indexes_match.group(1).strip().split("\n"):
                    line = line.strip()
                    if line.startswith(".index"):
                        indexes.append(line)

            if definition:
                models.append(
                    DataModel(
                        id=section_num,
                        name=name,
                        definition=definition,
                        section_ref=f"Section {section_num}",
                        indexes=indexes,
                    )
                )

        return models

    @classmethod
    def _extract_api_endpoints(cls, content: str) -> list[APIEndpoint]:
        """Extract API endpoints from a tech spec."""
        endpoints = []

        # Find sections like "### 6.1 orders:placeDma" or similar
        pattern = r"###\s+(\d+\.\d+)\s+(\w+:\w+)\s*\n(.*?)(?=\n###|\n##[^#]|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            section_num = match.group(1)
            name = match.group(2)
            section_content = match.group(3)

            # Look for request/response schemas
            req_match = re.search(
                r"//\s*Request\s*\n(.*?)(?=//\s*Response|\Z)",
                section_content,
                re.DOTALL,
            )
            resp_match = re.search(
                r"//\s*Response\s*\n(.*?)(?=```|\Z)", section_content, re.DOTALL
            )

            # Look for execution flow steps
            flow_steps = []
            flow_match = re.search(
                r"\*\*Execution Flow:?\*\*\s*\n(.*?)(?=\n###|\n##|\Z)",
                section_content,
                re.DOTALL,
            )
            if flow_match:
                for line in flow_match.group(1).strip().split("\n"):
                    line = line.strip()
                    if re.match(r"^\d+\.", line):
                        flow_steps.append(line)

            endpoints.append(
                APIEndpoint(
                    id=section_num,
                    name=name,
                    request_schema=req_match.group(1).strip() if req_match else None,
                    response_schema=resp_match.group(1).strip() if resp_match else None,
                    section_ref=f"Section {section_num}",
                    flow_steps=flow_steps,
                )
            )

        return endpoints

    @classmethod
    def _extract_scheduled_functions(cls, content: str) -> list[ScheduledFunction]:
        """Extract scheduled functions from a tech spec."""
        functions = []

        # Try numbered section first (e.g., "## 13. Scheduled Functions")
        section = None
        for i in range(1, 20):
            test_section = cls._extract_numbered_section(content, i)
            if test_section and "scheduled" in content.lower():
                # Check if this section's title contains "scheduled"
                header_match = re.search(
                    rf"##\s+{i}\.?\s+([^\n]+)", content, re.IGNORECASE
                )
                if header_match and "scheduled" in header_match.group(1).lower():
                    section = test_section
                    break

        if not section:
            section = cls._extract_section(content, ["Scheduled Functions"])
        if not section:
            return functions

        # Look for table rows like "| functionName | 30s | purpose |"
        table_pattern = r"\|\s*`?(\w+)`?\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"
        for match in re.finditer(table_pattern, section):
            name = match.group(1).strip()
            frequency = match.group(2).strip()
            purpose = match.group(3).strip()
            # Skip header separator and header row
            if name and not name.startswith("-") and name.lower() != "function":
                functions.append(
                    ScheduledFunction(
                        name=name,
                        frequency=frequency,
                        purpose=purpose,
                        section_ref="Scheduled Functions",
                    )
                )

        # Also look for bullet points like "- `functionName` - every 30s"
        bullet_pattern = r"[-*]\s*`([^`]+)`\s*[-:]\s*(?:every\s*)?(\d+\w*)"
        for match in re.finditer(bullet_pattern, section, re.IGNORECASE):
            name = match.group(1).strip()
            frequency = match.group(2).strip()
            # Try to extract purpose from rest of line
            functions.append(
                ScheduledFunction(
                    name=name,
                    frequency=frequency,
                    purpose="",
                    section_ref="Scheduled Functions",
                )
            )

        return functions

    @classmethod
    def _extract_error_codes(cls, content: str) -> list[ErrorCode]:
        """Extract error codes from a tech spec."""
        codes = []

        # Find Error Codes section or subsection
        section = cls._extract_section(content, ["Error Codes"])
        if not section:
            # Look within API Design section
            api_section = cls._extract_section(content, ["API Design"])
            if api_section:
                # Find Error Codes subsection
                match = re.search(
                    r"###\s+Error Codes\s*\n(.*?)(?=\n###|\Z)", api_section, re.DOTALL
                )
                if match:
                    section = match.group(1)

        if not section:
            return codes

        # Look for bullet points like "- `ERR_CODE` - description"
        pattern = r"[-*]\s*`(ERR_\w+)`\s*[-:]\s*(.+?)(?=\n[-*]|\n\n|\Z)"
        for match in re.finditer(pattern, section, re.DOTALL):
            codes.append(
                ErrorCode(code=match.group(1), description=match.group(2).strip())
            )

        return codes

    @classmethod
    def _extract_performance_slas(cls, content: str) -> list[PerformanceSLA]:
        """Extract performance SLAs from a tech spec."""
        slas = []

        # Find Performance SLAs section
        section = cls._extract_section(
            content, ["Performance SLAs", "Performance", "SLAs"]
        )
        if not section:
            return slas

        # Look for bullet points like "- `metric` p95 < 300ms"
        pattern = r"[-*]\s*`?([^`\n]+)`?\s+([^<>\n]*[<>][^<>\n]+)"
        for match in re.finditer(pattern, section):
            metric = match.group(1).strip()
            target = match.group(2).strip()
            slas.append(PerformanceSLA(metric=metric, target=target))

        return slas

    @classmethod
    def _extract_gauntlet_decisions(cls, content: str) -> list[GauntletDecision]:
        """Extract gauntlet decisions summary from a tech spec."""
        decisions = []

        # Try to find the section by searching for "Gauntlet" in numbered sections
        section = None
        for i in range(1, 25):
            header_match = re.search(
                rf"##\s+{i}\.?\s+([^\n]+)", content
            )
            if header_match and "gauntlet" in header_match.group(1).lower():
                section = cls._extract_numbered_section(content, i)
                break

        if not section:
            section = cls._extract_section(
                content, ["Gauntlet Decisions Summary", "Gauntlet Decisions"]
            )
        if not section:
            return decisions

        # Look for table rows like "| Concern | Decision |"
        pattern = r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"
        for match in re.finditer(pattern, section):
            concern = match.group(1).strip()
            decision = match.group(2).strip()
            # Skip header rows and separator rows
            if (
                concern
                and concern.lower() != "concern"
                and not concern.startswith("-")
                and not all(c in "-| " for c in concern)
            ):
                decisions.append(GauntletDecision(concern=concern, decision=decision))

        return decisions

    @classmethod
    def _extract_all_sections(cls, content: str) -> list[TechSpecSection]:
        """Extract all numbered sections from a tech spec for reference."""
        sections = []

        # Match ## N. Title or ## N Title patterns
        pattern = r"##\s+(\d+)\.?\s+(.+?)\n(.*?)(?=\n##[^#]|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            section_num = match.group(1)
            title = match.group(2).strip()
            section_content = match.group(3).strip()

            section = TechSpecSection(
                number=section_num, title=title, content=section_content
            )

            # Extract subsections (### N.M Title)
            subsection_pattern = rf"###\s+({section_num}\.\d+)\s+(.+?)\n(.*?)(?=\n###|\Z)"
            for sub_match in re.finditer(subsection_pattern, section_content, re.DOTALL):
                section.subsections.append(
                    TechSpecSection(
                        number=sub_match.group(1),
                        title=sub_match.group(2).strip(),
                        content=sub_match.group(3).strip(),
                    )
                )

            sections.append(section)

        return sections
