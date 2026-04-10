# Test Specification: Phase 4 Architecture Rewrite

> Promoted from tests-pseudo.md. Schema refs validated against spec-draft-v11.md.
> Updated for v15: fingerprint lifecycle (frozen state), human gates, roadmap normalization, external contracts, middleware identification.
> Updated for v16: non-web surface_id coverage (cli_command, public_api, data_stream), extended dry_run_check_id enum, middleware schema_ref field, TodoWrite stage/publish step.
> Updated for v17: observability check mandate for CLI/data_stream surfaces, linked_goals in middleware schema, matrix column constraint for non-web categories.

## US-1: Debate critiques across 6 focus areas

### TC-1.1: All focus areas receive at least one critique (happy path)
```
given: spec-draft-v1.md with 6 debate focus areas defined
  - framework fit (version-accurate)
  - surface completeness (including realtime_streaming when applicable)
  - cache consistency semantics
  - invariant verifiability
  - brownfield compatibility
  - requirement traceability
when: debate round completes with 2+ opponent models via debate.py critique
then: synthesis contains critique addressing each focus area
assert: len(focus_areas_with_critiques) == 6
schema_refs: debate_state.round_N_synthesis in session detail file
```

### TC-1.2: Debate produces actionable revisions (happy path)
```
given: round 1 critiques from opponent models (codex/gpt-5.4, gemini-cli/gemini-3.1-pro-preview)
when: synthesis is performed by Claude
then: at least 1 revision is proposed per focus area with surviving critiques
assert: spec-draft-v2.md differs from v1 in sections flagged by critiques
assert: debate_state.round increments
schema_refs: debate_state in session detail file, spec-draft-vN.md file naming
```

### TC-1.3: No model consensus after 2 rounds (error case)
```
given: opponent models disagree on a focus area after round 2
when: convergence check runs (Section 9: "Debate rounds default to a maximum of 3")
then: disagreement is surfaced to user with both positions
assert: user is asked to decide, not silently resolved
assert: at round 5, explicit user approval required to continue (Section 9)
schema_refs: debate_state.round, journey[] event for debate round
```

## US-2: Adversary stress test

### TC-2.1: Gauntlet covers cross-cutting concern completeness (happy path)
```
given: finalized spec with 9 base + 3 triggered cross-cutting concern categories
  - base: enforcement, sot, error_handling, validation, config, caching, observability (Concerns 1-9)
  - triggered: security, integration, realtime (Concerns 10-12)
  - concern_category enum: enforcement | sot | error_handling | validation | config | caching | observability | security | integration | realtime
when: BURN adversary attacks observability section
then: attack identifies specific gaps or confirms coverage
assert: each in-scope concern_category receives at least 1 adversary attack
schema_refs: concern_category enum (Section 0), Section 6 concern list
```

### TC-2.2: Gauntlet catches brownfield scoping issues (error case)
```
given: brownfield_feature flow with blast-zone scoping (Section 12)
when: adversary tests "can I skip a concern by claiming it's out of scope"
then: fitness assessment forces explicit verdict per concern:
  adequate | needs_extension | missing | conflicts (Section 12, step 3)
assert: no concern can be silently omitted
assert: existing debt flag raised when concern has "now" severity (Section 12, step 3)
schema_refs: context_mode enum, Section 12 brownfield feature flow
```

## US-3: Finalize and implement

### TC-3.1: target-architecture.md contains all three context modes (happy path)
```
given: finalized spec after debate + gauntlet
when: written to specs/<slug>/target-architecture.md
then: file contains sections for all three context_mode values:
  - greenfield (Section 7: full draft flow)
  - brownfield_feature (Section 12: blast-zone scoped)
  - brownfield_debug (Section 13: traversal path scoped)
assert: YAML header contains context_mode field
assert: required headers present (Section 7): schema_version, spec_slug, phase_mode,
  context_mode, framework, framework_version, surfaces, roadmap_path,
  tests_pseudo_path, architecture_fingerprint
schema_refs: Section 7 Required Headers, context_mode enum
```

