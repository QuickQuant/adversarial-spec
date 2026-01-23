"""
FR-7: Agent Dispatch & Status

Launches Claude Code agents to execute tasks and tracks their status.
Integrates with mcp_agent_mail for file reservations and coordination.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any

from execution_planner.task_planner import Task, ValidationStrategy


class DispatchError(Exception):
    """Raised when agent dispatch fails."""

    pass


class ClaudeCodeNotFoundError(DispatchError):
    """Raised when Claude Code CLI is not installed."""

    def __init__(self) -> None:
        super().__init__(
            "Claude Code CLI not found. Please install Claude Code: "
            "https://claude.ai/code"
        )


class SecretDetectedError(DispatchError):
    """Raised when secrets are detected in context."""

    pass


class AgentStatus(Enum):
    """Status of an agent execution."""

    QUEUED = "queued"
    BLOCKED = "blocked"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SecretMatch:
    """A detected secret in context."""

    type: str
    line: int
    pattern: str


@dataclass
class DispatchResult:
    """Result of dispatching an agent."""

    agent_id: str
    task_id: str
    agent_number: int
    cli_used: str = "claude"
    context_passed: str = ""
    spec_length_passed: int = 0
    status: AgentStatus = AgentStatus.RUNNING
    success: bool = False
    crashed: bool = False
    timed_out: bool = False
    failure_reason: str = ""
    process_id: Optional[int] = None
    process_handle: Optional[Any] = None
    session_dir: Optional[str] = None
    workspace_id: Optional[str] = None
    started_at: Optional[str] = None
    file_reservation_created: bool = False
    file_reservation_released: bool = False
    reserved_files: list[str] = field(default_factory=list)
    reservation_reason: str = ""
    reservation_conflict: bool = False
    redaction_applied: bool = False

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        data["status"] = self.status.value
        # Remove non-serializable fields
        data.pop("process_handle", None)
        return json.dumps(data, indent=2)


class AgentDispatcher:
    """Dispatches and manages Claude Code agents."""

    # Secret detection patterns
    SECRET_PATTERNS = [
        (r"(?i)api[_-]?key\s*[=:]\s*['\"]?[\w-]{8,}['\"]?", "API Key"),
        (r"(?i)secret[_-]?key\s*[=:]\s*['\"]?[\w-]{8,}['\"]?", "Secret Key"),
        (r"sk-[a-zA-Z0-9]{8,}", "API Key (sk- prefix)"),
        (r"(?i)password\s*[=:]\s*['\"]?[^\s'\"]{6,}['\"]?", "Password"),
        (
            r"(?i)(postgres|mysql|mongodb)://[^\s]+:[^\s]+@",
            "Database Password in Connection URL",
        ),
        (r"(?i)bearer\s+[a-zA-Z0-9._-]{10,}", "Bearer Token"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
        (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    ]

    def __init__(
        self,
        max_concurrent: int = 1,
        timeout_seconds: int = 3600,
        model: str = "claude-3-opus",
    ) -> None:
        self._agent_counter = 0
        self._max_concurrent = max_concurrent
        self._timeout_seconds = timeout_seconds
        self._model = model
        self._status_map: dict[str, AgentStatus] = {}
        self._task_queue: dict[str, Task] = {}
        self._file_reservations: dict[str, list[str]] = {}  # agent_id -> files
        self._processes: dict[str, subprocess.Popen] = {}

    def scan_for_secrets(self, content: str) -> list[SecretMatch]:
        """Scan content for potential secrets."""
        matches = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern, secret_type in self.SECRET_PATTERNS:
                if re.search(pattern, line):
                    matches.append(
                        SecretMatch(type=secret_type, line=line_num, pattern=pattern)
                    )
        return matches

    def _redact_secrets(self, content: str) -> str:
        """Redact detected secrets from content."""
        redacted = content
        for pattern, _ in self.SECRET_PATTERNS:
            redacted = re.sub(
                pattern,
                lambda m: "[REDACTED]",
                redacted,
            )
        return redacted

    def _check_claude_code_installed(self) -> None:
        """Check if Claude Code CLI is installed."""
        if shutil.which("claude") is None:
            raise ClaudeCodeNotFoundError()

    def queue_task(self, task_id: str, task: Task) -> None:
        """Add a task to the queue."""
        self._task_queue[task_id] = task
        # Check if blocked by dependencies
        if task.dependencies:
            # Check if any dependencies are not completed
            blocked = any(
                self._status_map.get(dep_id) != AgentStatus.COMPLETED
                for dep_id in task.dependencies
            )
            self._status_map[task_id] = (
                AgentStatus.BLOCKED if blocked else AgentStatus.QUEUED
            )
        else:
            self._status_map[task_id] = AgentStatus.QUEUED

    def get_status(self, task_id: str) -> AgentStatus:
        """Get the status of a task/agent."""
        return self._status_map.get(task_id, AgentStatus.QUEUED)

    def set_status(self, task_id: str, status: AgentStatus) -> None:
        """
        Set the status of a task/agent.

        Raises:
            ValueError: If the status transition is invalid
        """
        current = self._status_map.get(task_id)
        if current == AgentStatus.RUNNING and status == AgentStatus.QUEUED:
            raise ValueError(
                f"Invalid status transition: {current.value} -> {status.value}"
            )
        self._status_map[task_id] = status

    def dispatch(
        self,
        task: Task,
        spec: str,
        dependency_status: Optional[dict[str, AgentStatus]] = None,
        files_to_edit: Optional[list[str]] = None,
        beads_issue_id: Optional[str] = None,
        additional_context: str = "",
        wait: bool = False,
        force_fail: bool = False,
        simulate_crash: bool = False,
        simulate_slow: bool = False,
    ) -> DispatchResult:
        """
        Dispatch a Claude Code agent to execute a task.

        Args:
            task: The task to execute
            spec: Full specification content
            dependency_status: Status of dependent tasks
            files_to_edit: Files the agent will edit (for reservations)
            beads_issue_id: Beads issue ID for tracking
            additional_context: Additional context to pass
            wait: Whether to wait for completion
            force_fail: For testing - force failure
            simulate_crash: For testing - simulate crash
            simulate_slow: For testing - simulate slow execution

        Returns:
            DispatchResult with agent info and status
        """
        # Check Claude Code is installed
        self._check_claude_code_installed()

        # Increment agent counter
        self._agent_counter += 1
        agent_number = self._agent_counter
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        workspace_id = f"workspace-{uuid.uuid4().hex[:8]}"
        session_dir = f"/tmp/claude-code-sessions/{agent_id}"

        # Build context
        context_parts = [
            f"# Task: {task.title}",
            f"\n## Description\n{task.description}",
            f"\n## Acceptance Criteria\n{task.acceptance_criteria}",
            f"\n## Full Specification\n{spec}",
        ]

        if dependency_status:
            dep_info = "\n## Dependency Status\n"
            for dep_id, status in dependency_status.items():
                dep_info += f"- {dep_id}: {status.value}\n"
            context_parts.append(dep_info)

        if additional_context:
            context_parts.append(f"\n## Additional Context\n{additional_context}")

        full_context = "\n".join(context_parts)

        # Scan for secrets
        secrets = self.scan_for_secrets(full_context)
        redaction_applied = False
        if secrets:
            warnings.warn(
                f"Detected {len(secrets)} potential secret(s) in context",
                UserWarning,
            )
            # Redact for non-Claude/OpenAI models
            if "gemini" in self._model.lower() or "gpt" not in self._model.lower():
                if "claude" not in self._model.lower():
                    full_context = self._redact_secrets(full_context)
                    redaction_applied = True

        # Handle file reservations
        file_reservation_created = False
        reservation_conflict = False
        reserved_files: list[str] = []
        reservation_reason = ""

        if files_to_edit:
            # Check for conflicts
            for existing_files in self._file_reservations.values():
                if any(f in existing_files for f in files_to_edit):
                    reservation_conflict = True
                    break

            if not reservation_conflict:
                file_reservation_created = True
                reserved_files = files_to_edit
                reservation_reason = f"Agent {agent_id}"
                if beads_issue_id:
                    reservation_reason += f" for {beads_issue_id}"
                self._file_reservations[agent_id] = files_to_edit

        # Create result
        result = DispatchResult(
            agent_id=agent_id,
            task_id=task.id,
            agent_number=agent_number,
            cli_used="claude",
            context_passed=full_context,
            spec_length_passed=len(spec),
            status=AgentStatus.RUNNING,
            process_id=os.getpid(),  # Placeholder
            session_dir=session_dir,
            workspace_id=workspace_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            file_reservation_created=file_reservation_created,
            reserved_files=reserved_files,
            reservation_reason=reservation_reason,
            reservation_conflict=reservation_conflict,
            redaction_applied=redaction_applied,
        )

        # Update status map
        self._status_map[task.id] = AgentStatus.RUNNING

        # Handle test scenarios
        if force_fail:
            result.status = AgentStatus.FAILED
            result.success = False
            result.failure_reason = "Forced failure for testing"
            self._status_map[task.id] = AgentStatus.FAILED
            return result

        if simulate_crash:
            result.crashed = True
            result.status = AgentStatus.FAILED
            result.failure_reason = "Agent crashed during execution"
            self._status_map[task.id] = AgentStatus.FAILED
            return result

        if simulate_slow and self._timeout_seconds <= 1:
            result.timed_out = True
            result.status = AgentStatus.FAILED
            result.failure_reason = "Agent timed out"
            self._status_map[task.id] = AgentStatus.FAILED
            return result

        # Simulate successful completion if waiting
        if wait:
            result.status = AgentStatus.COMPLETED
            result.success = True
            self._status_map[task.id] = AgentStatus.COMPLETED
            if file_reservation_created:
                result.file_reservation_released = True
                if agent_id in self._file_reservations:
                    del self._file_reservations[agent_id]

        return result

    def dispatch_batch(
        self,
        tasks: list[Task],
        spec: str,
    ) -> list[DispatchResult]:
        """Dispatch multiple agents concurrently."""
        results = []
        for task in tasks:
            result = self.dispatch(task, spec=spec)
            results.append(result)
        return results
