# System Overview: adversarial-spec

> Generated: 2026-07-20T14:44:38-05:00 | Git: `2433efa` | Target: `/home/jason/PycharmProjects/adversarial-spec`
> Skill version: 4.0 | Model: Codex (Terra xhigh) | Freshness: caution
> Trust: mapped from source including a dirty worktree; source wins if derived files change.

## What This System Does

The project implements a Claude-facing adversarial specification workflow with Python runtime tools. A user-facing debate CLI gates and dispatches model critique, the gauntlet applies sequential adversarial phases and saves resumable evidence, and validation/TMR tooling produces auditable close artifacts.

## Architecture at a Glance

The runtime is intentionally file-backed. `debate.py` is the broad command dispatcher: it verifies pipeline/card requirements, loads or resumes a `SessionState`, invokes provider adapters in parallel, persists partial results, and can invoke the gauntlet (`debate.py:1026-1227,1623-1687`). The gauntlet packages phases behind `run_gauntlet()` (`gauntlet/orchestrator.py:205`) and separates domain dataclasses, model dispatch/rate control, persistence, and reporting. Pre-gauntlet runs before the standalone gauntlet when requested, gathering bounded Git/system/schema context and returning either enriched context or an alignment state (`pre_gauntlet/orchestrator.py:67-325`).

Validation emission is a separate command suite around a locked ledger. It derives ConOps, normalizes rows, binds evidence, emits digest batches, parses authenticated human replies, then writes and self-checks a system-validation artifact (`validation_emission.py:688-3102`). The TMR compiler, provenance journal and Phase 8 promotion tools add strict typed registry and transition evidence. Project hooks do not import the runtime: they receive JSON on stdin, guard tool use or append notifications/activity records, and fail safely when data is malformed.

## Primary Data Flows

### Debate to model results

Spec text comes from stdin or session state, optional context is loaded, and one future per model invokes the appropriate CLI/API adapter. Each result becomes a `ModelResponse`, partial results are persisted, then aggregate JSON/text is emitted (`debate.py:1026-1227`, `models.py:688-1199`).

### Gauntlet to persisted verdict

The gauntlet hashes the exact spec and config, writes an initial manifest, generates attacks, filters/clusters, evaluates in provider-bounded waves, optionally rebuts/adjudicates, and runs Final Boss before writing a complete run (`gauntlet/orchestrator.py:250-963`). Checkpoints carry schema/spec/config/data hashes and use file locks plus atomic replace (`gauntlet/persistence.py:111-152,560-583`).

### Validation closeout

ConOps and ledger rows are hash-bound; evidence and digest replies update the locked ledger; a close artifact is emitted only after coverage/provenance checks (`validation_emission.py:715-1372,1528-3036`). The CLI always emits a JSON `Envelope` to stdout (`validation_emission.py:200-214,3423-3462`).

### Hook side effects

Hook JSON is parsed from stdin. A Fizzy guard can block before a tool call, while notifications/activity handlers append JSONL or invoke optional messaging after relevant events (`fizzy_payload_guard.py:86-125`, `pipeline_notifications.py:392-437`, `session_activity_logger.py:55-96`).

## Key Architectural Decisions

- **Typed domain contracts:** gauntlet and TMR types make phase payloads and evidence validation explicit.
- **Artifact integrity over implicit state:** hashes, checkpoint metadata, lock files and atomic replace make resume data inspectable.
- **Provider-bounded parallelism:** models run concurrently, but gauntlet dispatch groups submissions by provider/rate policy.
- **Separate hook plane:** safety/coordination hooks are process-bound JSON adapters rather than runtime imports.
- **Evidence-gated closure:** validation/TMR components treat human judgment, live evidence and provenance as first-class state.

## Non-Obvious Things

- The root `adversarial_spec` symlink deliberately bridges distribution metadata to `skills/adversarial-spec/scripts`; root console help is verified, but preserve that bridge during packaging changes.
- Pre-gauntlet and the gauntlet CLI may be interactive; unattended execution changes only the input mechanism, not the blocking semantics.
- A locked atomic JSON writer does not protect an entire multi-step read-modify-write sequence.
- Notifications and dispatch logs are non-authoritative side effects; query live Fizzy state before treating one as a transition.

## Component Map

| Component | Purpose | Key Entry |
|---|---|---|
| Debate/session | model critique and resume | `main()` at `debate.py:1623` |
| Models/providers | provider selection and invocation | `call_models_parallel()` at `models.py:1114` |
| Gauntlet | seven-phase concern pipeline | `run_gauntlet()` at `orchestrator.py:205` |
| Pre-gauntlet | codebase grounding and alignment | `PreGauntletOrchestrator.run()` at `pre_gauntlet/orchestrator.py:85` |
| Validation emission | evidence lifecycle CLI | `main()` at `validation_emission.py:3423` |
| TMR/provenance | registry and transition evidence | `compile_tmr_records()` at `tmr_compile_step.py:64` |
| Hooks | safety and coordination adapters | `main()` at `fizzy_payload_guard.py:86` |

For operational detail, select a file under `structured/components/`.
