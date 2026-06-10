# Plan template — the tree falls out of the work

Copy this skeleton. The goal: a normal, process-free engineering plan that produces
a correct altitude tree *as a byproduct* of grouping work by blast radius — no
bolted-on ceremony. If the altitude structure reads as natural engineering, the
system has succeeded. Proven exemplars: `davetrade/.adversarial-spec/specs/exchangekit/plan.md`
and `fizzy-pipeline-mcp/.adversarial-spec/specs/altitude-front-door/plan.md`. Model:
`reference/altitude.md`.

Delete the `> guidance` lines as you fill it in.

---

# <name> — Implementation Plan

## Triage  *(from `phases/00-triage.md` — runs before any session machinery)*

- **Complexity:** <simple|medium|complex> — integrations=<…>, unknowns=<…>
- **Root altitude:** <component|subsystem|system> — highest-blast item is <X>,
  because <why it sets the root>.
- **Go/no-go:** GO.

> The forcing rule, stated where you pick the root: *the highest-blast item sets the
> root.* Any item with irreversible external consequences (or that crosses a
> process/repo boundary) is `system` and forces a `system` root.

## Purpose

> One paragraph: what this builds and why now.

## Scope

**In:** <…>
**Out (now):** <…>

## Requirements  *(optional — user stories / invariants)*

| ID | Requirement |
|----|-------------|
| US-1 | … |
| INV-1 | … |

## Work breakdown — by blast radius

> Group work by **how far a mistake propagates**; each item earns verification
> *proportional to that blast radius*. The tree below is the V-model decomposition
> input — one root, each child of strictly higher-altitude parent.

```
ROOT  <name>                                   [<root altitude>]
├─ SS-1  <subsystem>                            [subsystem]
│   ├─ C-1  <component>                          [component]
│   └─ C-2  <component>                          [component]
└─ …                                            [<altitude>]
```

### Why each item sits where it does

> Plain reasoning per node, no jargon. "X is a component because a mistake is caught
> by a unit test and contained." "Y is subsystem because two consumers depend on its
> contract." "Z is system because <irreversible consequence / boundary crossed>."

## Verification ladder (proportional)

| Tier | Verification earned |
|------|---------------------|
| component | Unit / component tests. The floor — never zero. |
| subsystem | Integration tests + a contract-conformance suite every consumer must pass. |
| system | End-to-end against a safe stand-in (paper/staging) + consequence-safety guardrails (idempotency, dry-run default, kill switch, audit log) + manual go-live gate. |

> Keep only the rows your tree actually has. A component-rooted plan has one row.

## Sequencing

> Numbered build order. Prefer: de-risk the contract first, deliver value on
> reversible surfaces before any irreversible one, gate the irreversible flip.

## Risks

| Risk | Mitigation |
|------|------------|
| … | … |
