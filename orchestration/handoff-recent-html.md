# Handoff: build .reports/recent.html.tmp

Role: HTML/JS builder. Repo root = current directory (`adversarial-spec`).

Hard boundaries:
- Write EXACTLY ONE file: `.reports/recent.html.tmp` (create `.reports/` if missing).
- Do NOT touch any other file. Do NOT commit. No MCP, no network.
- Single-file HTML: all CSS/JS inline, vanilla JS only, zero external resources (no CDN, no fonts, no images). Must work opened via `file://` and via an HTTP reports server.
- Console must be clean (no errors/warnings from your own code).
- No hand-positioned SVG geometry (pure CSS layout only).
- Final message ≤ 10 lines.

## Deliverable spec

`<title>adversarial-spec — recent activity</title>`. Responsive; light + dark theme via `@media (prefers-color-scheme: dark)`. Top banner line: `Generated 2026-07-04 · session 91ad8d32 · git b31f8fd`.

### Header status table (3 rows)
- **Last worked:** 2026-07-03 → 2026-07-04 (this session)
- **What we did:** Closed the liveness-gate-test-ladder session (finalized card #5715 → Completed-Unmapped; 22/22 task cards terminal, 891 tests green). Ran a five-way investigation (architecture corpus, session artifacts + 6 process-failure reports, raw Claude/codex/gemini transcripts, Fizzy board history) and distilled it into 5 improvement goals (docs/improvement-goals-2026-07.md, commit b31f8fd).
- **Up next:** Jason hands back a goal via /goal — a dogfooded adversarial-spec session on post-Fable hardening. ~3 days of Fable access remain.

### Section 1 — block-id `session-close` — "Liveness-gate session closed"
Stat tiles (CSS grid): `22/22 cards terminal` · `891 tests green` · `12 debate rounds` · `3 agents (claude/codex/gemini)` · `6/11 reviews changes_requested` · `2 blocking bugs caught in review`.
Horizontal lane-flow strip (flex boxes with arrows, no SVG): New Todo → Review → Untested → Passed Test → Swept, caption "22 cards, ~2 days".
A native `<details>` "Review catches & friction": fail-open corrupt-JSON (W1-4), duplicate-spine override-floor (W1-1); friction: `tested_by` load-gate parity seam, 5 benign WRONG_LANE races, quota 429s.
Comment box (see feedback wiring).

### Section 2 — block-id `failure-classes` — "Five failure classes from the investigation"
Five `<details>` cards, each: name, one-liner, status pill, evidence file in small mono text.
1. **Verification theater at the seams** — components green while the end-to-end path fails; prediction-prime "2 days and it's not up"; gateway 25-bug ledger. Pill: `no owner phase — open`. Evidence: `docs/reports/process-retrospectives/2026-06-18-gateway-live-execution-process-study.md`
2. **Attest-instead-of-derive gates** — 12 seam holes; gates trust stored flags / local reimplementations instead of deriving from ground truth. Pill: `skill-side fixed / fizzy-side open (#1 #2 #5 #8 #10)`. Evidence: `adversarial-spec-process-failure-report-pipeline-seams-20260530.md`
3. **Debate inefficiency** — 12 rounds, 2 false convergences, derived-artifact drift caused R8/R11 rework. Pill: `open`. Evidence: `docs/reports/process-retrospectives/2026-06-18-card-5715-process-study.md`
4. **Dispatch fragility** — triple litellm pathway, dual CLI surfaces, 2 drifting model registries, quota deaths mid-debate. Pill: `open`. Evidence: `.architecture/concerns.md (CON-001/007/009)`
5. **Honor-system gates + 90K phase docs** — gates "LLM-enforced, not runtime-validated"; biggest post-Fable risk. Pill: `open`. Evidence: `2026-05-30-vmodel-pipeline-shortcomings.md`
Comment box.

### Section 3 — block-id `goals` — "Improvement goals G1–G5 (docs/improvement-goals-2026-07.md)"
Five goal cards, each: title, one-line problem, `<details>` with deliverables bullets, one-line success criterion.
- **G1 Post-Fable operability** (badge: `highest leverage`) — mechanize honor-system gates into code or rubric+golden-fixture; split 90K/76K/54K phase docs into lean operating spines + reference appendices; conductor competence harness ("given this session state, what's the next action?" golden evals). Success: every gate fires in code or has a rubric+fixture; no phase spine > ~25K; harness green under Sonnet/Opus.
- **G2 V-model ascending arm** — subsystem/system verification phases driven off the TMR registry; blocking pseudo→real promotion gate for critical-seam tests; ConOps walkthrough of the happy-path spine. Success: a session structurally cannot complete with unrun critical-seam tests.
- **G3 Fizzy contract reconciliation** — implement v4→v12 handover; SEC-1 F-prime gauntlet-entry gate; seam holes #1/#2/#5/#8/#10 + skip/deferred enum; playbook↔tool-surface parity (new seam: playbook names nonexistent `pipeline_finalize`). Success: skill v12 and fizzy schemas byte-agree; parity test in CI.
- **G4 Dispatch reliability** — one `call_model` pathway; unified CLI surfaces; one model registry shared with fizzy; declarative quota-death fallback policy; prompts.py shadow fix. Success: registry drift test in CI; simulated quota death resolves by policy.
- **G5 Debate efficiency** — frozen/settled packets; debate node registry; deterministic derived-artifact re-diff on every version bump; false-convergence guard. Success: fewer rounds, zero derived-artifact drift reaching the gauntlet.

**Decision widget** qid `q-20260704-goal-scope` (radio group, nothing preselected): "What shape should the /goal handback take?"
- a) One dogfooded session, two coordinated slices (skill: G1+G2+G5, fizzy: G3, G4 mechanical workstream) — as written *(recommended)*
- b) Trim to G1+G2 for the Fable window, rest post-Fable
- c) Fizzy-first: close G3 debt directly, then skill session
- d) Something else (explain in comment)
Plus a free-text comment field attached to this qid.

