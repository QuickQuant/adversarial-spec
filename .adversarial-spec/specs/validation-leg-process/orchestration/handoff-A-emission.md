# Handoff A: Gate V3 JSON + Step 9b Schema-3 Emission (Codex, xhigh)

You are Codex, working alone in repo root `/home/jason/PycharmProjects/adversarial-spec`.
Your job: produce the Gate V3 coverage JSON and the complete Step 9b schema-3 emission
artifacts for the **validation-leg-process** execution plan, entirely LOCAL — no board,
no MCP, no network beyond what the repo needs.

## Hard boundaries
- Do NOT call any MCP tool (fizzy or otherwise). Do NOT `pipeline_load` or validate
  against the live board. The Claude-side orchestrator owns those legs.
- Do NOT modify: `execution-plan.md`, anything under `skills/` (skill source),
  `.claude/`, session files under `.adversarial-spec/sessions/`.
- Do NOT git commit.
- All new artifacts go under `.adversarial-spec/specs/validation-leg-process/`.

## Authoritative inputs (read these)
1. `.adversarial-spec/specs/validation-leg-process/execution-plan.md` — THE plan.
   25 nodes: 1 system (SYS), 5 subsystems (SS-1..SS-5), 19 components (C-1.1..C-1.4,
   C-2.1..C-2.3, C-3.1..C-3.3, C-4.1..C-4.6, C-5.1..C-5.3). Every per-node field you
   need (altitude, parent, realizes, impl_status, behavior_change, verification_mode/
   scope, strategy, architecture_refs, concern_refs, invariant_refs, surface_scope,
   test_refs, verify_commands, acceptance_criteria) is specified per node. Treat it as
   ground truth; do not invent fields or nodes.
2. `skills/adversarial-spec/phases/07-execution.md`:
   - L636–705: Gate V3 — exact `verification-coverage.json` schema (`report_schema_version: 1`).
   - L936–1061: Step 9b — schema-3 plan shape, per-altitude field table (strict superset
     chain), dotted-line verification plan/procedure artifacts with `plan_hash` (12-char
     sha256 prefix), `requirement_metadata` (NASA 4.2-2), requirement lint, self-check loop.
   - **v4 is VERIFICATION-ONLY**: no `validation-ledger.json`, no `system_validation`
     binding, no force/override fields.
3. `skills/adversarial-spec/scripts/mini_spec_emission.py` — the emitter. Key API:
   `emit_fizzy_plan` (L355), `self_check_plan` (L411), `lint_requirement_text` (L143),
   `altitude_spec_shape` (L99), `_write_artifact` (L123). READ THE CODE to learn the
   exact signature, what artifacts it writes itself vs expects pre-existing, and the
   reject codes `self_check_plan` enforces.
4. `.adversarial-spec/specs/validation-leg-process/fizzy-validation-contract.md` — the
   8 gate reject classes (context for hashes/shape parity).
5. `.adversarial-spec/specs/validation-leg-process/tests-spec.md` — TC ids referenced by
   test_refs.
6. `.adversarial-spec/specs/validation-leg-process/roadmap/manifest.json` — US-0..US-13
   (realizes_refs must stay subsets of ancestor stories).
7. Optional context: `target-architecture.md`, `architecture-invariants.json` (INV-A1..A7),
   `gauntlet-concerns-2026-06-11.json` (concern text), `spec-output.md` (FINAL spec).

## Deliverables (exact paths)
1. `.adversarial-spec/specs/validation-leg-process/verification-coverage.json`
   — Gate V3 schema from 07-execution.md L673–699. Derive counts from the plan
   yourself, then cross-check against these expected values (they were hand-derived by
   the orchestrator; if YOUR derivation disagrees, STOP, record the discrepancy in the
   emission report, and use your derivation only if the plan text clearly supports it):
   - total_tasks: 25
   - behavior_changing_count: 20 (false on exactly: C-4.6, SS-5, C-5.1, C-5.2, C-5.3)
   - counts_by_mode: automated-unit 16, automated-integration 6 (SYS + 5 SS),
     artifact-sync 1 (C-5.1), static-check 1 (C-5.2), manual-ux 1 (C-5.3)
   - exempt_tasks: C-5.1 (artifact-sync), C-5.2 (static-check), C-5.3 (manual-ux) with
     the exemption_reason strings from the plan
   - unmapped_behavior_tasks: [] (MUST be empty — if you find a behavior-changing node
     with no verification mode, that is a blocking finding; report it, do not paper over)
   - validation_errors: []
2. Per-node spec docs + dotted-line verification artifacts under
   `.adversarial-spec/specs/validation-leg-process/<task_id>/...` — whatever layout
   `emit_fizzy_plan`/`_write_artifact` produce/expect: `normative.md` (component),
   `subsystem-spec.md` (subsystem), `system-spec.md` (system), plus
   component/subsystem/system verification plan/procedure docs. Content: derive from the
   plan's per-node acceptance_criteria, verify_commands, test_refs, invariant_refs,
   concern_refs — substantive, not lorem. Verification plan docs must state what is run
   (the verify_commands), what evidence counts, and which TCs map.
3. `.adversarial-spec/specs/validation-leg-process/orchestration/emit_driver.py`
   — the reproducible driver script that builds the 25 node dicts and calls
   `emit_fizzy_plan`. Runnable via `uv run python <path>`. This is the resume point if
   the validate loop later needs re-emission.
4. `.adversarial-spec/specs/validation-leg-process/fizzy-plan.json`
   — `plan_schema_version: 3`, `session_id: "adv-spec-202606110339-validation-leg-process"`,
   25 tasks, per-altitude verification_binding keys EXACTLY matching the obligation set
   (component: component_verification only; subsystem: + subsystem_verification;
   system: + system_verification), `requirement_metadata` on every node,
   `realizes_refs` ⊆ ancestor stories, hashes re-derivable from the real files.
5. `self_check_plan()` MUST return clean. Run it; include its raw output in the report.
   Also run `lint_requirement_text` on every requirement_metadata rationale/shall
   statement you author; fix failures before finishing.
6. `.adversarial-spec/specs/validation-leg-process/orchestration/emission-report.md`
   — what you produced, self_check output, lint results, every judgment call you made,
   and an `## OPEN QUESTIONS` section for anything ambiguous (choose the conservative
   reading and flag it; do NOT silently invent).

## Definition of done
- All 6 deliverables exist at the exact paths above.
- `self_check_plan` output shows zero reject codes.
- emission-report.md is honest about anything you were unsure of.
Your final message: 5-10 lines — deliverable paths, self_check verdict, count of open
questions.
