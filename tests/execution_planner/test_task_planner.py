"""
Test specifications for FR-3: Task Plan Generation and FR-3.1: Plan Editing

The Task Planner generates a directed acyclic graph (DAG) of tasks from a spec.
Each task includes metadata for execution planning.

Acceptance Criteria (FR-3):
- Generates tasks with: title, description, dependencies, acceptance criteria,
  effort estimate, risk level, validation strategy, parallel stream assignment
- Dependencies form a valid DAG (no cycles)
- Acceptance criteria derived from spec
- Effort estimates: XS/S/M/L/XL
- Risk levels: low/medium/high

Acceptance Criteria (FR-3.1):
- User can add/delete tasks
- User can edit task details
- User can modify dependencies
- User can change test strategy
- User can reorder tasks
- Validation: detect circular dependencies, warn on orphaned deps

Edge Cases:
- Spec with no clear tasks → prompt user
- Circular dependency created by edit → error before save
- Deleted task has dependents → warn user
"""

import pytest
import json

# These imports will fail until implementation exists
from execution_planner.task_planner import (
    TaskPlanner,
    TaskPlan,
    Task,
    TaskPlanError,
    CircularDependencyError,
    ValidationStrategy,
)
from execution_planner.spec_intake import SpecIntake


# Test fixtures
BASIC_SPEC = """# Basic Feature

## Executive Summary
Add a simple counter component.

## User Stories
- **US-1**: As a user, I want to increment a counter.
- **US-2**: As a user, I want to reset the counter.

## Functional Requirements

### FR-1: Counter Display
- Show current count value
- Start at zero

### FR-2: Increment Button
- Click to add one to count
- Button labeled "+"

### FR-3: Reset Button
- Click to reset count to zero
- Button labeled "Reset"

## Non-Functional Requirements

### NFR-1: Performance
- Counter updates should be instant (< 16ms)
"""

COMPLEX_SPEC_WITH_DEPS = """# Feature With Dependencies

## Executive Summary
Add user auth with protected routes.

## Functional Requirements

### FR-1: Auth Context
- Create React context for auth state
- Provider wraps app root

### FR-2: Login Form
- Email and password fields
- Calls auth endpoint
- Requires: FR-1 (needs auth context)

### FR-3: Protected Route Component
- Redirects if not authenticated
- Requires: FR-1 (needs auth context)

### FR-4: Dashboard Page
- Shows user info
- Requires: FR-3 (needs protected route)
"""

VAGUE_SPEC = """# Unclear Feature

## Summary
Make it work better.

## Notes
- Should be faster
- Should be nicer
"""


