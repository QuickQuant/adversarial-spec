"""Authoring lint for happy-path spine and maturity ladder rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from spine_coverage_checker import SpineCoverageChecker, SpineCoverageResult

if TYPE_CHECKING:
    from tmr_schema import TestMaturityRecord


@dataclass(frozen=True)
class AuthoringFinding:
    code: str
    message: str
    target: dict[str, str]
    severity: Literal["blocking", "warning"] = "blocking"


@dataclass(frozen=True)
class AuthoringLintResult:
    passed: bool
    findings: list[AuthoringFinding]
    spine_coverage: SpineCoverageResult
    promotions: dict[str, Literal["PROMOTE", "BLOCK"]] = field(default_factory=dict)


class AuthoringLint:
    """Validate author-time TMR records before debate/gauntlet promotion."""

    @staticmethod
    def check(
        roadmap_user_stories: list[str],
        records: list[TestMaturityRecord],
    ) -> AuthoringLintResult:
        spine_coverage = SpineCoverageChecker.check(
            roadmap_user_stories,
            records,
            phase="authoring",
        )
        findings: list[AuthoringFinding] = []

        for story in spine_coverage.uncovered:
            findings.append(
                AuthoringFinding(
                    code="missing_spine_designation",
                    message=f"User story {story} has no happy-path spine designation.",
                    target={"user_story": story},
                )
            )

        for story in spine_coverage.duplicate:
            findings.append(
                AuthoringFinding(
                    code="duplicate_spine_designation",
                    message=f"User story {story} has multiple happy-path spine designations.",
                    target={"user_story": story},
                )
            )

        promotions: dict[str, Literal["PROMOTE", "BLOCK"]] = {}
        for record in records:
            if record.status != "active":
                continue

            if record.maturity == "nl":
                promotions[record.tmr_uid] = "PROMOTE" if record.accessors else "BLOCK"

            if not record.spine and record.spine_of and not record.spine_step_ref:
                findings.append(
                    AuthoringFinding(
                        code="missing_spine_step_ref",
                        message=(
                            f"Failure/variant test {record.test_id} cites spine_of "
                            f"{record.spine_of} but has no spine_step_ref."
                        ),
                        target={"test_id": record.test_id, "spine_of": record.spine_of},
                    )
                )

        return AuthoringLintResult(
            passed=spine_coverage.passed and not findings,
            findings=findings,
            spine_coverage=spine_coverage,
            promotions=promotions,
        )
