## Advanced Features

### Critique Focus Modes

Direct models to prioritize specific concerns using `--focus`:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.5 --focus security --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**Available focus areas:**
- `security` - Authentication, authorization, input validation, encryption, vulnerabilities
- `scalability` - Horizontal scaling, sharding, caching, load balancing, capacity planning
- `performance` - Latency targets, throughput, query optimization, memory usage
- `ux` - User journeys, error states, accessibility, mobile experience
- `reliability` - Failure modes, circuit breakers, retries, disaster recovery
- `cost` - Infrastructure costs, resource efficiency, build vs buy

Run `python3 ~/.claude/skills/adversarial-spec/scripts/debate.py focus-areas` to see all options.

### Model Personas

Have models critique from specific professional perspectives using `--persona`:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.5 --persona "security-engineer" --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**Available personas:**
- `security-engineer` - Thinks like an attacker, paranoid about edge cases
- `oncall-engineer` - Cares about observability, error messages, debugging at 3am
- `junior-developer` - Flags ambiguity and tribal knowledge assumptions
- `qa-engineer` - Identifies missing test scenarios and acceptance criteria
- `site-reliability` - Focuses on deployment, monitoring, incident response
- `product-manager` - Focuses on user value and success metrics
- `data-engineer` - Focuses on data models and ETL implications
- `mobile-developer` - API design from mobile perspective
- `accessibility-specialist` - WCAG compliance, screen reader support
- `legal-compliance` - GDPR, CCPA, regulatory requirements

Run `python3 ~/.claude/skills/adversarial-spec/scripts/debate.py personas` to see all options.

Custom personas also work: `--persona "fintech compliance officer"`

### Context Injection

Include existing documents as context for the critique using `--context`:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.5 --context ./existing-api.md --context ./schema.sql --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

Use cases:
- Include existing API documentation that the new spec must integrate with
- Include database schemas the spec must work with
- Include design documents or prior specs for consistency
- Include compliance requirements documents

### Session Persistence and Resume

Long debates can crash or need to pause. Sessions save state automatically:

```bash
# Start a named session
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.5 --session my-feature-spec --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF

# Resume where you left off (no stdin needed)
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --resume my-feature-spec

# List all sessions
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py sessions
```

Sessions save:
- Current spec state
- Round number
- All configuration (models, focus, persona, preserve-intent)
- History of previous rounds

Sessions are stored in `~/.config/adversarial-spec/sessions/`.

### Auto-Checkpointing

When using sessions, each round's spec is saved to `.adversarial-spec-checkpoints/` in the current directory:

```
.adversarial-spec-checkpoints/
├── my-feature-spec-round-1.md
├── my-feature-spec-round-2.md
└── my-feature-spec-round-3.md
```

Use these to rollback if a revision makes things worse.

### Retry on API Failure

API calls automatically retry with exponential backoff (1s, 2s, 4s) up to 3 times. If a model times out or rate-limits, you'll see:

```
Warning: codex/gpt-5.5 failed (attempt 1/3): rate limit exceeded. Retrying in 1.0s...
```

If all retries fail, the error is reported and other models continue.

### Response Validation

If a model provides critique but doesn't include proper `[SPEC]` tags, a warning is displayed:

```
Warning: codex/gpt-5.5 provided critique but no [SPEC] tags found. Response may be malformed.
```

This catches cases where models forget to format their revised spec correctly.

### Preserve Intent Mode

Convergence can collapse toward lowest-common-denominator interpretations, sanding off novel design choices. The `--preserve-intent` flag makes removals expensive:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.5 --preserve-intent --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

When enabled, models must:

1. **Quote exactly** what they want to remove or substantially change
2. **Justify the harm** - not just "unnecessary" but what concrete problem it causes
3. **Distinguish error from preference**:
   - ERRORS: Factually wrong, contradictory, or technically broken (remove/fix)
   - RISKS: Security holes, scalability issues, missing error handling (flag)
   - PREFERENCES: Different style, structure, or approach (DO NOT remove)
4. **Ask before removing** unusual but functional choices

This shifts the default from "sand off anything unusual" to "add protective detail while preserving distinctive choices."

**Use when:**
- Your spec contains intentional unconventional choices
- You want models to challenge your ideas, not homogenize them
- Previous rounds removed things you wanted to keep
- You're refining an existing spec that represents deliberate decisions

Can be combined with other flags: `--preserve-intent --focus security`

### Cost Tracking

Every critique round displays token usage and estimated cost:

```
=== Cost Summary ===
Total tokens: 12,543 in / 3,221 out
Total cost: $0.0847

By model:
  codex/gpt-5.5: $0.00 (8,234 in / 2,100 out) [subscription]
  gemini-cli/gemini-3.1-pro-preview: $0.00 (4,309 in / 1,121 out) [free tier]
```

Cost is also included in JSON output and Telegram notifications.

### Saved Profiles

Save frequently used configurations as profiles:

**Create a profile:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py save-profile strict-security --models codex/gpt-5.5,gemini-cli/gemini-3.1-pro-preview --focus security --doc-type tech
```

**Use a profile:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --profile strict-security <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**List profiles:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py profiles
```

Profiles are stored in `~/.config/adversarial-spec/profiles/`.

Profile settings can be overridden by explicit flags.

### Diff Between Rounds

Generate a unified diff between spec versions:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py diff --previous round1.md --current round2.md
```

Use this to see exactly what changed between rounds. Helpful for:
- Understanding what feedback was incorporated
- Reviewing changes before accepting
- Documenting the evolution of the spec

### Export to Task List

Extract actionable tasks from a finalized spec:

```bash
cat spec-output.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py export-tasks --models codex/gpt-5.5 --doc-type prd
```

Output includes:
- Title
- Type (user-story, task, spike, bug)
- Priority (high, medium, low)
- Description
- Acceptance criteria

Use `--json` for structured output suitable for importing into issue trackers:

```bash
cat spec-output.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py export-tasks --models codex/gpt-5.5 --doc-type prd --json > tasks.json
```

