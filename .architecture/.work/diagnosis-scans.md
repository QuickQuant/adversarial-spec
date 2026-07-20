# Phase 6 Mandatory Cross-File Scans

> Generated: 2026-07-19T08:43:13-05:00 | Git: `ef18c66`

## Registry / Config / Mapping Deduplication

Command family used:

```text
rg -l -i 'registry|_registry|config|mapping|catalog' skills/adversarial-spec/scripts .claude execution_planner
rg -n 'listdir|iterdir|scandir|os.walk|glob\(' skills/adversarial-spec/scripts .claude execution_planner
```

Result: no confirmed same-purpose registry pair with less than 50% key
overlap. `MODEL_COSTS` and `BEDROCK_MODEL_MAP` map different entities;
`ADVERSARIES` is a persona catalog; validation `SUBCOMMANDS` and `HANDLERS`
are one command table plus its dispatch implementation; the hook registry is
metadata, not the active settings registry. The `.conductor/agents` JSON files
are a role-discovery data source and are covered by the hook contract.

## Near-Duplicate Command / Endpoint Names

Command used:

```text
uv run python -c '...SequenceMatcher over the entry-point names...'
```

Result: `NO_NEAR_DUPLICATE_NAMES`. The two live gauntlet CLI surfaces have
different names and behavior, but they are a semantic duplication finding
because their timeout defaults diverge; they do not meet the edit-distance
trigger by name alone.

## Documentation Accuracy Spot-Check

Command family used:

```text
rg -n '\b[0-9]{1,4}\b|multiple|several' .architecture/{primer,overview,filesystem-map,INDEX,access-guide,patterns}.md
rg -n 'SUBCOMMANDS|KNOWN_ROLES|MODEL_COSTS|BEDROCK_MODEL_MAP|ADVERSARIES|FINAL_BOSS|PRE_GAUNTLET' skills/adversarial-spec/scripts .claude/hooks
```

Result: no high-level cardinality claim exceeded the 20% mismatch threshold.
The exact claims retained in high-level docs are the eight adversarial-spec
pipeline phases, two active gauntlet CLI surfaces, and the five timed-out
delegated discovery explorers; each was checked against project docs, source
entry points, and this run's delegation result.
