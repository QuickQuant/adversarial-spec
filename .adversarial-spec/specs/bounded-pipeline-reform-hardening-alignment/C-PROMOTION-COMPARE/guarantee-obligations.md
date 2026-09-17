# C-PROMOTION-COMPARE — guarantee-plus-obligation artifact (Phase A/B, v6)

Leaf: `C-PROMOTION-COMPARE` (card **21549**) · Session
`adv-spec-202609150549-bounded-reform-hardening-align` · authored 2026-09-15 by
Codex at Jason's instruction. Hash-bound in `obligations.json`. This is the
**A/B authoring package**; product implementation belongs to subsequent candidate
work. `.adversarial-spec/session-state.json` reports pipeline Phase **debate**.
A/B names the bounded-leaf procedure, not additional pipeline phases.

## Guarantee (what this leaf promises)

Promotion compares a validated obligation with supplied runner evidence, rejects
wrong targets and incomplete runtime joins, applies the policy-owned freshness
rule, detects typed replacement producers, and names uncovered terminal states.
Every rejection explains the affected test/obligation, expected and observed
values, evidence class, next actor, and permitted recovery. The pure functions
neither execute a proof nor manufacture missing evidence.

D0 ownership: **R-4, R-6, R-18**. Inputs are typed fixture provenance, validated
target bindings, runner captures, and explicit comparison facts. State/effect
authority: **none**. Failure authority: promotion verdict and diagnostic shape.

| edge / boundary | direction | guarantee supplied here / limit |
|---|---|---|
| E-2 | C-TMR-CONTRACT → this leaf | Consume `TargetProofBinding`, `TargetObservation`, `CodeRunEvidence`; retain their strict schema |
| E-3 | C-GATE-POLICY → this leaf | Consume `RejectCode`, `EnforcementMode`, `is_receipt_fresh`, `FRESHNESS_WINDOW_SECONDS`; policy owns the version/date fence |
| E-7 | C-OBS-CAPTURE → this leaf | Consume `TargetObservationCapture` from `capture_run_evidence`; incomplete captures cannot acquire a result during comparison |
| E-8 | C-BINDING-COMPILE → this leaf | Consume validated records with `target_binding` and derived `target_binding_status`; never write the binding or registry |
| E-12 | C-OBS-CAPTURE → C-CUSTODY-RECONCILE | Preserve the partial/absent capture while evaluating it; no result synthesis, receipt mutation, or custody write |
| E-17 | C-GOLDEN-HARNESS → this leaf | Expose pure callable validators so harness fixture adapters can collect actual issue codes |

**D0 direction clarification:** the request groups E-12/E-17 as produced
interfaces. The manifest assigns E-12 receipt production to **C-OBS-CAPTURE**
and the E-17 call to **C-GOLDEN-HARNESS**. This leaf supplies comparison verdicts
and receipt preservation, not a second capture producer or replay harness.

**Owned roadmap coverage:** TC-5.0 S3/S4 (promotion half), TC-5.1, TC-5.2,
TC-5.5, TC-6.0/6.1/6.2, TC-13.0 diagnostic/recovery-data contract, TC-13.1.
**Not owned:** TC-5.3 and TC-5.4 capture-side behavior (**C-OBS-CAPTURE**, already
Synthesized); TC-13.2 unavailable reviewer (**review-plane**); the golden replay
harness (**C-GOLDEN-HARNESS**). This package tests pure freshness/process-identity
comparison with synthetic facts; it does not claim TC-5.4's real process restart
acceptance. TC-13.0's three live worker-seat recoveries are downstream usability
acceptance, not established by checking payloads. TC-5.0's real command execution
and capture remain the capture half of the composed proof.

### Public comparison surface (E.4)

**Extend, do not rewrite** `skills/adversarial-spec/scripts/phase8_promotion.py`.
Preserve `PromotionRequest`, `RunExecution`, `TargetObservationCapture`,
`capture_run_evidence`, and existing close checks. Add:

```python
compare_target_observation(binding, observation, *, now, cutover_mode) -> list[PromotionIssue]
classify_fixture_provenance(record) -> PromotionIssue | None
terminal_enum_coverage(binding, reachable_states) -> PromotionIssue | None
diagnose(issue, record) -> RejectionDiagnostic
evaluate_phase8_close(
    records, *, now=None, cutover_mode="legacy", comparison_contexts=None,
) -> Phase8PromotionReport
```

`binding` is the canonical binding mapping with an ephemeral `_comparison`
mapping. `observation` is the E-7 capture envelope with an ephemeral
`_comparison` mapping, or `None`. Neither projection is persisted or passed as
an expanded canonical schema object. `now` is an explicit timezone-aware
`datetime` or ISO-8601 string for new comparisons; no clock sampling. The old
one-argument close call remains usable in legacy mode.

`requires_target_binding(record) -> bool` is a small integration surface for
the existing trigger policy. The oracle requires **False for CTRL-001**; this
leaf does not redesign architecture/path trigger discovery. Active spine,
critical-seam, or runtime-chain obligations in this suite require comparison.
The known-good control implements only those exercised triggers. Candidates
must retain broader upstream trigger semantics.

### Comparison context: explicit data missing from the frozen schema

The frozen E-2 observation contains receipt ID, PID/start time, intended
outcome/caller/path labels, actual entrypoint/authority reference, two contract
hashes, and terminal state. It has **no** captured timestamp, target ref,
observed caller kind, observed authority role, or source/package/activation
join fields. E-7 supplies timestamp/ref outside E-2. Capture deliberately labels
caller/path from the request binding, so equality of those labels alone cannot
establish the actual caller/path.

This package fixes a **consumer-only comparison context**, rather than adding
unrepresentable fields to TMR or rewriting the already Synthesized capture
contract. Its collection/authentication is an explicit upstream assumption.
The existing modules do not already populate this additional context.

```python
comparison_contexts[tmr_uid] = {
    "capture": TargetObservationCapture | None,
    "expected": {
        "target_ref": str,  # current opaque resolved source/artifact identity
        "real_producer_boundaries": list[str],
        "runtime_slots": {
            slot_id: {"intended_source": str, "pid": int, "pid_start_time": str},
        },
    },
    "observed": {
        "caller_id_observed": str,
        "caller_kind_observed": "product" | "operator" | "system" | "harness",
        "path_id_observed": str,
        "authority_role_observed": "authoritative" | "projection" | "legacy" |
                                   "emergency" | "retiring" | "dead",
        "runtime_slots": {
            slot_id: {
                "packaged_source": str, "activation_source": str,
                "running_source": str, "gateway_source": str,
                "pid": int, "pid_start_time": str,
            },
        },
    },
    "reachable_states": list[str],
}
```

All runtime-slot IDs come from the binding's `runtime_slots`. `expected.pid`
and `expected.pid_start_time` mean the **currently sampled process identity**,
not an owner-selected future PID. Observed values come from the captured
runtime join. The first slot is the capture's primary process; its identity
also equals E-2's PID/start time. Other shipped slots have their own identities.
When `runtime_chain_required` is false, source/process joins are not demanded.
When true, all declared slots must be represented. The golden listener mapping
uses gateway source as the join's final reporter source; applications must
supply the applicable source identity, never invent one from intended source.

`expected.real_producer_boundaries` is an exact-name projection of the
obligation's required real producers, supplied by the validated obligation's
owner. It is independent of a fixture author's `claim_ceiling`, helper name,
data-strategy label, or prose. No substring boundary matching. An explicit
empty list means no such boundary is required. Nonempty provenance with no
boundary-requirement projection is invalid input (`ValueError`), not a silent
permission to pass. E-8 owns typed kind validation; invalid kind input also
fails fast instead of being treated as `none`.

For comparison, close projects `context.expected` into
`binding["_comparison"]` and `context.observed` into
`observation["_comparison"]`. For classification, it projects
`context.expected` into `record["_comparison"]`. The unmodified capture and
canonical record remain available to custody and other consumers.