### TC-3.2: Cross-references are valid (error case prevention)
```
given: updated 04-target-architecture.md deployed to ~/.claude/skills/adversarial-spec/phases/
when: 02-roadmap.md, 05-gauntlet.md, 07-execution.md reference Phase 4 outputs
then: all referenced outputs are defined in Phase 4:
  - architecture-invariants.json (Section 8.2, normative schema)
  - target-architecture.md (Section 7, draft format + required headers)
  - decision_journal[] (Section 11, normative schema)
  - dry-run-results.json (Section 10.3, normative schema)
  - phase4_bootstrap (Section 0, bootstrap contract)
  - tests-pseudo.md invariant tests (Section 8.3, marker protocol)
assert: no dangling references to removed Phase 4 concepts
schema_refs: Section 22 (Phase Interactions), Section 20 (Migration Plan)
```

## Fingerprint Lifecycle (v15)

### TC-4.1: Fingerprint is null during scaffold and draft (happy path)
```
given: Phase 4 run in full mode, Steps 7-9 in progress
when: scaffold target-architecture.md is written (Step 7)
  and draft invariants are being revised (Steps 8-9)
then: phase4_bootstrap.architecture_fingerprint == null
  and target-architecture.md YAML header architecture_fingerprint == null
  and architecture-invariants.json architecture_fingerprint == null
schema_refs: §0 Draft vs Published fingerprint lifecycle table
```

### TC-4.2: Fingerprint computed at freeze, before dry-run (happy path)
```
given: Phase 4 full mode, debate converged, draft_review gate approved
when: content is frozen (pre-dry-run)
then: phase4_bootstrap.architecture_fingerprint is computed sha256 (non-null)
  and phase4_bootstrap.status transitions to "dry_run"
  and dry-run-results.json uses the bootstrap fingerprint value
assert: dry_run_results.architecture_fingerprint == phase4_bootstrap.architecture_fingerprint
schema_refs: §0 Fingerprint lifecycle (frozen state), §10.3 dry-run-results.json
```

### TC-4.3: Post-freeze change recomputes fingerprint (error recovery)
```
given: Phase 4 with frozen fingerprint, dry-run in progress or passed
when: a fingerprint input changes (e.g., invariant modified, debate reopened)
then: architecture_fingerprint is recomputed
  and artifact_publish_state reset to "none"
  and affected dry-runs must re-run
assert: old fingerprint != new fingerprint
schema_refs: §0 Post-freeze changes
```

### TC-4.4: Published artifacts match bootstrap fingerprint (consistency check)
```
given: Phase 4 at publish time, all dry-runs passed
when: artifact headers are injected with fingerprint and staged
then: every published artifact's architecture_fingerprint == phase4_bootstrap.architecture_fingerprint
assert: mismatch halts with P4_ARTIFACT_SET_INCONSISTENT
schema_refs: §0 fingerprint lifecycle, §16 blocking errors
```

## Human Gate Protocol (v14)

### TC-5.1: Scale check gate blocks until resolved (happy path)
```
given: Phase 4 bootstrap, scale check complete with recommendation
when: gate_approvals.scale_check.status == "pending"
then: agent presents recommendation and waits for user input
  and does NOT proceed to Step 3
assert: no context_mode detection until scale_check gate resolved
schema_refs: §0 Human Gate Protocol, gate definitions table
```

### TC-5.2: Quality gate cannot be auto-confirmed (error case)
```
given: session detail has auto_confirm_gates: true
when: draft_review gate is reached
then: agent halts with P4_PENDING_USER_GATE
  and does NOT auto-approve the draft
assert: auto_confirm_gates only skips mode gates (scale_check, context_mode)
schema_refs: §0 Auto-confirm mode, §16 P4_PENDING_USER_GATE
```

### TC-5.3: Gate override updates downstream state (happy path)
```
given: scale_check recommends "lightweight"
when: user overrides to "full"
then: gate_approvals.scale_check.status = "overridden"
  and gate_approvals.scale_check.final_value = "full"
  and phase4_bootstrap.phase_mode = "full"
assert: downstream steps use overridden value
schema_refs: §0 Human Gate Protocol, state transitions
```

