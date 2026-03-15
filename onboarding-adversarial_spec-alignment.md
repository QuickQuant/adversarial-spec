# Onboarding + Adversarial-Spec Alignment Specification

**For:** Brainquarters (onboarding system owner)
**From:** Adversarial-Spec design session
**Date:** 2026-01-27
**Status:** Ready for Brainquarters review

---

## Executive Summary

This document specifies how the Brainquarters onboarding system integrates with adversarial-spec's new **Roadmap Alignment** phase.

### Key Philosophy Change

**Before:** CLAUDE.md was heavy with domain knowledge to prevent Claude from making mistakes.

**After:** The adversarial-spec process prevents mistakes (roadmap, checkpoints, validation). CLAUDE.md becomes minimal.

### Goals

1. **Minimal CLAUDE.md** - Only safety rules + hooks, not domain history
2. **Task-based session detection** - Run `/tasks` to see where you are
3. **On-demand context** - Load domain context only when working on that domain
4. **Process handles quality** - Adversarial-spec's checkpoints prevent mistakes, not context bloat

This enables "adversarial-spec-first" development while maximizing context window for actual work.

---

## Minimal CLAUDE.md Philosophy

### Why Shrink CLAUDE.md?

| Before (Heavy) | After (Minimal) |
|----------------|-----------------|
| Load domain history to prevent mistakes | Process prevents mistakes |
| Full project context every session | On-demand context loading |
| Context window mostly "protective" | Context window for active work |

### What CLAUDE.md Should Contain (60-100 lines)