**Trust limit:** measured context must come from trusted runner/census/runtime
join inputs. Owner-written strings, receipt IDs, and a JSON `"runner"` marker
do not authenticate themselves. Missing measured caller/path/role is incomplete
evidence even when capture's intended labels match. No new live collector or
authentication mechanism is delivered by this package. No caller equivalence
is inferred from a nonempty reference; the pinned wrong-caller case has no
equivalence proof, and references alone cannot waive a mismatch.

### Comparison, severity, and close semantics

1. Check capture completeness and origin before target comparisons. An absent
   observation, INCOMPLETE capture, missing identity, or missing measured
   caller/path/role produces `RUNTIME_IDENTITY_INCOMPLETE` with class `MISSING`.
   The complete capture's `runtime_receipt` must equal its nested
   `run_evidence.target_observation`. Owner origin or a detached nested
   observation produces the same code with class `UNSUPPORTED_ORIGIN`.
   These rows return no `PROOF_*` mismatch. A stored green record cannot replace
   an absent supplied capture. Null/partial `run_evidence` stays null/partial;
   comparison never stamps `result`.
2. Compare measured caller ID/kind, path ID plus actual entrypoint, and actual
   authority ref plus measured role against the bound values. Emit each
   applicable typed mismatch; do not stop after the first of the three.
   Compare outcome and producer/consumer hashes independently. `env: live`,
   matching accessors, fresh timestamps, and matching intended labels cannot
   widen evidence to a different path or authority.
3. Call **`gate_policy.is_receipt_fresh(captured_at, now,
   target_ref_at_capture=capture.target_ref, target_ref_now=expected.target_ref)`**.
   Accept ages **0 through `FRESHNESS_WINDOW_SECONDS` inclusive**; frozen policy
   defines **86400**. One second beyond, future timestamps, or changed resolved
   ref/hash invalidate. Emit `RUNTIME_IDENTITY_INCOMPLETE`, class `STALE`.
   A missing/malformed timestamp is incomplete evidence, class `MISSING`.
   No duplicate local freshness formula. A PID/start-time change independently
   invalidates inside the age window. The function never queries procfs or Git.
4. For each required runtime slot, compare intended → packaged → activated →
   running → reporter source identities. A broken/missing source link emits
   both `RUNTIME_IDENTITY_INCOMPLETE` and `PACKAGE_COMPONENT_UNPROVEN`. Identify
   the slot and broken link, including `activation_source -> running_source`
   for golden -007. A missing shipped slot cannot disappear from the comparison.
5. `terminal_enum_coverage` computes the sorted, unique difference
   `reachable_states - terminal_oracle.accepted_states`. Return `None` only if
   empty; otherwise `TERMINAL_ENUM_UNCOVERED` with
   `observed.uncovered_states`. Compare also checks the actual terminal state.
   Close checks the **whole supplied reachable set**, even when the present run
   completed or a capture is partial. A timeout is not evidence of enum coverage.
6. `classify_fixture_provenance` examines **each**
   `record["target_binding"]["fixture_provenance"]` entry. At a required real
   producer boundary, `recorded`, `constructed`, `stub`, and `mock` produce
   `FIXTURE_PROVENANCE_CEILING`; `none` and `real-source` do not. Entries at
   unrelated boundaries do not impose a ceiling. A first safe entry cannot
   hide a later substitution. Return one issue naming the first offending
   boundary; this return type does not promise a complete census of substitutions.
7. `_lint_boundary_mock` keeps code `boundary_mock_detected`, but its severity
   is always **`advisory`**. It never halts. No typed substitution is inferred
   from the phrase `Verified real test - no mocks used anywhere`.
