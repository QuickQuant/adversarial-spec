## Adversarial Gauntlet

The gauntlet is a multi-phase stress test that puts your spec through adversarial attack by specialized personas, then evaluates which attacks are valid.

### Gauntlet Phases

1. **Phase 1: Adversary Attacks** - Multiple adversary personas attack the spec in parallel
2. **Phase 2: Evaluation** - A frontier model evaluates each attack (accept/dismiss/defer)
3. **Phase 3: Rebuttals** - Dismissed adversaries can challenge the evaluation
4. **Phase 4: Summary** - Aggregated results showing accepted concerns
5. **Phase 5: Final Boss** (optional) - Opus 4.6 UX Architect reviews the spec holistically

### Adversary Personas

| Persona | Focus |
|---------|-------|
| `paranoid_security` | Auth holes, injection, encryption gaps, trust boundaries |
| `burned_oncall` | Missing alerts, log gaps, failure modes, debugging at 3am |
| `lazy_developer` | Complexity that the platform/SDK already handles. Dismissals must prove simpler fails. |
| `pedantic_nitpicker` | Inconsistencies, spec gaps, undefined edge cases |
| `asshole_loner` | Aggressive devil's advocate, challenges fundamental assumptions |
| `prior_art_scout` | Finds existing code, SDKs, legacy implementations that spec ignores |
| `assumption_auditor` | Challenges domain premises, demands documentation citations |
| `information_flow_auditor` | Audits architecture arrows - every unlabeled flow, every assumed mechanism |

### Usage

```bash
# Run gauntlet with all adversaries (generally this is what you want)
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --gauntlet-adversaries all

# Run with specific adversaries
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --gauntlet-adversaries paranoid_security,burned_oncall

# Combine with regular critique (gauntlet runs first)
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex --gauntlet --gauntlet-adversaries all

# Skip rebuttals for faster execution
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --gauntlet-adversaries all --no-rebuttals

# List available adversaries
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet-adversaries

# View adversary performance stats
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py adversary-stats
```

### Final Boss Review

After phase 4 completes, you'll be prompted:

```
Run Final Boss UX review? (y/n):
```

The Final Boss is an Opus 4.6 UX Architect who reviews the spec for:
- User journey completeness
- Error state handling
- Accessibility concerns
- Overall coherence

This is expensive but thorough. You can also pre-commit with `--final-boss` to skip the prompt.

### Gauntlet Options

- `--gauntlet, -g` - Enable gauntlet mode (can combine with critique)
- `--gauntlet-adversaries` - **NAMES only** (comma-separated or `all`). NOT a count!
  - ✅ `--gauntlet-adversaries all`
  - ✅ `--gauntlet-adversaries paranoid_security,burned_oncall`
  - ❌ `--gauntlet-adversaries 5` (WRONG - this is not a count)
- `--gauntlet-model` - Model for adversary attacks (default: auto-select free model)
- `--gauntlet-frontier` - Model for evaluation (default: auto-select frontier model)
- `--no-rebuttals` - Skip Phase 3 rebuttal phase
- `--final-boss` - Auto-run Phase 5 (skips prompt)

