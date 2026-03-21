## Adversarial Gauntlet

The gauntlet is a multi-phase stress test that puts your spec through adversarial attack by specialized personas, then evaluates which attacks are valid. It runs as a 16-module package (`gauntlet/`) with `orchestrator.py:run_gauntlet()` as the primary entry point.

### Gauntlet Phases

1. **Phase 1: Adversary Attacks** — Multiple adversary personas attack the spec in parallel across multiple models
2. **Phase 2: Big Picture Synthesis** — A single model generates a holistic synthesis across all raw attacks
3. **Phase 3: Filter + Cluster** — Dedup, filter resolved concerns, cluster by theme (FileLock checkpoint)
4. **Phase 3.5: Checkpoint** — Persist clustered concerns to disk (enables `--gauntlet-resume`)
5. **Phase 4: Multi-model Evaluation** — Multiple eval models evaluate concerns in batches of 15 (wave-based)
6. **Phase 5: Adversary Rebuttals** — Dismissed adversaries challenge the evaluation verdicts
7. **Phase 6: Final Adjudication** — Synthesize evaluations + rebuttals into final verdicts
8. **Phase 7: Final Boss** (optional) — Opus 4.6 UX Architect reviews the spec holistically

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
| `architect` | Code structure, data flow, component boundaries, shared patterns |
| `information_flow_auditor` | Audits architecture arrows - every unlabeled flow, every assumed mechanism |

### Usage

**Two CLI entry points exist:**

```bash
# ─── Via debate.py (integrates with critique workflow) ───

# Run gauntlet with all adversaries
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --gauntlet-adversaries all

# Run with specific adversaries and multiple attack models
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet \
  --gauntlet-adversaries paranoid_security,burned_oncall \
  --gauntlet-attack-models "codex/gpt-5.4,gemini-cli/gemini-3-pro-preview"

# Resume from checkpoint (reuse Phase 1-3 concerns)
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet \
  --gauntlet-adversaries all --gauntlet-resume

# Combine with regular critique (gauntlet runs first)
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models codex/gpt-5.4 --gauntlet --gauntlet-adversaries all

# List available adversaries
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet-adversaries

# View adversary performance stats
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py adversary-stats

# Show run manifest for a gauntlet run
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --show-manifest [HASH]

# ─── Via standalone CLI (gauntlet-only, different flag names) ───

# Run gauntlet standalone
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/gauntlet/cli.py --adversaries all

# Standalone with resume + unattended
python3 ~/.claude/skills/adversarial-spec/scripts/gauntlet/cli.py \
  --spec-file spec.md --adversaries all --resume --unattended

# List runs and show details
python3 ~/.claude/skills/adversarial-spec/scripts/gauntlet/cli.py --list-runs
python3 ~/.claude/skills/adversarial-spec/scripts/gauntlet/cli.py --show-run FILENAME
```

**Flag name mapping** (debate.py → standalone cli.py):

| debate.py | cli.py | Purpose |
|-----------|--------|---------|
| `--gauntlet-adversaries` | `--adversaries` | Adversary selection |
| `--gauntlet-model` | `--adversary-model` | Legacy single attack model |
| `--gauntlet-attack-models` | `--attack-models` | Multi-model attacks |
| `--gauntlet-frontier` | `--eval-model` | Evaluation model |
| `--codex-reasoning` | `--attack-codex-reasoning` | Attack reasoning effort |
| `--eval-codex-reasoning` | `--eval-codex-reasoning` | Eval reasoning effort |
| `--gauntlet-resume` | `--resume` | Resume from checkpoint |
| N/A | `--unattended` | No stdin prompts + auto-checkpoint |
| N/A | `--spec-file PATH` | Read spec from file |

### Final Boss Review

After Phase 6 (adjudication) completes, the Final Boss review can run as Phase 7:

The Final Boss is an Opus 4.6 UX Architect who reviews the spec holistically for:
- User journey completeness
- Error state handling
- Accessibility concerns
- Overall coherence

This is expensive but thorough. Use `--final-boss` to enable it.

### Gauntlet Options (debate.py flags)

- `--gauntlet, -g` — Enable gauntlet mode (can combine with critique)
- `--gauntlet-adversaries` — **NAMES only** (comma-separated or `all`). NOT a count!
  - ✅ `--gauntlet-adversaries all`
  - ✅ `--gauntlet-adversaries paranoid_security,burned_oncall`
  - ❌ `--gauntlet-adversaries 5` (WRONG - this is not a count)
- `--gauntlet-model` — Legacy single model for attacks (default: auto-select free model)
- `--gauntlet-attack-models` — Comma-separated models for Phase 1 attacks (overrides --gauntlet-model)
- `--gauntlet-frontier` — Model for evaluation (default: auto-select frontier model)
- `--codex-reasoning` — Reasoning effort for attack phases (default: low). Choices: minimal, low, medium, high, xhigh
- `--eval-codex-reasoning` — Reasoning effort for eval/adjudication (default: xhigh)
- `--no-rebuttals` — Skip Phase 5 rebuttal phase
- `--final-boss` — Auto-run Phase 7 (skips prompt)
- `--gauntlet-resume` — Resume from checkpoint (reuse Phase 1-3 concerns, skip re-eval)
- `--timeout` — Timeout per model call in seconds (default: 600 via debate.py, 300 via standalone)

### Checkpointing & Resume

The gauntlet saves checkpoints after each phase to `.adversarial-spec-gauntlet/`. Checkpoints use `filelock` for atomic writes and include `spec_hash` + `config_hash` for validation.

On `--gauntlet-resume`:
1. Load checkpoint file matching current spec hash
2. Verify `config_hash` matches (attack models, eval models, adversary list)
3. Skip completed phases, resume from the earliest incomplete phase
4. If no valid checkpoint exists, start fresh (no error)

The `--unattended` flag (standalone CLI only) enables auto-checkpointing after expensive phases and disables all `input()` calls.

### Run Manifests

Each gauntlet run produces a manifest with per-phase `PhaseMetrics`:
- Duration, input/output tokens, models used, config snapshot
- Saved to `.adversarial-spec-gauntlet/run-manifest-{hash}-{timestamp}.json`
- View via `debate.py gauntlet --show-manifest [HASH]` or `cli.py --list-runs`