8. Consume the **already resolved** gate-policy mode. `reject` maps new issues
   to **`halt`**; `warn` maps them to **`warning`**. `legacy` skips the new
   enforcement checks while preserving old close checks and advisory lint.
   Unknown mode raises `ValueError`. `Phase8PromotionReport.can_close` ignores
   `warning`/`advisory`, but remains false for `halt`/`failing`. Existing missing
   oracle, unbound accessor, non-green/untrusted run, exemption, and dev/ci
   technique rules retain blocking behavior. Warning-mode permission to close
   is a rollout decision, not a passing evidence assertion.

Every emitted `PROOF_*`, `RUNTIME_*`, `FIXTURE_*`, and `TERMINAL_*` code must be
an exact `gate_policy.RejectCode` member by string equality. Package/contract
codes used here must also match that enum. Do not fork it. Pure helpers return
`PromotionIssue` values; close attaches the owning `tmr_uid` and applies mode
to classifier/terminal issues. Helpers take no filesystem, network, subprocess,
registry, or board actions; all returned data is detached from mutable inputs.

### RejectionDiagnostic: exact required shape

```python
@dataclass(frozen=True)
class RejectionDiagnostic:
    code: str
    message: str
    test_id: str
    obligation_id: str
    expected: dict
    observed: dict
    evidence_class: Literal["MISSING", "MISMATCH", "STALE", "UNSUPPORTED_ORIGIN"]
    next_actor: str
    permitted_recovery: list[str]
```

A JSON-serializable dict with these keys is also accepted. `obligation_id`
equals the durable **record.tmr_uid**, not the display test ID or package O-number.
`expected`/`observed` carry at least `field` and `value`, naming the affected
path, boundary, runtime slot/link, or terminal-oracle field. Terminal diagnostics
add `observed.uncovered_states`. Missing values remain null/absent observations;
never copy expected values into observed to fill a gap. Messages contain a plain
explanation, not just the reject code. No exact prose wording is frozen.

`PromotionIssue` retains existing positional fields `code, tmr_uid, message,
severity`; candidates may add `expected`, `observed`, and `evidence_class` with
defaults to carry structured data to `diagnose`. `diagnose` must not parse a
free-text message to recover missing structure.

For these fixtures, `next_actor` is **`worker`**. Permitted recovery is a nonempty
list: rerun the bound caller/path/authority; obtain a complete fresh runtime
join; activate the intended package and rerun each affected process; use the
real producer; or add the named terminal states to the oracle and rerun. A path
mismatch's recovery names the expected path, so the diagnostic alone identifies
the next run. It grants no bypass, destruction, or unrelated obligation reset.

### Decision rows (A / B.1)

| row | input | required output / class |
|---|---|---|
| B.1 match | Validated bound record, complete matching capture/context, fresh ref/identity, covered terminals | `[]`; `can_close=True` |
| A caller | Actual caller ID or kind differs | `PROOF_CALLER_MISMATCH` / MISMATCH |
| A path | Actual path ID or entrypoint differs | `PROOF_PATH_MISMATCH` / MISMATCH |
| A authority | Actual authority ref or role differs, including legacy/emergency/dead | `PROOF_AUTHORITY_ROLE_MISMATCH` / MISMATCH |
| A outcome | Observation outcome differs | `PROOF_OUTCOME_MISMATCH` / MISMATCH |
| A contracts | Either observed hash differs | `PRODUCER_CONSUMER_CONTRACT_UNPROVEN` / MISMATCH |
| A old process | Running source differs from fresh activated package | `RUNTIME_IDENTITY_INCOMPLETE` + `PACKAGE_COMPONENT_UNPROVEN` / MISMATCH |
| A missing slot/link | Any required shipped process or source join absent | Same two runtime/package codes / MISSING |
| B.1 repaired join | Fresh package activated and all required running/reporting sources match | No runtime/package issue; close succeeds |
| B.1 freshness boundary | Age 0, 86399, or 86400 seconds, same ref/identity | No freshness issue |
| A stale receipt | Age 86401, future timestamp, changed ref/hash, PID, or start time | `RUNTIME_IDENTITY_INCOMPLETE` / STALE |
| A absent identity | Observation absent, partial capture, missing receipt ID/PID/start time, missing measured caller/role/time | `RUNTIME_IDENTITY_INCOMPLETE` / MISSING; no PROOF_*; cannot close in reject mode |
| A origin | Owner origin or receipt differs from nested observation | `RUNTIME_IDENTITY_INCOMPLETE` / UNSUPPORTED_ORIGIN |
| A terminal | Reachable partial/rejected/timeout or golden aborted omitted from matrix | `TERMINAL_ENUM_UNCOVERED` / MISMATCH, names all uncovered states |
| B.1 terminal coverage | Whole reachable enum covered, including non-success states | No terminal issue; a completed green run can close |
| A constructed boundary | `makeEnvelope`, no lexical mock, constructed gateway producer at required real boundary | `FIXTURE_PROVENANCE_CEILING` / UNSUPPORTED_ORIGIN |
| B.1 fixture floor | none/real-source; substitution at unrelated boundary; pure CTRL-001 | No ceiling; CTRL-001 needs no target binding/runtime chain |
| B.1 prose | Exact no-mocks title with empty typed provenance | `boundary_mock_detected` advisory only; close succeeds |
| B.1 warn | Otherwise valid record with new mismatch/fixture ceiling in warn mode | warning retained; close allowed; old failures still block |