## Roadmap Normalization (v15)

### TC-6.1: v1 manifest (milestones[].user_stories[]) normalized (happy path)
```
given: manifest.json with shape v1:
  goals: ["Goal A", "Goal B"]
  milestones: [{id: "M-1", user_stories: [{id: "US-1", persona: "dev", action: "do thing"}]}]
when: Phase 4 reads and normalizes
then: normalized_roadmap.goals = [{id: "G-1", description: "Goal A"}, ...]
  and normalized_roadmap.user_stories = [{id: "US-1", description: "do thing", goal_ids: ["G-1"]}]
assert: synthetic IDs assigned, stories flattened from milestones
schema_refs: §17.5 Roadmap Manifest, Shape v1
```

### TC-6.2: v2 manifest (top-level user_stories[]) passes through (happy path)
```
given: manifest.json with shape v2:
  goals: [{id: "G-1", description: "Goal A"}]
  user_stories: [{id: "US-1", description: "do thing", goal_ids: ["G-1"]}]
when: Phase 4 reads and normalizes
then: normalized_roadmap matches input (pass-through with validation)
schema_refs: §17.5 Roadmap Manifest, Shape v2
```

### TC-6.3: Unknown manifest shape halts (error case)
```
given: manifest.json with neither v1 nor v2 shape (e.g., missing both milestones and user_stories)
when: Phase 4 attempts normalization
then: halt with P4_UNSUPPORTED_ROADMAP_SHAPE
assert: no partial normalization or silent fallback
schema_refs: §17.5 Normalization rules, §16 P4_UNSUPPORTED_ROADMAP_SHAPE
```

### TC-6.4: Unaligned story detected post-normalization (error case)
```
given: v1 manifest where a user story cannot be linked to any goal
when: normalization attempts goal linking
then: halt with P4_UNALIGNED_STORY
assert: specific story ID and reason surfaced in blocking_error
schema_refs: §17.5 Validation, §16 P4_UNALIGNED_STORY
```

## External Contracts (v14)

### TC-7.1: debate.py critique subprocess returns valid JSON (happy path)
```
given: target-architecture.md piped to debate.py critique with --models and --round
when: subprocess exits with code 0
then: stdout is valid JSON array of critique objects
  and each object has: model, agreed (bool), response (string)
  and critiques saved to .adversarial-spec-checkpoints/
schema_refs: §17.5 debate.py critique Subprocess Contract
```

### TC-7.2: debate.py subprocess failure halts (error case)
```
given: debate.py critique invoked
when: subprocess exits with code != 0 or times out
then: Phase 4 halts with descriptive error
  and does NOT silently skip the debate round
schema_refs: §17.5 Exit codes, Timeout
```

## Middleware Identification (v13)

### TC-8.1: Middleware candidates identified in full mode (happy path)
```
given: Phase 4 full mode, draft complete with typed interfaces
when: §7.5 middleware scan runs
then: middleware-candidates.json written with schema_version, candidates[]
  and each candidate has: id, name, inputs, outputs, linked_invariants, linked_user_stories
  and architecture_fingerprint matches bootstrap
schema_refs: §7.5 Output Artifact schema
```

### TC-8.2: Empty candidates is valid (edge case)
```
given: Phase 4 full mode, spec has no reusable cross-surface interfaces
when: §7.5 middleware scan runs
then: middleware-candidates.json written with candidates: []
assert: empty array is valid, not an error
schema_refs: §7.5 Rules
```

### TC-8.3: Skip mode produces no middleware artifact (boundary)
```
given: Phase 4 skip mode
when: Phase 4 completes
then: no middleware-candidates.json written
  and artifact_paths.middleware_candidates is absent
schema_refs: §7.5 Mode Behavior
```

