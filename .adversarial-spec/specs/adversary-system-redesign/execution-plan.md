# Execution Plan: Adversary System Redesign

## Summary
- Tasks: 11 (S: 4, M: 4, L: 2, docs: 1)
- Workstreams: 2 (Registry & Pipeline, Phase Docs & Tests)
- Gauntlet concerns addressed: 15/15 accepted findings mapped to tasks
- Estimated effort: 16-28 hours

## Test Strategy

| Task | Strategy | Reason |
|------|----------|--------|
| T1: AdversaryTemplate + aliases | test-after | Foundation types, key validation is medium risk |
| T2: minimalist + traffic_engineer | test-after | Data definitions, low risk |
| T3: GUARDRAILS registry | test-after | Data definitions, low risk |
| T4: SYNTHESIS_CATEGORIES | test-after | Single constant, trivial |
| T5: run_gauntlet() update | test-first | 5 concerns linked (FM-1, CB-4, CB-5, FM-4, US-3) |
| T6: generate_attacks() prompts | test-after | Small change, 0 direct concerns |
| T7: Eval model fix | test-after | Small fix, process failure prevention |
| T8: Concern parser replacement | test-first | HIGH risk, design-level rewrite |
| T9: synthesis_extract.py | test-first | Format correctness critical (DD-2) |
| T10: Phase docs | skip | Documentation only |
| T11: Test suite | — | IS the test task |

## Tasks

### Workstream A: Registry & Pipeline

#### T1: Add AdversaryTemplate dataclass, aliases, and resolver
- **Effort:** M (1-4hr)
- **Strategy:** test-after
- **Spec refs:** §1.1, §1.2, §7.2
- **Concerns:** CB-2 (ADVERSARIES alias claim), US-2 (scope_guidelines key validation)
- **File:** `scripts/adversaries.py`
- **Acceptance criteria:**
  - [ ] `AdversaryTemplate` frozen dataclass with all fields from §1.1 (name, prefix, tone, focus_areas, valid_dismissal, invalid_dismissal, valid_acceptance, rule, scope_guidelines, version)
  - [ ] `ADVERSARY_ALIASES: dict[str, str]` with `lazy_developer→minimalist`, `prior_art_scout→minimalist`
  - [ ] `resolve_adversary_name(name) → str` returns canonical name or pass-through
  - [ ] `ADVERSARY_TEMPLATES: dict[str, AdversaryTemplate]` — empty initially, populated in T2
  - [ ] `scope_guidelines` key validation: reject keys not matching `{category}:{value}` enum pairs (US-2)
  - [ ] `ADVERSARIES` dict does NOT contain alias entries — aliases live only in `ADVERSARY_ALIASES` (CB-2)
- **Dependencies:** None

#### T2: Add minimalist and traffic_engineer adversaries
- **Effort:** M (1-4hr)
- **Strategy:** test-after
- **Spec refs:** §2.1, §2.2, §2.3, §2.4, §2.5
- **File:** `scripts/adversaries.py`
- **Acceptance criteria:**
  - [ ] `minimalist` (MINI) in both `ADVERSARIES` and `ADVERSARY_TEMPLATES` with tone/focus from §2.1
  - [ ] `traffic_engineer` (TRAF) in both `ADVERSARIES` and `ADVERSARY_TEMPLATES` with tone/focus from §2.2
  - [ ] Remove `lazy_developer` and `prior_art_scout` from `ADVERSARIES`
  - [ ] PEDA focus_areas sharpened to data-level correctness (§2.3)
  - [ ] ASSH focus_areas sharpened to design-level correctness (§2.3)
  - [ ] BURN focus_areas extended with explicit recovery ownership (§2.4)
  - [ ] `ADVERSARY_PREFIXES` includes MINI, TRAF, retains LAZY, PREV for historical lookups
- **Dependencies:** T1

#### T3: Add GUARDRAILS registry
- **Effort:** S (<1hr)
- **Strategy:** test-after
- **Spec refs:** §4.1, §4.5, §4.6
- **Concerns:** CB-3 (CONS prompt is static, references guardrail-prompts.md)
- **File:** `scripts/adversaries.py`
- **Acceptance criteria:**
  - [ ] 3 `Adversary` instances: `consistency_auditor` (CONS), `scope_creep_detector` (SCOPE), `requirements_tracer` (TRACE)
  - [ ] `GUARDRAILS: dict[str, Adversary]` — separate from `ADVERSARIES` and `ADVERSARY_TEMPLATES`
  - [ ] Persona text matches static prompts in `guardrail-prompts.md` (CB-3)
  - [ ] Guardrail adversaries NOT in `ADVERSARIES` or `ADVERSARY_TEMPLATES`
- **Dependencies:** T1

