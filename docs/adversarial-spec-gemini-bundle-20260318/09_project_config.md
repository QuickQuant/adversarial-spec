<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: pyproject.toml (80 lines, 2149 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "adversarial-spec"
version = "1.0.0"
description = "Multi-model adversarial debate for spec refinement"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Zak Cole", email = "zcole@linux.com"}
]
keywords = ["llm", "specification", "debate", "adversarial", "critique"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Quality Assurance",
]
dependencies = [
    "litellm==1.80.13",
    "mcp>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest==8.4.2",
    "pytest-cov==7.0.0",
    "ruff==0.14.11",
    "mypy==1.19.1",
    "types-requests==2.32.4.20260107",
    "pre-commit==4.0.1",
]

[project.scripts]
adversarial-spec = "adversarial_spec.debate:main"
mcp-tasks = "mcp_tasks.server:mcp.run"

[project.urls]
Homepage = "https://github.com/zscole/adversarial-spec"
Repository = "https://github.com/zscole/adversarial-spec"
Issues = "https://github.com/zscole/adversarial-spec/issues"

[tool.setuptools.packages.find]
where = ["."]
include = ["adversarial_spec*", "execution_planner*", "mcp_tasks*"]

[tool.setuptools.package-data]
"*" = ["py.typed"]

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N"]
ignore = [
    "UP007",  # Don't convert Optional[X] to X | None (requires Python 3.10+)
    "E501",   # Line too long (docstrings and help text benefit from longer lines)
]

