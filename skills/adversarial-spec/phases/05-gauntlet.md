# Gauntlet (Phase 5)

Stress-test the converged spec and approved target architecture, preserve every Concern, and reconcile accepted changes before finalization. Inspect the active card's version, lane and `session_altitude` with explicit `board_id` before arming. Required pipeline gates remain binding; a user declining an optional legacy gauntlet does not waive a current completion gate.

Use a local milestone worklist:

```text
TodoWrite([
  {content: "Check spec/architecture drift and triage SCOUT [GATE]", status: "in_progress", activeForm: "Checking gauntlet readiness"},
  {content: "Confirm roster, threat model and cost with user [GATE]", status: "pending", activeForm: "Sizing gauntlet"},
  {content: "Revalidate context and approve attack prompts [GATE]", status: "pending", activeForm: "Arming adversaries"},
  {content: "Run attacks and preserve complete evidence", status: "pending", activeForm: "Running gauntlet"},
  {content: "Synthesize all concerns and revise spec/tests", status: "pending", activeForm: "Reconciling concerns"},
  {content: "Run required checkpoint guardrails [GATE]", status: "pending", activeForm: "Checking revisions"},
  {content: "Verify completion artifacts and record handoff", status: "pending", activeForm: "Recording gauntlet evidence"},
])
```

## Entry Gate 1: Spec/Architecture Drift

Load `target-architecture.md` from active detail. A valid Phase 4 skip stub satisfies this gate; a missing artifact does not. Compare the actual contracts, revision notes and freshness against the active spec. Timestamps are a signal, not proof of agreement.

If architecture demands changes absent from the spec—such as a superseded delivery, authorization or locking model—stop before arming. Present the conflicting passages. Reconcile the spec first and repeat the check, or obtain an explicit operator waiver with rationale in the decisions log. Never dispatch silently against known drift.

## Entry Gate 2: SCOUT Solo Pass

Before the fleet, dispatch one `spec_coroner` review using `SCOUT_GAUNTLET` in [adversaries.py](../scripts/adversaries.py), the spec and the same architecture/lookup/context material required below. Select the seat through [current-models.md](../reference/current-models.md). Preserve the prompt, raw response, ranked concerns and `VERDICT`.

**Runner limit:** `spec_coroner` is registered separately; `debate.py` fleet validation, `run_gauntlet()` and `generate_attacks()` accept fleet personas only. Use a separate read-only reviewer invocation through the supported seat runner, tied to the active card and approved input bundle. Do not pass SCOUT as a fleet name or substitute a debate round. If that dispatch is unavailable, report the gate blocked.

The phase owner triages the result:

| Outcome | Action |
|---|---|
| Structural contradiction or fictional load-bearing component | Reconcile the spec, repeat drift gate and SCOUT |
| Bounded stale/self-contradictory sections | Patch, record the change and recheck drift |
| Real but bounded concerns | Carry them into fleet prompts as known terrain |
| No structural issue | Continue |

Record the triage decision and rationale. Carry SCOUT concerns into final synthesis; keep scout statistics separate from fleet leaderboards.

## Review Boundaries

Reviewers are read-only: inspect supplied evidence, report concerns and missing observations, and do not execute the system under review. The phase owner obtains any authorized observations and supplies their evidence. A reviewer's expected outcome is not an observation.

State the execution scope and claim ceiling of each observation. Missing fixtures/access remain blocked with named unblock requirements. Mocked logic establishes only the logic/fixture exercised; it cannot establish browser, wire, permissions or credential behavior. Never promote an unverified assumption into a runtime claim.

## Human Sizing and Roster

Ask the user to confirm threat model, personas, attack/evaluation seats and cost before launch. Surface blast radius, money/irreversibility, external SDKs, network/trust boundaries, concurrency and architecture gaps. Recommend a bounded roster; the human may expand or shrink it within the required altitude floor.

Read the card before arming and use [reference/altitude.md](../reference/altitude.md) for minimum attacker models, distinct families and foci. Those counts are separate from persona count. A nine-persona run on one model does not establish multi-family coverage. Recheck floors after any user-approved skip.

Review `debate.py adversary-versions`, `adversary-stats` and `gauntlet-adversaries` before selection. Canonical fleet names come from `ADVERSARIES` in [adversaries.py](../scripts/adversaries.py):

| Prefix | Canonical name | Lens |
|---|---|---|
| PARA | `paranoid_security` | Authorization, trust and security boundaries |
| BURN | `burned_oncall` | Failure, recovery and operational visibility |
| MINI | `minimalist` | Complexity, bypass opportunities and existing capabilities |
| PEDA | `pedantic_nitpicker` | Types, encodings and boundary correctness |
| ASSH | `asshole_loner` | Abstractions, contracts and design assumptions |
| AUDT | `assumption_auditor` | Unverified premises and external claims |
| FLOW | `information_flow_auditor` | Data flow and missing mechanisms |
| ARCH | `architect` | Structure and component boundaries |
| TRAF | `traffic_engineer` | Throughput, concurrency and limits |

