---
name: evaluate-plan
description: Evaluate a plan file against mapcodebase 3.0 architecture docs. Use when the user wants to review a plan, decide whether architecture docs are fresh enough, identify the blast zone and matched components, or determine what exploration should happen before adversarial-spec or implementation.
---

# Evaluate Plan

Take a plan file, determine how much the current architecture docs can be trusted, and produce a focused next-step recommendation.

This skill is a thin consumer over `mapcodebase 3.0`. It should not invent a second architecture system and it should not rediscover the codebase from scratch when fresh architecture docs already exist.

## Usage

```text
/evaluate-plan /path/to/plan.md
/evaluate-plan .claude/plans/example-plan.md
```

If the path is omitted, ask the user for the plan file path before doing anything else.

## Core Goal

Produce two outputs:

1. A plan evaluation:
   - Can the current `.architecture/` docs be trusted for this plan?
   - What parts of the system does the plan touch?
   - What do the docs already answer?
   - What still needs exploration?

2. A bootstrap handoff for later work:
   - what architecture docs to load
   - which components matter
   - what questions remain open
   - what exploration targets should be checked next

## Workflow

### 1. Read the Plan First

Read the plan file in full before touching architecture docs.

Extract the plan blast zone:
- file paths
- module names
- routes/endpoints
- data models / schema terms
- external systems
- auth / access-control changes
- UI components mentioned as reusable or modified

Summarize the blast zone in a compact list before deeper evaluation.

### 2. Architecture Gate

Inspect `.architecture/manifest.json` if it exists.

Classify the architecture state:

- `fresh`
  - manifest exists
  - `schema_version = 2.0`
  - `primer.md` and `access-guide.md` exist
  - `manifest.git_hash` matches current `HEAD`, or the manifest clearly reports `freshness_status = fresh`

- `caution`
  - schema `2.0` exists
  - accessor files exist
  - but `HEAD` differs from `manifest.git_hash`, or the manifest reports caution/drift

- `legacy`
  - no manifest
  - or `schema_version < 2.0`
  - or `primer.md` / `access-guide.md` is missing

- `stale`
  - docs exist but are materially out of date for the blast zone

If the state is `legacy` or `stale`, do not silently proceed as if architecture docs are trustworthy.

Tell the user:

`Cannot evaluate this plan with trustworthy architecture docs. Must run mapcodebase. Continue anyway?`

Present these options:

1. `Run /mapcodebase now`
2. `Use stale docs + commit delta review`
3. `Use targeted exploration only`
4. `Recommend a plan of action`

If the user chooses option 1:
- use full `/mapcodebase` for legacy output
- use `/mapcodebase --update` only for existing 3.0 output that is merely stale
- stop the evaluation until mapcodebase completes

### 3. Fresh-Docs Path

If architecture state is `fresh`, use the accessor layer in this order:

1. Read `.architecture/INDEX.md` for navigation only
2. Read `.architecture/primer.md`
3. Read `.architecture/access-guide.md` if it helps choose depth
4. Use `manifest.access_paths.plan_evaluation` if present
5. Match the blast zone against:
   - `components[].key_files`
   - `components[].intent_tags`
6. Read the 2-4 most relevant component docs from `.architecture/structured/components/`
7. Read `.architecture/structured/cross-references.md` if the plan changes:
   - contracts
   - routes
   - auth boundaries
   - data model / RPC surfaces
8. Read `.architecture/structured/flows.md` only if the plan crosses component boundaries or introduces a new end-to-end flow

Do not read the full architecture corpus by default.

### 4. Caution Path

If architecture state is `caution`, start with the same architecture-led path, then do a focused delta review:

1. Compare `manifest.git_hash` to current `HEAD`
2. Review commits and diffs since the manifest for files that overlap the blast zone
3. Prefer:
   - changed key files from matched components
   - changed contract / schema files
   - changed routes or access boundaries
4. Mark all conclusions as lower-confidence than the fresh-docs path

This mode is for “docs are still useful, but not enough by themselves.”

### 5. Exploration-Only Path

If the user chooses exploration without trustworthy architecture docs:

1. Start from files and modules named in the plan
2. Search outward toward:
   - contracts and exported types
   - routes / handlers / RPCs
   - auth and access boundaries
   - schema / migration / model files
   - reusable UI component interfaces
3. Only then inspect implementation details

This path is slower and lower-leverage than fresh architecture docs. Say that explicitly.

### 6. Recommendation Path

If the user asks for a recommendation instead of immediate evaluation, choose one of:

- `Run /mapcodebase now`
  - when docs are legacy or missing

- `Use stale docs + delta review`
  - when schema `2.0` exists and the blast zone only partially drifted

- `Use exploration only`
  - when the plan touches areas not represented in `.architecture/`, or when docs are too stale to trust

Give a short reason tied to freshness, blast zone overlap, and contract/boundary risk.

## Output Format

Return two sections.

### Plan Evaluation

- `Architecture status:` `fresh | caution | legacy | stale`
- `Recommendation:` one sentence
- `Blast zone:` concise list of files/modules/routes/contracts
- `Matched components:` component names plus why they matched
- `Docs used:` exact architecture docs relied on
- `What the docs already answer:` the useful context already present
- `Key contracts and boundaries:` types, data model surfaces, access boundaries, reusable components
- `Risks / mismatches:` where the plan conflicts with existing architecture or live-vs-target drift
- `What still needs exploration:` specific unanswered questions and target files
- `Suggested next step:` one concrete next move

### Bootstrap for Adversarial Spec

- `docs_to_load:` the smallest useful architecture set
- `components:` the key components to keep in context
- `open_questions:` unresolved items that matter for debate/spec work
- `explore_targets:` files or boundaries to inspect next
- `trust_notes:` freshness caveats to carry forward

## Rules

- `INDEX.md` is navigation only. Never treat it as substantive context.
- `primer.md` is the default initial payload.
- Do not default to `overview.md` or `flows.md` first.
- Fresh architecture docs should guide exploration, not be ignored.
- Legacy docs should not be treated as “good enough” without an explicit user choice.
- If using stale docs + delta review, say so explicitly in the result.
- Prefer matched component docs over broad source wandering.
- The goal is to warm up later `adversarial-spec` work, not to finish implementation planning in one jump.
