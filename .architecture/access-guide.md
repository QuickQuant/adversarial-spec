# Architecture Access Guide

> How to read `.architecture/` without loading everything.

## General Primer

1. Read [primer.md](primer.md).
2. Use [INDEX.md](INDEX.md) only to select a component.
3. Escalate to [overview.md](overview.md) for whole-system shape.

## Actionable Concerns

1. Read [concerns.md](concerns.md).
2. Follow its source references into the matched component doc and [findings.md](findings.md).
3. Use this route before planning a fix or starting adversarial review.

## Plan Evaluation

1. Start with [primer.md](primer.md), then match plan paths and nouns in [INDEX.md](INDEX.md).
2. Read the matching [component doc](structured/components/).
3. For any CLI/file/hook boundary, read [cross-references.md](structured/cross-references.md).
4. Read [flows.md](structured/flows.md) only when the change crosses components.

## Component Deep Dive

1. Start with [primer.md](primer.md) and the component’s quick-reference/contracts section.
2. Read [cross-references.md](structured/cross-references.md) for callers, contracts and config precedence.
3. Read [flows.md](structured/flows.md) only for lifecycle or recovery semantics.
