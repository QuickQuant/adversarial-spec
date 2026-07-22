# C-5 Component Mini-Spec

Title: Critic-runner stdout contract + provenance-coupled salvage

One shared parser ([AGREE] xor critique+[SPEC], line-start markers, first-wins, duplicate-conflict invalid, size cap, escape rule) with fixture tests; debate_return_quality invalid marking; salvage flow (original path + SHA-256 at discovery + timestamp + dispatch id, copy + decisions-log entry through ONE StateTransaction); agentic-CLI prompts demand stdout-only.

Acceptance criteria:
- DF-17 parser edge fixtures green
- crash-injected salvage never exposes artifact without provenance record
- salvaged report recorded as violation evidence, never raw return

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task C-5.
Implementation status: partial — dispatch/return handling exists in models.py + fizzy round machinery (R3 gemini salvage was manual - the live incident this mechanizes); shared parser + transactional salvage new
