# Pre-Gauntlet Adversary: Technical Design

**Status:** Design Complete (Reviewed by Gemini Pro 3 + Codex xhigh)
**Created:** 2026-01-24
**Based on:** adversary-request-existing-system-compatibility.md

---

## Problem Statement

During implementation of a spec that passed the full gauntlet (179 concerns), we discovered the codebase itself was not deployable due to pre-existing schema/data drift. None of the 5 adversarial LLMs caught this because they reviewed the spec in isolation, without access to actual codebase state.

---

## Goals and Non-Goals

### Goals
- Deterministic, read-only collection of repo state with machine-readable report
- Explicit alignment gate with interactive and non-interactive behavior
- Config-driven checks per document type (PRD, Tech Spec, Debug)
- Secret-safe handling of output and context injection

### Non-Goals
- Automated fixes, rebases, or schema migrations
- Remote repo access or network calls
- Full static analysis or style enforcement beyond context injection
- Long-running builds beyond configured limits

---

## Architecture Overview

The `existing_system_compatibility` adversary operates as a **Hybrid Adversary** with two phases:

1. **Deterministic Collection** - Scripts gather actual codebase state
2. **Probabilistic Analysis** - LLM compares spec against collected context

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRE-GAUNTLET PHASE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Git Position Collector (READ-ONLY)                              │
│     ├── Current branch + head commit                                │
│     ├── Commits ahead/behind base branch                            │
│     ├── Last sync with base (merge-base date)                       │
│     └── Recent commits to affected files                            │
│                                                                     │
│  2. System State Collector                                          │
│     ├── Build command output (shell=False, redacted)                │
│     ├── Schema file contents (with SHA256)                          │
│     ├── Critical path directory trees                               │
│     └── Git status (dirty/clean)                                    │
│                                                                     │
│  3. Spec Affected Files Extractor                                   │
│     └── Parse spec text for file path references                    │
│                                                                     │
│  4. Context Injection → LLM Prompt                                  │
│     ├── SYSTEM CONTEXT section (ground truth)                       │
│     ├── GIT POSITION section (staleness detection)                  │
│     └── PROPOSED SPEC section                                       │
│                                                                     │
│  5. COMP Concern Generation                                         │
│     └── If BLOCKER concerns → ALIGNMENT MODE                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
skills/adversarial-spec/scripts/
├── integrations/
│   ├── git_cli.py          # All git command execution and parsing
│   └── process_runner.py   # Controlled command execution, timeout, redaction
├── collectors/
│   ├── git_position.py     # Build GitPosition from git integration
│   └── system_state.py     # Build SystemState from process runner
├── extractors/
│   └── spec_affected_files.py  # Parse spec text into repo file paths
└── pre_gauntlet/
    ├── context_builder.py  # Build LLM context markdown
    ├── alignment_mode.py   # Interactive and non-interactive alignment flow
    └── orchestrator.py     # Entry point for gauntlet integration
```

---

## CLI Interface

### Command

```bash
python3 gauntlet.py --spec <path> --doc-type <prd|tech|debug> --pre-gauntlet [--report-path <path>]
```

### Exit Codes

| Code | Status | Meaning |
|------|--------|---------|
| 0 | COMPLETE | No blockers, gauntlet can proceed |
| 2 | NEEDS_ALIGNMENT | Alignment mode triggered, user action required |
| 3 | ABORTED | User chose to quit |
| 4 | CONFIG_ERROR | Invalid configuration in pyproject.toml |
| 5 | INFRA_ERROR | Git or filesystem access failed |

---

## Data Models

All models use Pydantic for validation.

### Configuration

```python
class DocTypeRule(BaseModel):
    enabled: bool = True
    require_git: bool = True
    require_build: bool = True
    require_schema: bool = False
    require_trees: bool = False

class CompatibilityConfig(BaseModel):
    enabled: bool = True
    base_branch: str = "main"
    build_command: list[str] | None = None  # e.g., ["npm", "run", "type-check"]
    build_timeout_seconds: int = Field(default=60, ge=5, le=300)
    schema_files: list[str] = []
    critical_paths: list[str] = []
    include_untracked: bool = False
    file_max_bytes: int = Field(default=200_000, le=2_000_000)
    tree_max_depth: int = Field(default=6, le=8)
    tree_max_entries: int = Field(default=5000, le=20_000)
    context_max_chars: int = Field(default=200_000, le=250_000)
    staleness_threshold_days: int = Field(default=3, ge=1, le=30)
    doc_type_rules: dict[str, DocTypeRule] = {}
```

### Git Position

```python
class CommitSummary(BaseModel):
    hash: str
    author: str
    date: datetime
    subject: str

class FileChange(BaseModel):
    path: str
    status: Literal["A", "M", "D", "R"]  # Added, Modified, Deleted, Renamed

