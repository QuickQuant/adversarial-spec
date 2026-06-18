from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tmr_schema import TestMaturityRecord

from gate_result import GateFinding


class CriticalityClassifier:
    """Sole writer/updater of critical_seam and criticality_source fields in TMR records.

    It should be the only reader of architecture_link.
    """

    def classify(self, records: list[TestMaturityRecord]) -> tuple[list[TestMaturityRecord], list[GateFinding]]:
        """Classifies TMR records and returns the modified records along with any findings."""
        findings: list[GateFinding] = []

        for record in records:
            arch_link = record.architecture_link
            raw_seam = record.critical_seam
            raw_source = record.criticality_source
            altitude = record.altitude

            resolved_seam = raw_seam
            resolved_source = raw_source

            if altitude == "system":
                if arch_link:
                    resolved_source = "architecture_link"
                    if raw_seam is False:
                        resolved_seam = True
                        findings.append(
                            GateFinding(
                                code="DISAGREEMENT_WARNING",
                                message=(
                                    f"TMR {record.tmr_uid} has explicit critical_seam = False but non-empty "
                                    f"architecture_link: {arch_link}. Resolved to True."
                                ),
                                severity="blocking",
                                target={"tmr_uid": record.tmr_uid}
                            )
                        )
                    else:
                        resolved_seam = True
                else:
                    if raw_source == "unknown":
                        resolved_seam = True
            else:
                # Non-system altitude
                if arch_link:
                    resolved_source = "architecture_link"

            record.critical_seam = resolved_seam
            record.criticality_source = resolved_source
            record._classified = True

        return records, findings
