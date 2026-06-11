# Post-Gauntlet Guardrails — spec-draft-v5 (2026-06-11)

Run after incorporating gauntlet concerns (48 accepted themes from
`gauntlet-concerns-2026-06-11.json`) into v5.

## CONS (consistency) — PASS after 2 fixes

Found and fixed:
1. Mutator-count mismatch: §6.2 said "six" while listing seven subcommands,
   and §7 said "seven" while `record-evidence` (which writes the row's
   `evidence_summary` into the ledger) was omitted from the owner list.
   Fixed: canonical list is EIGHT mutators, identical in §6.2 and §7.
2. `record-evidence` described as "mutating via normalize path" — vague
   ownership. Fixed: it is a first-class ledger mutator in the owner list.

Checked clean (no contradiction found): S6/S6b needs-reexecution flow vs
delta-digest inclusion rule (INV-4 forces fresh evidence before re-digest);
close-algorithm step 4 fail-routing vs NOTHING_TO_DIGEST; INV-5 vs re-entry
(self-check always re-runs — CB-5 fix held everywhere); batch status enum
consistent across §6.2 schema, lifecycle prose, §7, and TC-G1; full-hash
local storage vs 12-hex artifact emission (§6.2/§6.4/SEC-8); supersession
rule identical in §6.2 refresh rule, S7, INV-3, INV-13 (any state,
human-approved); story-removal-via-manifest consistent in §4.8, §6.1, INV-2.

## CANON (named types/enums/contracts) — PASS after 2 amendments

1. TC-INV-A4 (Phase 4 block) still described the v4 `--sender-id` interface;
   amended to the v5 `--update-file` payload-extraction contract (cross-ref
   TC-G3). The P4 invariant itself (INV-A4 allowlist, no hardcoded ids) is
   unchanged.
2. TC-INV-A7 referenced `--reset-failed` as an assemble-digest flag; amended
   to the standalone `reset-failed` subcommand (DD-1).

Checked clean: result enum `pass|fail|not-applicable` + `na` mapping
(§6.2/§6.4/grammar/TC-G8); row_id regex everywhere; alias list §6.5 == TC-G2;
local error-code names §7 == §10 == TC-G*; batch states; `approval_ref`
format §6.2 == INV-3 == TC-G5; INV numbering additive (INV-16/17 new, none
renumbered).

## TCOV (test coverage of new/changed semantic claims) — PASS after 1 addition

Added TC-G1..G12 with the v5 revision; TCOV sweep found one uncovered claim:
derive-conops lints (stray US-id, duplicate story ids, overwrite safety,
story_hashes map — CB-11/DD-7/FM-3 derivation half) → added TC-G13.

Coverage map (new claim → TC): INV-16 delivery gate → TC-G1; natural aliases
→ TC-G2; payload sender extraction + fail-closed config → TC-G3; per-story
evidence binding → TC-G4; any-state transactional supersession → TC-G5;
reply_ref idempotency + edited messages → TC-G6; terminal provenance →
TC-G7; grammar tightenings (fail justification, duplicates, continuation,
case rules, ordering) → TC-G8; secret lint + row byte budget + digest dir →
TC-G9; re-entry routing + INV-5-always + TOCTOU hash check → TC-G10;
normalize-rows as sole hash producer → TC-G11; status command → TC-G12;
derive lints → TC-G13.

Deferred-minor (documented, not separately tested): per-part message-id →
batch binding is asserted inside TC-G3/TC-G1 rather than its own TC; commit
cadence and remediation-card payload are `[conductor]` procedures measured at
dogfood (TC-4.1 metrics), consistent with the enforcement legend.

SCOPE/TRACE: not run — gauntlet fixes were Claude-evaluated revisions, no
user-visible scope expansion, requirement coverage unchanged (per 05-gauntlet
§7 guidance).
