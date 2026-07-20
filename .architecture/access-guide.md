# Architecture Access Guide

> How to read `.architecture/` without loading everything. Generated at `ef18c66`; if a referenced source file changed after that commit, trust source over this corpus.

## General Primer

1. Read [primer.md](primer.md).
2. Use [INDEX.md](INDEX.md) only for navigation and component selection.
3. Escalate to [overview.md](overview.md) when the primer does not explain the system shape.

## Actionable Concerns

1. Read [concerns.md](concerns.md).
2. Follow each concern's source refs into [findings.md](findings.md), [patterns.md](patterns.md), or the cited component document.
3. Use [structured/cross-references.md](structured/cross-references.md) when the recommended action changes a shared type, file boundary, or persistence contract.

## Plan Evaluation

1. Start with [primer.md](primer.md).
2. Use [INDEX.md](INDEX.md) to match plan paths and terms to `components[].key_files` and `intent_tags`.
3. Read [concerns.md](concerns.md) for known hazards in the proposed blast zone.
4. Read the matched document in [structured/components/](structured/components/).
5. Read [structured/cross-references.md](structured/cross-references.md) for contracts, called-by relationships, and shared files.
6. Read [structured/flows.md](structured/flows.md) only when the plan crosses components or runtime boundaries.

## Component Deep Dive

1. Read [primer.md](primer.md), then [overview.md](overview.md) if needed.
2. Read the selected component document in [structured/components/](structured/components/); its Contracts and Invariants sections come first.
3. Read [concerns.md](concerns.md) if that component is named in a concern.
4. Read [structured/flows.md](structured/flows.md) for the component's cross-boundary flows.

`INDEX.md` is navigation-only. `manifest.json` is the machine-readable source of truth for freshness, component metadata, access paths, verification debt, and findings.
