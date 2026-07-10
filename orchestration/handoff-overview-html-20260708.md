# Handoff: build .reports/overview.html (first revamp) + report-state "overview" section — 2026-07-08

Role: HTML build executor for the html-whole-project report. Repo root = current directory (/home/jason/PycharmProjects/adversarial-spec). This is the FIRST generation of overview.html — the long-lived "step back" page read at architecture-decision gates.

## Hard boundaries
- No MCP, no git commits, no network (single-file HTML, everything inline, zero external URLs).
- Write ONLY: `.reports/overview.html`, `.reports/report-state.json` (add/replace the `overview` section, preserve `schema_version`, `recent`, `feedback` verbatim), optional `orchestration/overview-html-verify-notes.md`. Atomic writes; report-state under `flock .reports/.lock`.

## Authoritative inputs (read in this order; NEVER invent facts not in these)
1. `.architecture/primer.md` — system narrative source.
2. `.architecture/INDEX.md` — component table (12 components), architecture decisions (5 one-liners), retired-module list.
3. `.architecture/concerns.md` — fix-first concerns (CON-001…009); summarize top items, do not copy wholesale.
4. `.architecture/overview.md` — deeper narrative where primer is thin.
5. `.adversarial-spec/checkpoints/checkpoint-202607081610-roadmap-complete-debate-entered.md` — current program state; seeds the first appended-tail entry.
6. `.adversarial-spec/specs/post-fable-hardening-skill/roadmap/manifest.json` — the in-flight spec (9 milestones/17 US, goals G1/G2/G5) driving the in-flight markers.
7. `.adversarial-spec/sessions/adv-spec-202607060132-post-fable-hardening-skill.decisions.log` — decision ledger.
8. `docs/improvement-goals-2026-07.md` — the five failure classes (G1–G5) motivating current work.

## Page structure
**MANDATORY top banner**: architecture corpus is CAUTION-stale — generated 2026-06-11 at commit f198887, now 50 commits behind b31f8fd; the TMR/F-prime/validation-emission wave is unmapped; refresh deliberately deferred (Jason 2026-07-05). Narrative claims below derive from that corpus and may trail HEAD.

**Narrative half** (from inputs 1–4, widget-dense where a diagram beats prose):
- What the program is: Claude Code skill refining specs through multi-model adversarial debate, driving an 8-phase pipeline (requirements → roadmap → debate → target-architecture → gauntlet → finalize → execution → implementation) coordinated on a Fizzy board.
- How it works: pipeline flow diagram (CSS/flex, no hand-positioned SVG); debate (collaborative Opponents, numbered rounds, convergence) vs gauntlet (hostile Adversary personas, 7 internal steps, output = Concerns) — render this distinction as a two-column comparison diagram, it is the most-confused concept; component table from INDEX (name, purpose, key files) as a compact grid with plain-language purpose lines; the 5 architecture decisions as a pill list.
- Why / current program: the five failure classes from docs/improvement-goals (verification theater at seams, attest-not-derive gates, debate inefficiency, dispatch fragility, honor-system gates + oversized phase docs) — diagram as a before/after or problem→goal mapping to G1–G5. Note G3/G4 live in the fizzy slice / a later session.
- Top concerns from concerns.md, few lines each, plain language.

**In-flight markers** (visible ⚠ chips on affected narrative sections): spec `post-fable-hardening-skill` is in debate NOW and will change: phase-doc corpus (G1 decomposition), gate enforcement (G1 mechanization), debate engine (G5 freeze/reconcile), pipeline completion semantics (G2 verification phases + promotion gate). Marker text: "⚠ changing during post-fable-hardening-skill, in progress".

**Appended tail** (dated, newest last) — seed with one entry: 2026-07-08, session 3ba11a17-79e7-4c2b-afa4-6d13b2e22e94, checkpoint checkpoint-202607081610-roadmap-complete-debate-entered.md, git b31f8fd: "Requirements gate passed with G1-F2 amendment (discrete phase-doc units, no size caps). Roadmap completed: 9 milestones / 17 user stories through one debate round; card 5857 in Debate lane."

**Header**: link to `recent.html` ("recent activity" companion). Clock widget — identical spec to recent.html: monospace 3-line generated/now/age, America/Chicago, minutes precision, live ~30s update, sv-SE formatter for date/time + separate en-US formatToParts timeZoneName for the CDT/CST abbreviation.

**Every section gets a comment-box affordance** wired into a page-bottom report-feedback/1 JSON encoder (project "adversarial-spec", block ids: "narrative-what", "narrative-how", "narrative-why", "components", "concerns", "tail") + Copy button + Submit POST to relative `/feedback/adversarial-spec` (note Submit needs the reports server; Copy works from file://). No decision widgets on this page (none pending here — recent.html owns those).

## Style (same rules as recent.html)
`<meta name="viewport" content="width=768">` pinned; grey/beige/sepia light palette; pills contained (flex-wrap:wrap, min-width:0); symbols over words; no unexplained jargon (every internal term gets a plain phrase inline; popovers only for depth); Jason verbatim quotes bold+italic spartan green if any are used.

## report-state.json — add:
```json
"overview": {"last_full_revamp_at": "<now ISO>", "mapcodebase_git_hash": "f198887",
  "appended": [{"at": "<now ISO>", "session_id": "3ba11a17-79e7-4c2b-afa4-6d13b2e22e94",
                "checkpoint_file": "checkpoint-202607081610-roadmap-complete-debate-entered.md",
                "git_head": "b31f8fd"}],
  "redlines": []}
```

## Verification + end-state assertions
- Playwright soft gate if available (768+1280, console clean, overflow check); if not installed, note and ship.
- `.reports/overview.html` exists; contains the staleness banner text "f198887", the in-flight marker string "post-fable-hardening-skill", a link to recent.html, zero `https?://` matches, and all six block ids.
- `python3 -c "import json; s=json.load(open('.reports/report-state.json')); assert 'overview' in s and 'recent' in s"` passes.
- Final message ≤ 12 lines.
