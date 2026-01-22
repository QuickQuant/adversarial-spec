#!/usr/bin/env python3
"""
Scope Management for Adversarial Spec.

Detects scope expansion during spec refinement, generates mini-specs for
tangential discoveries, and manages user checkpoints for scope decisions.

Key concepts:
- ScopeDiscovery: A potential feature or expansion discovered during refinement
- MiniSpec: A stub document for a discovered feature (to be refined later)
- ScopeCheckpoint: A decision point where the user chooses how to handle discoveries
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# =============================================================================
# DATA STRUCTURES
# =============================================================================


class DiscoveryType(Enum):
    """Classification of scope discoveries."""

    TANGENTIAL_FEATURE = "tangential_feature"  # Nice-to-have, not blocking
    SCOPE_EXPANSION = "scope_expansion"  # Core task is bigger than expected
    PREREQUISITE = "prerequisite"  # Need this before the main task
    DECOMPOSITION = "decomposition"  # Task should split into multiple specs


class DiscoveryPriority(Enum):
    """Priority classification for discoveries."""

    NICE_TO_HAVE = "nice_to_have"  # Could be useful, not critical
    RECOMMENDED = "recommended"  # Should consider, improves quality
    IMPORTANT = "important"  # Significantly impacts the spec
    BLOCKING = "blocking"  # Cannot proceed without addressing


@dataclass
class ScopeDiscovery:
    """A potential feature or scope expansion discovered during refinement."""

    id: str
    name: str
    description: str
    discovery_type: DiscoveryType
    priority: DiscoveryPriority
    trigger_text: str  # The critique/concern that triggered this discovery
    source_model: str  # Which model identified this
    user_value: str  # Why this matters to users
    stub_location: Optional[str] = None  # Where to reference in main spec
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "discovery_type": self.discovery_type.value,
            "priority": self.priority.value,
            "trigger_text": self.trigger_text,
            "source_model": self.source_model,
            "user_value": self.user_value,
            "stub_location": self.stub_location,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScopeDiscovery":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            discovery_type=DiscoveryType(data["discovery_type"]),
            priority=DiscoveryPriority(data["priority"]),
            trigger_text=data["trigger_text"],
            source_model=data["source_model"],
            user_value=data["user_value"],
            stub_location=data.get("stub_location"),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class ScopeDecision:
    """User's decision about a discovery."""

    discovery_id: str
    action: str  # "stub", "expand", "defer", "reject"
    notes: Optional[str] = None
    decided_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ScopeReport:
    """Complete scope analysis from a refinement session."""

    discoveries: list[ScopeDiscovery]
    decisions: list[ScopeDecision] = field(default_factory=list)
    original_scope: str = ""
    session_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "discoveries": [d.to_dict() for d in self.discoveries],
            "decisions": [
                {
                    "discovery_id": d.discovery_id,
                    "action": d.action,
                    "notes": d.notes,
                    "decided_at": d.decided_at,
                }
                for d in self.decisions
            ],
            "original_scope": self.original_scope,
            "session_id": self.session_id,
        }

    def get_pending_decisions(self) -> list[ScopeDiscovery]:
        """Get discoveries that haven't been decided yet."""
        decided_ids = {d.discovery_id for d in self.decisions}
        return [d for d in self.discoveries if d.id not in decided_ids]

    def get_stubs(self) -> list[ScopeDiscovery]:
        """Get discoveries marked as stubs."""
        stub_ids = {d.discovery_id for d in self.decisions if d.action == "stub"}
        return [d for d in self.discoveries if d.id in stub_ids]

    def get_expansions(self) -> list[ScopeDiscovery]:
        """Get discoveries marked for expansion."""
        expand_ids = {d.discovery_id for d in self.decisions if d.action == "expand"}
        return [d for d in self.discoveries if d.id in expand_ids]


# =============================================================================
# MINI-SPEC TEMPLATE
# =============================================================================

