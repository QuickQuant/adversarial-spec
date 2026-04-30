## Script Reference

```bash
# Full path to debate.py (required - scripts are in a subdirectory)
DEBATE="python3 ~/.claude/skills/adversarial-spec/scripts/debate.py"

# Core commands
$DEBATE critique --models MODEL_LIST --doc-type TYPE [OPTIONS] < spec.md
$DEBATE critique --resume SESSION_ID
$DEBATE diff --previous OLD.md --current NEW.md
$DEBATE export-tasks --models MODEL --doc-type TYPE [--json] < spec.md

# Info commands
$DEBATE providers      # List supported providers and API key status
$DEBATE focus-areas    # List available focus areas
$DEBATE personas       # List available personas
$DEBATE profiles       # List saved profiles
$DEBATE sessions       # List saved sessions

# Profile management
$DEBATE save-profile NAME --models ... [--focus ...] [--persona ...]

# Telegram
$DEBATE send-final --models MODEL_LIST --doc-type TYPE --rounds N < spec.md

# Gauntlet (adversarial attack on specs — 7-phase pipeline)
# IMPORTANT: --gauntlet-adversaries expects NAMES, not a count!
$DEBATE gauntlet --gauntlet-adversaries all < spec.md                    # All adversaries
$DEBATE gauntlet --gauntlet-adversaries paranoid_security,burned_oncall  # Specific ones
$DEBATE gauntlet --gauntlet-adversaries all --gauntlet-resume            # Resume from checkpoint
$DEBATE gauntlet --gauntlet-adversaries all \
  --gauntlet-attack-models "codex/gpt-5.5,gemini-cli/gemini-3.1-pro-preview"  # Multi-model attacks
$DEBATE gauntlet --show-manifest                                         # Show latest run manifest
$DEBATE gauntlet --show-manifest abc1234                                 # Show specific run manifest
$DEBATE gauntlet-adversaries  # List available adversary names
$DEBATE adversary-stats       # View adversary performance
$DEBATE medal-leaderboard     # View medal rankings

# Standalone gauntlet CLI (different flag names — see reference/gauntlet-details.md)
GAUNTLET="python3 ~/.claude/skills/adversarial-spec/scripts/gauntlet/cli.py"
$GAUNTLET --adversaries all < spec.md
$GAUNTLET --spec-file spec.md --adversaries all --resume --unattended
$GAUNTLET --list-runs
$GAUNTLET --show-run FILENAME
```

**Critique options:**
- `--models, -m` - Comma-separated model list (auto-detects from available API keys if not specified)
- `--doc-type, -d` - Document type: prd or tech (default: tech)
- `--round, -r` - Current round number (default: 1)
- `--focus, -f` - Focus area for critique
- `--persona` - Professional persona for critique
- `--context, -c` - Context file (can be used multiple times)
- `--profile` - Load settings from saved profile
- `--preserve-intent` - Require explicit justification for any removal
- `--session, -s` - Session ID for persistence and checkpointing
- `--resume` - Resume a previous session by ID
- `--press, -p` - Anti-laziness check for early agreement
- `--telegram, -t` - Enable Telegram notifications
- `--poll-timeout` - Telegram reply timeout in seconds (default: 60)
- `--json, -j` - Output as JSON
- `--codex-search` - Enable web search for Codex CLI models (allows researching current info)
- `--timeout` - Timeout in seconds for model API/CLI calls (default: 600)
- `--show-cost` - Show cost summary after critique

**Gauntlet options (via debate.py):**
- `--gauntlet, -g` - Enable gauntlet mode (can combine with critique)
- `--gauntlet-adversaries` - **NAMES only** (comma-separated or `all`)
- `--gauntlet-attack-models` - Comma-separated models for Phase 1 attacks
- `--gauntlet-model` - Legacy single attack model (overridden by --gauntlet-attack-models)
- `--gauntlet-frontier` - Evaluation model
- `--codex-reasoning` - Attack reasoning effort (default: low). Maps to `attack_codex_reasoning` in the pipeline
- `--eval-codex-reasoning` - Eval/adjudication reasoning (default: xhigh)
- `--gauntlet-resume` - Resume from checkpoint
- `--no-rebuttals` - Skip Phase 5 rebuttals
- `--final-boss` - Auto-run Phase 7
- `--show-manifest [HASH]` - Display run manifest

## External Documentation Discovery (Context7)

Before the gauntlet runs, the **Discovery Agent** extracts external services from your spec and fetches their official documentation via Context7. This prevents models from making assumptions based on training data patterns.

### Why Discovery Matters

AI models share training data and thus share false assumptions. The classic failure:

> All models assumed "crypto trading = on-chain transactions" when Polymarket's CLOB is actually off-chain with SDK-handled signing. 11 concerns were raised about nonces that don't exist.

### How to Use Discovery

When you have Context7 MCP tools available, run discovery before the gauntlet:

1. **Extract services from spec:**
   ```python
   from pre_gauntlet import DiscoveryAgent, run_discovery

   result = run_discovery(spec_text, min_confidence=0.6, max_services=5)
   print(f"Discovered: {[s.name for s in result.services]}")
   ```

2. **Fetch documentation via Context7:**
   - Use `mcp__context7__resolve-library-id` to resolve library names
   - Use `mcp__context7__query-docs` to fetch relevant documentation
   - Results are cached locally (24h TTL, `~/.cache/adversarial-spec/knowledge/`)

3. **Inject priming context into gauntlet:**
   ```python
   from pre_gauntlet import run_pre_gauntlet

   pre_result = run_pre_gauntlet(
       spec_text=spec,
       doc_type="tech",
       discovery_result=discovery_result,  # Includes priming context
   )
   ```

### Integration with Adversaries

The `assumption_auditor` adversary specifically challenges domain assumptions and demands documentation citations. When discovery has fetched docs, claims can be verified against actual documentation:

- **VERIFIED**: Claim matches documentation
- **REFUTED**: Documentation contradicts claim
- **UNVERIFIABLE**: No documentation found
- **PENDING**: Documentation found, needs LLM analysis

