"""
FR-9: Progress Visibility

Provides real-time visibility into execution status, logs, and branch state.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Any

from execution_planner.agent_dispatch import AgentStatus
from execution_planner.task_planner import TaskPlan


class LogLevel(Enum):
    """Log severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogEntry:
    """A structured log entry."""

    timestamp: str
    level: LogLevel
    message: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "message": self.message,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class TaskStatus:
    """Status of a single task."""

    task_id: str
    title: str
    status: AgentStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 0


@dataclass
class BranchStatus:
    """Status of a git branch."""

    branch_name: str
    task_ids: list[str] = field(default_factory=list)
    is_ready_to_merge: bool = False
    has_conflicts: bool = False
    last_commit: Optional[str] = None


@dataclass
class ProgressReport:
    """Summary progress report."""

    generated_at: str
    total_tasks: int
    queued: int
    running: int
    completed: int
    failed: int
    blocked: int
    skipped: int
    task_statuses: list[TaskStatus] = field(default_factory=list)
    branch_statuses: list[BranchStatus] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "generated_at": self.generated_at,
            "summary": {
                "total_tasks": self.total_tasks,
                "queued": self.queued,
                "running": self.running,
                "completed": self.completed,
                "failed": self.failed,
                "blocked": self.blocked,
                "skipped": self.skipped,
            },
            "task_statuses": [
                {
                    "task_id": ts.task_id,
                    "title": ts.title,
                    "status": ts.status.value,
                    "started_at": ts.started_at,
                    "completed_at": ts.completed_at,
                    "error_message": ts.error_message,
                    "attempt_count": ts.attempt_count,
                }
                for ts in self.task_statuses
            ],
            "branch_statuses": [asdict(bs) for bs in self.branch_statuses],
            "timeline": self.timeline,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class ProgressTracker:
    """Tracks and reports execution progress."""

    def __init__(
        self,
        plan: TaskPlan,
        log_dir: Optional[Path] = None,
        state_file: Optional[Path] = None,
        max_log_size: int = 10 * 1024 * 1024,  # 10 MB
        log_retention_count: int = 5,
    ) -> None:
        self._plan = plan
        self._log_dir = log_dir or Path.cwd() / ".execution_logs"
        self._state_file = state_file or self._log_dir / "state.json"
        self._max_log_size = max_log_size
        self._log_retention_count = log_retention_count

        self._task_statuses: dict[str, TaskStatus] = {}
        self._branch_statuses: dict[str, BranchStatus] = {}
        self._timeline: list[dict] = []
        self._log_entries: list[LogEntry] = []
        self._lock = threading.RLock()

        # Initialize task statuses
        for task in plan.tasks:
            self._task_statuses[task.id] = TaskStatus(
                task_id=task.id,
                title=task.title,
                status=AgentStatus.QUEUED,
            )

        # Set up logging
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up rotating log handler."""
        self._log_dir.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("execution_planner.progress")
        self._logger.setLevel(logging.DEBUG)

        # Rotating file handler
        log_file = self._log_dir / "execution.log"
        handler = RotatingFileHandler(
            log_file,
            maxBytes=self._max_log_size,
            backupCount=self._log_retention_count,
        )
        handler.setLevel(logging.DEBUG)

        # JSON formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"message": "%(message)s", "name": "%(name)s"}'
        )
        handler.setFormatter(formatter)

        self._logger.addHandler(handler)

    def log(
        self,
        level: LogLevel,
        message: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        **metadata: Any,
    ) -> LogEntry:
        """Log an execution event."""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            task_id=task_id,
            agent_id=agent_id,
            metadata=metadata,
        )

        with self._lock:
            self._log_entries.append(entry)

            # Check for high log volume (warning)
            if len(self._log_entries) > 1000:
                self._logger.warning(
                    "High log volume detected - may indicate workflow issue"
                )

        # Also write to file logger
        log_func = getattr(self._logger, level.value)
        log_func(f"[{task_id or 'system'}] {message}")

        return entry

    def log_decision(
        self,
        decision: str,
        task_id: Optional[str] = None,
        **context: Any,
    ) -> LogEntry:
        """Log an execution decision."""
        return self.log(
            LogLevel.INFO,
            f"Decision: {decision}",
            task_id=task_id,
            decision=decision,
            **context,
        )

    def log_agent_output(
        self,
        agent_id: str,
        output: str,
        task_id: Optional[str] = None,
    ) -> LogEntry:
        """Log agent output."""
        return self.log(
            LogLevel.INFO,
            f"Agent output: {output[:200]}..." if len(output) > 200 else f"Agent output: {output}",
            task_id=task_id,
            agent_id=agent_id,
            full_output=output,
        )

    def update_task_status(
        self,
        task_id: str,
        status: AgentStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the status of a task."""
        with self._lock:
            if task_id not in self._task_statuses:
                return

            task_status = self._task_statuses[task_id]
            old_status = task_status.status
            task_status.status = status

            now = datetime.now(timezone.utc).isoformat()

            if status == AgentStatus.RUNNING and task_status.started_at is None:
                task_status.started_at = now
                task_status.attempt_count += 1

            if status in [AgentStatus.COMPLETED, AgentStatus.FAILED]:
                task_status.completed_at = now

            if error_message:
                task_status.error_message = error_message

            # Add to timeline
            self._timeline.append({
                "timestamp": now,
                "task_id": task_id,
                "old_status": old_status.value,
                "new_status": status.value,
            })

            # Log the status change
            self.log(
                LogLevel.INFO,
                f"Task status changed: {old_status.value} -> {status.value}",
                task_id=task_id,
            )

        # Persist state
        self._save_state()

    def update_branch_status(
        self,
        branch_name: str,
        task_ids: Optional[list[str]] = None,
        is_ready_to_merge: Optional[bool] = None,
        has_conflicts: Optional[bool] = None,
        last_commit: Optional[str] = None,
    ) -> None:
        """Update the status of a branch."""
        with self._lock:
            if branch_name not in self._branch_statuses:
                self._branch_statuses[branch_name] = BranchStatus(
                    branch_name=branch_name
                )

            bs = self._branch_statuses[branch_name]

            if task_ids is not None:
                bs.task_ids = task_ids
            if is_ready_to_merge is not None:
                bs.is_ready_to_merge = is_ready_to_merge
            if has_conflicts is not None:
                bs.has_conflicts = has_conflicts
            if last_commit is not None:
                bs.last_commit = last_commit

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status for a specific task."""
        with self._lock:
            return self._task_statuses.get(task_id)

    def get_tasks_by_status(self, status: AgentStatus) -> list[TaskStatus]:
        """Get all tasks with a specific status."""
        with self._lock:
            return [
                ts for ts in self._task_statuses.values()
                if ts.status == status
            ]

    def get_progress_report(self) -> ProgressReport:
        """Generate a progress report."""
        with self._lock:
            statuses = list(self._task_statuses.values())

            return ProgressReport(
                generated_at=datetime.now(timezone.utc).isoformat(),
                total_tasks=len(statuses),
                queued=sum(1 for ts in statuses if ts.status == AgentStatus.QUEUED),
                running=sum(1 for ts in statuses if ts.status == AgentStatus.RUNNING),
                completed=sum(1 for ts in statuses if ts.status == AgentStatus.COMPLETED),
                failed=sum(1 for ts in statuses if ts.status == AgentStatus.FAILED),
                blocked=sum(1 for ts in statuses if ts.status == AgentStatus.BLOCKED),
                skipped=0,  # Would need to track separately
                task_statuses=statuses,
                branch_statuses=list(self._branch_statuses.values()),
                timeline=self._timeline.copy(),
            )

    def get_logs(
        self,
        task_id: Optional[str] = None,
        level: Optional[LogLevel] = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Get log entries with optional filtering."""
        with self._lock:
            entries = self._log_entries.copy()

        # Filter by task
        if task_id:
            entries = [e for e in entries if e.task_id == task_id]

        # Filter by level
        if level:
            entries = [e for e in entries if e.level == level]

        # Limit
        return entries[-limit:]

    def _save_state(self) -> None:
        """Persist state to disk."""
        state = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "task_statuses": {
                tid: {
                    "task_id": ts.task_id,
                    "title": ts.title,
                    "status": ts.status.value,
                    "started_at": ts.started_at,
                    "completed_at": ts.completed_at,
                    "error_message": ts.error_message,
                    "attempt_count": ts.attempt_count,
                }
                for tid, ts in self._task_statuses.items()
            },
            "branch_statuses": {
                name: asdict(bs)
                for name, bs in self._branch_statuses.items()
            },
            "timeline": self._timeline,
        }

        # Atomic write
        self._log_dir.mkdir(parents=True, exist_ok=True)
        temp_file = self._state_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_file, self._state_file)

    def load_state(self) -> bool:
        """Load state from disk."""
        if not self._state_file.exists():
            return False

        try:
            with open(self._state_file, encoding="utf-8") as f:
                state = json.load(f)

            with self._lock:
                for tid, ts_data in state.get("task_statuses", {}).items():
                    if tid in self._task_statuses:
                        ts = self._task_statuses[tid]
                        ts.status = AgentStatus(ts_data["status"])
                        ts.started_at = ts_data.get("started_at")
                        ts.completed_at = ts_data.get("completed_at")
                        ts.error_message = ts_data.get("error_message")
                        ts.attempt_count = ts_data.get("attempt_count", 0)

                for name, bs_data in state.get("branch_statuses", {}).items():
                    self._branch_statuses[name] = BranchStatus(**bs_data)

                self._timeline = state.get("timeline", [])

            return True

        except (json.JSONDecodeError, KeyError, ValueError):
            return False


