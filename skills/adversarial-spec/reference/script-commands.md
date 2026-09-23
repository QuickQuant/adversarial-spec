## Script Reference

Model and seat selection belongs to `reference/current-models.md`. The two
entrypoints below have different parsers; do not transfer flags between them.
Set `$CARD_ID`, `$MODEL_LIST`, and `$SESSION_ID` before using templates that
reference them.

### Primary entrypoint: `debate.py`

```bash
DEBATE="$HOME/.claude/skills/adversarial-spec/scripts/debate.py"

# Tracked technical critique.
python3 "$DEBATE" critique --pipeline-card "$CARD_ID" --models "$MODEL_LIST" \
  --doc-type spec --depth technical < spec.md

# Resume a saved debate; resume supplies the document, so no stdin is needed.
python3 "$DEBATE" critique --pipeline-card "$CARD_ID" --resume "$SESSION_ID"

# Tracked gauntlet runs still read the spec from stdin.
python3 "$DEBATE" gauntlet --pipeline-card "$CARD_ID" \
  --gauntlet-adversaries all < spec.md
python3 "$DEBATE" gauntlet --pipeline-card "$CARD_ID" \
  --gauntlet-adversaries NAME_A,NAME_B --gauntlet-resume < spec.md

# Manifest inspection does not consume a spec.
python3 "$DEBATE" gauntlet --pipeline-card "$CARD_ID" --show-manifest
python3 "$DEBATE" gauntlet --pipeline-card "$CARD_ID" --show-manifest HASH
```

`critique` and `gauntlet` require `--pipeline-card`. Use
`IntentionalOverride` only with a meaningful `--override-reason` of at least 50
characters. The pipeline path remains the normal path.

#### Actions

| Action | Purpose / required operands |
|---|---|
| `critique` | Run a critique round or `--resume SESSION_ID`. Reads stdin unless resuming. |
| `gauntlet` | Run the integrated gauntlet; reads stdin except with `--show-manifest`. |
| `gauntlet-adversaries` | List registered adversaries. |
| `adversary-stats` | Show adversary performance. |
| `medal-leaderboard` | Show medal rankings. |
| `adversary-versions` | Show the adversary version manifest. |
| `providers` | Show provider availability. |
| `send-final` | Send the stdin document; use `--models`, `--doc-type`, and `--rounds`. |
| `diff` | Requires `--previous OLD.md --current NEW.md`. |
| `focus-areas` | List focus values. |
| `personas` | List personas. |
| `profiles` | List saved profiles. |
| `save-profile NAME` | Save the supplied model/document/focus/persona/context/intent settings. |
| `sessions` | List saved debate sessions. |
| `bedrock SUBCOMMAND [ARG]` | `status`, `enable`, `disable`, `add-model`, `remove-model`, `alias`, or `list-models`; `enable` accepts `--region`. |

Utility-only flags are `--previous` and `--current` for `diff`, plus `--region`
and the optional second positional argument for `bedrock`.

#### Critique and shared flags

| Flag | Choices / default | Meaning |
|---|---|---|
| `--models, -m` | comma-separated; auto-detect when omitted | Critic models. |
| `--doc-type, -d` | `spec`, `debug`, `architecture`; `spec` | Document contract. |
| `--depth` | `product`, `technical`, `full`; `technical` | Used only with `--doc-type spec`. |
| `--round, -r` | integer; `1` | Current critique round. |
| `--rounds` | integer; `1` | Completed rounds reported by `send-final`. |
| `--cwd` | path; unset | Working directory for CLI subprocesses. |
| `--focus, -f` | text; unset | Critique focus. |
| `--persona` | text; unset | Built-in or custom persona. |
| `--context, -c` | repeatable path; none | Include each file in full. |
| `--preserve-intent` | off | Require justification for removals. |
| `--press, -p` | off | Require a fuller early-agreement check. |
| `--session, -s` | ID; unset | Persist a named debate. |
| `--resume` | ID; unset | Resume persisted state. |
| `--profile` | name; unset | Fill unset settings from a saved profile. |
| `--json, -j` | off | Emit structured output. |
| `--show-cost` | off | Print the text cost summary. |
| `--telegram, -t` | off | Send the direct debate-round notification and poll for feedback. |
| `--poll-timeout` | seconds; `60` | Direct Telegram poll limit. |
| `--codex-reasoning`, `--attack-codex-reasoning` | `minimal|low|medium|high|xhigh`; `xhigh` | Reasoning effort for primary/Codex attack calls. |
| `--codex-search` | off | Permit search for supported CLI calls. |
| `--timeout` | seconds; `1200` | Per model-call timeout. |
| `--skip-preflight` | off | Skip the pre-dispatch model ping. |