class GitPosition(BaseModel):
    current_branch: str
    head_commit: str
    base_branch: str
    base_commit: str
    merge_base_commit: str
    commits_ahead: int
    commits_behind: int
    last_sync_with_base: datetime
    main_recent_commits: list[CommitSummary]  # last 10 on base branch
    affected_files_changes: list[FileChange]  # spec-relevant files changed
    working_tree_clean: bool
    detached_head: bool = False
```

### System State

```python
class FileSnapshot(BaseModel):
    path: str
    sha256: str
    content: str
    truncated: bool = False

class DirectoryTree(BaseModel):
    path: str
    tree: str
    truncated: bool = False

class SystemState(BaseModel):
    build_status: Literal["PASS", "FAIL", "TIMEOUT", "SKIP"]
    build_exit_code: int | None = None
    build_duration_ms: int = 0
    build_output_excerpt: str = ""  # Redacted, truncated
    schema_contents: list[FileSnapshot] = []
    directory_trees: list[DirectoryTree] = []
    working_tree_clean: bool = True
    collection_timestamp: datetime
```

### Concerns

```python
class EvidenceRef(BaseModel):
    type: Literal["COMMAND_OUTPUT", "FILE_CONTENT", "GIT_LOG"]
    source: str
    excerpt: str  # Redacted

class Concern(BaseModel):
    id: str  # Format: COMP-{hash8}
    severity: Literal["BLOCKER", "WARN", "INFO"]
    category: Literal["GIT", "BUILD", "SCHEMA", "CONFIG", "CONTEXT", "DOC_TYPE"]
    title: str
    message: str
    evidence_refs: list[EvidenceRef] = []

class AlignmentIssue(BaseModel):
    concern_id: str
    status: Literal["UNRESOLVED", "RESOLVED", "OVERRIDDEN"]
    resolution: Literal["FIX_CODE", "UPDATE_SPEC", "IGNORE"] | None = None
```

### Result

```python
class PreGauntletResult(BaseModel):
    status: Literal["COMPLETE", "NEEDS_ALIGNMENT", "ABORTED", "CONFIG_ERROR", "INFRA_ERROR"]
    doc_type: Literal["prd", "tech", "debug"]
    concerns: list[Concern] = []
    alignment_issues: list[AlignmentIssue] = []
    git_position: GitPosition | None = None
    system_state: SystemState | None = None
    context_summary: dict = {}  # context_chars, truncated_sections
    timings_ms: dict = {}  # git, build, files, total
