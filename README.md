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
│  2. Claude drafts spec                                          │
│                            ↓                                    │
│  3. THE GAUNTLET: 5 adversary personas attack                   │
│     • paranoid_security finds threats everywhere                │
│     • burned_oncall asks "what happens at 3am?"                 │
│     • lazy_developer says "this is too complicated"             │
│     • pedantic_nitpicker asks about leap seconds                │
│     • asshole_loner points out your design is broken            │
│                            ↓                                    │
│  4. Frontier model evaluates each concern                       │
│     Adversaries can rebut if dismissed too easily               │
│                            ↓                                    │
│  5. Multiple LLMs critique in parallel                          │
│     (GPT, Gemini, Grok, etc.)                                   │
│                            ↓                                    │
│  6. Claude synthesizes all feedback + adds own critique         │
│                            ↓                                    │
│  7. Revise and repeat until ALL models agree                    │
│                            ↓                                    │
│  8. User review: accept, request changes, or run another cycle  │
│                            ↓                                    │
│  9. Final document output                                       │
│                            ↓                                    │
│  10. Generate execution plan with tasks linked to concerns      │
└─────────────────────────────────────────────────────────────────┘
```

The gauntlet is where your spec gets stress-tested by personas who are *paid to find problems*. Then multiple LLMs debate until they all agree. Then you review. Then you get an execution plan that links tasks back to the concerns that drove them.

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

| Persona | What They Do | Why They're Annoying (In a Good Way) |
|---------|--------------|--------------------------------------|
| `paranoid_security` | Sees threats everywhere. Every input is malicious. Every dependency will be compromised. | Occasionally catches what everyone else missed because they weren't paranoid *enough*. |
| `burned_oncall` | Has been paged at 3am too many times. Obsessed with failure modes. "What happens when Redis goes down?" | Doesn't trust anything to stay up. Has seen too much. |
| `lazy_developer` | "This is too complicated. Why can't we just use X?" | Sometimes just lazy, sometimes catches genuine overengineering. |
| `pedantic_nitpicker` | What if the string is empty? What about 2^31 items? Leap seconds? Unicode? | Most concerns don't matter. Some really do. |
| `asshole_loner` | Brilliant antisocial engineer who jumps to conclusions. Blunt. Accepts good reasoning without argument. | Trusts logic, not authority. If you can prove it, they'll shut up. |

### The Final Boss

After all technical concerns are addressed and models agree, the **UX Architect** (running on Opus 4.5) asks: *"Did we lose the forest for the trees?"*

```bash
# Enable the final boss review
cat spec.md | python3 debate.py gauntlet --final-boss
```

This catches fundamental UX problems that got lost in technical discussions. User stories that don't add value. Measurement strategies that don't exist. Clever implementations that users didn't ask for.

### Adversary Leaderboard

Track which adversaries are actually useful over time:

```bash
python3 debate.py adversary-stats
```

Shows signal score (acceptance rate vs dismissal effort), rebuttal success rates, and which personas consistently find real issues vs which ones cry wolf.

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

# Gauntlet commands
debate.py gauntlet < spec.md                                    # Run full gauntlet
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
- `--doc-type, -d` - prd or tech
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
└── skills/
    └── adversarial-spec/
        ├── SKILL.md              # Skill definition and process
        └── scripts/
            ├── adversaries.py    # Centralized adversary personas
            ├── debate.py         # Multi-model debate orchestration
            ├── gauntlet.py       # Adversarial gauntlet engine
            ├── providers.py      # API key detection
            └── telegram_bot.py   # Telegram notifications
```

## License

MIT
