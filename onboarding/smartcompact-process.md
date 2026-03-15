<!-- Brainquarters SmartCompact v1.5 | Added Current Work + File References | 2026-01-26 -->
# SmartCompact Process Spec

This spec defines how to turn a coding/debugging/design session into reusable context for future onboarding.

SmartCompact and Onboarding are **paired pillars**:
- **Onboarding** pulls existing context via `context_loader.sh`
- **SmartCompact** pushes new knowledge back into source files

SmartCompact runs at the **end of a session**, never at the beginning.

---

## 0. File Editing Rules

### Read-Only Files (NEVER edit during SmartCompact)
These files are shared infrastructure - changes happen upstream in Brainquarters:
- `core-practices.md`
- `context_loader.sh`
- `onboarding.md`
- `smartcompact-process.md`

If you discover an improvement to these, note it in `current-challenges.md` for the user.

### Versioned Files (Update header when editing)
These files have a version header like:
```markdown
<!-- Base: Brainquarters v1.0 | Project: v1.2 | Last synced: 2025-12-18 -->
```

When you add content:
1. **Increment the Project version** (v1.2 → v1.3)
2. **Only add to project-specific sections** - don't modify base content
3. **Don't change "Last synced"** - that's for manual base updates

Versioned files:
- `project-practices.md` - Add patterns to the project-specific section
- `roles/*.md` - Add project-specific role rules (if applicable)

### Freely Editable Files
Everything else - task-domains/, allcontext/, onboarding/context/, project-reference.md - edit as needed.

---

## 1. What SmartCompact Writes

SmartCompact writes to these locations (matching what `context_loader.sh` reads):

### Files that go into CLAUDE.md (via context_loader.sh)
- `project-practices.md` - Project-specific patterns
- `task-domains/<domain>/task-summary.md` - Main domain doc
- `task-domains/<domain>/current-challenges.md` - Active design questions

### Files that go into .active_context.md (via context_loader.sh)
- `task-domains/<domain>/*.md` - All other domain files
- `task-domains/allcontext/*.md` - Global/cross-domain docs
- `project-reference.md` - Historical patterns and deep reference
- `onboarding/context/meta/<domain>/*.md` - Narrative chunks
- `onboarding/context/code/<domain>/*.code` - Code chunks
- `onboarding/context/_index.json` - Dedup index

### Archive Files (git-only, NOT loaded into context)
- `task-domains/<domain>/challenges-archive.md` - Resolved challenges + historical notes
- `task-domains/<domain>/task-summary-history.md` - Session logs + historical status

These files are excluded by context_loader.sh to prevent context bloat. They exist for git history and manual reference only.

---

## 2. SmartCompact Phases

At the end of a meaningful session:

1. **Phase S0** – Confirm domain and scope
2. **Phase S1** – Session recap (for yourself)
3. **Phase S2** – Update project-practices.md (if patterns discovered)
4. **Phase S3** – Update task-summary.md and current-challenges.md
5. **Phase S4** – Build/update meta context chunks
6. **Phase S5** – Build/update code context chunks
7. **Phase S6** – Maintain `onboarding/context/_index.json`
8. **Phase S7** – Sanity-check for future onboarding

---

## 3. Phase S2 – Evolving project-practices.md

**This is critical**: project-practices.md should evolve as the project matures.

### Versioning Reminder
This file has a version header. When adding patterns:
1. Increment the Project version in the header
2. Add to the project-specific section (look for "Project-Specific Patterns" or similar)
3. Don't modify base content from Brainquarters template

### Evolution During SmartCompact
After each significant session, ask:

1. **Did you discover a project-specific anti-pattern?**
   - Add it to the "Project-Specific Patterns" section
   - Example: "Never call X directly, always use Y wrapper"

2. **Did you learn a canonical way to do something?**
   - Add a pattern with good/bad examples
   - Example: Quarterdeck's exchange-specific logging imports

3. **Did the execution environment get clarified?**
   - Update the environment section with specific commands
   - Example: conda vs uv, specific test commands

4. **Did you hit a security edge case?**
   - Add it to the secret handling or fail-fast sections

### Format for New Patterns
Use dense JSON blocks like the existing rules:
```json
{
  "pattern_name": {
    "rule": "One-line description",
    "good": ["example 1", "example 2"],
    "bad": ["anti-pattern 1", "anti-pattern 2"],
    "rationale": "Why this matters"
  }
}
```

### What NOT to Add
- Temporary debugging notes
- One-off fixes that won't recur
- Patterns that are already in the code (just document in code)

---

## 3.5. Phase S2.5 – Hookification Check

After discovering a new pattern for project-practices.md, check if it should become a hook.

### Decision Criteria

Ask yourself:

1. **Is the violation detectable via pattern matching?**
   - Banned phrases → YES (regex on output)
   - Wrong command syntax → YES (regex on commands)
   - Missing action before another → YES (transcript check)
   - Architectural decisions → NO (semantic understanding needed)

2. **When would the violation be detectable?**
   - In Claude's prose response → `Stop` hook
   - In code Claude writes → `PostToolUse` hook on Write|Edit
   - Before a command runs → `PreToolUse` hook on Bash

3. **What should happen on violation?**
   - Learning/exploration work → Warn (flexible mode)
   - Production/critical work → Block (strict mode)
   - Security violation → ALWAYS Block (both modes)

### Hookification Steps

If the practice is hookable:

1. **Create the hook script** from template:
   ```bash
   cp .claude/hooks/_template.py .claude/hooks/<new_hook_name>.py
   ```

2. **Register in hook_config.json** `_hook_registry` section

3. **Add to settings.json** in the appropriate event (Stop/PreToolUse/PostToolUse)

4. **Add `hook` field** to the practice in project-practices.md:
   ```json
   {
     "practice_name": {
       "rule": "...",
       "hook": {
         "name": "<hook_name>",
         "version": "1.0.0",
         "modes": ["flexible", "strict"]
       }
     }
   }
   ```

5. **Update version header** in project-practices.md

6. **Generate updated hash checklist** (if in Brainquarters)

### If Not Hookable

Just add the pattern to project-practices.md normally - soft enforcement via Claude reading the rules is often sufficient for semantic or context-dependent patterns.

---

## 4. Phase S3 – Update Domain Files

**See `onboarding/task-domain-structure.md` for the canonical structure.**

Every domain MUST have these files:
- `task-summary.md` - Main domain doc
- `current-challenges.md` - Open design questions
- `restarttest-questions.md` - Context verification

### task-summary.md

**CRITICAL: The first two sections are MANDATORY and enable session continuity.**

#### 1. Current Work Section (REQUIRED FIRST)

Update this EVERY session. Format:
```markdown
## Current Work
<!-- Updated: YYYY-MM-DD -->

**Last session:** Brief description of what was done
**In progress:** What's partially complete
**Next:** What to do first when resuming
**Blocked by:** Any blockers (or "None")
```

#### 2. File References Section (REQUIRED SECOND)

Update when files are created or significantly modified:
```markdown
## File References
<!-- Recently created/modified files relevant to current work -->

| File | Purpose | Created |
|------|---------|---------|
| `path/to/new-file.ts` | What it does | YYYY-MM-DD |
```

**Cleanup rule:** Remove entries older than 2 weeks or no longer relevant.

#### 3. Rest of task-summary.md
- Update status if work changed the domain's state
- Add new invariants or goals discovered
- Keep it as the "one doc to understand this domain"

### current-challenges.md
- Add new design questions encountered
- Move resolved items to `challenges-archive.md`
- Keep active - only questions that need answers

### challenges-archive.md (optional)
- Add resolved challenges and historical debugging notes

### task-summary-history.md (optional)
- Add historical status updates and session logs

### restarttest-questions.md
- Update if domain understanding changed significantly
- Ensure questions still test current knowledge
- Keep answer key in sync with answers

---

## 4.5. File Size Limits

SmartCompact MUST enforce these limits on core domain files:

| File | Max Lines | When Exceeded |
|------|-----------|---------------|
| `task-summary.md` | 200 | Archive historical status, keep settled lessons |
| `current-challenges.md` | 150 | Move resolved items to `challenges-archive.md` |

**Archive files (`*-archive.md`, `*-history.md`):**
- Append-only logs for git history/reference
- **NOT loaded into .active_context.md** (excluded by context_loader.sh v2.3+)
- Use for: resolved challenges, session logs, historical debugging notes

**Settled lessons vs archives:**
- If a pattern is VALUABLE and should inform future work → keep in `task-summary.md`
- If it's purely HISTORICAL (what happened when) → archive it
- Rule: "Would a new agent need this to do the job?" YES → task-summary, NO → archive

**context_loader.sh health check:**
- v2.3+ warns at runtime if task-summary.md or current-challenges.md exceed limits
- If you see warnings, archive resolved content before ending the session

---

## 5. Phases S4-S5 – Context Chunks

### Meta Chunks (onboarding/context/meta/<domain>/*.md)
Narrative explanations of workflows, architecture, decisions.

Header format:
```
{"id":"meta_example","file":"onboarding/context/meta/domain/example.md","domains":["domain"],"tags":["tag1"],"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}

# Narrative Title

Markdown body...
```

### Code Chunks (onboarding/context/code/<domain>/*.code)
Important, reusable code slices with line references.

Header format:
```
{"id":"code_example","file":"src/module.py","start_line":100,"end_line":150,"hash":"sha256...","tags":["tag1"],"domains":["domain"],"created_at":"2025-01-01T00:00:00Z"}

def example_function():
    # code slice
    ...
```

