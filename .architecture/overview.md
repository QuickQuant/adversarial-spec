# System Overview: adversarial-spec

> Generated: 2026-07-19T08:43:13-05:00 | Git: ef18c66 | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 4.0 | Model: Codex
> Freshness: caution | Trust: source-backed local synthesis after delegated explorer timeout; if derived source files changed after `ef18c66`, trust source over this document.

## What This System Does

`adversarial-spec` is a Claude Code plugin and Python CLI that turns a product idea or document into a specification refined by multiple model critiques. Once a round reaches the desired agreement, the gauntlet attacks the surviving spec with named adversary personas, evaluates and adjudicates the resulting concerns, and emits a verdict plus resumable artifacts. The current repository also contains a schema-first test-maturity/evidence toolchain and Claude Code hook processes used to enforce pipeline safety.

## Architecture at a Glance

The primary runtime begins at the `adversarial-spec` console entry declared in `pyproject.toml:48`, resolving to `debate.main` at `skills/adversarial-spec/scripts/debate.py:1623`. The CLI parses spec, model, profile, session, pipeline-gate, and gauntlet options. It resolves providers and credentials through `providers.py`, optionally preflights models, then sends independent calls through `models.py`. The model layer supports CLI subprocess adapters and LiteLLM/Bedrock paths, returning `ModelResponse` objects and updating a thread-safe token tracker.

Debate output can be checkpointed and resumed through `session.py`. A gauntlet request enters `gauntlet/orchestrator.py:205`, which resolves prompts/adversaries and runs a sequence of internal phases: attack generation, synthesis/filtering, clustering, tiered evaluation, rebuttal, adjudication, and final-boss verdict. Typed dataclasses in `gauntlet/core_types.py` are the shared contract. `gauntlet/persistence.py` stores checkpoints and run manifests behind FileLock and integrity hashes; raw model results and phase artifacts remain file-backed so a partial run can resume.

The pre-gauntlet subsystem checks whether a spec is compatible with the repository before hostile review. It loads `[tool.adversarial-spec.compatibility]` from `pyproject.toml`, gathers git/system context, discovers relevant services, runs configured build/schema/validation commands, and returns typed status/exit outcomes. This path is secondary to the debate CLI but can block gauntlet entry when baseline drift is detected.

The newer evidence layer is deliberately schema-first. `tmr_schema.py` defines strict `TestMaturityRecord` validation; `tmr_compile_step.py` turns candidate prose/accessors into confirmed registry records and a derived prose view. `validation_emission.py` manages a locked ledger and a JSON `Envelope` boundary for row normalization, digest assembly, Telegram reply parsing, system-validation evidence, self-check, and stale-batch status. `provenance_journal.py` provides ordered multi-file locks, expected-coordinate checks, append-only transitions, and atomic registry/journal/index writes. `phase8_promotion.py`, `criticality_classifier.py`, and `tcov_liveness.py` consume these contracts to decide whether implementation evidence is sufficient for close.

The `.claude/hooks/` directory is a separate process boundary. Claude Code invokes `codex_pretool_combined.py` and individual hooks with JSON on stdin. Safety hooks classify commands and payloads; pipeline hooks detect roles, inject continuation/status messages, and optionally write activity or notification records. They communicate via stdout and intentionally do not import the runtime skill modules.

## Primary Data Flows

### Debate round

Spec text and CLI/profile input enter `debate.py:525-611`, are converted into model routes by `parse_models` at `debate.py:757`, validated at `debate.py:1312`, then sent through `models.call_models_parallel` at `models.py:1114`. Responses are parsed into critique/spec/task shapes and written to output/session/Telegram surfaces by `debate.py:1227` and `session.py:45-133`.

### Gauntlet verdict

The spec enters `run_gauntlet` at `gauntlet/orchestrator.py:205`. Adversary calls produce `Concern` records, later phases cluster and evaluate them, rebuttals and adjudication update disposition, and the final boss produces a `GauntletResult`. Persistence writes checkpoint envelopes, run manifests, raw responses, stats, medals, and the spec copy through `gauntlet/persistence.py:469-629`.

### Test maturity and validation evidence

Candidate records are compiled and assigned stable `tmr_uid` values by `tmr_compile_step.py:64-249`, then validated by `tmr_schema.py:377`. Validation commands mutate a locked ledger at `validation_emission.py:1337`, assemble and parse bounded batches, record evidence, and emit an `Envelope` from `validation_emission.py:3423`. Provenance updates take ordered locks and atomically update the registry/journal/index at `provenance_journal.py:581-596`.

### Hook decision

A Claude Code event enters `codex_pretool_combined.main` at `.claude/hooks/codex_pretool_combined.py:57`. It invokes configured hook modules, which may deny/warn/allow or emit a system message. The combined result is returned on stdout; notification and activity logging are optional side effects, not authoritative pipeline state.

## Key Architectural Decisions

- **File-backed resumability:** checkpoints, manifests, ledgers, and journals are inspectable and recoverable without a daemon.
- **Typed phase contracts:** dataclasses/Pydantic models centralize cross-module fields and make validation failures explicit.
- **Integrity + locking:** FileLock, content hashes, atomic replacement, and expected-coordinate checks protect concurrent or stale writers.
- **Parallel model calls:** ThreadPoolExecutor reduces wall-clock time; token accounting is protected by a lock.
- **Schema-first evidence:** TMR JSON is authoritative, while Markdown/prose views are derived.
- **Process-separated hooks:** safety/coordination hooks use stdin/stdout protocols and stay outside runtime skill imports.

## Non-Obvious Things

- The root `adversarial_spec` path is a symlink to the canonical source directory. Packaging and direct imports therefore depend on the source layout, not a conventional root package directory.
- The top-level debate CLI and `gauntlet` CLI are both live surfaces with divergent flag names/defaults.
- `python-dotenv` is declared, but provider behavior is primarily environment-name checks and JSON profile/config reads.
- Large `.adversarial-spec/` session/spec artifacts, generated reports, caches, and historical Gemini bundles are not runtime architecture components.
- The current source includes both the established debate/gauntlet runtime and a validation-leg/test-maturity subsystem; the latter is not simply a gauntlet subphase.

## Component Map

| Component | Purpose | Key Entry |
|-----------|---------|-----------|
| Debate CLI | top-level parsing, gates, critique orchestration | `main()` at `debate.py:1623` |
| Models and providers | model adapters, config, credentials, cost | `call_models_parallel()` at `models.py:1114` |
| Gauntlet pipeline | adversary-to-verdict processing | `run_gauntlet()` at `gauntlet/orchestrator.py:205` |
| Gauntlet persistence | checkpoint/run/stat/medal storage | `save_checkpoint()` at `gauntlet/persistence.py:560` |
| Pre-gauntlet | compatibility/alignment checks | `run_pre_gauntlet()` at `pre_gauntlet/orchestrator.py:207` |
| TMR schema/compiler | typed registry and prose derivation | `compile_tmr_records()` at `tmr_compile_step.py:64` |
| Validation emission | locked ledger and evidence protocol | `main()` at `validation_emission.py:3423` |
| Provenance and promotion | lineage, liveness, Phase 8 close | `ProvenanceJournalWriter` at `provenance_journal.py:112` |
| Harness hooks | Claude Code safety/coordination boundary | `main()` at `.claude/hooks/codex_pretool_combined.py:57` |
| Plan analysis | dependency semantics and concern parsing | `analyze_plan()` at `dependency_semantics.py:82` |
