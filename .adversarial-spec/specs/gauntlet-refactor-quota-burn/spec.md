# Specification: Refactor gauntlet.py into gauntlet/ Package + Quota Burn Fixes

> **Version:** 1.0 | **Status:** gauntlet_complete
> **Spec Hash:** d453f1d84d77 | **Git Base:** 0eb7ad9 | **Branch:** main
> **Debate:** 2 rounds (Codex 5.4 + Gemini 3 Pro) | **Gauntlet:** 9 adversaries, 75->42->23 concerns
> **Created:** 2026-03-20 | **Updated:** 2026-03-21

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Architecture Overview](#3-architecture-overview)
4. [Data Model](#4-data-model)
5. [Module Specifications](#5-module-specifications)
6. [API Contracts](#6-api-contracts)
7. [Prompt Templates](#7-prompt-templates)
8. [Persistence Specification](#8-persistence-specification)
9. [CLI Specification](#9-cli-specification)
10. [Error Contract](#10-error-contract)
11. [Timeout Policy](#11-timeout-policy)
12. [Security Considerations](#12-security-considerations)
13. [Concurrency Model](#13-concurrency-model)
14. [Testing Specification](#14-testing-specification)
15. [Execution Steps](#15-execution-steps)
16. [Verification Strategy](#16-verification-strategy)
17. [Migration Guide](#17-migration-guide)
18. [Quota Burn Fixes](#18-quota-burn-fixes)
19. [Decision Journal](#19-decision-journal)
20. [Debate Dispositions](#20-debate-dispositions)
21. [Gauntlet Dispositions](#21-gauntlet-dispositions)
22. [Scope Exclusions](#22-scope-exclusions)
- [Appendix A: Source Line Mapping](#appendix-a-source-line-mapping)
- [Appendix B: Commit Strategy](#appendix-b-commit-strategy)
- [Appendix C: Gauntlet Run Statistics](#appendix-c-gauntlet-run-statistics)

---

## 1. Executive Summary

Refactor `scripts/gauntlet.py` (4087 lines — the largest file in the codebase by 2-3x) into a 16-file `scripts/gauntlet/` package. The refactor extracts as-is except for 6 targeted fixes from the Quota Burn Incident. The external import surface (5 symbols consumed by `debate.py`) is unchanged.

**Inputs:** Single monolith file, 5 known defects, 4 applied hotfixes.
**Outputs:** 16-file package, 6 defect fixes, 10 new pytest tests, 3 new CLI flags.
**Constraints:** Zero breaking changes to `debate.py` imports, extract-as-is for phase internals.

### Getting Started

After the refactor, validate the system works:
```bash
uv sync --dev                                        # install deps (adds filelock)
uv run pytest && uvx ruff check                      # tests + lint
uv run debate gauntlet --list-adversaries             # CLI loads, package wired
echo "# Test" > /tmp/test.md
cat /tmp/test.md | uv run debate gauntlet \
  --gauntlet-adversaries paranoid_security \
  --timeout 300 --unattended                          # one-adversary live smoke test
```

For standalone entry point (secondary): `PYTHONPATH=skills/adversarial-spec/scripts uv run python -m gauntlet --list-adversaries`

---

## 2. Problem Statement

### 2.1 Structural Problem

`gauntlet.py` concentrates the entire 7-phase adversarial pipeline, all data classes, model dispatch, stats/medals/persistence, report formatting, and a standalone CLI into a single file. Both our architecture analysis (FIND-002) and Gemini's review (AD-2) recommend splitting it into a package.

### 2.2 Quota Burn Incident

A production gauntlet run burned excessive API quota due to 5 behavioral defects:

| # | Defect | Root Cause | Impact |
|---|--------|-----------|--------|
| 1 | **Ignored timeouts** | 13 hardcoded `timeout=60/120/300/600` defaults scattered across phase functions | CLI `--timeout` flag is overridden by function defaults in most phases |
| 2 | **Silent clustering fallback** | `except Exception as e: print(warning)` at line 2889 | Clustering failure silently falls back to no dedup, pushing 100% raw concerns to expensive evaluation |
| 3 | **No resume** | Zero checkpoint-based resume capability | Killing or crashing a run loses ALL previous API calls |
| 4 | **Useless dedup-stats** | `dedup-stats.json` is write-only — never read by any consumer | Diagnosis after quota burn is impossible |
| 5 | **False documentation** | `05-gauntlet.md` claims `--codex-reasoning` is a GLOBAL flag | Only attacks use it; evals use a hardcoded default |

### 2.3 Process Failure

Additionally, the process of writing this spec itself exposed a 6th defect: session artifacts (session-state.json, session file, manifest) were not created before the first debate round. This is the same failure class as the zombie pointer bug (Feb 9) and execution plan not persisted (Feb 13).

### 2.4 Current State

**4 hotfixes already applied to gauntlet.py** (not yet committed):
- Phase 2 synthesis: `timeout=120` -> `timeout=timeout`
- Phase 3 filtering: `timeout=60` -> `timeout=timeout`
- Phase 3.5 clustering: `timeout=60` -> `timeout=timeout`
- Phase 7 Final Boss: `timeout=600` -> `timeout=max(timeout, 600)`

---

## 3. Architecture Overview

### 3.1 Target Package Structure

```
scripts/gauntlet/
├── __init__.py              # 5 public symbols (matches current debate.py imports)
├── __main__.py              # `from gauntlet.cli import main; main()` — enables `python -m gauntlet`
├── core_types.py            # All dataclasses, enums, verdict normalization, GauntletConfig, CheckpointMeta
├── model_dispatch.py        # call_model(), select_*_model(), rate limiting, model name validation
├── persistence.py           # Atomic JSON IO, checkpoint save/load, run manifests, stats, runs DB
├── medals.py                # Medal calculation, generation, saving, leaderboard
├── reporting.py             # format_gauntlet_report(), leaderboard, synergy, run manifest formatting
├── phase_1_attacks.py       # generate_attacks()
├── phase_2_synthesis.py     # generate_big_picture_synthesis() + BIG_PICTURE_PROMPT
├── phase_3_filtering.py     # filter + cluster + GauntletClusteringError (NO silent fallback)
├── phase_4_evaluation.py    # evaluate_concerns(), evaluate_concerns_multi_model()
├── phase_5_rebuttals.py     # run_rebuttals() + REBUTTAL_PROMPT
├── phase_6_adjudication.py  # final_adjudication()
├── phase_7_final_boss.py    # run_final_boss_review()
├── orchestrator.py          # run_gauntlet() — phase sequencing, --resume, --unattended
└── cli.py                   # main() argparse entry point (standalone)
```

### 3.2 Import Surface (unchanged)

`debate.py:80-86` imports exactly 5 symbols — this is the ONLY external consumer:
```python
from gauntlet import (
    ADVERSARIES,            # re-exported from adversaries.py
    format_gauntlet_report, # reporting.py
    get_adversary_leaderboard, # reporting.py
    get_medal_leaderboard,  # medals.py
    run_gauntlet,           # orchestrator.py
)
```

### 3.3 Dependency Graph (no cycles)

```
adversaries.py, models.py, providers.py  [external, unchanged]
         |
   core_types.py  (GauntletConfig, GauntletClusteringError, all dataclasses)
         |
   model_dispatch.py  (model name validation, call_model reads config.timeout)
         |
   persistence.py  (filelock, run manifest, resume loader)
         |
   medals.py    (imports persistence, NOT reporting)
   reporting.py (imports medals + persistence — ONE-WAY, medals never imports reporting)
         |
   phase_1..7 (each reads GauntletConfig for timeout/reasoning — NO hardcoded defaults)
         |
   orchestrator.py (imports all phases + persistence + medals, builds GauntletConfig)
         |
   cli.py (imports orchestrator + reporting + persistence + medals)
         |
   __init__.py (imports 5 public symbols)
```

### 3.4 Blast Zone

| File | Lines | Role |
|------|-------|------|
| `scripts/gauntlet.py` | 4087 | REPLACED — becomes `scripts/gauntlet/` package (16 files) |
| `scripts/debate.py` | ~1100 | MODIFIED — new CLI flags wired to `run_gauntlet()` (lines 80-86 import surface, ~458 argparse, ~989 call site) |
| `scripts/models.py` | ~900 | MODIFIED — `threading.Lock` added to `CostTracker.add()` |
| `phases/05-gauntlet.md` | ~400 | MODIFIED — false claims corrected |
| `pyproject.toml` | ~60 | MODIFIED — `filelock==3.16.1` dependency added |

---

## 4. Data Model

### 4.1 Enums

```python
class FinalBossVerdict(str, Enum):
    """Verdict from the Final Boss review."""
    PASS = "pass"           # Proceed to implementation
    REFINE = "refine"       # Address concerns, then proceed
    RECONSIDER = "reconsider"  # Re-evaluate approach before proceeding
```

### 4.2 Core Dataclasses (existing — extracted as-is)

```python
@dataclass
class Concern:
    """A single concern raised by an adversary about the spec."""
    adversary: str          # adversary key (e.g., "paranoid_security")
    text: str               # full concern text (markdown)
    severity: str = "medium"  # "low", "medium", "high", "critical"
    id: str = ""            # auto-generated via generate_concern_id() from adversaries.py
    source_model: str = ""  # model that generated this concern

    def __post_init__(self):
        """Auto-generate ID if not provided."""
        if not self.id:
            from adversaries import generate_concern_id
            self.id = generate_concern_id(self.adversary)


@dataclass
class Evaluation:
    """Evaluation verdict for a concern."""
    concern: Concern
    verdict: str            # "dismissed", "accepted", "acknowledged", "deferred"
    reasoning: str          # justification for the verdict

    def __post_init__(self):
        """Normalize verdict to canonical form."""
        self.verdict = normalize_verdict(self.verdict)


@dataclass
class Rebuttal:
    """An adversary's rebuttal to a dismissal."""
    evaluation: Evaluation
    response: str           # full rebuttal text
    sustained: bool         # True if rebuttal challenges the dismissal


@dataclass
class BigPictureSynthesis:
    """Phase 2: Holistic synthesis of all concerns."""
    total_concerns: int
    unique_texts: int
    real_issues: list[str]          # 2-4 things that actually matter most
    hidden_connections: list[str]   # cross-adversary connections
    whats_missing: list[str]        # blind spots
    meta_concern: str               # one parent concern
    high_signal: list[str]          # 2-3 concerns deserving most careful review
    raw_response: str               # full model response


@dataclass
class GauntletResult:
    """Complete result from a gauntlet run."""
    concerns: list[Concern]                     # post-filtering, pre-clustering
    evaluations: list[Evaluation]               # expanded (attributed to original members)
    rebuttals: list[Rebuttal]
    final_concerns: list[Concern]               # technical + UX concerns
    adversary_model: str                        # comma-joined attack model names
    eval_model: str                             # comma-joined eval model names
    total_time: float                           # seconds
    total_cost: float                           # USD
    final_boss_result: Optional[FinalBossResult] = None
    raw_concerns: Optional[list[Concern]] = None          # before filtering
    dropped_concerns: Optional[list[Concern]] = None      # dropped by filtering
    spec_hash: Optional[str] = None
    adversary_timing: Optional[dict[str, float]] = None   # seconds per adversary
    big_picture: Optional[BigPictureSynthesis] = None
    clustered_concerns: Optional[list[Concern]] = None    # representatives after clustering
    clustered_evaluations: Optional[list[Evaluation]] = None
    cluster_members: Optional[dict[str, list[Concern]]] = None
    concerns_path: Optional[str] = None  # NEW: path to saved concerns JSON

    def get_adversary_stats(self) -> dict[str, dict]:
        """Compute per-adversary statistics from evaluations."""
        ...

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        ...


@dataclass
class Medal:
    """Award for exceptional adversary performance."""
    name: str
    adversary: str
    description: str
    concern_text: str
    spec_hash: str
    run_id: str
    awarded_at: str = ""

    def to_dict(self) -> dict: ...


@dataclass
class ExplanationMatch:
    """A match between a concern and a previously resolved explanation."""
    explanation_id: str
    pattern: str
    explanation: str
    confidence: float
    matched_concern_text: str


@dataclass
class DismissalReviewStats:
    """Telemetry from Final Boss's review of dismissed simplification concerns."""
    dismissed_simplifications_reviewed: int
    dismissals_flagged_invalid: int
    invalid_dismissal_ids: list[str]

    def review_yield_rate(self) -> float: ...
    def to_dict(self) -> dict: ...


@dataclass
class FinalBossResult:
    """Result from Phase 7 Final Boss UX review."""
    verdict: FinalBossVerdict
    response: str
    model: str
    concerns: list[str] = field(default_factory=list)
    reconsider_reason: str = ""
    alternate_approaches: list[str] = field(default_factory=list)
    process_meta_report: str = ""
    self_meta_report: str = ""
    dismissal_review_stats: Optional[DismissalReviewStats] = None

    def approved(self) -> bool:
        return self.verdict == FinalBossVerdict.PASS
```

### 4.3 NEW Dataclasses

```python
@dataclass
class GauntletConfig:
    """
    Central configuration object passed to every phase function.
    Replaces 13 hardcoded timeout/reasoning defaults scattered across the monolith.
    Built once at the top of run_gauntlet() from CLI parameters.

    QUOTA BURN FIX 1: This is the primary fix for ignored CLI flags.
    """
    timeout: int = 300
    attack_codex_reasoning: str = "low"
    eval_codex_reasoning: str = "xhigh"     # NEW
    auto_checkpoint: bool = False
    resume: bool = False
    unattended: bool = False


class GauntletClusteringError(Exception):
    """
    Raised when Phase 3 clustering fails after retry.
    Halts pipeline — NO silent fallback to singleton clusters.
    QUOTA BURN FIX 2.
    """
    pass


class GauntletExecutionError(Exception):
    """
    Raised when any phase fails in a way that should halt with exit code 3.
    """
    pass


@dataclass
class CheckpointMeta:
    """Metadata envelope for checkpoint files."""
    schema_version: int = 2
    spec_hash: str = ""
    config_hash: str = ""
    phase: str = ""
    created_at: str = ""
    data_hash: str = ""


@dataclass
class PhaseMetrics:
    """
    Per-phase telemetry for the run manifest.
    Replaces the write-only dedup-stats.json.
    QUOTA BURN FIX 4.
    """
    phase: str
    phase_index: int
    status: str             # "completed" | "failed" | "skipped_resume"
    duration_seconds: float
    input_tokens: int
    output_tokens: int
    models_used: list[str]
    config_snapshot: dict
    error: Optional[str] = None
    spec_hash: str = ""
```

### 4.4 Verdict Normalization

```python
_VERDICT_NORMALIZE = {
    "dismiss": "dismissed", "dismissed": "dismissed", "reject": "dismissed",
    "accept": "accepted", "accepted": "accepted",
    "acknowledge": "acknowledged", "acknowledged": "acknowledged",
    "defer": "deferred", "deferred": "deferred",
}

def normalize_verdict(raw: str) -> str:
    """Map 8 raw verdict strings to 4 canonical forms."""
    return _VERDICT_NORMALIZE.get(raw.lower().strip(), raw.lower().strip())
```

---

## 5. Module Specifications

### 5.1 `__init__.py`

```python
"""Adversarial Gauntlet — 7-phase adversarial spec review pipeline."""
from gauntlet.orchestrator import run_gauntlet
from gauntlet.reporting import format_gauntlet_report, get_adversary_leaderboard
from gauntlet.medals import get_medal_leaderboard
from adversaries import ADVERSARIES

__all__ = [
    "ADVERSARIES",
    "format_gauntlet_report",
    "get_adversary_leaderboard",
    "get_medal_leaderboard",
    "run_gauntlet",
]
```

### 5.2 `__main__.py`

```python
from gauntlet.cli import main
main()
```

### 5.3 `core_types.py`

**Source lines:** 33-37, 99-116, 121-340, 1393-1399, 1580-1627.
**New additions:** GauntletConfig, GauntletClusteringError, GauntletExecutionError, CheckpointMeta, PhaseMetrics, `concerns_path` on GauntletResult.
**Imports:** `dataclasses`, `enum`, `typing`. NO gauntlet-internal imports.

### 5.4 `model_dispatch.py`

**Source lines:** 2145-2170, 2347-2531.

| Function | Signature |
|----------|-----------|
| `call_model()` | `(model, system_prompt, user_message, timeout=300, codex_reasoning=DEFAULT_CODEX_REASONING) -> tuple[str, int, int]` |
| `running_in_claude_code()` | `() -> bool` |
| `select_adversary_model()` | `() -> str` |
| `select_eval_model()` | `() -> str` |
| `select_gauntlet_models()` | `(adversary_override=None, eval_override=None) -> tuple[str, str]` |
| `get_rate_limit_config()` | `(model_name) -> tuple[int, int]` |
| `_get_model_provider()` | `(model) -> str` |
| `get_available_eval_models()` | `() -> list[str]` |
| **NEW** `_validate_model_name()` | `(model: str) -> None` — blocklist validation |

### 5.5 `persistence.py`

**Source lines:** 384-526, 588-632, 1246-1391.

**Existing functions (extracted as-is):**
`load_adversary_stats`, `save_adversary_stats`, `update_adversary_stats`, `save_gauntlet_run`, `list_gauntlet_runs`, `load_gauntlet_run`, `load_resolved_concerns`, `save_resolved_concerns`, `get_spec_hash`, `add_resolved_concern`, `calculate_explanation_confidence`, `record_explanation_match`, `verify_explanation`.

**NEW functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `_load_json_safe()` | `(path: Path) -> Optional[Any]` | Consolidated JSON load with fallback |
| `_write_json_atomic()` | `(path: Path, data: Any) -> None` | Atomic write via temp + os.replace() |
| `_serialize_dataclass()` | `(obj) -> dict` | Canonical dataclass serialization |
| `get_config_hash()` | `(config, attack_models, eval_models, adversaries, flags) -> str` | SHA-256 config fingerprint |
| `save_checkpoint()` | `(path, phase, data, spec_hash, config_hash) -> None` | Write checkpoint with envelope |
| `load_partial_run()` | `(spec_hash, config, attack_models, eval_models, adversaries, flags) -> dict` | Resume loader |
| `save_partial_clustering()` | `(spec_hash, concerns, config_hash) -> None` | Crash recovery for Phase 3.5 |
| `save_run_manifest()` | `(manifest, spec_hash) -> str` | Create run manifest file |
| `update_run_manifest()` | `(manifest_path, phase_metrics) -> None` | Append phase metrics |
| `load_run_manifest()` | `(hash_prefix) -> Optional[dict]` | Load for --show-manifest |
| `format_path_safe()` | `(base_dir, filename) -> Path` | Path-traversal guard |

**New dependency:** `filelock==3.16.1` (pinned).

### 5.6 `medals.py`

**Source lines:** 774-1095, 1181-1244.

| Function | Signature |
|----------|-----------|
| `_get_concern_keywords()` | `(text) -> set[str]` |
| `_concerns_are_similar()` | `(concern1, concern2, threshold=0.3) -> bool` |
| `calculate_medals()` | `(result, spec_hash, run_id) -> list[Medal]` |
| `generate_medal_report()` | `(medal) -> str` |
| `save_medal_reports()` | `(medals) -> str` |
| `format_medals_for_display()` | `(medals) -> str` |
| `get_medal_leaderboard()` | `() -> str` |

### 5.7 `reporting.py`

**Source lines:** 634-772, 1097-1179, 3710-3828.

| Function | Signature |
|----------|-----------|
| `format_gauntlet_report()` | `(result: GauntletResult) -> str` |
| `get_adversary_leaderboard()` | `() -> str` |
| `get_adversary_synergy()` | `(result) -> dict[str, dict]` |
| `format_synergy_report()` | `(synergy) -> str` |
| **NEW** `format_run_manifest()` | `(manifest: dict) -> str` |

### 5.8 Phase Modules (1-7)

Each phase module follows this pattern:
1. Extracted from monolith with its prompt constants
2. **All hardcoded timeout/reasoning defaults stripped** — replaced with `config: GauntletConfig` parameter
3. Phase internals NOT refactored (extract-as-is)
4. Each module imports `GauntletConfig` from `core_types` and relevant functions from `model_dispatch`

#### 5.8.1 `phase_1_attacks.py`

**Source lines:** 2528-2728.
**Imports from gauntlet:** `core_types.Concern`, `core_types.GauntletConfig`, `model_dispatch.call_model`, `model_dispatch.get_rate_limit_config`, `model_dispatch._get_model_provider`
**External imports:** `adversaries.ADVERSARIES`

| Function | Current Signature | After Refactor |
|----------|------------------|----------------|
| `generate_attacks()` | `(spec, adversaries, models, timeout=300, codex_reasoning="low") -> tuple[list[Concern], dict[str, float], dict[str, str]]` | `(spec, adversaries, models, config: GauntletConfig) -> tuple[list[Concern], dict[str, float], dict[str, str]]` |

**Behavior:**
- Accepts `models` as `list[str] | str` (normalizes to list)
- Creates `adversary × model` cross-product pairs
- Groups pairs by provider for rate-limited batching
- Uses `ThreadPoolExecutor(max_workers=min(32, len(pairs)))` for parallel dispatch
- Per pair: constructs system/user prompts (see §7.1), calls `call_model(model, system, user, config.timeout, config.attack_codex_reasoning)`
- Parses numbered list response into `Concern` objects with sub-bullet grouping
- Returns `(concerns, timing_dict, raw_responses_dict)` — timing keyed by `"{adversary}@{model}"`
- **Error handling:** Individual adversary failures print warning, return empty for that pair (no halt)

**Internal functions (stay private):**
- `run_adversary_with_model(adversary_key, model)` — inner closure that produces concerns for one pair
- `collect_result(future, adv_key, model)` — accumulates results from futures
- `flush_concern()` — parser helper for numbered list grouping

#### 5.8.2 `phase_2_synthesis.py`

**Source lines:** 1630-1709.
**Imports from gauntlet:** `core_types.Concern`, `core_types.BigPictureSynthesis`, `core_types.GauntletConfig`
**Note:** Uses inline model dispatch (litellm `completion()` directly), NOT `call_model()`. Extract as-is.

| Function | Current Signature | After Refactor |
|----------|------------------|----------------|
| `generate_big_picture_synthesis()` | `(concerns, model, timeout=120) -> BigPictureSynthesis` | `(concerns, model, config: GauntletConfig) -> BigPictureSynthesis` |

**Behavior:**
- Groups concerns by adversary for prompt context
- Uses `BIG_PICTURE_PROMPT` (module-level constant, see §7.2)
- Calls litellm `completion()` directly with `max_tokens=2000`, `temperature=0.3`
- Parses response by scanning for section headers (`REAL_ISSUES:`, `HIDDEN_CONNECTIONS:`, etc.)
- Returns `BigPictureSynthesis` dataclass
- **Error handling:** On failure, returns synthesis with `raw_response` containing the error

**Constants:** `BIG_PICTURE_PROMPT` (see §7.2)

#### 5.8.3 `phase_3_filtering.py`

**Source lines:** 2380-2940 (filtering + clustering + expansion).
**Imports from gauntlet:** `core_types.Concern`, `core_types.Evaluation`, `core_types.GauntletConfig`, `core_types.GauntletClusteringError`, `model_dispatch.call_model`, `model_dispatch.get_rate_limit_config`, `persistence.save_partial_clustering`

| Function | Current Signature | After Refactor |
|----------|------------------|----------------|
| `match_concern_to_explanation()` | `(concern, spec_hash, model, timeout=60)` | `(concern, spec_hash, model, config: GauntletConfig)` |
| `filter_concerns_with_explanations()` | `(concerns, spec_hash, model, timeout=60) -> tuple[list, list]` | `(concerns, spec_hash, model, config: GauntletConfig) -> tuple[list, list]` |
| `choose_clustering_model()` | `(attack_models, fallback) -> str` | unchanged (no timeout) |
| `_normalize_concern_text()` | `(text) -> str` | unchanged (pure function) |
| `cluster_concerns_with_provenance()` | `(concerns, model, timeout=60) -> tuple[list[Concern], dict[str, list[Concern]]]` | `(concerns, model, config: GauntletConfig) -> tuple[list[Concern], dict[str, list[Concern]]]` |
| `expand_clustered_evaluations()` | `(evaluations, cluster_members) -> list[Evaluation]` | unchanged (pure function) |

**QUOTA BURN FIX 2 — Nuke silent catch-all in `cluster_concerns_with_provenance()`:**

```python
# BEFORE (line 2889-2890):
except Exception as e:
    print(f"  Warning: Clustering failed ({e}); falling back to exact dedup only",
          file=sys.stderr)
    # Falls through silently — 100% raw concerns hit expensive eval

# AFTER:
except Exception as e:
    # Retry once with backoff for transient API failures (Codex R2)
    print(f"  Clustering failed ({e}), retrying in 2s...", file=sys.stderr)
    time.sleep(2)
    try:
        response, in_tokens, out_tokens = call_model(
            model=model,
            system_prompt=system_prompt,
            user_message=user_prompt,
            timeout=config.timeout,
        )
        # ... parse clusters same as above ...
    except Exception as e2:
        # Save partial state for crash recovery before halting
        save_partial_clustering(spec_hash, concerns, config_hash)
        raise GauntletClusteringError(
            f"Clustering failed after retry: {e2}. Partial state saved to "
            f".adversarial-spec-gauntlet/clustered-concerns-*.json"
        )
```

**Clustering algorithm (2-step):**
1. **Exact dedup** (free, deterministic): Normalize text → group by normalized form → pick first as representative
2. **Semantic clustering** (LLM): If >1 candidate after exact dedup, call cheap model with clustering prompt (§7.3) → parse JSON clusters → merge groups

**`choose_clustering_model()` heuristic:** Prefer models with "flash", "mini", "haiku", "small", "low" in name. Fallback: first attack model.

#### 5.8.4 `phase_4_evaluation.py`

**Source lines:** 2986-3103, 2145-2340.
**Imports from gauntlet:** `core_types.Concern`, `core_types.Evaluation`, `core_types.GauntletConfig`, `model_dispatch.call_model`, `model_dispatch.get_rate_limit_config`, `model_dispatch.get_available_eval_models`
**External imports:** `adversaries.ADVERSARIES`

| Function | Current Signature | After Refactor |
|----------|------------------|----------------|
| `evaluate_concerns()` | `(spec, concerns, model, timeout=300) -> list[Evaluation]` | `(spec, concerns, model, config: GauntletConfig) -> list[Evaluation]` |
| `evaluate_concerns_multi_model()` | `(spec, concerns, models, batch_size=15, timeout=300) -> list[Evaluation]` | `(spec, concerns, models, config: GauntletConfig, batch_size=15) -> list[Evaluation]` |
| `get_available_eval_models()` | `() -> list[str]` | unchanged (no timeout) |

**`evaluate_concerns()` behavior:**
- Builds system prompt with per-adversary response protocols from `ADVERSARIES` registry (see §7.4)
- Calls `call_model(model, system, user, config.timeout)` — uses `config.eval_codex_reasoning` for Codex models
- Parses JSON response: `{"evaluations": [{"concern_index": N, "verdict": "...", "reasoning": "..."}]}`
- JSON extraction: finds first `{` to last `}` (handles markdown-wrapped responses)
- **Error handling:** On parse failure or API error, defers all concerns (`verdict="deferred"`)

**`evaluate_concerns_multi_model()` behavior:**
- Uses up to 3 models for diversity
- Splits concerns into batches of `batch_size` (default 15)
- Runs all batches for each model concurrently (rate-limited per provider)
- Different models run fully in parallel (independent rate limits)
- **Consensus algorithm:** For each concern, collects verdicts from all models → majority wins, ties resolved by strictest verdict, reasoning merged from all models with per-model attribution
- Falls back to single-model if only 1 model available

#### 5.8.5 `phase_5_rebuttals.py`

**Source lines:** 3111-3193.
**Imports from gauntlet:** `core_types.Evaluation`, `core_types.Rebuttal`, `core_types.GauntletConfig`, `model_dispatch.call_model`, `model_dispatch.get_rate_limit_config`
**External imports:** `adversaries.ADVERSARIES`

| Function | Current Signature | After Refactor |
|----------|------------------|----------------|
| `run_rebuttals()` | `(evaluations, model, timeout=300) -> list[Rebuttal]` | `(evaluations, model, config: GauntletConfig) -> list[Rebuttal]` |

**Behavior:**
- Filters to `verdict == "dismissed"` evaluations only
- For each dismissed evaluation: constructs adversary-personalized rebuttal prompt (see §7.5)
- Runs rebuttals in rate-limited batches using `ThreadPoolExecutor(max_workers=len(batch))`
- Response parsing: checks for `"CHALLENGED:"` in uppercased response → `sustained=True`
- **Error handling:** Individual rebuttal failures print warning, skip that rebuttal (no halt)

**Constants:** `REBUTTAL_PROMPT` (see §7.5)

#### 5.8.6 `phase_6_adjudication.py`

**Source lines:** 3201-3283.
**Imports from gauntlet:** `core_types.Concern`, `core_types.Rebuttal`, `core_types.GauntletConfig`, `model_dispatch.call_model`

| Function | Current Signature | After Refactor |
|----------|------------------|----------------|
| `final_adjudication()` | `(spec, rebuttals, model, timeout=300) -> list[Concern]` | `(spec, rebuttals, model, config: GauntletConfig) -> list[Concern]` |

**Behavior:**
- Filters to `sustained=True` (challenged) rebuttals only
- Constructs adjudication prompt with original concern + dismissal + rebuttal (see §7.6)
- Calls `call_model(model, system, user, config.timeout)` — uses `config.eval_codex_reasoning` for Codex
- Parses JSON: `{"decisions": [{"challenge_index": N, "verdict": "upheld|overturned", "reasoning": "..."}]}`
- Returns list of overturned concerns (these survive to the final concerns list)
- **Error handling:** Conservative fallback — all challenged concerns survive on parse failure

#### 5.8.7 `phase_7_final_boss.py`

**Source lines:** 1811-2138.
**Imports from gauntlet:** `core_types.*` (Concern, Evaluation, FinalBossResult, FinalBossVerdict, DismissalReviewStats, GauntletConfig), `model_dispatch.select_eval_model`
**External imports:** `adversaries.FINAL_BOSS`

| Function | Current Signature | After Refactor |
|----------|------------------|----------------|
| `run_final_boss_review()` | `(spec, gauntlet_summary, accepted_concerns, dismissed_evaluations, timeout=600) -> FinalBossResult` | `(spec, gauntlet_summary, accepted_concerns, dismissed_evaluations, config: GauntletConfig) -> FinalBossResult` |

**Timeout:** `max(config.timeout, 600)` — Opus 4.6 with large context needs a floor.

**Model selection priority:**
1. `ANTHROPIC_API_KEY` set → `claude-opus-4-6`
2. Codex available → `codex/gpt-5.3-codex`
3. Fallback → `select_eval_model()`

**Behavior:**
- Builds dynamic user prompt with concern distribution, alternate approaches, dismissed simplifications (see §7.7)
- Dismissed simplification mining: scans `lazy_developer`, `prior_art_scout`, `information_flow_auditor` concerns for simplification keywords
- Calls model with `FINAL_BOSS["ux_architect"].persona` as system prompt
- Parses response: verdict → concerns → reconsider details → meta-reports → invalid dismissals
- Builds `DismissalReviewStats` from invalid dismissal parsing
- **Error handling:** Fallback to `REFINE` verdict with raw response as `reconsider_reason`

### 5.9 `orchestrator.py`

**Source lines:** 3290-3707.

**Primary API:**
```python
def run_gauntlet(
    spec: str,
    adversaries: Optional[list[str]] = None,
    adversary_model: Optional[str] = None,
    attack_models: Optional[list[str]] = None,
    eval_models: Optional[list[str]] = None,
    allow_rebuttals: bool = True,
    use_multi_model: bool = True,
    skip_filtering: bool = False,
    run_final_boss: bool = False,
    timeout: int = 300,
    attack_codex_reasoning: str = "low",
    eval_codex_reasoning: str = "xhigh",      # NEW
    resume: bool = False,                       # NEW
    unattended: bool = False,                   # NEW
) -> GauntletResult:
```

**Orchestration flow (pseudocode):**

```python
def run_gauntlet(...) -> GauntletResult:
    # ── Step 1: Build config ──
    config = GauntletConfig(
        timeout=timeout,
        attack_codex_reasoning=attack_codex_reasoning,
        eval_codex_reasoning=eval_codex_reasoning,
        auto_checkpoint=unattended,
        resume=resume,
        unattended=unattended,
    )

    # ── Step 2: Resolve models ──
    if attack_models:
        atk_models = attack_models          # explicit overrides legacy
    elif adversary_model:
        atk_models = [adversary_model]      # legacy single model
    else:
        atk_models = [select_adversary_model()]

    if eval_models:
        ev_models = eval_models
    elif use_multi_model:
        ev_models = get_available_eval_models()
    else:
        ev_models = [select_eval_model()]

    # ── Step 3: Early model validation (Gauntlet G-6: fail fast) ──
    for m in atk_models + ev_models:
        _validate_model_name(m)  # raises ValueError on bad name → exit 1

    # ── Step 4: Unattended enforcement (Gauntlet G-4) ──
    original_input = None
    if config.unattended:
        import builtins
        original_input = builtins.input
        builtins.input = lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("input() called in unattended mode")
        )

    try:
        # ── Step 5: Resume loader (QUOTA BURN FIX 3) ──
        spec_hash = get_spec_hash(spec)
        partial = {}
        if config.resume:
            partial = load_partial_run(spec_hash, config)
            # partial = {"phase_1": {...}, "phase_4": {...}, ...} or {}
            if not partial:
                print("No valid checkpoint found, starting fresh", file=sys.stderr)

        manifest_path = None  # built iteratively

        # ── Phase 1: Attacks ──
        if "phase_1" in partial:
            concerns = partial["phase_1"]["concerns"]
            timing = partial["phase_1"]["timing"]
            raw_responses = partial["phase_1"]["raw_responses"]
            # Check which adversaries already ran
            completed_advs = {c.adversary for c in concerns}
            missing_advs = [a for a in active_adversaries if a not in completed_advs]
            if missing_advs:
                new_concerns, new_timing, new_raw = generate_attacks(
                    spec, missing_advs, atk_models, config
                )
                concerns.extend(new_concerns)
                timing.update(new_timing)
                raw_responses.update(new_raw)
        else:
            concerns, timing, raw_responses = generate_attacks(
                spec, active_adversaries, atk_models, config
            )
        save_checkpoint("concerns", spec_hash, concerns, config)
        manifest_path = update_run_manifest(manifest_path, phase_1_metrics)

        # ── Phase 2: Big Picture Synthesis ──
        synthesis = generate_big_picture_synthesis(concerns, eval_model, config)
        manifest_path = update_run_manifest(manifest_path, phase_2_metrics)

        # ── Phase 3: Filtering ──
        if not skip_filtering:
            filtered, dropped = filter_concerns_with_explanations(
                concerns, spec_hash, eval_model, config
            )
        else:
            filtered, dropped = concerns, []
        manifest_path = update_run_manifest(manifest_path, phase_3_metrics)

        # ── Phase 3.5: Clustering ──
        clustered, cluster_members = cluster_concerns_with_provenance(
            filtered, clustering_model, config
        )
        if config.auto_checkpoint:
            save_checkpoint("clustered-concerns", spec_hash, clustered, config)
        manifest_path = update_run_manifest(manifest_path, phase_3_5_metrics)

        # ── Phase 4: Evaluation ──
        if "phase_4" in partial:
            # Validate concern set alignment before reusing
            saved_concern_ids = {e["concern_id"] for e in partial["phase_4"]["evaluations"]}
            current_concern_ids = {c.id for c in clustered}
            if saved_concern_ids == current_concern_ids:
                evaluations = partial["phase_4"]["evaluations"]  # reuse
            else:
                evaluations = evaluate(spec, clustered, ev_models, config)  # re-eval
        else:
            evaluations = evaluate(spec, clustered, ev_models, config)
        if config.auto_checkpoint:
            save_checkpoint("evaluations", spec_hash, evaluations, config)
        manifest_path = update_run_manifest(manifest_path, phase_4_metrics)

        # ── Phase 5: Rebuttals ──
        rebuttals = []
        if allow_rebuttals:
            rebuttals = run_rebuttals(evaluations, atk_models[0], config)
        manifest_path = update_run_manifest(manifest_path, phase_5_metrics)

        # ── Phase 6: Adjudication ──
        overturned = []
        if rebuttals and any(r.sustained for r in rebuttals):
            overturned = final_adjudication(spec, rebuttals, ev_models[0], config)
        manifest_path = update_run_manifest(manifest_path, phase_6_metrics)

        # ── Phase 7: Final Boss ──
        final_boss_result = None
        if run_final_boss:
            final_boss_result = run_final_boss_review(
                spec, gauntlet_summary, accepted, dismissed, config
            )
            if config.auto_checkpoint:
                save_checkpoint("final-boss", spec_hash, final_boss_result, config)
        manifest_path = update_run_manifest(manifest_path, phase_7_metrics)

        # ── Build result ──
        result = GauntletResult(
            concerns=filtered,
            evaluations=expanded_evals,
            rebuttals=rebuttals,
            final_concerns=accepted + overturned,
            concerns_path=f".adversarial-spec-gauntlet/concerns-{spec_hash[:8]}.json",
            # ... all other fields ...
        )
        save_stats(result)
        save_medals(result)
        return result

    except KeyboardInterrupt:
        if manifest_path:
            update_run_manifest(manifest_path, {"status": "interrupted"})
        sys.exit(130)
    finally:
        if original_input is not None:
            builtins.input = original_input
```

**Flag precedence:**
- `attack_models` overrides legacy `adversary_model`; `adversary_model` overrides auto-select
- `eval_models=None` → `get_available_eval_models()`; `use_multi_model=False` → `[select_eval_model()]`
- `unattended=True` → forbids `input()`, enables auto-checkpoint; Final Boss only runs when `run_final_boss=True`
- `resume=True` → load partial run; no-op if no valid checkpoint or config changed

**Resume skip logic (QUOTA BURN FIX 3):**
1. `load_partial_run(spec_hash, config)` reads checkpoint files from `.adversarial-spec-gauntlet/`
2. If `_meta.config_hash` doesn't match current config → discard, warn "Config changed"
3. Phase 1 partial: load concerns, diff adversary sets, only dispatch for missing adversaries
4. Phase 4 partial: validate concern IDs match current Phase 3 output; if mismatch → discard Phase 4, re-evaluate
5. No partial data → proceed normally (no error — resume of fresh spec is no-op)
6. **All return paths populate `concerns_path`** — including error/early-return paths

**Auto-checkpoint (`--unattended`) writes after:**
- Phase 1 (concerns) — always written regardless of unattended
- Phase 3.5 (clustering) — NEW, highest-cost crash failure mode (G-2)
- Phase 4 (evaluations) — NEW
- Phase 7 (final boss) — NEW

**KeyboardInterrupt handling:** Write manifest status `"interrupted"`, exit code 130.

### 5.10 `cli.py`

**Source lines:** 3836-4087.

**Existing CLI flags** (preserved): `--adversaries`, `--adversary-model`, `--attack-models`, `--eval-model`, `--no-rebuttals`, `--attack-codex-reasoning`, `--timeout`, `--json`, `--list-adversaries`, `--stats`, `--list-runs`, `--show-run`, `--pre-gauntlet`, `--doc-type`, `--spec-file`, `--report-path`.

**NEW CLI flags:** `--unattended`, `--resume`, `--eval-codex-reasoning`.

---

## 6. API Contracts

### 6.1 Primary API: `run_gauntlet()`

**Full signature** (14 parameters — preserves all current params, adds 3 new ones):
```python
def run_gauntlet(
    spec: str,                              # markdown spec text
    adversaries: Optional[list[str]] = None,  # adversary keys; None = all
    adversary_model: Optional[str] = None,    # LEGACY single attack model
    attack_models: Optional[list[str]] = None,  # multi-model attacks
    eval_models: Optional[list[str]] = None,    # multi-model evaluation
    allow_rebuttals: bool = True,             # enable Phase 5
    use_multi_model: bool = True,             # multi-model evaluation
    skip_filtering: bool = False,             # skip Phase 3 filtering
    run_final_boss: bool = False,             # enable Phase 7
    timeout: int = 300,                       # per-call timeout (seconds)
    attack_codex_reasoning: str = "low",      # Codex reasoning for attacks
    eval_codex_reasoning: str = "xhigh",      # NEW: Codex reasoning for eval/adjudication
    resume: bool = False,                      # NEW: resume from checkpoint
    unattended: bool = False,                  # NEW: no stdin + auto-checkpoint
) -> GauntletResult:
```

**Parameter behavior:**

| Parameter | Default | Behavior |
|-----------|---------|----------|
| `spec` | required | Markdown text of the specification to review |
| `adversaries` | `None` | When `None`, uses all keys from `ADVERSARIES` dict. When list, uses only those adversaries. Unknown keys print warning and skip. |
| `adversary_model` | `None` | **LEGACY.** Single attack model. Overridden by `attack_models` if both provided. Auto-selects via `select_adversary_model()` if both `None`. |
| `attack_models` | `None` | List of models for Phase 1 attacks. Creates adversary × model cross-product. Overrides `adversary_model`. |
| `eval_models` | `None` | List of models for Phase 4 evaluation. When `None` with `use_multi_model=True`, calls `get_available_eval_models()`. |
| `allow_rebuttals` | `True` | Enables Phase 5 (adversary rebuttals to dismissals). |
| `use_multi_model` | `True` | `True` → use multiple eval models; `False` → use single `select_eval_model()`. |
| `skip_filtering` | `False` | Skips Phase 3 explanation-based filtering (all concerns pass to clustering). |
| `run_final_boss` | `False` | Enables Phase 7 Final Boss UX review. When `False`, Phase 7 is skipped entirely. |
| `timeout` | `300` | Per-call timeout for all model calls. Stored in `GauntletConfig`. |
| `attack_codex_reasoning` | `"low"` | Reasoning effort for Codex attacks. Low is sufficient for adversary generation. |
| `eval_codex_reasoning` | `"xhigh"` | **NEW.** Reasoning effort for Codex evaluations/adjudication. High quality matters for verdicts. |
| `resume` | `False` | **NEW.** Load partial run from checkpoint files. No-op if no valid checkpoint exists. |
| `unattended` | `False` | **NEW.** Forbids `input()` (monkey-patches builtins) + enables auto-checkpoint after Phases 3.5, 4, 7. |

**Return value:** `GauntletResult` (see §4.2) — always has `concerns_path` populated (even on error paths).

**Flag precedence:**
1. `attack_models` > `adversary_model` > `select_adversary_model()` (auto)
2. `eval_models` > `get_available_eval_models()` (when `use_multi_model=True`) > `[select_eval_model()]` (when `use_multi_model=False`)
3. `unattended=True` implies `auto_checkpoint=True` + forbids `input()`
4. `resume=True` is a no-op if no valid checkpoint or config changed since last run

See §5.9 for full orchestration flow pseudocode.

### 6.2 debate.py Integration (Step 8.5)

**debate.py is the PRIMARY user entry point.** Users run `uv run debate gauntlet`, not `python -m gauntlet`.

**Import surface (unchanged — lines 80-86 of debate.py):**
```python
from gauntlet import (
    ADVERSARIES,
    format_gauntlet_report,
    get_adversary_leaderboard,
    get_medal_leaderboard,
    run_gauntlet,
)
```

**New flags added to debate.py gauntlet subcommand (~line 458):**

| Flag | Type | Default | Maps to | Notes |
|------|------|---------|---------|-------|
| `--gauntlet-resume` | store_true | False | `run_gauntlet(resume=True)` | **NOT `--resume`** — debate.py already has `--resume SESSION_ID` (G-1 CRITICAL) |
| `--unattended` | store_true | False | `run_gauntlet(unattended=True)` | Also implies auto-checkpoint |
| `--eval-codex-reasoning` | choices: minimal/low/medium/high/xhigh | "xhigh" | `run_gauntlet(eval_codex_reasoning=...)` | Matches DEFAULT_CODEX_REASONING |
| `--show-manifest` | optional str (hash prefix) | None | `persistence.load_run_manifest(hash)` → `reporting.format_run_manifest()` → print → exit(0) | Human-readable manifest viewer |

**Call site (~line 989 of debate.py) — add new args:**
```python
result = run_gauntlet(
    spec=spec_text,
    adversaries=adversary_list,
    attack_models=attack_model_list,
    eval_models=eval_model_list,
    allow_rebuttals=not args.no_rebuttals,
    use_multi_model=True,
    run_final_boss=args.final_boss,
    timeout=args.timeout,
    attack_codex_reasoning=args.codex_reasoning,
    eval_codex_reasoning=args.eval_codex_reasoning,  # NEW
    resume=args.gauntlet_resume,                      # NEW
    unattended=args.unattended,                       # NEW
)
```

**`--show-manifest` handler (before run_gauntlet call):**
```python
if args.show_manifest:
    from gauntlet.persistence import load_run_manifest
    from gauntlet.reporting import format_run_manifest
    manifest = load_run_manifest(args.show_manifest)
    if manifest:
        print(format_run_manifest(manifest))
    else:
        print(f"No manifest found for hash prefix: {args.show_manifest}", file=sys.stderr)
    sys.exit(0 if manifest else 1)
```

### 6.3 Standalone CLI: `python -m gauntlet`

Secondary entry point. Same flags as debate.py EXCEPT:
- Uses `--resume` (not `--gauntlet-resume`) — no session concept
- No `--show-manifest` (not worth duplicating — use debate.py)
- Requires `PYTHONPATH=skills/adversarial-spec/scripts` to resolve imports

---

## 7. Prompt Templates

All prompts are extracted as-is into their respective phase modules. Constants stay with their phases.

### 7.1 Attack Generation (Phase 1)

Stays in `phase_1_attacks.py`. Constructed per adversary/model pair:

**System prompt:**
```
You are an adversarial reviewer with this persona:

{adversary.persona}

Your job is to find problems with the specification below. Be aggressive.
Output a numbered list of concerns. Each concern should be a potential problem
you've identified. Don't hold back - even if you're not 100% sure, raise it.
```

**User prompt:**
```
Review this specification and identify all potential problems:

{spec}

Output your concerns as a numbered list. Be specific and cite parts of the spec.
```

**Response parsing:** Numbered list parser that:
1. Groups numbered items (e.g., `1. ...`, `2) ...`) with their sub-bullets
2. Joins continuation lines into a single concern
3. Deduplicates by exact text within each adversary/model pair
4. Warns on bare quotes (possible parse issue)

### 7.2 Big Picture Synthesis (Phase 2)

Stays in `phase_2_synthesis.py` as `BIG_PICTURE_PROMPT`:

```
You are analyzing ALL concerns raised by adversarial reviewers about a spec.
Your job is to look at these concerns HOLISTICALLY and synthesize insights that individual
evaluation would miss.

## Concerns by Adversary

{concerns_by_adversary}

## Your Analysis

Look at these concerns as a WHOLE. What story do they tell?

1. **THE REAL ISSUES**: Looking across all adversaries, what are the 2-4 things that
   actually matter most? Cut through the noise. What would you tell the spec author
   if you only had 30 seconds?

2. **HIDDEN CONNECTIONS**: Where do concerns from different adversaries connect in
   ways they don't realize? Security concern X and operations concern Y might be
   the same underlying issue.

3. **WHAT'S MISSING**: Given all the concerns raised, what DIDN'T anyone catch?
   Is there a blind spot? Sometimes the most important insight is what's absent.

4. **THE META-CONCERN**: If these concerns had one parent concern that generated
   them all, what would it be? "The spec doesn't understand X" or "The architecture
   is fighting against Y."

5. **HIGH-SIGNAL ALERTS**: If you had to prioritize the evaluator's attention,
   which 2-3 concerns deserve the most careful review? Why?

Be concise and insightful. Don't just summarize - synthesize.

Format:

REAL_ISSUES:
- [Issue 1]
- [Issue 2]

HIDDEN_CONNECTIONS:
- [Connection 1]

WHATS_MISSING:
- [Gap 1]

META_CONCERN: [One sentence]

HIGH_SIGNAL:
- [Concern ID or quote]: [why it matters]
```

**Note:** `generate_big_picture_synthesis()` uses inline model dispatch (not `call_model()`). Extract as-is — do NOT change dispatch pattern.

### 7.3 Clustering (Phase 3.5)

Stays in `phase_3_filtering.py`. Two-part prompt for semantic clustering:

**System prompt:**
```
You cluster near-duplicate engineering concerns.

Goal: Merge concerns that describe the SAME underlying issue in different words.

Rules:
1. Merge ONLY when the root cause AND required mitigation are the same.
2. Do NOT merge concerns that are thematically related but require different fixes.
3. Every concern index must appear in exactly one cluster.
4. When in doubt, keep concerns SEPARATE. Over-merging loses insights.

## GOOD merges (same root cause, same fix):
- "Fill events could be lost if DB write fails midway" + "No transactional guarantee
  for fill event insertion" → MERGE (both about atomicity of fill writes, same fix:
  wrap in transaction)
- "getMyFills has no pagination" + "Fill query returns unbounded results" → MERGE
  (both about missing pagination on the same endpoint)
- "Status filter uses wrong enum values" + "getActiveAlgoStates filters on 'executing'
  but DB has 'working'" → MERGE (same bug described at different abstraction levels)
- "No auth check on /devtest" + "Dev test page accessible without authentication" →
  MERGE (identical concern, different wording)

## BAD merges (related topic but DIFFERENT root causes or fixes):
- "Fill events lost during concurrent writes" + "Fill events lost if mutation fails
  midway" → DO NOT MERGE (first is race condition needing locking, second is atomicity
  needing transactions)
- "getMyFills missing exchange field" + "getMyExecutions missing exchange field" →
  DO NOT MERGE (different endpoints, different code paths, fixed independently)
- "DMA orders show 0/0 progress" + "Arb orders show wrong leg count" → DO NOT MERGE
  (different order types, different display bugs, different fixes)
- "No rate limiting on order placement" + "No rate limiting on fill queries" → DO NOT
  MERGE (different endpoints, different risk profiles)

Output JSON only:
{
  "clusters": [
    [1, 7, 14],
    [2],
    [3, 9]
  ]
}
```

**User prompt:**
```
Cluster these concerns by semantic equivalence.
Remember: only merge when root cause AND fix are the same. When in doubt, keep separate.

[indexed concerns with adversary and model metadata]

Return JSON only.
```

### 7.4 Evaluation (Phase 4)

Stays in `phase_4_evaluation.py`. System prompt dynamically includes per-adversary response protocols:

**System prompt:**
```
You are a senior engineer evaluating concerns raised by adversarial reviewers.

For each concern, you must decide:
- DISMISS: The concern is not valid (must cite specific evidence)
- ACCEPT: The concern is valid (spec needs revision)
- ACKNOWLEDGE: The concern is valid and insightful, but won't be addressed due to
  external constraints (out of scope, known tradeoff, business decision, etc.)
- DEFER: Need more context to decide

IMPORTANT: Use ACKNOWLEDGE when the adversary raised a GOOD point that you appreciate
them thinking about, but you're choosing not to act on it for reasons they couldn't
have known. This credits the adversary for valuable thinking without requiring spec changes.

RESPONSE PROTOCOLS:
### When evaluating {adversary_key}:
Valid dismissal: {adversary.valid_dismissal}
Invalid dismissal: {adversary.invalid_dismissal}
Rule: {adversary.rule}
[... repeated for each adversary represented in the concern set ...]

CRITICAL RULES:
1. No emotional language - just logic and evidence
2. For DISMISS: You MUST cite specific reasons from the spec or architecture
3. For ACCEPT: Briefly note what needs to change
4. For ACKNOWLEDGE: Note why the point is valid AND why it's not being addressed
5. For DEFER: Note what information is missing

Output your evaluation as JSON with this structure:
{
  "evaluations": [
    {"concern_index": 0, "verdict": "dismissed|accepted|acknowledged|deferred", "reasoning": "..."},
    ...
  ]
}
```

**User prompt:**
```
## SPECIFICATION
{spec}

## CONCERNS TO EVALUATE
### Concern 1 (from {adversary})
{concern_text}
[... all concerns ...]

Evaluate each concern according to the response protocols. Output valid JSON.
```

**Multi-model consensus** (`evaluate_concerns_multi_model`):
- Runs all batches per model in parallel within provider rate limits
- Different models run fully in parallel (independent limits)
- Consensus: majority-wins on verdict, merged reasoning, records per-model votes
- Falls back to single-model if only 1 model available

### 7.5 Rebuttal (Phase 5)

Stays in `phase_5_rebuttals.py`. `REBUTTAL_PROMPT` is a module-level constant:

```
The frontier model dismissed your concern with this reasoning:

{dismissal_reasoning}

Evaluate this dismissal. You have two options:

OPTION A - ACCEPT DISMISSAL:
If the dismissal is logically sound, respond with:
"ACCEPTED: [brief acknowledgment that the reasoning is valid]"

OPTION B - CHALLENGE DISMISSAL:
If the dismissal is NOT logically sound, respond with:
"CHALLENGED: [specific counter-evidence or logical flaw]"

RULES:
1. No emotional language ("that's unfair", "they're ignoring me")
2. No appeals to authority ("but I'm the security expert")
3. Only logic and evidence
4. If their reasoning is actually valid, accept it gracefully
5. If you have new evidence, present it clearly
```

**System prompt construction:**
```
You are an adversarial reviewer with this persona:

{adversary.persona}

You raised a concern that was dismissed. Evaluate the dismissal LOGICALLY.

{REBUTTAL_PROMPT}
```

**User prompt:**
```
Your original concern:
{evaluation.concern.text}

The dismissal reasoning:
{evaluation.reasoning}

Evaluate this dismissal. Output either:
ACCEPTED: [brief acknowledgment] if the reasoning is valid
CHALLENGED: [counter-evidence or logical flaw] if the reasoning is flawed
```

**Response parsing:** Check for `"CHALLENGED:"` in uppercase response → `sustained=True`.

### 7.6 Adjudication (Phase 6)

Stays in `phase_6_adjudication.py`:

**System prompt:**
```
You are making final decisions on challenged dismissals.

For each challenge, decide:
- UPHELD: The original dismissal was correct despite the challenge
- OVERTURNED: The challenge reveals a valid concern that needs addressing

Be rigorous. If the adversary raised a valid logical point, overturn the dismissal.

Output as JSON:
{
  "decisions": [
    {"challenge_index": 0, "verdict": "upheld|overturned", "reasoning": "..."},
    ...
  ]
}
```

**User prompt:**
```
## SPECIFICATION
{spec}

## CHALLENGED DISMISSALS
### Challenge 1 (from {adversary})
Original concern: {concern.text}
Dismissal reasoning: {evaluation.reasoning}
Rebuttal: {rebuttal.response}
[... all challenged dismissals ...]

Make your final decisions. Output valid JSON.
```

**Fallback behavior:** On parse failure, conservative fallback — all challenged concerns survive (are overturned).

### 7.7 Final Boss (Phase 7)

Stays in `phase_7_final_boss.py`. Uses Opus 4.6 with expensive timeout.

**System prompt:** `FINAL_BOSS["ux_architect"].persona` from adversaries.py.

**Model selection priority:** `ANTHROPIC_API_KEY` → `claude-opus-4-6` → Codex fallback → `select_eval_model()` fallback.

**User prompt construction** (dynamically built):
```
## SPECIFICATION TO REVIEW

{spec}

## GAUNTLET RESULTS

This spec has passed through the adversarial gauntlet:

{gauntlet_summary}

## CONCERN DISTRIBUTION BY ADVERSARY

{concern_analysis}

Total accepted concerns: {len(accepted_concerns)}

## ALTERNATE APPROACHES SUGGESTED (ACCEPTED)
[if any accepted concerns suggest alternate implementations — up to 5]

## DISMISSED SIMPLIFICATION CONCERNS (REVIEW THESE!)
[Concerns from lazy_developer, prior_art_scout, information_flow_auditor
that were dismissed but contain "why not", "just use", "instead", "simpler",
"over-engineer", "already", "platform", etc. — up to 5]

A dismissal is INVALID if it just says "we need X" without proving the
simpler approach can't do X.

If any dismissals are invalid, list them in your output as:
INVALID DISMISSALS: D1, D3 (etc.)

## YOUR TASK

Step back from the technical details. Consider:

1. **USER STORY**: Is this user actually better off?
2. **CONCERN VOLUME**: With N accepted concerns, is this spec trying to do too much?
3. **FUNDAMENTAL CHALLENGES**: Did multiple adversaries challenge the same core assumption?
4. **ALTERNATE APPROACHES**: Should any suggested alternates have been explored first?
5. **DISMISSED SIMPLIFICATIONS**: Were any "use simpler X" concerns dismissed without
   proving X doesn't work?

## REQUIRED OUTPUT FORMAT

You MUST issue one of three verdicts:

VERDICT: PASS
RATIONALE: [Why the user story is sound and concerns are normal refinements]

OR

VERDICT: REFINE
CONCERNS TO ADDRESS:
1. [Concern]
2. [Concern]

OR

VERDICT: RECONSIDER
FUNDAMENTAL ISSUE: [What's wrong with the current approach]
ALTERNATE APPROACHES TO EVALUATE:
1. [Approach]
2. [Approach]

## REQUIRED META-REPORTS (after your verdict)

PROCESS META-REPORT:
[2-3 sentences on gauntlet process quality, adversary coverage, gaps]

SELF META-REPORT:
[2-3 sentences on own review quality, was dismissed-concern review worthwhile]
```

**Response parsing:**
1. Extract verdict: scan for `VERDICT:` line → `PASS`/`REFINE`/`RECONSIDER`
2. Extract concerns: lines after `CONCERNS TO ADDRESS:` numbered list
3. Extract `RECONSIDER` details: `FUNDAMENTAL ISSUE:` + `ALTERNATE APPROACHES:`
4. Extract meta-reports: `PROCESS META-REPORT:` and `SELF META-REPORT:` blocks
5. Extract `INVALID DISMISSALS:` → parse comma-separated D-numbers for `DismissalReviewStats`
6. Fallback on parse failure: `FinalBossVerdict.REFINE` with raw response as `reconsider_reason`

---

## 8. Persistence Specification

### 8.1 Checkpoint Envelope Schema

```json
{
  "_meta": {
    "schema_version": 2,
    "spec_hash": "a1b2c3d4e5f6...",
    "config_hash": "f6e5d4c3b2a1...",
    "phase": "phase_1_attacks",
    "created_at": "2026-03-20T23:52:00Z",
    "data_hash": "9876543210ab..."
  },
  "data": [...]
}
```

### 8.2 Checkpoint Files

| File | Phase | Contents |
|------|-------|----------|
| `concerns-{hash}.json` | Phase 1 | Array of concern dicts |
| `raw-responses-{hash}.json` | Phase 1 | Adversary -> raw LLM response |
| `clustered-concerns-{hash}.json` | Phase 3.5 | Representatives + cluster_members |
| `evaluations-{hash}.json` | Phase 4 | Array of evaluation dicts |
| `run-manifest-{hash}-{timestamp}.json` | All | Array of PhaseMetrics |

`{hash}` = first 8 characters of spec_hash.

### 8.3 Resume Validation

1. **Config hash mismatch** -> discard, warn, run fresh
2. **Corrupt JSON** -> treat as missing, warn, don't crash
3. **Legacy format** (bare list) -> diagnostic-readable, not resumable
4. **Path traversal** -> reject `..`, symlinks outside base dir
5. **Concern set mismatch** (Phase 4 vs current Phase 3 output) -> discard Phase 4, re-evaluate

### 8.4 Atomic Write Implementation

```python
def _write_json_atomic(path: Path, data: Any) -> None:
    tmp = tempfile.NamedTemporaryFile(
        dir=path.parent, delete=False, suffix='.tmp', mode='w'
    )
    try:
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except:
        tmp.close()
        os.unlink(tmp.name)  # cleanup on error
        raise
```

### 8.5 Hash Algorithm

SHA-256, full-length hex digest for both `spec_hash` and `config_hash`.

---

## 9. CLI Specification

### 9.1 debate.py gauntlet (Primary)

```
uv run debate gauntlet [OPTIONS]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--gauntlet-adversaries` | str | "all" | Comma-separated adversary keys |
| `--gauntlet-model` | str | auto | Legacy single attack model |
| `--gauntlet-attack-models` | str | auto | Comma-separated attack models |
| `--gauntlet-frontier` | str | auto | Eval model(s) |
| `--no-rebuttals` | store_true | False | Skip Phase 5 |
| `--final-boss` | store_true | False | Run Phase 7 |
| `--timeout` | int | 300 | Per-call timeout |
| `--codex-reasoning` | choices | "low" | Attack reasoning effort |
| `--gauntlet-resume` | store_true | False | **NEW** Resume from checkpoint |
| `--unattended` | store_true | False | **NEW** No stdin + auto-checkpoint |
| `--eval-codex-reasoning` | choices | "xhigh" | **NEW** Eval reasoning effort |
| `--show-manifest HASH` | str | | **NEW** Print manifest, exit |

### 9.2 python -m gauntlet (Secondary)

Same flags but uses `--resume` (not `--gauntlet-resume`) since no session concept.

---

## 10. Error Contract

| Condition | Behavior | Exit Code |
|-----------|----------|-----------|
| Missing spec, unknown adversary, invalid model name | Print error, exit | 1 |
| Invalid CLI syntax | argparse exit | 2 |
| `GauntletClusteringError` or `GauntletExecutionError` | Print user_message, exit | 3 |
| `--resume` with no checkpoint | Warn, run fresh | 0 |
| Corrupt checkpoint JSON | Warn, ignore file, run fresh | 0 |
| Config mismatch on checkpoint | Warn, ignore file, run fresh | 0 |
| `KeyboardInterrupt` | Write manifest status `interrupted`, exit | 130 |

---

## 11. Timeout Policy

| Phase | Timeout Source | Reasoning Source |
|-------|---------------|-----------------|
| Phase 1 (attacks) | `config.timeout` | `config.attack_codex_reasoning` |
| Phase 2 (synthesis) | `config.timeout` | `config.attack_codex_reasoning` |
| Phase 3 (filtering) | `config.timeout` | N/A |
| Phase 3.5 (clustering) | `config.timeout` | N/A |
| Phase 4 (evaluation) | `config.timeout` | `config.eval_codex_reasoning` |
| Phase 5 (rebuttals) | `config.timeout` | `config.attack_codex_reasoning` |
| Phase 6 (adjudication) | `config.timeout` | `config.eval_codex_reasoning` |
| Phase 7 (Final Boss) | `max(config.timeout, 600)` | N/A |

---

## 12. Security Considerations

### 12.1 Model Name Validation

**Approach:** Blocklist (not allowlist — Pre-gauntlet Codex #7 determined allowlist regex too brittle for new provider formats like `codex/gpt-5.4`, `gemini-cli/gemini-3-pro-preview`, `xai/grok-3`).

**`_validate_model_name(model: str) -> None`** — called at top of `call_model()` AND early in `run_gauntlet()`:

```python
def _validate_model_name(model: str) -> None:
    """Reject model names containing dangerous patterns.

    Defense-in-depth: primary protection is list-based subprocess.run()
    which prevents shell injection. This catches malformed names early.
    """
    if not model or not model.strip():
        raise ValueError("Model name cannot be empty")

    dangerous_chars = set(';|&$`\\<>(){}!#~\'"')
    if any(c in model for c in dangerous_chars):
        raise ValueError(f"Model name contains shell metacharacter: {model!r}")

    if model.startswith('-') or '--' in model:
        raise ValueError(f"Model name looks like a CLI flag: {model!r}")

    if ' ' in model or '\t' in model or '\n' in model:
        raise ValueError(f"Model name contains whitespace: {model!r}")

    if any(ord(c) < 32 for c in model):
        raise ValueError(f"Model name contains control characters: {model!r}")
```

**What this does NOT catch:** A validly-named model that doesn't exist at the provider. That's a runtime error (API returns 404), not a security issue.

### 12.2 Atomic Writes

**Implementation:** `_write_json_atomic(path, data)` in persistence.py:

```python
def _write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON atomically: temp file -> fsync -> os.replace().

    Prevents: partial writes on crash, symlink attacks (G-7),
    stale temp files on ENOSPC (G-9).
    """
    tmp = tempfile.NamedTemporaryFile(
        dir=path.parent,  # same filesystem for os.replace()
        delete=False,      # we manage lifecycle
        suffix='.tmp',
        mode='w',
    )
    try:
        json.dump(data, tmp, indent=2, default=_json_default)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)  # atomic on POSIX
    except:
        tmp.close()
        try:
            os.unlink(tmp.name)  # cleanup stale temp (G-9)
        except OSError:
            pass  # temp already gone
        raise
```

**Why `tempfile.NamedTemporaryFile` instead of manual temp paths:**
- OS generates unpredictable name (prevents symlink pre-creation attacks — G-7)
- `dir=path.parent` ensures same filesystem (required for atomic `os.replace()`)
- `delete=False` gives us explicit control over lifecycle

**Where used:** All checkpoint writes, run manifest writes, stats/runs DB writes. Legacy code that uses `json.dump(open(..., 'w'))` is migrated to this function during extraction.

### 12.3 Path Traversal Guard

```python
def format_path_safe(base_dir: Path, filename: str) -> Path:
    """Resolve path under base_dir. Reject traversal attempts."""
    # Reject obvious traversal
    if '..' in filename or filename.startswith('/'):
        raise ValueError(f"Path traversal attempt: {filename!r}")

    resolved = (base_dir / filename).resolve()
    base_resolved = base_dir.resolve()

    # Verify resolved path is under base_dir
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError(f"Path escapes base directory: {resolved}")

    return resolved
```

**Where used:** All checkpoint file path construction (`concerns-{hash}.json`, `evaluations-{hash}.json`, `run-manifest-{hash}-{ts}.json`). The `{hash}` component comes from `spec_hash` which is user-controlled (via spec content). The guard ensures even crafted spec content can't write outside `.adversarial-spec-gauntlet/`.

### 12.4 Checkpoint Trust Model

All disk-loaded JSON is treated as **untrusted input**:
- Never execute or `eval()` checkpoint content
- Validate `_meta.schema_version` before parsing `data[]`
- Validate `_meta.config_hash` matches current config before reusing
- Validate `_meta.data_hash` matches SHA-256 of `data[]` for integrity
- On any validation failure: discard file, log warning, run fresh (never crash)
- Corrupted JSON (parse error): same as missing file (warn + fresh)
- Legacy format (bare list, no `_meta`): readable for diagnostics but never reused for resume

### 12.5 Dependencies

`filelock==3.16.1` pinned to exact version (G-8). Well-maintained minimal dependency used by pip, uv, virtualenv. No transitive dependencies.

### 12.6 Subprocess Dispatch

All model calls via CLI tools (`codex`, `gemini-cli`, `claude-cli`) use **list-based `subprocess.run()`**, not `shell=True`. This is the primary defense against shell injection — model name validation (§12.1) is defense-in-depth.

```python
# SAFE — list-based, no shell interpretation
subprocess.run(["codex", "--model", model_name, ...], ...)

# NEVER — shell=True would interpret metacharacters
subprocess.run(f"codex --model {model_name}", shell=True, ...)  # ← NOT THIS
```

---

## 13. Concurrency Model

### 13.1 ThreadPoolExecutor Usage

| Phase | Max Workers | Pattern | Rate Limiting |
|-------|------------|---------|---------------|
| Phase 1 (attacks) | `min(32, len(pairs))` | Parallel adversary×model pairs | Batched by provider: same-provider pairs in rate-limited waves; different providers run concurrently |
| Phase 3 (filtering) | per-batch | Parallel concern-to-explanation matching | Same rate limiting as evaluation |
| Phase 4 (evaluation) | per-wave per-model | Multi-level parallelism: models parallel with each other, batches within each model in rate-limited waves | Wave size from `get_rate_limit_config()` |
| Phase 5 (rebuttals) | `len(batch)` | Parallel rebuttals per dismissed evaluation | Batched with provider-specific delays |

### 13.2 Rate Limiting

`get_rate_limit_config(model_name) -> (batch_size, delay_seconds)`:

| Provider | Free Tier | Paid Tier | Env Var |
|----------|-----------|-----------|---------|
| Gemini | batch=3, delay=15s | batch=10, delay=2s | `GEMINI_PAID_TIER=true` |
| Claude | batch=5, delay=5s | batch=20, delay=1s | `CLAUDE_PAID_TIER=true` |
| Codex/GPT | batch=10, delay=2s | same (message quotas) | — |
| Unknown | batch=3, delay=10s | — | — |

**Provider grouping:** `_get_model_provider(model)` extracts provider key from model name prefix. Models with the same provider share rate limits; different providers run independently.

### 13.3 Thread Safety

**CostTracker** (in `models.py`, NOT in gauntlet package):
- `add(model, input_tokens, output_tokens)` — gets `threading.Lock()` (FIND-003)
- Read methods (`get_summary()`, etc.) — NOT locked. CostTracker is informational only (logging/display). Stale reads don't affect correctness.
- **Why now:** Python 3.14+ may remove the GIL (PEP 703). Currently the GIL makes the race benign, but adding the lock is cheap insurance.

**Phase modules:** No shared mutable state between threads. Each thread gets its own model call and writes to a thread-local result. Results are collected by the orchestrator's `ThreadPoolExecutor` futures.

**Checkpoint writes:** Single-threaded (orchestrator writes after phase completes, not during). `filelock` is used for checkpoint files that may be read during `--resume` while a write is in progress (unlikely but possible if user runs two gauntlets on same spec simultaneously).

---

## 14. Testing Specification

### 14.1 Test File

`scripts/tests/test_gauntlet_persistence.py` — 10 required tests. All use fixtures and mocks — NO live model calls.

### 14.2 Test Details

#### Test 1: `test_write_json_atomic_crash_safety`
**Purpose:** Verify `_write_json_atomic()` never leaves partial files on disk.
**Setup:** Create a temp directory with a target path.
**Actions:**
1. Write valid JSON via `_write_json_atomic(path, {"key": "value"})` — verify file exists and is valid
2. Monkey-patch `json.dump` to raise `OSError("disk full")` midway — call `_write_json_atomic()` again
3. Verify original file is still intact (not corrupted by failed write)
4. Verify no `.tmp` files left in directory (cleanup on error)
**Assertions:** File content unchanged after failed write; no temp files leaked.

#### Test 2: `test_load_partial_run_valid_checkpoint`
**Purpose:** Verify valid checkpoint files with correct envelope load successfully.
**Setup:** Create fixture checkpoint file at `.adversarial-spec-gauntlet/concerns-{hash}.json` with:
```json
{
  "_meta": {
    "schema_version": 2,
    "spec_hash": "a1b2c3d4",
    "config_hash": "<matching hash>",
    "phase": "phase_1_attacks",
    "created_at": "2026-03-20T23:00:00Z",
    "data_hash": "<computed>"
  },
  "data": [{"adversary": "paranoid_security", "text": "test concern", "id": "PARA-1234"}]
}
```
**Actions:** Call `load_partial_run(spec_hash, config)` with matching config.
**Assertions:** Returns dict with `"phase_1"` key containing the loaded concerns. Concerns are well-formed.

#### Test 3: `test_load_partial_run_corrupted_json`
**Purpose:** Verify corrupted checkpoint files are treated as missing without crashing.
**Setup:** Write garbage bytes (`b"not json {{{"]`) to a checkpoint file path.
**Actions:** Call `load_partial_run(spec_hash, config)`.
**Assertions:** Returns empty dict (no crash). Warning logged to stderr.

#### Test 4: `test_load_partial_run_config_mismatch`
**Purpose:** Verify checkpoints with different `config_hash` are discarded.
**Setup:** Create valid checkpoint with `config_hash = "abc123"`. Build `GauntletConfig` that produces a DIFFERENT hash (e.g., different timeout).
**Actions:** Call `load_partial_run(spec_hash, config)`.
**Assertions:** Returns empty dict. Warning logged: "Config changed since last run — starting fresh".

#### Test 5: `test_load_partial_run_legacy_format`
**Purpose:** Verify bare-list (no `_meta` envelope) checkpoint files are not used for resume.
**Setup:** Write a bare JSON array (`[{"adversary": "test", "text": "concern"}]`) to checkpoint path.
**Actions:** Call `load_partial_run(spec_hash, config)`.
**Assertions:** Returns empty dict. Legacy files readable for diagnostics but never reused for resume.

#### Test 6: `test_concern_set_hash_mismatch_forces_reeval`
**Purpose:** Verify Phase 4 evaluation data is discarded when concern IDs don't match current Phase 3 output.
**Setup:** Create valid Phase 4 checkpoint with evaluations referencing concern IDs `["PARA-1", "BURN-2"]`. Create current Phase 3 output with concern IDs `["PARA-1", "BURN-3"]` (ID mismatch).
**Actions:** Load partial run, check if Phase 4 data is reusable given the current Phase 3 output.
**Assertions:** Phase 4 data is NOT returned in the partial dict (discarded due to concern set mismatch).

#### Test 7: `test_config_hash_deterministic`
**Purpose:** Verify `get_config_hash()` is deterministic and sensitive to config changes.
**Setup:** Build two identical `GauntletConfig` objects and one with different timeout.
**Actions:**
1. `hash_a = get_config_hash(config_1, atk_models, eval_models, adversaries, flags)`
2. `hash_b = get_config_hash(config_1_copy, atk_models, eval_models, adversaries, flags)`
3. `hash_c = get_config_hash(config_different_timeout, atk_models, eval_models, adversaries, flags)`
**Assertions:** `hash_a == hash_b` (deterministic); `hash_a != hash_c` (sensitive to changes).

#### Test 8: `test_model_name_validation_blocklist`
**Purpose:** Verify `_validate_model_name()` accepts valid names and rejects dangerous patterns.
**Valid names (must pass):**
- `"codex/gpt-5.4"`
- `"claude-opus-4-6"`
- `"gemini-cli/gemini-3-pro-preview"`
- `"gemini/gemini-3-flash"`
- `"deepseek/deepseek-v4"`
**Rejected names (must raise ValueError):**
- `""` (empty)
- `"model; rm -rf /"` (shell metacharacter `;`)
- `"model | cat /etc/passwd"` (shell metacharacter `|`)
- `"--flag-injection"` (starts with `-`)
- `"model name with spaces"` (spaces)
- `"model\ninjection"` (newline/control chars)
- `"model$(command)"` (shell substitution)

#### Test 9: `test_cost_tracker_thread_safety`
**Purpose:** Verify concurrent `CostTracker.add()` calls don't lose data.
**Setup:** Create a `CostTracker` instance.
**Actions:** Launch 100 threads, each calling `tracker.add("model", 10, 5)` exactly once.
**Assertions:** After all threads join: `tracker.total_input_tokens == 1000`, `tracker.total_output_tokens == 500`. No data lost due to race conditions.

#### Test 10: `test_unattended_never_calls_input`
**Purpose:** Verify `--unattended` mode prevents any `input()` calls.
**Setup:** Mock `builtins.input` to track calls (or use the real monkey-patch).
**Actions:**
1. Set `config.unattended = True`
2. Apply the unattended enforcement (the `builtins.input` monkey-patch)
3. Call `builtins.input("prompt")` — must raise `RuntimeError("input() called in unattended mode")`
4. Restore original `builtins.input`
**Alternative approach:** Static analysis — grep all phase modules for `input(` calls and verify none exist outside the unattended guard.
**Assertions:** RuntimeError raised on any `input()` call during unattended mode.

---

## 15. Execution Steps

### Step 0: Scaffold package with shim
- Create `scripts/gauntlet/` directory
- Rename `scripts/gauntlet.py` → `scripts/gauntlet_monolith.py`
- Create `scripts/gauntlet/__init__.py` that exports ONLY the 5 public symbols from `gauntlet_monolith`:
  ```python
  from gauntlet_monolith import (
      run_gauntlet,
      format_gauntlet_report,
      get_adversary_leaderboard,
      get_medal_leaderboard,
  )
  from adversaries import ADVERSARIES
  __all__ = ["ADVERSARIES", "format_gauntlet_report", "get_adversary_leaderboard",
             "get_medal_leaderboard", "run_gauntlet"]
  ```
  **NOT `from gauntlet_monolith import *`** — explicit exports only (Pre-gauntlet Codex #1)
- **Verify:** `uv run pytest` passes, `from gauntlet import run_gauntlet` works
- **Risk:** LOW — instant revert by renaming back
- **Commit:** `refactor(gauntlet): scaffold package with shim`

### Step 1: Extract core_types.py
- Move: `FinalBossVerdict`, `Concern`, `Evaluation`, `Rebuttal`, `BigPictureSynthesis`, `GauntletResult`, `Medal`, `ExplanationMatch`, `DismissalReviewStats`, `FinalBossResult` (lines 33-37, 99-340, 1393-1627)
- Move: `_VERDICT_NORMALIZE` dict and `normalize_verdict()`
- **NEW:** Add `GauntletConfig`, `GauntletClusteringError`, `GauntletExecutionError`, `CheckpointMeta`, `PhaseMetrics` (see §4.3)
- **NEW:** Add `concerns_path: Optional[str] = None` field to `GauntletResult`
- Replace imports in monolith: `from gauntlet.core_types import ...`
- **Risk:** LOW — types have no side effects
- **Commit:** `refactor(gauntlet): extract core_types with GauntletConfig and GauntletClusteringError`

### Step 2: Extract model_dispatch.py
- Move: `call_model()`, `running_in_claude_code()`, `select_adversary_model()`, `select_eval_model()`, `select_gauntlet_models()`, `get_rate_limit_config()`, `_get_model_provider()`, `get_available_eval_models()` (lines 2145-2531)
- **NEW:** Add `_validate_model_name(model: str) -> None` — blocklist validation at top of `call_model()`. Rejects: shell metacharacters (`;|&$\``), spaces, control chars, flag-like patterns (`--`, starts with `-`), empty strings.
- Replace imports in monolith: `from gauntlet.model_dispatch import ...`
- **Risk:** LOW — pure functions + one new guard
- **Commit:** `refactor(gauntlet): extract model_dispatch with model name validation`

### Step 3: Extract persistence.py + concurrency fix
- Move: path constants, `load_adversary_stats()`, `save_adversary_stats()`, `update_adversary_stats()`, `save_gauntlet_run()`, `list_gauntlet_runs()`, `load_gauntlet_run()`, `load_resolved_concerns()`, `save_resolved_concerns()`, `get_spec_hash()`, `add_resolved_concern()`, `calculate_explanation_confidence()`, `record_explanation_match()`, `verify_explanation()` (lines 384-632, 1246-1391)
- **NEW:** `_load_json_safe()`, `_write_json_atomic()`, `_serialize_dataclass()`, `get_config_hash()`, `save_checkpoint()`, `load_partial_run()`, `save_partial_clustering()`, `save_run_manifest()`, `update_run_manifest()`, `load_run_manifest()`, `format_path_safe()` (see §5.5)
- Add `filelock==3.16.1` to both `pyproject.toml` files
- **Separate commit:** Add `threading.Lock()` to `CostTracker.add()` in `models.py` (FIND-003)
- Replace imports in monolith: `from gauntlet.persistence import ...`
- **Risk:** MEDIUM — new dependency, new persistence structures
- **Commits:**
  - `refactor(gauntlet): extract persistence with filelock, resume loader, run manifest`
  - `fix(models): add threading.Lock to CostTracker`

### Step 4: Extract medals.py
- Move: `MEDALS_DIR`, `calculate_medals()`, `generate_medal_report()`, `save_medal_reports()`, `format_medals_for_display()`, `get_medal_leaderboard()`, `_get_concern_keywords()`, `_concerns_are_similar()` (lines 774-1244)
- Replace imports in monolith
- **Risk:** LOW
- **Commit:** `refactor(gauntlet): extract medals`

### Step 5: Extract reporting.py
- Move: `format_gauntlet_report()`, `get_adversary_leaderboard()`, `get_adversary_synergy()`, `format_synergy_report()` (lines 634-772, 1097-1179, 3710-3828)
- **NEW:** Add `format_run_manifest(manifest: dict) -> str` for human-readable manifest output
- Replace imports in monolith
- **Risk:** LOW — pure formatting
- **Commit:** `refactor(gauntlet): extract reporting with run manifest formatting`

### Step 6: Extract phase modules (1-7)
- Extract in pipeline order: 1, 2, 3, 4, 5, 6, 7 (Pre-gauntlet Codex #3: extracting out-of-order forces temporary back-imports)
- Each prompt constant stays with its phase (see §7)
- **QUOTA BURN FIX 1 (cont.):** Strip ALL hardcoded timeout/reasoning defaults from every phase function. Replace with `config: GauntletConfig` parameter. Affected functions: see §18 hardcoded defaults table.
- **QUOTA BURN FIX 2 (cont.):** Nuke silent catch-all in `cluster_concerns_with_provenance()`. Replace with retry-once + `GauntletClusteringError` (see §5.8.3).
- **Note:** `generate_big_picture_synthesis()` has inline litellm dispatch — extract as-is, do NOT change
- **Verification:** `grep -n 'timeout: int = [0-9]' scripts/gauntlet/phase_*.py` must return zero results
- **Risk:** MEDIUM — core LLM logic, config threading through all signatures
- **Commit:** `refactor(gauntlet): extract phases 1-7, strip hardcoded defaults, nuke silent catch-all`

### Step 7: Extract orchestrator.py
- Move `run_gauntlet()` (lines 3290-3707)
- Build `GauntletConfig` at top from parameters (see §5.9)
- **NEW:** Unattended enforcement — monkey-patch `builtins.input` (G-4)
- **NEW:** Early model name validation — `_validate_model_name()` for all models before Phase 1 (G-6)
- **NEW (QUOTA BURN FIX 3):** Resume logic — `load_partial_run()`, skip completed adversaries/phases (see §5.9 pseudocode)
- **NEW (QUOTA BURN FIX 4):** Run manifest — `update_run_manifest()` after each phase
- **NEW:** Auto-checkpoint after Phase 3.5, 4, 7 when `config.auto_checkpoint=True` (G-2)
- **NEW:** KeyboardInterrupt → manifest `"interrupted"` + exit 130
- **NEW:** All return paths populate `GauntletResult.concerns_path`
- **Risk:** HIGH — hub of all dependencies, most new logic
- **Commit:** `refactor(gauntlet): extract orchestrator with config, resume, checkpoint, manifest`

### Step 8: Extract cli.py + __main__.py + finalize
- Move `main()` (lines 3836-4087) to `cli.py`
- Create `__main__.py`: `from gauntlet.cli import main; main()`
- **NEW CLI flags:** `--unattended` (store_true), `--resume` (store_true), `--eval-codex-reasoning` (choices, default "xhigh")
- Replace shim `__init__.py` with final version exposing 5 public symbols from extracted modules
- Delete `scripts/gauntlet_monolith.py`
- **Risk:** LOW — monolith is empty at this point
- **Commit:** `refactor(gauntlet): extract cli + __main__.py, remove monolith`

### Step 8.5: Wire new flags into debate.py (CRITICAL — primary entry point)
- Update `debate.py` gauntlet subcommand parser (~line 458):
  - `--gauntlet-resume` (store_true) — **NOT `--resume`** (flag collision with `--resume SESSION_ID`)
  - `--unattended` (store_true)
  - `--eval-codex-reasoning` (choices: minimal/low/medium/high/xhigh, default: "xhigh")
  - `--show-manifest HASH` (optional, prints manifest and exits)
- Update `run_gauntlet()` call site (~line 989) to pass new args
- `--show-manifest` handler: `persistence.load_run_manifest(hash)` → `reporting.format_run_manifest()` → print → exit(0)
- **Risk:** MEDIUM — touches main entry point, but just arg-passing
- **Commit:** `feat(debate): wire --gauntlet-resume/--unattended/--eval-codex-reasoning into debate.py gauntlet`

### Step 9: Update architecture docs
- Update `.architecture/` manifest and component docs for new file paths
- Deploy: `cp -r skills/adversarial-spec/* ~/.claude/skills/adversarial-spec/`
- **Risk:** LOW
- **Commit:** `docs: update architecture for gauntlet package`

### Step 10: Update phase docs + instruction manual
- **05-gauntlet.md fixes:**
  - **Remove** false claim at line 71-72: `"--codex-reasoning is GLOBAL"`. Replace with docs for `--attack-codex-reasoning` (default: low) and `--eval-codex-reasoning` (default: xhigh)
  - **Add** directive: **"NEVER kill a background debate.py task, and NEVER launch a duplicate run, without first running `ls .adversarial-spec-gauntlet/` to check for partial output artifacts."**
  - **Document** `--gauntlet-resume`, `--unattended`, `--eval-codex-reasoning` flags
- **03-debate.md + 05-gauntlet.md session enforcement:**
  - Add directive: **"Before the FIRST debate round on a new spec, Claude MUST create: (1) spec file, (2) manifest with status `drafting`, (3) session file, (4) update session-state.json. This is a hard gate."**
- **Doc migration:** Replace all `python3 gauntlet.py` references with `python -m gauntlet` in README.md, PRE_GAUNTLET_DESIGN.md, and any other docs
- **Risk:** LOW — documentation only
- **Commit:** `docs: fix 05-gauntlet.md false claims, migrate python3 gauntlet.py references`

---

## 16. Verification Strategy

### 16.1 Per-Step Smoke Check (after EVERY step)

These 3 commands must pass after every commit. If any fail, the step is broken — fix before proceeding.

```bash
# 1. Import surface intact
uv run python -c "from gauntlet import run_gauntlet, format_gauntlet_report, get_adversary_leaderboard, get_medal_leaderboard, ADVERSARIES; print('OK')"

# 2. Tests pass
uv run pytest

# 3. Lint clean
uvx ruff check
```

### 16.2 Step-Specific Checks

| Step | Command | Verifies |
|------|---------|----------|
| 0 | `uv run python -c "from gauntlet import run_gauntlet; print(type(run_gauntlet))"` | Shim correctly delegates to monolith |
| 1 | `uv run python -c "from gauntlet.core_types import GauntletConfig, GauntletClusteringError, GauntletExecutionError, GauntletResult; assert hasattr(GauntletResult, 'concerns_path'); print('OK')"` | All types extracted, new types exist, concerns_path field present |
| 2 | `uv run python -c "from gauntlet.model_dispatch import _validate_model_name; _validate_model_name('codex/gpt-5.4'); _validate_model_name('claude-opus-4-6'); _validate_model_name('gemini-cli/gemini-3-pro-preview'); print('OK')"` | Validation accepts valid model names |
| 2 | `uv run python -c "from gauntlet.model_dispatch import _validate_model_name; try: _validate_model_name('model; rm -rf /'); assert False except ValueError: print('Blocked')"` | Validation rejects shell metacharacters |
| 3 | `uv run python -c "from gauntlet.persistence import _write_json_atomic, load_partial_run, format_path_safe; print('OK')"` | New persistence functions importable |
| 3 | `uv run python -c "import filelock; print(filelock.__version__)"` | filelock dependency installed |
| 6 | `grep -rn 'timeout: int = [0-9]' scripts/gauntlet/phase_*.py` | Must return ZERO results — all hardcoded defaults stripped |
| 6 | `grep -rn 'except Exception.*:' scripts/gauntlet/phase_3_filtering.py \| grep -v retry` | Silent catch-all removed (only retry catch remains) |
| 7 | `uv run python -c "from gauntlet.orchestrator import run_gauntlet; import inspect; sig = inspect.signature(run_gauntlet); assert 'resume' in sig.parameters; assert 'unattended' in sig.parameters; assert 'eval_codex_reasoning' in sig.parameters; print('OK')"` | New parameters exist on orchestrator |
| 8 | `uv run debate gauntlet --help \| grep -E '(unattended\|gauntlet-resume\|eval-codex-reasoning\|show-manifest)'` | All 4 new flags in debate.py help |
| 8 | `uv run debate gauntlet --list-adversaries` | CLI loads, package wired, adversaries accessible |
| 8 | `PYTHONPATH=skills/adversarial-spec/scripts uv run python -m gauntlet --list-adversaries` | Standalone entry point works |

### 16.3 End-to-End Live Smoke Test

After ALL steps complete, run a single-adversary live gauntlet:

```bash
echo "# Test Spec\n\nThis is a minimal test specification for smoke testing." > /tmp/test-spec.md
cat /tmp/test-spec.md | uv run debate gauntlet \
  --gauntlet-adversaries paranoid_security \
  --timeout 300 \
  --unattended \
  --no-rebuttals
```

**Expected output:**
- Phase 1: 1 adversary generates concerns
- Phase 2: synthesis runs
- Phase 3: filtering + clustering
- Phase 4: evaluation
- Phase 5: skipped (--no-rebuttals)
- Phase 6: skipped (no rebuttals)
- Phase 7: skipped (no --final-boss)
- Run manifest written to `.adversarial-spec-gauntlet/run-manifest-*.json`
- Auto-checkpoints written (--unattended)
- No `input()` prompts (--unattended enforcement)

### 16.4 Resume Smoke Test

After the live smoke test above:

```bash
# Run again with --gauntlet-resume — should detect partial run and skip Phase 1
cat /tmp/test-spec.md | uv run debate gauntlet \
  --gauntlet-adversaries paranoid_security \
  --timeout 300 \
  --unattended \
  --no-rebuttals \
  --gauntlet-resume
```

**Expected:** Phase 1 detects that paranoid_security already ran, skips attack generation.

### 16.5 Pytest Tests

Run the 10 new tests from §14:

```bash
uv run pytest scripts/tests/test_gauntlet_persistence.py -v
```

All 10 must pass. No live model calls — all tests use fixtures and mocks.

---

## 17. Migration Guide

### 17.1 External Consumers (debate.py — zero changes)

debate.py imports exactly 5 symbols. The package name is unchanged (`gauntlet`). **No import changes required.**

```python
# Before AND after:
from gauntlet import (
    ADVERSARIES,
    format_gauntlet_report,
    get_adversary_leaderboard,
    get_medal_leaderboard,
    run_gauntlet,
)
```

The only debate.py changes are in Step 8.5: adding 4 new CLI flags and passing them through to `run_gauntlet()`.

### 17.2 Internal Development (within the package)

If any future code needs to import gauntlet internals (e.g., for testing or new tools):

```python
# Before (monolith):
from gauntlet import Concern, call_model, GauntletResult, save_adversary_stats

# After (package):
from gauntlet.core_types import Concern, GauntletResult
from gauntlet.model_dispatch import call_model
from gauntlet.persistence import save_adversary_stats

# Phase functions:
from gauntlet.phase_1_attacks import generate_attacks
from gauntlet.phase_4_evaluation import evaluate_concerns
from gauntlet.orchestrator import run_gauntlet

# NEW types:
from gauntlet.core_types import GauntletConfig, GauntletClusteringError, GauntletExecutionError
from gauntlet.core_types import CheckpointMeta, PhaseMetrics

# NEW persistence:
from gauntlet.persistence import load_partial_run, save_checkpoint, _write_json_atomic
```

### 17.3 Standalone CLI Invocation

```bash
# Before:
python3 scripts/gauntlet.py --list-adversaries
python3 scripts/gauntlet.py --stats

# After:
PYTHONPATH=skills/adversarial-spec/scripts uv run python -m gauntlet --list-adversaries
PYTHONPATH=skills/adversarial-spec/scripts uv run python -m gauntlet --stats

# New flags (standalone only):
PYTHONPATH=scripts uv run python -m gauntlet --resume --unattended
PYTHONPATH=scripts uv run python -m gauntlet --eval-codex-reasoning high
```

### 17.4 Deployment

```bash
# Same as always — manual copy to Claude Code skills directory
cp -r skills/adversarial-spec/* ~/.claude/skills/adversarial-spec/
```

### 17.5 Rollback

If the refactor needs to be reverted:
1. Step 0 created `gauntlet_monolith.py` — rename back to `gauntlet.py`
2. Delete `scripts/gauntlet/` directory
3. Remove `filelock` from pyproject.toml
4. Revert debate.py changes (4 new CLI flags)
5. `cp -r skills/adversarial-spec/* ~/.claude/skills/adversarial-spec/`

Alternatively, `git revert` individual step commits (one commit per step for clean bisectability).

### 17.6 Doc References

All documentation references to `gauntlet.py` or `python3 gauntlet.py` must be updated in Step 10:

| File | Old Reference | New Reference |
|------|--------------|---------------|
| README.md | `python3 scripts/gauntlet.py` | `python -m gauntlet` (with PYTHONPATH) |
| PRE_GAUNTLET_DESIGN.md | `python3 gauntlet.py` | `python -m gauntlet` |
| phases/05-gauntlet.md | Various | Updated per Step 10 |
| phases/03-debate.md | Various | Updated per Step 10 |
| CLAUDE.md | N/A (doesn't reference gauntlet.py directly) | No change needed |

---

## 18. Quota Burn Fixes

| # | Fix | Root Cause | Steps | Key Change |
|---|-----|-----------|-------|------------|
| 1 | GauntletConfig | 13 hardcoded timeouts/reasoning ignored CLI flags | 1, 6, 7 | Single config object to all phases |
| 2 | GauntletClusteringError | Silent `except Exception` pushed 100% raw to expensive eval | 1, 6 | Retry once, save partial, halt |
| 3 | --resume idempotency | Reruns start from zero | 3, 7, 8 | Load partial run, skip completed |
| 4 | Run manifest | dedup-stats.json useless | 3, 5, 7 | Per-phase metrics, iterative writes |
| 5 | Fix 05-gauntlet.md | False "global --codex-reasoning" claim | 10 | Accurate docs |
| 6 | Session artifact gate | No enforcement before debate/gauntlet | 10 | Hard gate directive |

### Functions with hardcoded defaults eliminated:

| Function | Old Default | New Source |
|----------|------------|-----------|
| `match_concern_to_explanation()` | timeout=60 | config.timeout |
| `filter_concerns_with_explanations()` | timeout=60 | config.timeout |
| `generate_big_picture_synthesis()` | timeout=120 | config.timeout |
| `run_final_boss_review()` | timeout=600 | max(config.timeout, 600) |
| `evaluate_concerns_multi_model()` | timeout=300 | config.timeout |
| `generate_attacks()` | timeout=300, codex_reasoning="low" | config.timeout, config.attack_codex_reasoning |
| `cluster_concerns_with_provenance()` | timeout=60 | config.timeout |
| `evaluate_concerns()` | timeout=300 | config.timeout |
| `run_rebuttals()` | timeout=300 | config.timeout |
| `final_adjudication()` | timeout=300 | config.timeout |

---

## 19. Decision Journal

| Decision | Reason | Source |
|----------|--------|--------|
| `--gauntlet-resume` not `--resume` | debate.py flag collision | G-1 (prior_art_scout) |
| Pin `filelock==3.16.1` | Supply chain risk | G-8 (paranoid_security) |
| Checkpoint after Phase 3.5 | Highest-cost crash failure mode | G-2 (burned_oncall) |
| Monkey-patch `builtins.input` | Runtime enforcement | G-4 (pedantic_nitpicker) |
| Blocklist for model validation | Allowlist too brittle | Pre-gauntlet Codex #7 |
| SHA-256 full hex digest | Collision-resistant | G-5 (paranoid_security) |
| `eval_codex_reasoning` default "xhigh" | Matches DEFAULT_CODEX_REASONING | G-13 |
| Final Boss 600s floor | Opus 4.6 needs minimum time | Design decision |
| Functional orchestrator | Preserve `run_gauntlet` contract | Scope constraint |
| Gauntlet-specific persistence | Scope containment | prior_art_scout |

---

## 20. Debate Dispositions

**Debate models:** codex/gpt-5.4 + gemini-cli/gemini-3-pro-preview + Claude (3rd voice/synthesizer)
**2 rounds, 22 total findings**

### Round 1 (Codex 5.4 + Gemini — 10 findings)

| # | Finding | Source | Disposition | Detail |
|---|---------|--------|-------------|--------|
| R1-1 | New flags (`--resume`, `--unattended`, `--eval-codex-reasoning`) not wired into debate.py | Codex 5.4 | **Fixed** | Added Step 8.5: wire all 3 flags + `--show-manifest` into debate.py gauntlet subparser. CRITICAL — debate.py is the primary user entry point, not standalone cli.py. |
| R1-2 | No bootstrap/getting-started workflow section | Codex 5.4 + Gemini | **Acknowledged** | This is an implementation plan, not a product spec. Bootstrap is in CLAUDE.md. Added brief Getting Started section (§1) for verification commands. |
| R1-3 | Doc references to `python3 gauntlet.py` will break after refactor | Codex 5.4 | **Fixed** | Step 10 now includes doc migration: replace all `python3 gauntlet.py` references with `python -m gauntlet` across README.md, PRE_GAUNTLET_DESIGN.md, and phase docs. |
| R1-4 | Persistence contract incomplete — no `save_partial_clustering()`, no concern-set matching | Codex 5.4 | **Fixed** | Added checkpoint envelope schema (§8.1), `save_partial_clustering()` to persistence API (§5.5), concern_set_hash matching in resume validation (§8.3). |
| R1-5 | FIND-004 (tasks.json locking) conflated with gauntlet persistence | Codex 5.4 | **Fixed** | Step 3 now explicitly separates them. FIND-004 affects `mcp_tasks/server.py` and `task_manager.py`, NOT gauntlet. Marked out of scope for this refactor. |
| R1-6 | Timeout policy inconsistent — Final Boss gets `config.timeout` but needs 600s floor | Codex 5.4 | **Fixed** | Added Timeout Policy section (§11): `max(config.timeout, 600)` for Final Boss, `config.timeout` for all other phases. |
| R1-7 | Missing exit-code matrix — what happens on each error type? | Codex 5.4 | **Fixed** | Added Error Contract section (§10): 7 conditions mapped to behaviors and exit codes 0/1/2/3/130. |
| R1-8 | Need `__main__.py` for `python -m gauntlet` | Codex 5.4 | **Fixed** | Added to target structure (§3.1) and Step 8. Contents: `from gauntlet.cli import main; main()`. |
| R1-9 | Spec needs formal sections (Security, Observability, SLA, etc.) | Gemini | **Acknowledged** | Valid for a product spec, but this is an implementation plan. Security/observability concerns addressed inline in steps. Would add bureaucratic overhead without improving implementation clarity. |
| R1-10 | `--unattended` should mean "never prompt stdin" — current spec only says "auto-checkpoint" | Codex 5.4 | **Fixed** | Step 8 clarifies: `--unattended` = auto-checkpoint + no stdin prompts. Final Boss prompt skipped unless `--final-boss` explicitly passed. |

### Round 2 (Codex 5.4 + Gemini — 12 findings)

| # | Finding | Source | Disposition | Detail |
|---|---------|--------|-------------|--------|
| R2-1 | Exact `run_gauntlet()` signature needed — current spec says "add params" without specifying | Both | **Fixed** | Added full API Contract section (§6) with complete signature, all 14 parameters, types, and defaults. |
| R2-2 | `GauntletExecutionError` referenced in error contract but never defined | Codex | **Fixed** | Added to core_types.py (§4.3) alongside `GauntletClusteringError`. Exit code 3 on either. |
| R2-3 | Flag precedence rules needed — what overrides what? | Codex | **Fixed** | Added to §5.9: `attack_models` > `adversary_model` > auto-select; `use_multi_model=False` → single eval model; etc. |
| R2-4 | `--show-manifest HASH` CLI viewer for run manifests | Gemini | **Fixed** | Added to Step 8.5: `persistence.load_run_manifest(hash)` → `reporting.format_run_manifest()` → print → exit(0). |
| R2-5 | Real pytest tests needed — `python -c` one-liners are not sufficient for behavior changes | Both | **Fixed** | Replaced "minimal smoke tests" with 10 required pytest tests in §14, each with setup/actions/assertions. |
| R2-6 | Exit 130 + manifest status `"interrupted"` on KeyboardInterrupt | Codex | **Fixed** | Added to Error Contract (§10) and orchestrator pseudocode (§5.9). |
| R2-7 | Path-traversal guard on checkpoint paths — `..` or symlink escape | Codex | **Fixed** | Added `format_path_safe()` to persistence.py (§5.5) and Resume Validation (§8.3). |
| R2-8 | Bootstrap/Getting Started section (repeat from R1-2) | Both | **Fixed** | Added Getting Started section with actual shell commands for post-refactor validation. |
| R2-9 | Full replacement spec with SLAs, observability metrics, security sections | Both | **Declined** | Over-engineered for a single-developer skill's implementation plan. Relevant concerns (security, observability via manifest) are addressed inline. |
| R2-10 | PYTHONPATH for standalone `python -m gauntlet` needs documentation | Codex | **Fixed** | Documented in Getting Started: `PYTHONPATH=skills/adversarial-spec/scripts uv run python -m gauntlet`. |
| R2-11 | 5-stage deployment rollback plan | Codex | **Declined** | `cp -r` + monolith shim (Step 0) is sufficient for a single-developer tool. 5-stage deployment plan is appropriate for production services, not CLI skills. |
| R2-12 | Manifest viewer should also be in standalone cli.py | Codex | **Declined** | debate.py is the primary entry point. Adding `--show-manifest` to standalone CLI too is unnecessary duplication. Users who need standalone access can use `python -c`. |

---

## 21. Gauntlet Dispositions

**9 adversaries, 75 raw -> 42 clustered -> 23 accepted**
**Attack model:** gemini-cli/gemini-3-flash-preview
**Eval models:** codex/gpt-5.3-codex, gemini-cli/gemini-3-pro-preview
**Duration:** 1897.1 seconds (~32 minutes)

### Fixed in Spec (9)

| # | Concern | Adversary | Severity | Spec Change |
|---|---------|-----------|----------|-------------|
| G-1 | `--resume` flag collision with debate.py `--resume SESSION_ID` | prior_art_scout | CRITICAL | Renamed to `--gauntlet-resume` in debate.py; standalone `cli.py` keeps `--resume` (no session concept). Added to §9.1 CLI Specification. |
| G-2 | Missing checkpoint after Phase 3.5 clustering — in-memory clustered data is highest-cost crash failure mode | burned_oncall | HIGH | Added auto-checkpoint after clustering in orchestrator (§5.9). `clustered-concerns-{hash}.json` written when `config.auto_checkpoint=True`. |
| G-3 | JSON serialization strategy unspecified — how do dataclasses become JSON? Enum handling? | pedantic_nitpicker | MEDIUM | Specified `dataclasses.asdict()` + custom encoder for Enum types. Consolidated into `_serialize_dataclass()` helper in persistence.py (§5.5). |
| G-4 | Unattended enforcement mechanism unspecified — "policy only" is insufficient | pedantic_nitpicker | MEDIUM | Monkey-patch `builtins.input` to raise `RuntimeError("input() called in unattended mode")` at start of `run_gauntlet()`. Restore on exit (§5.9). |
| G-5 | Hash algorithm unspecified — could use MD5, SHA-1, truncated, etc. | paranoid_security | MEDIUM | Explicitly documented: SHA-256, full-length hex digest for both `spec_hash` and `config_hash` (§8.5). |
| G-6 | Model names validated too late — in `call_model()` at runtime, not at startup | info_flow_auditor | MEDIUM | Early validation at top of `run_gauntlet()` BEFORE any phase dispatch. Fail fast with exit code 1 (§5.9 Step 3). |
| G-7 | Predictable temp file names — symlink attack vector | paranoid_security | LOW | Use `tempfile.NamedTemporaryFile(dir=target_dir, delete=False)` for secure temp creation in `_write_json_atomic()` (§8.4). |
| G-8 | filelock version unpinned — supply chain risk from `>=3.12.0` | paranoid_security | LOW | Pinned to `filelock==3.16.1` in both `pyproject.toml` files (§5.5). |
| G-9 | Disk full leaves stale temp files — ENOSPC during atomic write | pedantic_nitpicker | LOW | try/finally cleanup in `_write_json_atomic()` — always `os.unlink(tmp.name)` on error (§8.4). |

### Accepted as Design Decisions (7)

| # | Concern | Adversary | Severity | Rationale |
|---|---------|-----------|----------|-----------|
| G-10 | Final Boss 600s floor is still "hardcoded" | burned_oncall | LOW | Documented design decision: Opus 4.6 with large context needs minimum time. `max(config.timeout, 600)` is intentional, not a bug. See §11 Timeout Policy. |
| G-11 | Model blocklist bypass possible — attacker could craft name that passes blocklist | burned_oncall | LOW | Primary protection is `subprocess.run()` with list-based args (no shell). Blocklist is defense-in-depth, not primary barrier. |
| G-13 | `eval_codex_reasoning` "xhigh" default is expensive | pedantic_nitpicker | LOW | Matches existing `DEFAULT_CODEX_REASONING` constant. Evaluation quality is the priority — cost is a deliberate tradeoff. |
| G-14 | CostTracker read race — lock only on `add()`, not on reads | paranoid_security | LOW | CostTracker is informational only (logging/display). Stale reads don't affect correctness. Adding read locks would add contention for no benefit. |
| G-15 | Phase 3.5 naming ambiguity — clustering is IN `phase_3_filtering.py` | info_flow_auditor | LOW | Filtering + clustering are the same dedup phase, just two steps. Splitting to separate file adds a module for one function. |
| G-16 | filelock supply chain risk — transitive dependency | paranoid_security | LOW | Well-maintained, minimal dependency. Used by pip, uv, virtualenv. Pinned to exact version (G-8). |
| G-17-23 | SHA-256 collision, JSON parsing bombs, litellm compat, ghost config, stale locks, leap seconds, manifest info leak | various | LOW | SHA-256 collision infeasible; parsing bombs require local access; litellm compat preserved by extract-as-is; ghost config fixed in Step 10 docs; filelock handles stale locks natively; leap seconds irrelevant for duration tracking; manifest is local-only, no sensitive data. |

### Deferred (1)

| # | Concern | Adversary | Severity | Rationale |
|---|---------|-----------|----------|-----------|
| G-12 | Global timeout circuit breaker — no upper bound on total run time | burned_oncall | LOW | Valid concern but out of scope for this refactor. Would require significant orchestrator changes (wall-clock timer, graceful phase cancellation). Better as a separate feature with its own spec. |

### Dismissed (16)

| Concern | Adversary | Rationale |
|---------|-----------|-----------|
| Checkpoint poisoning via malicious JSON | paranoid_security | Checkpoints are local files written by the tool itself. Attacker with local write access has already won. Path traversal guard addresses the realistic attack surface. |
| 16-file fragmentation is over-engineered | lazy_developer | Architecture analysis (FIND-002) and Gemini review (AD-2) both recommend splitting. 4087-line monolith is the problem, not the solution. |
| Checkpoint envelope is over-engineered | lazy_developer | Envelope enables resume validation (config_hash), corruption detection (data_hash), and version migration (schema_version). Each field has a concrete use case. |
| GauntletConfig is a "junk drawer" | asshole_loner | Config has 6 fields, all used by multiple phases. It's a parameter object, not a junk drawer. Alternative (passing 6 individual params to every phase) is worse. |
| Run manifest is redundant with checkpoint files | lazy_developer | Manifest tracks per-phase duration/tokens/models — data NOT in checkpoints. Different purpose: checkpoints are for resume, manifest is for diagnosis. |
| Import fragility — 16 files means 16 potential import errors | lazy_developer | Mitigated by Step 0 shim approach (monolith stays functional until all modules extracted). Per-step smoke check catches import errors immediately. |
| Manifest write failure could crash run | burned_oncall | Manifest writes are in try/except — failure logs warning but doesn't halt the pipeline. Manifest is telemetry, not critical path. |
| Stale file locks from crashed processes | burned_oncall | filelock handles stale locks natively — locks are released on process exit. No manual lock cleanup needed. |
| Clustering hard halt is too aggressive | lazy_developer | Already addressed by Codex review #6: retry once before hard halt. Silent fallback (the current behavior) is the actual problem — it caused the Quota Burn. |
| compatibility_engineer self-break | asshole_loner | 5-symbol import surface is unchanged. debate.py is the only consumer. This is tested by per-step smoke checks. |
| debate.py dependency brittleness | architect | debate.py imports exactly 5 symbols. The package restructure doesn't change this. Import paths are tested in Step 0. |
| Manual file locking is error-prone | prior_art_scout | Using well-tested `filelock` library, not manual locking. The library handles cross-platform concerns. |
| Model dispatching overlap between model_dispatch.py and phase modules | architect | Phase modules call `call_model()` from model_dispatch.py. No overlap — model_dispatch owns dispatch, phases own prompts. |
| Orchestrator pattern should be class-based | architect | Functional API preserves the existing `run_gauntlet()` contract. Class-based orchestrator is a larger refactor with no concrete benefit for this use case. |
| Config duplication between GauntletConfig and CLI args | pedantic_nitpicker | Config is built ONCE from CLI args in orchestrator. No duplication — args are the source, config is the runtime representation. |
| Resume logic collision with debate.py session resume | prior_art_scout | Already fixed: `--gauntlet-resume` in debate.py (G-1). Standalone CLI uses `--resume`. No collision. |

### Pre-Gauntlet Codex Review (14 findings)

| # | Finding | Severity | Disposition |
|---|---------|----------|-------------|
| 1 | Shim `__init__.py` exports too much (uses `*`) | HIGH | **Fixed** — exports only 5 named symbols |
| 2 | reporting/medals/persistence import cycle | HIGH | **Fixed** — dependency graph enforces one-way: reporting → medals → persistence |
| 3 | Phase extraction order (5,6 before 3,4) risks back-imports | HIGH | **Fixed** — changed to pipeline order 1,2,3,4,5,6,7 |
| 4 | Resume lacks config invalidation guard | HIGH | **Fixed** — `config_hash` in checkpoint `_meta`, discard on mismatch |
| 5 | "Skip to Phase 5" unsafe — concern set may have changed | HIGH | **Fixed** — validate concern ID alignment before skipping |
| 6 | GauntletClusteringError too aggressive — no retry | HIGH | **Fixed** — retry once with 2s backoff before hard halt |
| 7 | Model name regex allowlist too restrictive for new providers | MEDIUM | **Fixed** — switched to blocklist (reject dangerous chars) |
| 8 | FileLock without atomic writes — partial JSON on crash | MEDIUM | **Fixed** — temp file + `os.replace()` strategy |
| 9 | RunManifest missing fields for crash reconstruction | MEDIUM | **Fixed** — added phase_index, status, error, spec_hash |
| 10 | `concerns_path` None on error/early-return paths | MEDIUM | **Fixed** — all return paths populate it |
| 11 | Verification misses resume code paths | MEDIUM | **Fixed** — added resume smoke tests + 10 pytest tests |
| 12 | Monolith deletion timing unclear | LOW | **Accepted** — monolith is empty by Step 8, safe to delete in same commit |
| 13 | "No tests" conflicts with behavior changes | LOW | **Fixed** — 10 targeted tests for new behavioral paths |
| 14 | CLI flag `--codex-reasoning` backward compat needed | LOW | **No action** — `--codex-reasoning` as a global flag never existed in CLI. False claim was only in 05-gauntlet.md docs. |

---

## 22. Scope Exclusions

| Exclusion | Rationale |
|-----------|-----------|
| **Not refactoring phase internals** | Extract-as-is except the 6 Quota Burn fixes. Phase logic is complex LLM prompt engineering — changing it during a structural refactor risks introducing subtle bugs. Refactor first, improve later. |
| **Not adding full test suite** | 10 targeted tests for NEW behavioral paths (resume, atomic writes, validation). Existing phase logic has no tests today — adding them is a separate effort with different risk profile. |
| **Not renaming functions** | All internal function names preserved. Renaming during extraction adds unnecessary diff noise and makes bisect harder. |
| **Not removing `existing_system_compatibility`** | It's a real adversary in the `PRE_GAUNTLET` registry in adversaries.py. Used via `--pre-gauntlet` flag. Not dead code. |
| **Not adding `--codex-reasoning` backward-compat** | The global `--codex-reasoning` flag never existed in CLI. The false claim was only in 05-gauntlet.md docs. No backward compatibility needed because there's nothing to be backward-compatible with. |
| **Not unifying persistence with session.py** | Gauntlet persistence (checkpoint files, run manifests) and session persistence (session-state.json, session files) serve different purposes with different schemas and lifecycles. Unifying them would create coupling for no benefit. |
| **Not adding global timeout circuit breaker** | G-12 is a valid concern (no upper bound on total run time) but requires significant orchestrator changes (wall-clock timer, graceful phase cancellation, partial result assembly). Better as a separate feature. |
| **Not class-based orchestrator** | Functional `run_gauntlet()` preserves the existing contract. Class-based orchestrator would require debate.py integration changes for no concrete benefit. |
| **FIND-004 (tasks.json locking)** | Affects `mcp_tasks/server.py` and `task_manager.py`, not gauntlet. Different subsystem, different fix, different PR. |

### Process Failure Documentation

**What happened:** Ran 2 debate rounds + full gauntlet (9 adversaries, 75 concerns, ~32 minutes of LLM calls) without creating session-state.json, session file, or manifest. User had to prompt for these after the entire process completed.

**Root cause:** No enforcement gate at spec-session start. Claude can invoke `debate.py critique` and `debate.py gauntlet` without first initializing tracking artifacts. The adversarial-spec SKILL.md phases describe the workflow but nothing BLOCKS progress if artifacts are missing.

**Same failure class as:**
- Zombie pointer bug (Feb 9): session-state.json pointed to non-existent session file
- Execution plan not persisted (Feb 13): plan existed in conversation context but not on disk

**All three failures are "deliverable created in conversation context but not persisted to disk."**

**Fix:** Step 10 adds hard gate directive to 03-debate.md and 05-gauntlet.md:
> "Before the FIRST debate round on a new spec, Claude MUST create: (1) spec file at `.adversarial-spec/specs/<slug>/spec.md`, (2) manifest at `.adversarial-spec/specs/<slug>/manifest.json` with status `drafting`, (3) session file, (4) update session-state.json. This is a hard gate — do not proceed to debate or gauntlet without these artifacts."

---

## Appendix A: Source Line Mapping

Complete mapping of `gauntlet.py` functions to target modules. Lines reference the current monolith (4087 lines) with 4 hotfixes applied but not committed.

| Source Lines | Function/Class | Target Module |
|-------------|---------------|---------------|
| 33-37 | `FinalBossVerdict` enum | `core_types.py` |
| 92-112 | `REBUTTAL_PROMPT` | `phase_5_rebuttals.py` |
| 119-175 | `Concern`, `Evaluation`, `Rebuttal` | `core_types.py` |
| 177-337 | `BigPictureSynthesis`, `GauntletResult`, `Medal`, `ExplanationMatch`, `DismissalReviewStats`, `FinalBossResult` | `core_types.py` |
| 340-383 | `_VERDICT_NORMALIZE`, `normalize_verdict()` | `core_types.py` |
| 384-526 | Path constants, `load_adversary_stats()`, `save_adversary_stats()`, `update_adversary_stats()`, `save_gauntlet_run()`, `list_gauntlet_runs()`, `load_gauntlet_run()` | `persistence.py` |
| 528-632 | `load_resolved_concerns()`, `save_resolved_concerns()`, `get_spec_hash()`, `add_resolved_concern()`, `calculate_explanation_confidence()`, `record_explanation_match()`, `verify_explanation()` | `persistence.py` |
| 634-772 | `format_gauntlet_report()`, `get_adversary_leaderboard()` | `reporting.py` |
| 774-1095 | `MEDALS_DIR`, `_get_concern_keywords()`, `_concerns_are_similar()`, `calculate_medals()`, `generate_medal_report()`, `save_medal_reports()`, `format_medals_for_display()` | `medals.py` |
| 1097-1179 | `get_adversary_synergy()`, `format_synergy_report()` | `reporting.py` |
| 1181-1244 | `get_medal_leaderboard()` | `medals.py` |
| 1246-1391 | `_track_dedup_stats()` (DEPRECATED), related helpers | `persistence.py` |
| 1393-1399 | Additional type helpers | `core_types.py` |
| 1580-1627 | Additional dataclass fields | `core_types.py` |
| 1630-1709 | `BIG_PICTURE_PROMPT`, `generate_big_picture_synthesis()` | `phase_2_synthesis.py` |
| 1811-2138 | `run_final_boss_review()` + Final Boss prompt construction | `phase_7_final_boss.py` |
| 2145-2170 | `get_available_eval_models()` | `model_dispatch.py` |
| 2172-2340 | `evaluate_concerns_multi_model()` | `phase_4_evaluation.py` |
| 2347-2383 | `select_adversary_model()` | `model_dispatch.py` |
| 2385-2425 | `select_eval_model()`, `select_gauntlet_models()` | `model_dispatch.py` |
| 2432-2487 | `call_model()` | `model_dispatch.py` |
| 2494-2526 | `get_rate_limit_config()`, `_get_model_provider()` | `model_dispatch.py` |
| 2533-2728 | `generate_attacks()` (Phase 1) | `phase_1_attacks.py` |
| 2736-2758 | `choose_clustering_model()`, `_normalize_concern_text()` | `phase_3_filtering.py` |
| 2760-2940 | `cluster_concerns_with_provenance()`, `expand_clustered_evaluations()` | `phase_3_filtering.py` |
| 2942-2984 | `match_concern_to_explanation()`, `filter_concerns_with_explanations()` | `phase_3_filtering.py` |
| 2986-3103 | `evaluate_concerns()` (Phase 4) | `phase_4_evaluation.py` |
| 3111-3193 | `run_rebuttals()` (Phase 5) | `phase_5_rebuttals.py` |
| 3201-3283 | `final_adjudication()` (Phase 6) | `phase_6_adjudication.py` |
| 3290-3707 | `run_gauntlet()` (orchestrator) | `orchestrator.py` |
| 3710-3828 | Report formatting helpers | `reporting.py` |
| 3836-4087 | `main()` CLI entry point | `cli.py` |

**NEW code (not in monolith):**

| Target Module | New Functions/Classes |
|---------------|----------------------|
| `core_types.py` | `GauntletConfig`, `GauntletClusteringError`, `GauntletExecutionError`, `CheckpointMeta`, `PhaseMetrics` |
| `model_dispatch.py` | `_validate_model_name()` |
| `persistence.py` | `_load_json_safe()`, `_write_json_atomic()`, `_serialize_dataclass()`, `get_config_hash()`, `save_checkpoint()`, `load_partial_run()`, `save_partial_clustering()`, `save_run_manifest()`, `update_run_manifest()`, `load_run_manifest()`, `format_path_safe()` |
| `reporting.py` | `format_run_manifest()` |
| `orchestrator.py` | Resume logic, unattended enforcement, auto-checkpoint, manifest building, early model validation, KeyboardInterrupt handling |
| `cli.py` | `--unattended`, `--resume`, `--eval-codex-reasoning` flags |
| `__main__.py` | `from gauntlet.cli import main; main()` |

---

## Appendix B: Commit Strategy

One commit per step for clean `git bisect`:

| # | Commit Message | Risk | Reversible |
|---|----------------|------|------------|
| 0 | `refactor(gauntlet): scaffold package with shim` | LOW | Rename back |
| 1 | `refactor(gauntlet): extract core_types with GauntletConfig and GauntletClusteringError` | LOW | Types are side-effect-free |
| 2 | `refactor(gauntlet): extract model_dispatch with model name validation` | LOW | Pure functions |
| 3a | `refactor(gauntlet): extract persistence with filelock, resume loader, run manifest` | MEDIUM | New dependency |
| 3b | `fix(models): add threading.Lock to CostTracker` | LOW | One-line change |
| 4 | `refactor(gauntlet): extract medals` | LOW | Pure functions |
| 5 | `refactor(gauntlet): extract reporting with run manifest formatting` | LOW | Pure functions |
| 6 | `refactor(gauntlet): extract phases 1-7, strip hardcoded defaults, nuke silent catch-all` | MEDIUM | Core LLM logic |
| 7 | `refactor(gauntlet): extract orchestrator with config, resume, checkpoint, manifest` | HIGH | Hub of all deps |
| 8 | `refactor(gauntlet): extract cli + __main__.py, remove monolith` | LOW | Monolith empty |
| 8.5 | `feat(debate): wire --gauntlet-resume/--unattended/--eval-codex-reasoning into debate.py gauntlet` | MEDIUM | Main entry point |
| 9 | `docs: update architecture for gauntlet package` | LOW | Docs only |
| 10 | `docs: fix 05-gauntlet.md false claims, migrate python3 gauntlet.py references` | LOW | Docs only |

**Per-commit verification:** After EVERY commit, run the 3-command smoke check (§16).

---

## Appendix C: Gauntlet Run Statistics

| Metric | Value |
|--------|-------|
| Total adversaries | 9 (paranoid_security, burned_oncall, lazy_developer, pedantic_nitpicker, asshole_loner, prior_art_scout, assumption_auditor, information_flow_auditor, architect) |
| Attack model | gemini-cli/gemini-3-flash-preview |
| Eval models | codex/gpt-5.3-codex, gemini-cli/gemini-3-pro-preview |
| Raw concerns | 75 |
| After clustering | 42 |
| Accepted | 20 |
| Dismissed | 16 |
| Acknowledged | 4 |
| Deferred | 2 |
| Rebuttals challenged | 8 |
| Overturned | 1 |
| Final concerns | 23 |
| Concerns addressed in spec | 9 |
| Duration | 1897.1 seconds (~31.6 minutes) |

**Checkpoint files (all in `.adversarial-spec-gauntlet/`):**
- `concerns-d453f1d8.json` — 75 raw concerns
- `raw-responses-d453f1d8.json` — per-adversary raw LLM responses
- `evaluations-d453f1d8.json` — 42 clustered evaluations with verdicts

**Debate rounds (before gauntlet):**
- Pre-gauntlet Codex review: 14 findings (6 HIGH, 5 MEDIUM, 3 LOW), all addressed
- Round 1 (Codex 5.4 + Gemini): 10 findings, all addressed
- Round 2 (Codex 5.4 + Gemini): 12 findings, 9 addressed, 3 declined
