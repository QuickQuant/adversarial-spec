# C-TMR-CONTRACT — guarantee-plus-obligation artifact (Phase A/B, v6)

Leaf: `C-TMR-CONTRACT` (card 21545) · session `adv-spec-202609150549-bounded-reform-hardening-align` · authored 2026-09-15 by the conductor (claude). Hash-bound in `obligations.json`.

## Guarantee (what this leaf promises)

The TMR keystone contract carries proof-target identity: a strict `target_binding` on a test record, a runner-owned `target_observation` on code run evidence, expected target fields inside the obligation-identity hash, and a keystone-first packaging that keeps the machine schema, the pinned sha, and the canonical document in agreement. Legacy records stay valid and visibly unbound. Nothing here validates plans (Fizzy) or executes runs (runner); this leaf owns the shapes and their hash.

## Obligations (exactly one primary failing test each; `|T| = |O| = 6`)

| id | obligation | primary test | discharges |
|---|---|---|---|
| O-1 | `TestMaturityRecord.target_binding: TargetProofBinding \| None = None`; strict (extra forbid); round-trips validate → dump → reload byte-equal; `binding_version` const 1; stable ids match `^[A-Z][A-Z0-9_-]{2,127}$` | `test_o1_target_binding_round_trip` | TC-1.0 (contract half), E-1 |
| O-2 | Progressive population at the schema: a binding at maturity `nl`/`acceptance` needs only the identity core (`outcome_id, caller_id, caller_kind, path_id, entrypoint, authority_ref, authority_role`), list fields default to `[]`; at `concrete` every binding field is required and a missing one is a `SchemaValidationError` naming it; `target_binding_status` is a derived field (`bound` \| `legacy-unbound`) accepted on input so a dump re-validates; a stored value disagreeing with the binding is a schema error; a record with no binding validates and dumps `legacy-unbound` | `test_o2_progressive_population_and_legacy_unbound` | TC-1.1, TC-1.2 (schema half), TC-2.0 (schema half), E-8 |
| O-3 | `OBLIGATION_IDENTITY_FIELDS` includes `target_binding`; `compute_tmr_record_hash` changes when any expected target field changes and is unchanged when `run_evidence` (incl. `target_observation`) changes; stored hash never trusted (existing) | `test_o3_hash_projection_expected_in_observed_out` | TC-1.3, keystone §2b (OQ-1) |
| O-4 | `CodeRunEvidence.target_observation: TargetObservation \| None = None`, strict, with runner-only fields `runtime_receipt_id, pid, pid_start_time, outcome_id, caller_id, path_id, entrypoint_observed, authority_ref_observed, producer_contract_hash, consumer_contract_hash, terminal_state`; validates inside a full record | `test_o4_code_run_evidence_target_observation` | TC-5.0 (contract half), E-2, E-31 |
| O-5 | Keystone-first packaging: `KEYSTONE_SCHEMA_SHA256 == schema_sha256()`; `reference/test-maturity-record.schema.json` equals `tmr_json_schema(include_generated_comment=True)`; the leaf ships `keystone-patch.diff` which, applied to a copy of the canonical keystone, pins that same sha and documents `target_binding` and `target_observation` | `test_o5_keystone_first_packaging` | TC-1.4, X-KEYSTONE |
| O-6 | `reference/contract-ownership.json` exists and names one owner per shared contract with each consumer's validation scope: TMR keystone → Brainquarters (adversarial-spec mirrors; runner executes); plan schema + card metadata → fizzy-pipeline-mcp; the record is loadable and every `owner` is one of `Brainquarters`, `adversarial-spec`, `fizzy-pipeline-mcp` | `test_o6_contract_ownership_record` | TC-15.0, E-21 (consumer side) |

Not owned here (attested elsewhere): TC-15.1 (Fizzy validate/load parity, C-PLAN-EMIT / X-FIZZY), compile diagnostics for missing bindings (C-BINDING-COMPILE), observation capture at run time (C-OBS-CAPTURE).

## Controls (A.5)

- **known-good**: `ab_suite/ab_controls/good_contract.py`, a minimal self-contained implementation of the six surfaces; the suite must PASS 6/6 under `AB_CONTROL=good`.
- **known-bad**: the frozen pre-reform tree at commit `b544a00` (modules extracted read-only via `git show`); the suite must FAIL 6/6 under `AB_CONTROL=bad`.
- **target X**: the working tree or a candidate worktree selected by `AB_TARGET_ROOT`; three clean fixed-seed runs must fail with identical fingerprints before candidates exist (red for the right reason).

## Safety (B.3)

The suite touches no live system: it reads files, applies a patch to a temp copy, and never writes the keystone or the repo.
