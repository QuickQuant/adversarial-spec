# Architecture Access Guide

> How to read `.architecture/` without loading everything.

## General Primer

1. Read [primer.md](primer.md).
2. Use [INDEX.md](INDEX.md) only for navigation and component selection.
3. Escalate to [overview.md](overview.md) if the primer does not explain the system shape well enough.

## Actionable Concerns

1. Read [concerns.md](concerns.md) for the fix-first rollup.
2. Each concern traces back to source items — follow `source_refs` to [findings.md](findings.md), [patterns.md](patterns.md), or hazards in `manifest.json`.
3. Read the relevant [component doc](structured/components/) to understand the blast zone before fixing.

## Plan Evaluation

1. Start with [primer.md](primer.md).
2. Read [INDEX.md](INDEX.md) to match the plan's paths, modules, and keywords to components.
3. Read the matched docs in [structured/components/](structured/components/).
4. Read [structured/cross-references.md](structured/cross-references.md) if the plan changes contracts, routes, or boundaries.
5. Read [structured/flows.md](structured/flows.md) only when the plan crosses component boundaries or introduces a new flow.

## Component Deep Dive

1. Start with [primer.md](primer.md).
2. Read [overview.md](overview.md) for full-system context.
3. Read the selected component doc in [structured/components/](structured/components/).
4. Read [structured/flows.md](structured/flows.md) only if the component participates in a larger multi-step flow.