#### T4: Add SYNTHESIS_CATEGORIES constant
- **Effort:** S (<1hr)
- **Strategy:** test-after
- **Spec refs:** §3.1
- **Concerns:** CB-1 (taxonomy as code constant)
- **File:** `scripts/gauntlet/core_types.py`
- **Acceptance criteria:**
  - [ ] `SYNTHESIS_CATEGORIES: list[str]` with exactly 8 categories from §3.1
  - [ ] Order matches spec (Correctness Bugs, Race Conditions, Failure Modes, Security, Operability, Scalability, Design Debt, Underspecification)
- **Dependencies:** None

#### T5: Update run_gauntlet() for dynamic prompts
- **Effort:** M (1-4hr)
- **Strategy:** test-first
- **Spec refs:** §1.6, §1.7, §5
- **Concerns:** FM-1 (hash mismatch → hard stop), CB-4 (dedup after alias resolution), CB-5/US-3 (unknown adversary → hard error), FM-4 (spec_hash via sha256sum, not LLM)
- **File:** `scripts/gauntlet/orchestrator.py`
- **Acceptance criteria:**
  - [ ] Load `approved-prompts.json` if it exists
  - [ ] Validate `spec_hash` — mismatch → halt with actionable error, NOT silent fallback (FM-1)
  - [ ] Resolve all adversary names via `resolve_adversary_name()`
  - [ ] Deduplicate after resolution — `lazy_developer` + `minimalist` both resolve to `minimalist`, emit one attack not two (CB-4)
  - [ ] Filter skipped adversaries BEFORE passing to `generate_attacks()` — skipped adversaries must not be in the list (§1.7 step 4)
  - [ ] Unknown adversary after resolution → hard error (CB-5)
  - [ ] Zero adversaries after filtering → `ValueError` hard stop
  - [ ] Extract flat `{name: full_persona}` dict from approved entries
  - [ ] Pass filtered list + prompts dict to `generate_attacks()`
- **Dependencies:** T1, T2

#### T6: Add prompts parameter to generate_attacks()
- **Effort:** S (<1hr)
- **Strategy:** test-after
- **Spec refs:** §1.7
- **File:** `scripts/gauntlet/phase_1_attacks.py`
- **Acceptance criteria:**
  - [ ] New `prompts: dict[str, str] | None = None` parameter
  - [ ] If `prompts` has key for adversary, use that persona text
  - [ ] If `prompts` is None or missing key, fall back to `ADVERSARIES[resolve_adversary_name(key)].persona`
  - [ ] Zero-length `adversaries` list → `ValueError`
  - [ ] No changes to system prompt template construction or downstream phases
- **Dependencies:** T1

#### T7: Fix eval model selection
- **Effort:** S (<1hr)
- **Strategy:** test-after
- **Spec refs:** §5 (gpt-5.3 process failure row)
- **File:** `scripts/gauntlet/model_dispatch.py`
- **Acceptance criteria:**
  - [ ] `get_available_eval_models()` prefers `codex/gpt-5.4` over `codex/gpt-5.3-codex`
  - [ ] If 5.4 unavailable, warn before falling back to 5.3
- **Dependencies:** None

#### T8: Replace deterministic concern parser
- **Effort:** L (4-8hr) — HIGH RISK
- **Strategy:** test-first
- **Spec refs:** §5 (Gemini parse failure row, quality gate row)
- **File:** `scripts/gauntlet/phase_1_attacks.py`
- **Acceptance criteria:**
  - [ ] Primary: structured output (JSON mode) for models that support it (Codex, Gemini)
  - [ ] Fallback: LLM extraction for responses that produce 0 parsed concerns from non-empty text
  - [ ] Minimum: anomaly detection — non-empty response + 0 concerns = parse failure → warn/halt
  - [ ] Quality gate after Phase 1: check each adversary×model pair, flag parse failures before Phase 2
  - [ ] No silent continuation after parse failures — pipeline halts or offers re-parse
  - [ ] Backward compatible: existing numbered-list format still parses correctly
- **Dependencies:** T6

#### T9: Create synthesis_extract.py
- **Effort:** M (1-4hr)
- **Strategy:** test-first
- **Spec refs:** §3.2, §3.3
- **Concerns:** DD-2 (no truncation — full text), CB-1 (prepend taxonomy header)
- **File:** `scripts/gauntlet/synthesis_extract.py` (new)
- **Acceptance criteria:**
  - [ ] CLI: `--run-log <path>` + `--output <path>`
  - [ ] Reads gauntlet run log JSON (from `save_gauntlet_run()`)
  - [ ] Output format: `[{id}] {adversary} | {severity} | verdict={pipeline_verdict} | {full_text}`
  - [ ] Full concern text — no truncation (DD-2)
  - [ ] Newlines in text replaced with spaces
  - [ ] All concerns included regardless of verdict
  - [ ] Sorted by concern ID for deterministic ordering
  - [ ] Prepends synthesis prompt header with 8 categories (§3.3)
  - [ ] Exit 0 for success, exit 0 for empty run log, exit 2 for invalid schema
  - [ ] No LLM calls — code-only extraction
