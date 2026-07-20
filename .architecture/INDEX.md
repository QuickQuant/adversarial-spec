# Architecture: adversarial-spec

> Generated: 2026-07-19T08:43:13-05:00 | Git: ef18c66 | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 4.0 | Freshness: caution | Trust: source-backed local synthesis; five delegated explorers timed out. If source files changed after `ef18c66`, trust source over this map.

## System Summary

`adversarial-spec` is a Python-backed Claude Code skill for multi-model specification debate and adversarial gauntlet review. Its runtime is a file-backed CLI system with typed model/gauntlet/evidence contracts, resumable checkpoints, and a separate stdin/stdout hook plane for safety and pipeline coordination.

## Quick Start

- **Primer first:** [primer.md](primer.md) is the default small-context entrypoint for humans and LLMs.
- **Fix first:** [concerns.md](concerns.md) answers what to fix first.
- **Navigation only:** this file routes readers; it is not opponent-model payload.
- **Need guided reading?** Start with [access-guide.md](access-guide.md).

## Components

| Component | Purpose | Runtime | Architecture | Key Files |
|-----------|---------|---------|--------------|-----------|
| Debate CLI | parsing, gates, critique rounds, output | implemented | active_primary | `scripts/debate.py` |
| Models/providers | model adapters, profiles, credentials, cost | implemented | active_primary | `scripts/models.py`, `providers.py` |
| Gauntlet pipeline | adversary-to-verdict processing | implemented | active_primary | `scripts/gauntlet/` |
| Gauntlet persistence | locking, hashes, checkpoint/run artifacts | implemented | active_primary | `scripts/gauntlet/persistence.py` |
| Pre-gauntlet | compatibility and alignment checks | implemented | active_secondary | `scripts/pre_gauntlet/` |
| TMR/evidence toolchain | schema, compiler, liveness, provenance, promotion | implemented | active_primary | `tmr_schema.py`, `provenance_journal.py`, `phase8_promotion.py` |
| Validation emission | ledger, digest, reply, self-check, status | implemented | active_primary | `validation_emission.py` |
| Plan analysis | concern parser and dependency semantics | partial | active_secondary | `execution_planner/`, `dependency_semantics.py` |
| Harness hooks | safety and pipeline coordination | implemented | active_primary | `.claude/hooks/` |
| Telegram/usage | notifications and local routing | implemented | active_secondary | `telegram_bot.py`, `usage_router.py` |

## Navigation

**Understand the system:**

| Question | Read |
|----------|------|
| What does this system do? | [primer.md](primer.md) |
| What should I fix first? | [concerns.md](concerns.md) |
| What should I read next? | [access-guide.md](access-guide.md) |
| What does it do in depth? | [overview.md](overview.md) |
| Where is code located? | [filesystem-map.md](filesystem-map.md) |

**Work on specific tasks:**

| Task | Read |
|------|------|
| Evaluate a plan | [primer.md](primer.md) → matched [component docs](structured/components/) → [cross-references.md](structured/cross-references.md) |
| Modify debate/model routing | [debate-engine.md](structured/components/debate-engine.md) → [models.md](structured/components/models.md) → [providers.md](structured/components/providers.md) → [flows.md](structured/flows.md) |
| Modify gauntlet behavior | [gauntlet.md](structured/components/gauntlet.md) → [gauntlet-persistence.md](structured/components/gauntlet-persistence.md) → [flows.md](structured/flows.md) |
| Modify TMR/evidence | `structured/components/tmr-evidence-toolchain.md` → `validation-emission.md` → [cross-references.md](structured/cross-references.md) |
| Modify a hook | `structured/components/harness-hooks.md` → [cross-references.md](structured/cross-references.md) |

**Deep reference:**

| Need | Read |
|------|------|
| Fix-first concern rollup | [concerns.md](concerns.md) |
| Current fix-first themes | final-boss gate, shared-state writes, hook role/config drift, CLI timeout divergence |
| Cross-cutting patterns | [patterns.md](patterns.md) |
| Architecture findings | [findings.md](findings.md) |
| All entry points | [structured/entry-points.md](structured/entry-points.md) |
| Flow-by-flow breakdown | [structured/flows.md](structured/flows.md) |
| Calls, data paths, and contracts | [structured/cross-references.md](structured/cross-references.md) |
| Human diagrams | [HUMAN_READ_ONLY_visuals/](HUMAN_READ_ONLY_visuals/) |
| System overview HTML | [system-overview.html](HUMAN_READ_ONLY_visuals/system-overview.html) |
| Complex component flows | [gauntlet-flow.html](HUMAN_READ_ONLY_visuals/gauntlet-flow.html), [validation-emission-flow.html](HUMAN_READ_ONLY_visuals/validation-emission-flow.html), [harness-hooks-flow.html](HUMAN_READ_ONLY_visuals/harness-hooks-flow.html) |

## Architecture Decisions

- **File-backed resumability:** checkpoints, ledgers, journals, and reports are durable artifacts.
- **Typed boundaries:** dataclasses/Pydantic models carry gauntlet, gate, TMR, and evidence contracts.
- **Integrity and locking:** hashes, FileLock, atomic replacement, and expected-coordinate checks protect state.
- **Schema-first TMR:** JSON registry is authoritative; prose is derived.
- **Separate hooks:** hook safety/coordination uses stdin/stdout and stays outside runtime imports.
- **Parallel model calls:** ThreadPoolExecutor is used for latency, with explicit token accounting.

## Generation Info

| Field | Value |
|-------|-------|
| Generated by | `/mapcodebase` |
| Skill version | 4.0 |
| Schema version | 2.0 |
| Model | Codex |
| Generated | 2026-07-19T08:43:13-05:00 |
| Git hash | ef18c66 |
| Freshness | caution |
| Update | incremental; prior map at f198887 |

Use `manifest.json` as the source of truth for freshness, trust notes, component metadata, access paths, verification debt, and diagnosis outputs. This file is navigation-only; do not pass it as opponent-model context.