MINI_SPEC_TEMPLATE = """# Suggested Feature: {name}

**Status**: Stub (discovered during adversarial review)
**Discovered**: {created_at}
**Source**: {source_model}
**Priority**: {priority}

## Summary

{description}

## User Value

{user_value}

## Trigger

This feature was identified when reviewing the main spec:

> {trigger_text}

## Scope Notes

- **Type**: {discovery_type}
- **Stub Location**: {stub_location}

## Next Steps

- [ ] Decide if this should be a separate spec
- [ ] If yes, run `/adversarial-spec` on this document to flesh it out
- [ ] Link back to original spec if implemented

---
*Generated by adversarial-spec scope management*
"""

STUB_REFERENCE_TEMPLATE = """
> **Scope Note**: {name}
>
> {description}
>
> See: [suggested-features/{slug}.md](suggested-features/{slug}.md)
"""


def generate_mini_spec(discovery: ScopeDiscovery) -> str:
    """Generate a mini-spec document from a discovery."""
    return MINI_SPEC_TEMPLATE.format(
        name=discovery.name,
        created_at=discovery.created_at[:10],
        source_model=discovery.source_model,
        priority=discovery.priority.value.replace("_", " ").title(),
        description=discovery.description,
        user_value=discovery.user_value,
        trigger_text=discovery.trigger_text[:500],
        discovery_type=discovery.discovery_type.value.replace("_", " ").title(),
        stub_location=discovery.stub_location or "N/A",
    )


def generate_stub_reference(discovery: ScopeDiscovery) -> str:
    """Generate a stub reference to insert into the main spec."""
    slug = slugify(discovery.name)
    return STUB_REFERENCE_TEMPLATE.format(
        name=discovery.name,
        description=discovery.description[:200],
        slug=slug,
    )


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


# =============================================================================
# SCOPE DETECTION
# =============================================================================

SCOPE_DETECTION_PROMPT = """Analyze this critique/response for scope implications.

You are looking for signs that:
1. The task is bigger than originally thought (SCOPE_EXPANSION)
2. A tangential feature was discovered that's worth noting (TANGENTIAL_FEATURE)
3. Something needs to be done first (PREREQUISITE)
4. The task should be split into multiple specs (DECOMPOSITION)

MODEL RESPONSE TO ANALYZE:
{response}

ORIGINAL SPEC CONTEXT:
{spec_summary}

For each scope implication found, output in this exact JSON format:
```json
{{
  "discoveries": [
    {{
      "name": "Short feature/task name",
      "description": "1-2 sentences describing what was discovered",
      "discovery_type": "tangential_feature|scope_expansion|prerequisite|decomposition",
      "priority": "nice_to_have|recommended|important|blocking",
      "trigger_text": "The specific text that triggered this discovery",
      "user_value": "Why this matters to users"
    }}
  ]
}}
```

If no scope implications found, output:
```json
{{"discoveries": []}}
```

IMPORTANT:
- Only flag genuine scope discoveries, not minor implementation details
- A critique about missing error handling is NOT a scope discovery
- A critique suggesting "you should also add user preferences" IS a tangential feature
- Focus on things that would require NEW design work, not just fixes to the current spec
"""

SCOPE_CHECKPOINT_PROMPT = """## Scope Checkpoint

During review, {count} potential scope {items} discovered:

{discoveries_summary}

### Options

For each discovery, choose:
- **stub**: Create a mini-spec and continue with core task
- **expand**: Add to current scope (increases complexity)
- **defer**: Note it but don't create stub
- **reject**: Not relevant, ignore

What would you like to do?
"""


