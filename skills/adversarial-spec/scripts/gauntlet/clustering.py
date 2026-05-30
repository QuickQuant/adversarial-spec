"""Pure-code Jaccard clustering for gauntlet concerns (Layer B).

Replaces the previously-removed haiku-based dedup that lost ~48% of concerns
(see commit 39cba1e fix(CR-8)). The earlier failure mode was an LLM-driven
synthesis pass dropping concerns silently. This module is purely deterministic:
it tokenizes concern text, computes pairwise Jaccard similarity per adversary,
and greedily clusters using single-link at a configurable threshold.

Cross-adversary clustering is OFF by default — different adversary lenses on
the same root cause carry valuable signal that should not be merged.

Auto-trigger: callers should clamp clustering to runs where the post-filter
concern count exceeds CLUSTERING_AUTO_THRESHOLD; below that, pass-through is
fine and the historical CR-8 regression risk is moot.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from gauntlet.core_types import Concern

# Trigger clustering automatically only when N exceeds this. Below this, the
# original "adversary scope handles overlap upstream" assumption holds.
CLUSTERING_AUTO_THRESHOLD = 200

# Greedy single-link Jaccard threshold. 0.65 was chosen empirically to merge
# concerns that share the same root cause without merging mere thematic overlap.
DEFAULT_JACCARD_THRESHOLD = 0.65


# Common English stopwords + adversarial-spec noise. Intentionally short — we
# trim a few high-frequency words to denoise the similarity score, but we don't
# attempt semantic NLP.
_STOPWORDS: frozenset[str] = frozenset(
    """
    a an the of and or to in on for with at by from as is are was were be been
    being have has had do does did this that these those it its will would
    should could may might can not no nor but if then else when where which
    who what whom why how all any some each every both either neither such
    only own same so than too very just also more most less least more
    spec section impact alternative flow consequence production occurrence
    """.split()
)

# Strip common markdown decorations before tokenizing. Note: underscore is NOT
# stripped — it's a legitimate part of code identifiers (e.g. `auth_module`,
# `eval_context`) that the gauntlet adversaries reference frequently.
_MARKDOWN_NOISE = re.compile(r"[`*~\[\]()#>]")
# Tokens are alphanumeric sequences, length >= 2.
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]+")


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip markdown noise, drop stopwords, return a token set."""
    if not text:
        return set()
    cleaned = _MARKDOWN_NOISE.sub(" ", text.lower())
    return {tok for tok in _TOKEN_RE.findall(cleaned) if tok not in _STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Return |a ∩ b| / |a ∪ b|. Both empty → 0.0."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def _pick_representative(members: list[Concern]) -> Concern:
    """Per cluster, pick the concern with the longest text as the representative.

    Longer text typically carries more context (rationale, mitigation, refs)
    and is the better synthesis input. Ties broken by lexicographic id.
    """
    return max(members, key=lambda c: (len(c.text), c.id))


def cluster_concerns(
    concerns: list[Concern],
    *,
    threshold: float = DEFAULT_JACCARD_THRESHOLD,
    cross_adversary: bool = False,
) -> tuple[list[Concern], dict[str, list[Concern]]]:
    """Greedy single-link Jaccard clustering of concerns.

    Args:
        concerns: All concerns to cluster.
        threshold: Minimum Jaccard similarity for two concerns to be in the
            same cluster. Default 0.65.
        cross_adversary: If False (default), only concerns from the same
            adversary may cluster together. If True, clustering ignores the
            adversary boundary.

    Returns:
        (representatives, cluster_members) where:
        - representatives: one Concern per cluster (longest text in the cluster).
        - cluster_members: {representative_id: [member_concerns...]}, including
          the representative itself in the member list.

    Algorithm:
        Single-link: a concern joins an existing cluster iff it is similar
        enough to *any* member of that cluster (not just the representative).
        This is greedy and order-dependent; in practice, ordering is stable
        because the input list is stable.
    """
    if not concerns:
        return [], {}

    # Pre-tokenize once.
    tokens: list[set[str]] = [_tokenize(c.text) for c in concerns]

    # clusters: list of list-of-indices.
    clusters: list[list[int]] = []
    # adv_to_clusters: maps adversary name to a list of cluster references
    # (so single-adversary mode does not scan unrelated clusters).
    adv_to_clusters: dict[str, list[list[int]]] = defaultdict(list)

    for i, concern in enumerate(concerns):
        if cross_adversary:
            candidate_clusters = clusters
        else:
            candidate_clusters = adv_to_clusters[concern.adversary]

        target_cluster: list[int] | None = None
        for cluster in candidate_clusters:
            # Single-link: similarity to ANY existing member is enough.
            for j in cluster:
                if _jaccard(tokens[i], tokens[j]) >= threshold:
                    target_cluster = cluster
                    break
            if target_cluster is not None:
                break

        if target_cluster is not None:
            target_cluster.append(i)
        else:
            new_cluster = [i]
            clusters.append(new_cluster)
            if not cross_adversary:
                adv_to_clusters[concern.adversary].append(new_cluster)

    representatives: list[Concern] = []
    cluster_members: dict[str, list[Concern]] = {}
    for cluster in clusters:
        members = [concerns[idx] for idx in cluster]
        rep = _pick_representative(members)
        representatives.append(rep)
        cluster_members[rep.id] = members

    return representatives, cluster_members


def render_cluster_report(
    concerns: list[Concern],
    representatives: list[Concern],
    cluster_members: dict[str, list[Concern]],
    *,
    threshold: float,
    spec_hash_short: str | None = None,
    cross_adversary: bool = False,
) -> str:
    """Render a markdown report of clusters for human review.

    The report is intentionally compact: one line per representative, one
    indented line per non-representative member. No JSON, no LLM output —
    designed for inspection before promotion to Phase 4.
    """
    lines: list[str] = []
    lines.append("# Cluster Report")
    lines.append("")
    if spec_hash_short:
        lines.append(f"> Spec: {spec_hash_short}")
    lines.append(
        f"> Input: {len(concerns)} concerns → {len(representatives)} clusters "
        f"(reduction: {len(concerns) - len(representatives)})"
    )
    lines.append(f"> Threshold: {threshold:.2f}")
    lines.append(f"> Cross-adversary: {'on' if cross_adversary else 'off'}")
    lines.append("")

    # Per-adversary breakdown so the operator can see where the merging happened.
    by_adv: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for c in concerns:
        before, after = by_adv[c.adversary]
        by_adv[c.adversary] = (before + 1, after)
    for rep in representatives:
        before, after = by_adv[rep.adversary]
        by_adv[rep.adversary] = (before, after + 1)

    lines.append("## Per-adversary reduction")
    lines.append("")
    for adv in sorted(by_adv):
        before, after = by_adv[adv]
        delta = before - after
        lines.append(f"- {adv}: {before} → {after}  (-{delta})")
    lines.append("")

    # Detailed cluster listing, sorted by cluster size (largest first) so the
    # operator sees the biggest dedup wins at the top.
    sorted_reps = sorted(
        representatives,
        key=lambda r: (-len(cluster_members[r.id]), r.id),
    )
    lines.append("## Clusters (largest first)")
    lines.append("")
    for rep in sorted_reps:
        members = cluster_members[rep.id]
        if len(members) == 1:
            # Skip singletons in the detail section — they aren't dedup wins.
            continue
        first_line = rep.text.split("\n", 1)[0][:200]
        lines.append(f"### [{rep.id}] {rep.adversary} — {len(members)} concerns")
        lines.append(f"  Rep: {first_line}")
        for m in members:
            if m.id == rep.id:
                continue
            m_first = m.text.split("\n", 1)[0][:160]
            lines.append(f"    - [{m.id}] {m.adversary}/{m.source_model}: {m_first}")
        lines.append("")

    n_singletons = sum(1 for r in representatives if len(cluster_members[r.id]) == 1)
    if n_singletons:
        lines.append(f"_(skipped {n_singletons} singleton clusters)_")

    return "\n".join(lines) + "\n"


def should_auto_cluster(n_concerns: int, *, threshold: int = CLUSTERING_AUTO_THRESHOLD) -> bool:
    """Return True iff the post-filter concern count crosses the auto-trigger.

    Lifted into a function so the orchestrator decision is unit-testable and
    the threshold can be parameterized via env or config later.
    """
    return n_concerns > threshold


__all__ = (
    "CLUSTERING_AUTO_THRESHOLD",
    "DEFAULT_JACCARD_THRESHOLD",
    "cluster_concerns",
    "render_cluster_report",
    "should_auto_cluster",
)