---

## 6. Phase S6 – Maintain Index

`onboarding/context/_index.json` tracks all code chunks for deduplication:
```json
{
  "chunks": [
    {
      "id": "code_example",
      "file": "src/module.py",
      "hash": "sha256...",
      "domains": ["domain"],
      "tags": ["tag1"],
      "first_seen_at": "2025-01-01T00:00:00Z",
      "last_seen_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

## 7. Phase S7 – Sanity Check

Before finishing, imagine a fresh LLM tomorrow:

1. They run `./onboarding/context_loader.sh <domain>`
2. CLAUDE.md has: core + project practices + task-summary + challenges
3. .active_context.md has: other domain files + reference + chunks (archives excluded)

Ask yourself:
- Can they understand the domain from task-summary.md?
- Are the current challenges actually current?
- Did you add patterns to project-practices.md that would have helped YOU?
- Are context chunks up-to-date with code changes?

### Hook Sanity Check

If this project uses Claude Code hooks, also ask:

- **Are all hookable practices actually hooked?**
  - Review any new patterns added in this session
  - If hookable (detectable via regex), was a hook created?

- **Are hook versions current?**
  - If you modified a hook, did you increment the version?
  - Did you regenerate the hash checklist?

- **Is the mode appropriate for this project phase?**
  - Early development: flexible mode (warn only)
  - Pre-production: consider strict mode
  - Production: strict mode recommended

### Reporting Hook Improvements to Brainquarters

If you discover an improvement to a core hook:

1. Make the change locally in the project's hook
2. Increment the project version (e.g., 1.0.0 → 1.1.0)
3. Create a proposal file: `.claude/proposals/<hook_name>_<date>.md`
4. Notify Brainquarters to review and potentially propagate to all projects

---

## 7.5. Updating project-reference.md

`project-reference.md` is the append-only document for **REFERENCE** patterns - historical context, debugging notes, "good to know" information. Unlike project-practices.md (constraints), these are informational patterns that help but aren't required.

### Domain Tagging

Sections are tagged so context_loader.sh only loads relevant content for each domain:

```markdown
## Section Title
<!-- tags: domain1, domain2 -->

Content here...
```

**Tag rules:**
- `global` - Include for ALL domains (use sparingly)
- Domain names (e.g., `ws_feeding_convex`, `order-execution`) - Include only for those domains
- No tags = include for all (same as global)

### Adding New Entries

When you discover a useful pattern during a session:

1. **Decide if it's a CONSTRAINT or REFERENCE**
   - CONSTRAINT ("must do this or break something") → `project-practices.md`
   - REFERENCE ("good to know") → `project-reference.md`

2. **Add to project-reference.md with tags:**
   ```markdown
   ---

   ## Your Pattern Title
   <!-- tags: relevant_domain -->

   Description of the pattern.

   \`\`\`json
   {
     "pattern_name": {
       "problem": "...",
       "solution": "...",
       "implementation": "file/path.ts"
     }
   }
   \`\`\`

   ---
   ```

3. **Choose the right tags:**
   - If it's only useful for one domain → tag that domain
   - If it's useful across domains → tag "global"
   - If it's useful for 2-3 specific domains → list them all

### Example Tags by Domain

| Tag | When to use |
|-----|-------------|
| `global` | Convex patterns, env setup, tooling |
| `ws_feeding_convex` | Worker patterns, ingestion, WebSocket |
| `order-execution` | Order placement, exchange credentials |
| `polymarket_onchain` | Polymarket-specific patterns |
| `multiexchange_refactor` | Exchange adapter architecture |

---

## 8. Minimal vs Full SmartCompact

**Minimal** (small fix, little new understanding):
- Maybe update current-challenges.md
- Maybe a note in task-summary.md

**Full** (new feature, major debugging, refactor):
- Update project-practices.md with patterns
- Update task-summary.md with new status/invariants
- Create/update meta and code chunks
- Update onboarding/context/_index.json

---

## 9. Safety

SmartCompact must obey `core-practices.md` and `project-practices.md`:
- Do not record secrets in any files
- Do not include API keys, passwords, or sensitive URLs

---

## 10. Summary

SmartCompact produces/updates:
- `project-practices.md` - Evolving project-specific CONSTRAINTS
- `project-reference.md` - Append-only REFERENCE patterns (tagged by domain)
- `task-summary.md` - Domain status and invariants
- `current-challenges.md` - Active design questions
- `challenges-archive.md` - Resolved challenges + historical notes
- `task-summary-history.md` - Session logs + historical status
- `onboarding/context/meta/*.md` - Narrative chunks
- `onboarding/context/code/*.code` - Code chunks
- `onboarding/context/_index.json` - Dedup index

**Key insight**: project-practices.md should grow more project-specific over time. Every session is an opportunity to capture patterns that would help future LLMs.