Pipeline-gate flags are `--pipeline-card`, `--override-reason`,
`--accept-tests-stale`, `--accept-missing-spine`, and
`--spine-override-reason`. Use the acceptance flags only for their named gate;
they are logged and do not bypass other checks.

#### Integrated gauntlet flags

| Flag | Choices / default | Meaning |
|---|---|---|
| `--gauntlet, -g` | off | Parsed but currently unused; dispatch through the positional `gauntlet` action. |
| `--gauntlet-adversaries`, `--adversaries` | names or `all`; `all` | Select adversaries by name, never by count. |
| `--gauntlet-model`, `--adversary-model` | model; auto | Legacy single attack model. |
| `--gauntlet-attack-models`, `--attack-models` | comma-separated; unset | Attack models; overrides the single-model flag. |
| `--gauntlet-frontier`, `--eval-model` | comma-separated; auto | Evaluation models. |
| `--no-rebuttals` | off | Skip rebuttals. |
| `--final-boss` | off | Run the final review stage. |
| `--eval-codex-reasoning` | `minimal|low|medium|high|xhigh`; `xhigh` | Evaluation/adjudication effort. |
| `--gauntlet-resume` | off | Resume valid gauntlet checkpoints. |
| `--unattended` | off | Disable stdin prompts and enable automatic checkpoints. |
| `--show-manifest [HASH]` | unset | Show the newest or matching run manifest and exit. |

### Lower-level entrypoint: standalone gauntlet CLI

This entrypoint reads stdin unless `--spec-file` is supplied.

```bash
GAUNTLET="$HOME/.claude/skills/adversarial-spec/scripts/gauntlet/cli.py"

python3 "$GAUNTLET" --adversaries all < spec.md
python3 "$GAUNTLET" --spec-file spec.md --adversaries all --resume --unattended
python3 "$GAUNTLET" --list-adversaries
python3 "$GAUNTLET" --list-runs
python3 "$GAUNTLET" --show-run FILENAME
```

| Flag | Choices / default | Meaning |
|---|---|---|
| `--adversaries` | names or `all`; `all` | Attack roster. |
| `--adversary-model` | model; auto | Legacy single attack model. |
| `--attack-models` | comma-separated; unset | Attack models; overrides the single-model flag. |
| `--eval-model` | model; auto | Evaluation model. |
| `--no-rebuttals` | off | Skip rebuttals. |
| `--attack-codex-reasoning` | `minimal|low|medium|high|xhigh`; `low` | Attack effort. |
| `--eval-codex-reasoning` | same choices; `xhigh` | Evaluation/adjudication effort. |
| `--timeout` | seconds; `1800` | Per model-call timeout. |
| `--json` | off | Emit JSON. |
| `--list-adversaries` | off | List adversaries and exit. |
| `--stats` | off | Show performance statistics and exit. |
| `--list-runs [N]` | `10` when flag has no value | List recent runs and exit. |
| `--show-run FILENAME` | unset | Show a persisted run and exit. |
| `--pre-gauntlet` | off | Run compatibility checks before attacks. |
| `--doc-type` | `prd`, `tech`, `debug`; `tech` | Standalone compatibility type. |
| `--spec-file PATH` | unset | Read the spec from a file instead of stdin. |
| `--report-path PATH` | `.adversarial-spec/pre_gauntlet_report.json` | Save the pre-gauntlet report. |
| `--unattended` | off | Disable prompts and enable automatic checkpoints. |
| `--resume` | off | Resume a valid checkpoint; no-op when none exists. |
| `--eval-tier-strategy` | `flat`, `power_law_length`; `power_law_length` | Evaluation batching strategy. |
| `--eval-tier-min-concerns` | integer; `30` | Minimum count before power-law tiering. |
| `--eval-flat-batch-size` | integer; `15` | Flat fallback batch size. |

### Optional documentation discovery

External-service discovery is not automatic in either command above. The
discovery module can extract service names, but the repository's former
`KnowledgeService` implementation has been removed. Documentation fetching
skips unless a caller injects a compatible service, and the standalone CLI does
not inject one. Treat Context7 or another documentation source as an optional
preparation step, then pass verified output through the normal context path.