[tool.mypy]
python_version = "3.10"
warn_return_any = false
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["skills/adversarial-spec/scripts/tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --strict-markers"


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/pyproject.toml (16 lines, 364 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "adversarial-spec-skill"
version = "1.0.0"
description = "Adversarial spec skill for Claude Code"
requires-python = ">=3.10"
dependencies = [
    "litellm>=1.50.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["scripts*", "execution_planner*"]


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: CLAUDE.md (110 lines, 4206 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# CLAUDE.md
<!-- Base: Brainquarters v1.5 | Project: v1.0 | Last synced: 2026-03-13 -->
<!-- Last reviewed: 2026-03-13 | Next review: 2026-04-03 -->
<!-- Target: 60-100 lines | If >100 lines, prune or move to .active_context.md -->

## WHAT: Project & Stack

**adversarial-spec** - Claude Code skill for iterative spec development through multi-model debate.

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.14+ |
| Dependencies | uv, pyproject.toml |
| Tests | pytest |
| Lint | ruff |

**Key paths:**
- `skills/adversarial-spec/` - Skill definition (phases, scripts, reference)
- `~/.claude/skills/adversarial-spec/` - Deployed skill (what Claude Code uses)
- `adversarial-spec-process-failure-report.md` - Process lessons learned

## WHY: Purpose

1. **Iterative refinement** - Generate specs through adversarial debate with multiple LLMs
2. **User story anchoring** - Ensure specs are grounded in user needs (being improved)
3. **Consensus-driven** - Continue debate until all models agree
4. **Process documentation** - Capture lessons learned for continuous improvement

## HOW: Working in This Codebase

### Session Start
```
/tasks              # Check pending improvements (#94-97)
```

### Commands
```bash
uv run pytest                            # Test
uvx ruff check --fix --unsafe-fixes      # Lint
```

### Resuming Work
```
/tasks                    # See work streams and pending tasks
/tasks <context>          # See tasks for specific work stream
```

### Deployment
Changes to `skills/adversarial-spec/` need manual copy to `~/.claude/skills/`:
```bash
cp -r skills/adversarial-spec/* ~/.claude/skills/adversarial-spec/
```

### Current Focus
Process improvements from failure report:
- Task #94: Fix 03-debate.md to USE user stories (high)
- Task #95: Enhance opponent prompts (high)
- Task #96: Require Bootstrap section (medium)
- Task #97: Structure debate rounds (low)

## Guardrails

**Hooks enforce safety** - see `.claude/hooks/`.

Critical rules (enforced by hooks):
- Never log/print API keys or config objects containing secrets
- Never use `git push --force`, `git reset --hard`, `rm -rf`
- Always use `uv run` for Python commands
- **Before exploring a codebase, read `.architecture/INDEX.md` first.** Do not glob/grep for orientation when architecture docs exist.

Token discipline (see `core-practices.md` §8 for rationale):
- Hook blocks a command → switch tools immediately. Do NOT read hook source to diagnose.
- Codex calls → always `timeout=900000`+ and `run_in_background`. Hook enforces minimums.
- `TaskOutput(block=true)` returns full result — never re-read the same output file.
- Background tasks → check `block=false` at ~45s before committing to a blocking wait.
- Failure patterns (rate limits, wrong defaults) → record in MEMORY.md same session.
- Background notification for already-consumed task → reply "Already processed." (one line).

## Progressive Disclosure

**This file is minimal by design.** Load context on-demand:

| Need | Action |
|------|--------|
| Process lessons | Read `adversarial-spec-process-failure-report.md` |
| Skill phases | Read `skills/adversarial-spec/phases/` |
| Project patterns | Read `onboarding/project-practices.md` |
| Universal rules | Read `onboarding/core-practices.md` |

---

## Review Trigger

**`/checkpoint` check:** If `Next review` date has passed:
1. Verify this file still matches actual workflows
2. Check line count (target: 60-100, max: 100)
3. Update `Last reviewed` and `Next review` (+ 21 days)
4. Sync AGENTS.md (identical content)

## Debugging Rules
- REPRODUCE the bug first. Do not jump to fixes.
- Read the ENTIRE error message and stack trace before forming a hypothesis.
- Write a failing test that captures the bug before attempting a fix.
- Do NOT propose speculative fixes. No "maybe", "possibly", "could be".
- If root cause isn't proven, produce a diagnostic plan, not a patch.
- Apply the minimal fix — touch as few files as possible.
- After fixing, run the failing test again to confirm it passes.
- Never rewrite large sections of code to fix a bug. If you feel the urge, you don't understand the root cause yet.

<!-- Line count: ~105 -->


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: README.md (1012 lines, 41548 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# adversarial-spec

A Claude Code plugin that iteratively refines product specifications through multi-model debate until consensus is reached.

**Key insight:** A single LLM reviewing a spec will miss things. Multiple LLMs debating a spec will catch gaps, challenge assumptions, and surface edge cases that any one model would overlook. The result is a document that has survived rigorous adversarial review.

**Claude is an active participant**, not just an orchestrator. Claude provides independent critiques, challenges opponent models, and contributes substantive improvements alongside external models.

## Quick Start

```bash
# 1. Add the marketplace and install the plugin
claude plugin marketplace add zscole/adversarial-spec
claude plugin install adversarial-spec

# 2. Set at least one API key
export OPENAI_API_KEY="sk-..."
# Or use OpenRouter for access to multiple providers with one key
export OPENROUTER_API_KEY="sk-or-..."

# 3. Run it
/adversarial-spec "Build a rate limiter service with Redis backend"
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  1. You describe product (or provide existing doc)              │
│                            ↓                                    │
│  2. Claude drafts spec + Q&A with you                           │
│                            ↓                                    │
│  3. COLLABORATIVE REFINEMENT: You + multiple LLMs improve spec  │
│     • GPT, Gemini, Grok suggest improvements in parallel        │
│     • Claude asks YOU about product decisions                   │
│     • Claude synthesizes feedback + adds own improvements       │
│     • Repeat until ALL models agree spec is ready               │
│                            ↓                                    │
│  4. PRE-GAUNTLET: Codebase compatibility check                  │
│     • existing_system_compatibility verifies build, schema,     │
│       naming conflicts before stress testing                    │
│                            ↓                                    │
│  5. THE GAUNTLET: 8 adversary personas attack the agreed spec   │
│     • paranoid_security finds threats everywhere                │
│     • burned_oncall asks "what happens at 3am?"                 │
│     • lazy_developer says "this is too complicated"             │
│     • pedantic_nitpicker asks about leap seconds                │
│     • asshole_loner points out your design is broken            │
│     • prior_art_scout finds existing code to reuse              │
│     • assumption_auditor demands "where's the citation?"        │
│     • information_flow_auditor audits every arrow in diagrams   │
│                            ↓                                    │
│  6. Frontier model evaluates each concern                       │
│     Adversaries can rebut if dismissed too easily               │
│                            ↓                                    │
│  7. Address accepted concerns (back to step 3 if major changes) │
│                            ↓                                    │
│  8. FINAL BOSS: ux_architect asks "did we lose the forest?"     │
│     Issues PASS / REFINE / RECONSIDER verdict                   │
│                            ↓                                    │
│  9. User review: accept, request changes, or run another cycle  │
│                            ↓                                    │
│  10. Final document output                                      │
│                            ↓                                    │
│  11. Generate execution plan with tasks linked to concerns      │
│                            ↓                                    │
│  12. Track all work via MCP Tasks (cross-project visibility)    │
└─────────────────────────────────────────────────────────────────┘
```

First you and multiple LLMs collaborate until everyone agrees the spec is solid. *Then* the gauntlet stress-tests it with adversary personas who are paid to find problems. You address those concerns, get final boss approval, and end up with an execution plan that links tasks back to the concerns that drove them.

## Task-Driven Workflow

Every adversarial-spec session is tracked via MCP Tasks—replicating the same task system used by Claude Code's built-in CLI task tools (`TaskCreate`, `TaskList`, `TaskGet`, `TaskUpdate`).

> **Note:** This MCP-based approach is a stopgap until Anthropic adds native task support to VSCode Claude Code. The API matches the canonical CLI tools exactly, so switching to official support will be seamless.

Tasks are created automatically as work progresses:

```
Phase 1: Requirements Gathering    → TaskCreate for each step
Phase 2: Adversarial Debate        → Round tasks added dynamically
Phase 3: Gauntlet                  → Adversary attack tasks
Phase 4: Finalization              → Quality checks
Phase 5: PRD → Tech Spec           → Continuation tasks
Phase 6: Execution Planning        → Planning tasks with concern IDs
Phase 7: Implementation            → Tasks linked to gauntlet concerns
```

**Concern ID linking:** Implementation tasks include `concern_ids` in metadata (e.g., `BURN-abc123`, `PARA-def456`) linking directly to the gauntlet concerns they address. This creates full traceability from adversary critique → task → implementation.

**Cross-project visibility:** When you invoke `/adversarial-spec` from another project, tasks are stored in *that project's* `.claude/tasks.json`. Use `TaskList` to see progress at any time.

**No setup required.** The MCP Tasks server auto-detects the project root by walking up from your working directory looking for `.git`, `.claude`, `pyproject.toml`, or `package.json`.

## Pre-Gauntlet Compatibility Checks

Before the adversarial gauntlet runs, an optional **pre-gauntlet phase** verifies that your spec is grounded in the actual codebase state. This catches issues like:

- Build baseline is broken (can't deploy current code)
- Schema/data drift exists
- Spec is designed against stale codebase understanding
- Naming conflicts with existing code

```bash
# Run gauntlet with pre-gauntlet checks
cat spec.md | python -m gauntlet --pre-gauntlet --doc-type tech

# Or read spec from file
python -m gauntlet --pre-gauntlet --doc-type tech --spec-file spec.md
```

### Why Pre-Gauntlet?

During implementation of a spec that passed the full gauntlet (179 concerns), we discovered the codebase itself was not deployable due to pre-existing schema/data drift. None of the 5 adversarial LLMs caught this because they reviewed the spec in isolation.

The pre-gauntlet ensures your spec is grounded in reality before adversaries start debating it.

### What It Checks

| Check | Tech Spec | PRD | Debug |
|-------|-----------|-----|-------|
| Git position (branch staleness) | Yes | No | Yes |
| Build command (baseline health) | Yes | No | Yes |
| Schema files (conflicts) | Yes | No | Depends |
| Directory trees (patterns) | Yes | No | No |

### Alignment Mode

When blockers are detected (build fails, spec-affected files changed on main), the system enters **Alignment Mode**:

```
ALIGNMENT MODE: Drift detected between spec and codebase

The following issues require resolution before proceeding:

  COMP-a1b2c3d4: Baseline Build Fails [BLOCKER]
  The build command `npm run type-check` fails with schema validation errors.

Options:
  [f] Fix codebase - Pause gauntlet, fix the issues, then re-check
  [u] Update spec  - Edit the spec to match current codebase state
  [i] Ignore       - Force proceed (DANGEROUS - requires confirmation)
  [q] Quit         - Exit gauntlet without proceeding
```

### Configuration

Configure pre-gauntlet in `pyproject.toml`:

```toml
[tool.adversarial-spec.compatibility]
enabled = true
base_branch = "main"
build_command = ["npm", "run", "type-check"]
build_timeout_seconds = 60
schema_files = ["prisma/schema.prisma", "convex/schema.ts"]
critical_paths = ["src/api/", "convex/"]
staleness_threshold_days = 3

# Validation commands for schema/data consistency checks
# IMPORTANT: Always specify 'environment' to avoid false positives from wrong instance
[[tool.adversarial-spec.compatibility.validation_commands]]
name = "convex"
command = ["npx", "convex", "dev", "--once"]
timeout_seconds = 90
description = "Validates Convex schema against production data"
environment = "production"  # CRITICAL: specify which instance is being validated

[[tool.adversarial-spec.compatibility.validation_commands]]
name = "prisma"
command = ["npx", "prisma", "validate"]
timeout_seconds = 30
description = "Validates Prisma schema syntax and relations"
environment = "production"

[tool.adversarial-spec.compatibility.doc_type_rules.tech]
enabled = true
require_git = true
require_build = true
require_schema = true
require_validation = true
```

### Validation Commands

Validation commands are separate from the build command and specifically check for schema/data consistency:

| Framework | Example Command | What It Catches |
|-----------|-----------------|-----------------|
| Convex | `npx convex dev --once` | Schema vs production data drift |
| Prisma | `npx prisma validate` | Schema syntax and relation errors |
| TypeORM | `npm run typeorm schema:log` | Entity vs database drift |
| Drizzle | `npx drizzle-kit check` | Schema vs database drift |

When a validation command fails, it generates a **BLOCKER** concern that triggers Alignment Mode.

### Environment Awareness

**CRITICAL:** Always specify the `environment` field for validation commands.

```toml
[[tool.adversarial-spec.compatibility.validation_commands]]
name = "convex"
command = ["npx", "convex", "dev", "--once"]
environment = "production"  # or "development", "staging"
```

Why this matters:
- Validation commands often check against a specific database instance
- Running against development when production is the target causes **false positives**
- The pre-gauntlet displays environment prominently in output to prevent confusion
- Missing environment triggers a warning: `[ENV: UNKNOWN]`

Example output:
```
### Validation Checks

⚠️ **WARNING: Some validations have no environment specified.**
Verify these are running against the correct instance (production vs development).

- **convex** [production]: ✅ PASS
- **prisma** [ENV: UNKNOWN]: ❌ FAIL  ← Which instance failed?
```

### Exit Codes

| Code | Status | Meaning |
|------|--------|---------|
| 0 | COMPLETE | No blockers, gauntlet proceeds |
| 2 | NEEDS_ALIGNMENT | Blockers detected, user action required |
| 3 | ABORTED | User quit |
| 4 | CONFIG_ERROR | Invalid pyproject.toml |
| 5 | INFRA_ERROR | Git/filesystem failure |

## External Documentation Lookup (Context7)

Before the debate begins, the **Discovery Agent** scans your spec for external services and fetches their official documentation via Context7. This grounds the debate in reality rather than letting models pattern-match from training data.

```bash
# Discovery runs automatically when Context7 MCP tools are available
# No additional configuration needed
```

### What It Does

1. **Service extraction**: Scans spec text for SDK patterns (`@polymarket/clob-client`), API mentions, and known service names
2. **Documentation fetch**: Uses Context7 to retrieve official docs for discovered services
3. **Priming context**: Injects fetched documentation into the debate context

### Why This Matters

AI models share training data, which means they share false assumptions about external systems. The classic failure mode:

> All models assumed "crypto trading = on-chain transactions" when Polymarket's CLOB is actually off-chain with SDK-handled signing.

By fetching actual documentation first, models debate based on ground truth rather than pattern-matched assumptions.

### Caching

Documentation is cached locally to avoid redundant fetches:

- **Location**: `~/.cache/adversarial-spec/knowledge/`
- **TTL**: 24 hours (configurable)
- **Format**: Gzip-compressed JSON

### Token Limits

The system uses **soft token limits** with tracking:

```python
# Default: 2000 tokens per query
# Violations are logged but not blocked
"Soft token limit exceeded: 3500 > 2000 (library=/polymarket/clob-client)"
```

This allows review of whether limits need adjustment without blocking operations.

### Integration with Adversaries

The `assumption_auditor` adversary uses the evidence log to verify claims:

```
CLAIM: "Polymarket requires nonces for order submission"
STATUS: PENDING
EVIDENCE: [Context7 docs showing SDK handles signing internally]
```

When documentation contradicts a claim, it's flagged before models build elaborate concerns on false premises.

### API Interface Verification (Constructive Phase)

When defining interfaces for external APIs, models must verify against authoritative sources - not pattern-match.

**Example Failure:**
```typescript
// WHAT 3 FRONTIER MODELS AGREED ON (WRONG):
interface KalshiOrder { filled_count: number; }  // ❌ API uses "fill_count"
```

**Solution: Check SDK type definitions first.**
```bash
grep "fill_count" node_modules/kalshi-typescript/dist/models/order.d.ts
# → 'fill_count': number;  ✓
```

SDK `.d.ts` files are auto-generated from OpenAPI specs - authoritative, local, grepable.

See SKILL.md Step 2.6 for full guidance.

## The Adversarial Gauntlet

The gauntlet is where specs go to get stress-tested by personas who are *paid to find problems*.

```bash
# Run the gauntlet on any spec
cat spec.md | python3 debate.py gauntlet

# Pick your adversaries
cat spec.md | python3 debate.py gauntlet --gauntlet-adversaries paranoid_security,burned_oncall

# Include the gauntlet in a full debate
cat spec.md | python3 debate.py critique --models codex/gpt-5.2-codex --gauntlet
```

### The Adversaries

**Pre-Gauntlet (codebase verification):**

| Persona | What They Do | Why They're Annoying (In a Good Way) |
|---------|--------------|--------------------------------------|
| `existing_system_compatibility` | Verifies spec is grounded in actual codebase state. Checks build baseline, schema drift, naming conflicts, pattern consistency. | Catches when specs are designed against stale understanding. Triggers ALIGNMENT MODE when drift is found. |

**Main Gauntlet (spec attack):**

| Persona | What They Do | Why They're Annoying (In a Good Way) |
|---------|--------------|--------------------------------------|
| `paranoid_security` | Sees threats everywhere. Every input is malicious. Every dependency will be compromised. | Occasionally catches what everyone else missed because they weren't paranoid *enough*. |
| `burned_oncall` | Has been paged at 3am too many times. Obsessed with failure modes. "What happens when Redis goes down?" | Doesn't trust anything to stay up. Has seen too much. |
| `lazy_developer` | "This is too complicated. Why can't we just use X?" | Not lazy whining - engineering judgment. Dismissals must prove the simpler approach fails. |
| `pedantic_nitpicker` | What if the string is empty? What about 2^31 items? Leap seconds? Unicode? | Most concerns don't matter. Some really do. |
| `asshole_loner` | Brilliant antisocial engineer who jumps to conclusions. Blunt. Accepts good reasoning without argument. | Trusts logic, not authority. If you can prove it, they'll shut up. |
| `prior_art_scout` | Thinks in patterns. Finds similar concepts in the codebase and proposes implementations that blend with existing abstractions. | Suggests architecture improvements: "This looks like BaseClient - extend it instead of building standalone." |
| `assumption_auditor` | Challenges domain premises, not just logic. "How do we KNOW this is how it works?" Demands documentation citations. | Catches when all models share the same false assumption about an external system. |
| `information_flow_auditor` | Audits every arrow in architecture diagrams. "What mechanism does 'Result' represent?" | Catches unspecified flows that default to polling when push is available. |

**Final Boss (holistic review):**

| Persona | What They Do | Why They're Annoying (In a Good Way) |
|---------|--------------|--------------------------------------|
| `ux_architect` | Senior UX engineer asking "Did we lose the forest for the trees?" Reviews user story, experience delta, measurement strategy. | Issues PASS/REFINE/RECONSIDER verdict. Can send spec back for re-architecture if concerns suggest fundamental issues. |

### The Final Boss

After all technical concerns are addressed and models agree, the **UX Architect** (running on Opus 4.5) asks: *"Did we lose the forest for the trees?"*

```bash
# Enable the final boss review
cat spec.md | python3 debate.py gauntlet --final-boss
```

The Final Boss issues one of three verdicts:

| Verdict | Meaning |
|---------|---------|
| **PASS** | User story is sound, concerns are normal refinements. Proceed to implementation. |
| **REFINE** | Specific concerns need addressing, but the approach is correct. Address them, then proceed. |
| **RECONSIDER** | Too many fundamental issues or unexplored alternate approaches. Models should debate re-architecture. |

When **RECONSIDER** is issued:
1. The Final Boss explains why the current approach is problematic
2. Lists alternate approaches that should have been explored (often from `prior_art_scout` or `information_flow_auditor`)
3. Models debate: keep current approach with justification, or re-architect
4. If re-architecture occurs, the gauntlet runs again on the new spec

This catches cases where adversaries raised dozens of valid concerns that could have been avoided with a different approach - like when 62 concerns about error handling would disappear if the spec used an existing SDK instead of building from scratch.

### Adversary Leaderboard

Track which adversaries are actually useful over time:

```bash
python3 debate.py adversary-stats
```

Shows signal score (acceptance rate vs dismissal effort), rebuttal success rates, and which personas consistently find real issues vs which ones cry wolf.

### Known Limitations

**The gauntlet has blind spots.** When all AI models share the same training data, they share similar false assumptions about external systems.

**What the gauntlet catches well:**
- Logic errors and inconsistencies
- Missing edge cases
- Security vulnerabilities
- Operational gaps

**What the gauntlet can miss:**
- Shared false assumptions about external APIs ("crypto = on-chain transactions")
- Domain knowledge gaps common to all models
- Sophisticated reasoning built on false premises

**Mitigation:** The `assumption_auditor` adversary explicitly challenges domain premises and demands documentation citations. However, human verification of external system assumptions is still valuable - a single "I've used this system" can invalidate hours of AI spec work.

**Rule of thumb:** For external system integrations, cite official documentation or confirm with someone who has used the system.

### Concern IDs

Every concern gets a stable ID like `BURN-a3f7c912` (burned_oncall concern, content hash). These IDs let execution plans reference specific concerns that need to be addressed during implementation.

## Execution Plans

Turn a converged spec into an actionable implementation plan:

```bash
# Generate from spec
python3 debate.py execution-plan --spec-file spec.md

# Include gauntlet concerns for richer context
python3 debate.py execution-plan --spec-file spec.md --concerns-file gauntlet-concerns.json

# Output formats
python3 debate.py execution-plan --spec-file spec.md --plan-format markdown
python3 debate.py execution-plan --spec-file spec.md --plan-format summary
```

Execution plans include:
- **Phases** with clear milestones
- **Tasks** with dependencies and validation strategies
- **Concern links** connecting tasks to gauntlet concerns they address
- **Parallelization analysis** for multi-agent execution

## Requirements

- Python 3.10+
- `litellm` package: `pip install litellm`
- API key for at least one LLM provider

## Supported Models

**CLI tools are FREE and frontier-quality** - use these first:

| Tool       | Requirement            | Models                                       |
|------------|------------------------|----------------------------------------------|
| Codex CLI  | ChatGPT Plus/Pro       | `codex/gpt-5.2-codex`, `codex/gpt-5.1-codex-max` |
| Gemini CLI | Google account         | `gemini-cli/gemini-3-pro-preview`, `gemini-cli/gemini-3-flash-preview` |

**API providers** (pay-per-token fallback):

| Provider   | Env Var                | Example Models                               |
|------------|------------------------|----------------------------------------------|
| OpenAI     | `OPENAI_API_KEY`       | `gpt-5.2`, `o3-mini`, `gpt-5.2-mini`         |
| Anthropic  | `ANTHROPIC_API_KEY`    | `claude-opus-4-5-20251124`, `claude-sonnet-4-5-20250929` |
| Google     | `GEMINI_API_KEY`       | `gemini/gemini-3-pro`, `gemini/gemini-3-flash` |
| xAI        | `XAI_API_KEY`          | `xai/grok-4`, `xai/grok-4.1-fast`            |
| Mistral    | `MISTRAL_API_KEY`      | `mistral/mistral-large-3`, `mistral/mistral-medium-3` |
| Groq       | `GROQ_API_KEY`         | `groq/llama-4-maverick`, `groq/llama-3.3-70b-versatile` |
| DeepSeek   | `DEEPSEEK_API_KEY`     | `deepseek/deepseek-r1`, `deepseek/deepseek-v3.2-exp` |
| OpenRouter | `OPENROUTER_API_KEY`   | `openrouter/openai/gpt-5.2`, `openrouter/anthropic/claude-sonnet-4.5` |
| Zhipu      | `ZHIPUAI_API_KEY`      | `zhipu/glm-4`, `zhipu/glm-4-plus`            |

Check which keys are configured:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py providers
```

## AWS Bedrock Support

For enterprise users who need to route all model calls through AWS Bedrock (e.g., for security compliance or inference gateway requirements):

```bash
# Enable Bedrock mode
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock enable --region us-east-1

# Add models enabled in your Bedrock account
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock add-model claude-3-sonnet
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock add-model claude-3-haiku

# Check configuration
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock status

# Disable Bedrock mode
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock disable
```

When Bedrock is enabled, **all model calls route through Bedrock** - no direct API calls are made. Use friendly names like `claude-3-sonnet` which are automatically mapped to Bedrock model IDs.

Configuration is stored at `~/.claude/adversarial-spec/config.json`.

## OpenRouter Support

[OpenRouter](https://openrouter.ai) provides unified access to multiple LLM providers through a single API. This is useful for:
- Accessing models from multiple providers with one API key
- Comparing models across different providers
- Automatic fallback and load balancing
- Cost optimization across providers

**Setup:**

```bash
# Get your API key from https://openrouter.ai/keys
export OPENROUTER_API_KEY="sk-or-..."

# Use OpenRouter models (prefix with openrouter/)
python3 debate.py critique --models openrouter/openai/gpt-5.2,openrouter/anthropic/claude-sonnet-4.5 < spec.md
```

**Popular OpenRouter models:**
- `openrouter/openai/gpt-5.2` - GPT-5.2 via OpenRouter
- `openrouter/anthropic/claude-sonnet-4.5` - Claude Sonnet 4.5
- `openrouter/google/gemini-3-pro` - Gemini 3 Pro
- `openrouter/meta-llama/llama-4-maverick` - Llama 4 Maverick
- `openrouter/deepseek/deepseek-r1` - DeepSeek R1

See the full model list at [openrouter.ai/models](https://openrouter.ai/models).

## Codex CLI Support

[Codex CLI](https://github.com/openai/codex) allows ChatGPT Pro subscribers to use OpenAI models without separate API credits. Models prefixed with `codex/` are routed through the Codex CLI.

**Setup:**

```bash
# Install Codex CLI (requires ChatGPT Pro subscription)
npm install -g @openai/codex

# Use Codex models (prefix with codex/)
python3 debate.py critique --models codex/gpt-5.2-codex,gemini-cli/gemini-3-flash-preview < spec.md
```

**Reasoning effort:**

Control how much thinking time the model uses with `--codex-reasoning`:

```bash
# Available levels: low, medium, high, xhigh (default: xhigh)
python3 debate.py critique --models codex/gpt-5.2-codex --codex-reasoning high < spec.md
```

Higher reasoning effort produces more thorough analysis but uses more tokens.

**Available Codex models:**
- `codex/gpt-5.2-codex` - GPT-5.2 via Codex CLI
- `codex/gpt-5.1-codex-max` - GPT-5.1 Max via Codex CLI

Check Codex CLI installation status:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py providers
```

## Gemini CLI Support

[Gemini CLI](https://github.com/google-gemini/gemini-cli) allows Google account holders to use Gemini models without separate API credits. Models prefixed with `gemini-cli/` are routed through the Gemini CLI.

**Setup:**

```bash
# Install Gemini CLI
npm install -g @google/gemini-cli && gemini auth

# Use Gemini CLI models (prefix with gemini-cli/)
python3 debate.py critique --models gemini-cli/gemini-3-pro-preview < spec.md
```

**Available Gemini CLI models:**
- `gemini-cli/gemini-3-pro-preview` - Gemini 3 Pro via CLI
- `gemini-cli/gemini-3-flash-preview` - Gemini 3 Flash via CLI

Check Gemini CLI installation status:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py providers
```

## OpenAI-Compatible Endpoints

For models that expose an OpenAI-compatible API (local LLMs, self-hosted models, alternative providers), set `OPENAI_API_BASE`:

```bash
# Point to a custom endpoint
export OPENAI_API_KEY="your-key"
export OPENAI_API_BASE="https://your-endpoint.com/v1"

# Use with any model name
python3 debate.py critique --models codex/gpt-5.2-codex < spec.md
```

This works with:
- Local LLM servers (Ollama, vLLM, text-generation-webui)
- OpenAI-compatible providers
- Self-hosted inference endpoints

## Usage

**Start from scratch:**

```
/adversarial-spec "Build a rate limiter service with Redis backend"
```

**Refine an existing document:**

```
/adversarial-spec ./docs/my-spec.md
```

You will be prompted for:

1. **Document type**: PRD (business/product focus) or tech spec (engineering focus)
2. **Interview mode**: Optional in-depth requirements gathering session
3. **Opponent models**: Comma-separated list (e.g., `codex/gpt-5.2-codex,gemini-cli/gemini-3-pro-preview`)

More models = more perspectives = stricter convergence.

## Document Types

### PRD (Product Requirements Document)

For stakeholders, PMs, and designers.

**Sections:** Executive Summary, Problem Statement, Target Users/Personas, User Stories, Functional Requirements, Non-Functional Requirements, Success Metrics, Scope (In/Out), Dependencies, Risks

**Critique focuses on:** Clear problem definition, well-defined personas, measurable success criteria, explicit scope boundaries, no technical implementation details

### Technical Specification

For developers and architects.

**Sections:** Overview, Goals/Non-Goals, System Architecture, Component Design, API Design (full schemas), Data Models, Infrastructure, Security, Error Handling, Performance/SLAs, Observability, Testing Strategy, Deployment Strategy

**Critique focuses on:** Complete API contracts, data model coverage, security threat mitigation, error handling, specific performance targets, no ambiguity for engineers

## Core Features

### Interview Mode

Before the debate begins, opt into an in-depth interview session to capture requirements upfront.

**Covers:** Problem context, users/stakeholders, functional requirements, technical constraints, UI/UX, tradeoffs, risks, success criteria

The interview uses probing follow-up questions and challenges assumptions. After completion, Claude synthesizes answers into a complete spec before starting the adversarial debate.

### Claude's Active Participation

Each round, Claude:

1. Reviews opponent critiques for validity
2. Provides independent critique (what did opponents miss?)
3. States agreement/disagreement with specific points
4. Synthesizes all feedback into revisions

Display format:

```
--- Round N ---
Opponent Models:
- [GPT-4o]: critiqued: missing rate limit config
- [Gemini]: agreed

Claude's Critique:
Security section lacks input validation strategy. Adding OWASP top 10 coverage.

Synthesis:
- Accepted from GPT-4o: rate limit configuration
- Added by Claude: input validation, OWASP coverage
- Rejected: none
```

### Early Agreement Verification

If a model agrees within the first 2 rounds, Claude is skeptical. The model is pressed to:

- Confirm it read the entire document
- List specific sections reviewed
- Explain why it agrees
- Identify any remaining concerns

This prevents false convergence from models that rubber-stamp without thorough review.

### User Review Period

After all models agree, you enter a review period with three options:

1. **Accept as-is**: Document is complete
2. **Request changes**: Claude updates the spec, you iterate without a full debate cycle
3. **Run another cycle**: Send the updated spec through another adversarial debate

### Additional Review Cycles

Run multiple cycles with different strategies:

- First cycle with fast models (gemini-cli/gemini-3-flash-preview), second with frontier (codex/gpt-5.2-codex)
- First cycle for structure/completeness, second for security focus
- Fresh perspective after user-requested changes

### PRD to Tech Spec Flow

When a PRD reaches consensus, you're offered the option to continue directly into a Technical Specification based on the PRD. This creates a complete documentation pair in a single session.

## Advanced Features

### Critique Focus Modes

Direct models to prioritize specific concerns:

```bash
--focus security      # Auth, input validation, encryption, vulnerabilities
--focus scalability   # Horizontal scaling, sharding, caching, capacity
--focus performance   # Latency targets, throughput, query optimization
--focus ux            # User journeys, error states, accessibility
--focus reliability   # Failure modes, circuit breakers, disaster recovery
--focus cost          # Infrastructure costs, resource efficiency
```

### Model Personas

Have models critique from specific professional perspectives:

```bash
--persona security-engineer      # Thinks like an attacker
--persona oncall-engineer        # Cares about debugging at 3am
--persona junior-developer       # Flags ambiguity and tribal knowledge
--persona qa-engineer            # Missing test scenarios
--persona site-reliability       # Deployment, monitoring, incidents
--persona product-manager        # User value, success metrics
--persona data-engineer          # Data models, ETL implications
--persona mobile-developer       # API design for mobile
--persona accessibility-specialist  # WCAG, screen readers
--persona legal-compliance       # GDPR, CCPA, regulatory
```

Custom personas also work: `--persona "fintech compliance officer"`

### Context Injection

Include existing documents for models to consider:

```bash
--context ./existing-api.md --context ./schema.sql
```

Use cases:
- Existing API documentation the new spec must integrate with
- Database schemas the spec must work with
- Design documents or prior specs for consistency
- Compliance requirements documents

### Session Persistence and Resume

Long debates can crash or need to pause. Sessions save state automatically:

```bash
# Start a named session
echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --session my-feature-spec

# Resume where you left off
python3 debate.py critique --resume my-feature-spec

# List all sessions
python3 debate.py sessions
```

Sessions save:
- Current spec state
- Round number
- All configuration (models, focus, persona, etc.)
- History of previous rounds

Sessions are stored in `~/.config/adversarial-spec/sessions/`.

### Auto-Checkpointing

When using sessions, each round's spec is saved to `.adversarial-spec-checkpoints/`:

```
.adversarial-spec-checkpoints/
├── my-feature-spec-round-1.md
├── my-feature-spec-round-2.md
└── my-feature-spec-round-3.md
```

Use these to rollback if a revision makes things worse.

### Preserve Intent Mode

Convergence can sand off novel ideas when models interpret "unusual" as "wrong". The `--preserve-intent` flag makes removal expensive:

```bash
--preserve-intent
```

When enabled, models must:

1. **Quote exactly** what they want to remove or substantially change
2. **Justify the harm** - not just "unnecessary" but what concrete problem it causes
3. **Distinguish error from preference** - only remove things that are factually wrong, contradictory, or risky
4. **Ask before removing** unusual but functional choices: "Was this intentional?"

This shifts the default from "sand off anything unusual" to "add protective detail while preserving distinctive choices."

Use when:
- Your spec contains intentional unconventional choices
- You want models to challenge your ideas, not homogenize them
- Previous rounds removed things you wanted to keep

### Cost Tracking

Every critique round displays token usage and estimated cost:

```
=== Cost Summary ===
Total tokens: 12,543 in / 3,221 out
Total cost: $0.0847

By model:
  codex/gpt-5.2-codex: $0.00 (8,234 in / 2,100 out)  # FREE with subscription
  gemini-cli/gemini-3-pro-preview: $0.00 (4,309 in / 1,121 out)  # FREE
```

### Saved Profiles

Save frequently used configurations:

```bash
# Create a profile
python3 debate.py save-profile strict-security \
  --models codex/gpt-5.2-codex,gemini-cli/gemini-3-pro-preview \
  --focus security \
  --doc-type tech

# Use a profile
python3 debate.py critique --profile strict-security < spec.md

# List profiles
python3 debate.py profiles
```

Profiles are stored in `~/.config/adversarial-spec/profiles/`.

### Diff Between Rounds

See exactly what changed between spec versions:

```bash
python3 debate.py diff --previous round1.md --current round2.md
```

### Export to Task List

Extract actionable tasks from a finalized spec:

```bash
cat spec-output.md | python3 debate.py export-tasks --models codex/gpt-5.2-codex --doc-type prd
```

Output includes title, type, priority, description, and acceptance criteria.

Use `--json` for structured output suitable for importing into issue trackers.

## Telegram Integration (Optional)

Get notified on your phone and inject feedback during the debate.

**Setup:**

1. Message @BotFather on Telegram, send `/newbot`, follow prompts
2. Copy the bot token
3. Run: `python3 ~/.claude/skills/adversarial-spec/scripts/telegram_bot.py setup`
4. Message your bot, run setup again to get your chat ID
5. Set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
```

**Features:**

- Async notifications when rounds complete (includes cost)
- 60-second window to reply with feedback (incorporated into next round)
- Final document sent to Telegram when debate concludes

## Output

Final document is:

- Complete, following full structure for document type
- Vetted by all models until unanimous agreement
- Ready for stakeholders without further editing

Output locations:

- Printed to terminal
- Written to `spec-output.md` (PRD) or `tech-spec-output.md` (tech spec)
- Sent to Telegram (if enabled)

Debate summary includes rounds completed, cycles run, models involved, Claude's contributions, cost, and key refinements made.

## CLI Reference

```bash
# Core commands
debate.py critique --models MODEL_LIST --doc-type TYPE [OPTIONS] < spec.md
debate.py critique --resume SESSION_ID
debate.py diff --previous OLD.md --current NEW.md
debate.py export-tasks --models MODEL --doc-type TYPE [--json] < spec.md

# Gauntlet commands (with optional pre-gauntlet)
gauntlet.py --pre-gauntlet --doc-type tech < spec.md            # Pre-gauntlet + gauntlet
gauntlet.py --pre-gauntlet --spec-file spec.md                  # Read spec from file
gauntlet.py --pre-gauntlet --report-path report.json < spec.md  # Custom report path
debate.py gauntlet < spec.md                                    # Run full gauntlet (no pre-gauntlet)
debate.py gauntlet --gauntlet-adversaries paranoid_security,burned_oncall < spec.md
debate.py gauntlet --final-boss < spec.md                       # Include UX architect review
debate.py gauntlet-adversaries                                  # List adversary personas
debate.py adversary-stats                                       # Show adversary leaderboard

# Execution planning
debate.py execution-plan --spec-file spec.md                    # Generate implementation plan
debate.py execution-plan --spec-file spec.md --concerns-file concerns.json
debate.py execution-plan --plan-format markdown --plan-output plan.md

# Info commands
debate.py providers      # List providers and API key status
debate.py focus-areas    # List focus areas
debate.py personas       # List personas
debate.py profiles       # List saved profiles
debate.py sessions       # List saved sessions

# Profile management
debate.py save-profile NAME --models ... [--focus ...] [--persona ...]

# Bedrock management
debate.py bedrock status                      # Show Bedrock configuration
debate.py bedrock enable --region REGION      # Enable Bedrock mode
debate.py bedrock disable                     # Disable Bedrock mode
debate.py bedrock add-model MODEL             # Add model to available list
debate.py bedrock remove-model MODEL          # Remove model from list
debate.py bedrock list-models                 # List built-in model mappings
```

**Options:**
- `--models, -m` - Comma-separated model list (auto-detects from available API keys if not specified)
- `--doc-type, -d` - prd, tech, or debug
- `--codex-reasoning` - Reasoning effort for Codex models (low, medium, high, xhigh; default: xhigh)
- `--focus, -f` - Focus area (security, scalability, performance, ux, reliability, cost)
- `--persona` - Professional persona
- `--context, -c` - Context file (repeatable)
- `--preserve-intent` - Require justification for removals
- `--session, -s` - Session ID for persistence and checkpointing
- `--resume` - Resume a previous session
- `--gauntlet, -g` - Run adversarial gauntlet
- `--gauntlet-adversaries` - Specific adversaries to use
- `--gauntlet-model` - Model for adversary attacks
- `--gauntlet-frontier` - Model for evaluation
- `--final-boss` - Enable UX architect review
- `--pre-gauntlet` - Run pre-gauntlet compatibility checks before gauntlet
- `--spec-file` - Read spec from file instead of stdin
- `--report-path` - Path to save pre-gauntlet report JSON
- `--press, -p` - Anti-laziness check
- `--telegram, -t` - Enable Telegram
- `--json, -j` - JSON output

## File Structure

```
adversarial-spec/
├── .claude-plugin/
│   └── plugin.json               # Plugin metadata
├── README.md
├── LICENSE
├── execution_planner/            # Spec → Implementation planning
│   ├── spec_intake.py            # Parse specs into structured data
│   ├── task_planner.py           # Generate phased task plans
│   ├── gauntlet_concerns.py      # Link concerns to plan tasks
│   └── ...
├── mcp_tasks/                    # MCP Task Management Server
│   ├── server.py                 # TaskCreate/List/Get/Update tools
│   └── __init__.py
└── skills/
    └── adversarial-spec/
        ├── SKILL.md              # Skill definition and process
        └── scripts/
            ├── adversaries.py    # Centralized adversary personas
            ├── debate.py         # Multi-model debate orchestration
            ├── gauntlet.py       # Adversarial gauntlet engine
            ├── providers.py      # API key detection
            ├── task_manager.py   # Python API for task coordination
            ├── telegram_bot.py   # Telegram notifications
            ├── integrations/     # External system integrations
            │   ├── git_cli.py    # Git command wrapper (read-only)
            │   ├── process_runner.py  # Safe command execution
            │   └── knowledge_service.py  # Context7 integration with caching
            ├── collectors/       # Data collectors for pre-gauntlet
            │   ├── git_position.py    # Branch/commit status
            │   └── system_state.py    # Build status, schema files
            ├── extractors/       # Spec analysis
            │   └── spec_affected_files.py  # File path extraction
            └── pre_gauntlet/     # Pre-gauntlet compatibility checks
                ├── models.py     # Pydantic data models
                ├── discovery.py  # Pre-debate service discovery & doc fetch
                ├── context_builder.py  # LLM context generation
                ├── alignment_mode.py   # Interactive alignment flow
                └── orchestrator.py     # Main entry point
```

## License

MIT


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: CONTRIBUTING.md (81 lines, 1725 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Contributing to Adversarial Spec

## Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd adversarial-spec

# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## Code Quality

All code must pass:

```bash
# Lint
ruff check skills/adversarial-spec/scripts/

# Format
ruff format skills/adversarial-spec/scripts/

# Type check
mypy skills/adversarial-spec/scripts/ --ignore-missing-imports

# Tests with coverage
cd skills/adversarial-spec/scripts
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=90
```

Pre-commit hooks run these automatically on staged files.

## Code Standards

- Type hints on all functions
- Google-style docstrings with Args, Returns, Raises sections
- No silent exception handling (log or re-raise)
- Input validation for security-sensitive operations
- Test coverage minimum: 90%

## Testing

Tests live in `skills/adversarial-spec/scripts/tests/`. Structure mirrors the source.

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_models.py -v

# Run with coverage report
python -m pytest tests/ --cov=. --cov-report=html
```

## Pull Request Process

1. Create feature branch from main
2. Write tests for new functionality
3. Ensure all checks pass locally
4. Submit PR with clear description
5. Address review feedback

## Commit Messages

Format: `<type>: <description>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Build, CI, dependency updates

Example: `feat: add bedrock integration for enterprise deployments`


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: CHANGELOG.md (106 lines, 5428 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **Adversarial Gauntlet System** (`gauntlet.py`) - Multi-phase adversarial review pipeline
  - 5 adversary personas: paranoid_security, burned_oncall, lazy_developer, pedantic_nitpicker, asshole_loner
  - Multi-model consensus evaluation (2-3 models vote, majority wins, ties favor acceptance)
  - Self-filtering against resolved concerns database (prevents repeated concerns)
  - Rebuttal phase where adversaries can challenge dismissals
  - Final Boss UX Architect review (Phase 5) - uses Opus 4.5 for user story validation
  - Confidence decay model for cached explanations (age decay, spec change penalty, usage boost)
  - Per-adversary performance tracking (signal score, acceptance rate, dismissal effort)
  - CLI commands: `gauntlet`, `gauntlet-adversaries`, `adversary-stats`

- **Scope Management System** (`scope.py`) - Detect and manage scope expansion during refinement
  - ScopeDiscovery dataclass for tracking tangential features and scope expansions
  - Mini-spec template generation for discovered features
  - Heuristic keyword detection for scope implications
  - User checkpoints for scope decisions (stub, expand, defer, reject)
  - Persistence of scope reports and mini-specs

- **Gemini CLI Integration** - Free Google Gemini access via CLI tool
  - Models: `gemini-cli/gemini-3-pro-preview`, `gemini-cli/gemini-3-flash-preview`
  - No API key needed - uses Google account authentication
  - Install: `npm install -g @google/gemini-cli && gemini auth`

- **Free-First Model Selection** - Prioritizes free CLI tools over paid APIs
  - Codex CLI (ChatGPT subscription) and Gemini CLI checked first
  - Falls back to API models only when CLI tools unavailable

- Gauntlet CLI arguments: `--gauntlet`, `--gauntlet-adversaries`, `--gauntlet-model`, `--gauntlet-frontier`, `--no-rebuttals`, `--final-boss`
- Adversary response protocols with valid/invalid dismissal criteria
- Cost-weighted signal score metric for adversary effectiveness

### Fixed

- Replaced hardcoded `gpt-4o` default model with dynamic detection based on available API keys
- Added pre-flight validation to check that models have required API keys before running critique
- Added clear error messages when API keys are missing, showing which key is needed for each model
- Fixed model selection to prioritize available providers in order: Bedrock, OpenAI, Anthropic, Google, xAI, etc.
- Added documentation for resolving Claude Code auth conflicts (claude.ai token vs ANTHROPIC_API_KEY)
- Updated documentation to include Anthropic provider in supported models table

### Changed

- `--models` argument now auto-detects default model from available API keys instead of assuming `gpt-4o`
- Script now fails fast with helpful error messages if no API keys are configured
- Profile loading now correctly handles the new dynamic default model selection

### Added

- New `get_available_providers()` function to detect configured API keys
- New `get_default_model()` function to select appropriate default based on available keys
- New `validate_model_credentials()` function to pre-validate model API key requirements
- Comprehensive test coverage for new validation functions (11 new tests, 297 total)

## [1.0.0] - 2025-01-11

### Added

- Multi-model adversarial debate for spec refinement
- Support for multiple LLM providers via LiteLLM:
  - OpenAI (gpt-4o, gpt-4-turbo, o1)
  - Google (gemini/gemini-2.0-flash, gemini/gemini-pro)
  - xAI (xai/grok-3, xai/grok-beta)
  - Mistral (mistral/mistral-large, mistral/codestral)
  - Groq (groq/llama-3.3-70b-versatile)
  - Deepseek (deepseek/deepseek-chat)
  - Zhipu (zhipu/glm-4, zhipu/glm-4-plus)
- Codex CLI integration for ChatGPT subscription models
- AWS Bedrock integration for enterprise users
- OpenAI-compatible endpoint support for local/self-hosted models
- Document types: PRD (product) and Tech Spec (engineering)
- Interview mode for in-depth requirements gathering
- Claude's active participation in debates alongside opponent models
- Early agreement verification to prevent rubber-stamping
- User review period with change request workflow
- PRD to Tech Spec flow for complete documentation
- Critique focus modes: security, scalability, performance, ux, reliability, cost
- Professional personas: security-engineer, oncall-engineer, junior-developer, qa-engineer, etc.
- Context injection for existing documents
- Session persistence and resume functionality
- Auto-checkpointing for rollback capability
- Preserve intent mode requiring justification for removals
- Cost tracking with per-model breakdown
- Saved profiles for frequently used configurations
- Diff between spec versions
- Export to task list (with JSON output option)
- Telegram integration for async notifications and human-in-the-loop feedback
- Retry with exponential backoff for API resilience
- Response validation warnings for malformed outputs

### Technical

- Modular codebase: debate.py, models.py, providers.py, session.py, prompts.py, telegram_bot.py
- Full type hints with py.typed marker
- Google-style docstrings
- Input validation for security-sensitive operations
- Structured logging for exception handling
- Unit tests with pytest (194 tests, 91% coverage)
- CI workflow with linting (ruff), type checking (mypy), tests with coverage threshold
- Pre-commit hooks for code quality


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .github/workflows/ci.yml (97 lines, 2730 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install ruff
        run: pip install ruff

      - name: Run ruff check
        run: ruff check skills/adversarial-spec/scripts/

      - name: Run ruff format check
        run: ruff format --check skills/adversarial-spec/scripts/

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install mypy litellm types-requests

      - name: Run mypy
        run: mypy --explicit-package-bases skills/adversarial-spec/scripts/*.py --ignore-missing-imports --no-error-summary

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install pytest pytest-cov litellm

      - name: Run tests with coverage
        working-directory: skills/adversarial-spec/scripts
        run: python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=90

  validate-manifests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate plugin.json
        run: python -c "import json; json.load(open('.claude-plugin/plugin.json'))"

      - name: Validate marketplace.json
        run: python -c "import json; json.load(open('.claude-plugin/marketplace.json'))"

      - name: Check plugin.json required fields
        run: |
          python -c "
          import json
          data = json.load(open('.claude-plugin/plugin.json'))
          required = ['name', 'version', 'description']
          for field in required:
              assert field in data, f'Missing required field: {field}'
          print('plugin.json validation passed')
          "

      - name: Check marketplace.json required fields
        run: |
          python -c "
          import json
          data = json.load(open('.claude-plugin/marketplace.json'))
          assert 'name' in data, 'Missing name'
          assert 'plugins' in data, 'Missing plugins'
          assert len(data['plugins']) > 0, 'No plugins defined'
          print('marketplace.json validation passed')
          "


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: adversarial-spec-process-failure-report.md (361 lines, 12134 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Adversarial-Spec Process Failure Report

**Session:** Targeted Documentation Lookup Protocol
**Date:** 2026-01-27
**Rounds Completed:** 3
**Critical Gap Identified:** User stories and use cases were never defined

---

## Executive Summary

The adversarial-spec session for the Targeted Documentation Lookup Protocol ran 3 full debate rounds with two frontier models (Gemini 3 Pro, GPT-5.2 Codex) without ever establishing clear user stories or validating requirements with the user. The resulting spec is technically detailed but missed fundamental workflow questions until the user explicitly asked: "Is there a defined sequence of steps for how we will bootstrap the initial indexing?"

This represents a systemic failure in the adversarial-spec process itself.

---

## What Went Wrong

### 1. No User Stories Before Debate

The spec jumped directly into technical architecture without defining WHO would use this system and WHAT they're trying to accomplish. The following user stories should have been defined BEFORE Round 1:

**Missing User Stories:**

```
US-1: Developer Bootstrapping New API
  AS A developer starting a new project against an API (e.g., Kalshi)
  I WANT TO quickly set up documentation lookup for that API
  SO THAT I can get targeted, token-efficient answers about API endpoints

US-2: LLM Agent Using Documentation
  AS AN LLM agent (Claude Code) working on code
  I WANT TO query API documentation with minimal token overhead
  SO THAT I can implement features without wasting context on bulk docs

US-3: Adversarial-Spec Using Documentation
  AS THE adversarial-spec skill validating external API interfaces
  I WANT TO fetch and verify API documentation during spec development
  SO THAT specs don't contain invented/incorrect API contracts

US-4: Developer Refreshing Stale Documentation
  AS A developer whose local docs are outdated
  I WANT TO refresh documentation from upstream
  SO THAT I'm working against current API contracts

US-5: Developer Switching Projects
  AS A developer switching between projects (Kalshi → Polymarket → unrelated)
  I WANT TO enable/disable documentation sources per project
  SO THAT I don't pay token overhead for irrelevant docs
```

### 2. No User Q&A After Round 1

Round 1 should have included a checkpoint asking the user:

- "What's your primary use case for this tool?"
- "How do you expect to bootstrap documentation initially?"
- "What's your workflow when starting a new API integration?"
- "Do you need this to work without Context7 available?"

Instead, Round 1 went straight into technical critiques about:
- Data model insufficiency (TypeSchema)
- Markdown parsing strategies
- Search ranking algorithms
- CLI output optimization

These are valid concerns, but they're implementation details disconnected from user goals.

### 3. Bootstrap Workflow Was an Afterthought

The bootstrap workflow—arguably the most important user-facing feature—was:
- Not mentioned in the original spec
- Not raised by either opponent model in 3 rounds
- Only addressed when the user explicitly asked

**Timeline:**
| Round | Focus | Bootstrap Mentioned? |
|-------|-------|---------------------|
| 1 | Data models, parsing strategies | No |
| 2 | Registry patterns, ID generation | No |
| 3 | Search algorithms, token pre-calc | No |
| Post-debate | User asks | Finally addressed |

### 4. Debate Optimized for Technical Correctness, Not User Value

Both opponent models (Gemini, Codex) critiqued:
- O(N) search algorithms
- Runtime token estimation overhead
- Dynamic import security risks
- ID collision handling

These are valid technical concerns. But neither asked:
- "How does a user actually get documentation into this system?"
- "What happens if Context7 isn't available?"
- "What's the happy path for a new user?"

The models were debating HOW to build a system without establishing WHAT the system should accomplish for users.

---

## Impact

### Spec Quality Issues

1. **Bootstrap workflow undefined for 3 rounds** - Added only after user intervention
2. **No acceptance criteria** - How do we know the spec is "done"?
3. **No user journey mapping** - Spec describes components, not experiences
4. **Technical debt in spec itself** - Rework required to add fundamental features

### Process Issues

1. **User forced to intervene** - User shouldn't need to ask "wait, how does setup work?"
2. **Wasted debate rounds** - 3 rounds on implementation before validating requirements
3. **False sense of completeness** - Spec appeared thorough but missed core workflows

---

## Root Cause Analysis

### Process Gap: Missing Requirements Phase

The adversarial-spec skill instructions include:

```
Phase 1: Requirements Gathering
- [ ] Determine document type (PRD/tech/debug)
- [ ] Identify starting point (existing file or new concept)
- [ ] Offer interview mode (PRD/tech only; debug skips interview)
- [ ] Conduct interview (if selected, PRD/tech only)
```

**However:**
- Interview mode was not offered
- User stories were not gathered
- The "interview topics" (Problem & Context, Users & Stakeholders, Functional Requirements) were skipped
- Debate started immediately after generating an initial draft

### Why This Happened

1. **Onboarding docs provided context** - The skill saw existing architecture docs and assumed requirements were known
2. **Tech spec bias** - Tech specs often skip user stories (incorrectly)
3. **Model behavior** - Opponent models critique what's in front of them, not what's missing
4. **No explicit checkpoint** - Process doesn't require user validation after Round 1

---

## Recommendations for Adversarial-Spec Process

### 1. MANDATORY User Stories Before Debate

Add to Phase 1 (before any debate rounds):

```markdown
## Phase 1.5: User Story Definition (REQUIRED)

Before generating the initial spec draft, define 3-5 user stories:

1. **Primary User Story**: The main use case this system serves
2. **Setup/Bootstrap Story**: How a new user gets started
3. **Daily Usage Story**: The common workflow after setup
4. **Edge Case Story**: What happens when things go wrong

Format:
  AS A [user type]
  I WANT TO [action]
  SO THAT [benefit]

These user stories become ACCEPTANCE CRITERIA for the spec.
Do not proceed to debate until user confirms these stories.
```

### 2. Round 1 Must Include User Validation

After Round 1 critiques, BEFORE applying changes:

```markdown
## Round 1 Checkpoint (REQUIRED)

Before synthesizing Round 1 feedback, ask the user:

1. "Based on opponent critiques, here are the main technical concerns: [list]
   Do any of these conflict with your priorities?"

2. "The spec currently assumes [X workflow]. Is this how you expect to use it?"

3. "Are there any user scenarios we haven't addressed?"

Do not proceed to Round 2 until user confirms direction.
```

### 3. Bootstrap/Setup Must Be Explicit Section

For any tool/system spec, require:

```markdown
## Getting Started (REQUIRED SECTION)

Every tech spec must include a "Getting Started" section that answers:

1. What does a new user need before they can use this?
2. What's the step-by-step first-run experience?
3. What happens if prerequisites aren't met?
4. How long until a user can perform their first real task?

This section should be written BEFORE implementation details.
```

### 4. Opponent Model Prompt Enhancement

Add to the critique prompt sent to opponent models:

```markdown
## Critique Requirements

In addition to technical review, you MUST address:

1. **User Journey**: Is there a clear path from "new user" to "productive user"?
2. **Setup/Bootstrap**: How does a user get started? Is this defined?
3. **Error Recovery**: What happens when things go wrong?
4. **Missing Use Cases**: What user scenarios are NOT addressed?

If the spec lacks user stories or a clear setup workflow, this is a CRITICAL gap
that must be raised before any implementation details are discussed.
```

### 5. Debate Round Focus Progression

Structure rounds with explicit focus:

```markdown
## Debate Round Structure

Round 1: REQUIREMENTS VALIDATION
- Are user stories complete?
- Is the setup/bootstrap workflow defined?
- Are acceptance criteria clear?
- USER CHECKPOINT before proceeding

Round 2: ARCHITECTURE & DESIGN
- Component design
- Data models
- API contracts

Round 3: IMPLEMENTATION DETAILS
- Algorithms
- Performance
- Security
- Error handling

Round 4+: REFINEMENT
- Edge cases
- Polish
```

---

## The User Stories That Should Have Been

Here are the user stories that should have driven this spec from the start:

### US-1: Developer Bootstrapping New API Documentation

```
AS A developer starting work on a Kalshi trading bot
I WANT TO set up targeted documentation lookup for Kalshi's API
SO THAT I can query specific endpoints without loading 400KB of docs

ACCEPTANCE CRITERIA:
- [ ] Can bootstrap from Context7 if available
- [ ] Can bootstrap from URL if Context7 unavailable
- [ ] Can bootstrap manually if neither available
- [ ] Setup takes < 5 minutes
- [ ] Clear error messages if something fails
- [ ] Can verify setup worked before disabling Context7
```

### US-2: LLM Agent Querying Documentation

```
AS Claude Code working on trading bot implementation
I WANT TO query "how to place an order on Kalshi"
SO THAT I get only the relevant endpoint info (~100 tokens) not bulk docs (~10K tokens)

ACCEPTANCE CRITERIA:
- [ ] Query returns < 500 tokens for typical questions
- [ ] Results are ranked by relevance
- [ ] Can request more detail if needed (graduated levels)
- [ ] Zero always-on token overhead (CLI-based)
- [ ] < 200ms latency for queries
```

### US-3: Adversarial-Spec Verifying API Interfaces

```
AS THE adversarial-spec skill writing a tech spec
I WANT TO verify that API interfaces in my spec match actual documentation
SO THAT I don't hallucinate field names or invent endpoints

ACCEPTANCE CRITERIA:
- [ ] Can fetch current documentation during spec development
- [ ] Can query specific endpoints to verify schemas
- [ ] Documentation source is cited in spec
- [ ] Warning if documentation couldn't be verified
```

### US-4: Developer Switching Projects

```
AS A developer who works on multiple trading projects
I WANT TO enable Kalshi docs for Project A, Polymarket for Project B
SO THAT each project only loads relevant documentation

ACCEPTANCE CRITERIA:
- [ ] Per-project MCP configuration
- [ ] Disabled sources have zero overhead
- [ ] Can quickly switch active sources
- [ ] Sources don't interfere with each other
```

### US-5: Developer Refreshing Documentation

```
AS A developer whose Kalshi integration broke after an API update
I WANT TO refresh my local documentation from upstream
SO THAT I'm working against the current API contract

ACCEPTANCE CRITERIA:
- [ ] Single command to refresh: `docmaster fetch kalshi`
- [ ] Automatic re-indexing after fetch
- [ ] Can rollback if new docs break something
- [ ] Notified if docs changed significantly
```

---

## Conclusion

The adversarial-spec process successfully produced a technically sound specification, but it failed to anchor that specification in user needs. Three rounds of debate with frontier models refined data models, search algorithms, and security considerations—but none of that matters if users can't figure out how to get started.

**Key Lesson:** Technical correctness is necessary but not sufficient. User stories and workflows must be defined BEFORE implementation details are debated.

**Recommended Action:** Update the adversarial-spec skill to:
1. Require user stories before debate
2. Add a mandatory user checkpoint after Round 1
3. Require a "Getting Started" section in all tech specs
4. Prompt opponent models to critique missing user journeys

---

## Appendix: Session Statistics

| Metric | Value |
|--------|-------|
| Total Rounds | 3 |
| Opponent Models | gemini-cli/gemini-3-pro-preview, codex/gpt-5.2-codex |
| User Checkpoints | 0 (should have been 1+) |
| User Stories Defined | 0 (should have been 3-5) |
| Bootstrap Workflow Defined | Round 4 (after user asked) |
| Lines of Spec Before Bootstrap Section | ~600 |
| Lines Added for Bootstrap | ~120 |


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: MODEL_REFERENCE.md (260 lines, 10592 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Model Reference for Adversarial Spec

**Last Updated:** February 2026

This file is the single source of truth for model references throughout the adversarial-spec skill. When new models are released, update this file first, then use the mappings to update examples in SKILL.md, debate.py, and specs.

## Architecture: Who Is Who?

**Claude (Opus) = The Orchestrator**
- Claude is running the adversarial-spec skill
- Claude is NOT called via API - it IS the coordinating agent
- Claude provides its own critiques alongside the opponent models

**Opponent Models = External Challengers**
- These are the models called via CLI/API to challenge the spec
- You want **strong** models here - weak opponents defeat the purpose
- CLI tools are ideal: **FREE + frontier quality**

**Haiku's role**: NOT for debate opponents. Haiku is only useful for Claude Code's internal quick tasks. In adversarial debate, you want the strongest challengers possible.

---

## IMPORTANT: CLI Tools = Free Frontier Models

**CLI tools give you frontier-quality models for FREE (part of subscriptions).**

Why pay for `deepseek/r1-distill` at $0.03/1M when `codex/gpt-5.3-codex` is **$0.00** AND better?

### Priority Order:
1. **CLI tools (free + frontier)**: Codex CLI, Gemini CLI
2. **API (if no subscriptions)**: Only as fallback

---

## CLI Tools (FREE - Subscription-Based)

### Codex CLI (ChatGPT Plus $20/mo or Pro $200/mo)

| Model | Default Reasoning | Notes |
|-------|-------------------|-------|
| `codex/gpt-5.3-codex` | **xhigh** | **NEW (Feb 2026)** 25% faster, 400k context, 128k output, mid-turn steering |
| `codex/gpt-5.2-codex` | xhigh | Previous frontier, still available |
| `codex/gpt-5.1-codex-max` | xhigh | Extended tasks (24+ hours) |
| `codex/gpt-5.1-codex-mini` | medium | Quick iterations (but why use weaker?) |

**Requires Codex CLI v0.98.0+** for gpt-5.3-codex. Update: `npm install -g @openai/codex@latest`

**Reasoning effort**: `--codex-reasoning` (minimal, low, medium, high, xhigh)
- Default for gpt-5.3-codex: **xhigh**
- OpenAI recommends "medium" as daily driver, "xhigh" for hard tasks
- For adversarial debate: **use xhigh** (we want rigorous critique)

### Gemini CLI (Free tier or Google AI Premium)

| Model | Use Case | Notes |
|-------|----------|-------|
| `gemini-cli/gemini-3-pro-preview` | **Best for debate** | Top LMArena (1501 Elo) |
| `gemini-cli/gemini-3-flash-preview` | Fast iteration | Pro-level at Flash speed |

**Free tier**: 60 requests/min, 1000/day with personal Google account

### Claude Code (Claude Pro $20/mo, Max $100-200/mo)

**Note**: Claude is the orchestrator, not an opponent. These models are for when YOU'RE running Claude Code, not for calling as debate opponents.

| Model | Notes |
|-------|-------|
| `claude-opus-4-6` | **Use this (Feb 2026)**. Latest Opus, most capable. |
| `claude-sonnet-4-5-20250929` | Good, but Opus is often same total cost due to efficiency |
| `claude-haiku-4-5-20251001` | NOT for debate. Only for quick internal tasks. |

**Economics**: Opus uses fewer tokens for the same prompt, so total cost is often on par with Sonnet. When in doubt, use Opus.

---

## API Models (Pay-Per-Token)

Only use these when CLI tools are unavailable.

## Model Tier Definitions

| Tier | Use Case | Characteristics |
|------|----------|-----------------|
| **Frontier** | Best quality, complex tasks | Highest capability, slower, most expensive |
| **Balanced** | Good quality/cost tradeoff | Near-frontier quality, moderate cost |
| **Fast** | Quick iterations, simple tasks | Lower latency, good for drafts |
| **Budget** | High volume, cost-sensitive | Cheapest, basic tasks |

---

## API Model Mappings (January 2026)

### OpenAI (API: `OPENAI_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `o1`, `gpt-4-turbo` | `gpt-5.2` | Best reasoning, $1.25/$10 per 1M tokens |
| Balanced | `gpt-4o` | `o3-mini` | Good reasoning at lower cost |
| Fast | `gpt-4o-mini` | `gpt-5.2-mini` | Fast, cheaper |
| Budget | - | `o4-mini` | Batch processing available |

### OpenAI Codex CLI (Subscription-based)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `codex/gpt-5.2-codex` | `codex/gpt-5.3-codex` | 25% faster, 400k ctx, 128k output |
| Balanced | `codex/o1-codex` | `codex/gpt-5.2-codex` | Still excellent |
| Extended | - | `codex/gpt-5.1-codex-max` | 24+ hour tasks |

### Anthropic (API: `ANTHROPIC_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `claude-opus-4-5-20251124` | `claude-opus-4-6` | Latest Opus, best for complex reasoning |
| Balanced | `claude-3.5-sonnet`, `claude-sonnet-4` | `claude-sonnet-4-5-20250929` | Best value, $3/$15 per 1M |
| Fast | `claude-3-sonnet` | `claude-haiku-4-5` | Near-frontier quality, fast |
| Budget | `claude-3-haiku` | `claude-haiku-4-5` | Same as fast tier now |

### Google Gemini (API: `GEMINI_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `gemini/gemini-pro` | `gemini/gemini-3-pro` | Top LMArena score (1501 Elo) |
| Balanced | `gemini/gemini-2.0-flash` | `gemini/gemini-2.5-pro` | Stable, long-context |
| Fast | `gemini/gemini-1.5-flash` | `gemini/gemini-3-flash` | 3x faster than 2.5 Pro, $0.50/$3 per 1M |
| Budget | - | `gemini/gemini-3-flash` | Same as fast (very cheap) |

### Google Gemini CLI (Subscription-based)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | - | `gemini-cli/gemini-3-pro-preview` | Full Gemini 3 Pro |
| Fast | - | `gemini-cli/gemini-3-flash-preview` | Fast iteration |

### xAI (API: `XAI_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `xai/grok-2`, `xai/grok-3` | `xai/grok-4` | Native tool use, real-time search |
| Balanced | `xai/grok-beta` | `xai/grok-4.1-fast` | Enterprise API |
| Fast | - | `xai/grok-3-mini-think` | Reasoning model |

### Mistral (API: `MISTRAL_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `mistral/mistral-large` | `mistral/mistral-large-3` | 675B MoE, Apache 2.0 |
| Balanced | `mistral/mistral-medium` | `mistral/mistral-medium-3` | $0.40/$2 per 1M |
| Fast | `mistral/mistral-small` | `mistral/mistral-small-3.1` | Efficient |
| Budget | `mistral/mistral-tiny` | `mistral/ministral-8b` | Edge/local use |

### Groq (API: `GROQ_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `groq/llama-3-70b` | `groq/llama-4-maverick` | 400B total params |
| Balanced | `groq/llama-3.3-70b-versatile` | `groq/llama-3.3-70b-versatile` | Still excellent |
| Fast | `groq/llama-3-8b` | `groq/llama-4-scout` | 460 tok/s, $0.11/$0.34 per 1M |
| Budget | - | `groq/llama-3.3-70b-specdec` | 1665 tok/s with spec decoding |

### DeepSeek (API: `DEEPSEEK_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | - | `deepseek/deepseek-r1` | o1-level reasoning, $0.70/$2.40 per 1M |
| Balanced | `deepseek/deepseek-chat` | `deepseek/deepseek-v3.2-exp` | $0.028/$0.32 per 1M (extremely cheap) |
| Fast | - | `deepseek/deepseek-v3.1` | $0.15/$0.75 per 1M |
| Budget | - | `deepseek/r1-distill-llama-70b` | $0.03/$0.11 per 1M |

### OpenRouter (API: `OPENROUTER_API_KEY`)

Routes to other providers. Update prefixes to match current models:

| Old Reference | Current Model |
|---------------|---------------|
| `openrouter/openai/gpt-4o` | `openrouter/openai/gpt-5.2` |
| `openrouter/anthropic/claude-3.5-sonnet` | `openrouter/anthropic/claude-sonnet-4.5` |

---

## Recommended Opponent Combinations for Debate

**Goal**: Get the strongest challengers possible. Weak opponents = weak specs.

### Best (FREE - CLI tools):
```bash
# Frontier models, zero cost
codex/gpt-5.3-codex,gemini-cli/gemini-3-pro-preview

# Add Flash for a third perspective (still free, still strong)
codex/gpt-5.3-codex,gemini-cli/gemini-3-pro-preview,gemini-cli/gemini-3-flash-preview
```

### If no subscriptions (API fallback):
```bash
# Best API value - still want strong models, not budget
deepseek/deepseek-r1,groq/llama-4-maverick

# NOT recommended: weak models like deepseek-v3.2-exp or groq/llama-4-scout
# Save money on volume tasks, not on quality critique
```

### DON'T use for debate:
- `codex/gpt-5.1-codex-mini` - weaker model, defeats purpose
- `claude-haiku-*` - not an opponent, and too weak anyway
- Any "budget" tier model - you want rigorous critique

---

## Example Replacements

When updating documentation, **use CLI tools** (free + frontier):

| Old (2024 model) | New (CLI - FREE + frontier) |
|------------------|----------------------------|
| `gpt-4o` | `codex/gpt-5.3-codex` |
| `gpt-4o,gemini/gemini-2.0-flash` | `codex/gpt-5.3-codex,gemini-cli/gemini-3-pro-preview` |
| `o1` | `codex/gpt-5.3-codex` (defaults to xhigh reasoning) |
| `gemini/gemini-2.0-flash` | `gemini-cli/gemini-3-flash-preview` |
| `gemini/gemini-pro` | `gemini-cli/gemini-3-pro-preview` |

**API fallback** (only if no subscriptions):

| Old | New (API - strong models) |
|-----|---------------------------|
| `gpt-4o` | `deepseek/deepseek-r1` or `groq/llama-4-maverick` |
| Multi-model | `deepseek/deepseek-r1,xai/grok-4` |

**Notes:**
- Don't recommend budget API models for debate - defeats the purpose
- CLI tools are both free AND frontier quality - no tradeoff
- Always show CLI examples first in docs

---

## Sources

- [OpenAI Pricing](https://openai.com/api/pricing/) - GPT-5.2, o3 series
- [Anthropic Claude](https://www.anthropic.com/claude/opus) - Opus 4.5, Sonnet 4.5, Haiku 4.5
- [Google Gemini](https://blog.google/products/gemini/gemini-3/) - Gemini 3 Pro/Flash
- [xAI Grok](https://x.ai/news) - Grok 4 series
- [Mistral AI](https://mistral.ai/pricing) - Large 3, Medium 3
- [Groq](https://groq.com/pricing) - Llama 4 on LPU
- [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing) - V3.2, R1

---

## Maintenance Notes

**When to update this file:**
1. New model releases from any provider
2. Model deprecations
3. Significant pricing changes
4. New providers added to litellm

**After updating this file:**
1. Update SKILL.md examples
2. Update debate.py docstring examples
3. Update providers.py model lists
4. Consider updating test fixtures (optional - tests use model names as fixtures)