Based on [2026 best practices research](https://www.humanlayer.dev/blog/writing-a-good-claude-md):
- Frontier LLMs can follow ~150-200 instructions; Claude Code uses ~50 internally
- This leaves ~100-150 instruction budget for CLAUDE.md
- Over-specified CLAUDE.md causes instructions to be ignored uniformly

**Template structure (WHAT/WHY/HOW framework):**

```markdown
# CLAUDE.md
<!-- Version: 1.0 | Last reviewed: 2026-01-27 | Next review: 2026-02-17 -->
<!-- Target: 60-100 lines | If >100 lines, prune or move to .active_context.md -->

## WHAT: Project & Stack
[One-liner description + tech stack table + key paths]

## WHY: Purpose
[3-4 bullet points on what the project does]

## HOW: Working in This Codebase
- Session Start: /tasks, /adversarial-spec
- Commands: install, test, lint
- Context Loading: on-demand via context_loader.sh
- API Keys: env vars (never log values)

## Guardrails
[Only if hooks NOT installed; otherwise just "Hooks enforce safety"]

## Progressive Disclosure
[Table of what to read for deeper context]

## Review Trigger
[SmartCompact validation instructions]
```

**Key principles:**
1. **Universal content only** - Task-specific content goes in `.active_context.md`
2. **Reference, don't embed** - Use `file:line` pointers instead of code snippets
3. **Hooks for enforcement** - Don't document what hooks already enforce
4. **Review quarterly** - SmartCompact validates staleness at session end

### What Moves Elsewhere

| Content | New Location |
|---------|--------------|
| Domain knowledge | `onboarding/task-domains/<domain>/` (load on demand) |
| Session state | `.adversarial-spec/session-state.json` + Tasks |
| Historical patterns | `project-reference.md` (read when needed) |
| Roadmap context | `roadmap/*.md` (load for milestone work) |

### File Distinction

| File | Purpose | Loaded | Mutability |
|------|---------|--------|------------|
| `CLAUDE.md` | Universal project rules | Always (auto by Claude Code) | **Static** - never changes during session, git-tracked |
| `AGENTS.md` | Same as CLAUDE.md | When user opens Codex | **Static** - identical to CLAUDE.md |
| `.active_context.md` | Domain + session context | On-demand (after context_loader.sh) | **Generated** - includes session state if active |

### .active_context.md Relationship

With minimal CLAUDE.md, the context loading hierarchy becomes:

```
CLAUDE.md (~75 lines, always loaded)
    ↓ points to
.active_context.md (~500 lines, loaded on-demand)
    ↓ generated from
onboarding/task-domains/<domain>/*.md
```

**Flow:**
1. CLAUDE.md loads automatically (minimal, universal)
2. User runs `/tasks` to see current work
3. If working on a domain: `./onboarding/context_loader.sh <domain>`
4. Read `.active_context.md` once for that domain's deep context
5. Don't re-read individual source files

**What goes in .active_context.md:**
- Domain-specific patterns and constraints
- Historical decisions and their rationale
- Code chunks and meta chunks from `onboarding/context/`
- Architecture documentation from `task-domains/allcontext/`

**What stays in CLAUDE.md:**
- Project tooling (stack, commands)
- Session start instructions
- Progressive disclosure pointers
- Review trigger (for SmartCompact validation)

---

## Session State and Resume

### Session State File

Adversarial-spec writes `.adversarial-spec/session-state.json` for session continuity:

```json
{
  "schema_version": "1.0",
  "session_id": "adv-spec-20260127-150000",
  "current_phase": "debate",
  "current_step": "Round 3",
  "doc_type": "spec",
  "depth": "technical",
  "roadmap_path": "roadmap/manifest.json",
  "spec_path": ".adversarial-spec-checkpoints/latest-spec.md",
  "last_checkpoint": ".adversarial-spec-checkpoints/round-2.md",
  "models": ["codex/gpt-5.2-codex", "gemini-cli/gemini-3-pro-preview"],
  "updated_at": "2026-01-27T18:00:00Z"
}
```

### Session Resume Flow

```
New Session
    ↓
User runs /tasks (or TaskList)
    ↓
Sees: "[in_progress] [Debate R3] Round 3 critique"
    ↓
Runs /adversarial-spec
    ↓
Skill reads session-state.json
    ↓
Offers: "Resume session at Phase debate, Round 3?"
    ↓
Loads minimal context: checkpoint + last round
    ↓
Continues work
```

**Key insight:** Session continuity via Tasks + files, not CLAUDE.md pre-loading.

---

## CLI Opponent Models and Onboarding

**Important clarification:** CLI opponent models (Codex, Gemini CLI) do NOT use onboarding context.

| Actor | Has Onboarding? | Why |
|-------|-----------------|-----|
| Claude (orchestrator) | Minimal CLAUDE.md | Needs safety rules |
| CLI opponent models | NO | External reviewers, spec should stand alone |
| Gauntlet adversaries | NO (mostly) | Testing spec in isolation |
| `prior_art_scout` | Via pre-gauntlet scan | Needs codebase awareness |

The orchestrator (Claude) has project context. It:
- Can include files via `--context` flag when invoking debate
- Filters/contextualizes critiques based on project knowledge
- Synthesizes critiques through project understanding

Opponent models critique the spec as written - this is intentional.

---

## Background

### Current Onboarding Flow (Brainquarters)

```
1. Run context_loader.sh <domain>
2. CLAUDE.md generated (core + project + domain)
3. .active_context.md generated (deeper context)
4. Work on task
5. /checkpoint to save state (lightweight, ~5% context)
```

### New Adversarial-Spec Flow (with Roadmap Alignment)

```
1. Run /tasks to check for existing session
2. If resuming: /adversarial-spec loads from checkpoint
3. If new: adversarial-spec roadmap init
4. Roadmap created: manifest.json + rendered views
5. Tasks created for milestones + user stories
6. Run adversarial-spec critique (debate anchored to roadmap)
7. Implementation guided by execution plan
8. Tests linked via @spec:TC-X.Y tags
9. Progress tracked in _progress.json
```

### Integration Point

These flows work together via Tasks:
- Roadmap milestones become Tasks (always) and task domains (complex tier)
- `/tasks` shows current state without full context load
- `/checkpoint` saves state to files + updates task statuses
- Domain context loaded only when actively working on that domain

---

## Changes Required in Brainquarters

### 1. New File: `onboarding/roadmap-alignment.md`

Add this file to onboarding folders to indicate roadmap integration is enabled:

```markdown
# Roadmap Alignment Configuration
#roadmap #adversarial-spec

## Status
enabled: true
roadmap_path: roadmap/manifest.json

## Integration Mode
mode: auto  # auto | manual | disabled

## Auto-Created Domains
# These domains were created by adversarial-spec roadmap init
# Do not edit directly; they sync from manifest.json
auto_domains:
  - M1-core-engine
  - M2-user-interface
```

**Behavior:**
- If this file exists and `enabled: true`, context_loader.sh includes roadmap context
- `auto` mode means domains are managed by adversarial-spec
- `manual` mode means user manages domains, adversarial-spec only updates manifest

**Ad-hoc notes in auto-generated domains:**
- Auto-generated files (`task-summary.md`, `current-challenges.md`) are read-only
- To add project-specific notes, create `notes.md` in the domain folder
- `context_loader.sh` will include `notes.md` if it exists
- Example: `onboarding/task-domains/M1-core-engine/notes.md`

### 2. context_loader.sh Changes

Add session detection and roadmap context loading.

**Session Detection (inject into .active_context.md, NOT CLAUDE.md):**

CLAUDE.md must remain static for git stability. Session state goes into `.active_context.md`:

```bash
# Check for active adversarial-spec session
# NOTE: Inject into .active_context.md, NOT CLAUDE.md
if [ -f ".adversarial-spec/session-state.json" ]; then
    # Use python for JSON parsing (no jq dependency)
    session_info=$(python3 -c "
import json, sys
try:
    with open('.adversarial-spec/session-state.json') as f:
        d = json.load(f)
    print(f\"{d.get('current_phase', 'unknown')}|{d.get('current_step', 'unknown')}\")
except: print('unknown|unknown')
" 2>/dev/null)
    session_phase=$(echo "$session_info" | cut -d'|' -f1)
    session_step=$(echo "$session_info" | cut -d'|' -f2)

    cat >> "$ACTIVE_CONTEXT" << EOF

## Active Adversarial-Spec Session

**Status:** Phase ${session_phase}, ${session_step}
**Session file:** .adversarial-spec/session-state.json

To resume this session, run: \`/adversarial-spec\`

Do NOT start unrelated work without first checking session status.
EOF
fi
```

**Roadmap context loading (after domain loading):**

```bash
# After loading domain files, check for roadmap alignment
if [ -f "onboarding/roadmap-alignment.md" ]; then
    roadmap_enabled=$(grep "^enabled:" onboarding/roadmap-alignment.md | cut -d' ' -f2)

    if [ "$roadmap_enabled" = "true" ]; then
        # If domain is a milestone (M1-*, M2-*, etc), load milestone context
        if [[ "$DOMAIN" =~ ^M[0-9]+-.*$ ]]; then
            milestone_id=$(echo "$DOMAIN" | cut -d'-' -f1)

            # Add to .active_context.md
            echo "## Roadmap Context: $milestone_id" >> "$ACTIVE_CONTEXT"

            # Include milestone-specific roadmap files
            if [ -d "roadmap/milestones/$DOMAIN" ]; then
                cat roadmap/milestones/$DOMAIN/*.md >> "$ACTIVE_CONTEXT"
            fi
        fi

        # Always include progress summary
        if [ -f "roadmap/_progress.md" ]; then
            echo "## Current Roadmap Progress" >> "$ACTIVE_CONTEXT"
            cat roadmap/_progress.md >> "$ACTIVE_CONTEXT"
        fi
    fi
fi
```

### 3. Lightweight Checkpoint (Replaces SmartCompact)

**Key insight:** With minimal CLAUDE.md + Tasks + session-state.json, we don't need heavy "compaction". We need lightweight save/restore.

**New commands:**

| Command | Action | Context Cost |
|---------|--------|--------------|
| `/checkpoint` | Save state to files + update tasks | ~5% |
| `/resume` | Load from checkpoint (built into `/adversarial-spec`) | N/A |

**`/checkpoint` does:**
```
1. Write .adversarial-spec/session-state.json           # 1 file
2. Write .adversarial-spec/checkpoints/round-N.md       # 1 file
3. Symlink .adversarial-spec/checkpoints/latest.md      # 1 symlink
4. Update MCP task statuses                             # API calls
5. Run `adversarial-spec roadmap sync`                  # 1 bash command
6. Print brief summary                                  # Text output
```

**That's it.** No complex "compaction", no updating onboarding files, no generating summaries to save.

**Important:** `/checkpoint` is a **save point**, not a context clear. To clear context:
1. Run `/checkpoint` to save state
2. Start a new Claude Code session
3. Run `/tasks` → see session to resume
4. Run `/adversarial-spec` → loads from checkpoint

**Exit codes:**
| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Invalid arguments |
| 3 | Missing required file |
| 4 | Schema validation error |
| 5 | External command failure |
| 6 | Task update failure |

**Context thresholds:**

| Level | Action |
|-------|--------|
| **92%** | Info: "Context at 92%. Run `/checkpoint` at natural break." |
| **97%** | Auto: Save checkpoint, warn before continuing |

**Brainquarters update needed:** `~/.claude/commands/checkpoint.md` should implement this.

### CLAUDE.md Review (Periodic, Not Every Session)

CLAUDE.md review is triggered by date, not by checkpoint:

```markdown
### CLAUDE.md + AGENTS.md Review (every 3 weeks)

1. Parse version header: `<!-- Version: X.Y | Last reviewed: YYYY-MM-DD | Next review: YYYY-MM-DD -->`
2. If `Next review` date has passed, prompt user (advisory, not blocking)
3. Review checks: line count <100, pointers valid, commands work
4. Update dates if reviewed (next review = today + 21 days)
```

**Both files get same treatment:**
- `CLAUDE.md` - For Claude Code
- `AGENTS.md` - For Codex (identical content, even if Codex doesn't use it in our debate flow, users may open it directly)

**Trigger:** Checked when user runs `/checkpoint`. Advisory only.

### 4. Task Domain Template for Milestones

When adversarial-spec creates a milestone task domain, it uses this template:

**`onboarding/task-domains/M{N}-{slug}/task-summary.md`:**

```markdown
# {Milestone Name} Task Domain
#milestone-{N} #roadmap #{slug}

## Domain Overview

This domain covers: {milestone.description}

**Roadmap Source:** `roadmap/manifest.json` → Milestone {milestone.id}

## When to Use This Domain

Onboard into this domain when:
- Implementing features for this milestone
- Debugging issues in this area
- Writing or updating tests for this milestone
- Reviewing user stories and acceptance criteria

## Linked Roadmap Data

| Field | Value |
|-------|-------|
| Milestone ID | {milestone.id} |
| Status | {milestone.status} |
| Dependencies | {milestone.dependency_ids or "None"} |
| User Stories | {count} |
| Test Cases | {total} ({passing} passing, {failing} failing) |

## User Stories

{for story in milestone.user_stories}
### {story.id}: {story.action}

**As a** {story.persona}, **I want to** {story.action} **so that** {story.benefit}

**Status:** {story.status}

**Success Criteria:**
{for criterion in story.success_criteria}
- {criterion.description}
{/for}

**Test Cases:**
{for test in story.test_cases}
- [{test.status}] {test.id}: {test.description}
{/for}
{/for}

## Tags for Context Loading

```bash
./onboarding/context_loader.sh {domain_slug}
```
```

**`onboarding/task-domains/M{N}-{slug}/current-challenges.md`:**

```markdown
# {Milestone Name} - Current Challenges
#milestone-{N} #challenges

## Open Questions

{for question in milestone.open_questions where not resolved}
### {question.id}: {question.description}

**Status:** Open
**Added:** {question.created_at or "During roadmap creation"}
{/for}

## Blocked Items

{for story in milestone.user_stories where story.status == "blocked"}
### {story.id} is blocked

**Reason:** {story.blocked_reason or "Dependencies not met"}
{/for}

---

*This file is auto-generated from `roadmap/manifest.json`. Edit the manifest to update.*
```

### 5. Alignment File in Onboarding Folder

For projects using both systems, add an alignment file to explain the relationship:

**`onboarding/task-domains/allcontext/roadmap-integration.md`:**

```markdown
# Roadmap Integration with Onboarding

This project uses adversarial-spec's Roadmap Alignment to manage task domains.

## How It Works

1. **Roadmap is source of truth** for milestones, user stories, and test cases
2. **Task domains are auto-generated** from roadmap milestones (complex tier only)
3. **SmartCompact syncs progress** at session end

## File Hierarchy

```
roadmap/
  manifest.json         ← Source of truth (JSON)
  overview.md           ← Rendered view
  _progress.json        ← Test status
  _progress.md          ← Human-readable progress
  milestones/
    M1-core-engine/     ← Milestone detail files

onboarding/
  roadmap-alignment.md  ← Integration config
  task-domains/
    M1-core-engine/     ← Auto-generated domain
      task-summary.md   ← From manifest
      current-challenges.md ← From open_questions
```

## Rules

1. **Don't edit auto-generated domains directly** - Edit manifest.json instead
2. **Run `adversarial-spec roadmap sync`** after manifest changes
3. **Use context_loader.sh normally** - It includes roadmap context automatically

## Checking Progress

```bash
# View overall roadmap status
adversarial-spec roadmap status

# Focus on a specific milestone
./onboarding/context_loader.sh M1-core-engine
```
```

---

## New Task Metadata Fields

Brainquarters should recognize these metadata fields in MCP Tasks:

```json
{
  "schema_version": "1.0",
  "source": "roadmap",           // Indicates task came from roadmap
  "roadmap_path": "roadmap/manifest.json",
  "milestone_id": "M1",
  "user_story_id": "US-1",       // null for milestone-level tasks
  "test_case_id": "TC-1.1",      // null unless test_case task
  "task_type": "milestone|user_story|test_case|implementation",
  "test_summary": {
    "total": 5,
    "passing": 3,
    "failing": 1,
    "not_started": 1
  }
}
```

**Task naming conventions:**

| Task Type | Subject Format | Owner |
|-----------|----------------|-------|
| Milestone | `[M1] Core Engine` | `adv-spec:roadmap` |
| User Story | `[US-1] Bootstrap documentation` | `adv-spec:roadmap` |
| Test Case | `[TC-1.1] Bootstrap from Context7` | `adv-spec:test` |
| Implementation | `[IMPL] Implement bootstrap command` | `adv-spec:impl:{workstream}` |
| Debate Round | `[Debate R1] Requirements validation` | `adv-spec:debate` |

---

## Workflow Examples

### Example 1: Starting a New Project with Adversarial-Spec

```bash
# 1. Initialize roadmap (this also creates onboarding alignment)
adversarial-spec roadmap init --depth full

# Output:
# Roadmap created at roadmap/manifest.json
# Task domains created:
#   - onboarding/task-domains/M1-core-engine/
#   - onboarding/task-domains/M2-user-interface/
# Alignment file: onboarding/roadmap-alignment.md

# 2. Work on a milestone
./onboarding/context_loader.sh M1-core-engine

# 3. Run /checkpoint to save state + sync roadmap progress
```

### Example 2: Existing Project Adding Roadmap

```bash
# 1. Project already has onboarding/task-domains/auth/ and similar

# 2. Initialize roadmap from existing structure
adversarial-spec roadmap init --depth technical

# 3. Creates roadmap-alignment.md but preserves existing domains
# Auto-domains only created for complex tier

# 4. Manual domains continue to work normally
./onboarding/context_loader.sh auth  # Still works

# 5. New milestone domains also work
./onboarding/context_loader.sh M1-core-engine  # Also works
```

### Example 3: Context Loading with Roadmap

```bash
# Load milestone domain (includes roadmap context)
./onboarding/context_loader.sh M1-core-engine

# CLAUDE.md now includes:
# - core-practices.md
# - project-practices.md
# - M1-core-engine/task-summary.md
# - M1-core-engine/current-challenges.md
# - (Roadmap Alignment section with progress)

# .active_context.md includes:
# - roadmap/milestones/M1-core-engine/*.md
# - roadmap/_progress.md
# - Any other domain files
```

---

## Migration Path for Existing Projects

### Phase 1: Enable Coexistence

1. Adversarial-spec creates `onboarding/roadmap-alignment.md` on `roadmap init`
2. Existing domains are preserved
3. context_loader.sh checks for alignment file before adding roadmap context
4. No breaking changes to existing workflows

### Phase 2: Gradual Adoption

1. New features use adversarial-spec workflow with roadmap
2. Existing features can be migrated to roadmap milestones if desired
3. SmartCompact handles both manual and auto domains

### Phase 3: Full Integration

1. All new work starts with `adversarial-spec roadmap init`
2. Roadmap milestones become primary task organization
3. Manual domains used for cross-cutting concerns (not milestone-specific)

---

## Open Questions for Brainquarters

1. **Domain naming collision** - If a project has `onboarding/task-domains/core/` and roadmap creates `M1-core-engine/`, how should context_loader handle ambiguity? Proposal: Milestone domains always have `M{N}-` prefix to avoid collision.

2. **Checkpoint invocation** - `/checkpoint` should call `adversarial-spec roadmap sync` directly. Proposal: Direct call with error handling.

3. **Read-only status** - Should auto-generated domain files be marked read-only (chmod) to prevent accidental edits? Proposal: Yes, with a comment header explaining how to edit.

4. **Cross-project roadmaps** - If a roadmap spans multiple repos (monorepo milestones), how should onboarding handle this? Proposal: Defer to v2; for now, one roadmap per project.

---

## Implementation Checklist for Brainquarters

### Phase 1: Minimal CLAUDE.md + AGENTS.md
- [ ] Create minimal CLAUDE.md template (60-100 lines, WHAT/WHY/HOW framework)
- [ ] Create identical AGENTS.md (sync on review)
- [ ] Add version header: `<!-- Version: X.Y | Last reviewed: YYYY-MM-DD | Next review: YYYY-MM-DD -->`
- [ ] Review cycle: 21 days (not quarterly)
- [ ] Ensure hooks are installed and enforce safety
- [ ] Move domain content loading to on-demand (not automatic in CLAUDE.md)

### Phase 2: Slash Commands (`~/.claude/commands/`)
- [ ] Create `/checkpoint.md` - lightweight state save (replaces SmartCompact)
  - Write session-state.json
  - Update MCP task statuses
  - Run `adversarial-spec roadmap sync`
  - Check CLAUDE.md review date
- [ ] Update `/onboard.md` if it exists
- [ ] Deprecate `/smartcompact.md` (redirect to /checkpoint)

### Phase 3: Session Detection
- [ ] Update `context_loader.sh` to detect `.adversarial-spec/session-state.json`
- [ ] Add session status to CLAUDE.md output when detected
- [ ] Document `/tasks` as primary session check method

### Phase 4: Roadmap Integration
- [ ] Add `onboarding/roadmap-alignment.md` template to Brainquarters core
- [ ] Update `context_loader.sh` to load roadmap context for milestone domains (on-demand)
- [ ] Create milestone domain templates

### Phase 5: Documentation
- [ ] Add `onboarding/task-domains/allcontext/roadmap-integration.md` template
- [ ] Document task metadata fields for MCP Tasks compatibility
- [ ] Write migration guide for existing projects
- [ ] Test coexistence with existing onboarding workflows

---

## Version Compatibility

| Brainquarters | Adversarial-Spec | Compatibility |
|---------------|------------------|---------------|
| < 1.4 | Any | No roadmap integration |
| >= 1.4 | < 2.0 | Coexistence mode |
| >= 1.4 | >= 2.0 | Full integration |

Brainquarters 1.4 should be the minimum version that understands `roadmap-alignment.md`.

---

## Appendix: Test Case Linking Standard

Adversarial-spec uses `@spec:TC-X.Y` tags to link concrete tests to roadmap test cases.

**Syntax:**
```python
def test_bootstrap_from_url():
    """
    Test that documentation can be bootstrapped from a URL.
    @spec:TC-1.1
    """
    result = bootstrap("https://example.com/api-docs")
    assert result.success
```

**Alternative formats (all equivalent):**
```python
# @spec:TC-1.1
# Reference: TC-1.1
# spec:TC-1.1
```

**Linking behavior:**
- `adversarial-spec roadmap sync` scans for these tags
- Updates `_progress.json` with code_reference paths
- Test status determined by test runner output (pytest, jest, etc.)

This standard is language-agnostic and works in any file type that supports comments.