### Section 4 — block-id `approvals` — "Open approvals"
**Decision widget** qid `q-20260704-mapcodebase-refresh` (radio): "Architecture corpus is 50 commits stale (whole TMR/F-prime/validation-emission wave unmapped). Approve a mapcodebase+diagnosecodebase run at HEAD?"
- a) Yes — run before the debate so opponents get fresh context
- b) No — skip, budget elsewhere
- c) Fold into the goal session as its first step
Plus a free-text comment field attached to this qid.

### Section 5 — block-id `risks` — "Risks & housekeeping"
Rows with pills:
- `Fable access ends ~2026-07-07 (≈3 days)` — warning-styled pill.
- Duplicate Claude session `c4a2b65a` started 2026-07-04 11:19Z — likely killed this session's wake-listener (exit 144); listener restarted and holding.
- 4 commits on branch `phase7/liveness-gate-test-ladder-execution-plan` (d5e53ca, 8a2e46f, 7fc6b1b, b31f8fd) — not yet merged to main.
Comment box.

### Footer — feedback encoder (load-bearing, get this exactly right)
- Every section above has a comment `<textarea>` (block comment) with its block-id; the two decision widgets each also have a per-qid comment field.
- A live `<textarea id="feedback-json" readonly>` renders this JSON, re-generated on EVERY input/change event anywhere on the page:
```json
{"schema":"report-feedback/1","project":"adversarial-spec","report_generated_at":"2026-07-04T22:55:00Z",
 "answers":[{"qid":"q-20260704-goal-scope","choice":"a","comment":"..."}],
 "comments":[{"block":"session-close","comment":"..."}]}
```
- `answers[]`: one entry per ANSWERED radio (choice = the letter a/b/c/d); include its comment string (empty string ok) only when the radio is answered OR the qid comment is non-empty.
- `comments[]`: one entry per NON-EMPTY block comment box.
- **Copy JSON** button: `navigator.clipboard.writeText` with select()+`document.execCommand('copy')` fallback; show brief "copied" confirmation inline.
- **Submit** button: `fetch('/feedback/adversarial-spec', {method:'POST', headers:{'Content-Type':'application/json'}, body:...})`; show success/error inline. Note under buttons: "Submit works via the reports server; from file:// use Copy and paste it to Claude."

## End-state assertions (verify before finishing)
- File exists at `.reports/recent.html.tmp`, is valid standalone HTML, ~600–900 lines.
- Grep-verifiable: both qids appear exactly as spelled; all five block-ids appear; string `report-feedback/1` appears; no `http://` or `https://` resource loads (relative fetch URL only).
- Open-in-browser sanity is NOT required of you; static correctness is.
