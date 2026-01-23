"""
FR-4: Test Strategy Configuration

Assigns validation strategies to tasks and manages test-first workflows.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from execution_planner.task_planner import Task, TaskPlan, ValidationStrategy


class StrategyReason(Enum):
    """Reason for strategy recommendation."""

    HIGH_RISK = "high_risk"
    MEDIUM_RISK = "medium_risk"
    LOW_RISK = "low_risk"
    COMPLEX_TASK = "complex_task"
    SIMPLE_TASK = "simple_task"
    VAGUE_AC = "vague_acceptance_criteria"
    DOCUMENTATION = "documentation_task"
    CONFIG_TASK = "configuration_task"
    USER_OVERRIDE = "user_override"


@dataclass
class TestTask:
    """A test task generated for validation."""

    id: str
    title: str
    description: str
    test_criteria: str
    test_file_path: Optional[str] = None
    implementation_task_id: str = ""
    strategy: ValidationStrategy = ValidationStrategy.TEST_AFTER
    stream_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "test_criteria": self.test_criteria,
            "test_file_path": self.test_file_path,
            "implementation_task_id": self.implementation_task_id,
            "strategy": self.strategy.value,
            "stream_id": self.stream_id,
        }


@dataclass
class StrategyAssignment:
    """Strategy assignment for a task with reasoning."""

    task_id: str
    strategy: ValidationStrategy
    reason: StrategyReason
    confidence: float = 1.0  # 0-1
    user_override: bool = False
    test_task: Optional[TestTask] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "strategy": self.strategy.value,
            "reason": self.reason.value,
            "confidence": self.confidence,
            "user_override": self.user_override,
            "test_task": self.test_task.to_dict() if self.test_task else None,
        }


@dataclass
class StrategyPlan:
    """Collection of strategy assignments for a task plan."""

    assignments: dict[str, StrategyAssignment] = field(default_factory=dict)
    test_tasks: list[TestTask] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "assignments": {
                tid: a.to_dict() for tid, a in self.assignments.items()
            },
            "test_tasks": [t.to_dict() for t in self.test_tasks],
            "warnings": self.warnings,
            "created_at": self.created_at,
        }, indent=2)

    @property
    def all_none(self) -> bool:
        """Check if all assignments are 'none'."""
        return all(
            a.strategy == ValidationStrategy.NONE
            for a in self.assignments.values()
        )


class TestStrategyManager:
    """Manages test strategy assignment and test task generation."""

    # Words that indicate vague acceptance criteria
    VAGUE_INDICATORS = [
        "good", "nice", "fast", "better", "improve", "work",
        "correctly", "properly", "should", "appropriate",
    ]

    # Words that indicate documentation/config tasks
    DOC_INDICATORS = [
        "document", "readme", "docs", "comment", "config",
        "configuration", "setup", "install", "deploy",
    ]

    @classmethod
    def assign_strategies(cls, plan: TaskPlan) -> StrategyPlan:
        """
        Assign test strategies to all tasks in a plan.

        Args:
            plan: The task plan to assign strategies to

        Returns:
            StrategyPlan with assignments and generated test tasks
        """
        strategy_plan = StrategyPlan(
            created_at=datetime.now(timezone.utc).isoformat()
        )

        for task in plan.tasks:
            assignment = cls._recommend_strategy(task)
            strategy_plan.assignments[task.id] = assignment

            # Generate test task if needed
            if assignment.strategy != ValidationStrategy.NONE:
                test_task = cls._create_test_task(task, assignment)
                assignment.test_task = test_task
                strategy_plan.test_tasks.append(test_task)

        # Check for warnings
        if strategy_plan.all_none:
            strategy_plan.warnings.append(
                "All tasks have 'none' strategy - no validation will be performed. "
                "Consider adding test strategies for important tasks."
            )

        return strategy_plan

    @classmethod
    def _recommend_strategy(cls, task: Task) -> StrategyAssignment:
        """Recommend a test strategy for a task."""
        # Check for documentation/config tasks
        task_lower = (task.title + task.description).lower()
        if any(word in task_lower for word in cls.DOC_INDICATORS):
            return StrategyAssignment(
                task_id=task.id,
                strategy=ValidationStrategy.NONE,
                reason=StrategyReason.DOCUMENTATION,
                confidence=0.8,
            )

        # Check for vague acceptance criteria
        ac_lower = task.acceptance_criteria.lower()
        vague_count = sum(1 for word in cls.VAGUE_INDICATORS if word in ac_lower)
        if vague_count >= 2:
            return StrategyAssignment(
                task_id=task.id,
                strategy=ValidationStrategy.TEST_FIRST,
                reason=StrategyReason.VAGUE_AC,
                confidence=0.7,
            )

        # High risk -> test-first
        if task.risk_level == "high":
            return StrategyAssignment(
                task_id=task.id,
                strategy=ValidationStrategy.TEST_FIRST,
                reason=StrategyReason.HIGH_RISK,
                confidence=0.9,
            )

        # Medium risk -> test-after
        if task.risk_level == "medium":
            return StrategyAssignment(
                task_id=task.id,
                strategy=ValidationStrategy.TEST_AFTER,
                reason=StrategyReason.MEDIUM_RISK,
                confidence=0.8,
            )

        # Check effort for complexity
        if task.effort_estimate in ["L", "XL"]:
            return StrategyAssignment(
                task_id=task.id,
                strategy=ValidationStrategy.TEST_FIRST,
                reason=StrategyReason.COMPLEX_TASK,
                confidence=0.75,
            )

        # Low risk, simple task -> test-after
        return StrategyAssignment(
            task_id=task.id,
            strategy=ValidationStrategy.TEST_AFTER,
            reason=StrategyReason.LOW_RISK,
            confidence=0.7,
        )

    @classmethod
    def _create_test_task(
        cls,
        task: Task,
        assignment: StrategyAssignment,
    ) -> TestTask:
        """Create a test task for the given implementation task."""
        test_id = f"test-{uuid.uuid4().hex[:8]}"

        # Determine test file path based on task title
        # Simple heuristic: convert task title to snake_case
        safe_name = "".join(
            c if c.isalnum() else "_"
            for c in task.title.lower()
        )
        test_file_path = f"tests/test_{safe_name[:30]}.py"

        # Generate test criteria from acceptance criteria
        test_criteria = cls._derive_test_criteria(task.acceptance_criteria)

        # Determine stream ID based on strategy
        stream_id = task.stream_id
        if assignment.strategy == ValidationStrategy.TEST_FIRST:
            # Test-first: test runs before impl, so same stream
            stream_id = task.stream_id
        elif assignment.strategy == ValidationStrategy.TEST_PARALLEL:
            # Test-parallel: same stream for concurrent execution
            stream_id = task.stream_id
        elif assignment.strategy == ValidationStrategy.TEST_AFTER:
            # Test-after: could be different stream, but keep same for simplicity
            stream_id = task.stream_id

        return TestTask(
            id=test_id,
            title=f"Test: {task.title}",
            description=f"Write tests for: {task.description}",
            test_criteria=test_criteria,
            test_file_path=test_file_path,
            implementation_task_id=task.id,
            strategy=assignment.strategy,
            stream_id=stream_id,
        )

    @classmethod
    def _derive_test_criteria(cls, acceptance_criteria: str) -> str:
        """Derive testable criteria from acceptance criteria."""
        # Remove vague words and make more specific
        criteria = acceptance_criteria

        # Add concrete test assertions template
        test_points = []
        lines = criteria.split("|")  # Our AC format uses | as separator

        for line in lines:
            line = line.strip()
            if line:
                # Convert to assertion format
                test_points.append(f"- Verify: {line}")

        if test_points:
            return "\n".join(test_points)
        return f"- Verify: {criteria}"

    @classmethod
    def override_strategy(
        cls,
        strategy_plan: StrategyPlan,
        task_id: str,
        new_strategy: ValidationStrategy,
        task: Optional[Task] = None,
    ) -> bool:
        """
        Override the strategy for a task.

        Args:
            strategy_plan: The strategy plan to modify
            task_id: Task to override
            new_strategy: New strategy to assign
            task: Optional task object for regenerating test task

        Returns:
            True if override was successful
        """
        if task_id not in strategy_plan.assignments:
            return False

        old_assignment = strategy_plan.assignments[task_id]

        # Create new assignment with override flag
        new_assignment = StrategyAssignment(
            task_id=task_id,
            strategy=new_strategy,
            reason=StrategyReason.USER_OVERRIDE,
            confidence=1.0,
            user_override=True,
        )

        # Remove old test task if exists
        if old_assignment.test_task:
            strategy_plan.test_tasks = [
                t for t in strategy_plan.test_tasks
                if t.id != old_assignment.test_task.id
            ]

        # Generate new test task if needed
        if new_strategy != ValidationStrategy.NONE and task:
            test_task = cls._create_test_task(task, new_assignment)
            new_assignment.test_task = test_task
            strategy_plan.test_tasks.append(test_task)

        strategy_plan.assignments[task_id] = new_assignment

        # Update warnings
        if strategy_plan.all_none and "no validation" not in str(strategy_plan.warnings):
            strategy_plan.warnings.append(
                "All tasks have 'none' strategy - no validation will be performed."
            )
        elif not strategy_plan.all_none:
            strategy_plan.warnings = [
                w for w in strategy_plan.warnings
                if "no validation" not in w
            ]

        return True

    @classmethod
    def check_vague_ac(cls, task: Task) -> tuple[bool, list[str]]:
        """
        Check if a task has vague acceptance criteria.

        Returns:
            Tuple of (is_vague, list of vague terms found)
        """
        ac_lower = task.acceptance_criteria.lower()
        found_vague = [
            word for word in cls.VAGUE_INDICATORS
            if word in ac_lower
        ]
        return len(found_vague) >= 2, found_vague

    @classmethod
    def get_blocking_order(cls, strategy_plan: StrategyPlan) -> list[str]:
        """
        Get the order of task IDs respecting test-first blocking.

        For test-first tasks, test task must complete before implementation.

        Returns:
            List of task/test IDs in execution order
        """
        order = []

        for task_id, assignment in strategy_plan.assignments.items():
            if assignment.strategy == ValidationStrategy.TEST_FIRST:
                # Test comes first
                if assignment.test_task:
                    order.append(assignment.test_task.id)
                order.append(task_id)
            elif assignment.strategy == ValidationStrategy.TEST_AFTER:
                # Implementation comes first
                order.append(task_id)
                if assignment.test_task:
                    order.append(assignment.test_task.id)
            elif assignment.strategy == ValidationStrategy.TEST_PARALLEL:
                # Both can run together (add impl first for ordering)
                order.append(task_id)
                if assignment.test_task:
                    order.append(assignment.test_task.id)
            else:
                # No test
                order.append(task_id)

        return order
