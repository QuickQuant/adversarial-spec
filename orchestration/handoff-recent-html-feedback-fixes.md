# Handoff: apply Jason's feedback to .reports/recent.html (surgical edit)

Role: fix rendering + iconography issues in `/home/jason/PycharmProjects/adversarial-spec/.reports/recent.html`
(single-file self-contained HTML report; ~keep everything else intact — this is
surgery, not regeneration).

Feedback being applied (verbatim from Jason):
1. Block "session-close": "22/22 cards terminal" is unclear → rephrase to plain
   language, e.g. "all 22 pipeline cards closed" with a hover/popover keeping the
   original detail. "891 tests green" → render as `891 ✓` with the ✓ styled green
   (#2ea043); keep "tests" as a muted label or popover. Debate-round mentions get a
   📣 prefix. Model names (claude / codex / gemini) must appear as brand-style
   badges instead of bare names: inline SVG monogram chips — Claude: rounded chip
   #d97757 background with a white asterisk-star mark; Codex: #0f0f0f chip, white
   circular knot-style "◯" mark; Gemini: #1a73e8→#8ab4f8 gradient chip with white
   four-point spark "✦". Title attribute = full model name. NO external images/fonts.
2. Blocks "failure-classes" and "goals": pills overflow their containers, and
   "pill fixed-open" breaks at narrower widths; cards reflow differently narrow and
   pills fail in different ways. Fix the pill system globally: containers get
   `display:flex; flex-wrap:wrap; gap; min-width:0`; pills get `max-width:100%;
   overflow-wrap:anywhere; white-space:normal` (or ellipsis + title where wrapping
   is wrong); any fixed-width/absolutely-positioned or "fixed-open" pill state must
   become flow-layout so it cannot escape its box. Verify no horizontal overflow of
   any card at 375, 768, 1280 px widths.

Boundaries:
- Edit ONLY `.reports/recent.html` in this repo. No git, no MCP, no network.
- Preserve: all qids/block ids, the report-feedback/1 JSON encoder behavior, all
  existing widget logic, the POST/copy buttons.
- End-state: file parses (open in headless chromium if available: zero console
  errors); grep-verifiable: "891" adjacent to a check glyph; "📣" present; no
  literal standalone words "claude"/"codex"/"gemini" in the affected model chips
  (title attrs are fine); document.body scrollWidth <= viewport width at 375px.
- Final message ≤ 8 lines: what changed, what you could not fix.
