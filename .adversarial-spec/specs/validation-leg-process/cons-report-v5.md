# CONS Report — spec-draft-v5.md (post-gauntlet reconciliation, 2026-06-11)

Consistency sweep over the revised spec after incorporating 48 accepted gauntlet
themes (full detail: post-gauntlet-guardrails.md).

CONTRADICTION: Ledger mutator count — §6.2 said "six" while listing seven
subcommands, and §7 said "exactly seven" while omitting record-evidence (which
writes the row's evidence_summary into the ledger).
RESOLVED: Canonical owner list is EIGHT mutators (normalize-rows,
record-evidence, parse-reply, assemble-digest, record-send, cancel-batch,
reset-failed, supersede-row), stated identically in §6.2 and §7; record-evidence
explicitly marked mutating.

CONTRADICTION: record-evidence ownership ambiguity — described as "mutating via
normalize path" while absent from the mutation-ownership list, leaving its lock
discipline unspecified.
RESOLVED: record-evidence is a first-class ledger mutator in the §7 owner list;
it takes validation-rows.json.lock like every other mutator.

Checked clean (no contradiction found): S6/S6b needs-reexecution vs delta-digest
inclusion (INV-4 forces fresh evidence); close-algorithm fail-routing vs
NOTHING_TO_DIGEST (CB-5 fix); INV-5 self-check-always vs re-entry shortcuts;
batch status enum across §6.2 schema/lifecycle prose/§7/TC-G1; full-hash local
storage vs 12-hex artifact emission; supersession rule across §6.2/S7/INV-3/
INV-13 (any state, human-approved); story-removal-via-manifest across
§4.8/§6.1/INV-2; result enum + na mapping across §6.2/§6.4/grammar.

Final state: all detected contradictions resolved in spec-draft-v5.md.
