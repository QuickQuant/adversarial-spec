# Architecture Primer: adversarial-spec

> Generated: 2026-07-19T08:43:13-05:00 | Git: ef18c66
> Freshness: caution | Trust: source-backed local synthesis; five delegated discovery explorers timed out, and the worktree is dirty. If a derived source file changes after `ef18c66`, trust source over this document.

## System Summary

`adversarial-spec` is a Python-backed Claude Code skill for refining product specifications through multi-model debate, then stress-testing the result through a resumable gauntlet. The runtime is a CLI plus file-backed tooling: model/provider adapters produce typed responses, gauntlet phases transform concerns into a verdict, and the newer TMR/validation/provenance toolchain records test maturity and evidence. Claude Code hooks form a separate stdin/stdout safety and pipeline-coordination plane.

## Most Important Components

| Component | Role | Runtime | Architecture |
|-----------|------|---------|--------------|
| Debate CLI | Parse specs, enforce gates, run critique rounds | implemented | active_primary |
| Model/provider routing | Select providers, run CLI/LiteLLM calls, track cost | implemented | active_primary |
| Gauntlet pipeline | Generate, cluster, evaluate, rebut, adjudicate, and finalize concerns | implemented | active_primary |
| Gauntlet persistence | Lock, hash, checkpoint, resume, and report runs | implemented | active_primary |
| TMR/evidence toolchain | Validate test-maturity records, liveness, promotion, and provenance | implemented | active_primary |
| Validation emission | Ledger lifecycle, digest/reply parsing, system validation, self-check | implemented | active_primary |
| Pre-gauntlet | Check repo compatibility before stress testing | implemented | active_secondary |
| Harness hooks | Enforce shell/Fizzy/pipeline safety and send coordination notices | implemented | active_primary |
| Plan analysis | Parse gauntlet concerns and inspect task dependency semantics | partial | active_secondary |
| Telegram/usage helpers | Human notification and local model-headroom routing | implemented | active_secondary |

## Shared Contracts and Boundaries

- **Gauntlet typed chain:** `Concern → Evaluation → Rebuttal → FinalBossResult → GauntletResult` in `gauntlet/core_types.py:83-232`; phase modules and persistence depend on these shapes.
- **Checkpoint envelope:** `_meta` carries schema/spec/config/data hashes; `gauntlet/persistence.py:79-137,281-333` rejects mismatched resume state.
- **TMR registry:** `tmr_schema.py:175-377` is strict and authoritative; `tmr_compile_step.py:64-156` derives the prose view.
- **Validation `Envelope`:** `validation_emission.py:200-220` is the CLI boundary; `status`, `issues`, and command-specific `data` must be interpreted together.
- **Hook stdio:** `.claude/hooks/codex_pretool_combined.py:18-72` runs configured classifiers and emits tool-protocol decisions. Hook output is transient; notifications are not transition proof.
- **File locks:** ledger, provenance, and gauntlet checkpoint writes use FileLock/ordered locks; the shared filtering stats append remains a concurrency review point.

## Non-Obvious Gotchas

- `adversarial_spec` is a root symlink to `skills/adversarial-spec/scripts`; edit the canonical target, and keep both packaging and import paths in mind.
- There are two active gauntlet CLIs: top-level `debate.py` and `gauntlet/cli.py`; their flags/defaults are not a single contract.
- `tmr-registry.json` is authoritative once present; `tests-pseudo.md` is a derived prose view and must not be edited as the source of truth.
- A missing field in the validation `Envelope` is not automatically success; consumers must inspect `status` and `issues`.
- TMR maturity/liveness is evidence-sensitive: unit-green, mock-only, and live/induced evidence are distinct classifications.
- Hook modules are intentionally process-boundary code. They should emit safe JSON and avoid importing runtime skill modules.
- The repository contains large historical specs/checkpoints/reports; `.adversarial-spec/` is excluded from architecture source mapping.

## Top Actionable Concerns

See [concerns.md](concerns.md) for the fix-first rollup. Current priorities are
the final-boss failure-as-PASS path, shared gauntlet stats writes, duplicated
hook role resolution, and the divergent gauntlet CLI timeout contract.

## Escalation Guidance

- Read [concerns.md](concerns.md) when you need the fix-first architecture debt and next actions.
- Read [overview.md](overview.md) for the full system narrative.
- Read [structured/flows.md](structured/flows.md) when a change crosses CLI, model, gauntlet, evidence, or hook boundaries.
- Read matched docs in [structured/components/](structured/components/) for a specific blast zone.
- Read [access-guide.md](access-guide.md) for guided reading paths by task type.
