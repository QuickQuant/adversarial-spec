"""
FR-3: Task Plan Generation and FR-3.1: Plan Editing

Generates a directed acyclic graph (DAG) of tasks from a spec.
Each task includes metadata for execution planning.
"""

from __future__ import annotations

import json
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any

from execution_planner.spec_intake import SpecDocument


class TaskPlanError(Exception):
    """Raised when task planning fails."""

    pass


class CircularDependencyError(TaskPlanError):
    """Raised when a circular dependency is detected."""

    pass


class ValidationStrategy(Enum):
    """Test/validation strategy for a task."""

    TEST_FIRST = "test-first"
    TEST_AFTER = "test-after"
    TEST_PARALLEL = "test-parallel"
    NONE = "none"


@dataclass
class Task:
    """A single task in the execution plan."""

    title: str
    description: str
    acceptance_criteria: str
    effort_estimate: str  # XS, S, M, L, XL
    risk_level: str  # low, medium, high
    validation_strategy: ValidationStrategy
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    dependencies: list[str] = field(default_factory=list)
    stream_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of plan validation."""

    validated: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class TaskPlan:
    """A plan containing tasks with dependencies forming a DAG."""

    tasks: list[Task] = field(default_factory=list)
    llm_model: Optional[str] = None
    spec_length_used: int = 0
    created_at: Optional[str] = None
    _approved: bool = field(default=False, repr=False)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = {
            "tasks": [
                {
                    **asdict(t),
                    "validation_strategy": t.validation_strategy.value,
                }
                for t in self.tasks
            ],
            "llm_model": self.llm_model,
            "spec_length_used": self.spec_length_used,
            "created_at": self.created_at,
        }
        return json.dumps(data, indent=2)

    def is_valid_dag(self) -> bool:
        """Check if task dependencies form a valid DAG (no cycles)."""
        try:
            self.topological_sort()
            return True
        except CircularDependencyError:
            return False

    def topological_sort(self) -> list[Task]:
        """
        Return tasks in topological order (dependencies before dependents).

        Raises:
            CircularDependencyError: If a cycle is detected
        """
        task_map = {t.id: t for t in self.tasks}
        in_degree = {t.id: 0 for t in self.tasks}
        adjacency: dict[str, list[str]] = {t.id: [] for t in self.tasks}

        # Build adjacency list and in-degree count
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id in adjacency:
                    adjacency[dep_id].append(task.id)
                    in_degree[task.id] += 1

        # Kahn's algorithm
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(task_map[current])
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.tasks):
            raise CircularDependencyError("Circular dependency detected in task graph")

        return result

    def get_root_tasks(self) -> list[Task]:
        """Return tasks with no dependencies (starting points)."""
        return [t for t in self.tasks if not t.dependencies]

    def get_leaf_tasks(self) -> list[Task]:
        """Return tasks that nothing depends on (end points)."""
        all_deps: set[str] = set()
        for task in self.tasks:
            all_deps.update(task.dependencies)
        return [t for t in self.tasks if t.id not in all_deps]

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def add_task(self, task: Task) -> None:
        """Add a new task to the plan."""
        self.tasks.append(task)

    def delete_task(self, task_id: str) -> None:
        """Delete a task from the plan."""
        self.tasks = [t for t in self.tasks if t.id != task_id]
        # Also remove from dependencies
        for task in self.tasks:
            task.dependencies = [d for d in task.dependencies if d != task_id]

    def update_task(self, task_id: str, **kwargs: Any) -> None:
        """Update task attributes."""
        task = self.get_task(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

    def add_dependency(self, task_id: str, depends_on_id: str) -> None:
        """
        Add a dependency relationship.

        Raises:
            CircularDependencyError: If this would create a cycle
        """
        task = self.get_task(task_id)
        if task and depends_on_id not in task.dependencies:
            # Check for cycle before adding
            task.dependencies.append(depends_on_id)
            try:
                self.topological_sort()
            except CircularDependencyError:
                task.dependencies.remove(depends_on_id)
                raise CircularDependencyError(
                    f"Adding dependency from {task_id} to {depends_on_id} "
                    f"would create a circular dependency"
                )

    def remove_dependency(self, task_id: str, depends_on_id: str) -> None:
        """Remove a dependency relationship."""
        task = self.get_task(task_id)
        if task and depends_on_id in task.dependencies:
            task.dependencies.remove(depends_on_id)

    def reorder_tasks(self, new_order: list[str]) -> None:
        """Reorder tasks by ID list."""
        task_map = {t.id: t for t in self.tasks}
        self.tasks = [task_map[tid] for tid in new_order if tid in task_map]

    def validate_delete(self, task_id: str) -> list[str]:
        """Check what would happen if a task is deleted."""
        warnings = []
        for task in self.tasks:
            if task_id in task.dependencies:
                warnings.append(
                    f"Task '{task.title}' depends on the task being deleted"
                )
        return warnings

    def validate(self) -> list[str]:
        """Validate the entire plan and return warnings."""
        warnings = []

        # Check for excessive task count
        if len(self.tasks) > 50:
            warnings.append(
                f"Plan has {len(self.tasks)} tasks - this may be excessive. "
                "Consider consolidating related tasks."
            )

        # Check for orphaned dependencies
        task_ids = {t.id for t in self.tasks}
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    warnings.append(
                        f"Task '{task.title}' has orphaned dependency: {dep_id}"
                    )

        return warnings

    def approve(self) -> ValidationResult:
        """Validate and approve the plan."""
        warnings = self.validate()
        errors = []

        # Check for cycles
        try:
            self.topological_sort()
        except CircularDependencyError as e:
            errors.append(str(e))

        self._approved = len(errors) == 0
        return ValidationResult(
            validated=self._approved,
            warnings=warnings,
            errors=errors,
        )


class TaskPlanner:
    """Generates task plans from specifications."""

    @classmethod
    def generate(
        cls,
        spec_doc: SpecDocument,
        timeout_ms: int = 30000,
    ) -> TaskPlan:
        """
        Generate a task plan from a specification.

        Args:
            spec_doc: Parsed specification document
            timeout_ms: Timeout for LLM analysis in milliseconds

        Returns:
            TaskPlan with generated tasks
        """
        plan = TaskPlan(
            llm_model="heuristic" if timeout_ms <= 1 else "claude-3-opus",
            spec_length_used=len(spec_doc.raw_content),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Generate tasks from FRs
        fr_task_map: dict[str, str] = {}  # FR-ID -> Task-ID mapping

        for fr in spec_doc.functional_requirements:
            task = cls._fr_to_task(fr, spec_doc)
            plan.tasks.append(task)
            fr_task_map[fr.id] = task.id

        # Add dependencies based on FR content
        cls._infer_dependencies(plan, spec_doc, fr_task_map)

        # Assign stream IDs for parallel execution
        cls._assign_streams(plan)

        return plan

    @classmethod
    def _fr_to_task(cls, fr: Any, spec_doc: SpecDocument) -> Task:
        """Convert a functional requirement to a task."""
        # Derive acceptance criteria from FR and related user stories
        ac = cls._derive_acceptance_criteria(fr, spec_doc)

        # Estimate effort based on content
        effort = cls._estimate_effort(fr.content)

        # Assess risk
        risk = cls._assess_risk(fr, spec_doc)

        # Determine validation strategy
        strategy = cls._determine_validation_strategy(fr, risk)

        return Task(
            title=f"Implement {fr.id}: {fr.title}",
            description=fr.content,
            acceptance_criteria=ac,
            effort_estimate=effort,
            risk_level=risk,
            validation_strategy=strategy,
        )

    @classmethod
    def _derive_acceptance_criteria(cls, fr: Any, spec_doc: SpecDocument) -> str:
        """Derive acceptance criteria from FR and user stories."""
        ac_parts = []

        # Add FR requirements
        ac_parts.append(fr.content)

        # Find related user stories
        fr_lower = fr.content.lower()
        for us in spec_doc.user_stories:
            us_lower = us.content.lower()
            # Check for keyword overlap
            if any(
                word in fr_lower
                for word in us_lower.split()
                if len(word) > 4
            ):
                ac_parts.append(f"User story {us.id}: {us.content}")

        return " | ".join(ac_parts)

    @classmethod
    def _estimate_effort(cls, content: str) -> str:
        """Estimate effort based on content complexity."""
        word_count = len(content.split())
        bullet_count = content.count("-") + content.count("*")

        if word_count < 20 and bullet_count <= 2:
            return "XS"
        elif word_count < 50 and bullet_count <= 4:
            return "S"
        elif word_count < 100 and bullet_count <= 6:
            return "M"
        elif word_count < 200:
            return "L"
        else:
            return "XL"

    @classmethod
    def _assess_risk(cls, fr: Any, spec_doc: SpecDocument) -> str:
        """Assess risk level for a task."""
        # Check if any high-risk items relate to this FR
        for risk in spec_doc.risks:
            if risk.severity.upper() == "HIGH":
                # Simple keyword matching
                if any(
                    word in fr.content.lower()
                    for word in risk.title.lower().split()
                    if len(word) > 3
                ):
                    return "high"
            elif risk.severity.upper() == "MEDIUM":
                if any(
                    word in fr.content.lower()
                    for word in risk.title.lower().split()
                    if len(word) > 3
                ):
                    return "medium"

        # Default to low risk
        return "low"

    @classmethod
    def _determine_validation_strategy(cls, fr: Any, risk: str) -> ValidationStrategy:
        """Determine validation strategy based on FR and risk."""
        # High risk tasks get test-first
        if risk == "high":
            return ValidationStrategy.TEST_FIRST

        # Look for testing keywords in FR
        content_lower = fr.content.lower()
        if "test" in content_lower or "verify" in content_lower:
            return ValidationStrategy.TEST_FIRST

        # Medium risk gets test-after
        if risk == "medium":
            return ValidationStrategy.TEST_AFTER

        # Default
        return ValidationStrategy.TEST_AFTER

    @classmethod
    def _infer_dependencies(
        cls,
        plan: TaskPlan,
        spec_doc: SpecDocument,
        fr_task_map: dict[str, str],
    ) -> None:
        """Infer task dependencies from FR content."""
        for task in plan.tasks:
            # Look for "Requires: FR-X" patterns in description
            import re
            requires_pattern = r"Requires?:\s*(FR-\d+)"
            matches = re.findall(requires_pattern, task.description, re.IGNORECASE)
            for fr_id in matches:
                if fr_id in fr_task_map:
                    dep_task_id = fr_task_map[fr_id]
                    if dep_task_id != task.id and dep_task_id not in task.dependencies:
                        task.dependencies.append(dep_task_id)

    @classmethod
    def _assign_streams(cls, plan: TaskPlan) -> None:
        """Assign parallel stream IDs to tasks."""
        # Simple stream assignment based on dependencies
        stream_counter = 1
        assigned: set[str] = set()

        # First, assign streams to root tasks
        for task in plan.get_root_tasks():
            task.stream_id = f"stream-{stream_counter}"
            assigned.add(task.id)
            stream_counter += 1

        # Then propagate to dependent tasks
        for task in plan.tasks:
            if task.id not in assigned:
                if task.dependencies:
                    # Use same stream as first dependency
                    dep_task = plan.get_task(task.dependencies[0])
                    if dep_task and dep_task.stream_id:
                        task.stream_id = dep_task.stream_id
                    else:
                        task.stream_id = f"stream-{stream_counter}"
                        stream_counter += 1
                else:
                    task.stream_id = f"stream-{stream_counter}"
                    stream_counter += 1
                assigned.add(task.id)
