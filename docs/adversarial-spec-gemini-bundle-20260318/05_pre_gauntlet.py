# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/pre_gauntlet/__init__.py (92 lines, 1844 bytes)
# ══════════════════════════════════════════════════════════════
"""
Pre-Gauntlet Module

Provides pre-gauntlet checks for spec/codebase compatibility
and discovery of external service documentation.
"""

from .discovery import (
    DiscoveredService,
    DiscoveryAgent,
    DiscoveryResult,
    run_discovery,
)
from .models import (
    AlignmentIssue,
    AlignmentResolution,
    AlignmentStatus,
    BuildStatus,
    CompatibilityConfig,
    Concern,
    ConcernCategory,
    ConcernSeverity,
    ContextSummary,
    DiscoveredServiceSummary,
    DiscoverySummary,
    DocType,
    DocTypeRule,
    EvidenceRef,
    EvidenceType,
    FileSnapshot,
    GitPosition,
    PreGauntletResult,
    PreGauntletStatus,
    SystemState,
    Timings,
    ValidationCommand,
    ValidationResult,
)
from .orchestrator import (
    EXIT_ABORTED,
    EXIT_COMPLETE,
    EXIT_CONFIG_ERROR,
    EXIT_INFRA_ERROR,
    EXIT_NEEDS_ALIGNMENT,
    get_exit_code,
    load_config_from_pyproject,
    run_pre_gauntlet,
    save_report,
)

__all__ = [
    # Discovery
    "DiscoveredService",
    "DiscoveryAgent",
    "DiscoveryResult",
    "run_discovery",
    # Models
    "AlignmentIssue",
    "AlignmentResolution",
    "AlignmentStatus",
    "BuildStatus",
    "CompatibilityConfig",
    "Concern",
    "ConcernCategory",
    "ConcernSeverity",
    "ContextSummary",
    "DiscoveredServiceSummary",
    "DiscoverySummary",
    "DocType",
    "DocTypeRule",
    "EvidenceRef",
    "EvidenceType",
    "FileSnapshot",
    "GitPosition",
    "PreGauntletResult",
    "PreGauntletStatus",
    "SystemState",
    "Timings",
    "ValidationCommand",
    "ValidationResult",
    # Functions
    "get_exit_code",
    "load_config_from_pyproject",
    "run_pre_gauntlet",
    "save_report",
    # Exit codes
    "EXIT_ABORTED",
    "EXIT_COMPLETE",
    "EXIT_CONFIG_ERROR",
    "EXIT_INFRA_ERROR",
    "EXIT_NEEDS_ALIGNMENT",
]


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py (325 lines, 10914 bytes)
# ══════════════════════════════════════════════════════════════
"""
Pre-Gauntlet Orchestrator

Entry point for pre-gauntlet execution. Coordinates collectors, extractors,
context building, and alignment mode.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.git_position import GitPositionCollector
from collectors.system_state import SystemStateCollector
from extractors.spec_affected_files import extract_spec_affected_files
from integrations.git_cli import GitCliError

from .alignment_mode import run_alignment_mode
from .context_builder import build_context


class PreGauntletOrchestrator:
    """Orchestrates pre-gauntlet execution."""

    def __init__(
        self,
        repo_root: str | Path,
        config: CompatibilityConfig,
        interactive: bool = True,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.config = config
        self.interactive = interactive

    def run(
        self,
        spec_text: str,
        doc_type: DocType,
        discovery_result: DiscoveryResult | None = None,
    ) -> PreGauntletResult:
        """Run pre-gauntlet checks.

        Args:
            spec_text: The specification document text
            doc_type: Type of document (prd, tech, debug)
            discovery_result: Optional discovery result with priming context

        Returns:
            PreGauntletResult with status, concerns, and context
        """
        start_time = time.monotonic()
        timings = Timings()

        # Get doc type rules
        rules = self.config.get_doc_type_rule(doc_type)

        # Check if pre-gauntlet is enabled for this doc type
        if not self.config.enabled or not rules.enabled:
            return PreGauntletResult(
                status=PreGauntletStatus.COMPLETE,
                doc_type=doc_type,
                context_markdown=spec_text,  # Just pass through the spec
            )

        all_concerns = []
        git_position = None
        system_state = None

        # Extract spec-affected files
        try:
            spec_affected_files = extract_spec_affected_files(
                spec_text=spec_text,
                repo_root=self.repo_root,
                include_untracked=self.config.include_untracked,
                critical_paths=self.config.critical_paths,
            )
        except Exception as e:
            print(f"Warning: Could not extract spec-affected files: {e}", file=sys.stderr)
            spec_affected_files = []

        # Collect git position
        if rules.require_git:
            git_start = time.monotonic()
            try:
                collector = GitPositionCollector(
                    repo_root=self.repo_root,
                    base_branch=self.config.base_branch,
                    staleness_threshold_days=self.config.staleness_threshold_days,
                    spec_affected_files=spec_affected_files,
                )
                git_position, git_concerns = collector.collect()
                all_concerns.extend(git_concerns)
            except GitCliError as e:
                return PreGauntletResult(
                    status=PreGauntletStatus.INFRA_ERROR,
                    doc_type=doc_type,
                    context_markdown=f"Git error: {e}",
                )
            timings.git_ms = int((time.monotonic() - git_start) * 1000)

        # Collect system state
        if rules.require_build or rules.require_schema or rules.require_trees or rules.require_validation:
            state_start = time.monotonic()
            try:
                collector = SystemStateCollector(
                    repo_root=self.repo_root,
                    build_command=self.config.build_command if rules.require_build else None,
                    build_timeout=self.config.build_timeout_seconds,
                    validation_commands=self.config.validation_commands if rules.require_validation else None,
                    schema_files=self.config.schema_files if rules.require_schema else None,
                    critical_paths=self.config.critical_paths if rules.require_trees else None,
                    file_max_bytes=self.config.file_max_bytes,
                    tree_max_depth=self.config.tree_max_depth,
                    tree_max_entries=self.config.tree_max_entries,
                )
                system_state, state_concerns = collector.collect()
                all_concerns.extend(state_concerns)

                timings.build_ms = system_state.build_duration_ms
                timings.files_ms = int((time.monotonic() - state_start) * 1000) - timings.build_ms

            except Exception as e:
                return PreGauntletResult(
                    status=PreGauntletStatus.INFRA_ERROR,
                    doc_type=doc_type,
                    context_markdown=f"System state collection error: {e}",
                )

        # Build context
        context_markdown, truncated_sections = build_context(
            git_position=git_position,
            system_state=system_state,
            spec_text=spec_text,
            max_chars=self.config.context_max_chars,
        )

        # Prepend discovery priming context if available
        if discovery_result and discovery_result.priming_context:
            context_markdown = discovery_result.priming_context + "\n\n" + context_markdown

        # Calculate total time
        timings.total_ms = int((time.monotonic() - start_time) * 1000)

        # Build discovery summary if available
        discovery_summary = None
        if discovery_result:
            discovery_summary = DiscoverySummary(
                services=[
                    DiscoveredServiceSummary(
                        name=s.name,
                        confidence=s.confidence,
                        doc_fetched=s.doc_fetched,
                    )
                    for s in discovery_result.services
                ],
                discovery_time_ms=discovery_result.discovery_time_ms,
                errors=discovery_result.errors,
            )

        # Build initial result
        result = PreGauntletResult(
            status=PreGauntletStatus.COMPLETE,
            doc_type=doc_type,
            concerns=all_concerns,
            git_position=git_position,
            system_state=system_state,
            discovery_summary=discovery_summary,
            context_summary=ContextSummary(
                context_chars=len(context_markdown),
                truncated_sections=truncated_sections,
            ),
            timings=timings,
            context_markdown=context_markdown,
        )

        # Check for blockers and run alignment mode if needed
        blockers = result.get_blockers()
        if blockers:
            status, alignment_issues, was_overridden = run_alignment_mode(
                blockers=blockers,
                result=result,
                interactive=self.interactive,
            )
            result.status = status
            result.alignment_issues = alignment_issues
            result.alignment_override = was_overridden

        return result


def run_pre_gauntlet(
    spec_text: str,
    doc_type: DocType | str,
    repo_root: str | Path | None = None,
    config: CompatibilityConfig | None = None,
    interactive: bool = True,
    discovery_result: DiscoveryResult | None = None,
) -> PreGauntletResult:
    """Run pre-gauntlet checks.

    Args:
        spec_text: The specification document text
        doc_type: Type of document (prd, tech, debug)
        repo_root: Path to repository root (default: current directory)
        config: Configuration (default: auto-load from pyproject.toml)
        interactive: Whether to run in interactive mode
        discovery_result: Optional discovery result with external service documentation

    Returns:
        PreGauntletResult with status, concerns, and context
    """
    # Convert string to enum
    if isinstance(doc_type, str):
        doc_type = DocType(doc_type.lower())

    # Default repo root
    if repo_root is None:
        repo_root = Path.cwd()
    repo_root = Path(repo_root).resolve()

    # Load config from pyproject.toml if not provided
    if config is None:
        config = load_config_from_pyproject(repo_root)

    orchestrator = PreGauntletOrchestrator(
        repo_root=repo_root,
        config=config,
        interactive=interactive,
    )

    return orchestrator.run(
        spec_text=spec_text,
        doc_type=doc_type,
        discovery_result=discovery_result,
    )


def load_config_from_pyproject(repo_root: Path) -> CompatibilityConfig:
    """Load configuration from pyproject.toml.

    Args:
        repo_root: Path to repository root

    Returns:
        CompatibilityConfig (defaults if not found)
    """
    pyproject_path = repo_root / "pyproject.toml"

    if not pyproject_path.exists():
        return CompatibilityConfig()

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            # No TOML parser available, use defaults
            return CompatibilityConfig()

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        tool_config = data.get("tool", {}).get("adversarial-spec", {}).get("compatibility", {})

        if not tool_config:
            return CompatibilityConfig()

        return CompatibilityConfig(**tool_config)

    except Exception as e:
        print(f"Warning: Could not parse pyproject.toml: {e}", file=sys.stderr)
        return CompatibilityConfig()


def save_report(result: PreGauntletResult, output_path: Path) -> None:
    """Save pre-gauntlet report to JSON file.

    Args:
        result: Pre-gauntlet result
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict, excluding the full context markdown
    report = result.model_dump(exclude={"context_markdown"})

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)


# Exit codes for CLI
EXIT_COMPLETE = 0
EXIT_NEEDS_ALIGNMENT = 2
EXIT_ABORTED = 3
EXIT_CONFIG_ERROR = 4
EXIT_INFRA_ERROR = 5


