# Gauntlet Runner Map

[Phase 5](../phases/05-gauntlet.md) owns human gates, approved context, synthesis and completion evidence. `gauntlet/orchestrator.py::run_gauntlet` runs attacks → synthesis → filter/cluster → evaluation → rebuttals → adjudication → optional Final Boss. These are gauntlet-internal steps, not additional pipeline phases.

## Evaluation Strategy

`power_law_length` is the `run_gauntlet` and standalone argparse default: concern length cutoffs p60/p90, batches 75/30/12. Below `eval_tier_min_concerns=30`, use flat batches of 15. Standalone flags `--eval-tier-strategy flat`, `--eval-flat-batch-size` and `--eval-tier-min-concerns` provide overrides; `debate.py` does not expose these tunables.

## Personas and Seats

Canonical `ADVERSARIES` in [adversaries.py](../scripts/adversaries.py): `paranoid_security`, `burned_oncall`, `minimalist`, `pedantic_nitpicker`, `asshole_loner`, `assumption_auditor`, `information_flow_auditor`, `architect`, `traffic_engineer`.

Separate registries hold `existing_system_compatibility` (pre-gauntlet), `spec_coroner` (SCOUT) and `ux_architect` (Final Boss); these are not fleet CLI names. SCOUT needs the separate reviewer dispatch described in Phase 5. Compatibility aliases `lazy_developer` and `prior_art_scout` map to `minimalist` in the orchestrator, but `debate.py` rejects aliases.

[current-models.md](current-models.md) owns seats. Runner auto-selection still includes retired routes; explicit attack/evaluation overrides do not replace every internal default. Final Boss calls `select_eval_model()` separately. Verify actual routes before launching.

## Tracked Path and Development Surface

Run from the subject project root with approved prompts already in `.adversarial-spec-gauntlet/`:

```bash
uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet \
  --pipeline-card "$CARD_ID" --gauntlet-adversaries "$PERSONAS" \
  --gauntlet-attack-models "$ATTACK_MODELS" --gauntlet-frontier "$EVAL_MODELS" \
  < "$SPEC_PATH"
```

Supply canonical persona names (comma-separated or `all`), never a count. The card fence applies before dispatch. CLI success does not establish pipeline completion; Phase 5 calls the MCP verifier with explicit `board_id` and admissible artifacts.

`python -m gauntlet` is the secondary/development surface; expose the skill's scripts directory on the Python import path when invoking it from a working directory containing the intended artifacts. It is not a tracked-card gate bypass.

| `debate.py gauntlet` | `python -m gauntlet` | Purpose |
|---|---|---|
| `--gauntlet-adversaries` | `--adversaries` | Persona names |
| `--gauntlet-model` | `--adversary-model` | Single attack override |
| `--gauntlet-attack-models` | `--attack-models` | Multiple attack overrides |
| `--gauntlet-frontier` | `--eval-model` | Comma-separated evaluation list / single evaluation model |
| `--codex-reasoning` | `--attack-codex-reasoning` | Attack effort; argparse default `low` |
| `--eval-codex-reasoning` | Same | Evaluation effort; argparse default `xhigh` |
| `--gauntlet-resume` | `--resume` | Reuse valid checkpoints |
| `--unattended` | Same | Disable stdin prompts, enable expensive-step checkpointing |
| stdin | stdin or `--spec-file PATH` | Spec text; both CLIs strip outer whitespace |
| `--timeout` | Same | Per-call default **1200s** / **1800s**, respectively |
| `--no-rebuttals` | Same | Omit rebuttals |
| `--final-boss` | No dedicated flag | Request Final Boss; its timeout is at least 1800s |

Flag/default authority: `debate.py` argparse and `gauntlet/cli.py::main`. Effort defaults describe execution, not seat policy.

## Resume and Inspection

Checkpoints under `.adversarial-spec-gauntlet/` use `_meta` + `data`, with schema, spec/config hashes and payload integrity. Resume reuses compatible completed work; rejected/missing checkpoints can cause fresh calls. Inspect resume warnings before assuming saved cost. Persistence uses file locks and atomic file replacement; avoid concurrent same-spec writers.

The runner loads `approved-prompts.json` into attack `prompts` overrides; retain that file with the reviewed inputs. `get_spec_hash` returns the full SHA-256 of the supplied string. A changed spec invalidates approved prompts; changed context requires reapproval even when the hash is unchanged. Prompt contents are not part of `get_config_hash`; omit resume when prompts/context changed so old attacks are not reused.

Inspect `run-manifest-{hash}-{timestamp}.json`: top-level status/spec hash/reviewed-spec path plus `phases[]` metrics (duration, tokens, models, configuration). `debate.py gauntlet --pipeline-card "$CARD_ID" --show-manifest "$HASH"` displays the matching manifest. Standalone `--list-runs` and `--show-run FILENAME` inspect saved run reports.

The runner does not emit the altitude manifest required by `pipeline_mark_gauntlet_complete`. Read [Phase 5 completion evidence](../phases/05-gauntlet.md#completion-evidence-and-handoff) before claiming completion; a manifest's existence is insufficient.
