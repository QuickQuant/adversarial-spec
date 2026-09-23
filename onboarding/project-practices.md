# Project practices

Repository-specific conventions for `adversarial-spec`. Global safety and
workflow policy remains in [`AGENTS.md`](../AGENTS.md); adversarial-spec safety
extensions live in [`core-practices.md`](core-practices.md).

## Runtime and checks

The project requires Python 3.14 or newer and uses `uv`.

```bash
uv sync --extra dev
uv run pytest
uvx ruff check
```

`pyproject.toml` owns dependencies, console scripts, pytest discovery, and Ruff
configuration. Do not create a second dependency or tool configuration path.

## Source navigation

Read [`.architecture/INDEX.md`](../.architecture/INDEX.md) first, then
[`primer.md`](../.architecture/primer.md). Treat changed source as authoritative
when generated architecture documentation is stale.

| Change | Start here |
|---|---|
| Entry, resume, routing, transitions | [`skills/adversarial-spec/SKILL.md`](../skills/adversarial-spec/SKILL.md) |
| Phase behavior | [`skills/adversarial-spec/phases/`](../skills/adversarial-spec/phases/) |
| Shared guidance and protocols | [`skills/adversarial-spec/reference/`](../skills/adversarial-spec/reference/) |
| Python behavior | [`skills/adversarial-spec/scripts/`](../skills/adversarial-spec/scripts/) |
| Tests | [`skills/adversarial-spec/scripts/tests/`](../skills/adversarial-spec/scripts/tests/) |
| Machine-facing spec records | [`contracts/spec-record-contract.md`](../contracts/spec-record-contract.md) |
| Model assignments | [`reference/current-models.md`](../skills/adversarial-spec/reference/current-models.md) |

The root `adversarial_spec` symlink maps the installable package to
`skills/adversarial-spec/scripts`. Preserve that bridge when changing imports or
packaging. The declared console scripts are `adversarial-spec` and
`gauntlet-check`.

## Naming

Use qualified skill-owned terms and fields. Prefer `data_strategy` and
`test_strategy` over an ambiguous bare `strategy`; add new domain terms to
[`CONTEXT.md`](../CONTEXT.md).

External wire contracts keep the owner's spelling. For example, a Fizzy schema
field named `strategy` is not ours to rename. Change an external key only through
a coordinated owner-led migration. See
[`ADR 0001`](../docs/adr/0001-disambiguate-strategy-vocabulary.md).

## Integration boundaries

- Keep provider, process, filesystem, and external-service details in dedicated
  integration or adapter modules.
- Core orchestration consumes normalized internal interfaces; it does not grow
  provider-specific branches or payload conversions.
- Entrypoints coordinate services. They do not duplicate integration logic.
- Search for an existing adapter or shared contract before adding a new one.

Keep changes minimal and source-backed. If a contract producer and consumer live
in different repositories, name the owner and coordinate the migration instead
of forking the contract locally.
