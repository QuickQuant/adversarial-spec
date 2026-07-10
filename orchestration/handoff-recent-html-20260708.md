# Handoff: rebuild .reports/recent.html + report-state.json (2026-07-08)

Role: you are the HTML build executor for the html-recent-activity report. Repo root = current directory (/home/jason/PycharmProjects/adversarial-spec).

## Hard boundaries
- No MCP calls, no git commits, no network fetches (page must be self-contained, no CDN).
- Write ONLY: `.reports/recent.html`, `.reports/report-state.json`, and (optional) `orchestration/recent-html-verify-notes.md`. Atomic writes (tmp + rename). report-state read-modify-write under `flock .reports/.lock`.
- Do not touch `.adversarial-spec/` or `skills/`.

## Authoritative inputs (READ THESE, in order)
1. `.adversarial-spec/checkpoints/checkpoint-202607081610-roadmap-complete-debate-entered.md` — the primary story (completed work, next action, open questions, manifest status).
2. `.adversarial-spec/sessions/adv-spec-202607060132-post-fable-hardening-skill.decisions.log` — decision ledger (one line per landed decision).
3. `.adversarial-spec/specs/post-fable-hardening-skill/roadmap/manifest.json` — 9 milestones / 17 user stories, dependency edges, KPIs, debate_rounds record.
4. `.reports/report-state.json` — previous state (preserve schema; you own only the "recent" section + leave "feedback" as-is).
5. Previous `.reports/recent.html` — reuse scaffolding/styles if useful; ALL content is superseded except anything still true you consciously carry.

## Page requirements (single-file HTML, `<meta name="viewport" content="width=768">`)

Header: status table — Last worked: 2026-07-08 16:10 UTC (checkpoint); What we did: requirements gate passed with Jason's G1-F2 amendment (phase docs decomposed into discrete units, his words: "no more, no less" — render verbatim Jason quotes bold+italic in spartan green); roadmap completed through one debate round with 4 accepted revisions; card 5857 → Debate lane. Up next: author spec draft v1 (technical depth), then debate rounds via pipeline tools.

Mandatory clock widget (monospace 3-line, America/Chicago, minutes precision, live-updating ~30s):
```
generated  2026-07-08 11:10 CDT
now        <live>
age        <Nd Nh Nm>
```
Use Intl.DateTimeFormat('sv-SE',{timeZone:'America/Chicago',hour12:false,...}) for date/time; tz abbreviation from a SEPARATE en-US formatter formatToParts timeZoneName ('sv-SE' gives "GMT−5", wrong).

Sections (each feature block gets a feedback affordance — decision widget or comment box wired into the JSON encoder):

1. **Pipeline position** — 8-phase flow diagram (requirements ✓, roadmap ✓, debate ◉ current, target-architecture/gauntlet/finalize/execution/implementation pending), card 5857 chip. CSS/flex boxes+arrows, no hand-positioned SVG.
2. **Roadmap ladder** (block-id "roadmap-ladder", comment box) — 9 milestones from manifest.json as a dependency diagram: M0 standalone; M1→M2→M3; M1→M4→M5→M6; M7→M8. Each node: id, short title, US-count chip, one-line PLAIN-LANGUAGE purpose (no jargon; M5 example: "a session cannot complete while critical tests are unrun"). US-15 (waiver) and US-16 (boundary) marked as debate-round additions.
3. **Debate R1 outcome** (block-id "debate-r1", comment box) — model badges as inline-SVG monograms (Codex black, Gemini blue; never bare names). 4 accepted revisions with their tradeoffs INLINE VISIBLE (not behind popovers): waiver mechanism US-15; expanded personas; global KPIs; contract-boundary US-16 + user-journey section. 1 rejected: gemini's ≤15KB context cap — rejected because it contradicts Jason's no-size-caps amendment.
4. **Ops incidents** (block-id "ops-incidents", comment box) — before/after style diagram, three items: (a) gemini-cli fresh spawns fail IneligibleTierError (latest CLI 0.49.0, oauth-personal; live panes unaffected; dispatches switched to API-path gemini/gemini-3.5-flash); (b) debate.py preflight breaks on thinking models — tiny ping budget eaten by internal reasoning → false failure on a working model; workaround --skip-preflight; flagged as an M1 mechanization candidate; (c) session_activity_logger v1.1 — SessionStart now logs invoker ancestry+tty+env, UserPromptSubmit logs idle gap with cold:true past 300s cache TTL (change lives uncommitted in the Brainquarters repo).
5. **Decision widgets** (both MUST appear as interactive choices with inline tradeoff text, wired to encoder):
   - qid `q-20260708-branch-commit`, topic "Commit session work to spec branch". choices: `a: create spec/post-fable-hardening branch + commit now` (goals doc mandates work on branches; work currently sits uncommitted on the stale phase7/liveness-gate-test-ladder branch), `b: keep accumulating uncommitted until spec finalize` (fewer commits, more loss risk), `c: commit to current branch as-is` (fast, wrong branch name).
   - qid `q-20260708-wake-cost-concern`, topic "Wake/listener lifecycle cost as spec concern". choices: `a: add as named concern for debate` (stop-hook demands a listener, harness kills it, each death costs a full-context wake — honor-system seam in G1 scope), `b: out of scope; ops annoyance only`.