class TestTaskGeneration:
    """FR-3: Core task generation functionality."""

    def test_generates_tasks_from_spec(self):
        """Should generate at least one task from a valid spec."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        assert len(plan.tasks) >= 1

    def test_task_has_title(self):
        """Each task should have a descriptive title."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert task.title is not None
            assert len(task.title) > 0

    def test_task_has_description(self):
        """Each task should have a description explaining what to do."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert task.description is not None
            assert len(task.description) > 0

    def test_task_has_dependencies(self):
        """Each task should have a list of dependency task IDs (may be empty)."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert hasattr(task, "dependencies")
            assert isinstance(task.dependencies, list)

    def test_task_has_acceptance_criteria(self):
        """Each task should have acceptance criteria derived from spec."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert task.acceptance_criteria is not None
            assert len(task.acceptance_criteria) > 0

    def test_task_has_effort_estimate(self):
        """Each task should have effort: XS, S, M, L, or XL."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert task.effort_estimate in ["XS", "S", "M", "L", "XL"]

    def test_task_has_risk_level(self):
        """Each task should have risk: low, medium, or high."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert task.risk_level in ["low", "medium", "high"]

    def test_task_has_validation_strategy(self):
        """Each task should have strategy: test-first, test-after, test-parallel, none."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert task.validation_strategy in [
                ValidationStrategy.TEST_FIRST,
                ValidationStrategy.TEST_AFTER,
                ValidationStrategy.TEST_PARALLEL,
                ValidationStrategy.NONE,
            ]

    def test_task_has_parallel_stream(self):
        """Each task should have parallel stream assignment (stream ID or null)."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert hasattr(task, "stream_id")
            # stream_id can be None for sequential tasks


class TestTaskDAG:
    """FR-3: DAG validation."""

    def test_dependencies_form_valid_dag(self):
        """Task dependencies should form a directed acyclic graph."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC_WITH_DEPS)
        plan = TaskPlanner.generate(spec_doc)
        # Should not raise - DAG validation happens during generation
        assert plan.is_valid_dag()

    def test_no_self_dependencies(self):
        """No task should depend on itself."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC_WITH_DEPS)
        plan = TaskPlanner.generate(spec_doc)
        for task in plan.tasks:
            assert task.id not in task.dependencies

    def test_all_dependencies_exist(self):
        """All dependency IDs should reference existing tasks."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC_WITH_DEPS)
        plan = TaskPlanner.generate(spec_doc)
        task_ids = {task.id for task in plan.tasks}
        for task in plan.tasks:
            for dep_id in task.dependencies:
                assert dep_id in task_ids, f"Dependency {dep_id} not found"

    def test_topological_sort_possible(self):
        """Should be able to topologically sort the task graph."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC_WITH_DEPS)
        plan = TaskPlanner.generate(spec_doc)
        sorted_tasks = plan.topological_sort()
        assert len(sorted_tasks) == len(plan.tasks)
        # Verify order: dependencies come before dependents
        seen = set()
        for task in sorted_tasks:
            for dep_id in task.dependencies:
                assert dep_id in seen, f"Task {task.id} appears before dependency {dep_id}"
            seen.add(task.id)

    def test_identifies_root_tasks(self):
        """Should identify tasks with no dependencies (starting points)."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC_WITH_DEPS)
        plan = TaskPlanner.generate(spec_doc)
        roots = plan.get_root_tasks()
        assert len(roots) >= 1
        for root in roots:
            assert len(root.dependencies) == 0

    def test_identifies_leaf_tasks(self):
        """Should identify tasks that nothing depends on (end points)."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC_WITH_DEPS)
        plan = TaskPlanner.generate(spec_doc)
        leaves = plan.get_leaf_tasks()
        assert len(leaves) >= 1
        # Verify nothing depends on leaf tasks
        all_deps = set()
        for task in plan.tasks:
            all_deps.update(task.dependencies)
        for leaf in leaves:
            assert leaf.id not in all_deps


class TestAcceptanceCriteriaDerivation:
    """FR-3: AC derivation from spec."""

    def test_ac_derived_from_user_stories(self):
        """AC should reflect requirements from related user stories."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        # At least one task's AC should reference incrementing
        all_ac = " ".join([t.acceptance_criteria for t in plan.tasks])
        assert "increment" in all_ac.lower() or "count" in all_ac.lower()

    def test_ac_derived_from_frs(self):
        """AC should reflect requirements from related FRs."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        # AC should mention specific FR requirements
        all_ac = " ".join([t.acceptance_criteria for t in plan.tasks])
        assert "button" in all_ac.lower() or "display" in all_ac.lower()

    def test_ac_is_specific_and_testable(self):
        """AC should be concrete enough to verify (not vague)."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        vague_terms = ["good", "nice", "fast", "better", "improve"]
        for task in plan.tasks:
            ac_lower = task.acceptance_criteria.lower()
            # AC shouldn't just be vague adjectives
            assert any(
                word not in vague_terms
                for word in ac_lower.split()
            ), f"AC too vague: {task.acceptance_criteria}"


class TestPlanEditing:
    """FR-3.1: Plan editing functionality."""

    def test_can_add_task(self):
        """Should be able to add a new task to the plan."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        original_count = len(plan.tasks)
        new_task = Task(
            title="New Task",
            description="A manually added task",
            acceptance_criteria="It works",
            effort_estimate="S",
            risk_level="low",
            validation_strategy=ValidationStrategy.TEST_AFTER,
        )
        plan.add_task(new_task)
        assert len(plan.tasks) == original_count + 1

    def test_can_delete_task(self):
        """Should be able to delete a task from the plan."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        original_count = len(plan.tasks)
        task_to_delete = plan.tasks[0]
        plan.delete_task(task_to_delete.id)
        assert len(plan.tasks) == original_count - 1

    def test_can_edit_task_title(self):
        """Should be able to modify task title."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        task = plan.tasks[0]
        new_title = "Updated Title"
        plan.update_task(task.id, title=new_title)
        updated_task = plan.get_task(task.id)
        assert updated_task.title == new_title

    def test_can_edit_task_description(self):
        """Should be able to modify task description."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        task = plan.tasks[0]
        new_desc = "Updated description"
        plan.update_task(task.id, description=new_desc)
        updated_task = plan.get_task(task.id)
        assert updated_task.description == new_desc

    def test_can_edit_task_acceptance_criteria(self):
        """Should be able to modify task acceptance criteria."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        task = plan.tasks[0]
        new_ac = "Updated acceptance criteria"
        plan.update_task(task.id, acceptance_criteria=new_ac)
        updated_task = plan.get_task(task.id)
        assert updated_task.acceptance_criteria == new_ac

    def test_can_modify_dependencies(self):
        """Should be able to add/remove task dependencies."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        if len(plan.tasks) >= 2:
            task1 = plan.tasks[0]
            task2 = plan.tasks[1]
            # Add dependency
            plan.add_dependency(task2.id, task1.id)
            updated = plan.get_task(task2.id)
            assert task1.id in updated.dependencies
            # Remove dependency
            plan.remove_dependency(task2.id, task1.id)
            updated = plan.get_task(task2.id)
            assert task1.id not in updated.dependencies

    def test_can_change_test_strategy(self):
        """Should be able to change validation strategy."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        task = plan.tasks[0]
        plan.update_task(task.id, validation_strategy=ValidationStrategy.TEST_FIRST)
        updated = plan.get_task(task.id)
        assert updated.validation_strategy == ValidationStrategy.TEST_FIRST

    def test_can_reorder_tasks(self):
        """Should be able to change task order within constraints."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        if len(plan.tasks) >= 2:
            original_order = [t.id for t in plan.tasks]
            # Swap first two tasks (assuming no dependency conflict)
            plan.reorder_tasks([original_order[1], original_order[0]] + original_order[2:])
            new_order = [t.id for t in plan.tasks]
            assert new_order[0] == original_order[1]


