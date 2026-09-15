# Architecture Primer: adversarial-spec

> Generated: 2026-07-20T14:44:38-05:00 | Git: `2433efa`
> Freshness: **caution** | Trust: full source scan includes the dirty worktree. Every substantive claim below is source-anchored; if a listed source file changes, trust source over this document.

## System Summary

`adversarial-spec` is a Python-backed skill and CLI suite for moving a specification through multi-model critique, compatibility grounding, a seven-phase gauntlet, and evidence-backed closeout. It combines file-backed resumability and typed contracts with a separate hook plane for local tool safety and Fizzy coordination.

## Most Important Components

| Component | Role | Runtime | Architecture |
|---|---|---|---|
| Debate and session | Gate, resume and run parallel critique rounds | implemented | active_primary |
| Model/provider routing | Profile models, invoke CLI/API adapters, record cost | implemented | active_primary |
| Gauntlet orchestration | Attack through Final Boss pipeline | implemented | active_primary |
| Gauntlet persistence | Hash, lock, atomically resume checkpoint artifacts | implemented | active_primary |
| Pre-gauntlet | Build repo context and alignment decision | implemented | active_primary |
| Validation emission | Ledger, evidence, digest, judgment and close artifact CLI | implemented | active_primary |
| TMR/provenance | Strict TMR registry and append-only transition evidence | implemented | active_primary |
| Hook plane | Guard tool calls and emit dispatch/activity side effects | implemented | active_primary |
| Plan analysis | Parse gauntlet concerns and analyze dependencies | partial | active_secondary |
| Telegram/usage | Human reply protocol and one-shot headroom routing | implemented | active_secondary |

## Shared Contracts and Boundaries

- **Validation `Envelope`:** stdout always contains `status`, `code`, `issues`, and `data`; null/empty defaults are intentional, not omitted fields (`validation_emission.py:200-214,3423-3459`).
- **Gauntlet checkpoint envelope:** `_meta` binds schema/spec/config/phase/data hash to `data`; resume rejects incompatible envelopes (`gauntlet/persistence.py:560-583,281-325`).
- **Gauntlet types:** `Concern → Evaluation → FinalBossResult → GauntletResult` is the cross-phase payload chain (`gauntlet/core_types.py:83-232`).
- **TMR registry:** `TestMaturityRecord` is strict and drives compiler/provenance/promotion behavior (`tmr_schema.py:175-377`).
- **Hook session activity:** a missing `session_id` or `event` produces no JSONL record; `source`/`model` exist only for SessionStart (`.claude/hooks/session_activity_logger.py:55-96`).

## Non-Obvious Gotchas

- Root console metadata targets `adversarial_spec.*`, and the root `adversarial_spec` symlink deliberately maps that package to `skills/adversarial-spec/scripts`; `uv run adversarial-spec --help` succeeds. Preserve that bridge when changing imports or packaging (`pyproject.toml:44-55`).
- Two gauntlet entrances exist—`debate.py gauntlet` and `python -m gauntlet`—so defaults and gate behavior are not a single CLI contract (`debate.py:898`, `gauntlet/cli.py:13`).
- Checkpoint atomicity protects individual files, not all read-modify-write sidecars; concurrent same-spec runs can still lose data (`gauntlet/persistence.py:124-152`, `phase_3_filtering.py:211-233`).
- A Final Boss execution failure currently returns PASS with warning text, rather than a failure verdict (`gauntlet/phase_7_final_boss.py:239-252`).
- Hook notification is an audit/dispatch side effect, not proof that a card transition or wakeup succeeded (`pipeline_notifications.py:392-437`).
- TMR prose is derived from strict registry records; edit the registry/compile path, not an output view (`tmr_compile_step.py:64-156`).

## Top Actionable Concerns

- **Phase lifecycle mismatch:** make the canonical phase list include the verification work performed in later phase documents; see [concerns.md](concerns.md).
- **Concurrent gauntlet sidecars:** lock or isolate raw-response/cluster/stats writes by run; see [concerns.md](concerns.md).
- **Final Boss failure-as-PASS:** decide whether transport failure can safely satisfy a final decision gate; see [concerns.md](concerns.md).

## Escalation Guidance

- Read [concerns.md](concerns.md) for fix-first architecture debt.
- Read [overview.md](overview.md) for system narrative.
- Read [structured/flows.md](structured/flows.md) for multi-component behavior.
- Read [structured/components/](structured/components/) for a targeted blast zone.
- Read [access-guide.md](access-guide.md) for the compact reading paths.
