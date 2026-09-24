# Contributing to adversarial-spec

## Setup

Use Python 3.14 or newer and `uv` from the repository root.

```bash
uv sync --extra dev
```

Runtime and development dependencies are declared in `pyproject.toml`. Do not
add an undocumented parallel requirements file.

## Checks

Run the configured test suite and linter before requesting review:

```bash
uv run pytest
uvx ruff check
```

Tests live under `skills/adversarial-spec/scripts/tests/`; pytest discovers that
path from `pyproject.toml`. Run a focused test during development, then the full
suite for the final handoff.

The repository does not define a mandatory formatter, type-check, or coverage
threshold for contributions. Do not claim those gates unless project
configuration adds them.

## Change discipline

- Keep each change focused and preserve unrelated work already in the tree.
- Add or update tests for behavioral changes. Do not pin incidental prose.
- Validate required fields at boundaries and fail explicitly; never fabricate a
  success path from missing state.
- Keep secrets out of source, fixtures, logs, examples, and commits.
- Follow [`AGENTS.md`](AGENTS.md) and the active Phase guidance for safety and
  workflow rules.

## Review

A review should be able to trace the requested behavior to source, tests, and
any affected specification artifact. Call out:

- behavior or contract changed;
- relevant checks run and their result;
- migration or compatibility impact;
- deferred work and its owner.

The implementer must not approve their own pipeline review.

## Commits and pull requests

Use Conventional Commit subjects, with a scope when it improves routing:

```text
docs(readme): refresh operator guide
fix(pipeline): reject missing plan provenance
```

Keep commits reviewable. Pull requests should summarize the outcome, name the
evidence used for validation, and avoid unrelated cleanup.