- **Dependencies:** T4

### Workstream B: Phase Docs & Testing

#### T10: Update phase docs
- **Effort:** M (1-4hr)
- **Strategy:** skip (documentation)
- **Spec refs:** §4.2, §4.3, §4.7, §4.8, §7.1
- **Concerns:** FM-2 (depth limit), FM-3 (finalize all 3 guardrails), DD-3 (first-draft exemption), US-1 (invocation contract)
- **Files:** `phases/03-debate.md`, `phases/05-gauntlet.md`, `phases/06-finalize.md`
- **Acceptance criteria:**
  - [ ] `03-debate.md`: add guardrail step after each round incorporation (§4.2)
  - [ ] `03-debate.md`: max 2 CONS reruns, then defer to user (FM-2)
  - [ ] `03-debate.md`: SCOPE/TRACE can run on first draft; CONS cannot (DD-3)
  - [ ] `03-debate.md`: invocation contract — how Claude assembles guardrail inputs (US-1)
  - [ ] `05-gauntlet.md`: scope classification + prompt generation/review in Arm Adversaries
  - [ ] `05-gauntlet.md`: fix interaction validation for post-gauntlet incorporation (§4.8)
  - [ ] `06-finalize.md`: final guardrail pass runs all 3 (CONS + SCOPE + TRACE), not just CONS (FM-3)
- **Dependencies:** T3

#### T11: Test suite
- **Effort:** L (4-8hr)
- **Strategy:** —
- **Spec refs:** §6
- **Files:** `tests/` (new test files)
- **Acceptance criteria:**
  - [ ] Unit: `AdversaryTemplate` fixed fields never mutated during prompt assembly
  - [ ] Unit: `resolve_adversary_name()` — alias resolution for legacy names, unknown pass-through
  - [ ] Unit: `synthesis_extract.py` — all concerns extracted, deterministic sort, exact format, exit codes
  - [ ] Unit: scope_guidelines key validation rejects unknown keys
  - [ ] Integration: `run_gauntlet()` with approved prompts — skipped removed, approved override static
  - [ ] Integration: `run_gauntlet()` without approved-prompts.json — static fallback, full roster
  - [ ] Integration: hash mismatch → hard stop (not silent fallback)
  - [ ] Integration: all skipped → hard stop (not empty run)
  - [ ] Backward compat: `resolve_adversary_name("lazy_developer")` → `"minimalist"`
  - [ ] Guardrail registration: in GUARDRAILS, NOT in ADVERSARIES or ADVERSARY_TEMPLATES
  - [ ] Skip-filtering safety: skipped adversary does NOT execute via static fallback
- **Dependencies:** T1-T9 (all implementation tasks)

## Dependency Graph

```
T1 (template+aliases) ─┬─→ T2 (roster) ──→ T5 (run_gauntlet)
                        ├─→ T3 (guardrails) ──→ T10 (phase docs)
                        └─→ T6 (generate_attacks) ──→ T8 (parser) ──┐
                                                                      ├──→ T11 (tests)
T4 (categories) ──→ T9 (synthesis_extract) ──────────────────────────┘
T7 (eval model fix) ─────────────────────────────────────────────────┘
```

Critical path: T1 → T6 → T8 → T11

## Risk Register

| Task | Risk | Mitigation |
|------|------|------------|
| T8 (parser) | Highest — replacing working parser with structured output across 2+ model APIs | Test-first with golden files from existing gauntlet runs; keep old parser as fallback behind flag |
| T5 (run_gauntlet) | Medium — many behavioral changes in orchestration | Test-first; each acceptance criterion is a separate test case |
| T2 (roster) | Low-medium — removing 2 adversaries, historical data compat | ADVERSARY_PREFIXES retains old prefixes; run against historical concern files |

## Uncovered Concerns

- **DD-1 (registry unification):** Acknowledged as design debt, deferred. No task — revisit if fourth registry or cross-tier lookups emerge.
- **OP-1 (success metrics):** Acknowledged as out of scope. No task.
- **OP-2 (artifact cleanup):** Acknowledged as out of scope. No task.

## Implementation Order

Recommended sequence for a single agent:

1. T4 (SYNTHESIS_CATEGORIES) — trivial, unblocks T9
2. T1 (AdversaryTemplate + aliases) — foundation, unblocks everything
3. T7 (eval model fix) — independent, quick win
4. T3 (GUARDRAILS registry) — small, unblocks T10
5. T2 (roster — minimalist + traffic_engineer)
6. T6 (generate_attacks prompts param)
7. T5 (run_gauntlet update) — test-first, most complex orchestration
8. T9 (synthesis_extract.py) — test-first
9. T8 (concern parser replacement) — test-first, highest risk
10. T10 (phase docs)
11. T11 (test suite — fill gaps not covered by test-first tasks)
