# W0-2 Component Mini-Spec

Title: MW-001 StrictArtifactCodec + canonical_sets

artifacts.py + canonical_sets.py: bounded strict decode (dup-member/NaN/BOM/surrogate/negative-zero rejection), schema validation, RFC 8785 JCS, content-hash verify with spec-exact exclusions, domain-prefix signature bytes, authority-signed/local-derived profiles, canonical_set() with bytewise order + duplicate REJECTION, discriminated authorization-fact variants (OR-1, structural absence).

Acceptance criteria:
- byte-level conformance suite (DF-1) green incl. signed-bytes and profile cases
- provisional vs committed deferral facts hash differently
- duplicate set members rejected, never deduplicated

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-2.
Implementation status: greenfield — no codec exists; nearest prior art gauntlet/persistence.py:560-583 stays untouched
