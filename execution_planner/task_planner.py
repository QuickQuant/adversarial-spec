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
class SpecReference:
    """Reference to a spec section."""

    section_number: str  # e.g., "4.1", "6.2"
    section_title: str  # e.g., "orders", "orders:placeDma"
    source_type: str  # "data_model", "api_endpoint", "scheduled_function", "fr"


@dataclass
class ConcernReference:
    """Reference to a gauntlet concern."""

    concern_id: str  # Stable ID like BURN-abc123
    title: str
    adversary: str
    severity: str
    text: str  # Full concern text for context


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

    # Enhanced fields for tech spec support
    spec_refs: list[SpecReference] = field(default_factory=list)
    concerns: list[ConcernReference] = field(default_factory=list)
    acceptance_criteria_from_concerns: list[str] = field(default_factory=list)
    algorithm_refs: list[str] = field(default_factory=list)  # References to algorithms in spec
    test_cases: list[str] = field(default_factory=list)  # Test cases derived from concerns


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

    def export_to_mcp_tasks(
        self,
        task_manager,
        session_id: Optional[str] = None,
        workstream: Optional[str] = None,
    ) -> dict[str, str]:
        """
        Export tasks to MCP Tasks system.

        Creates MCP Tasks from the internal task plan, preserving dependencies
        and linking to concerns/spec sections via metadata.

        Args:
            task_manager: TaskManager instance from task_manager.py
            session_id: Optional session ID for linking
            workstream: Optional workstream identifier

        Returns:
            Mapping of internal task ID to MCP task ID
        """
        # Map internal task IDs to MCP task IDs
        id_map: dict[str, str] = {}

        # Create tasks in topological order to ensure dependencies exist
        sorted_tasks = self.topological_sort()

        for task in sorted_tasks:
            # Build metadata
            metadata = {
                "phase": "implementation",
                "internal_task_id": task.id,
                "effort": task.effort_estimate,
                "risk_level": task.risk_level,
                "validation": task.validation_strategy.value,
            }

            if session_id:
                metadata["session_id"] = session_id

            if workstream:
                metadata["workstream"] = workstream

            # Add concern IDs (stable IDs like BURN-abc123)
            if task.concerns:
                metadata["concern_ids"] = [c.concern_id for c in task.concerns]

            # Add spec references
            if task.spec_refs:
                metadata["spec_refs"] = [
                    f"Section {r.section_number}: {r.section_title}"
                    for r in task.spec_refs
                ]

            # Map dependencies to MCP task IDs
            blocked_by = [id_map[dep] for dep in task.dependencies if dep in id_map]

            # Determine owner based on workstream
            owner = "adv-spec:impl"
            if workstream:
                owner = f"adv-spec:impl:{workstream}"

            # Create MCP task
            mcp_task = task_manager.create_task(
                subject=task.title,
                description=task.description,
                active_form=f"Implementing: {task.title}",
                owner=owner,
                metadata=metadata,
                blocked_by=blocked_by,
            )

            id_map[task.id] = mcp_task.id

        return id_map


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

    # =========================================================================
    # Tech Spec Generation Methods
    # =========================================================================

    @classmethod
    def generate_from_tech_spec(
        cls,
        spec_doc: SpecDocument,
        gauntlet_report: Optional["GauntletReport"] = None,  # noqa: F821
        timeout_ms: int = 30000,
    ) -> TaskPlan:
        """
        Generate a task plan from a technical specification.

        Creates tasks from:
        - Data models → schema implementation tasks
        - API endpoints → endpoint implementation tasks
        - Scheduled functions → cron job implementation tasks

        Args:
            spec_doc: Parsed specification document
            gauntlet_report: Optional gauntlet concerns to link
            timeout_ms: Timeout for LLM analysis

        Returns:
            TaskPlan with generated tasks
        """
        from execution_planner.gauntlet_concerns import GauntletReport

        plan = TaskPlan(
            llm_model="heuristic" if timeout_ms <= 1 else "claude-3-opus",
            spec_length_used=len(spec_doc.raw_content),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Maps for dependency resolution
        section_to_task: dict[str, str] = {}

        # Phase 1: Create tasks from data models (foundation)
        for dm in spec_doc.data_models:
            task = cls._data_model_to_task(dm, spec_doc, gauntlet_report)
            plan.tasks.append(task)
            section_to_task[dm.id] = task.id

        # Phase 2: Create tasks from API endpoints (depends on schemas)
        schema_tasks = [t.id for t in plan.tasks]  # All schema tasks
        for ep in spec_doc.api_endpoints:
            task = cls._api_endpoint_to_task(ep, spec_doc, gauntlet_report)
            # API tasks depend on schema tasks
            task.dependencies = schema_tasks.copy()
            plan.tasks.append(task)
            section_to_task[ep.id] = task.id

        # Phase 3: Create tasks from scheduled functions (depends on core)
        for sf in spec_doc.scheduled_functions:
            task = cls._scheduled_function_to_task(sf, spec_doc, gauntlet_report)
            # Scheduled functions may depend on everything else
            task.dependencies = schema_tasks.copy()
            plan.tasks.append(task)

        # Refine dependencies based on spec content
        cls._infer_tech_spec_dependencies(plan, spec_doc, section_to_task)

        # Assign stream IDs
        cls._assign_streams(plan)

        return plan

    @classmethod
    def _data_model_to_task(
        cls,
        dm: "DataModel",  # noqa: F821
        spec_doc: SpecDocument,
        gauntlet_report: Optional["GauntletReport"] = None,  # noqa: F821
    ) -> Task:
        """Create a task from a data model definition."""
        from execution_planner.spec_intake import DataModel
        from execution_planner.gauntlet_concerns import GauntletReport

        # Build description from definition
        description_parts = [
            f"Implement the `{dm.name}` schema as defined in Section {dm.section_ref}.",
            "",
            "Schema definition:",
            "```typescript",
            dm.definition,
            "```",
        ]

        if dm.indexes:
            description_parts.extend(["", "Indexes:", "```typescript"])
            description_parts.extend(dm.indexes)
            description_parts.append("```")

        # Build acceptance criteria
        ac_parts = [
            f"Schema `{dm.name}` is created with all specified fields",
            "Field types match specification exactly",
            "Indexes are created for specified fields",
        ]

        # Get related concerns
        concerns = []
        test_cases = []
        ac_from_concerns = []

        if gauntlet_report:
            for lc in gauntlet_report.linked_concerns:
                if (
                    lc.spec_section == dm.id
                    or dm.name in lc.related_data_models
                ):
                    concerns.append(
                        ConcernReference(
                            concern_id=lc.concern.id,
                            title=lc.concern.title or "Unnamed concern",
                            adversary=lc.concern.adversary,
                            severity=lc.concern.severity,
                            text=lc.concern.text[:500],  # Truncate for size
                        )
                    )
                    # Derive acceptance criteria from concerns
                    if lc.concern.failure_mode:
                        ac_from_concerns.append(
                            f"Must not exhibit: {lc.concern.failure_mode[:200]}"
                        )
                    if lc.concern.consequence:
                        test_cases.append(
                            f"Verify protection against: {lc.concern.consequence[:200]}"
                        )

        # Assess risk based on concern count
        risk = "low"
        if len(concerns) >= 3:
            risk = "high"
        elif len(concerns) >= 1:
            risk = "medium"

        return Task(
            title=f"Implement schema: {dm.name}",
            description="\n".join(description_parts),
            acceptance_criteria=" | ".join(ac_parts),
            effort_estimate=cls._estimate_schema_effort(dm.definition),
            risk_level=risk,
            validation_strategy=(
                ValidationStrategy.TEST_FIRST if risk == "high" else ValidationStrategy.TEST_AFTER
            ),
            spec_refs=[
                SpecReference(
                    section_number=dm.id,
                    section_title=dm.name,
                    source_type="data_model",
                )
            ],
            concerns=concerns,
            acceptance_criteria_from_concerns=ac_from_concerns,
            test_cases=test_cases,
        )

    @classmethod
    def _api_endpoint_to_task(
        cls,
        ep: "APIEndpoint",  # noqa: F821
        spec_doc: SpecDocument,
        gauntlet_report: Optional["GauntletReport"] = None,  # noqa: F821
    ) -> Task:
        """Create a task from an API endpoint definition."""
        from execution_planner.spec_intake import APIEndpoint
        from execution_planner.gauntlet_concerns import GauntletReport

        # Build description
        description_parts = [
            f"Implement the `{ep.name}` action as defined in Section {ep.section_ref}.",
        ]

        if ep.request_schema:
            description_parts.extend(["", "Request:", "```typescript", ep.request_schema, "```"])
        if ep.response_schema:
            description_parts.extend(["", "Response:", "```typescript", ep.response_schema, "```"])
        if ep.flow_steps:
            description_parts.extend(["", "Execution flow:"])
            description_parts.extend(ep.flow_steps)

        # Build acceptance criteria
        ac_parts = [
            f"Action `{ep.name}` handles all specified request parameters",
            "Returns response matching schema",
            "All validation errors return appropriate error codes",
        ]

        # Get related concerns
        concerns = []
        test_cases = []
        ac_from_concerns = []
        algorithm_refs = []

        if gauntlet_report:
            for lc in gauntlet_report.linked_concerns:
                if (
                    lc.spec_section == ep.id
                    or ep.name in lc.related_endpoints
                ):
                    concerns.append(
                        ConcernReference(
                            concern_id=lc.concern.id,
                            title=lc.concern.title or "Unnamed concern",
                            adversary=lc.concern.adversary,
                            severity=lc.concern.severity,
                            text=lc.concern.text[:500],
                        )
                    )
                    # Derive test cases from concerns
                    if lc.concern.failure_mode:
                        test_cases.append(
                            f"Test: {lc.concern.failure_mode[:200]}"
                        )
                    if lc.concern.detection:
                        test_cases.append(
                            f"Verify monitoring: {lc.concern.detection[:200]}"
                        )

        # Check for algorithm references in the spec section
        section = spec_doc.get_section_by_number(ep.id)
        if section:
            # Look for algorithm-like patterns
            import re
            algo_matches = re.findall(
                r"(?:Algorithm|Steps?|Flow|Process):\s*\n((?:\d+\..+\n?)+)",
                section.content,
                re.IGNORECASE,
            )
            for match in algo_matches:
                algorithm_refs.append(match[:500])

        # Assess risk
        risk = "low"
        if len(concerns) >= 3:
            risk = "high"
        elif len(concerns) >= 1:
            risk = "medium"

        return Task(
            title=f"Implement endpoint: {ep.name}",
            description="\n".join(description_parts),
            acceptance_criteria=" | ".join(ac_parts),
            effort_estimate=cls._estimate_endpoint_effort(ep),
            risk_level=risk,
            validation_strategy=(
                ValidationStrategy.TEST_FIRST if risk == "high" else ValidationStrategy.TEST_AFTER
            ),
            spec_refs=[
                SpecReference(
                    section_number=ep.id,
                    section_title=ep.name,
                    source_type="api_endpoint",
                )
            ],
            concerns=concerns,
            acceptance_criteria_from_concerns=ac_from_concerns,
            test_cases=test_cases,
            algorithm_refs=algorithm_refs,
        )

    @classmethod
    def _scheduled_function_to_task(
        cls,
        sf: "ScheduledFunction",  # noqa: F821
        spec_doc: SpecDocument,
        gauntlet_report: Optional["GauntletReport"] = None,  # noqa: F821
    ) -> Task:
        """Create a task from a scheduled function definition."""
        from execution_planner.spec_intake import ScheduledFunction

        description = (
            f"Implement scheduled function `{sf.name}` that runs every {sf.frequency}.\n\n"
            f"Purpose: {sf.purpose}"
        )

        ac_parts = [
            f"Function `{sf.name}` is scheduled correctly",
            f"Runs at {sf.frequency} interval",
            "Handles errors gracefully without blocking subsequent runs",
        ]

        return Task(
            title=f"Implement scheduled function: {sf.name}",
            description=description,
            acceptance_criteria=" | ".join(ac_parts),
            effort_estimate="S",
            risk_level="low",
            validation_strategy=ValidationStrategy.TEST_AFTER,
            spec_refs=[
                SpecReference(
                    section_number=sf.section_ref,
                    section_title=sf.name,
                    source_type="scheduled_function",
                )
            ],
        )

    @classmethod
    def _estimate_schema_effort(cls, definition: str) -> str:
        """Estimate effort for schema implementation."""
        field_count = definition.count(":")
        if field_count <= 5:
            return "XS"
        elif field_count <= 10:
            return "S"
        elif field_count <= 20:
            return "M"
        else:
            return "L"

    @classmethod
    def _estimate_endpoint_effort(cls, ep: "APIEndpoint") -> str:  # noqa: F821
        """Estimate effort for endpoint implementation."""
        from execution_planner.spec_intake import APIEndpoint

        # Count flow steps and schema complexity
        step_count = len(ep.flow_steps) if ep.flow_steps else 0
        has_complex_response = bool(ep.response_schema and len(ep.response_schema) > 200)

        if step_count >= 8 or has_complex_response:
            return "L"
        elif step_count >= 4:
            return "M"
        elif step_count >= 2:
            return "S"
        else:
            return "S"

    @classmethod
    def _infer_tech_spec_dependencies(
        cls,
        plan: TaskPlan,
        spec_doc: SpecDocument,
        section_to_task: dict[str, str],
    ) -> None:
        """Infer dependencies between tech spec tasks."""
        import re

        for task in plan.tasks:
            # Look for section references in description
            section_refs = re.findall(r"Section\s+(\d+(?:\.\d+)?)", task.description)
            for ref in section_refs:
                if ref in section_to_task:
                    dep_task_id = section_to_task[ref]
                    if dep_task_id != task.id and dep_task_id not in task.dependencies:
                        task.dependencies.append(dep_task_id)