def get_exit_code(status: PreGauntletStatus) -> int:
    """Get CLI exit code for a status."""
    return {
        PreGauntletStatus.COMPLETE: EXIT_COMPLETE,
        PreGauntletStatus.NEEDS_ALIGNMENT: EXIT_NEEDS_ALIGNMENT,
        PreGauntletStatus.ABORTED: EXIT_ABORTED,
        PreGauntletStatus.CONFIG_ERROR: EXIT_CONFIG_ERROR,
        PreGauntletStatus.INFRA_ERROR: EXIT_INFRA_ERROR,
    }.get(status, 1)


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/pre_gauntlet/models.py (334 lines, 9626 bytes)
# ══════════════════════════════════════════════════════════════
"""
Pre-Gauntlet Data Models

Pydantic models for configuration, git position, system state, concerns, and results.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# =============================================================================
# ENUMS
# =============================================================================


class DocType(str, Enum):
    PRD = "prd"
    TECH = "tech"
    DEBUG = "debug"


class PreGauntletStatus(str, Enum):
    COMPLETE = "COMPLETE"
    NEEDS_ALIGNMENT = "NEEDS_ALIGNMENT"
    ABORTED = "ABORTED"
    CONFIG_ERROR = "CONFIG_ERROR"
    INFRA_ERROR = "INFRA_ERROR"


class ConcernSeverity(str, Enum):
    BLOCKER = "BLOCKER"
    WARN = "WARN"
    INFO = "INFO"


class ConcernCategory(str, Enum):
    GIT = "GIT"
    BUILD = "BUILD"
    SCHEMA = "SCHEMA"
    CONFIG = "CONFIG"
    CONTEXT = "CONTEXT"
    DOC_TYPE = "DOC_TYPE"


class BuildStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"
    SKIP = "SKIP"


class FileChangeStatus(str, Enum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"


class AlignmentResolution(str, Enum):
    FIX_CODE = "FIX_CODE"
    UPDATE_SPEC = "UPDATE_SPEC"
    IGNORE = "IGNORE"


class AlignmentStatus(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    RESOLVED = "RESOLVED"
    OVERRIDDEN = "OVERRIDDEN"


class EvidenceType(str, Enum):
    COMMAND_OUTPUT = "COMMAND_OUTPUT"
    FILE_CONTENT = "FILE_CONTENT"
    GIT_LOG = "GIT_LOG"


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================


class DocTypeRule(BaseModel):
    """Configuration for a specific document type."""

    enabled: bool = True
    require_git: bool = True
    require_build: bool = True
    require_schema: bool = False
    require_trees: bool = False
    require_validation: bool = True  # Run validation commands


class ValidationCommand(BaseModel):
    """A named validation command for schema/data consistency checks."""

    name: str  # e.g., "convex", "prisma", "typecheck"
    command: list[str]  # e.g., ["npx", "convex", "dev", "--once"]
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    description: str = ""  # What this validates
    environment: str = ""  # e.g., "production", "development", "staging" - CRITICAL for avoiding false positives
    error_patterns: list[str] = Field(default_factory=list)  # Regex patterns that indicate failure


class CompatibilityConfig(BaseModel):
    """Configuration for pre-gauntlet compatibility checks."""

    enabled: bool = True
    base_branch: str = "main"
    build_command: list[str] | None = None
    build_timeout_seconds: int = Field(default=60, ge=5, le=300)
    validation_commands: list[ValidationCommand] = Field(default_factory=list)
    schema_files: list[str] = Field(default_factory=list)
    critical_paths: list[str] = Field(default_factory=list)
    include_untracked: bool = False
    file_max_bytes: int = Field(default=200_000, le=2_000_000)
    tree_max_depth: int = Field(default=6, le=8)
    tree_max_entries: int = Field(default=5000, le=20_000)
    context_max_chars: int = Field(default=200_000, le=250_000)
    staleness_threshold_days: int = Field(default=3, ge=1, le=30)
    doc_type_rules: dict[str, DocTypeRule] = Field(default_factory=dict)

    def get_doc_type_rule(self, doc_type: DocType) -> DocTypeRule:
        """Get the rule for a document type, with defaults."""
        if doc_type.value in self.doc_type_rules:
            return self.doc_type_rules[doc_type.value]

        # Default rules per doc type
        defaults = {
            DocType.PRD: DocTypeRule(
                enabled=False,
                require_git=False,
                require_build=False,
                require_schema=False,
                require_trees=False,
            ),
            DocType.TECH: DocTypeRule(
                enabled=True,
                require_git=True,
                require_build=True,
                require_schema=True,
                require_trees=True,
            ),
            DocType.DEBUG: DocTypeRule(
                enabled=True,
                require_git=True,
                require_build=True,
                require_schema=False,
                require_trees=False,
            ),
        }
        return defaults.get(doc_type, DocTypeRule())


# =============================================================================
# GIT POSITION MODELS
# =============================================================================


class CommitSummary(BaseModel):
    """Summary of a git commit."""

    hash: str
    author: str
    date: datetime
    subject: str


class FileChange(BaseModel):
    """A file change between branches."""

    path: str
    status: FileChangeStatus


class GitPosition(BaseModel):
    """Current git repository position and status."""

    current_branch: str
    head_commit: str
    base_branch: str
    base_commit: str
    merge_base_commit: str
    commits_ahead: int
    commits_behind: int
    last_sync_with_base: datetime
    main_recent_commits: list[CommitSummary] = Field(default_factory=list)
    affected_files_changes: list[FileChange] = Field(default_factory=list)
    working_tree_clean: bool = True
    detached_head: bool = False


# =============================================================================
# SYSTEM STATE MODELS
# =============================================================================


class FileSnapshot(BaseModel):
    """Snapshot of a file's contents."""

    path: str
    sha256: str
    content: str
    truncated: bool = False


class DirectoryTree(BaseModel):
    """Directory tree listing."""

    path: str
    tree: str
    truncated: bool = False


class ValidationResult(BaseModel):
    """Result of a validation command execution."""

    name: str  # e.g., "convex", "prisma"
    command: list[str]
    status: BuildStatus
    exit_code: int | None = None
    duration_ms: int = 0
    output_excerpt: str = ""
    description: str = ""
    environment: str = ""  # Which environment was validated (production, development, staging)


class SystemState(BaseModel):
    """Current system/build state."""

    build_status: BuildStatus = BuildStatus.SKIP
    build_exit_code: int | None = None
    build_duration_ms: int = 0
    build_output_excerpt: str = ""
    validation_results: list[ValidationResult] = Field(default_factory=list)
    schema_contents: list[FileSnapshot] = Field(default_factory=list)
    directory_trees: list[DirectoryTree] = Field(default_factory=list)
    working_tree_clean: bool = True
    collection_timestamp: datetime = Field(default_factory=datetime.now)


# =============================================================================
# CONCERN MODELS
# =============================================================================


class EvidenceRef(BaseModel):
    """Reference to evidence supporting a concern."""

    type: EvidenceType
    source: str
    excerpt: str


class Concern(BaseModel):
    """A compatibility concern raised by pre-gauntlet."""

    id: str  # Format: COMP-{hash8}
    severity: ConcernSeverity
    category: ConcernCategory
    title: str
    message: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class AlignmentIssue(BaseModel):
    """An alignment issue requiring user action."""

    concern_id: str
    status: AlignmentStatus = AlignmentStatus.UNRESOLVED
    resolution: AlignmentResolution | None = None


# =============================================================================
# RESULT MODELS
# =============================================================================


class ContextSummary(BaseModel):
    """Summary of the generated context."""

    context_chars: int = 0
    truncated_sections: list[str] = Field(default_factory=list)


class Timings(BaseModel):
    """Timing information for pre-gauntlet execution."""

    git_ms: int = 0
    build_ms: int = 0
    files_ms: int = 0
    total_ms: int = 0


class DiscoveredServiceSummary(BaseModel):
    """Summary of a discovered external service."""

    name: str
    confidence: float
    doc_fetched: bool = False


class DiscoverySummary(BaseModel):
    """Summary of discovery phase results."""

    services: list[DiscoveredServiceSummary] = Field(default_factory=list)
    discovery_time_ms: int = 0
    errors: list[str] = Field(default_factory=list)