def format_scope_checkpoint(discoveries: list[ScopeDiscovery]) -> str:
    """Format a user checkpoint prompt for scope decisions."""
    count = len(discoveries)
    items = "expansion was" if count == 1 else "expansions were"

    summaries = []
    for i, d in enumerate(discoveries, 1):
        priority_marker = ""
        if d.priority == DiscoveryPriority.BLOCKING:
            priority_marker = " [BLOCKING]"
        elif d.priority == DiscoveryPriority.IMPORTANT:
            priority_marker = " [IMPORTANT]"

        summaries.append(
            f"{i}. **{d.name}**{priority_marker} ({d.discovery_type.value.replace('_', ' ')})\n"
            f"   {d.description}\n"
            f"   _User value: {d.user_value}_"
        )

    return SCOPE_CHECKPOINT_PROMPT.format(
        count=count,
        items=items,
        discoveries_summary="\n\n".join(summaries),
    )


def parse_scope_discoveries(
    response: str,
    model: str,
    spec_summary: str,
) -> list[ScopeDiscovery]:
    """Parse scope discoveries from a model response.

    This is a simple heuristic parser. For production, you'd use the
    SCOPE_DETECTION_PROMPT with a model call.
    """
    import uuid

    discoveries = []

    # Look for JSON in the response
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            for d in data.get("discoveries", []):
                discoveries.append(
                    ScopeDiscovery(
                        id=str(uuid.uuid4())[:8],
                        name=d.get("name", "Unnamed"),
                        description=d.get("description", ""),
                        discovery_type=DiscoveryType(
                            d.get("discovery_type", "tangential_feature")
                        ),
                        priority=DiscoveryPriority(
                            d.get("priority", "nice_to_have")
                        ),
                        trigger_text=d.get("trigger_text", ""),
                        source_model=model,
                        user_value=d.get("user_value", ""),
                    )
                )
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    return discoveries


# =============================================================================
# SCOPE DETECTION (HEURISTIC)
# =============================================================================

# Keywords that suggest scope expansion
EXPANSION_KEYWORDS = [
    "should also",
    "would also need",
    "additionally requires",
    "this implies",
    "you'll also need",
    "consider adding",
    "might want to add",
    "would benefit from",
    "requires a separate",
    "out of scope but",
    "beyond the scope but",
    "future enhancement",
    "nice to have",
    "could also",
    "extends to",
]

PREREQUISITE_KEYWORDS = [
    "first need to",
    "before this",
    "prerequisite",
    "depends on",
    "requires first",
    "must have",
    "blocking on",
]

DECOMPOSITION_KEYWORDS = [
    "should be split",
    "separate spec",
    "multiple phases",
    "break this into",
    "too much for one",
    "should be its own",
]


def detect_scope_hints_heuristic(response: str) -> list[dict]:
    """Detect potential scope discoveries using keyword heuristics.

    Returns list of hints with the triggering text and suggested type.
    This is a fast, cheap alternative to using a model for detection.
    """
    hints = []
    response_lower = response.lower()

    # Check for expansion keywords
    for keyword in EXPANSION_KEYWORDS:
        if keyword in response_lower:
            # Extract surrounding context
            idx = response_lower.find(keyword)
            start = max(0, idx - 50)
            end = min(len(response), idx + len(keyword) + 150)
            context = response[start:end]

            hints.append(
                {
                    "type": "tangential_feature",
                    "keyword": keyword,
                    "context": context,
                }
            )

    # Check for prerequisite keywords
    for keyword in PREREQUISITE_KEYWORDS:
        if keyword in response_lower:
            idx = response_lower.find(keyword)
            start = max(0, idx - 50)
            end = min(len(response), idx + len(keyword) + 150)
            context = response[start:end]

            hints.append(
                {
                    "type": "prerequisite",
                    "keyword": keyword,
                    "context": context,
                }
            )

    # Check for decomposition keywords
    for keyword in DECOMPOSITION_KEYWORDS:
        if keyword in response_lower:
            idx = response_lower.find(keyword)
            start = max(0, idx - 50)
            end = min(len(response), idx + len(keyword) + 150)
            context = response[start:end]

            hints.append(
                {
                    "type": "decomposition",
                    "keyword": keyword,
                    "context": context,
                }
            )

    return hints


