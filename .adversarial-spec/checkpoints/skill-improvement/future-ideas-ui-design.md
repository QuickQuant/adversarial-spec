# Future Ideas: UI Design
<!-- Archived: 2026-01-28 | Source: onboarding/task-domains/ui-design/ -->

This checkpoint preserves future feature ideas for a UI layer on adversarial-spec.
Not active work - reference when considering UI features.

---

## Overview

The tool is currently CLI-only. These are ideas for evolving toward a graphical interface.

## Potential Approaches

| Approach | Pros | Cons |
|----------|------|------|
| Web UI (FastAPI + HTMX) | Simple, works everywhere, SSE for streaming | Requires running a server |
| Web UI (FastAPI + React) | Rich interactions, modern tooling | Heavier bundle, more complexity |
| TUI (Textual/Rich) | No external deps, stays in terminal | Limited visual flexibility |
| Desktop (Tauri) | Native feel, single binary | Build complexity, platform testing |

## Key Design Considerations

1. **Long-running operations**: Debates can take many minutes; UI must show progress
2. **Multi-model display**: Show critiques from multiple models clearly
3. **Document comparison**: Show diffs between spec versions
4. **Cost visibility**: Make token usage and costs prominent
5. **Session management**: Resume, rollback, compare sessions

## Open Questions (Parking Lot)

- What's the target deployment model? Local dev tool only, or shared/hosted?
- Should users be able to inject feedback mid-debate?
- What's more important - comparing models or seeing synthesis?
- Should UI show session "health" (stale, incomplete, successful)?
- Should there be a max budget that auto-stops debate?

## Success Criteria (When We Build This)

1. Users can start and monitor debates without terminal
2. Progress is visible during long-running operations
3. Multi-model critiques are easy to compare
4. Spec history and diffs are accessible
5. Cost tracking is clear and actionable

---

**Status**: Future consideration, not active work.