class PreGauntletResult(BaseModel):
    """Result of pre-gauntlet execution."""

    status: PreGauntletStatus
    doc_type: DocType
    concerns: list[Concern] = Field(default_factory=list)
    alignment_issues: list[AlignmentIssue] = Field(default_factory=list)
    git_position: GitPosition | None = None
    system_state: SystemState | None = None
    discovery_summary: DiscoverySummary | None = None
    context_summary: ContextSummary = Field(default_factory=ContextSummary)
    timings: Timings = Field(default_factory=Timings)
    context_markdown: str = ""  # The generated context for LLM injection
    alignment_override: bool = False  # True if user forced ignore

    def has_blockers(self) -> bool:
        """Check if there are any BLOCKER severity concerns."""
        return any(c.severity == ConcernSeverity.BLOCKER for c in self.concerns)

    def get_blockers(self) -> list[Concern]:
        """Get all BLOCKER severity concerns."""
        return [c for c in self.concerns if c.severity == ConcernSeverity.BLOCKER]


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/pre_gauntlet/discovery.py (303 lines, 9983 bytes)
# ══════════════════════════════════════════════════════════════
"""
Discovery Agent - Pre-Debate Documentation Fetching

Runs BEFORE the constructive debate to:
1. Extract external service/library names from the user's prompt
2. Fetch high-level documentation via Context7
3. Build a "priming context" that grounds the debate in reality

This prevents assumptions by giving models actual documentation
rather than letting them pattern-match from training data.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredService:
    """An external service/library identified in the spec."""
    name: str
    confidence: float  # 0.0 to 1.0
    context: str  # Surrounding text where it was found
    doc_fetched: bool = False
    doc_summary: str = ""


@dataclass
class DiscoveryResult:
    """Result of the discovery phase."""
    services: list[DiscoveredService] = field(default_factory=list)
    priming_context: str = ""
    token_usage: dict[str, Any] = field(default_factory=dict)
    discovery_time_ms: int = 0
    errors: list[str] = field(default_factory=list)


class DiscoveryAgent:
    """
    Extracts external services from spec text and fetches their documentation.

    This runs BEFORE the constructive debate phase to prevent the models
    from making assumptions about how external systems work.
    """

    # Common service/library patterns to detect
    SERVICE_PATTERNS = [
        # SDK patterns: @org/package, org-package
        (r"@[\w-]+/[\w-]+", 0.9),  # @polymarket/clob-client
        (r"[\w]+-sdk", 0.8),  # stripe-sdk

        # API mentions
        (r"\b(\w+)\s+API\b", 0.7),  # "Polymarket API"
        (r"\bAPI\s+for\s+(\w+)", 0.7),  # "API for Stripe"

        # Integration keywords
        (r"integrat(?:e|ing|ion)\s+(?:with\s+)?(\w+)", 0.6),

        # Common services (high confidence when mentioned)
        (r"\b(Polymarket|Kalshi|Stripe|Twilio|SendGrid|AWS|GCP|Azure|Firebase|Supabase|Convex|Prisma|MongoDB|PostgreSQL|Redis|Kafka|RabbitMQ)\b", 0.95),
    ]

    # Patterns that look like services but aren't
    FALSE_POSITIVE_PATTERNS = [
        r"^(the|a|an|this|that|our|their|your)$",
        r"^(API|SDK|HTTP|REST|GraphQL|WebSocket)$",  # Generic terms
        r"^\d+$",  # Numbers
    ]

    def __init__(self, knowledge_service=None):
        """
        Initialize the discovery agent.

        Args:
            knowledge_service: KnowledgeService instance for doc fetching.
                              If None, discovery still works but won't fetch docs.
        """
        self.knowledge_service = knowledge_service

    def extract_services(self, text: str) -> list[DiscoveredService]:
        """
        Extract external service names from text.

        Uses regex patterns and heuristics. Not perfect, but catches
        the common cases that lead to false assumptions.
        """
        services: dict[str, DiscoveredService] = {}

        for pattern, confidence in self.SERVICE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract the service name
                if match.lastindex:
                    name = match.group(1)
                else:
                    name = match.group(0)

                name = name.strip()

                # Skip false positives
                if self._is_false_positive(name):
                    continue

                # Get surrounding context (50 chars each side)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                # Use highest confidence if seen multiple times
                if name.lower() in services:
                    existing = services[name.lower()]
                    if confidence > existing.confidence:
                        existing.confidence = confidence
                        existing.context = context
                else:
                    services[name.lower()] = DiscoveredService(
                        name=name,
                        confidence=confidence,
                        context=context,
                    )

        # Sort by confidence descending
        return sorted(services.values(), key=lambda s: -s.confidence)

    def _is_false_positive(self, name: str) -> bool:
        """Check if a name is a false positive."""
        if len(name) < 2:
            return True

        for pattern in self.FALSE_POSITIVE_PATTERNS:
            if re.match(pattern, name, re.IGNORECASE):
                return True

        return False

    def fetch_service_docs(
        self,
        service: DiscoveredService,
        query: str = "overview architecture how it works",
    ) -> bool:
        """
        Fetch documentation for a discovered service.

        Args:
            service: The service to look up
            query: What to ask about the service

        Returns:
            True if docs were fetched successfully
        """
        if not self.knowledge_service:
            logger.warning("No knowledge service configured, skipping doc fetch")
            return False

        try:
            # Try to resolve the library
            library_id = self.knowledge_service.resolve_library(
                service.name,
                query,
            )

            if not library_id:
                service.doc_summary = f"Could not find documentation for {service.name}"
                return False

            # Fetch docs
            docs = self.knowledge_service.get_documentation(
                library_id,
                query,
            )

            if docs:
                service.doc_fetched = True
                service.doc_summary = docs[0][:1500]  # Truncate for context
                return True
            else:
                service.doc_summary = f"No documentation found for {library_id}"
                return False

        except Exception as e:
            logger.error(f"Error fetching docs for {service.name}: {e}")
            service.doc_summary = f"Error: {e}"
            return False

    def build_priming_context(
        self,
        services: list[DiscoveredService],
        include_unfetched: bool = True,
    ) -> str:
        """
        Build markdown context to inject into the debate.

        This gives models ground truth about external services
        instead of letting them assume.
        """
        if not services:
            return ""

        lines = [
            "## External Service Documentation (Ground Truth)",
            "",
            "**IMPORTANT**: The following documentation was fetched from official sources.",
            "Do NOT make assumptions about these services - refer to this documentation.",
            "",
        ]

        fetched = [s for s in services if s.doc_fetched]
        unfetched = [s for s in services if not s.doc_fetched]

        if fetched:
            for service in fetched:
                lines.append(f"### {service.name}")
                lines.append("")
                lines.append(service.doc_summary)
                lines.append("")

        if include_unfetched and unfetched:
            lines.append("### Services Without Documentation")
            lines.append("")
            lines.append("The following services were mentioned but documentation could not be fetched.")
            lines.append("**Treat all claims about these services as UNVERIFIED.**")
            lines.append("")
            for service in unfetched:
                lines.append(f"- **{service.name}**: {service.doc_summary or 'Not found'}")
            lines.append("")

        return "\n".join(lines)

    def discover(
        self,
        spec_text: str,
        min_confidence: float = 0.6,
        max_services: int = 5,
    ) -> DiscoveryResult:
        """
        Run the full discovery pipeline.

        Args:
            spec_text: The specification or user prompt
            min_confidence: Minimum confidence to include a service
            max_services: Maximum services to fetch docs for (to avoid token explosion)

        Returns:
            DiscoveryResult with services, context, and metadata
        """
        start_time = datetime.now()
        result = DiscoveryResult()

        # Extract services
        all_services = self.extract_services(spec_text)
        result.services = [s for s in all_services if s.confidence >= min_confidence]

        # Limit to top N for doc fetching
        services_to_fetch = result.services[:max_services]

        # Fetch docs for each
        for service in services_to_fetch:
            try:
                self.fetch_service_docs(service)
            except Exception as e:
                result.errors.append(f"Failed to fetch {service.name}: {e}")

        # Build priming context
        result.priming_context = self.build_priming_context(result.services)

        # Capture token usage if knowledge service is available
        if self.knowledge_service:
            result.token_usage = self.knowledge_service.get_token_usage_summary()

        result.discovery_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result


def run_discovery(
    spec_text: str,
    knowledge_service=None,
    min_confidence: float = 0.6,
    max_services: int = 5,
) -> DiscoveryResult:
    """
    Convenience function to run discovery.

    Args:
        spec_text: The specification text
        knowledge_service: Optional KnowledgeService for doc fetching
        min_confidence: Minimum confidence threshold
        max_services: Maximum services to fetch

    Returns:
        DiscoveryResult with priming context
    """
    agent = DiscoveryAgent(knowledge_service=knowledge_service)
    return agent.discover(
        spec_text,
        min_confidence=min_confidence,
        max_services=max_services,
    )


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/pre_gauntlet/context_builder.py (225 lines, 7905 bytes)
# ══════════════════════════════════════════════════════════════
"""
Context Builder

Builds the LLM context markdown from collected data.
"""

from __future__ import annotations

from datetime import datetime

from .models import (
    GitPosition,
    SystemState,
)


class ContextBuilder:
    """Builds LLM context markdown from pre-gauntlet data."""

    def __init__(self, max_chars: int = 200_000):
        self.max_chars = max_chars
        self.truncated_sections: list[str] = []

    def build(
        self,
        git_position: GitPosition | None,
        system_state: SystemState | None,
        spec_text: str,
    ) -> str:
        """Build the context markdown.

        Args:
            git_position: Git position data (optional)
            system_state: System state data (optional)
            spec_text: The specification text

        Returns:
            Formatted markdown context
        """
        sections = []

        # Header
        sections.append("# SYSTEM CONTEXT (GROUND TRUTH)")
        sections.append("")
        sections.append(
            "Trust this section over any assumptions. "
            "If the spec contradicts this, raise a COMP concern."
        )
        sections.append("")

        # Git Position
        if git_position:
            sections.append(self._build_git_section(git_position))

        # Baseline Health
        if system_state:
            sections.append(self._build_health_section(system_state))

        # Schema Snapshots
        if system_state and system_state.schema_contents:
            sections.append(self._build_schema_section(system_state))

        # Directory Trees
        if system_state and system_state.directory_trees:
            sections.append(self._build_tree_section(system_state))

        # Proposed Spec
        sections.append("## 5. Proposed Spec")
        sections.append("")
        sections.append(spec_text)

        # Join and truncate if needed
        result = "\n".join(sections)
        result = self._truncate_if_needed(result)

        return result

    def _build_git_section(self, pos: GitPosition) -> str:
        """Build the git position section."""
        lines = ["## 1. Git Position", ""]

        # Basic info
        lines.append(f"- Branch: {pos.current_branch} ({pos.commits_ahead} ahead, {pos.commits_behind} behind {pos.base_branch})")
        lines.append(f"- Head: {pos.head_commit[:12]}")

        # Last sync
        now = datetime.now(pos.last_sync_with_base.tzinfo) if pos.last_sync_with_base.tzinfo else datetime.now()
        days_ago = (now - pos.last_sync_with_base).days
        lines.append(f"- Last sync with {pos.base_branch}: {pos.last_sync_with_base.date()} ({days_ago} days ago)")

        # Working tree
        clean_status = "CLEAN" if pos.working_tree_clean else "DIRTY (uncommitted changes)"
        lines.append(f"- Working tree: {clean_status}")

        # Detached HEAD warning
        if pos.detached_head:
            lines.append("- WARNING: Detached HEAD state")

        # Recent commits on base if behind
        if pos.commits_behind > 0 and pos.main_recent_commits:
            lines.append("")
            lines.append(f"WARNING: {pos.base_branch} has {pos.commits_behind} new commit(s) since this branch diverged:")
            for commit in pos.main_recent_commits[: pos.commits_behind]:
                lines.append(f"  - {commit.hash[:7]}: \"{commit.subject}\"")

        # Affected files changed
        if pos.affected_files_changes:
            lines.append("")
            lines.append("CRITICAL: Spec-affected files have changed on base branch:")
            for fc in pos.affected_files_changes:
                lines.append(f"  - {fc.path} ({fc.status.value})")

        lines.append("")
        return "\n".join(lines)

    def _build_health_section(self, state: SystemState) -> str:
        """Build the baseline health section."""
        lines = ["## 2. Baseline Health", ""]

        status_str = state.build_status.value
        lines.append(f"- Build Status: {status_str}")

        if state.build_exit_code is not None:
            lines.append(f"- Exit Code: {state.build_exit_code}")

        if state.build_duration_ms > 0:
            lines.append(f"- Duration: {state.build_duration_ms}ms")

        if state.build_output_excerpt:
            lines.append("- Output (redacted):")
            lines.append("```")
            lines.append(state.build_output_excerpt)
            lines.append("```")

        # Validation results
        if state.validation_results:
            lines.append("")
            lines.append("### Validation Checks")

            # Check if any validations are missing environment specification
            missing_env = [v for v in state.validation_results if not v.environment]
            if missing_env:
                lines.append("")
                lines.append("⚠️ **WARNING: Some validations have no environment specified.**")
                lines.append("Verify these are running against the correct instance (production vs development).")
                lines.append("")

            for val in state.validation_results:
                status_icon = "✅ PASS" if val.status.value == "PASS" else "❌ FAIL"
                env_label = f" [{val.environment}]" if val.environment else " [ENV: UNKNOWN]"
                lines.append(f"- **{val.name}**{env_label}: {status_icon}")
                if val.description:
                    lines.append(f"  - {val.description}")
                if val.status.value != "PASS" and val.output_excerpt:
                    lines.append("  - Output:")
                    lines.append("  ```")
                    for line in val.output_excerpt.split("\n")[:10]:  # First 10 lines
                        lines.append(f"  {line}")
                    lines.append("  ```")

        lines.append("")
        return "\n".join(lines)

    def _build_schema_section(self, state: SystemState) -> str:
        """Build the schema snapshots section."""
        lines = ["## 3. Schema Snapshots", ""]

        for snapshot in state.schema_contents:
            lines.append(f"### {snapshot.path} (sha256: {snapshot.sha256[:16]}...)")
            if snapshot.truncated:
                lines.append("*[TRUNCATED]*")
            lines.append("```")
            lines.append(snapshot.content)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _build_tree_section(self, state: SystemState) -> str:
        """Build the directory trees section."""
        lines = ["## 4. Directory Trees", ""]

        for tree in state.directory_trees:
            lines.append(f"### {tree.path}")
            if tree.truncated:
                lines.append("*[TRUNCATED]*")
            lines.append("```")
            lines.append(tree.tree)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _truncate_if_needed(self, text: str) -> str:
        """Truncate text if it exceeds max_chars."""
        if len(text) <= self.max_chars:
            return text

        # Truncate from end, preserving structure
        truncated = text[: self.max_chars]

        # Find last complete section
        last_section = truncated.rfind("\n## ")
        if last_section > self.max_chars // 2:
            truncated = truncated[:last_section]

        truncated += "\n\n... [CONTEXT TRUNCATED DUE TO SIZE]"
        self.truncated_sections.append("FULL_CONTEXT")

        return truncated


def build_context(
    git_position: GitPosition | None,
    system_state: SystemState | None,
    spec_text: str,
    max_chars: int = 200_000,
) -> tuple[str, list[str]]:
    """Convenience function to build context.

    Returns: (context_markdown, truncated_sections)
    """
    builder = ContextBuilder(max_chars=max_chars)
    context = builder.build(git_position, system_state, spec_text)
    return context, builder.truncated_sections


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/pre_gauntlet/alignment_mode.py (201 lines, 6687 bytes)
# ══════════════════════════════════════════════════════════════
"""
Alignment Mode

