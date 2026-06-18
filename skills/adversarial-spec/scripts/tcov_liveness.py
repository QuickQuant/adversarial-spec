"""TCOV liveness checks and promoter implementation (W2-3 / card 5749)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from tmr_schema import TestMaturityRecord

from criticality_classifier import CriticalityClassifier
from gate_result import GateFinding


class TcovLivenessAuditor:
    """Audits TMR records for test coverage and liveness-gate adequacy."""

    def audit(
        self, records: list[TestMaturityRecord]
    ) -> tuple[list[GateFinding], dict[str, Literal["PROMOTE", "BLOCK"]]]:
        """Runs the TCOV liveness audits on a list of TMR records.

        Steps:
        1. Classifies records using CriticalityClassifier (coercing system altitude unknown to critical).
        2. Gathers any classification findings.
        3. Audits each active record for:
           - missing_liveness_test
           - promoter checks
           - data_strategy_mismatch
        """
        # 1. Classify/resolve records
        classifier = CriticalityClassifier()
        classified_records, findings = classifier.classify(records)

        promotions: dict[str, Literal["PROMOTE", "BLOCK"]] = {}

        for record in classified_records:
            # Skip tombstoned records
            if record.status != "active":
                continue

            uid = record.tmr_uid

            # Accessing fields requires classification first
            critical_seam = record.critical_seam
            data_strategy = record.data_strategy
            live_or_induced = record.live_or_induced
            maturity = record.maturity

            # 1. missing_liveness_test check
            if critical_seam is True and data_strategy == "MOCK" and live_or_induced is None:
                findings.append(
                    GateFinding(
                        code="missing_liveness_test",
                        message=(
                            f"TMR {uid} is a critical seam with MOCK data strategy "
                            f"but has no live_or_induced technique (mock-only critical seam is blocked)."
                        ),
                        severity="blocking",
                        target={"tmr_uid": uid},
                    )
                )

            # 2. Promoter check
            if maturity == "nl":
                if record.accessors and len(record.accessors) >= 1:
                    promotions[uid] = "PROMOTE"
                else:
                    promotions[uid] = "BLOCK"

            # 3. data_strategy_mismatch check
            is_real_data = data_strategy in ("REAL-DATA", "REAL-DATA + PROPERTY")
            why_impossible = record.why_impossible_to_reproduce_live
            is_why_empty = why_impossible is None or not why_impossible.strip()

            if not is_real_data and is_why_empty:
                findings.append(
                    GateFinding(
                        code="data_strategy_mismatch",
                        message=(
                            f"TMR {uid} has non-real data strategy '{data_strategy}' "
                            f"but why_impossible_to_reproduce_live is empty/null."
                        ),
                        severity="blocking",
                        target={"tmr_uid": uid},
                    )
                )

        return findings, promotions
