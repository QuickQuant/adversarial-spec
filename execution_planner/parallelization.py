"""
FR-6: Parallelization Guidance

Identifies independent workstreams and recommends branch strategies.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from execution_planner.task_planner import TaskPlan, Task


class BranchPattern(Enum):
    """Git branch patterns for parallel execution."""

    SINGLE_BRANCH = "single-branch"
    FEATURE_BRANCHES = "feature-branches"
    STACKED_BRANCHES = "stacked-branches"


@dataclass
class Workstream:
    """A group of tasks that can execute together."""

    stream_id: str
    task_ids: list[str]
    branch_name: Optional[str] = None
    depends_on_streams: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "stream_id": self.stream_id,
            "task_ids": self.task_ids,
            "branch_name": self.branch_name,
            "depends_on_streams": self.depends_on_streams,
        }


@dataclass
class MergePoint:
    """Point where streams need to merge."""

    source_stream: str
    target_stream: str
    merge_order: int
    expected_conflict_risk: str = "low"  # low, medium, high

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "source_stream": self.source_stream,
            "target_stream": self.target_stream,
            "merge_order": self.merge_order,
            "expected_conflict_risk": self.expected_conflict_risk,
        }


@dataclass
class ConflictRecord:
    """Record of a merge conflict for learning."""

    file_path: str
    stream_a: str
    stream_b: str
    recorded_at: str
    resolution_notes: Optional[str] = None


@dataclass
class ParallelizationPlan:
    """Complete parallelization plan for a task plan."""

    streams: list[Workstream] = field(default_factory=list)
    execution_order: list[str] = field(default_factory=list)  # task IDs in order
    merge_sequence: list[MergePoint] = field(default_factory=list)
    branch_pattern: BranchPattern = BranchPattern.SINGLE_BRANCH
    warnings: list[str] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "streams": [s.to_dict() for s in self.streams],
            "execution_order": self.execution_order,
            "merge_sequence": [m.to_dict() for m in self.merge_sequence],
            "branch_pattern": self.branch_pattern.value,
            "warnings": self.warnings,
            "run_id": self.run_id,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class ParallelizationAdvisor:
    """Advises on parallel execution strategies."""

    DEFAULT_CONFLICT_THRESHOLD = 0.3  # 30% conflict rate triggers replanning

    def __init__(
        self,
        conflict_threshold: float = DEFAULT_CONFLICT_THRESHOLD,
    ) -> None:
        self._conflict_threshold = conflict_threshold
        self._conflict_history: list[ConflictRecord] = []
        self._contested_files: set[str] = set()

    def analyze(
        self,
        plan: TaskPlan,
        branch_pattern: BranchPattern = BranchPattern.FEATURE_BRANCHES,
    ) -> ParallelizationPlan:
        """
        Analyze a task plan and create parallelization recommendations.

        Args:
            plan: The task plan to analyze
            branch_pattern: Preferred branch pattern

        Returns:
            ParallelizationPlan with streams and merge sequence
        """
        result = ParallelizationPlan(
            branch_pattern=branch_pattern,
            run_id=uuid.uuid4().hex[:8],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Identify workstreams
        result.streams = self._identify_streams(plan)

        # Generate execution order
        result.execution_order = self._generate_execution_order(plan, result.streams)

        # Generate merge sequence
        result.merge_sequence = self._generate_merge_sequence(result.streams)

        # Assign branch names
        self._assign_branch_names(result, branch_pattern)

        # Add warnings
        result.warnings = self._generate_warnings(plan, result)

        return result

    def _identify_streams(self, plan: TaskPlan) -> list[Workstream]:
        """Identify independent workstreams from task dependencies."""
        streams: list[Workstream] = []
        task_to_stream: dict[str, str] = {}

        # Group tasks by existing stream_id if set
        stream_groups: dict[str, list[str]] = defaultdict(list)
        for task in plan.tasks:
            stream_id = task.stream_id or f"stream-{len(stream_groups) + 1}"
            stream_groups[stream_id].append(task.id)
            task_to_stream[task.id] = stream_id

        # Determine stream dependencies
        for stream_id, task_ids in stream_groups.items():
            depends_on: set[str] = set()

            for task_id in task_ids:
                task = plan.get_task(task_id)
                if task:
                    for dep_id in task.dependencies:
                        dep_stream = task_to_stream.get(dep_id)
                        if dep_stream and dep_stream != stream_id:
                            depends_on.add(dep_stream)

            streams.append(
                Workstream(
                    stream_id=stream_id,
                    task_ids=task_ids,
                    depends_on_streams=list(depends_on),
                )
            )

        return streams

    def _generate_execution_order(
        self,
        plan: TaskPlan,
        streams: list[Workstream],
    ) -> list[str]:
        """Generate task execution order respecting dependencies."""
        # Use topological sort from TaskPlan
        try:
            sorted_tasks = plan.topological_sort()
            return [t.id for t in sorted_tasks]
        except Exception:
            # Fallback to stream-based ordering
            order = []
            for stream in streams:
                order.extend(stream.task_ids)
            return order

    def _generate_merge_sequence(
        self,
        streams: list[Workstream],
    ) -> list[MergePoint]:
        """Generate optimal merge sequence."""
        merge_points: list[MergePoint] = []
        merge_order = 1

        # Find streams that depend on others (they need to be merged into)
        dependent_streams = {
            s.stream_id for s in streams if s.depends_on_streams
        }

        # Independent streams merge first
        independent_streams = [
            s for s in streams if s.stream_id not in dependent_streams
        ]

        # Create merge points for dependent streams
        for stream in streams:
            if stream.depends_on_streams:
                for dep_stream_id in stream.depends_on_streams:
                    # Assess conflict risk based on history
                    risk = self._assess_conflict_risk(stream.stream_id, dep_stream_id)

                    merge_points.append(
                        MergePoint(
                            source_stream=stream.stream_id,
                            target_stream=dep_stream_id,
                            merge_order=merge_order,
                            expected_conflict_risk=risk,
                        )
                    )
                    merge_order += 1

        # Sort by merge order
        merge_points.sort(key=lambda m: m.merge_order)

        return merge_points

    def _assign_branch_names(
        self,
        result: ParallelizationPlan,
        pattern: BranchPattern,
    ) -> None:
        """Assign branch names based on pattern."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")

        for stream in result.streams:
            if pattern == BranchPattern.SINGLE_BRANCH:
                stream.branch_name = "main"
            elif pattern == BranchPattern.FEATURE_BRANCHES:
                # Use stream ID and run ID for uniqueness
                stream.branch_name = f"feature/{stream.stream_id}-{result.run_id}"
            elif pattern == BranchPattern.STACKED_BRANCHES:
                # Include timestamp for stacked branches
                stream.branch_name = f"stack/{stream.stream_id}-{timestamp}"

    def _assess_conflict_risk(
        self,
        stream_a: str,
        stream_b: str,
    ) -> str:
        """Assess conflict risk based on history."""
        # Check conflict history for these streams
        conflicts = [
            c for c in self._conflict_history
            if {c.stream_a, c.stream_b} == {stream_a, stream_b}
        ]

        if len(conflicts) > 5:
            return "high"
        elif len(conflicts) > 2:
            return "medium"
        return "low"

    def _generate_warnings(
        self,
        plan: TaskPlan,
        result: ParallelizationPlan,
    ) -> list[str]:
        """Generate warnings about parallelization plan."""
        warnings = []

        # Check for all tasks in one stream (no parallelization)
        if len(result.streams) == 1:
            warnings.append(
                "All tasks are in a single stream - no parallelization possible. "
                "This may be due to task dependencies."
            )

        # Check for no dependencies (max parallelization but merge risk)
        all_independent = all(
            not stream.depends_on_streams for stream in result.streams
        )
        if all_independent and len(result.streams) > 1:
            warnings.append(
                "All streams are independent - maximum parallelization but "
                "higher merge conflict risk. Consider coordinating file edits."
            )

        # Check for contested files
        if self._contested_files:
            warnings.append(
                f"Files with conflict history: {', '.join(list(self._contested_files)[:5])}. "
                "Avoid concurrent edits to these files."
            )

        # Check for high conflict risk merges
        high_risk = [m for m in result.merge_sequence if m.expected_conflict_risk == "high"]
        if high_risk:
            warnings.append(
                f"{len(high_risk)} merge(s) have high conflict risk. "
                "Consider re-ordering or consolidating tasks."
            )

        return warnings

    def record_conflict(
        self,
        file_path: str,
        stream_a: str,
        stream_b: str,
        resolution_notes: Optional[str] = None,
    ) -> None:
        """Record a merge conflict for learning."""
        record = ConflictRecord(
            file_path=file_path,
            stream_a=stream_a,
            stream_b=stream_b,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            resolution_notes=resolution_notes,
        )
        self._conflict_history.append(record)
        self._contested_files.add(file_path)

    def get_contested_files(self) -> list[str]:
        """Get list of files with conflict history."""
        return list(self._contested_files)

    def check_excessive_conflicts(self) -> tuple[bool, Optional[str]]:
        """
        Check if conflict rate is excessive.

        Returns:
            Tuple of (is_excessive, suggestion if excessive)
        """
        if not self._conflict_history:
            return False, None

        # Simple heuristic: if more than threshold of recent operations conflict
        recent = self._conflict_history[-20:]  # Last 20 records
        if len(recent) >= 5:
            # Check unique file count
            conflicted_files = {c.file_path for c in recent}
            if len(conflicted_files) / max(len(recent), 1) > self._conflict_threshold:
                return True, (
                    "Excessive merge conflicts detected. Consider:\n"
                    "1. Re-planning tasks to reduce file overlap\n"
                    "2. Serializing tasks that touch the same files\n"
                    "3. Breaking up large files into smaller modules"
                )

        return False, None

    def suggest_replanning(self, plan: TaskPlan) -> list[str]:
        """Suggest how to replan to reduce conflicts."""
        suggestions = []

        if self._contested_files:
            suggestions.append(
                f"Files with conflicts: {', '.join(list(self._contested_files)[:5])}. "
                "Consider creating separate tasks for these files."
            )

        # Check for tasks that touch many files
        # (This would need file tracking to be fully implemented)
        suggestions.append(
            "Consider splitting large tasks into smaller, file-focused tasks."
        )

        return suggestions

    def set_conflict_threshold(self, threshold: float) -> None:
        """Set the threshold for excessive conflicts."""
        self._conflict_threshold = max(0.1, min(1.0, threshold))

    def get_parallel_start_tasks(
        self,
        result: ParallelizationPlan,
    ) -> list[list[str]]:
        """
        Get groups of tasks that can start simultaneously.

        Returns:
            List of task ID groups that can run in parallel
        """
        groups: list[list[str]] = []

        # Group by stream for independent streams
        independent_streams = [
            s for s in result.streams if not s.depends_on_streams
        ]

        if independent_streams:
            # All tasks from independent streams can start together
            # (respecting internal dependencies via execution order)
            first_tasks = []
            for stream in independent_streams:
                if stream.task_ids:
                    # Find first task in this stream from execution order
                    for task_id in result.execution_order:
                        if task_id in stream.task_ids:
                            first_tasks.append(task_id)
                            break
            if first_tasks:
                groups.append(first_tasks)

        return groups
