# Post-Fable Hardening — Skill Slice (G1+G2+G5)

> Status: **FINALIZED 2026-07-21** — canonical finalized spec:
> `spec-final.md` (v9.0, from draft v8.3 after gauntlet + final guardrail
> pass). This file remains the pre-draft investigation record.
> Goals source: docs/improvement-goals-2026-07.md (G1 post-Fable operability,
> G2 V-model ascending arm, G5 debate efficiency). Fizzy slice (G3+G4) is a
> coordinated separate plan in the fizzy repo.

## Investigation Results — Usage-Aware Dispatch Routing (G1, 2026-07-13..17)

Settled inputs for the debate draft; these are operator decisions plus verified
evidence, not open questions.

### Decisions (Jason, 2026-07-17, fb-20260717200015)
1. **Daemon route: self-supervised** — systemd user unit running
   `codex app-server --listen ws` (verified working on npm codex-cli 0.144.1;
   one daemon hosts many project sessions, cwd-per-session). Turnkey
   standalone-install/remote-control pairing rejected for now.
2. **Usage signal: headroom** (github.com/domanski-ai/headroom, local dashboard
   at `127.0.0.1:8388`). Its `/usage.json` snapshot covers **all** provider
   accounts — codex (5h/7d windows) *and* Claude (5h/7d plus a Fable-scoped
   window) — with per-account `routable`/`stale`/`ok` flags. Supersedes both
   candidate designs (codex app-server `account/rateLimits/read` polling;
   reactive-429 / usage-page screenshot for Claude).

### Verified facts
- sol/luna/terra share ONE codex rate-limit bucket; only 5.3-codex-spark is
  separate (live `account/rateLimits/read`, 2026-07-13).
- headroom identity for codex is verified via `codex_app_server`
  (`identity_method`), so the snapshot is the same source of truth the
  app-server would give, already aggregated.
- Fable-scoped Claude window is exposed (`scoped:Fable` used_percent) — the
  exact signal a Claude-side route guard needs.

### Prototype (evidence)
`skills/adversarial-spec/scripts/usage_router.py` + 12 unit tests
(`scripts/tests/test_usage_router.py`). Policy: default `codex/gpt-5.6-luna`
medium; codex bucket saturated (5h ≥85% or 7d ≥95%) → `gemini/gemini-3.5-flash`;
headroom dark/stale → fail-open luna-medium tagged `usage_blind`. Live smoke
2026-07-17: routed luna-medium off real snapshot (5h 0%/7d 62%), dispatched via
`codex exec`, returned ROUTER-SMOKE-OK.

### Open for debate
- Threshold values and whether 5h vs 7d saturation should route differently
  (cheap-tier degrade vs provider switch).
- Where the router loop lives long-term (skill script vs shared infra) and its
  telegram-ingest wiring (offset ownership vs wake-listener contract).
- Whether debate/gauntlet dispatch should consult the router before every
  round (usage-aware round pacing, G5 overlap).
