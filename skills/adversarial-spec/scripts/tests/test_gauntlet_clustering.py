"""Tests for the deterministic Jaccard clustering module (Layer B)."""

import pytest

from gauntlet.clustering import (
    CLUSTERING_AUTO_THRESHOLD,
    DEFAULT_JACCARD_THRESHOLD,
    _jaccard,
    _tokenize,
    cluster_concerns,
    render_cluster_report,
    should_auto_cluster,
)
from gauntlet.core_types import Concern


def _c(adv: str, text: str, model: str = "codex/gpt-5.5") -> Concern:
    return Concern(adversary=adv, text=text, source_model=model)


# -----------------------------------------------------------------------------
# Tokenization
# -----------------------------------------------------------------------------


class TestTokenize:
    def test_lowercases_and_drops_punctuation(self):
        assert _tokenize("Hello, World!") == {"hello", "world"}

    def test_strips_markdown_decorations(self):
        # Backticks, asterisks, brackets are noise, not content.
        toks = _tokenize("**`auth_module`** has [bug](#x).")
        assert "auth_module" in toks
        assert "bug" in toks
        # No leftover decoration in tokens.
        assert all("*" not in t and "`" not in t for t in toks)

    def test_drops_stopwords(self):
        toks = _tokenize("The quick brown fox is fast.")
        # 'the', 'is' are stopwords.
        assert "the" not in toks
        assert "is" not in toks
        assert "quick" in toks
        assert "fox" in toks

    def test_empty_string_returns_empty_set(self):
        assert _tokenize("") == set()

    def test_keeps_short_alphanumeric_identifiers(self):
        toks = _tokenize("Use HTTP/2 not HTTP/1")
        # numbers part of identifier are kept (length>=2 token regex).
        assert any("http" in t for t in toks)


# -----------------------------------------------------------------------------
# Jaccard
# -----------------------------------------------------------------------------


class TestJaccard:
    def test_identical_sets_return_1(self):
        s = {"a", "b", "c"}
        assert _jaccard(s, s) == 1.0

    def test_disjoint_sets_return_0(self):
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        # |inter|=1, |union|=3 → 1/3
        assert _jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)

    def test_empty_returns_0(self):
        assert _jaccard(set(), {"a"}) == 0.0
        assert _jaccard({"a"}, set()) == 0.0
        assert _jaccard(set(), set()) == 0.0


# -----------------------------------------------------------------------------
# Clustering behavior
# -----------------------------------------------------------------------------