# CLI functions for progress visibility
def cli_show_status(tracker: ProgressTracker) -> str:
    """CLI command to show current status."""
    report = tracker.get_progress_report()

    lines = [
        "=" * 60,
        "EXECUTION STATUS",
        "=" * 60,
        f"Total: {report.total_tasks} | "
        f"Completed: {report.completed} | "
        f"Running: {report.running} | "
        f"Queued: {report.queued} | "
        f"Failed: {report.failed}",
        "",
        "TASKS:",
    ]

    for ts in report.task_statuses:
        status_icon = {
            AgentStatus.QUEUED: "○",
            AgentStatus.RUNNING: "●",
            AgentStatus.COMPLETED: "✓",
            AgentStatus.FAILED: "✗",
            AgentStatus.BLOCKED: "⊘",
        }.get(ts.status, "?")

        lines.append(f"  {status_icon} [{ts.status.value:10}] {ts.title}")
        if ts.error_message:
            lines.append(f"    Error: {ts.error_message}")

    return "\n".join(lines)


def cli_show_logs(
    tracker: ProgressTracker,
    task_id: Optional[str] = None,
    limit: int = 50,
) -> str:
    """CLI command to show logs."""
    logs = tracker.get_logs(task_id=task_id, limit=limit)

    lines = [
        "=" * 60,
        f"EXECUTION LOGS (last {limit})",
        "=" * 60,
    ]

    for entry in logs:
        task_prefix = f"[{entry.task_id}] " if entry.task_id else ""
        lines.append(
            f"{entry.timestamp} {entry.level.value.upper():7} {task_prefix}{entry.message}"
        )

    return "\n".join(lines)
