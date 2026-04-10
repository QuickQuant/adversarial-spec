# T7 Greenfield Smoke Run

- Source read path: `~/.claude/skills/adversarial-spec/phases/04-target-architecture.md`
- Verified at: `2026-04-10T08:50:30Z`
- Scope: deployed Phase 4 doc, greenfield flow only

## Synthetic Scenario

- User stories: `US-1 create workspace`, `US-2 invite collaborator`, `US-3 add note item`
- Execution surfaces in scope: `request_response`, `mutation_entrypoint`
- Concerns in scope: `authn`, `validation`
- Existing codebase: none

## TodoWrite + Gates

The deployed doc starts with a required `TodoWrite([...])` block and includes all four gate items:

1. `Scale check — assess phase_mode [GATE]`
2. `Detect context mode and confirm with user [GATE]`
3. `Draft review — present draft for user approval [GATE]`
4. `Final approval — present dry-run results for user approval [GATE]`

## Canonical Enums

`surface_id` values (12):

1. `request_response`
2. `mutation_entrypoint`
3. `background_job`
4. `scheduled_work`
5. `startup_migration`
6. `client_runtime`
7. `webhook`
8. `outbound_integration`
9. `realtime_streaming`
10. `cli_command`
11. `public_api`
12. `data_stream`

`dry_run_check_id` values (15):

1. `enforcement_order`
2. `authn`
3. `authz`
4. `validation`
5. `sot_owner`
6. `cache_consistency`
7. `error_transform`
8. `observability`
9. `security_boundary`
10. `delivery_semantics`
11. `invariant_coverage`
12. `cli_parsing`
13. `idempotency`
14. `api_compatibility`
15. `data_integrity`

## Fingerprint Lifecycle

The deployed doc describes a four-state lifecycle:

1. `scaffold`: `architecture_fingerprint = null`
2. `draft`: `architecture_fingerprint = null`
3. `frozen`: fingerprint computed once in `phase4_bootstrap`
4. `published`: same bootstrap fingerprint injected into published artifacts

Post-freeze changes require recomputing the fingerprint, resetting publish state, and rerunning affected dry-runs.

## Smoke-Run Result

- `phase_mode`: `full`
  - Reason: Section 2 says `full` is required for `2+ concerns`, even when story count is only `3`.
- `context_mode`: `greenfield`
  - Reason: Section 3 says greenfield applies when there is no existing codebase.
- Halt behavior: no halt required for this smoke run.
  - The mode gates can be auto-confirmed (`decided_by = "auto"`), which allows the agent to reach a schema-valid bootstrap example without stalling before the later quality gates.
  - `draft_review` and `final_approval` remain pending because this smoke run stops before draft approval and dry-run completion.
- Input fingerprint:
  - `4250f9b086ecdeb7ac72b0f5eed151171f7b66f2202987ffe4fba94570ff939b`
- Bootstrap example:
  - See `t7-greenfield-bootstrap.json` in this same directory.

## Removed-Concept Regression Grep

Command used:

```bash
rg -n 'spec-draft-latest\.md|--ignore-stale-architecture|"target_architecture": "specs/<slug>/target-architecture\.md|"dry_run_results": "specs/<slug>/dry-run-results\.json' ~/.claude/skills/adversarial-spec/phases/04-target-architecture.md
```

Result: no matches.

Conclusion: the deployed Phase 4 doc is internally usable for a greenfield run and does not reference the removed path/flag concepts checked here.
