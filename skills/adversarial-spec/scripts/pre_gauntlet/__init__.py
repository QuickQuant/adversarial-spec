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
