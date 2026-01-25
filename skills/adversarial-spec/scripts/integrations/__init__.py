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
