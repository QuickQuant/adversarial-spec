"""Version-fence resolver for the liveness-gate contract (W1-3 / MW-007).

Decides whether a session is ``legacy`` (started before the fence — original
rules, no retroactive failure) or ``post_fence`` (the new F' requirements apply),
anchored on an **immutable creation timestamp** vs a fixed ``fence_cutover_ts`` —
NEVER the editable ``liveness_contract_version`` marker (spec §8.2 / INV-016 /
INV-033).

Read order (the anti-downgrade contract):
  1. ``fizzy_card_id`` present -> use the authoritative server-side Fizzy
     session-card creation timestamp (fetched via an injected callable). If the
     card exists but the timestamp is **unfetchable**, fail closed as post-fence
     and emit ``version_fence_error`` (the DR-7 honest-mistake guard) — never
     silently fall back to the editable local value.
  2. cardless / local-only sessions -> fall back to the editable local
     ``session-state.json`` ``created_at`` tier; missing/malformed -> fail closed
     as post-fence.
A missing or lower marker on a session whose authoritative ``created_at`` >=
``fence_cutover_ts`` is POST-fence (a deleted/edited marker cannot downgrade); a
session is legacy ONLY if its authoritative ``created_at < fence_cutover_ts``.

The comparator is numeric (``tmr.v<N>`` with N compared as a base-10 int, so
``tmr.v10 > tmr.v2``); a malformed / non-``tmr.v<int>`` marker is a named
``version_fence_error``, fail-closed as post-fence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Literal, Optional

from gate_result import GateFinding

CONTRACT_VERSION_RE = re.compile(r"^tmr\.v(\d+)$")
REQUIRED_CONTRACT_VERSION = "tmr.v1"

# Activation cutover for tmr.v1 enforcement. Finalized at the fizzy-side
# handshake/deploy (the R4 activation rule); sessions whose authoritative
# created_at predates this are legacy and keep their original rules.
DEFAULT_FENCE_CUTOVER_TS = "2026-06-18T00:00:00+00:00"

FenceStatus = Literal["legacy", "post_fence"]
FenceAnchor = Literal["fizzy_card", "local_created_at"]

# A fetcher maps a fizzy_card_id -> the card's creation timestamp (ISO string or
# datetime), or None when unfetchable. Injected so the resolver stays pure and
# unit-testable; production wiring calls the Fizzy MCP.
TimestampFetcher = Callable[[str], Optional[object]]


class VersionFenceError(ValueError):
    """Named fail-closed error: malformed marker or unfetchable authoritative ts."""

    def __init__(self, detail: str) -> None:
        self.code = "version_fence_error"
        self.detail = detail
        super().__init__(f"{self.code}: {detail}")


@dataclass(frozen=True)
class FenceDecision:
    status: FenceStatus
    anchor: FenceAnchor
    version_fence_error: bool
    detail: str

    @property
    def is_post_fence(self) -> bool:
        return self.status == "post_fence"

    def as_gate_finding(self) -> Optional[GateFinding]:
        """Surface a ``version_fence_error`` as a typed W0-3 GateFinding (INV-024)."""
        if not self.version_fence_error:
            return None
        return GateFinding(
            code="version_fence_error",
            message=self.detail,
            severity="blocking",
            target={"anchor": self.anchor},
        )


def parse_contract_version(value: object) -> Optional[int]:
    """Return N from ``tmr.v<N>``; None if missing/None/malformed (never raises)."""
    if not isinstance(value, str):
        return None
    match = CONTRACT_VERSION_RE.match(value.strip())
    if match is None:
        return None
    return int(match.group(1))


def compare_contract_version(a: str, b: str) -> int:
    """Numerically compare two ``tmr.v<N>`` strings (-1/0/1).

    Malformed input raises ``VersionFenceError`` (never a silent lexical compare).
    """
    na, nb = parse_contract_version(a), parse_contract_version(b)
    if na is None:
        raise VersionFenceError(f"malformed contract version: {a!r}")
    if nb is None:
        raise VersionFenceError(f"malformed contract version: {b!r}")
    return (na > nb) - (na < nb)


def contract_version_at_least(
    value: object, minimum: str = REQUIRED_CONTRACT_VERSION
) -> bool:
    """True iff ``value`` (``tmr.v<N>``) >= ``minimum``. Malformed -> VersionFenceError."""
    n = parse_contract_version(value)
    if n is None:
        raise VersionFenceError(f"malformed or missing contract version: {value!r}")
    floor = parse_contract_version(minimum)
    if floor is None:  # pragma: no cover - defensive; constant is well-formed
        raise VersionFenceError(f"malformed minimum: {minimum!r}")
    return n >= floor


def _parse_ts(value: object) -> Optional[datetime]:
    """Parse an ISO-8601 string or datetime to an aware datetime; None if invalid."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


class ContractVersionResolver:
    """Resolve fence status from an immutable timestamp, not the editable marker."""

    def __init__(
        self,
        *,
        fence_cutover_ts: object = DEFAULT_FENCE_CUTOVER_TS,
        card_timestamp_fetcher: Optional[TimestampFetcher] = None,
    ) -> None:
        cutover = _parse_ts(fence_cutover_ts)
        if cutover is None:
            raise ValueError(f"invalid fence_cutover_ts: {fence_cutover_ts!r}")
        self._cutover = cutover
        self._fetch = card_timestamp_fetcher

    def resolve(
        self,
        *,
        fizzy_card_id: Optional[str] = None,
        local_created_at: object = None,
        liveness_contract_version: object = None,
    ) -> FenceDecision:
        anchor: FenceAnchor = "fizzy_card" if fizzy_card_id else "local_created_at"

        # A present-but-malformed marker fails closed (a missing/None marker is
        # fine — the timestamp read order decides, not the marker).
        if (
            liveness_contract_version is not None
            and parse_contract_version(liveness_contract_version) is None
        ):
            return FenceDecision(
                "post_fence",
                anchor,
                True,
                f"malformed liveness_contract_version {liveness_contract_version!r}",
            )

        # Tier 1: authoritative Fizzy card timestamp.
        if fizzy_card_id:
            raw = self._fetch(fizzy_card_id) if self._fetch is not None else None
            ts = _parse_ts(raw)
            if ts is None:
                return FenceDecision(
                    "post_fence",
                    "fizzy_card",
                    True,
                    "authoritative Fizzy card timestamp unfetchable",
                )
            return self._classify(ts, "fizzy_card")

        # Tier 2: editable local created_at fallback.
        ts = _parse_ts(local_created_at)
        if ts is None:
            return FenceDecision(
                "post_fence",
                "local_created_at",
                True,
                "local created_at missing/malformed",
            )
        return self._classify(ts, "local_created_at")

    def _classify(self, ts: datetime, anchor: FenceAnchor) -> FenceDecision:
        if ts < self._cutover:
            return FenceDecision("legacy", anchor, False, "created_at < fence_cutover_ts")
        return FenceDecision("post_fence", anchor, False, "created_at >= fence_cutover_ts")
