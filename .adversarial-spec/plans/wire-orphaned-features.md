# Plan: Wire Orphaned debate.py Features into Pipeline

## Context
Audit of debate.py revealed several well-implemented features that are never invoked by the adversarial-spec phase instructions. Some of these solve problems we've already hit in practice.

## Scope
Changes are limited to:
- Phase instruction files (`~/.claude/skills/adversarial-spec/phases/*.md`)
- debate.py (minor: temperature guard fix, error message update)
- No changes to models.py, gauntlet.py, or other support files

## Tasks

### T1: Wire `--preserve-intent` into debate rounds 2+
**Files:** `phases/03-debate.md`
**Change:** Add `--preserve-intent` flag to all `debate.py critique` invocations starting from Round 2.
**Why:** Round 6 showed Gemini removing the entire gradient descent section instead of flagging the contradiction. With `--preserve-intent`, models must justify removals rather than silently deleting content.
**Risk:** Low. Flag is already implemented and tested.

### T2: Wire `--telegram` into critique invocations
**Files:** `phases/03-debate.md`, `phases/05-gauntlet.md`
**Change:** Add `--telegram --poll-timeout 120` to debate.py critique calls. Remove the manual urllib/telegram-send notification blocks from phase instructions since debate.py handles it natively.
**Why:** Phases currently require Claude to manually construct Telegram messages via urllib after each round. debate.py already has `send_telegram_notification()` that formats results, sends them, and polls for feedback — all in one flag. Eliminates ~20 lines of manual notification logic per phase.
**Risk:** Medium. Need to verify `telegram_bot.py` reads the same config as the project's Telegram setup (ETB uses FIZZYBOT_TELEGRAM_KEY, debate.py's telegram_bot.py may expect different env vars). Test before deploying.
**Dependency:** Verify telegram_bot.py config matches per-project bot setup.

### T3: Wire `--focus` into round progression
**Files:** `phases/03-debate.md`
**Change:** Update the round focus progression table to pass `--focus` flags:
- Round 2: `--focus architecture`
- Round 3: `--focus performance` (or `security` depending on spec type)
- Round 4+: no focus (general refinement)
**Why:** The round focus progression is currently advisory text ("Round 2 focuses on architecture"). Adding `--focus` makes it a concrete instruction to the opponent models, not just guidance for Claude's synthesis.
**Risk:** Low. Focus areas are already defined in prompts.py.

### T4: Wire `--persona` into gauntlet or targeted rounds
**Files:** `phases/03-debate.md` (optional Round 4+), `phases/05-gauntlet.md`
**Change:** Document when to use `--persona` for targeted critique. Suggested additions:
- After Round 3, if security concerns were raised: `--persona "security engineer"`
- After Round 3, if performance concerns were raised: `--persona "oncall-engineer"`
**Why:** Personas give opponent models a specific lens. Currently unused despite being fully implemented.
**Risk:** Low. Advisory addition, not a required change.

### T5: Fix gpt-5 temperature guard in debate.py
**Files:** `debate.py` (line 994 area), `models.py` (if temperature is set there too)
**Change:** Extend `is_o_series_model()` to also cover gpt-5 models, OR use `litellm.drop_params = True` globally, OR remove custom temperature entirely (let models use their defaults).
**Why:** gpt-5.5 rejects `temperature != 1`. The guard at line 994 only checks o-series models. This caused the Round 6 API failure.
**Risk:** Low. Simple conditional fix.

### T6: Update `parse_models` error message
**Files:** `debate.py` (lines 846-880)
**Change:** Reorder the "no models configured" error message to list CLI models first, API models second. Match the docstring change that moved API providers to "Unsupported."
**Why:** Consistency with the docstring change Jason already made. Error message still suggests API keys as equal options.
**Risk:** None. Cosmetic.

### T7: Add `diff` action to phase inter-round workflow
**Files:** `phases/03-debate.md`
**Change:** After incorporating critiques into spec-draft-v(N+1), run `debate.py diff --previous spec-draft-vN.md --current spec-draft-v(N+1).md` and include the diff in the round summary.
**Why:** Currently Claude describes changes in prose. A unified diff is more precise and auditable.
**Risk:** Low. Action already implemented.

## Out of Scope (Leave as Manual-Only)
- `--session` / `--resume` — Claude manages its own session state; no need to duplicate
- `--profile` / `save-profile` — Pipeline picks models per-round; profiles are for manual CLI users
- `export-tasks` — Phase 7 creates execution plans directly; task extraction is a different workflow
- `--track-tasks` / TaskManager — Would need design work to avoid conflicting with Claude's own TodoWrite
- Bedrock — AWS routing for users who want it; not a default pipeline feature
- `--codex-search` — Web search during critique; niche use case
- `--json` output — Claude parses text output fine; JSON adds no pipeline value

## Evaluation Criteria
- Does each change reduce manual steps in the phase instructions?
- Does each change solve a problem we've already encountered?
- Is the risk proportional to the benefit?
- Does it avoid breaking existing manual CLI usage?

## Priority Order
1. **T5** (temperature fix) — Blocks API model usage, trivial fix
2. **T1** (preserve-intent) — Prevents content deletion, low effort
3. **T6** (error message) — Consistency fix, trivial
4. **T7** (diff action) — Useful for auditability
5. **T3** (focus flags) — Improves round quality
6. **T2** (telegram) — Biggest win but needs config verification
7. **T4** (persona) — Nice-to-have, advisory
