# Phase 6 mandatory scans

> Run: 2026-07-20T15:27:47-05:00 | Git: `2433efa`

## Registry/configuration mapping

Command: `rg -n -i -C 2 "registry|mapping|config|duplicate|dedup|unique" skills/adversarial-spec/scripts/providers.py skills/adversarial-spec/scripts/gauntlet/model_dispatch.py skills/adversarial-spec/scripts/tmr_parser.py skills/adversarial-spec/scripts/tmr_schema.py skills/adversarial-spec/scripts/tmr_compile_step.py skills/adversarial-spec/scripts/gauntlet/phase_3_filtering.py`.

Result: `BEDROCK_MODEL_MAP` is intentionally overridden by explicit custom aliases; TMR parsing rejects duplicate keys and duplicate `tmr_uid`; dedup stats are a concurrency hazard recorded as `CON-003`, not a registry collision.

## Near-duplicate command names

Command: `rg -n "def .*main|ArgumentParser|add_parser|add_subparsers" skills/adversarial-spec/scripts/debate.py skills/adversarial-spec/scripts/gauntlet_check_cli.py skills/adversarial-spec/scripts/dependency_semantics.py skills/adversarial-spec/scripts/usage_router.py skills/adversarial-spec/scripts/telegram_bot.py skills/adversarial-spec/scripts/validation_emission.py skills/adversarial-spec/scripts/gauntlet/cli.py`.

Result: no ambiguous same-surface command pair. `gauntlet` and `gauntlet-check` differ in purpose and required arguments; their shared timeout behavior is separately recorded as `FIND-003`.

## Numeric/document accuracy

Commands:

- `rg --files .architecture/structured/components | wc -l` → 11 components.
- `rg -n '^### ' .architecture/structured/flows.md` → 9 documented flows.
- `rg -n '^### [a-z].*' .architecture/structured/cross-references.md` → 8 boundary contracts.
- `rg --files skills/adversarial-spec/scripts execution_planner .claude/hooks -g '*.py' | wc -l` → 142 mapped Python files.

Result: current high-level document claims use those counts; no inaccurate numeric claim found.
