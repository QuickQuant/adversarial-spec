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