class TestPlanValidation:
    """FR-3.1: Validation before approval."""

    def test_detects_circular_dependency(self):
        """Should detect and reject circular dependencies."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        if len(plan.tasks) >= 2:
            task1 = plan.tasks[0]
            task2 = plan.tasks[1]
            # Create circular dependency
            plan.add_dependency(task2.id, task1.id)
            with pytest.raises(CircularDependencyError):
                plan.add_dependency(task1.id, task2.id)

    def test_circular_dependency_error_is_clear(self):
        """Circular dependency error should identify the cycle."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        if len(plan.tasks) >= 2:
            task1 = plan.tasks[0]
            task2 = plan.tasks[1]
            plan.add_dependency(task2.id, task1.id)
            try:
                plan.add_dependency(task1.id, task2.id)
                assert False, "Should have raised CircularDependencyError"
            except CircularDependencyError as e:
                # Error message should mention the tasks involved
                assert task1.id in str(e) or task2.id in str(e)

    def test_warns_on_orphaned_dependencies(self):
        """Should warn when deleting a task that others depend on."""
        spec_doc = SpecIntake.parse(COMPLEX_SPEC_WITH_DEPS)
        plan = TaskPlanner.generate(spec_doc)
        # Find a task that others depend on
        all_deps = set()
        for task in plan.tasks:
            all_deps.update(task.dependencies)
        if all_deps:
            task_with_dependents = next(t for t in plan.tasks if t.id in all_deps)
            warnings = plan.validate_delete(task_with_dependents.id)
            assert len(warnings) > 0
            assert "depend" in warnings[0].lower()

    def test_warns_on_absurd_task_count(self):
        """Should prompt 'Are you sure?' for excessive task counts."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        # Add many tasks
        for i in range(100):
            plan.add_task(Task(
                title=f"Task {i}",
                description=f"Description {i}",
                acceptance_criteria="Done",
                effort_estimate="XS",
                risk_level="low",
                validation_strategy=ValidationStrategy.NONE,
            ))
        warnings = plan.validate()
        assert any("excessive" in w.lower() or "many" in w.lower() for w in warnings)

    def test_validation_runs_before_approval(self):
        """All validation should run before plan is approved."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        # Trying to approve should trigger validation
        validation_result = plan.approve()
        assert validation_result.validated is True


class TestTaskPlannerLLM:
    """FR-3: LLM integration for task generation."""

    def test_uses_llm_for_task_generation(self):
        """Should use LLM to analyze spec and generate tasks."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        assert plan.llm_model is not None

    def test_llm_receives_full_spec(self):
        """LLM should receive full spec, not trimmed."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        assert plan.spec_length_used == len(BASIC_SPEC)

    def test_handles_llm_timeout(self):
        """Should handle LLM timeout gracefully."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        # Force timeout
        plan = TaskPlanner.generate(spec_doc, timeout_ms=1)
        # Should still return something (fallback behavior)
        assert plan is not None


class TestTaskPlannerOutput:
    """FR-3: Output structure validation."""

    def test_returns_task_plan_object(self):
        """Should return a TaskPlan containing list of Tasks."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        assert isinstance(plan, TaskPlan)
        assert hasattr(plan, "tasks")
        assert all(isinstance(t, Task) for t in plan.tasks)

    def test_task_plan_is_serializable(self):
        """TaskPlan should be JSON serializable."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        json_str = plan.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert "tasks" in parsed

    def test_task_has_unique_id(self):
        """Each task should have a unique identifier."""
        spec_doc = SpecIntake.parse(BASIC_SPEC)
        plan = TaskPlanner.generate(spec_doc)
        ids = [task.id for task in plan.tasks]
        assert len(ids) == len(set(ids)), "Task IDs should be unique"
