# UI Design - Current Challenges
#ui-design #open-questions #design-notes

This document captures **open design questions and constraints** for the ui-design domain. Read this after the task-summary.

## 1. UI Technology Choice

The fundamental decision: what technology stack for the UI?

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| Web UI (FastAPI + HTMX) | Simple, works everywhere, SSE for streaming | Requires running a server |
| Web UI (FastAPI + React) | Rich interactions, modern tooling | Heavier bundle, more complexity |
| TUI (Textual/Rich) | No external deps, stays in terminal | Limited visual flexibility |
| Desktop (Tauri) | Native feel, single binary | Build complexity, platform testing |

**Open question**: What's the target deployment model? Local dev tool only, or something that could be shared/hosted?

## 2. Real-Time Progress Display

Debates can run for 10+ minutes with multiple rounds. Users need:

- Current round number and total expected
- Which models are currently being queried
- Streaming output as critiques come in
- Cost accumulation in real-time

**Technical options:**
- Server-Sent Events (SSE) for web
- WebSocket for bidirectional (if user can inject feedback mid-round)
- Polling (simplest but worst UX)

**Open question**: Should users be able to inject feedback mid-debate, or only at designated review points?

## 3. Multi-Model Critique Display

Each round has critiques from N models. How to display?

**Options:**
- Tabbed view (one model at a time)
- Side-by-side columns
- Unified view with model attribution
- Diff-style with agreements highlighted

**Open question**: What's more important - comparing models to each other, or seeing the synthesis?

## 4. Document Version Management

The spec evolves through many rounds. Users need to:

- See the current version
- Compare any two versions
- Rollback to a previous version
- Understand what changed in each round

**Technical consideration**: Checkpoints already exist in `.adversarial-spec-checkpoints/`. UI should leverage these.

## 5. Session Management UI

Sessions persist debate state. UI needs:

- List all sessions with metadata
- Resume a session
- Delete old sessions
- Export session history

**Open question**: Should the UI show session "health" (e.g., stale, incomplete, successful)?

## 6. Interview Mode UX

The interview mode is a multi-step Q&A. Current CLI is bare text prompts.

**UI opportunities:**
- Progress indicator (question N of M)
- Edit previous answers
- Save partial interviews
- Preview how answers will shape the spec

## 7. Cost Controls

Users care about costs. Potential UI features:

- Budget cap with warning before exceeding
- Cost breakdown by model
- "Cheap mode" that uses smaller models
- Historical cost tracking across sessions

**Open question**: Should the UI allow setting a max budget that auto-stops the debate?

## 8. Integration with Claude Code

The tool runs as a Claude Code skill. How does a UI fit?

**Options:**
- Separate web server, opened in browser
- Enhanced terminal output using ANSI/rich
- Native Claude Code UI extensions (if available)
- Hybrid: CLI for quick runs, web for deep sessions

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-22 | Domain created | Bootstrapping onboarding for future UI work |