Separate registries: `existing_system_compatibility` (COMP, pre-gauntlet), `spec_coroner` (SCOUT, solo entry review), `ux_architect` (UXAR, Final Boss). None is a fleet `--gauntlet-adversaries` value. Compatibility aliases `lazy_developer` and `prior_art_scout` resolve to `minimalist` in the lower-level orchestrator; `debate.py` rejects them. Use canonical names.

Use [current-models.md](../reference/current-models.md) as the only seat authority, including independent review. **The runner still defaults to retired routes** in `gauntlet/model_dispatch.py`; linking the policy does not change execution. Choose explicit supported attack/evaluation overrides and inspect actual selected routes. Internal calls, including Final Boss selection, may still use defaults; an unsupported current seat is a blocker to report, not permission to use a retired fallback.

Estimate calls from the actual persona×model roster and evaluation batches, with repeated spec/context cost included. See [gauntlet-details.md](../reference/gauntlet-details.md) for tiering and timeouts. Offer adjustments before spending quota. Follow current provider/runner concurrency limits and surface quota failures; never count a failed call as a clean review.

## Arm Adversaries

### Retained Context Inventory

Consume `extended_state.context_inventory` (`ContextInventoryV1`) retained by [Phase 3's Context Readiness Audit](03-debate.md). Keep it through the gauntlet. Compare its `git_hash` to current HEAD and inspect changed/dirty blast-zone files; re-extract stale sources and preserve known gaps. If missing, perform Phase 3's readiness audit before arming. Do not silently fall back to spec-only attacks.

Every attack prompt must carry:

- Architecture primer when available, relevant component/flow excerpts and known gaps.
- Approved target architecture: framework profile, execution surfaces, concern and triggered-concern decisions, concern/surface matrix and active invariants. Use [Phase 4 §6](04-target-architecture.md#section-6-cross-cutting-concerns-assessment) and [§8](04-target-architecture.md#section-8-architectural-invariants); include the skip rationale when applicable.
- `lookup-log.md` when present: resolved assumptions plus unresolved entries explicitly left open to attack.
- Blast-zone file descriptions, recent relevant git changes and evidence suited to the persona's lens.

Emphasize security/enforcement for PARA; delivery, recovery and observability for BURN; shortcuts/prior art for MINI; types/tests for PEDA; design rationale for ASSH; owner/API evidence for AUDT; full relevant flows for FLOW; components/shared patterns for ARCH; concurrency/load limits for TRAF. COMP consumes compatibility evidence in the separate pre-gauntlet path.

Include `tests-pseudo.md` for PEDA, COMP and BURN, and security-relevant cases for PARA. Test changes proposed by reviewers are candidates: the phase owner approves and writes them with source Concern IDs. Reviewers do not append tests automatically.

Keep context within the target seat's window: if combined inputs exceed 80%, preserve decisions, rationale and invariants while trimming implementation sketches and irrelevant supplements. Report estimated token overhead (`len(text) // 4` is only an estimate). Aim for 600–1,000 tokens of base context, 200–1,200 of supplements, and 150–400 of focused tests. Added context must not exceed twice the spec size per adversary or double aggregate input without revising scope/budget with the user; surface any required material omitted by trimming.

### Approved Prompts Transport

1. Classify scope using `VALID_SCOPE_KEYS` in `adversaries.py`.
2. Build each persona from its `ADVERSARY_TEMPLATES` tone, relevant scope guidelines and spec-specific focus. If templates are unavailable, use the static persona plus the required context and disclose that fallback.
3. Include the context above inside each `full_persona`; a file path alone does not supply its content to the attack runner. Ask reviewers to describe data provenance, reachability, violated obligations and concrete mechanisms without assuming an actor's intent.
4. Present the complete prompts, known gaps, roster and cost for human approval. Skips are user decisions and must still satisfy altitude requirements.
5. Write `.adversarial-spec-gauntlet/approved-prompts.json` before launch:

```json
{
  "spec_hash": "<full sha256 hex digest of the runner's spec string>",
  "prompts": {
    "paranoid_security": {
      "status": "approved",
      "full_persona": "<persona + scope focus + architecture/invariant/lookup context>"
    }
  }
}
```

Use one entry per selected canonical persona; `status: skipped` excludes a persona. Hash the exact string the CLI supplies: `get_spec_hash(spec)` in `gauntlet/persistence.py`; the CLIs read text and call `.strip()`. A raw file hash can differ on trailing whitespace.

`_load_approved_prompts()` validates that hash; `_resolve_and_filter_adversaries()` extracts `full_persona` values and passes them as `prompts` to `generate_attacks()`. Corrupt/stale files fail. Missing files or missing overrides fall back to static personas in code, so the agent must check completeness before dispatch. Regenerate and reapprove after spec/context changes; no invented fallback flag.

The approved file changes attack personas only. `spec-as-gauntleted` pins the runner's spec string, not these overrides: retain approved prompts and source-context evidence alongside the run manifest. Final Boss receives spec and concern summary through its separate runner path.

## Run and Synthesize

Use the tracked `debate.py gauntlet` path with the active `--pipeline-card`; see [runner map](../reference/gauntlet-details.md). The local runner dispatches models. `pipeline_mark_gauntlet_complete` verifies evidence; it does not launch attacks.

Preserve raw responses and checkpoints. Inspect every zero-concern or failed adversary/model pair before claiming coverage. Parse failure requires inspecting the raw response and repairing/re-running the affected work.

### Step 6b: Synthesis

Use jq/Python to extract the complete Concern set and evaluation records; unwrap checkpoint `data` when present. Do not truncate Concern text or filter by automated verdict. Include accepted, dismissed, acknowledged, deferred and SCOUT concerns, plus recoverable raw-response omissions.

One synthesis owner reads the entire set with codebase/spec context. Automated evaluation is advisory. Deduplicate by theme while preserving source IDs and attribution; classify each unique Concern into:

| Category | Category |
|---|---|
| Correctness Bugs | Race Conditions |
| Failure Modes | Security |
| Operability | Scalability |
| Design Debt | Underspecification |

Assign **Accept** (revision needed), **Acknowledge** (valid, explicit tradeoff/outside scope) or **Dismiss** (invalid, with reason). Present the consolidated report and counts to the user before incorporating changes. Keep one coherent adjudication across categories.

Before promoting external library/SDK claims into spec text, complete the human-initiated verification pass against actual type definitions and official documentation. Use Docmaster where covered; missing required coverage blocks promotion until supplied. An adversary flag is not verification of a field, endpoint or formula.

Revise affected spec sections and canonical tests with accepted concerns. For deletion, relocation, externalization, absorption, split or reframing of a capability, follow [morph-reconciliation.md](../reference/morph-reconciliation.md) before saving. Preserve user-story spines and coverage lineage. Save the complete report as `gauntlet-concerns-YYYY-MM-DD.json` under the active artifact root.

Run checkpoint guardrails using [Phase 3's shared mechanics](03-debate.md#checkpoint-guardrails-after-each-round-incorporation): CONS always; CANON for changed types, formulas, causality, payload/display meanings or active/legacy status; TCOV for changed or relied-upon tests; SCOPE/TRACE when scope or requirement coverage changes. Record why conditional checks are inapplicable. Fix and rerun CONS, escalating after two unsuccessful attempts. Strengthen weak or missing test oracles, or obtain an explicit user-approved deferral of the uncovered semantic claim. Significant changes may require renewed debate.

Display `debate.py adversary-stats` and `medal-leaderboard`; surface degraded signal and useful unique catches. Optional Final Boss (`ux_architect`) reviews the resulting concern summary only when its actual evaluator route complies with current policy.

## Completion Evidence and Handoff

**The current runner does not yet emit an admissible altitude manifest for `pipeline_mark_gauntlet_complete`.** It writes `spec_hash`, `spec_as_gauntleted_path` and per-internal-step metrics; nested attack data is not the required top-level attacker/focus evidence. CLI success alone cannot close this gate.

For altitude sessions, an admissible manifest must carry evidence-backed `adversaries: [{model, family}]` and distinct `foci`; record `session_altitude` from the card for provenance. The verifier takes altitude from the card and checks model families against its registry. Use [altitude.md](../reference/altitude.md) for floors and node coverage. Populate evidence only from actual completed dispatches and reviewed scopes, never a planned roster. Current v6 completion also verifies closure/probe evidence; the MCP owns those validations. If the evidence bundle is unavailable, remain blocked and report the missing producer.

Call the verifier only with admissible files and explicit identifiers:

```text
pipeline_mark_gauntlet_complete(
  card_id=CARD_ID, session_id=SESSION_ID, board_id=BOARD_ID,
  spec_path=SPEC_AS_GAUNTLETED_PATH,
  gauntlet_concerns_path=CONCERNS_PATH,
  gauntlet_evaluations_path=EVALUATIONS_PATH,
  gauntlet_run_manifest_path=MANIFEST_PATH
)
```

`spec_path` must contain the exact reviewed bytes matching the manifest hash; use the saved spec-as-gauntleted artifact, preserving the separately revised spec path. Supply evaluations as the nonempty JSON array the MCP accepts, not a checkpoint envelope. Keep original checkpoints as evidence. Never use `pipeline_patch_state` to skip completion or reconciliation fences.

Persist `gauntlet_concerns_path`, evaluation/manifest paths, reviewed-spec path, approved-prompt evidence and the revised draft in active detail. Resolve every required gate before transition; follow the card's reconciliation requirements before Phase 6.

See SKILL.md § [Decisions Log](../SKILL.md).

See SKILL.md § [Journey Log](../SKILL.md).

See SKILL.md § [Fizzy Card Comment Convention](../SKILL.md).

See SKILL.md § [Phase Transition Protocol](../SKILL.md).
