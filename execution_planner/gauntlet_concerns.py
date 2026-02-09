"""
Gauntlet Concern Parsing and Linking

Parses gauntlet concern JSON files and links concerns to spec sections
for richer execution plans.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add adversarial-spec scripts to path for shared imports
# Works whether execution_planner is in project root or skill directory
_PARENT = Path(__file__).parent.parent
_SCRIPTS_PATH = _PARENT / "scripts"  # Skill directory layout
if not _SCRIPTS_PATH.exists():
    _SCRIPTS_PATH = _PARENT / "skills" / "adversarial-spec" / "scripts"  # Project layout
if str(_SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PATH))

from adversaries import ADVERSARY_PREFIXES, generate_concern_id  # noqa: E402


@dataclass
class GauntletConcern:
    """A concern raised during gauntlet review."""

    adversary: str
    text: str
    severity: str
    id: str = ""  # Stable ID for linking (auto-generated if empty)
    section_refs: list[str] = field(default_factory=list)
    title: Optional[str] = None
    failure_mode: Optional[str] = None
    detection: Optional[str] = None
    blast_radius: Optional[str] = None
    consequence: Optional[str] = None

    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            self.id = generate_concern_id(self.adversary, self.text)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "adversary": self.adversary,
            "text": self.text,
            "severity": self.severity,
            "section_refs": self.section_refs,
            "title": self.title,
            "failure_mode": self.failure_mode,
            "detection": self.detection,
            "blast_radius": self.blast_radius,
            "consequence": self.consequence,
        }


@dataclass
class LinkedConcern:
    """A concern linked to specific spec elements."""

    concern: GauntletConcern
    spec_section: Optional[str] = None  # e.g., "4.3", "6.2"
    spec_title: Optional[str] = None  # e.g., "Nonce Management"
    data_model: Optional[str] = None  # e.g., "order_queue"
    api_endpoint: Optional[str] = None  # e.g., "orders:placeArbitrage"
    related_data_models: list[str] = field(default_factory=list)
    related_endpoints: list[str] = field(default_factory=list)


@dataclass
class GauntletReport:
    """Complete parsed gauntlet concerns with linking."""

    concerns: list[GauntletConcern] = field(default_factory=list)
    linked_concerns: list[LinkedConcern] = field(default_factory=list)
    by_section: dict[str, list[GauntletConcern]] = field(default_factory=dict)
    by_adversary: dict[str, list[GauntletConcern]] = field(default_factory=dict)
    by_severity: dict[str, list[GauntletConcern]] = field(default_factory=dict)
    source_path: Optional[str] = None

    def get_concerns_for_section(self, section: str) -> list[GauntletConcern]:
        """Get all concerns that reference a specific section."""
        return self.by_section.get(section, [])

    def get_high_severity(self) -> list[GauntletConcern]:
        """Get all high severity concerns."""
        return self.by_severity.get("high", [])

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(
            {
                "concerns": [c.to_dict() for c in self.concerns],
                "by_section": {
                    k: [c.to_dict() for c in v] for k, v in self.by_section.items()
                },
                "source_path": self.source_path,
            },
            indent=2,
        )


class GauntletConcernParser:
    """Parser for gauntlet concern JSON files."""

    # Patterns for extracting section references
    SECTION_PATTERNS = [
        r"\(Section\s*(\d+(?:\.\d+)?)\)",  # (Section 4.3)
        r"\((\d+\.\d+)\)",  # (4.3)
        r"Section\s+(\d+(?:\.\d+)?)",  # Section 4.3
        r"§\s*(\d+(?:\.\d+)?)",  # § 4.3
        r"\[Section\s*(\d+(?:\.\d+)?)\]",  # [Section 4.3]
    ]

    # Patterns for extracting data model references
    DATA_MODEL_PATTERNS = [
        r"`(\w+_\w+)`",  # `order_queue`
        r"`(\w+)`\s+table",  # `orders` table
        r"(\w+)\s+table",  # orders table
    ]

    # Patterns for extracting API endpoint references
    API_PATTERNS = [
        r"`(\w+:\w+)`",  # `orders:placeDma`
        r"(\w+:\w+)\s+action",  # orders:placeDma action
    ]

    @classmethod
    def parse(cls, content: str) -> GauntletReport:
        """
        Parse gauntlet concerns from JSON content.

        Args:
            content: Raw JSON content

        Returns:
            GauntletReport with parsed and linked concerns
        """
        data = json.loads(content)
        report = GauntletReport()

        for item in data:
            concern = cls._parse_concern(item)
            report.concerns.append(concern)

            # Index by section
            for ref in concern.section_refs:
                if ref not in report.by_section:
                    report.by_section[ref] = []
                report.by_section[ref].append(concern)

            # Index by adversary
            if concern.adversary not in report.by_adversary:
                report.by_adversary[concern.adversary] = []
            report.by_adversary[concern.adversary].append(concern)

            # Index by severity
            if concern.severity not in report.by_severity:
                report.by_severity[concern.severity] = []
            report.by_severity[concern.severity].append(concern)

        return report

    @classmethod
    def parse_file(cls, path: Path) -> GauntletReport:
        """
        Parse gauntlet concerns from a JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            GauntletReport with parsed concerns
        """
        if not path.exists():
            raise FileNotFoundError(f"Gauntlet file not found: {path}")

        content = path.read_text(encoding="utf-8")
        report = cls.parse(content)
        report.source_path = str(path)
        return report

    @classmethod
    def _parse_concern(cls, item: dict) -> GauntletConcern:
        """Parse a single concern from a dict."""
        text = item.get("text", "")

        # Extract section references
        section_refs = cls._extract_section_refs(text)

        # Extract title (often in **bold**)
        title = cls._extract_title(text)

        # Extract failure mode, detection, blast radius, consequence
        failure_mode = cls._extract_field(text, "Failure Mode")
        detection = cls._extract_field(text, "Detection", "How Operators Find Out")
        blast_radius = cls._extract_field(text, "Blast Radius")
        consequence = cls._extract_field(text, "Consequence")

        return GauntletConcern(
            adversary=item.get("adversary", ""),
            text=text,
            severity=item.get("severity", "medium"),
            id=item.get("id", ""),  # ID from JSON, or auto-generate via __post_init__
            section_refs=section_refs,
            title=title,
            failure_mode=failure_mode,
            detection=detection,
            blast_radius=blast_radius,
            consequence=consequence,
        )

    @classmethod
    def _extract_section_refs(cls, text: str) -> list[str]:
        """Extract section references from concern text."""
        refs = set()
        for pattern in cls.SECTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                refs.add(match.group(1))
        return sorted(refs)

    @classmethod
    def _extract_title(cls, text: str) -> Optional[str]:
        """Extract title from concern text (usually in **bold**)."""
        match = re.search(r"\*\*([^*]+)\*\*", text)
        if match:
            title = match.group(1).strip()
            # Remove trailing colon or punctuation
            title = re.sub(r"[:\s]+$", "", title)
            return title
        return None

    @classmethod
    def _extract_field(cls, text: str, *field_names: str) -> Optional[str]:
        """Extract a field value from concern text."""
        for name in field_names:
            pattern = rf"\*\*{re.escape(name)}:?\*\*:?\s*(.+?)(?=\*\*|\Z)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def link_to_spec(
        cls,
        report: GauntletReport,
        spec_doc: "SpecDocument",  # noqa: F821
    ) -> None:
        """
        Link concerns to spec elements.

        Updates the report's linked_concerns list with references to
        specific spec elements (data models, endpoints, etc.).
        """
        from execution_planner.spec_intake import SpecDocument

        report.linked_concerns = []

        for concern in report.concerns:
            linked = LinkedConcern(concern=concern)

            # Find matching spec section
            for ref in concern.section_refs:
                section = spec_doc.get_section_by_number(ref)
                if section:
                    linked.spec_section = ref
                    linked.spec_title = section.title
                    break

            # Find related data models
            for pattern in cls.DATA_MODEL_PATTERNS:
                for match in re.finditer(pattern, concern.text):
                    model_name = match.group(1)
                    for dm in spec_doc.data_models:
                        if dm.name.lower() == model_name.lower():
                            linked.related_data_models.append(dm.name)
                            if not linked.data_model:
                                linked.data_model = dm.name
                            break

            # Find related API endpoints
            for pattern in cls.API_PATTERNS:
                for match in re.finditer(pattern, concern.text):
                    endpoint_name = match.group(1)
                    for ep in spec_doc.api_endpoints:
                        if ep.name.lower() == endpoint_name.lower():
                            linked.related_endpoints.append(ep.name)
                            if not linked.api_endpoint:
                                linked.api_endpoint = ep.name
                            break

            report.linked_concerns.append(linked)


def load_concerns_for_spec(
    spec_path: Path,
    concerns_path: Optional[Path] = None,
) -> Optional[GauntletReport]:
    """
    Load gauntlet concerns for a spec file.

    If concerns_path is not provided, tries to find a matching concerns file
    in the same directory (e.g., gauntlet-concerns-*.json).

    Args:
        spec_path: Path to the spec file
        concerns_path: Optional explicit path to concerns JSON

    Returns:
        GauntletReport or None if no concerns found
    """
    if concerns_path and concerns_path.exists():
        return GauntletConcernParser.parse_file(concerns_path)

    # Try to find concerns file automatically
    spec_dir = spec_path.parent
    spec_stem = spec_path.stem

    # Look for patterns like:
    # - gauntlet-concerns-2026-01-23.json
    # - gauntlet-{spec_name}-concerns.json
    # - {spec_name}-gauntlet.json
    patterns = [
        "gauntlet-concerns-*.json",
        "gauntlet-*-concerns*.json",
        f"*{spec_stem}*gauntlet*.json",
    ]

    for pattern in patterns:
        matches = list(spec_dir.glob(pattern))
        if matches:
            # Return the most recent one
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return GauntletConcernParser.parse_file(matches[0])

    return None