### TC-8.4: Middleware inputs/outputs accept optional schema_ref (happy path)
```
given: Phase 4 full mode on a TypeScript project
when: §7.5 middleware scan emits a candidate with a typed interface
then: each input/output entry may set `schema_ref` to a repo-relative path
  and absence of schema_ref is valid (primitive or untyped language)
assert: validator accepts both forms
assert: middleware-candidates.json written with schema_ref populated where known
schema_refs: §7.5 inputs/outputs schema, Rules
```

## Non-Web Surface Coverage (v16)

### TC-9.1: CLI category requires cli_command surface (happy path)
```
given: architecture_taxonomy.category == "cli"
when: §4.2 execution surface map is assembled
then: execution_surfaces must include ≥1 entry whose surface_id == "cli_command"
assert: absence halts with P4_SURFACE_CATEGORY_MISMATCH (or an equivalent blocking error)
assert: §10.2 archetypes table includes a CLI row for read and write
schema_refs: §4.2 Category-to-surface mapping, §10.2 archetypes
```

### TC-9.2: Library category requires public_api surface (happy path)
```
given: architecture_taxonomy.category == "library"
when: §4.2 execution surface map is assembled
then: execution_surfaces must include ≥1 entry whose surface_id == "public_api"
assert: §10.5 required_check derivation includes api_compatibility for that surface
schema_refs: §4.2 Category-to-surface mapping, §10.5 Library surfaces
```

### TC-9.3: Data-pipeline category requires data_stream surface (happy path)
```
given: architecture_taxonomy.category == "data-pipeline"
when: §4.2 execution surface map is assembled
then: execution_surfaces must include ≥1 entry whose surface_id == "data_stream"
assert: §10.5 required_check derivation includes data_integrity and idempotency
schema_refs: §4.2 Category-to-surface mapping, §10.5 Data pipeline surfaces
```

### TC-9.4: CLI surface derives cli_parsing + idempotency checks (happy path)
```
given: execution_surfaces contains cli_command
when: dry-run required_check derivation runs (§10.5)
then: required_checks for cli archetypes include cli_parsing and idempotency
assert: dry_run_check_id values are drawn from the canonical enum (§ Canonical Enums)
schema_refs: §10.5 CLI surfaces, Canonical Enums dry_run_check_id
```

### TC-9.5: Web-only projects do not force non-web surfaces (boundary)
```
given: architecture_taxonomy.category == "web-app"
when: §4.2 execution surface map is assembled
then: execution_surfaces may omit cli_command, public_api, and data_stream
assert: no error is raised for omitting non-web surfaces on a web category
schema_refs: §4.2 Execution Surfaces, Category-to-surface mapping
```

## TodoWrite Checklist Coverage (v16)

### TC-10.1: TodoWrite includes stage-and-publish gate step (happy path)
```
given: Phase 4 §1 TodoWrite checklist
when: the checklist is rendered from the spec
then: it contains the exact step "Stage and publish artifacts atomically [GATE]"
  and that step appears after "Dry-run per phase_mode scope [GATE]"
  and before "Record decisions and dry-run results in session"
assert: gate step is not missing, not renamed, not out of order
schema_refs: §1 TodoWrite (Entry Point)
```

## Non-Web Observability Mandate (v17)

### TC-11.1: CLI surfaces require observability check (happy path)
```
given: execution_surfaces contains cli_command
when: §10.5 required_check derivation runs
then: required_checks for CLI archetypes include observability
  and the check verifies exit codes are deterministic and documented
  and the check verifies stdout/stderr signals conform to the spec
assert: observability in required_checks for cli_command surfaces
schema_refs: §10.5 CLI surfaces
```

### TC-11.2: Data pipeline surfaces require observability check (happy path)
```
given: execution_surfaces contains data_stream
when: §10.5 required_check derivation runs
then: required_checks for data_stream archetypes include observability
  and the check verifies per-batch success/failure signals
  and the check verifies records-in/out counts
  and the check verifies DLQ/poison-pill routing is emitted
assert: observability in required_checks for data_stream surfaces
schema_refs: §10.5 Data pipeline surfaces
```