```

---

## Component 1: Git Position Collector

**Purpose:** Detect if the codebase advanced while we were working on the spec.

### Git Commands (via integration module, READ-ONLY)

```bash
git rev-parse --abbrev-ref HEAD          # current branch or "HEAD" for detached
git rev-parse HEAD                        # head_commit
git rev-parse <base_branch>               # base_commit (error on missing)
git merge-base HEAD <base_branch>         # merge_base_commit
git rev-list --left-right --count <base_branch>...HEAD  # commits_behind, commits_ahead
git log -n 10 --format=%H|%ad|%an|%s <base_branch>      # main_recent_commits
git diff --name-status <base_branch>...HEAD             # changed_files
git status --porcelain                    # working_tree_clean
```

### Concern Generation

| Condition | Concern ID Pattern | Severity | Action |
|-----------|-------------------|----------|--------|
| `commits_behind > 0` | `GIT_STALE` | WARN | "Main has N new commits" |
| `affected_files_changes` not empty | `GIT_AFFECTED_FILES_CHANGED` | BLOCKER | ALIGNMENT MODE |
| `last_sync_with_base` > threshold | `GIT_STALE_TIME` | WARN | "Consider rebasing" |
| Detached HEAD | `GIT_DETACHED` | WARN | Include in report |

### When to Run

| Stage | Git Check | Purpose |
|-------|-----------|---------|
| Before gauntlet | Full collection | Establish baseline |
| Before implementation | Delta since last check | Detect drift during gauntlet |
| Before each phase | Quick check (commits_behind only) | Continuous awareness |

---

## Component 2: System State Collector

**Purpose:** Gather actual codebase state for LLM context injection.

### Build Command Execution

- **Security:** `shell=False` with argument array only
- **Validation:** Reject commands containing `;`, `&&`, `|`, or newlines
- **Timeout:** Configurable, default 60s, max 300s
- **Output:** Redacted with configurable patterns + high-entropy token detector

### Concern Generation

| Condition | Concern ID Pattern | Severity |
|-----------|-------------------|----------|
| Build fails (exit != 0) | `BASELINE_BUILD_FAILURE` | BLOCKER |
| Build timeout | `BASELINE_BUILD_FAILURE` | BLOCKER |
| Missing required schema file | `SCHEMA_MISSING` | BLOCKER |

---

## Component 3: Spec Affected Files Extractor

**Purpose:** Parse spec text for file path references to determine which codebase changes are relevant.

### Algorithm

1. Build file index: `git ls-files` (+ `--others --exclude-standard` if `include_untracked=true`)
2. Parse spec for path-like tokens: `(?<!https?://)[A-Za-z0-9_./-]+\.[A-Za-z0-9]+`
3. Keep tokens matching file index or `critical_paths` prefixes
4. Cap to `max_matches`, deterministic order

---

## Component 4: Context Injection Format

The LLM prompt receives a structured context section with fixed order:

```markdown
# SYSTEM CONTEXT (GROUND TRUTH)

Trust this section over any assumptions. If the spec contradicts this, raise a COMP concern.

## 1. Git Position
- Branch: feature/order-execution (12 commits ahead, 3 behind main)
- Head: abc123def456
- Last sync with main: 2026-01-22 (2 days ago)
- Working tree: CLEAN
- WARNING: Main has 3 new commits since this branch diverged:
  - abc1234: "refactor: split matchPairs metadata" (affects convex/schema.ts)
  - def5678: "fix: worker lifecycle cleanup" (affects convex/workers.ts)

## 2. Baseline Health
- Build Status: FAIL
- Exit Code: 1
- Duration: 24000ms
- Output (redacted):
  ```
  Schema validation failed.
  Document with ID "***REDACTED***" in table "matchPairs"
  does not match the schema: Object contains extra field `matchConfidence`
  ```

## 3. Schema Snapshots
### convex/schema.ts (sha256: abc123...)
[...file contents, truncated if needed...]

## 4. Directory Trees
### convex/
[...tree output, truncated if needed...]

## 5. Proposed Spec
[...spec text...]
```

### Truncation Order (when context exceeds limit)

1. Build output
2. Tree output
3. Schema content
4. Spec text (last resort)

---

## Component 5: Alignment Mode

When a BLOCKER concern is accepted, the system enters **Alignment Mode**.

### State Machine

```
                    ┌─────────────────┐
                    │  PRE_GAUNTLET   │
                    │   (running)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ BLOCKER concern │
                    │   detected?     │
                    └────────┬────────┘
                             │ YES
                    ┌────────▼────────┐
                    │ ALIGNMENT_MODE  │
                    │   (blocking)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       [f] Fix Code    [u] Update Spec   [i] Ignore
              │              │              │
              ▼              ▼              ▼
        Re-run build   Edit spec file   Force proceed
        Re-collect     Re-start check   (requires exact
        state                           confirmation token)
              │              │              │
              └──────────────┴──────────────┘
                             │
                    ┌────────▼────────┐
                    │  Continue or    │
                    │  Exit gauntlet  │
                    └─────────────────┘
```

### CLI Interaction (Interactive TTY)

```
ALIGNMENT MODE: Drift detected between spec and codebase

The following issues require resolution before proceeding:

  COMP-a1b2c3d4: Baseline Build Fails [BLOCKER]
  The build command `npm run type-check` fails with schema validation errors.
  This blocks ALL implementation work.

  COMP-e5f6g7h8: Affected Files Changed on Main [BLOCKER]
  Main has 3 new commits since this branch diverged. Commit abc1234 modifies
  convex/schema.ts which the spec references. The spec may be based on stale
  understanding.

Options:
  [f] Fix codebase - Pause gauntlet, fix the issues, then re-check
  [u] Update spec  - Edit the spec to match current codebase state
  [i] Ignore       - Force proceed (DANGEROUS - requires confirmation)
  [q] Quit         - Exit gauntlet without proceeding

Choice [f/u/i/q]:
```

### Ignore Confirmation

Requires exact token: `I KNOW THIS WILL BREAK`

Records `alignment_override=true` in report.

### Non-Interactive Mode

When stdin is not a TTY, returns `NEEDS_ALIGNMENT` status with no prompt.

---

## Configuration (`pyproject.toml`)

```toml
[tool.adversarial-spec.compatibility]
enabled = true
base_branch = "main"
build_command = ["npm", "run", "type-check"]
build_timeout_seconds = 60
schema_files = ["convex/schema.ts", "prisma/schema.prisma"]
critical_paths = ["convex/", "src/api/"]
include_untracked = false
file_max_bytes = 200000
tree_max_depth = 6
tree_max_entries = 5000
context_max_chars = 200000
staleness_threshold_days = 3

[tool.adversarial-spec.compatibility.doc_type_rules.prd]
enabled = false
require_git = false
require_build = false
require_schema = false
require_trees = false

[tool.adversarial-spec.compatibility.doc_type_rules.tech]
enabled = true
require_git = true
require_build = true
require_schema = true
require_trees = true

[tool.adversarial-spec.compatibility.doc_type_rules.debug]
enabled = true
require_git = true
require_build = true
require_schema = false
require_trees = false
```

---

## Document Type Variations

### PRD (Product Requirements Document)

**Codebase Coupling:** Low - PRDs describe what to build, not how.

| Check | Default | Rationale |
|-------|---------|-----------|
| Git Position | Disabled | May be greenfield project |
| Build Command | Disabled | No code to build yet |
| Schema Files | Disabled | No implementation exists |
| Pattern Consistency | Disabled | No patterns to match |

**When PRD needs alignment mode:**
- If PRD references existing features that have changed
- If PRD assumptions conflict with existing architecture docs

### Tech Spec (Technical Specification)

**Codebase Coupling:** High - Tech specs must integrate with existing code.

| Check | Default | Rationale |
|-------|---------|-----------|
| Git Position | Enabled | Spec must be based on current codebase |
| Build Command | Enabled | Baseline must be deployable |
| Schema Files | Enabled | Proposed schema must not conflict |
| Pattern Consistency | Enabled | Must follow existing conventions |

**This is the primary use case for pre-gauntlet.**

### Debug Investigation

**Codebase Coupling:** Critical - Debug specs investigate existing bugs.

| Check | Default | Rationale |
|-------|---------|-----------|
| Git Position | Enabled | Must know exactly which code version has the bug |
| Build Command | Enabled | Must verify baseline to isolate bug |
| Schema Files | Depends | If bug involves data layer |
| Pattern Consistency | Disabled | Focused on fixing, not conventions |

**Special Debug Checks:**

1. **Symptom Verification** - Can we reproduce the symptom RIGHT NOW?
2. **Code Version Pinning** - Record exact commit hash where bug was observed
3. **Evidence Freshness** - Are logs/errors current? (>24h = stale)

---

## Security Considerations

1. **Command Execution**
   - `shell=False` with argument arrays only
   - Reject commands containing `;`, `&&`, `|`, or newlines
   - Run only from project root

2. **Output Redaction**
   - High-entropy token detector for secrets
   - Configurable redaction patterns
   - Environment variables never logged

3. **File Access**
   - Limited to configured paths only
   - Reject `.env`, credentials files
   - Report files omit secret values

---

## Error Handling

| Condition | Exit Code | Behavior |
|-----------|-----------|----------|
| Missing base branch | 5 (INFRA_ERROR) | Block gauntlet |
| Git command failure | 5 (INFRA_ERROR) | Block gauntlet |
| Detached HEAD | 0 (with WARN) | Continue with concern |
| Missing config keys | 4 (CONFIG_ERROR) | Block gauntlet |
| Missing schema file | 0 (with BLOCKER) | Alignment mode |
| Build timeout | 0 (with BLOCKER) | Alignment mode |
| Non-TTY alignment | 2 (NEEDS_ALIGNMENT) | Return without prompt |

---

## Performance Requirements

| Component | Target | Maximum |
|-----------|--------|---------|
| Total pre-gauntlet | 60s | 90s |
| Git collector | 3s | 5s |
| Build command | 30s | configurable (max 300s) |
| File collection | 5s | 10s |
| Context size | 150k chars | 250k chars |

---

## Testing Strategy

1. **Unit Tests**
   - Config validation
   - Git output parsing
   - Redaction logic

2. **Integration Tests**
   - Temp git repo with ahead/behind scenarios
   - File change detection
   - Build command execution

3. **Edge Case Tests**
   - Detached HEAD
   - Missing base branch
   - Build timeout (with sleep command)
   - Non-interactive mode (stdin closed)

---

## Implementation Plan

### Phase 1: Core Infrastructure
1. `integrations/git_cli.py` - Git command wrapper
2. `integrations/process_runner.py` - Safe command execution
3. `collectors/git_position.py` - GitPosition builder
4. `collectors/system_state.py` - SystemState builder

### Phase 2: Extraction and Context
1. `extractors/spec_affected_files.py` - Spec parser
2. `pre_gauntlet/context_builder.py` - Markdown builder

### Phase 3: Alignment Mode
1. `pre_gauntlet/alignment_mode.py` - Interactive flow
2. `pre_gauntlet/orchestrator.py` - Entry point

### Phase 4: Integration
1. Update `gauntlet.py` to call orchestrator
2. Add `--pre-gauntlet` flag
3. Write report to `.adversarial-spec/pre_gauntlet_report.json`

---

## Success Criteria

1. Pre-existing build failures are caught BEFORE gauntlet runs
2. Schema/data drift is detected and surfaced
3. Spec staleness (main advanced) triggers alignment mode
4. User can choose to fix code, update spec, or force proceed
5. All COMP concerns link back to specific evidence (command output, file contents)
6. Non-interactive mode returns appropriate exit code for CI/CD
