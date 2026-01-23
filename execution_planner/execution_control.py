"""
FR-8: Execution Control

Provides user controls for managing running executions:
approve, pause, skip, retry, force-complete, resume.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Any

from execution_planner.task_planner import TaskPlan, Task
from execution_planner.agent_dispatch import AgentDispatcher, AgentStatus


class ExecutionState(Enum):
    """State of the execution controller."""

    NOT_STARTED = "not_started"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ControlAction(Enum):
    """Types of control actions."""

    APPROVE = "approve"
    PAUSE = "pause"
    RESUME = "resume"
    SKIP = "skip"
    RETRY = "retry"
    FORCE_COMPLETE = "force_complete"


@dataclass
class ControlActionRecord:
    """Record of a control action taken."""

    action: ControlAction
    timestamp: str
    user: str = "system"
    task_id: Optional[str] = None
    reason: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "action": self.action.value,
            "timestamp": self.timestamp,
            "user": self.user,
            "task_id": self.task_id,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class TaskExecutionState:
    """Execution state for a single task."""

    task_id: str
    status: AgentStatus = AgentStatus.QUEUED
    attempt_count: int = 0
    skipped: bool = False
    force_completed: bool = False
    force_complete_reason: Optional[str] = None
    additional_context: Optional[str] = None
    last_error: Optional[str] = None


@dataclass
class ApprovalRecord:
    """Record of plan approval."""

    approved: bool
    approved_at: str
    approved_by: str
    validation_passed: bool
    validation_warnings: list[str] = field(default_factory=list)


class ExecutionController:
    """Controls execution of a task plan."""

    def __init__(
        self,
        plan: TaskPlan,
        dispatcher: AgentDispatcher,
        max_retries: int = 3,
        state_file: Optional[Path] = None,
    ) -> None:
        self._plan = plan
        self._dispatcher = dispatcher
        self._max_retries = max_retries
        self._state_file = state_file or Path(
            tempfile.gettempdir(), "execution_state.json"
        )

        self._state = ExecutionState.AWAITING_APPROVAL
        self._approval: Optional[ApprovalRecord] = None
        self._task_states: dict[str, TaskExecutionState] = {}
        self._action_log: list[ControlActionRecord] = []

        # Initialize task states
        for task in plan.tasks:
            self._task_states[task.id] = TaskExecutionState(task_id=task.id)

    @property
    def state(self) -> ExecutionState:
        """Current execution state."""
        return self._state

    @property
    def is_approved(self) -> bool:
        """Whether the plan has been approved."""
        return self._approval is not None and self._approval.approved

    @property
    def is_paused(self) -> bool:
        """Whether execution is paused."""
        return self._state == ExecutionState.PAUSED

    def _log_action(
        self,
        action: ControlAction,
        user: str = "system",
        task_id: Optional[str] = None,
        reason: Optional[str] = None,
        **metadata: Any,
    ) -> ControlActionRecord:
        """Log a control action."""
        record = ControlActionRecord(
            action=action,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user=user,
            task_id=task_id,
            reason=reason,
            metadata=metadata,
        )
        self._action_log.append(record)
        return record

    def approve(
        self,
        user: str = "system",
        skip_validation: bool = False,
    ) -> ApprovalRecord:
        """
        Approve the plan for execution.

        Args:
            user: Who is approving
            skip_validation: Skip plan validation (not recommended)

        Returns:
            ApprovalRecord with validation results
        """
        # Validate plan
        validation_passed = True
        validation_warnings: list[str] = []

        if not skip_validation:
            result = self._plan.approve()
            validation_passed = result.validated
            validation_warnings = result.warnings

        # Create approval record
        self._approval = ApprovalRecord(
            approved=validation_passed,
            approved_at=datetime.now(timezone.utc).isoformat(),
            approved_by=user,
            validation_passed=validation_passed,
            validation_warnings=validation_warnings,
        )

        if validation_passed:
            self._state = ExecutionState.RUNNING
            self._log_action(ControlAction.APPROVE, user=user)

        return self._approval

    def pause(self, user: str = "system", reason: Optional[str] = None) -> bool:
        """
        Pause all execution.

        Args:
            user: Who is pausing
            reason: Why pausing

        Returns:
            True if paused successfully
        """
        if self._state not in [ExecutionState.RUNNING, ExecutionState.AWAITING_APPROVAL]:
            return False

        self._state = ExecutionState.PAUSED
        self._log_action(ControlAction.PAUSE, user=user, reason=reason)
        self._save_state()

        return True

    def resume(self, user: str = "system") -> bool:
        """
        Resume paused execution.

        Args:
            user: Who is resuming

        Returns:
            True if resumed successfully
        """
        if self._state != ExecutionState.PAUSED:
            return False

        self._state = ExecutionState.RUNNING
        self._log_action(ControlAction.RESUME, user=user)

        return True

    def skip(
        self,
        task_id: str,
        user: str = "system",
        reason: Optional[str] = None,
    ) -> tuple[bool, list[str]]:
        """
        Skip a task.

        Args:
            task_id: Task to skip
            user: Who is skipping
            reason: Why skipping

        Returns:
            Tuple of (success, warnings about dependents)
        """
        if task_id not in self._task_states:
            return False, ["Task not found"]

        task_state = self._task_states[task_id]

        # Check for dependents that would be affected
        warnings = []
        for task in self._plan.tasks:
            if task_id in task.dependencies:
                warnings.append(
                    f"Task '{task.title}' depends on the skipped task"
                )

        # Mark as skipped
        task_state.skipped = True
        task_state.status = AgentStatus.COMPLETED  # Treat as complete for dependency resolution
        self._dispatcher.set_status(task_id, AgentStatus.COMPLETED)

        self._log_action(
            ControlAction.SKIP,
            user=user,
            task_id=task_id,
            reason=reason,
            affected_dependents=len(warnings),
        )

        return True, warnings

    def retry(
        self,
        task_id: str,
        user: str = "system",
        additional_context: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Retry a failed task.

        Args:
            task_id: Task to retry
            user: Who is retrying
            additional_context: New context to provide

        Returns:
            Tuple of (success, error message if failed)
        """
        if task_id not in self._task_states:
            return False, "Task not found"

        task_state = self._task_states[task_id]

        # Check retry limit
        if task_state.attempt_count >= self._max_retries:
            return False, f"Maximum retry limit ({self._max_retries}) reached"

        # Check task is in a retryable state
        current_status = self._dispatcher.get_status(task_id)
        if current_status not in [AgentStatus.FAILED, AgentStatus.BLOCKED]:
            return False, f"Task cannot be retried in state: {current_status.value}"

        # Reset status and increment attempt count
        task_state.status = AgentStatus.QUEUED
        task_state.attempt_count += 1
        task_state.additional_context = additional_context
        task_state.last_error = None

        # Reset in dispatcher (note: this may raise if invalid transition)
        self._dispatcher._status_map[task_id] = AgentStatus.QUEUED

        self._log_action(
            ControlAction.RETRY,
            user=user,
            task_id=task_id,
            attempt=task_state.attempt_count,
            has_new_context=additional_context is not None,
        )

        return True, None

    def force_complete(
        self,
        task_id: str,
        user: str = "system",
        reason: str = "",
        confirmed: bool = False,
    ) -> tuple[bool, list[str]]:
        """
        Force-complete a task manually.

        Args:
            task_id: Task to force-complete
            user: Who is force-completing
            reason: Why force-completing
            confirmed: Whether user confirmed the action

        Returns:
            Tuple of (success, warnings)
        """
        if task_id not in self._task_states:
            return False, ["Task not found"]

        if not confirmed:
            return False, ["Force-complete requires explicit confirmation"]

        task_state = self._task_states[task_id]
        warnings = []

        # Check for failing tests (simulated check)
        task = self._plan.get_task(task_id)
        if task and task.validation_strategy.value == "test-first":
            warnings.append(
                "This task has test-first strategy - tests may not have passed"
            )

        # Mark as force-completed
        task_state.force_completed = True
        task_state.force_complete_reason = reason
        task_state.status = AgentStatus.COMPLETED

        self._log_action(
            ControlAction.FORCE_COMPLETE,
            user=user,
            task_id=task_id,
            reason=reason,
        )

        return True, warnings

    def get_task_state(self, task_id: str) -> Optional[TaskExecutionState]:
        """Get execution state for a task."""
        return self._task_states.get(task_id)

    def get_action_log(self) -> list[ControlActionRecord]:
        """Get the log of all control actions."""
        return self._action_log.copy()

    def can_dispatch(self) -> bool:
        """Check if new dispatches are allowed."""
        return self._state == ExecutionState.RUNNING and self.is_approved

    def _save_state(self) -> None:
        """Persist execution state to disk."""
        state_data = {
            "state": self._state.value,
            "approval": asdict(self._approval) if self._approval else None,
            "task_states": {
                tid: {
                    "task_id": ts.task_id,
                    "status": ts.status.value,
                    "attempt_count": ts.attempt_count,
                    "skipped": ts.skipped,
                    "force_completed": ts.force_completed,
                    "force_complete_reason": ts.force_complete_reason,
                    "additional_context": ts.additional_context,
                    "last_error": ts.last_error,
                }
                for tid, ts in self._task_states.items()
            },
            "action_log": [a.to_dict() for a in self._action_log],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        # Atomic write
        temp_file = self._state_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
        os.replace(temp_file, self._state_file)

    def _load_state(self) -> bool:
        """Load execution state from disk."""
        if not self._state_file.exists():
            return False

        try:
            with open(self._state_file, encoding="utf-8") as f:
                state_data = json.load(f)

            self._state = ExecutionState(state_data["state"])

            if state_data.get("approval"):
                self._approval = ApprovalRecord(**state_data["approval"])

            for tid, ts_data in state_data.get("task_states", {}).items():
                self._task_states[tid] = TaskExecutionState(
                    task_id=ts_data["task_id"],
                    status=AgentStatus(ts_data["status"]),
                    attempt_count=ts_data["attempt_count"],
                    skipped=ts_data["skipped"],
                    force_completed=ts_data["force_completed"],
                    force_complete_reason=ts_data.get("force_complete_reason"),
                    additional_context=ts_data.get("additional_context"),
                    last_error=ts_data.get("last_error"),
                )

            for action_data in state_data.get("action_log", []):
                self._action_log.append(
                    ControlActionRecord(
                        action=ControlAction(action_data["action"]),
                        timestamp=action_data["timestamp"],
                        user=action_data.get("user", "system"),
                        task_id=action_data.get("task_id"),
                        reason=action_data.get("reason"),
                        metadata=action_data.get("metadata", {}),
                    )
                )

            return True

        except (json.JSONDecodeError, KeyError, ValueError):
            return False

    @classmethod
    def resume_from_state(
        cls,
        plan: TaskPlan,
        dispatcher: AgentDispatcher,
        state_file: Path,
        user: str = "system",
    ) -> Optional[ExecutionController]:
        """
        Resume execution from saved state.

        Args:
            plan: The task plan
            dispatcher: The agent dispatcher
            state_file: Path to saved state file
            user: Who is resuming

        Returns:
            ExecutionController with restored state, or None if restore failed
        """
        controller = cls(plan, dispatcher, state_file=state_file)

        if not controller._load_state():
            return None

        # Log resume action
        controller._log_action(ControlAction.RESUME, user=user, reason="resumed from saved state")

        # Set state to running if it was paused or running before
        if controller._state in [ExecutionState.PAUSED, ExecutionState.RUNNING]:
            controller._state = ExecutionState.RUNNING

        return controller
