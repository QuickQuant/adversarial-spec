## Advanced Features

These examples use the primary `debate.py` entrypoint. Choose `MODEL_LIST` from
`reference/current-models.md`; tracked critique and gauntlet runs require a
pipeline card. In command templates, `$CARD_ID` and `$MODEL_LIST` are shell
variables already set to those values.

### Critique focus

Use `--focus` to prioritize one concern without changing the document type:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --models "$MODEL_LIST" \
  --doc-type spec --depth technical --focus security < spec.md
```

Built-in focus values:

- `security` — authentication, authorization, validation, encryption, vulnerabilities
- `scalability` — horizontal scale, sharding, caching, and capacity
- `performance` — latency, throughput, queries, and memory
- `ux` — journeys, error states, accessibility, and mobile behavior
- `reliability` — failure modes, retries, recovery, and operations
- `cost` — resource efficiency and build-versus-buy tradeoffs

Run `debate.py focus-areas` for the runtime list.

### Personas

Use `--persona` for a professional lens:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --models "$MODEL_LIST" \
  --doc-type spec --depth technical --persona security-engineer < spec.md
```

Built-in examples include `security-engineer`, `oncall-engineer`,
`junior-developer`, `qa-engineer`, `site-reliability`, `product-manager`,
`data-engineer`, `mobile-developer`, `accessibility-specialist`, and
`legal-compliance`. Custom persona text is also accepted. Run
`debate.py personas` for the runtime list.

### Context files

`--context` is repeatable and sends each selected file in full:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --models "$MODEL_LIST" \
  --doc-type spec --depth technical \
  --context ./existing-api.md --context ./schema.sql < spec.md
```

Apply the selection, exclusion, and staleness rules in
`reference/context-addition-protocol.md`.

### Persistent sessions and checkpoints

```bash
# Start a named debate.
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --models "$MODEL_LIST" \
  --doc-type spec --depth technical --session my-feature < spec.md

# Resume without stdin.
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --resume my-feature

# Inspect saved debates.
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py sessions
```

Session state records the current document, round, configuration, and history
under `~/.config/adversarial-spec/sessions/`. Named sessions also checkpoint
round documents under `.adversarial-spec-checkpoints/` in the working tree.

### Retry and response validation

Model calls make at most three attempts with exponential delays between failed
attempts. Exhausting one model reports its error while other model results remain
available. A critique response without `[SPEC]...[/SPEC]` produces a malformed
response warning rather than silently replacing the document.

### Preserve intent

Use `--preserve-intent` when unconventional but deliberate choices must survive
preference-driven convergence:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --models "$MODEL_LIST" \
  --doc-type spec --depth technical --preserve-intent < spec.md
```

Critics must quote a proposed removal, name its concrete harm, distinguish an
error or risk from preference, and ask before removing unusual but functional
behavior. Combine it with `--focus` or `--persona` when useful.

### Cost reporting

Text-mode cost output is shown only with `--show-cost`. `--json` includes a
structured `cost` object even without that flag.

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --models "$MODEL_LIST" \
  --doc-type spec --depth technical --show-cost < spec.md
```

### Profiles

```bash
# Save reusable parser settings.
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py save-profile \
  strict-security --models "$MODEL_LIST" --doc-type spec --depth technical \
  --focus security

# Use the profile while selecting spec depth explicitly.
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --profile strict-security \
  --doc-type spec --depth technical < spec.md

python3 ~/.claude/skills/adversarial-spec/scripts/debate.py profiles
```

Profiles fill options that remain unset; select depth explicitly because the
profile writer does not persist `--depth`. Profiles live under
`~/.config/adversarial-spec/profiles/`.

### Diff between rounds

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py diff \
  --previous round1.md --current round2.md
```

Use the diff to review incorporated feedback and detect accidental removals.

### Standalone gauntlet boundary

The lower-level `scripts/gauntlet/cli.py` is a separate entrypoint with different
flags and compatibility document types. Label its invocations explicitly:

```bash
# Standalone gauntlet CLI only; `tech` is valid here, not in debate.py.
python3 ~/.claude/skills/adversarial-spec/scripts/gauntlet/cli.py \
  --spec-file spec.md --doc-type tech --adversaries all
```

See `reference/script-commands.md` for both verified flag surfaces.
