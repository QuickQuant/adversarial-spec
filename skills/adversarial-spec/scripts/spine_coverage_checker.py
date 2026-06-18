"""Spine coverage checker for active TMR records (W0-4 / MW-002).

The one shared implementation of the "≥1 ∧ ≤1 happy-path-spine *designation* per
US" rule (spec S2 / §4.1 / §6, INV-006). Consumed by authoring-lint (warn), F′
(block), TRACE (ORPHANED) and TCOV (promote) — none of them re-implement coverage
logic (DD-6/DD-7).

Contract signature (W0-4): ``(roadmap US set, parsed TMRs, phase) ->
pass | uncovered[] | duplicate[]``. The structural ≥1 ∧ ≤1 rule is itself
phase-independent; ``phase`` is part of the contract so every consumer states the
phase/action it is checking for (e.g. ``"debate"``, ``"gauntlet"``, ``"critique"``,
``"authoring"``, ``"trace"``, ``"tcov"``). It is carried onto the result for
traceability; maturity-awareness (e.g. an ``nl`` spine passing at debate→gauntlet)
is handled by the F′ checker, not by this structural count.
"""

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
    phase: str


class SpineCoverageChecker:
    """Validates spine coverage over a list of roadmap user stories and TMR records."""

    @staticmethod
    def check(
        roadmap_user_stories: list[str],
        tmr_records: list[TestMaturityRecord],
        phase: str,
    ) -> SpineCoverageResult:
        """Run the spine coverage check for ``phase``.

        Rules:
        - Only active records (status == "active") where spine == True are counted.
        - The record must have a single scalar user_story field (i.e. a string).
        - If a record has user_story as a list or has also_covers, it does NOT satisfy
          any secondary/list/also_covers user stories for spine designation.
        - Exactly one active spine designation per user story in roadmap_user_stories -> pass.
        - 0 active spine records for a story in roadmap_user_stories -> uncovered.
        - >=2 active spine records for any story -> duplicate.

        ``phase`` is the consuming phase/action (carried onto the result for
        traceability); the structural ≥1 ∧ ≤1 rule does not vary by phase.
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
            phase=phase,
        )


def check_spine_coverage(
    roadmap_user_stories: list[str],
    tmr_records: list[TestMaturityRecord],
    phase: str,
) -> SpineCoverageResult:
    """Helper function wrapping SpineCoverageChecker.check (W0-4 contract signature)."""
    return SpineCoverageChecker.check(roadmap_user_stories, tmr_records, phase)