# =============================================================================
# PERSISTENCE
# =============================================================================

SCOPE_DIR = Path.home() / ".adversarial-spec" / "scope"


def save_mini_spec(discovery: ScopeDiscovery, output_dir: Optional[Path] = None) -> Path:
    """Save a mini-spec to disk.

    Args:
        discovery: The discovery to save
        output_dir: Directory to save to (default: ~/.adversarial-spec/scope/suggested-features/)

    Returns:
        Path to the saved file
    """
    if output_dir is None:
        output_dir = SCOPE_DIR / "suggested-features"

    output_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(discovery.name)
    filename = f"{slug}.md"
    filepath = output_dir / filename

    content = generate_mini_spec(discovery)
    filepath.write_text(content)

    return filepath


def save_scope_report(report: ScopeReport, session_id: str) -> Path:
    """Save a scope report to disk.

    Args:
        report: The scope report to save
        session_id: Session identifier

    Returns:
        Path to the saved file
    """
    SCOPE_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"scope-report-{session_id}.json"
    filepath = SCOPE_DIR / filename

    filepath.write_text(json.dumps(report.to_dict(), indent=2))

    return filepath


def load_scope_report(session_id: str) -> Optional[ScopeReport]:
    """Load a scope report from disk.

    Args:
        session_id: Session identifier

    Returns:
        ScopeReport if found, None otherwise
    """
    filename = f"scope-report-{session_id}.json"
    filepath = SCOPE_DIR / filename

    if not filepath.exists():
        return None

    try:
        data = json.loads(filepath.read_text())
        return ScopeReport(
            discoveries=[ScopeDiscovery.from_dict(d) for d in data.get("discoveries", [])],
            decisions=[
                ScopeDecision(
                    discovery_id=d["discovery_id"],
                    action=d["action"],
                    notes=d.get("notes"),
                    decided_at=d.get("decided_at", datetime.now().isoformat()),
                )
                for d in data.get("decisions", [])
            ],
            original_scope=data.get("original_scope", ""),
            session_id=data.get("session_id"),
        )
    except (json.JSONDecodeError, KeyError):
        return None


# =============================================================================
# FORMATTING
# =============================================================================


def format_discoveries_summary(discoveries: list[ScopeDiscovery]) -> str:
    """Format a brief summary of discoveries for output."""
    if not discoveries:
        return "No scope discoveries."

    lines = [f"=== Scope Discoveries ({len(discoveries)}) ===", ""]

    by_type: dict[str, list[ScopeDiscovery]] = {}
    for d in discoveries:
        type_name = d.discovery_type.value.replace("_", " ").title()
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(d)

    for type_name, type_discoveries in by_type.items():
        lines.append(f"**{type_name}**:")
        for d in type_discoveries:
            priority = f"[{d.priority.value.upper()}]" if d.priority != DiscoveryPriority.NICE_TO_HAVE else ""
            lines.append(f"  - {d.name} {priority}")
            lines.append(f"    {d.description[:100]}...")
        lines.append("")

    return "\n".join(lines)


def format_scope_notes_section(stubs: list[ScopeDiscovery]) -> str:
    """Format a scope notes section to append to a spec."""
    if not stubs:
        return ""

    lines = [
        "",
        "---",
        "",
        "## Scope Notes",
        "",
        "The following items were identified during adversarial review but deferred:",
        "",
    ]

    for stub in stubs:
        slug = slugify(stub.name)
        lines.append(f"### {stub.name}")
        lines.append("")
        lines.append(f"{stub.description}")
        lines.append("")
        lines.append(f"_Priority: {stub.priority.value.replace('_', ' ').title()}_")
        lines.append(f"_See: [suggested-features/{slug}.md](suggested-features/{slug}.md)_")
        lines.append("")

    return "\n".join(lines)