## Middleware Goal Traceability (v17)

### TC-12.1: Middleware candidates require linked_goals (happy path)
```
given: Phase 4 full mode, §7.5 middleware scan running
when: a candidate is emitted to middleware-candidates.json
then: the candidate MUST have linked_goals with at least 1 goal ID
  and the goal IDs must exist in normalized_roadmap.goals
assert: candidate without linked_goals halts with schema validation error
assert: candidate with unknown goal ID halts with traceability error
schema_refs: §7.5 Output Artifact schema, Rules
```

### TC-12.2: Middleware schema enforces all three traceability links (consistency)
```
given: middleware candidate with invariants + user_stories but no goals
when: validator checks the candidate
then: validation fails (all three of linked_invariants, linked_user_stories, linked_goals required)
assert: error message identifies which link is missing
schema_refs: §7.5 Rules
```

## Non-Web Matrix Column Constraint (v17)

### TC-13.1: CLI category matrix must use cli_command column (happy path)
```
given: architecture_taxonomy.category == "cli"
when: §6.3 concern x surface matrix is assembled in target-architecture.md
then: matrix column headers MUST include cli_command
  and MAY include additional surfaces (e.g., request_response for an embedded admin port)
assert: a CLI category matrix using only web columns halts with P4_MATRIX_CATEGORY_MISMATCH
schema_refs: §6.3 Category-native columns
```

### TC-13.2: Library category matrix must use public_api column (happy path)
```
given: architecture_taxonomy.category == "library"
when: §6.3 matrix is assembled
then: matrix column headers MUST include public_api
  and web surfaces are omitted unless the library bundles a server
schema_refs: §6.3 Category-native columns
```

### TC-13.3: Data-pipeline category matrix must use data_stream column (happy path)
```
given: architecture_taxonomy.category == "data-pipeline"
when: §6.3 matrix is assembled
then: matrix column headers MUST include data_stream
  and typically include scheduled_work or background_job as trigger surfaces
schema_refs: §6.3 Category-native columns
```

### TC-13.4: Mixed project matrix is union of applicable surfaces (edge case)
```
given: a project that is both a CLI and exposes a public_api library surface
when: §6.3 matrix is assembled
then: matrix columns are the union {cli_command, public_api}
  and no applicable surface is omitted
schema_refs: §6.3 Category-native columns
```

## Coverage Matrix

| Area | Test Cases | Sections Exercised |
|------|------------|-------------------|
| US-1 (Debate) | TC-1.1, TC-1.2, TC-1.3 | 9 |
| US-2 (Gauntlet) | TC-2.1, TC-2.2 | 6, 12, 22 |
| US-3 (Finalize) | TC-3.1, TC-3.2 | 7, 19, 20, 22 |
| Fingerprint Lifecycle | TC-4.1, TC-4.2, TC-4.3, TC-4.4 | 0, 10.3, 16 |
| Human Gates | TC-5.1, TC-5.2, TC-5.3 | 0, 16 |
| Roadmap Normalization | TC-6.1, TC-6.2, TC-6.3, TC-6.4 | 17.5, 16 |
| External Contracts | TC-7.1, TC-7.2 | 17.5 |
| Middleware Identification | TC-8.1, TC-8.2, TC-8.3, TC-8.4 | 7.5 |
| Non-Web Surface Coverage (v16) | TC-9.1, TC-9.2, TC-9.3, TC-9.4, TC-9.5 | 4.2, 10.2, 10.5, Canonical Enums |
| TodoWrite Checklist | TC-10.1 | 1 |
| Non-Web Observability (v17) | TC-11.1, TC-11.2 | 10.5 |
| Middleware Goal Traceability (v17) | TC-12.1, TC-12.2 | 7.5 |
| Non-Web Matrix Columns (v17) | TC-13.1, TC-13.2, TC-13.3, TC-13.4 | 6.3 |

All user stories have ≥1 test. All v14/v15/v16/v17 additions have ≥1 test. No orphan tests.