## Obligations (exactly one primary failing test each; `|T| = |O| = 9`)

| id | obligation | primary test | discharges |
|---|---|---|---|
| O-1 | Matching validated inputs close; enforcement severity and old guards compose | `test_o1_matching_validated_record_closes_and_modes_preserve_old_guards` | R-6; TC-5.0 promotion; E-2/E-3/E-7/E-8 |
| O-2 | Actual caller/path/authority and contract differences reject without environment widening | `test_o2_wrong_caller_path_authority_and_contracts_reject_without_live_widening` | R-6; TC-5.1; golden -005 |
| O-3 | Every shipped runtime source join is complete and matching, or names the broken link/component | `test_o3_package_runtime_join_names_broken_link_and_unproven_component` | R-6; TC-5.2; golden -007 |
| O-4 | Policy freshness and independently compared ref/PID/start-time changes invalidate | `test_o4_policy_freshness_window_ref_and_process_restart_invalidate` | R-6; E-3; synthetic TC-5.4 comparison only |
| O-5 | Whole terminal enum coverage names every uncovered state, including aborted | `test_o5_terminal_matrix_names_all_uncovered_states_including_golden_aborted` | R-6; TC-5.5; golden -013 |
| O-6 | Typed provenance imposes a ceiling exactly at required real-producer substitutions | `test_o6_typed_fixture_ceiling_checks_each_bound_real_producer` | R-4; TC-6.0; golden -012 |
| O-7 | Lexical mock is advisory and CTRL-001's narrow formula has no binding burden | `test_o7_lexical_mock_is_advisory_and_ctrl001_has_no_binding_burden` | R-4; TC-6.1/6.2; golden CTRL-001 |
| O-8 | Diagnostics identify durable obligation, values, class, actor, and scoped recovery | `test_o8_diagnostics_identify_obligation_values_class_actor_and_recovery` | R-18; TC-13.0 payload contract |
| O-9 | Absent/partial/unsupported observations never become target mismatches or passing evidence | `test_o9_missing_partial_and_unsupported_observations_never_become_mismatch_or_pass` | R-6/R-18; TC-13.1; E-12 preservation |

B.1 success rows occur in O-1, O-3, O-4, O-5, O-6, O-7, and O-8's repaired run.
A reject rows cover each typed code above. Loops stay inside nine pytest
functions; no parametrized collection expansion. Main comparison/close calls
run behind a filesystem/network/subprocess I/O prohibition and assert input
immutability. The suite imports no product module until a primary test runs.

### Golden fixtures and E-17

