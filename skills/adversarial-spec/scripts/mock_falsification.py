"""Strict MOCK falsification (W2-4 / US-3, spec §4.3).

A justified MOCK must deny that ANY listed or constructible live/induced technique
could reproduce the behavior. The deterministic rules (the code-tier part; the
"could state-injection/clock-stub force this?" adequacy judgment is the golden-corpus
judgment tier, TC-3.1):

- Keys on real-ness, not the label (DR-8): the requirement applies to EVERY non-REAL
  ``data_strategy`` for a ``critical_seam`` (MOCK / MOCK-EXTERNAL / SYNTHETIC / STATIC /
  FRONTEND), so a critical seam can't dodge it by relabelling itself SYNTHETIC.
- Naming a technique is proof of inducibility -> PROMOTE to REAL-DATA (INV-007). A
  present ``live_or_induced`` on a non-REAL record means the behavior is inducible.
- A critical-seam non-REAL record with an empty ``why_impossible_to_reproduce_live``
  -> PROMOTE (DR-8 hard rule; the schema also requires it, this is the guardrail layer).
- A justified ``MOCK`` (``live_or_induced: null``) must cite a concrete
  ``technical_constraint`` (DD-3) AND a non-empty ``why_impossible_to_reproduce_live``;
  scale / cost / time excuses are NOT impossibility -> PROMOTE (induce via
  state-injection / clock-stub / bounded fixtures).

Accepts a ``TestMaturityRecord`` or a raw mapping (the guardrail runs at authoring
time, possibly pre-validation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Optional

REAL_DATA_STRATEGIES = frozenset({"REAL-DATA", "REAL-DATA + PROPERTY"})

# Scale / cost / time excuses are inducible, not impossibility (spec §4.3).
_EXCUSE_PATTERNS = (
    r"\bslow\b",
    r"\bexpensive\b",
    r"\bcost(s|ly)?\b",
    r"\brate[\s-]?limit",
    r"\bexhaust",
    r"\btoo (many|long|big|large|slow)\b",
    r"\bscal(e|ing|ability)\b",
    r"\bperformance\b",
    r"\btimeout(s)?\b",
    r"2\s*\^\s*\d",       # 2^31
    r"2[²³⁰-⁹]",  # 2³¹ (superscripts)
    r"\bmillions?\b",
    r"\bbillions?\b",
)
_EXCUSE_RE = re.compile("|".join(_EXCUSE_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class MockVerdict:
    outcome: Literal["justified", "promote"]
    reason: str
    promote_to: Optional[str] = None

    @property
    def should_promote(self) -> bool:
        return self.outcome == "promote"


def _get(record: Any, name: str) -> Any:
    if isinstance(record, dict):
        return record.get(name)
    return getattr(record, name, None)


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_named_technique(live_or_induced: Any) -> bool:
    """True if live_or_induced names a present technique (not JSON null)."""
    if live_or_induced is None:
        return False
    # tagged object (record model) or dict with a non-null kind
    kind = _get(live_or_induced, "kind")
    return kind is not None


def is_excuse_constraint(text: Any) -> bool:
    """True if a technical_constraint is a scale/cost/time excuse (not impossibility)."""
    if not _non_empty(text):
        return False
    return _EXCUSE_RE.search(text) is not None


def falsify_mock(record: Any) -> MockVerdict:
    """Apply the strict MOCK falsification rule to one TMR (record or mapping)."""
    data_strategy = _get(record, "data_strategy")
    if data_strategy in REAL_DATA_STRATEGIES:
        return MockVerdict("justified", "REAL-DATA strategy; no MOCK to falsify")

    critical = _get(record, "critical_seam") is True
    why_impossible = _get(record, "why_impossible_to_reproduce_live")
    technical_constraint = _get(record, "technical_constraint")
    live_or_induced = _get(record, "live_or_induced")

    # Naming a technique proves inducibility (INV-007) -> promote.
    if _has_named_technique(live_or_induced):
        return MockVerdict(
            "promote",
            "live_or_induced names a technique => behavior is inducible; promote to REAL-DATA",
            promote_to="REAL-DATA",
        )

    # DR-8: a critical seam on any non-REAL strategy must justify impossibility.
    if critical and not _non_empty(why_impossible):
        return MockVerdict(
            "promote",
            "critical seam on a non-REAL data_strategy with empty "
            "why_impossible_to_reproduce_live; promote to REAL-DATA",
            promote_to="REAL-DATA",
        )

    # DD-3: a justified MOCK (live_or_induced null) needs a cited technical_constraint.
    if data_strategy == "MOCK":
        if not _non_empty(why_impossible):
            return MockVerdict(
                "promote",
                "MOCK with live_or_induced=null requires a non-empty "
                "why_impossible_to_reproduce_live",
                promote_to="REAL-DATA",
            )
        if not _non_empty(technical_constraint):
            return MockVerdict(
                "promote",
                "justified MOCK must cite a concrete technical_constraint (DD-3), "
                "not prose denial",
                promote_to="REAL-DATA",
            )
        if is_excuse_constraint(technical_constraint):
            return MockVerdict(
                "promote",
                "scale/cost/time excuse is not impossibility; induce via "
                "state-injection / clock-stub / bounded fixtures; promote to REAL-DATA",
                promote_to="REAL-DATA",
            )
        return MockVerdict("justified", "MOCK cites a concrete technical_constraint")

    # Non-critical non-REAL, non-MOCK (e.g. SYNTHETIC/STATIC) with a justification.
    return MockVerdict("justified", f"non-critical {data_strategy} accepted")
