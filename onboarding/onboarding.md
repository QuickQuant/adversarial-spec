<!-- Brainquarters Onboarding v1.3 | Requires: context_loader.sh 2.3+ | Last updated: 2026-01-13 -->
# Project Onboarding Spec

This spec defines how an LLM onboards into this codebase before working on any task.

**Complete onboarding before answering the user's first prompt or editing code.**

---

## 0. How context_loader.sh Works

Run `./onboarding/context_loader.sh <domain>` to generate two files:

### CLAUDE.md (auto-read by Claude Code)
Three-tier structure (~60% core + ~20% project + ~20% domain):
- `core-practices.md` - Universal rules from Brainquarters
- `project-practices.md` - Project-specific patterns/constraints
- `task-summary.md` - Main domain doc
- `current-challenges.md` - Active design questions

`AGENTS.md` is an identical copy for Codex.

### .active_context.md (read once for deeper context)
2-3x the size of CLAUDE.md:
- All other `*.md` files in the domain directory
- `task-domains/allcontext/*.md` - System architecture, cross-domain docs
- `project-reference.md` - Historical patterns and deep reference
- `onboarding/context/meta/<domain>/*.md` - Narrative chunks
- `onboarding/context/code/<domain>/*.code` - Code chunks

**Key point**: After running context_loader.sh, read `.active_context.md` once. Don't re-read individual source files.

---

## 1. Usage

```bash
# Work mode (default):
./onboarding/context_loader.sh <domain>

# Bootstrap mode (first-time, includes process specs):
./onboarding/context_loader.sh --bootstrap <domain>

# Check version:
./onboarding/context_loader.sh --version
```

---

## 2. Onboarding Phases

### Phase 0 – Generate Context
1. Identify the task domain from user's request
2. Run `context_loader.sh <domain>`
3. CLAUDE.md is auto-read. Read `.active_context.md` for deeper context.

### Phase 0.5 – Hooks Check (Optional)

If the project uses Claude Code hooks for runtime enforcement:

1. **Check if hooks are installed**: Look for `.claude/hooks/` directory
2. **If not installed**, hooks can be set up via Brainquarters:
   ```bash
   brainquarters/hooks/install_to_project.sh <project_path> [--mode flexible|strict]
   ```
3. **If installed**, verify sync with Brainquarters core:
   ```bash
   python3 brainquarters/hooks/build_hash_checklist.py \
     --hooks-dir <project>/.claude/hooks \
     --compare brainquarters/hooks/registry.json
   ```

Hooks provide **hard enforcement** of development practices at runtime, complementing the soft enforcement of Claude reading CLAUDE.md.

**Modes**:
- `flexible` - Warn on violations, allow continuation (good for learning/exploration)
- `strict` - Block on violations, require revision (good for production)

Some hooks (secret_exposure, banned_git_commands) always block regardless of mode.

### Phase 1 – Capture First Prompt
1. Understand what the user wants
2. Restate: What output? What constraints?
3. Do NOT start solving yet

### Phase 2 – Verify Understanding
1. From CLAUDE.md and .active_context.md, do you understand the domain?
2. Can you answer basic questions about the codebase?
3. If not, check if you used the right domain

### Phase 3 – Execute
1. Plan the work
2. Execute within `core-practices.md` + `project-practices.md` constraints
3. At session end, run SmartCompact

---

## 3. File Structure

### Files that go into CLAUDE.md
```
onboarding/
  core-practices.md            # Required - universal rules
  project-practices.md         # Required - project-specific patterns
  task-domains/<domain>/
    task-summary.md            # Required - main domain doc
    current-challenges.md      # Optional - active design questions
```

### Files that go into .active_context.md
```
onboarding/
  project-reference.md         # Historical patterns, deep reference
  task-domains/<domain>/
    *.md                       # All other domain files
    # EXCLUDED: *-archive.md, *-history.md (git-only)
  task-domains/allcontext/
    *.md                       # Global docs
onboarding/context/
  meta/<domain>/*.md           # Narrative chunks
  code/<domain>/*.code         # Code chunks
  _index.json                  # Dedup index
```

### Process Specs (bootstrap mode only)
```
onboarding/
  onboarding.md               # This file
  smartcompact-process.md     # End-of-session process
  llm-specific-guidance.md    # LLM behavioral guidance
```

---

## 4. Interplay with SmartCompact

- **Onboarding** pulls context via context_loader.sh
- **SmartCompact** pushes new knowledge back into source files

At session end, SmartCompact updates:
- `project-practices.md` - Add project-specific patterns discovered
- `task-summary.md` - Update domain status
- `current-challenges.md` - Add/resolve design questions
- `challenges-archive.md` - Optional: resolved challenges and historical notes
- `task-summary-history.md` - Optional: session logs and historical updates
- `onboarding/context/meta/*.md` and `onboarding/context/code/*.code` - Add chunks

---

## 5. For New Projects

1. Copy from Brainquarters:
   - `context_loader.sh`
   - `core-practices.md`
   - `project-practices-template.md` → `project-practices.md`
   - `onboarding.md`
   - `smartcompact-process.md`

2. Create domain structure:
   ```
   mkdir -p onboarding/task-domains/<domain>
   mkdir -p onboarding/context/meta/<domain>
   mkdir -p onboarding/context/code/<domain>
   ```

3. Create `task-summary.md` for your first domain

4. Run `./onboarding/context_loader.sh <domain>` to verify

---

## 6. File Classification

### Read-Only Files (Shared Infrastructure)
Do NOT edit these during normal work or SmartCompact:
- `core-practices.md`
- `context_loader.sh`
- `onboarding.md`
- `smartcompact-process.md`

If you discover improvements, note them in `current-challenges.md`.

### Versioned Files (Project Customization)
These files have a version header - increment the project version when adding content:
- `project-practices.md` - Project-specific patterns
- `roles/*.md` - Role-specific rules

### Project-Specific Files (Edit Freely)
- `project-reference.md` - Historical patterns, deep reference
- `task-domains/<domain>/` - Domain docs
- `task-domains/allcontext/` - Project architecture
- `onboarding/context/` - SmartCompact chunks

### Note: roles/ is Separate
The `roles/` directory is NOT loaded by context_loader.sh. It's a separate onboarding track:
- **Project onboarding** (context_loader.sh) → "What is this project?"
- **Role onboarding** (roles/) → "Who am I in this project?"

---

## 7. Summary

1. Run `context_loader.sh <domain>` to generate files
2. CLAUDE.md is auto-read (rules + domain summary)
3. Read `.active_context.md` once for deeper context
4. Execute within `core-practices.md` + `project-practices.md` constraints
5. Run SmartCompact at session end