`ab_suite/golden-fixtures.json` contains the **unchanged JSON values** of the
four named catalog cases plus **ASP-HARDEN-CTRL-001**, including each original
`fixture`, expected codes, and source references. Its source is packet
`05-golden-regression-catalog.json` under prediction-prime; source SHA-256:
`37186dff6cebc02fbb5cc4da99a0612923e5217be95080923407ea173dd8515d`.
Formatting is normalized JSON; no fixture key/value is rewritten. Runtime
tests read this local copy and need no access to prediction-prime.

| case | mechanical fixture mapping to pure functions | required codes |
|---|---|---|
| ASP-HARDEN-005 | Exact obligation/observed path, harness kind, null equivalence, live environment; scenario supplies product caller and legacy `/exit` authority context | three PROOF_* codes |
| ASP-HARDEN-007 | Exact intended/packaged/running/gateway sources; scenario's activation source is packaged source; one declared listener slot | RUNTIME_IDENTITY_INCOMPLETE, PACKAGE_COMPONENT_UNPROVEN |
| ASP-HARDEN-012 | Exact helper/source and replaced boundary; scenario declares kind constructed and binds that boundary to a real producer | FIXTURE_PROVENANCE_CEILING |
| ASP-HARDEN-013 | Exact runner_known_terminals → accepted states; exact system_terminal → reachable state | TERMINAL_ENUM_UNCOVERED |
| ASP-HARDEN-CTRL-001 | Exact SYNTHETIC, noncritical formula claim and no replaced boundary; adds only record coordinates/untriggered defaults | [] |

These mappings supply scenario facts absent from the terse fixture, never
rewrite its facts or return expected codes directly. Assertions compare actual
validator outputs with catalog expectations. No production `validate_golden`
dispatcher or case-ID switch is added. C-GOLDEN-HARNESS owns replay orchestration.

**SYNTHETIC fixtures are appropriate here:** they prove the validator's behavior,
never producer reality, live money-path operation, deployed process parity, or
authenticity of the represented receipt. Even the happy-path input whose TMR
field says REAL-DATA is synthetic data **about a validator input**. TC-6.1 uses
the exact reproduction title and provenance condition; the surrounding record
is canonical synthetic data, not a newly obtained historical live receipt.

## Controls (A.5)

- **known-good:** `ab_suite/ab_controls/good_contract.py`, a minimal
  self-contained executable control. It imports no product, candidate, or test
  module and does no I/O. Its schema/policy subsets serve only calibration.
  Required result: **9 passed**.
- **known-bad:** `ab_suite/ab_controls/bad_contract.py`, frozen integration
  **`08b848c90ff6b2b1b240a5d44a77cc4124d98e37`**. Verify commit/tree/blob objects,
  extract the exact three modules below into a temporary directory **inside
  this leaf**, and expose them through `MODULE`. No fabricated failing function.
  Required result: **9 failed**, every primary test at
  **`C-PROMOTION-COMPARE missing compare_target_observation`**, after successful
  collection/import. Setup failures are not red evidence.
- **target X:** unset `AB_CONTROL`, set **`AB_TARGET_ROOT`**. Explicitly load
  `tmr_schema.py`, `gate_policy.py`, and `phase8_promotion.py` from
  `AB_TARGET_ROOT/skills/adversarial-spec/scripts`. `MODULE` exposes all three
  attributes in both controls and target mode. No cwd/main-worktree fallback.
  Unknown control or absent target root is a setup error.

| frozen source | verified blob ID |
|---|---|
| `phase8_promotion.py` | `35309fe9db08e2b6d2f8281eac2155f180ff8b53` |
| `tmr_schema.py` | `02bd5d7b138d119986438eaefb4c713df9a73193` |
| `gate_policy.py` | `9945b6f2fc2ec3b45b3395560c8189b35b5e49da` |
| `tmr_compile_step.py` (read-only E-8 inspection) | `c276606f286cabdf58e394651f6cf6a250746af8` |

