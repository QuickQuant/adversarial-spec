# Handoff B: Draft 25 Per-Card Concern-Context Comments (Codex)

You are Codex, working alone in repo root `/home/jason/PycharmProjects/adversarial-spec`.
Your job: draft the Step 10 concern-context comment for every node of the
validation-leg-process execution plan — LOCAL ONLY. A separate agent posts them to the
board later, after cards exist.

## Hard boundaries
- Do NOT call any MCP tool. Do NOT post anything. Do NOT git commit.
- Only write the two output files listed below.

## Inputs
1. `.adversarial-spec/specs/validation-leg-process/execution-plan.md` — the 25-node plan
   (SYS, SS-1..SS-5, C-1.1..C-1.4, C-2.1..C-2.3, C-3.1..C-3.3, C-4.1..C-4.6,
   C-5.1..C-5.3). Each node lists concern_refs, invariant_refs, depends_on, realizes.
2. `.adversarial-spec/specs/validation-leg-process/gauntlet-concerns-2026-06-11.json`
   — the accepted gauntlet concerns (IDs like CB-1, RC-2, FM-5, SEC-1, DD-6, OP-3…)
   with their descriptions. Use these to explain WHY each task exists.
3. `.adversarial-spec/specs/validation-leg-process/spec-output.md` — FINAL spec, for
   plain-language problem descriptions where the concern text is too terse.

## Comment contract (from skills/adversarial-spec/phases/07-execution.md Step 10)
Each comment must include:
1. Which concern(s) the task addresses (with IDs traceable to the concerns doc)
2. The problem in plain language — what breaks without this
3. Why the fix takes this shape — which gauntlet concerns constrained the approach
4. How it connects to other cards — depends_on, Wave-0 blocking, fallback relationships
   (e.g. C-4.5 self-check runs on C-4.4's emitted bytes; SS-1 ledger-core blocks all
   feature subcommands; C-5.3 dogfood depends on everything)

Format per comment (markdown):
```
**Context: <primary concern id(s)> — <short problem description>**

[1–3 paragraphs]
```

Guidelines:
- Write for a human reading ONE card, not the full spec.
- Under 200 words each. Orient, don't restate the spec.
- For nodes with no driving concern (e.g. C-4.6 status reporter, doc tasks), explain
  what downstream tasks/agents need from this node instead.
- Subsystem and system nodes: summarize what the subtree delivers and the architecture
  spine rules (AS-1..AS-7) the children must obey — these comments orient reviewers.

## Deliverables
1. `.adversarial-spec/specs/validation-leg-process/orchestration/comments-draft.json`
   — a single JSON object: every task_id as key, comment markdown string as value.
   EXACTLY 25 keys: SYS, SS-1, SS-2, SS-3, SS-4, SS-5, C-1.1, C-1.2, C-1.3, C-1.4,
   C-2.1, C-2.2, C-2.3, C-3.1, C-3.2, C-3.3, C-4.1, C-4.2, C-4.3, C-4.4, C-4.5, C-4.6,
   C-5.1, C-5.2, C-5.3. Valid UTF-8 JSON, parseable by `json.load`.
2. `.adversarial-spec/specs/validation-leg-process/orchestration/comments-notes.md`
   — brief: any concern ids referenced in the plan you could NOT find in the concerns
   JSON, and any judgment calls.

Your final message: 3–5 lines — file paths, key count, any missing-concern flags.