Interactive and non-interactive alignment flow when blockers are detected.
"""

from __future__ import annotations

import sys
from enum import Enum

from .models import (
    AlignmentIssue,
    AlignmentResolution,
    AlignmentStatus,
    Concern,
    PreGauntletResult,
    PreGauntletStatus,
)


class AlignmentChoice(Enum):
    """User choice in alignment mode."""

    FIX_CODE = "f"
    UPDATE_SPEC = "u"
    IGNORE = "i"
    QUIT = "q"


# Required confirmation token for ignore
IGNORE_CONFIRMATION = "I KNOW THIS WILL BREAK"


class AlignmentModeController:
    """Controls the alignment mode flow."""

    def __init__(self, interactive: bool = True):
        """Initialize alignment mode controller.

        Args:
            interactive: If True, prompt user. If False, return NEEDS_ALIGNMENT.
        """
        self.interactive = interactive

    def handle_blockers(
        self,
        blockers: list[Concern],
        result: PreGauntletResult,
    ) -> tuple[PreGauntletStatus, list[AlignmentIssue]]:
        """Handle blocker concerns.

        Args:
            blockers: List of BLOCKER severity concerns
            result: Current pre-gauntlet result

        Returns:
            (status, alignment_issues)
        """
        if not blockers:
            return PreGauntletStatus.COMPLETE, []

        # Create alignment issues for each blocker
        issues = [
            AlignmentIssue(
                concern_id=b.id,
                status=AlignmentStatus.UNRESOLVED,
            )
            for b in blockers
        ]

        # Non-interactive mode
        if not self.interactive or not sys.stdin.isatty():
            return PreGauntletStatus.NEEDS_ALIGNMENT, issues

        # Interactive mode
        return self._interactive_flow(blockers, issues)

    def _interactive_flow(
        self,
        blockers: list[Concern],
        issues: list[AlignmentIssue],
    ) -> tuple[PreGauntletStatus, list[AlignmentIssue]]:
        """Run interactive alignment flow."""
        self._print_header()
        self._print_blockers(blockers)
        self._print_options()

        while True:
            choice = self._get_choice()

            if choice == AlignmentChoice.QUIT:
                return PreGauntletStatus.ABORTED, issues

            if choice == AlignmentChoice.FIX_CODE:
                print("\nPausing gauntlet. Fix the issues in the codebase, then re-run.")
                print("When ready, run the gauntlet again with --pre-gauntlet")
                return PreGauntletStatus.NEEDS_ALIGNMENT, issues

            if choice == AlignmentChoice.UPDATE_SPEC:
                print("\nPausing gauntlet. Update the spec to match the current codebase state.")
                print("When ready, run the gauntlet again with --pre-gauntlet")
                return PreGauntletStatus.NEEDS_ALIGNMENT, issues

            if choice == AlignmentChoice.IGNORE:
                if self._confirm_ignore():
                    # Mark all issues as overridden
                    for issue in issues:
                        issue.status = AlignmentStatus.OVERRIDDEN
                        issue.resolution = AlignmentResolution.IGNORE
                    return PreGauntletStatus.COMPLETE, issues
                # User didn't confirm, go back to menu
                self._print_options()

    def _print_header(self) -> None:
        """Print alignment mode header."""
        print("\n" + "=" * 60)
        print("ALIGNMENT MODE: Drift detected between spec and codebase")
        print("=" * 60)
        print()
        print("The following issues require resolution before proceeding:")
        print()

    def _print_blockers(self, blockers: list[Concern]) -> None:
        """Print blocker concerns."""
        for b in blockers:
            print(f"  {b.id}: {b.title} [BLOCKER]")
            # Print message indented
            for line in b.message.split("\n")[:5]:  # First 5 lines
                print(f"    {line}")
            if len(b.message.split("\n")) > 5:
                print("    ...")
            print()

    def _print_options(self) -> None:
        """Print available options."""
        print("Options:")
        print("  [f] Fix codebase - Pause gauntlet, fix the issues, then re-check")
        print("  [u] Update spec  - Edit the spec to match current codebase state")
        print("  [i] Ignore       - Force proceed (DANGEROUS - requires confirmation)")
        print("  [q] Quit         - Exit gauntlet without proceeding")
        print()

    def _get_choice(self) -> AlignmentChoice:
        """Get user's choice."""
        while True:
            try:
                choice = input("Choice [f/u/i/q]: ").strip().lower()
                if choice in ("f", "u", "i", "q"):
                    return AlignmentChoice(choice)
                print("Invalid choice. Please enter f, u, i, or q.")
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return AlignmentChoice.QUIT

    def _confirm_ignore(self) -> bool:
        """Confirm ignore action with explicit token."""
        print()
        print("WARNING: Ignoring these issues may cause:")
        print("  - Implementation to fail")
        print("  - Spec to be based on incorrect assumptions")
        print("  - Wasted effort on code that won't work")
        print()
        print(f"To proceed anyway, type exactly: {IGNORE_CONFIRMATION}")
        print()

        try:
            confirmation = input("Confirmation: ").strip()
            if confirmation == IGNORE_CONFIRMATION:
                print("\nProceeding with override. alignment_override=true recorded.")
                return True
            else:
                print("\nConfirmation did not match. Returning to menu.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return False


def run_alignment_mode(
    blockers: list[Concern],
    result: PreGauntletResult,
    interactive: bool = True,
) -> tuple[PreGauntletStatus, list[AlignmentIssue], bool]:
    """Run alignment mode for blocker concerns.

    Args:
        blockers: List of BLOCKER severity concerns
        result: Current pre-gauntlet result
        interactive: Whether to prompt user

    Returns:
        (status, alignment_issues, was_overridden)
    """
    controller = AlignmentModeController(interactive=interactive)
    status, issues = controller.handle_blockers(blockers, result)

    # Check if any issues were overridden
    was_overridden = any(i.status == AlignmentStatus.OVERRIDDEN for i in issues)

    return status, issues, was_overridden


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/collectors/__init__.py (13 lines, 244 bytes)
# ══════════════════════════════════════════════════════════════
"""
Collectors Module

Data collectors for git position and system state.
"""

from .git_position import GitPositionCollector
from .system_state import SystemStateCollector

__all__ = [
    "GitPositionCollector",
    "SystemStateCollector",
]


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/collectors/git_position.py (258 lines, 9555 bytes)
# ══════════════════════════════════════════════════════════════
"""
Git Position Collector

Collects git repository position and staleness information.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.git_cli import GitCli
from pre_gauntlet.models import (
    CommitSummary,
    Concern,
    ConcernCategory,
    ConcernSeverity,
    EvidenceRef,
    EvidenceType,
    FileChange,
    FileChangeStatus,
    GitPosition,
)


class GitPositionCollector:
    """Collects git position and generates staleness concerns."""

    def __init__(
        self,
        repo_root: str | Path,
        base_branch: str = "main",
        staleness_threshold_days: int = 3,
        spec_affected_files: list[str] | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.base_branch = base_branch
        self.staleness_threshold_days = staleness_threshold_days
        self.spec_affected_files = set(spec_affected_files or [])

        self.git = GitCli(repo_root)

    def collect(self) -> tuple[GitPosition, list[Concern]]:
        """Collect git position and generate concerns.

        Returns: (GitPosition, list of Concern)
        """
        concerns: list[Concern] = []

        # Check if base branch exists
        if not self.git.branch_exists(self.base_branch):
            raise GitCliError(f"Base branch '{self.base_branch}' does not exist")

        # Get basic position info
        current_branch = self.git.get_current_branch()
        head_commit = self.git.get_head_commit()
        base_commit = self.git.get_branch_commit(self.base_branch)
        merge_base = self.git.get_merge_base(self.base_branch)
        detached = self.git.is_detached_head()
        working_clean = self.git.is_working_tree_clean()

        # Get ahead/behind counts
        commits_ahead, commits_behind = self.git.get_commits_ahead_behind(self.base_branch)

        # Get merge base date
        last_sync = self.git.get_commit_date(merge_base)

        # Get recent commits on base branch
        recent_commits_raw = self.git.get_recent_commits(self.base_branch, count=10)
        recent_commits = [
            CommitSummary(
                hash=c["hash"],
                author=c["author"],
                date=c["date"],
                subject=c["subject"],
            )
            for c in recent_commits_raw
        ]

        # Get changed files
        changed_files_raw = self.git.get_changed_files(self.base_branch)
        all_changed = [
            FileChange(
                path=f["path"],
                status=FileChangeStatus(f["status"]),
            )
            for f in changed_files_raw
        ]

        # Filter to spec-affected files
        affected_changes = []
        if self.spec_affected_files:
            for fc in all_changed:
                if fc.path in self.spec_affected_files:
                    affected_changes.append(fc)

        # Build position object
        position = GitPosition(
            current_branch=current_branch,
            head_commit=head_commit,
            base_branch=self.base_branch,
            base_commit=base_commit,
            merge_base_commit=merge_base,
            commits_ahead=commits_ahead,
            commits_behind=commits_behind,
            last_sync_with_base=last_sync,
            main_recent_commits=recent_commits,
            affected_files_changes=affected_changes,
            working_tree_clean=working_clean,
            detached_head=detached,
        )

        # Generate concerns
        concerns.extend(self._generate_concerns(position))

        return position, concerns

    def _generate_concerns(self, position: GitPosition) -> list[Concern]:
        """Generate concerns based on git position."""
        concerns = []

        # Detached HEAD warning
        if position.detached_head:
            concerns.append(
                Concern(
                    id=self._make_id("GIT_DETACHED"),
                    severity=ConcernSeverity.WARN,
                    category=ConcernCategory.GIT,
                    title="Detached HEAD State",
                    message=(
                        "Repository is in detached HEAD state. "
                        "Commits may not be associated with a branch."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source="git rev-parse --abbrev-ref HEAD",
                            excerpt="HEAD",
                        )
                    ],
                )
            )

        # Commits behind warning
        if position.commits_behind > 0:
            # Get commit subjects for evidence
            commit_subjects = "\n".join(
                f"  - {c.hash[:7]}: {c.subject}"
                for c in position.main_recent_commits[:position.commits_behind]
            )

            concerns.append(
                Concern(
                    id=self._make_id("GIT_STALE"),
                    severity=ConcernSeverity.WARN,
                    category=ConcernCategory.GIT,
                    title=f"Branch Behind {position.base_branch}",
                    message=(
                        f"Current branch is {position.commits_behind} commit(s) behind "
                        f"{position.base_branch}. Recent commits:\n{commit_subjects}"
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source=f"git rev-list --count {position.base_branch}...HEAD",
                            excerpt=f"{position.commits_behind} commits behind",
                        )
                    ],
                )
            )

        # Staleness time warning
        # Handle timezone-aware vs naive datetime comparison
        now = datetime.now(position.last_sync_with_base.tzinfo) if position.last_sync_with_base.tzinfo else datetime.now()
        days_since_sync = (now - position.last_sync_with_base).days
        if days_since_sync > self.staleness_threshold_days:
            concerns.append(
                Concern(
                    id=self._make_id("GIT_STALE_TIME"),
                    severity=ConcernSeverity.WARN,
                    category=ConcernCategory.GIT,
                    title=f"Branch Stale ({days_since_sync} days)",
                    message=(
                        f"Last sync with {position.base_branch} was {days_since_sync} days ago "
                        f"(threshold: {self.staleness_threshold_days} days). "
                        "Consider rebasing to get latest changes."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source=f"git merge-base HEAD {position.base_branch}",
                            excerpt=position.last_sync_with_base.isoformat(),
                        )
                    ],
                )
            )

        # Affected files changed - BLOCKER
        if position.affected_files_changes:
            file_list = "\n".join(
                f"  - {fc.path} ({fc.status.value})"
                for fc in position.affected_files_changes
            )
            concerns.append(
                Concern(
                    id=self._make_id("GIT_AFFECTED_FILES_CHANGED"),
                    severity=ConcernSeverity.BLOCKER,
                    category=ConcernCategory.GIT,
                    title="Spec-Affected Files Changed on Base Branch",
                    message=(
                        f"Files referenced by the spec have changed on {position.base_branch} "
                        f"since this branch diverged:\n{file_list}\n\n"
                        "The spec may be based on stale understanding. ALIGNMENT MODE required."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source=f"git diff --name-status {position.base_branch}...HEAD",
                            excerpt=file_list,
                        )
                    ],
                )
            )

        # Dirty working tree warning
        if not position.working_tree_clean:
            concerns.append(
                Concern(
                    id=self._make_id("GIT_DIRTY"),
                    severity=ConcernSeverity.WARN,
                    category=ConcernCategory.GIT,
                    title="Uncommitted Changes",
                    message=(
                        "Working tree has uncommitted changes. "
                        "Baseline verification may not reflect committed state."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source="git status --porcelain",
                            excerpt="(non-empty output)",
                        )
                    ],
                )
            )

        return concerns

    def _make_id(self, suffix: str) -> str:
        """Generate a concern ID."""
        import hashlib
        content = f"{suffix}:{self.base_branch}:{self.repo_root}"
        hash_val = hashlib.sha1(content.encode()).hexdigest()[:8]
        return f"COMP-{hash_val}"


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/collectors/system_state.py (408 lines, 15310 bytes)
# ══════════════════════════════════════════════════════════════
"""
System State Collector

Collects build status, schema files, and directory trees.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.process_runner import ProcessRunner
from pre_gauntlet.models import (
    BuildStatus,
    DirectoryTree,
    FileSnapshot,
    SystemState,
    ValidationCommand,
    ValidationResult,
)


class SystemStateCollector:
    """Collects system state including build status, schemas, and trees."""

    def __init__(
        self,
        repo_root: str | Path,
        build_command: list[str] | None = None,
        build_timeout: int = 60,
        validation_commands: list[ValidationCommand] | None = None,
        schema_files: list[str] | None = None,
        critical_paths: list[str] | None = None,
        file_max_bytes: int = 200_000,
        tree_max_depth: int = 6,
        tree_max_entries: int = 5000,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.build_command = build_command
        self.build_timeout = build_timeout
        self.validation_commands = validation_commands or []
        self.schema_files = schema_files or []
        self.critical_paths = critical_paths or []
        self.file_max_bytes = file_max_bytes
        self.tree_max_depth = tree_max_depth
        self.tree_max_entries = tree_max_entries

        self.runner = ProcessRunner(repo_root, default_timeout=build_timeout)

    def collect(self) -> tuple[SystemState, list[Concern]]:
        """Collect system state and generate concerns.

        Returns: (SystemState, list of Concern)
        """
        concerns: list[Concern] = []
        collection_time = datetime.now()

        # Run build command
        build_status, build_exit, build_duration, build_output = self._run_build()
        if build_status in (BuildStatus.FAIL, BuildStatus.TIMEOUT):
            concerns.append(self._make_build_concern(build_status, build_output))

        # Run validation commands (schema/data consistency checks)
        validation_results, validation_concerns = self._run_validations()
        concerns.extend(validation_concerns)

        # Read schema files
        schema_contents, schema_concerns = self._read_schema_files()
        concerns.extend(schema_concerns)

        # Generate directory trees
        directory_trees = self._generate_trees()

        # Check working tree (via git status - reuse info)
        working_clean = self._check_working_tree()

        state = SystemState(
            build_status=build_status,
            build_exit_code=build_exit,
            build_duration_ms=build_duration,
            build_output_excerpt=build_output,
            validation_results=validation_results,
            schema_contents=schema_contents,
            directory_trees=directory_trees,
            working_tree_clean=working_clean,
            collection_timestamp=collection_time,
        )

        return state, concerns

    def _run_build(self) -> tuple[BuildStatus, int | None, int, str]:
        """Run the build command.

        Returns: (status, exit_code, duration_ms, output)
        """
        if not self.build_command:
            return BuildStatus.SKIP, None, 0, ""

        result = self.runner.run(self.build_command, timeout=self.build_timeout)

        if result.timed_out:
            return BuildStatus.TIMEOUT, None, result.duration_ms, result.stderr

        if result.success:
            return BuildStatus.PASS, result.exit_code, result.duration_ms, ""

        # Build failed - combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output = f"{output}\n{result.stderr}" if output else result.stderr

        return BuildStatus.FAIL, result.exit_code, result.duration_ms, output

    def _make_build_concern(self, status: BuildStatus, output: str) -> Concern:
        """Create a concern for build failure."""
        if status == BuildStatus.TIMEOUT:
            return Concern(
                id=self._make_id("BUILD_TIMEOUT"),
                severity=ConcernSeverity.BLOCKER,
                category=ConcernCategory.BUILD,
                title="Build Command Timed Out",
                message=(
                    f"Build command `{' '.join(self.build_command or [])}` "
                    f"timed out after {self.build_timeout}s. "
                    "Baseline health cannot be verified."
                ),
                evidence_refs=[
                    EvidenceRef(
                        type=EvidenceType.COMMAND_OUTPUT,
                        source=" ".join(self.build_command or []),
                        excerpt=f"Timeout after {self.build_timeout}s",
                    )
                ],
            )

        # Truncate output for display
        output_excerpt = output[:2000] if len(output) > 2000 else output

        return Concern(
            id=self._make_id("BUILD_FAILURE"),
            severity=ConcernSeverity.BLOCKER,
            category=ConcernCategory.BUILD,
            title="Baseline Build Fails",
            message=(
                f"Build command `{' '.join(self.build_command or [])}` failed. "
                "The codebase cannot be deployed in its current state. "
                "This blocks ALL implementation work.\n\n"
                f"Output:\n```\n{output_excerpt}\n```"
            ),
            evidence_refs=[
                EvidenceRef(
                    type=EvidenceType.COMMAND_OUTPUT,
                    source=" ".join(self.build_command or []),
                    excerpt=output_excerpt,
                )
            ],
        )

    def _run_validations(self) -> tuple[list[ValidationResult], list[Concern]]:
        """Run validation commands and generate concerns for failures.

        Returns: (list of ValidationResult, list of Concern)
        """
        results = []
        concerns = []

        for val_cmd in self.validation_commands:
            result = self.runner.run(val_cmd.command, timeout=val_cmd.timeout_seconds)

            # Determine status
            if result.timed_out:
                status = BuildStatus.TIMEOUT
            elif result.success:
                status = BuildStatus.PASS
            else:
                status = BuildStatus.FAIL

            # Combine output
            output = result.stdout
            if result.stderr:
                output = f"{output}\n{result.stderr}" if output else result.stderr
            output_excerpt = output[:2000] if len(output) > 2000 else output

            val_result = ValidationResult(
                name=val_cmd.name,
                command=val_cmd.command,
                status=status,
                exit_code=result.exit_code if not result.timed_out else None,
                duration_ms=result.duration_ms,
                output_excerpt=output_excerpt,
                description=val_cmd.description,
                environment=val_cmd.environment,
            )
            results.append(val_result)

            # Generate concern if failed
            if status in (BuildStatus.FAIL, BuildStatus.TIMEOUT):
                concerns.append(self._make_validation_concern(val_cmd, val_result))

        return results, concerns

    def _make_validation_concern(
        self, cmd: ValidationCommand, result: ValidationResult
    ) -> Concern:
        """Create a concern for validation failure."""
        cmd_str = " ".join(cmd.command)
        env_note = f" [Environment: {cmd.environment}]" if cmd.environment else " [Environment: UNKNOWN - consider specifying]"

        if result.status == BuildStatus.TIMEOUT:
            return Concern(
                id=self._make_id(f"VALIDATION_TIMEOUT_{cmd.name}"),
                severity=ConcernSeverity.BLOCKER,
                category=ConcernCategory.SCHEMA,
                title=f"Validation Timed Out: {cmd.name}{env_note}",
                message=(
                    f"Validation command `{cmd_str}` timed out after {cmd.timeout_seconds}s.\n"
                    f"Environment: **{cmd.environment or 'NOT SPECIFIED'}**\n"
                    f"Description: {cmd.description or 'Schema/data validation'}\n\n"
                    "⚠️ If no environment is specified, verify you are validating against "
                    "the correct instance (production vs development)."
                ),
                evidence_refs=[
                    EvidenceRef(
                        type=EvidenceType.COMMAND_OUTPUT,
                        source=cmd_str,
                        excerpt=f"Timeout after {cmd.timeout_seconds}s",
                    )
                ],
            )

        # Validation failed
        return Concern(
            id=self._make_id(f"VALIDATION_FAILED_{cmd.name}"),
            severity=ConcernSeverity.BLOCKER,
            category=ConcernCategory.SCHEMA,
            title=f"Validation Failed: {cmd.name}{env_note}",
            message=(
                f"Validation command `{cmd_str}` failed.\n"
                f"Environment: **{cmd.environment or 'NOT SPECIFIED'}**\n"
                f"Description: {cmd.description or 'Schema/data validation'}\n\n"
                "This indicates schema/data drift - the schema definition does not match "
                "the actual data state. This must be resolved before implementation.\n\n"
                "⚠️ **IMPORTANT**: Before investigating, verify this validation ran against "
                "the correct environment. Failures against development instances may be "
                "false positives if production is the deployment target.\n\n"
                f"Output:\n```\n{result.output_excerpt}\n```"
            ),
            evidence_refs=[
                EvidenceRef(
                    type=EvidenceType.COMMAND_OUTPUT,
                    source=cmd_str,
                    excerpt=result.output_excerpt,
                )
            ],
        )

    def _read_schema_files(self) -> tuple[list[FileSnapshot], list[Concern]]:
        """Read schema files and generate concerns for missing ones.

        Returns: (list of FileSnapshot, list of Concern)
        """
        snapshots = []
        concerns = []

        for schema_path in self.schema_files:
            full_path = self.repo_root / schema_path

            if not full_path.exists():
                concerns.append(
                    Concern(
                        id=self._make_id(f"SCHEMA_MISSING_{schema_path}"),
                        severity=ConcernSeverity.BLOCKER,
                        category=ConcernCategory.SCHEMA,
                        title=f"Schema File Missing: {schema_path}",
                        message=(
                            f"Required schema file `{schema_path}` does not exist. "
                            "Cannot verify schema compatibility."
                        ),
                        evidence_refs=[
                            EvidenceRef(
                                type=EvidenceType.FILE_CONTENT,
                                source=schema_path,
                                excerpt="File not found",
                            )
                        ],
                    )
                )
                continue

            try:
                content = full_path.read_text()
                truncated = False

                if len(content) > self.file_max_bytes:
                    content = content[: self.file_max_bytes]
                    truncated = True

                # Calculate SHA256
                sha = hashlib.sha256(full_path.read_bytes()).hexdigest()

                snapshots.append(
                    FileSnapshot(
                        path=schema_path,
                        sha256=sha,
                        content=content,
                        truncated=truncated,
                    )
                )

            except Exception as e:
                concerns.append(
                    Concern(
                        id=self._make_id(f"SCHEMA_READ_ERROR_{schema_path}"),
                        severity=ConcernSeverity.WARN,
                        category=ConcernCategory.SCHEMA,
                        title=f"Schema File Unreadable: {schema_path}",
                        message=f"Could not read schema file `{schema_path}`: {e}",
                        evidence_refs=[
                            EvidenceRef(
                                type=EvidenceType.FILE_CONTENT,
                                source=schema_path,
                                excerpt=str(e),
                            )
                        ],
                    )
                )

        return snapshots, concerns

    def _generate_trees(self) -> list[DirectoryTree]:
        """Generate directory trees for critical paths."""
        trees = []

        for path in self.critical_paths:
            full_path = self.repo_root / path

            if not full_path.exists():
                continue

            tree_output, truncated = self._generate_tree(full_path)
            trees.append(
                DirectoryTree(
                    path=path,
                    tree=tree_output,
                    truncated=truncated,
                )
            )

        return trees

    def _generate_tree(self, path: Path, prefix: str = "", depth: int = 0) -> tuple[str, bool]:
        """Generate a tree structure for a directory.

        Returns: (tree_string, was_truncated)
        """
        if depth >= self.tree_max_depth:
            return f"{prefix}... [max depth reached]\n", True

        lines = []
        truncated = False
        entries = 0

        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return f"{prefix}[permission denied]\n", False

        for i, item in enumerate(items):
            entries += 1
            if entries > self.tree_max_entries:
                lines.append(f"{prefix}... [{len(items) - i} more entries]\n")
                truncated = True
                break

            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{item.name}\n")

            if item.is_dir():
                extension = "    " if is_last else "│   "
                subtree, sub_truncated = self._generate_tree(
                    item, prefix + extension, depth + 1
                )
                lines.append(subtree)
                truncated = truncated or sub_truncated

        return "".join(lines), truncated

    def _check_working_tree(self) -> bool:
        """Check if working tree is clean via git status."""
        result = self.runner.run(["git", "status", "--porcelain"], validate=False)
        return result.success and len(result.stdout.strip()) == 0

    def _make_id(self, suffix: str) -> str:
        """Generate a concern ID."""
        content = f"{suffix}:{self.repo_root}"
        hash_val = hashlib.sha1(content.encode()).hexdigest()[:8]
        return f"COMP-{hash_val}"


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/integrations/__init__.py (46 lines, 908 bytes)
# ══════════════════════════════════════════════════════════════
"""
Integrations Module

External system integrations (git, process execution, knowledge/docs).
"""

from .git_cli import GitCli, GitCliError, GitCommandResult
from .knowledge_service import (
    DocCacheEntry,
    DocChunk,
    EvidenceItem,
    KnowledgeService,
    TokenUsageLog,
    VerificationStatus,
)
from .process_runner import (
    CommandValidationError,
    ProcessResult,
    ProcessRunner,
    ProcessRunnerError,
    redact_secrets,
    truncate_output,
    validate_command,
)

__all__ = [
    # Git
    "GitCli",
    "GitCliError",
    "GitCommandResult",
    # Knowledge/Docs
    "DocCacheEntry",
    "DocChunk",
    "EvidenceItem",
    "KnowledgeService",
    "TokenUsageLog",
    "VerificationStatus",
    # Process
    "CommandValidationError",
    "ProcessResult",
    "ProcessRunner",
    "ProcessRunnerError",
    "redact_secrets",
    "truncate_output",
    "validate_command",
]


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/integrations/git_cli.py (220 lines, 7532 bytes)
# ══════════════════════════════════════════════════════════════
"""
Git CLI Integration

All git command execution and parsing. Read-only operations only.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class GitCommandResult:
    """Result of a git command execution."""

    success: bool
    stdout: str
    stderr: str
    return_code: int


class GitCliError(Exception):
    """Error executing git command."""

    def __init__(self, message: str, result: GitCommandResult | None = None):
        super().__init__(message)
        self.result = result


class GitCli:
    """Git command line interface wrapper. Read-only operations only."""

    def __init__(self, repo_root: str | Path, timeout: int = 30):
        self.repo_root = Path(repo_root).resolve()
        self.timeout = timeout

        # Verify git is available
        if not self._check_git_available():
            raise GitCliError("Git is not available in PATH")

        # Verify this is a git repository
        if not self._is_git_repo():
            raise GitCliError(f"Not a git repository: {self.repo_root}")

    def _check_git_available(self) -> bool:
        """Check if git is available."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _is_git_repo(self) -> bool:
        """Check if repo_root is a git repository."""
        result = self._run(["rev-parse", "--git-dir"])
        return result.success

    def _run(self, args: list[str]) -> GitCommandResult:
        """Run a git command and return the result."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return GitCommandResult(
                success=result.returncode == 0,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return GitCommandResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                return_code=-1,
            )

    def get_current_branch(self) -> str:
        """Get the current branch name, or 'HEAD' if detached."""
        result = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
        if not result.success:
            raise GitCliError("Failed to get current branch", result)
        return result.stdout

    def get_head_commit(self) -> str:
        """Get the HEAD commit hash."""
        result = self._run(["rev-parse", "HEAD"])
        if not result.success:
            raise GitCliError("Failed to get HEAD commit", result)
        return result.stdout

    def get_branch_commit(self, branch: str) -> str:
        """Get the commit hash for a branch."""
        result = self._run(["rev-parse", branch])
        if not result.success:
            raise GitCliError(f"Failed to get commit for branch '{branch}'", result)
        return result.stdout

    def get_merge_base(self, branch: str) -> str:
        """Get the merge base between HEAD and a branch."""
        result = self._run(["merge-base", "HEAD", branch])
        if not result.success:
            raise GitCliError(f"Failed to get merge base with '{branch}'", result)
        return result.stdout

    def get_commits_ahead_behind(self, base_branch: str) -> tuple[int, int]:
        """Get commits ahead and behind relative to base branch.

        Returns: (commits_ahead, commits_behind)
        """
        result = self._run(["rev-list", "--left-right", "--count", f"{base_branch}...HEAD"])
        if not result.success:
            raise GitCliError(f"Failed to get ahead/behind count for '{base_branch}'", result)

        parts = result.stdout.split()
        if len(parts) != 2:
            raise GitCliError(f"Unexpected output format: {result.stdout}", result)

        return int(parts[1]), int(parts[0])  # ahead, behind

    def get_recent_commits(self, branch: str, count: int = 10) -> list[dict]:
        """Get recent commits on a branch.

        Returns list of dicts with: hash, author, date, subject
        """
        # Format: hash|ISO date|author|subject
        result = self._run([
            "log",
            "-n", str(count),
            "--format=%H|%aI|%an|%s",
            branch,
        ])
        if not result.success:
            # Branch might not exist or have no commits
            return []

        commits = []
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "date": datetime.fromisoformat(parts[1]),
                    "author": parts[2],
                    "subject": parts[3],
                })
        return commits

    def get_commit_date(self, commit: str) -> datetime:
        """Get the date of a commit."""
        result = self._run(["log", "-1", "--format=%aI", commit])
        if not result.success:
            raise GitCliError(f"Failed to get date for commit '{commit}'", result)
        return datetime.fromisoformat(result.stdout)

    def get_changed_files(self, base_branch: str) -> list[dict]:
        """Get files changed between base branch and HEAD.

        Returns list of dicts with: path, status (A/M/D/R)
        """
        result = self._run(["diff", "--name-status", f"{base_branch}...HEAD"])
        if not result.success:
            return []

        files = []
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status = parts[0][0]  # First char (R100 -> R)
                path = parts[1]
                files.append({"path": path, "status": status})
        return files

    def is_working_tree_clean(self) -> bool:
        """Check if the working tree is clean (no uncommitted changes)."""
        result = self._run(["status", "--porcelain"])
        if not result.success:
            return False
        return len(result.stdout) == 0

    def is_detached_head(self) -> bool:
        """Check if HEAD is detached."""
        branch = self.get_current_branch()
        return branch == "HEAD"

    def list_files(self, include_untracked: bool = False) -> list[str]:
        """List all tracked files in the repository."""
        result = self._run(["ls-files"])
        if not result.success:
            return []

        files = [f for f in result.stdout.split("\n") if f.strip()]

        if include_untracked:
            untracked_result = self._run(["ls-files", "--others", "--exclude-standard"])
            if untracked_result.success:
                files.extend([f for f in untracked_result.stdout.split("\n") if f.strip()])

        return files

    def branch_exists(self, branch: str) -> bool:
        """Check if a branch exists."""
        result = self._run(["rev-parse", "--verify", branch])
        return result.success


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/integrations/knowledge_service.py (483 lines, 16724 bytes)
# ══════════════════════════════════════════════════════════════
"""
Knowledge Service - Context7 Integration with Caching

Provides documentation lookup via Context7 MCP tools with:
- Local filesystem caching (24h TTL default)
- Soft token limits with tracking (not hard caps)
- Evidence logging for assumption verification
"""

from __future__ import annotations

import gzip
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Status of a claim verification against documentation."""
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNVERIFIABLE = "unverifiable"
    PENDING = "pending"


@dataclass
class DocChunk:
    """A chunk of documentation content."""
    content: str
    token_estimate: int  # Rough estimate: len/4
    source_query: str
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class DocCacheEntry:
    """Cached documentation for a library."""
    library_id: str
    library_name: str
    fetched_at: datetime
    expires_at: datetime
    chunks: list[DocChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def total_tokens(self) -> int:
        return sum(c.token_estimate for c in self.chunks)

    def to_dict(self) -> dict:
        return {
            "library_id": self.library_id,
            "library_name": self.library_name,
            "fetched_at": self.fetched_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "chunks": [
                {
                    "content": c.content,
                    "token_estimate": c.token_estimate,
                    "source_query": c.source_query,
                    "fetched_at": c.fetched_at.isoformat(),
                }
                for c in self.chunks
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DocCacheEntry:
        return cls(
            library_id=data["library_id"],
            library_name=data["library_name"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            chunks=[
                DocChunk(
                    content=c["content"],
                    token_estimate=c["token_estimate"],
                    source_query=c["source_query"],
                    fetched_at=datetime.fromisoformat(c["fetched_at"]),
                )
                for c in data.get("chunks", [])
            ],
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvidenceItem:
    """Evidence for or against a claim."""
    claim_id: str
    claim_text: str
    source_library: str
    verification_status: VerificationStatus
    supporting_text: str  # Quote from docs
    context7_query: str  # Query used to find this
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "source_library": self.source_library,
            "verification_status": self.verification_status.value,
            "supporting_text": self.supporting_text,
            "context7_query": self.context7_query,
            "checked_at": self.checked_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> EvidenceItem:
        return cls(
            claim_id=data["claim_id"],
            claim_text=data["claim_text"],
            source_library=data["source_library"],
            verification_status=VerificationStatus(data["verification_status"]),
            supporting_text=data["supporting_text"],
            context7_query=data["context7_query"],
            checked_at=datetime.fromisoformat(data["checked_at"]),
        )


@dataclass
class TokenUsageLog:
    """Tracks token usage for soft limit monitoring."""
    query: str
    library_id: str
    tokens_fetched: int
    soft_limit: int
    exceeded: bool
    timestamp: datetime = field(default_factory=datetime.now)


class KnowledgeService:
    """
    Manages documentation lookup via Context7 with caching.

    Uses soft limits with tracking - logs when limits are exceeded
    but doesn't block the operation. This allows review of whether
    limits need adjustment.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_hours: int = 24,
        soft_token_limit: int = 2000,
        context7_resolve: Callable | None = None,
        context7_query: Callable | None = None,
    ):
        """
        Initialize the knowledge service.

        Args:
            cache_dir: Where to store cached docs. Default: ~/.cache/adversarial-spec/knowledge/
            ttl_hours: Cache TTL in hours. Default: 24
            soft_token_limit: Soft limit for tokens per query. Logged but not enforced.
            context7_resolve: MCP tool function for resolve-library-id
            context7_query: MCP tool function for query-docs
        """
        self.cache_dir = cache_dir or Path.home() / ".cache" / "adversarial-spec" / "knowledge"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ttl = timedelta(hours=ttl_hours)
        self.soft_token_limit = soft_token_limit

        # MCP tool functions - injected by caller
        self._resolve_fn = context7_resolve
        self._query_fn = context7_query

        # In-memory cache for current session
        self._memory_cache: dict[str, DocCacheEntry] = {}

        # Token usage tracking
        self.token_usage_log: list[TokenUsageLog] = []

        # Evidence log for current session
        self.evidence_log: list[EvidenceItem] = []

    def _cache_path(self, library_id: str) -> Path:
        """Get the cache file path for a library."""
        # Sanitize library_id for filesystem
        safe_id = library_id.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_id}.json.gz"

    def _load_from_cache(self, library_id: str) -> DocCacheEntry | None:
        """Load a library from disk cache."""
        # Check memory cache first
        if library_id in self._memory_cache:
            entry = self._memory_cache[library_id]
            if not entry.is_expired():
                return entry
            else:
                del self._memory_cache[library_id]

        # Check disk cache
        cache_path = self._cache_path(library_id)
        if not cache_path.exists():
            return None

        try:
            with gzip.open(cache_path, "rt", encoding="utf-8") as f:
                data = json.load(f)
            entry = DocCacheEntry.from_dict(data)

            if entry.is_expired():
                cache_path.unlink()  # Clean up expired cache
                return None

            # Store in memory cache
            self._memory_cache[library_id] = entry
            return entry

        except (json.JSONDecodeError, gzip.BadGzipFile, KeyError) as e:
            logger.warning(f"Cache corruption for {library_id}: {e}. Deleting.")
            cache_path.unlink(missing_ok=True)
            return None

    def _save_to_cache(self, entry: DocCacheEntry) -> None:
        """Save a library to disk cache."""
        self._memory_cache[entry.library_id] = entry

        cache_path = self._cache_path(entry.library_id)
        with gzip.open(cache_path, "wt", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return len(text) // 4

    def _log_token_usage(self, query: str, library_id: str, tokens: int) -> None:
        """Log token usage for soft limit monitoring."""
        exceeded = tokens > self.soft_token_limit

        log_entry = TokenUsageLog(
            query=query,
            library_id=library_id,
            tokens_fetched=tokens,
            soft_limit=self.soft_token_limit,
            exceeded=exceeded,
        )
        self.token_usage_log.append(log_entry)

        if exceeded:
            logger.warning(
                f"Soft token limit exceeded: {tokens} > {self.soft_token_limit} "
                f"(library={library_id}, query={query[:50]}...)"
            )

    def resolve_library(self, library_name: str, user_query: str = "") -> str | None:
        """
        Resolve a library name to a Context7 library ID.

        Args:
            library_name: Name of the library (e.g., "polymarket", "@stripe/stripe-node")
            user_query: Context about what the user is trying to accomplish

        Returns:
            Library ID like "/polymarket/clob-client" or None if not found
        """
        if not self._resolve_fn:
            logger.warning("Context7 resolve function not configured")
            return None

        try:
            result = self._resolve_fn(libraryName=library_name, query=user_query)
            # Parse result to extract library ID
            # Context7 returns structured data with library matches
            if isinstance(result, dict) and "library_id" in result:
                return result["library_id"]
            elif isinstance(result, str):
                # May return the ID directly
                return result if result.startswith("/") else None
            return None
        except Exception as e:
            logger.error(f"Context7 resolve failed for {library_name}: {e}")
            return None

    def get_documentation(
        self,
        library_id: str,
        query: str,
        force_refresh: bool = False,
    ) -> list[str]:
        """
        Get documentation for a library, using cache when available.

        Args:
            library_id: Context7 library ID (e.g., "/polymarket/clob-client")
            query: What to look up in the docs
            force_refresh: Skip cache and fetch fresh

        Returns:
            List of relevant documentation chunks
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self._load_from_cache(library_id)
            if cached:
                # Look for existing chunk with similar query
                for chunk in cached.chunks:
                    if self._queries_similar(chunk.source_query, query):
                        return [chunk.content]

        # Fetch from Context7
        if not self._query_fn:
            logger.warning("Context7 query function not configured")
            return []

        try:
            result = self._query_fn(libraryId=library_id, query=query)

            if isinstance(result, str):
                content = result
            elif isinstance(result, dict):
                content = result.get("content", result.get("text", str(result)))
            else:
                content = str(result)

            # Track token usage (soft limit)
            tokens = self._estimate_tokens(content)
            self._log_token_usage(query, library_id, tokens)

            # Create and cache the chunk
            chunk = DocChunk(
                content=content,
                token_estimate=tokens,
                source_query=query,
            )

            # Update or create cache entry
            cached = self._load_from_cache(library_id) or DocCacheEntry(
                library_id=library_id,
                library_name=library_id.split("/")[-1] if "/" in library_id else library_id,
                fetched_at=datetime.now(),
                expires_at=datetime.now() + self.ttl,
            )
            cached.chunks.append(chunk)
            cached.expires_at = datetime.now() + self.ttl  # Refresh TTL
            self._save_to_cache(cached)

            return [content]

        except Exception as e:
            logger.error(f"Context7 query failed for {library_id}: {e}")
            return []

    def _queries_similar(self, q1: str, q2: str) -> bool:
        """Check if two queries are similar enough to reuse cached results."""
        # Simple: exact match or one contains the other
        q1_lower = q1.lower().strip()
        q2_lower = q2.lower().strip()
        return q1_lower == q2_lower or q1_lower in q2_lower or q2_lower in q1_lower

    def verify_claim(
        self,
        claim_text: str,
        library_name: str,
        verification_query: str,
    ) -> EvidenceItem:
        """
        Verify a claim against documentation.

        Args:
            claim_text: The claim to verify (e.g., "Polymarket requires nonces")
            library_name: Library to check (e.g., "polymarket")
            verification_query: Query to find relevant docs

        Returns:
            EvidenceItem with verification status
        """
        claim_id = self._make_claim_id(claim_text)

        # Resolve library
        library_id = self.resolve_library(library_name, verification_query)
        if not library_id:
            evidence = EvidenceItem(
                claim_id=claim_id,
                claim_text=claim_text,
                source_library=library_name,
                verification_status=VerificationStatus.UNVERIFIABLE,
                supporting_text=f"Could not resolve library: {library_name}",
                context7_query=verification_query,
            )
            self.evidence_log.append(evidence)
            return evidence

        # Fetch documentation
        docs = self.get_documentation(library_id, verification_query)
        if not docs:
            evidence = EvidenceItem(
                claim_id=claim_id,
                claim_text=claim_text,
                source_library=library_id,
                verification_status=VerificationStatus.UNVERIFIABLE,
                supporting_text="No documentation found for query",
                context7_query=verification_query,
            )
            self.evidence_log.append(evidence)
            return evidence

        # For now, return the docs as supporting text
        # Actual verification (VERIFIED vs REFUTED) requires LLM analysis
        evidence = EvidenceItem(
            claim_id=claim_id,
            claim_text=claim_text,
            source_library=library_id,
            verification_status=VerificationStatus.PENDING,
            supporting_text=docs[0][:2000],  # Truncate for storage
            context7_query=verification_query,
        )
        self.evidence_log.append(evidence)
        return evidence

    def _make_claim_id(self, claim_text: str) -> str:
        """Generate a stable ID for a claim."""
        h = hashlib.sha1(claim_text.encode()).hexdigest()[:8]
        return f"CLAIM-{h}"

    def get_token_usage_summary(self) -> dict:
        """Get summary of token usage for review."""
        if not self.token_usage_log:
            return {"total_fetches": 0, "total_tokens": 0, "exceeded_count": 0}

        return {
            "total_fetches": len(self.token_usage_log),
            "total_tokens": sum(log.tokens_fetched for log in self.token_usage_log),
            "exceeded_count": sum(1 for log in self.token_usage_log if log.exceeded),
            "soft_limit": self.soft_token_limit,
            "violations": [
                {
                    "query": log.query[:50],
                    "library": log.library_id,
                    "tokens": log.tokens_fetched,
                }
                for log in self.token_usage_log
                if log.exceeded
            ],
        }

    def save_evidence_log(self, path: Path) -> None:
        """Save evidence log to a file."""
        data = {
            "evidence": [e.to_dict() for e in self.evidence_log],
            "token_usage": self.get_token_usage_summary(),
            "saved_at": datetime.now().isoformat(),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def clear_cache(self, library_id: str | None = None) -> int:
        """
        Clear cached documentation.

        Args:
            library_id: Specific library to clear, or None for all

        Returns:
            Number of cache entries cleared
        """
        if library_id:
            self._memory_cache.pop(library_id, None)
            path = self._cache_path(library_id)
            if path.exists():
                path.unlink()
                return 1
            return 0

        # Clear all
        count = 0
        for path in self.cache_dir.glob("*.json.gz"):
            path.unlink()
            count += 1
        self._memory_cache.clear()
        return count


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/integrations/process_runner.py (226 lines, 6333 bytes)
# ══════════════════════════════════════════════════════════════
"""
Process Runner

Safe command execution with timeout, redaction, and security validation.
Shell=False only, argument arrays only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Patterns that indicate potential secrets (high-entropy tokens)
SECRET_PATTERNS = [
    r"[A-Za-z0-9+/]{40,}={0,2}",  # Base64 tokens
    r"[a-f0-9]{32,}",  # Hex tokens (API keys, hashes)
    r"sk-[a-zA-Z0-9]{20,}",  # OpenAI keys
    r"ghp_[a-zA-Z0-9]{36}",  # GitHub tokens
    r"gho_[a-zA-Z0-9]{36}",  # GitHub OAuth tokens
    r"xox[baprs]-[a-zA-Z0-9-]+",  # Slack tokens
    r"AIza[a-zA-Z0-9_-]{35}",  # Google API keys
    r"ya29\.[a-zA-Z0-9_-]+",  # Google OAuth tokens
]

# Dangerous shell metacharacters
DANGEROUS_CHARS = [";", "&&", "||", "|", "`", "$", "\n", "\r"]


@dataclass
class ProcessResult:
    """Result of a process execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False


class ProcessRunnerError(Exception):
    """Error in process execution."""

    pass


class CommandValidationError(ProcessRunnerError):
    """Command failed security validation."""

    pass


def validate_command(command: list[str]) -> None:
    """Validate a command for security issues.

    Raises CommandValidationError if the command is unsafe.
    """
    if not command:
        raise CommandValidationError("Empty command")

    for i, arg in enumerate(command):
        for char in DANGEROUS_CHARS:
            if char in arg:
                raise CommandValidationError(
                    f"Dangerous character '{repr(char)}' in argument {i}: {arg[:50]}"
                )


def redact_secrets(text: str, extra_patterns: list[str] | None = None) -> str:
    """Redact potential secrets from text.

    Args:
        text: Text to redact
        extra_patterns: Additional regex patterns to redact

    Returns:
        Text with secrets replaced by ***REDACTED***
    """
    patterns = SECRET_PATTERNS.copy()
    if extra_patterns:
        patterns.extend(extra_patterns)

    result = text
    for pattern in patterns:
        result = re.sub(pattern, "***REDACTED***", result)

    return result


def truncate_output(text: str, max_lines: int = 500, max_chars: int = 50000) -> tuple[str, bool]:
    """Truncate output to reasonable size.

    Returns: (truncated_text, was_truncated)
    """
    truncated = False

    # Truncate by characters first
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    # Then by lines
    lines = text.split("\n")
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True

    result = "\n".join(lines)
    if truncated:
        result += "\n... [TRUNCATED]"

    return result, truncated


class ProcessRunner:
    """Safe process runner with timeout and redaction."""

    def __init__(
        self,
        cwd: str | Path,
        default_timeout: int = 60,
        redact_output: bool = True,
        extra_redact_patterns: list[str] | None = None,
    ):
        self.cwd = Path(cwd).resolve()
        self.default_timeout = default_timeout
        self.redact_output = redact_output
        self.extra_redact_patterns = extra_redact_patterns or []

        if not self.cwd.is_dir():
            raise ProcessRunnerError(f"Working directory does not exist: {self.cwd}")

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        validate: bool = True,
    ) -> ProcessResult:
        """Run a command safely.

        Args:
            command: Command as argument array (NO shell=True)
            timeout: Timeout in seconds (default: self.default_timeout)
            validate: Whether to validate command for dangerous chars

        Returns:
            ProcessResult with output and timing

        Raises:
            CommandValidationError: If command fails validation
            ProcessRunnerError: If execution fails
        """
        if validate:
            validate_command(command)

        timeout = timeout or self.default_timeout
        start_time = time.monotonic()

        try:
            result = subprocess.run(
                command,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,  # NEVER shell=True
            )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            stdout = result.stdout
            stderr = result.stderr

            # Redact secrets
            if self.redact_output:
                stdout = redact_secrets(stdout, self.extra_redact_patterns)
                stderr = redact_secrets(stderr, self.extra_redact_patterns)

            # Truncate
            stdout, _ = truncate_output(stdout)
            stderr, _ = truncate_output(stderr)

            return ProcessResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                timed_out=False,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ProcessResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                duration_ms=duration_ms,
                timed_out=True,
            )

        except FileNotFoundError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ProcessResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command not found: {command[0]}",
                duration_ms=duration_ms,
                timed_out=False,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ProcessResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                timed_out=False,
            )


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/extractors/__init__.py (12 lines, 242 bytes)
# ══════════════════════════════════════════════════════════════
"""
Extractors Module

Extract information from spec documents.
"""

from .spec_affected_files import SpecAffectedFilesExtractor, extract_spec_affected_files

__all__ = [
    "SpecAffectedFilesExtractor",
    "extract_spec_affected_files",
]


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/extractors/spec_affected_files.py (171 lines, 5400 bytes)
# ══════════════════════════════════════════════════════════════
"""
Spec Affected Files Extractor

Parses spec text to identify file paths referenced in the spec.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.git_cli import GitCli


class SpecAffectedFilesExtractor:
    """Extracts file paths referenced in a spec document."""

    # Pattern to match file paths
    # Note: We filter out URLs in post-processing since variable-width lookbehind isn't supported
    FILE_PATH_PATTERN = re.compile(
        r"\b"  # Word boundary
        r"([a-zA-Z0-9_.-]+/)*"  # Optional directory parts
        r"[a-zA-Z0-9_.-]+"  # Filename
        r"\.[a-zA-Z0-9]+"  # Extension
        r"\b"  # Word boundary
    )

    # Pattern for directory references
    DIR_PATH_PATTERN = re.compile(
        r"\b"  # Word boundary
        r"([a-zA-Z0-9_.-]+/)+"  # One or more directory parts ending in /
    )

    # Pattern to detect URLs (for filtering)
    URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)

    def __init__(
        self,
        repo_root: str | Path,
        include_untracked: bool = False,
        critical_paths: list[str] | None = None,
        max_matches: int = 100,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.include_untracked = include_untracked
        self.critical_paths = set(critical_paths or [])
        self.max_matches = max_matches

        self.git = GitCli(repo_root)
        self._file_index: set[str] | None = None

    def _build_file_index(self) -> set[str]:
        """Build index of files in the repository."""
        if self._file_index is not None:
            return self._file_index

        files = self.git.list_files(include_untracked=self.include_untracked)
        self._file_index = set(files)
        return self._file_index

    def extract(self, spec_text: str) -> list[str]:
        """Extract file paths from spec text.

        Args:
            spec_text: The specification document text

        Returns:
            List of file paths that exist in the repository
        """
        file_index = self._build_file_index()
        matches: set[str] = set()

        # Find all URLs to exclude
        url_spans = set()
        for match in self.URL_PATTERN.finditer(spec_text):
            url_spans.add((match.start(), match.end()))

        def is_in_url(start: int, end: int) -> bool:
            """Check if a span overlaps with any URL."""
            for url_start, url_end in url_spans:
                if start >= url_start and end <= url_end:
                    return True
            return False

        # Extract file path matches
        for match in self.FILE_PATH_PATTERN.finditer(spec_text):
            # Skip if inside a URL
            if is_in_url(match.start(), match.end()):
                continue

            path = match.group(0)
            # Skip email-like patterns
            if "@" in spec_text[max(0, match.start() - 1) : match.start()]:
                continue

            if self._is_valid_path(path, file_index):
                matches.add(path)

        # Extract directory matches and add all files under them
        for match in self.DIR_PATH_PATTERN.finditer(spec_text):
            dir_path = match.group(0)
            # Add files that start with this directory
            for file_path in file_index:
                if file_path.startswith(dir_path):
                    matches.add(file_path)

        # Add critical paths
        for critical_path in self.critical_paths:
            for file_path in file_index:
                if file_path.startswith(critical_path):
                    matches.add(file_path)

        # Sort for deterministic order and limit
        result = sorted(matches)[: self.max_matches]
        return result

    def _is_valid_path(self, path: str, file_index: set[str]) -> bool:
        """Check if a path is valid (exists in file index or critical paths)."""
        # Direct match in file index
        if path in file_index:
            return True

        # Check if it's under a critical path
        for critical in self.critical_paths:
            if path.startswith(critical):
                return True

        # Check with common variations
        variations = [
            path,
            f"./{path}",
            path.lstrip("./"),
        ]

        for var in variations:
            if var in file_index:
                return True

        return False


def extract_spec_affected_files(
    spec_text: str,
    repo_root: str | Path,
    include_untracked: bool = False,
    critical_paths: list[str] | None = None,
    max_matches: int = 100,
) -> list[str]:
    """Convenience function to extract affected files from spec.

    Args:
        spec_text: The specification document text
        repo_root: Path to the repository root
        include_untracked: Whether to include untracked files
        critical_paths: Additional paths to always include
        max_matches: Maximum number of file paths to return

    Returns:
        List of file paths referenced in the spec
    """
    extractor = SpecAffectedFilesExtractor(
        repo_root=repo_root,
        include_untracked=include_untracked,
        critical_paths=critical_paths,
        max_matches=max_matches,
    )
    return extractor.extract(spec_text)


