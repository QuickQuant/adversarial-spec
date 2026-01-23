"""
FR-5: Over-Decomposition Guards

Prevents excessive task breakdown that adds overhead without value.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from execution_planner.task_planner import TaskPlan, Task
from execution_planner.spec_intake import SpecDocument


@dataclass
class ConsolidationSuggestion:
    """Suggestion for consolidating tasks."""

    task_ids: list[str]
    task_titles: list[str]
    reason: str
    suggested_merged_title: str
    confidence: float = 0.7

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_ids": self.task_ids,
            "task_titles": self.task_titles,
            "reason": self.reason,
            "suggested_merged_title": self.suggested_merged_title,
            "confidence": self.confidence,
        }


@dataclass
class GuardResult:
    """Result of over-decomposition guard check."""

    task_count: int
    threshold: int
    spec_size_factor: float
    exceeds_threshold: bool
    requires_confirmation: bool
    warnings: list[str] = field(default_factory=list)
    suggestions: list[ConsolidationSuggestion] = field(default_factory=list)
    confirmed: bool = False
    checked_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_count": self.task_count,
            "threshold": self.threshold,
            "spec_size_factor": self.spec_size_factor,
            "exceeds_threshold": self.exceeds_threshold,
            "requires_confirmation": self.requires_confirmation,
            "warnings": self.warnings,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "confirmed": self.confirmed,
            "checked_at": self.checked_at,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class OverDecompositionGuard:
    """Guards against excessive task decomposition."""

    # Default settings
    DEFAULT_BASE_THRESHOLD = 10  # Base threshold for small specs
    DEFAULT_TASKS_PER_FR = 3  # Expected tasks per FR
    ABSURD_THRESHOLD = 100  # Threshold that triggers "are you sure?"

    def __init__(
        self,
        base_threshold: int = DEFAULT_BASE_THRESHOLD,
        tasks_per_fr: float = DEFAULT_TASKS_PER_FR,
        config_file: Optional[Path] = None,
    ) -> None:
        self._base_threshold = base_threshold
        self._tasks_per_fr = tasks_per_fr
        self._config_file = config_file

        # Load saved config if exists
        if config_file and config_file.exists():
            self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            with open(self._config_file, encoding="utf-8") as f:
                config = json.load(f)
            self._base_threshold = config.get("base_threshold", self._base_threshold)
            self._tasks_per_fr = config.get("tasks_per_fr", self._tasks_per_fr)
        except (json.JSONDecodeError, IOError):
            pass

    def _save_config(self) -> None:
        """Save configuration to file."""
        if self._config_file:
            config = {
                "base_threshold": self._base_threshold,
                "tasks_per_fr": self._tasks_per_fr,
            }
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

    def set_threshold(
        self,
        base_threshold: Optional[int] = None,
        tasks_per_fr: Optional[float] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Set custom threshold values.

        Returns:
            Tuple of (success, warning message if absurd value)
        """
        warning = None

        if base_threshold is not None:
            if base_threshold >= self.ABSURD_THRESHOLD:
                warning = (
                    f"Setting threshold to {base_threshold} is unusually high. "
                    "Are you sure this is intentional?"
                )
            if base_threshold < 1:
                return False, "Threshold must be at least 1"
            self._base_threshold = base_threshold

        if tasks_per_fr is not None:
            if tasks_per_fr < 0.5:
                return False, "Tasks per FR must be at least 0.5"
            if tasks_per_fr > 10:
                warning = (
                    f"Setting {tasks_per_fr} tasks per FR is very high. "
                    "Are you sure this is intentional?"
                )
            self._tasks_per_fr = tasks_per_fr

        self._save_config()
        return True, warning

    def calculate_threshold(self, spec: Optional[SpecDocument] = None) -> int:
        """Calculate dynamic threshold based on spec size."""
        if not spec:
            return self._base_threshold

        # Scale threshold based on number of FRs
        fr_count = len(spec.functional_requirements)
        scaled_threshold = max(
            self._base_threshold,
            int(fr_count * self._tasks_per_fr),
        )

        return scaled_threshold

    def check(
        self,
        plan: TaskPlan,
        spec: Optional[SpecDocument] = None,
    ) -> GuardResult:
        """
        Check a task plan for over-decomposition.

        Args:
            plan: The task plan to check
            spec: Optional spec document for context-aware threshold

        Returns:
            GuardResult with warnings and suggestions
        """
        task_count = len(plan.tasks)
        threshold = self.calculate_threshold(spec)

        # Calculate spec size factor
        spec_size_factor = 1.0
        if spec:
            fr_count = len(spec.functional_requirements)
            if fr_count > 0:
                spec_size_factor = task_count / fr_count

        exceeds = task_count > threshold

        result = GuardResult(
            task_count=task_count,
            threshold=threshold,
            spec_size_factor=spec_size_factor,
            exceeds_threshold=exceeds,
            requires_confirmation=exceeds,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

        # Add warnings
        if exceeds:
            result.warnings.append(
                f"Task count ({task_count}) exceeds threshold ({threshold}). "
                f"This may indicate over-decomposition."
            )

        if spec_size_factor > 5:
            result.warnings.append(
                f"Average of {spec_size_factor:.1f} tasks per FR is high. "
                "Consider consolidating related tasks."
            )

        # Generate consolidation suggestions
        if exceeds or spec_size_factor > 3:
            result.suggestions = self._find_consolidation_candidates(plan)

        # Special case: threshold of 1 should still warn if exceeded
        if threshold == 1 and task_count > 1:
            result.warnings.append(
                "Threshold is set to 1 - any multi-task plan will trigger warnings."
            )

        return result

    def _find_consolidation_candidates(
        self,
        plan: TaskPlan,
    ) -> list[ConsolidationSuggestion]:
        """Find tasks that could be consolidated."""
        suggestions = []

        # Group tasks by stream
        stream_groups: dict[str, list[Task]] = {}
        for task in plan.tasks:
            stream_id = task.stream_id or "default"
            if stream_id not in stream_groups:
                stream_groups[stream_id] = []
            stream_groups[stream_id].append(task)

        # Look for tasks with similar titles/descriptions
        for stream_id, tasks in stream_groups.items():
            if len(tasks) < 2:
                continue

            # Simple similarity: tasks with common significant words
            for i, task1 in enumerate(tasks):
                for task2 in tasks[i + 1:]:
                    similarity = self._task_similarity(task1, task2)
                    if similarity > 0.5:
                        suggestions.append(
                            ConsolidationSuggestion(
                                task_ids=[task1.id, task2.id],
                                task_titles=[task1.title, task2.title],
                                reason=f"Similar scope (similarity: {similarity:.0%})",
                                suggested_merged_title=self._suggest_merged_title(
                                    task1, task2
                                ),
                                confidence=similarity,
                            )
                        )

        return suggestions[:5]  # Limit to top 5 suggestions

    def _task_similarity(self, task1: Task, task2: Task) -> float:
        """Calculate similarity between two tasks."""
        # Simple word overlap similarity
        words1 = set(task1.title.lower().split())
        words2 = set(task2.title.lower().split())

        # Remove common words
        common_words = {"implement", "add", "create", "the", "a", "an", "for", "to"}
        words1 -= common_words
        words2 -= common_words

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _suggest_merged_title(self, task1: Task, task2: Task) -> str:
        """Suggest a title for merged tasks."""
        # Extract common prefix or use first task's base
        title1 = task1.title
        title2 = task2.title

        # Find common prefix
        common_prefix = ""
        for c1, c2 in zip(title1, title2):
            if c1 == c2:
                common_prefix += c1
            else:
                break

        if len(common_prefix) > 10:
            return f"{common_prefix.strip()} (consolidated)"

        return f"{title1} + related tasks"

    def confirm(self, result: GuardResult) -> GuardResult:
        """Mark a guard result as confirmed by user."""
        result.confirmed = True
        return result

    def apply_consolidation(
        self,
        plan: TaskPlan,
        suggestion: ConsolidationSuggestion,
    ) -> bool:
        """
        Apply a consolidation suggestion to a plan.

        Args:
            plan: The task plan to modify
            suggestion: The consolidation to apply

        Returns:
            True if consolidation was applied
        """
        if len(suggestion.task_ids) < 2:
            return False

        # Find the tasks
        tasks = [plan.get_task(tid) for tid in suggestion.task_ids]
        if not all(tasks):
            return False

        # Keep the first task and update it
        primary_task = tasks[0]
        if primary_task:
            primary_task.title = suggestion.suggested_merged_title

            # Merge descriptions
            descriptions = [t.description for t in tasks if t]
            primary_task.description = "\n\n".join(descriptions)

            # Merge dependencies
            all_deps: set[str] = set()
            for task in tasks:
                if task:
                    all_deps.update(task.dependencies)
            # Remove self-references
            all_deps -= set(suggestion.task_ids)
            primary_task.dependencies = list(all_deps)

        # Delete other tasks
        for task_id in suggestion.task_ids[1:]:
            plan.delete_task(task_id)

        return True