**No-git instruction resolution:** `git show adv-spec/v6-synthesized:<path>`
names the requested source but conflicts with the explicit no-Git constraint.
Instead, the source inspection used `python -B` to read
`.git/refs/heads/adv-spec/v6-synthesized`, decompress commit/tree/blob objects
with `zlib`, and verify header lengths and SHA-1 object identities. The branch
resolved to the pinned commit in this authoring run. No Git executable ran.
The copied template's reader supports ordinary and linked worktrees with the
required objects in **loose storage**. Missing/packed-only/corrupt objects give
`Frozen control SETUP` errors; that storage limit is not a product requirement.

### Calibration commands and evidence

From the repository root:

```bash
AB_CONTROL=good PYTHONHASHSEED=0 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -B -m pytest -q -o addopts='' -p no:cacheprovider --noconftest .adversarial-spec/specs/bounded-pipeline-reform-hardening-alignment/C-PROMOTION-COMPARE/ab_suite/test_c_promotion_compare.py
AB_CONTROL=bad AB_TARGET_ROOT=/home/jason/PycharmProjects/adversarial-spec PYTHONHASHSEED=0 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -B -m pytest -q -o addopts='' -p no:cacheprovider --noconftest --tb=short .adversarial-spec/specs/bounded-pipeline-reform-hardening-alignment/C-PROMOTION-COMPARE/ab_suite/test_c_promotion_compare.py
AB_TARGET_ROOT=/path/to/candidate PYTHONHASHSEED=0 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -B -m pytest -q -o addopts='' -p no:cacheprovider --noconftest .adversarial-spec/specs/bounded-pipeline-reform-hardening-alignment/C-PROMOTION-COMPARE/ab_suite/test_c_promotion_compare.py
```

Executed control calibration: **9 passed / 9 failed**, all frozen failures at
the named missing-function assertion, with no collection or dependency errors.
This is calibration, not candidate attestation. `primary_map.red_fingerprint`
remains **`"TBD"`**, `red_runs.count=0`, and candidate red attestation remains
false. Fixed-seed candidate runs and A/B closure remain conductor-owned.

Adapter calibration also ran target mode with an absolute interpreter/suite
path and `cwd=/tmp`. A temporary candidate root inside this leaf containing the
three exact frozen files produced nine expected missing-function failures.
The same temporary root then used the good control's functions with imports of
the **exact frozen TMR schema and gate policy**, producing **9 passed**. This
checks schema acceptance, policy-function routing, and independence from cwd.
Temporary roots were cleaned at process exit. It is not a product candidate run.

## Safety (B.3) and assumptions

- Writes are confined to this leaf, including frozen extraction and temporary
  adapter roots. Preexisting `normative.md` and
  `component-verification-procedure.md` remain untouched. No live skill/source,
  registry, board, branch, global instruction, or external catalog is edited.
- Python bytecode, pytest cache, repository conftest loading, and plugin
  autoload are disabled by the commands. No network, live proof execution, or
  board/Git command is part of this suite. The only subprocess in calibration
  is pytest itself; validator calls prohibit process launch.
- Python, pytest, Pydantic, and `rfc8785` are available in `.venv`. Loose frozen
  objects and standard Python import isolation are control setup assumptions.
- Input TMRs are E-8 validated records. Synthetic happy paths are validated
  against the candidate's actual schema; damaged evidence rows intentionally
  exercise the consumer's failure classification. This leaf does not replace
  TMR parsing or the binding compiler.
- Additional comparison facts are required because the frozen schema cannot
  express them and capture copies intended caller/path labels. Their trusted
  production, process-slot mapping, and census-derived role/boundary facts
  remain **unverified upstream integration obligations**. A passing synthetic
  suite cannot discharge those live boundaries.
- Source/ref strings are opaque resolved identities, not Git lookups. Comparing
  supplied package/process identity strings does not prove the actual deployed
  bytes. PID reuse/restart here is synthetic, with no native process-restart claim.
- The mode is resolved upstream by `gate_policy`; this leaf does not reread card
  metadata or fork the created-at/version fence. Warning permission to close
  does not convert missing/mismatched observations into passing receipts.
