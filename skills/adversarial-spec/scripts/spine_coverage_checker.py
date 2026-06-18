"""Spine coverage checker for active TMR records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tmr_schema import TestMaturityRecord


@dataclass(frozen=True)
class SpineCoverageResult:
    """The result of a spine coverage check."""

    passed: bool
    uncovered: list[str]
    duplicate: list[str]


class SpineCoverageChecker:
    """Validates spine coverage over a list of roadmap user stories and TMR records."""

    @staticmethod
    def check(
        roadmap_user_stories: list[str],
        tmr_records: list[TestMaturityRecord],
    ) -> SpineCoverageResult:
        """Run the spine coverage check.

        Rules:
        - Only active records (status == "active") where spine == True are counted.
        - The record must have a single scalar user_story field (i.e. a string).
        - If a record has user_story as a list or has also_covers, it does NOT satisfy
          any secondary/list/also_covers user stories for spine designation.
        - Exactly one active spine designation per user story in roadmap_user_stories -> pass.
        - 0 active spine records for a story in roadmap_user_stories -> uncovered.
        - >=2 active spine records for any story -> duplicate.
        """
        active_spine_counts: dict[str, int] = {}
        for record in tmr_records:
            if record.status != "active":
                continue
            if not record.spine:
                continue
            # Spine designation must be the single scalar primary user_story field.
            if isinstance(record.user_story, str):
                us = record.user_story
                active_spine_counts[us] = active_spine_counts.get(us, 0) + 1
            # If user_story is a list, or we have also_covers, those do NOT satisfy
            # a secondary US for happy-path spine designation.

        uncovered: list[str] = []
        for us in roadmap_user_stories:
            if active_spine_counts.get(us, 0) == 0:
                uncovered.append(us)

        duplicate: list[str] = []
        for us, count in active_spine_counts.items():
            if count >= 2:
                duplicate.append(us)

        # Sort for deterministic output
        uncovered.sort()
        duplicate.sort()

        passed = len(uncovered) == 0 and len(duplicate) == 0

        return SpineCoverageResult(
            passed=passed,
            uncovered=uncovered,
            duplicate=duplicate,
        )


def check_spine_coverage(
    roadmap_user_stories: list[str],
    tmr_records: list[TestMaturityRecord],
) -> SpineCoverageResult:
    """Helper function wrapping SpineCoverageChecker.check."""
    return SpineCoverageChecker.check(roadmap_user_stories, tmr_records)