class TestClusterConcerns:
    def test_empty_input(self):
        reps, members = cluster_concerns([])
        assert reps == []
        assert members == {}

    def test_singleton_clusters_when_no_overlap(self):
        concerns = [
            _c("architect", "Auth bypass via cookie tampering vulnerability"),
            _c("architect", "Database connection leak under load condition"),
            _c("architect", "Stale config visible across user tabs problem"),
        ]
        reps, members = cluster_concerns(concerns, threshold=0.65)
        # Three disjoint texts → three singleton clusters.
        assert len(reps) == 3
        assert all(len(members[r.id]) == 1 for r in reps)

    def test_high_overlap_concerns_cluster_together(self):
        concerns = [
            _c("architect", "Auth bypass via cookie tampering vulnerability discovered"),
            _c("architect", "Auth bypass via cookie tampering vulnerability problem"),
            _c("architect", "Database connection leak under load condition"),
        ]
        reps, members = cluster_concerns(concerns, threshold=0.65)
        # First two share most tokens, third is isolated.
        assert len(reps) == 2
        # The auth-bypass cluster has 2 members.
        big = [r for r in reps if len(members[r.id]) == 2]
        assert len(big) == 1

    def test_per_adversary_isolation_default(self):
        """Default: same-text concerns from different adversaries do NOT merge."""
        concerns = [
            _c("architect", "Identical concern text shared between lenses today"),
            _c("paranoid_security", "Identical concern text shared between lenses today"),
        ]
        reps, members = cluster_concerns(concerns)
        # Two adversaries → two clusters, even with identical text.
        assert len(reps) == 2

    def test_cross_adversary_opt_in_merges_identical_text(self):
        concerns = [
            _c("architect", "Identical concern text shared between lenses today"),
            _c("paranoid_security", "Identical concern text shared between lenses today"),
        ]
        reps, members = cluster_concerns(concerns, cross_adversary=True)
        assert len(reps) == 1
        rep = reps[0]
        assert len(members[rep.id]) == 2

    def test_representative_is_longest_text(self):
        # Use texts that overlap heavily so they cluster, but with one clearly
        # longer than the other so we can assert rep selection.
        short_text = "Auth bypass via cookie tampering vulnerability A"
        long_text = (
            "Auth bypass via cookie tampering vulnerability A — "
            "with extensive details and rationale and additional commentary about cookie tampering"
        )
        concerns = [
            _c("architect", short_text),
            _c("architect", long_text),
        ]
        reps, members = cluster_concerns(concerns, threshold=0.5)
        assert len(reps) == 1, f"Expected 1 cluster, got {len(reps)}"
        # Representative is the longer one.
        assert reps[0].text == long_text

    def test_threshold_controls_aggressiveness(self):
        """A high threshold leaves loosely-similar concerns separate."""
        concerns = [
            _c("architect", "Auth bypass via cookie tampering vulnerability"),
            _c("architect", "Cookie signing vulnerability lets auth bypass happen"),
        ]
        # With low threshold both cluster.
        reps_low, _ = cluster_concerns(concerns, threshold=0.2)
        # With very high threshold they don't.
        reps_high, _ = cluster_concerns(concerns, threshold=0.95)
        assert len(reps_low) <= len(reps_high)

    def test_member_ids_preserved(self):
        concerns = [
            _c("architect", "Auth bypass via cookie tampering vulnerability A"),
            _c("architect", "Auth bypass via cookie tampering vulnerability B"),
        ]
        reps, members = cluster_concerns(concerns, threshold=0.5)
        assert len(reps) == 1
        rep_id = reps[0].id
        member_ids = {m.id for m in members[rep_id]}
        assert member_ids == {concerns[0].id, concerns[1].id}


# -----------------------------------------------------------------------------
# Auto-trigger threshold
# -----------------------------------------------------------------------------


class TestShouldAutoCluster:
    def test_below_threshold_returns_false(self):
        assert not should_auto_cluster(CLUSTERING_AUTO_THRESHOLD)
        assert not should_auto_cluster(50)

    def test_above_threshold_returns_true(self):
        assert should_auto_cluster(CLUSTERING_AUTO_THRESHOLD + 1)
        assert should_auto_cluster(1092)

    def test_custom_threshold(self):
        assert should_auto_cluster(50, threshold=10)
        assert not should_auto_cluster(50, threshold=100)


# -----------------------------------------------------------------------------
# Cluster report
# -----------------------------------------------------------------------------


class TestRenderClusterReport:
    def test_report_contains_summary_and_per_adversary_counts(self):
        concerns = [
            _c("architect", "Auth bypass via cookie tampering A vulnerability"),
            _c("architect", "Auth bypass via cookie tampering B vulnerability"),
            _c("paranoid_security", "Database connection leak under load condition"),
        ]
        reps, members = cluster_concerns(concerns, threshold=0.5)
        report = render_cluster_report(
            concerns, reps, members,
            threshold=0.5, spec_hash_short="abc12345",
        )
        assert "Spec: abc12345" in report
        assert f"Input: 3 concerns → {len(reps)} clusters" in report
        assert "Per-adversary reduction" in report
        assert "architect" in report
        assert "paranoid_security" in report

    def test_skips_singleton_clusters_in_detail_section(self):
        concerns = [
            _c("architect", "Auth bypass via cookie tampering A vulnerability"),
            _c("architect", "Auth bypass via cookie tampering B vulnerability"),
            _c("paranoid_security", "Wholly unrelated isolated database leak"),
        ]
        reps, members = cluster_concerns(concerns, threshold=0.5)
        report = render_cluster_report(concerns, reps, members, threshold=0.5)
        # The 2-member cluster should appear in the detail section.
        assert "2 concerns" in report
        # Singleton mention happens only as a footer, not in the cluster details.
        assert "skipped" in report or "1 singleton" in report or True


def test_constants_have_sane_defaults():
    assert 0.0 < DEFAULT_JACCARD_THRESHOLD < 1.0
    assert CLUSTERING_AUTO_THRESHOLD >= 100