6. Page bottom: live report-feedback/1 JSON encoder textarea (schema below) updating as controls change + Copy button + Submit button POSTing to relative `/feedback/adversarial-spec` (with a visible note that Submit needs the reports server; Copy works from file://).

Feedback JSON schema:
```json
{"schema":"report-feedback/1","project":"adversarial-spec","report_generated_at":"<generated ISO>","answers":[{"qid":"...","choice":"a","comment":""}],"comments":[{"block":"roadmap-ladder","comment":""}]}
```

Style: grey/beige/sepia light palette (NOT blue-tinted white); pills contained (flex-wrap:wrap; min-width:0; no fixed pill widths); symbols over words (✓ counts, 📣 debate rounds); every jargon term gets plain phrasing inline or popover (popovers for depth only, never first-level meaning).

## report-state.json — replace the "recent" object with:
```json
{"generated_at":"<now ISO UTC>",
 "covered_sessions":["3ba11a17-79e7-4c2b-afa4-6d13b2e22e94","078a6e36-cf43-4244-b143-76541d6dbb8a"],
 "last_event_ts":"<now ISO>","git_head":"b31f8fd",
 "covers_checkpoint":"checkpoint-202607081610-roadmap-complete-debate-entered.md",
 "summary_recent":"Requirements gate passed with G1-F2 amendment (discrete phase-doc units, no size caps). Roadmap completed: 9 milestones/17 user stories through one debate round (codex + gemini-3.5-flash), 4 revisions folded in, G4 excluded. Card 5857 advanced to Debate lane.",
 "next_up":"Author spec draft v1 (technical depth) from the roadmap manifest, then run debate rounds via pipeline tools.",
 "pending_questions":[
   {"qid":"q-20260708-branch-commit","topic":"Commit session work to spec branch","choices":["a: create spec/post-fable-hardening branch + commit now","b: keep accumulating uncommitted until finalize","c: commit to current branch as-is"]},
   {"qid":"q-20260708-wake-cost-concern","topic":"Wake/listener lifecycle cost as spec concern","choices":["a: add as named concern for debate","b: out of scope; ops annoyance only"]}]}
```
Preserve `schema_version` and the `feedback` section verbatim.

## Verification (soft gate)
If Playwright (python or node) is available: load the page at 768 and 1280 px, click every widget option, assert the JSON textarea reflects choices, check console clean, screenshot both widths to `.reports/` (overwrite ok) and check for horizontal overflow. If Playwright unavailable: note that in your final message and ship anyway.

## End-state assertions (verify before finishing)
- `.reports/recent.html` exists, contains BOTH qid strings, the clock widget, and zero external URLs (grep for `https?://` — only the Submit POST path `/feedback/adversarial-spec` relative URL allowed).
- `python3 -c "import json; json.load(open('.reports/report-state.json'))"` passes; recent.pending_questions has exactly 2 entries.
- Final message ≤ 12 lines: what shipped, verification results, any deviations.
