"""Contract tests for the version-fence resolver (W1-3).

Spec §8.2 / INV-016 / INV-033: fence status is decided by an immutable creation
timestamp vs ``fence_cutover_ts`` — never the editable ``liveness_contract_version``
marker. A post-cutover session cannot be downgraded to legacy by deleting/lowering
its marker; an unfetchable authoritative timestamp or a malformed marker fails
closed as post-fence + ``version_fence_error``.
"""

from __future__ import annotations

import pytest
from contract_version_resolver import (
    ContractVersionResolver,
    VersionFenceError,
    compare_contract_version,
    contract_version_at_least,
    parse_contract_version,
)

pytestmark = pytest.mark.deterministic

CUTOVER = "2026-06-01T00:00:00Z"
LEGACY_TS = "2026-05-01T00:00:00Z"   # < cutover
POST_TS = "2026-06-15T00:00:00Z"     # >= cutover


def resolver_with_card(ts):
    return ContractVersionResolver(
        fence_cutover_ts=CUTOVER,
        card_timestamp_fetcher=lambda card_id: ts,
    )


# --- numeric comparator (US-8): tmr.v10 > tmr.v2, not lexical ----------------

def test_numeric_comparator_beats_string_sort_us8():
    assert parse_contract_version("tmr.v10") == 10
    assert parse_contract_version("tmr.v2") == 2
    assert compare_contract_version("tmr.v10", "tmr.v2") > 0
    assert compare_contract_version("tmr.v2", "tmr.v10") < 0
    assert compare_contract_version("tmr.v1", "tmr.v1") == 0
    assert contract_version_at_least("tmr.v1") is True
    assert contract_version_at_least("tmr.v10") is True
    assert contract_version_at_least("tmr.v0") is False


def test_malformed_version_in_comparator_raises_version_fence_error():
    assert parse_contract_version("tmr.v") is None
    assert parse_contract_version("v1") is None
    assert parse_contract_version(None) is None
    with pytest.raises(VersionFenceError):
        compare_contract_version("tmr.vX", "tmr.v1")


# --- TC-12.0 [spine]: legacy (authoritative created_at < cutover) ------------

def test_tc12_0_legacy_session_keeps_original_rules_spine():
    r = resolver_with_card(LEGACY_TS)
    # legacy even when the local marker is missing or lower
    for marker in (None, "tmr.v0"):
        d = r.resolve(fizzy_card_id="5715", liveness_contract_version=marker)
        assert d.status == "legacy"
        assert d.anchor == "fizzy_card"
        assert d.version_fence_error is False
        assert d.is_post_fence is False


# --- TC-12.1: post-fence held to new gates even with missing/lower marker ----

def test_tc12_1_post_fence_with_missing_or_lower_marker_is_post_fence():
    r = resolver_with_card(POST_TS)
    for marker in (None, "tmr.v0"):
        d = r.resolve(fizzy_card_id="5715", liveness_contract_version=marker)
        assert d.status == "post_fence"
        assert d.version_fence_error is False


def test_tc12_1_marker_only_flip_is_invalid_timestamp_decides():
    # Editing ONLY the marker (timestamp unchanged, post-cutover) must NOT flip
    # the outcome to legacy — defeats the marker-deletion downgrade (INV-033).
    r = resolver_with_card(POST_TS)
    with_marker = r.resolve(fizzy_card_id="5715", liveness_contract_version="tmr.v1")
    without_marker = r.resolve(fizzy_card_id="5715", liveness_contract_version=None)
    assert with_marker.status == without_marker.status == "post_fence"


# --- TC-INV-016: non-retroactive, anchored on authoritative created_at -------

def test_tc_inv_016_outcome_flips_on_created_at_not_marker():
    marker = "tmr.v0"  # identical (lower) marker for both branches
    post = resolver_with_card(POST_TS).resolve(
        fizzy_card_id="5715", liveness_contract_version=marker
    )
    legacy = resolver_with_card(LEGACY_TS).resolve(
        fizzy_card_id="5715", liveness_contract_version=marker
    )
    # positive: post-fence; negative: legacy — only created_at differs.
    assert post.status == "post_fence"
    assert legacy.status == "legacy"


# --- fail-closed: unfetchable authoritative timestamp -----------------------

def test_card_present_but_timestamp_unfetchable_fails_closed_post_fence():
    r = ContractVersionResolver(
        fence_cutover_ts=CUTOVER,
        card_timestamp_fetcher=lambda card_id: None,  # unfetchable
    )
    d = r.resolve(fizzy_card_id="5715", liveness_contract_version="tmr.v1")
    assert d.status == "post_fence"
    assert d.version_fence_error is True
    assert d.anchor == "fizzy_card"


# --- fail-closed: malformed marker ------------------------------------------

def test_malformed_marker_fails_closed_post_fence():
    r = resolver_with_card(LEGACY_TS)  # would be legacy by timestamp
    d = r.resolve(fizzy_card_id="5715", liveness_contract_version="garbage")
    assert d.status == "post_fence"
    assert d.version_fence_error is True


# --- cardless fallback to the editable local created_at tier -----------------

def test_cardless_falls_back_to_local_created_at():
    r = ContractVersionResolver(fence_cutover_ts=CUTOVER)
    legacy = r.resolve(local_created_at=LEGACY_TS)
    post = r.resolve(local_created_at=POST_TS)
    assert legacy.status == "legacy"
    assert legacy.anchor == "local_created_at"
    assert post.status == "post_fence"


def test_cardless_missing_local_created_at_fails_closed_post_fence():
    r = ContractVersionResolver(fence_cutover_ts=CUTOVER)
    d = r.resolve(local_created_at=None)
    assert d.status == "post_fence"
    assert d.version_fence_error is True


# --- W0-3 integration: error surfaces as a typed GateFinding -----------------

def test_version_fence_error_surfaces_as_gate_finding_inv024():
    r = resolver_with_card(LEGACY_TS)
    d = r.resolve(fizzy_card_id="5715", liveness_contract_version="garbage")
    finding = d.as_gate_finding()
    assert finding is not None
    assert finding.code == "version_fence_error"
    assert finding.severity == "blocking"
    # a clean decision has no finding
    assert resolver_with_card(LEGACY_TS).resolve(fizzy_card_id="5715").as_gate_finding() is None
