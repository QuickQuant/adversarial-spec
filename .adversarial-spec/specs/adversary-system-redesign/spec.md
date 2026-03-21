# Adversary System Redesign: Dynamic Prompts, Roster, Taxonomy, and Checkpoint Guardrails

**Type:** Technical Spec | **Depth:** Technical | **Version:** 7 (post-gauntlet)

## Overview

Redesign the adversarial gauntlet's adversary system based on empirical findings from two BracketBattleAI process failure reports. Four changes: dynamic prompt generation, roster optimization, standard synthesis taxonomy, and checkpoint guardrails.

### Evidence Base

- **Synthesis failure report:** `BracketBattleAI/.adversarial-spec/process-failure-gauntlet-synthesis-v1-vs-v2.md` — haiku subagents dropped 48% of accepted concerns; code extraction + one Opus pass found 12 more
- **Contradiction failure report:** `BracketBattleAI/.adversarial-spec/process-failure-spec-internal-contradictions.md` — 10 internal contradictions survived 15 debate rounds + 9-adversary gauntlet, including a critical infinite retry loop introduced by incorporating a gauntlet fix
- **Extended commentary:** `extended commentary on adversaries.docx` — adversary-to-taxonomy mapping, scope-awareness gap, prompt rigidity analysis
- **Key finding:** The pipeline is optimized for finding architectural flaws and blind to editorial regressions. A single Codex pass found 10 contradictions the entire pipeline missed.

## Goals

1. **Dynamic prompts** — Replace static persona text with Claude-generated, scope-aware prompts that the user reviews before launch
2. **Roster optimization** — Merge redundant adversaries, add coverage for scalability gap
3. **Synthesis taxonomy** — Define the 8-category standard taxonomy as a code constant and prepend it to synthesis input, ensuring Claude always has the canonical categories available regardless of context eviction
4. **Checkpoint guardrails** — Lightweight adversaries that run after every spec revision to catch editorial regressions before they compound

## Non-Goals

- Changing the gauntlet pipeline phases (1-7) — those stay as-is
- Changing the evaluation/adjudication model selection
- Adding new pipeline phases to `debate.py`
- Changing the `Concern` or `Evaluation` data models (IDs, prefixes stay stable)
- Building standalone CLI tools for prompt review (Claude handles this conversationally)

---

## Getting Started (User Journey)

**Prerequisites:** Python 3.14+, `uv` package manager, Claude Code CLI installed and authenticated, the `adversarial-spec` skill deployed to `~/.claude/skills/adversarial-spec/`.

This system is a Claude Code skill — Claude is the interactive agent. There are no standalone CLI tools for prompt generation or review. The user journey is conversational:

1. **During debate** — after each round's changes are incorporated, Claude runs checkpoint guardrails (3 cheap checks) and surfaces any findings before proceeding to the next round
2. **Before gauntlet** — Claude reads the spec, classifies scope, generates dynamic prompts for the gauntlet adversaries, and presents them for user review
3. **During gauntlet** — `generate_attacks()` uses approved dynamic prompts (or static fallbacks)
4. **After gauntlet** — `synthesis_extract.py` extracts concerns for one-pass synthesis using standard taxonomy

**For a developer implementing this spec:**
1. Read `scripts/adversaries.py` — understand the `Adversary` dataclass and `ADVERSARIES` dict
2. Read `scripts/gauntlet/phase_1_attacks.py` — understand how personas become system prompts
3. Implement guardrail adversaries first (Section 4) — they're the highest-value change. Add `Adversary` instances + `GUARDRAILS` dict to `adversaries.py`.
4. Add `AdversaryTemplate`, `ADVERSARY_TEMPLATES` dict, `minimalist`, `traffic_engineer` to `adversaries.py`
5. Add `prompts` override to `generate_attacks()` in `scripts/gauntlet/orchestrator.py`
6. Add `synthesis_extract.py`
7. Update phase docs (`03-debate.md`, `05-gauntlet.md`, `06-finalize.md`)
8. Test with a real debate + gauntlet run

---

## 1. Dynamic Adversary Prompts

### Problem

Current adversary personas in `adversaries.py` are static strings. Every spec gets the same prompt regardless of:
- **Scope** — a local CLI tool vs a web app exposed to the internet
- **Domain** — a database migration vs a user-facing API vs an internal refactor
- **Risk surface** — specs with auth/payment flows need deeper security review than specs adding a CLI flag

The `asshole_loner` adversary produces unique findings precisely because its provocative tone forces the model into a different reasoning path than a polite reviewer would take. Static prompts preserve this — but they also mean the security adversary wastes tokens on localhost apps, and the operability adversary misses domain-specific failure modes.

### Design

#### 1.1 Prompt Template Structure

Each adversary gets a **template** instead of a static persona. The template has fixed and dynamic sections:

```python
@dataclass(frozen=True)
class AdversaryTemplate:
    name: str                      # e.g., "paranoid_security"
    prefix: str                    # e.g., "PARA" — stable, never changes
    tone: str                      # Fixed personality/voice (the "flavor")
    focus_areas: list[str]         # Fixed list of what this adversary cares about
    valid_dismissal: str           # Fixed — dismissal criteria don't change
    invalid_dismissal: str         # Fixed
    valid_acceptance: str | None   # Fixed
    rule: str                      # Fixed — one-line summary rule (from current Adversary)
    scope_guidelines: dict[str, str]  # "{category}:{value}" → guidance text
    version: str = "2.0"
```

**What's fixed (never changes per-spec):**
- `tone` — the personality voice ("You see threats EVERYWHERE", "You're the grumpy senior dev who's seen it all")
- `valid_dismissal` / `invalid_dismissal` / `valid_acceptance` / `rule` — the evaluation rules
- `prefix` — concern ID generation

**What's dynamic (generated per-spec by Claude):**
- The assembled `persona` string — combining tone + scope-specific guidance + spec-relevant focus
- Depth of investigation instructions — e.g., for a web app, security adversary gets "enumerate every input vector, check auth on every endpoint, look up OWASP top 10 for this stack"

#### 1.2 Scope Classification

Claude classifies the spec's scope inline (no separate LLM call — Claude is already reading the spec during the Arm Adversaries step):

```json
{
  "exposure": "public-internet | internal-network | local-only",
  "domain": "user-facing-api | data-pipeline | cli-tool | library | infrastructure",
  "risk_signals": ["auth", "payments", "PII", "external-integrations"],
  "stack": ["python", "fastapi", "redis"]
}
```

Claude presents this classification to the user before generating prompts:

```
Scope Classification
═══════════════════════════════════════
Exposure: public-internet
Domain: user-facing-api
Risk signals: auth, payments, external-integrations
Stack: Python, FastAPI, Redis, S3

[Confirm] [Adjust]
```

This classification drives which `scope_guidelines` sections are activated per adversary. The keys in each template's `scope_guidelines` dict use `{category}:{value}` format (e.g., `"exposure:public-internet"`, `"domain:cli-tool"`, `"risk_signals:auth"`). Claude matches the classification output against these keys to select relevant guidance.

**Key validation:** The set of valid keys is the Cartesian product of category names (`exposure`, `domain`, `risk_signals`, `stack`) and their enum values (e.g., `exposure` → `public-internet | internal-network | local-only`). On template registration, validate that every key in `scope_guidelines` matches a known `{category}:{value}` pair. Reject unknown keys with a clear error — a typo like `"exposure:public_internet"` (underscore vs hyphen) would silently omit that guidance for all public-internet specs.

#### 1.3 Prompt Generation Flow

This happens during the existing "Arm Adversaries" step in `05-gauntlet.md`, not as a separate pipeline:

```
1. Claude reads spec + classifies scope (1.2 above)
2. For each adversary template:
   a. Start with fixed `tone`
   b. Select relevant `scope_guidelines` based on scope classification
   c. Generate 2-4 sentences of spec-specific focus ("For THIS spec, pay attention to X, Y, Z")
   d. Assemble into full persona string
3. Present ALL generated prompts to user for review (1.4 below)
4. User approves / edits / skips individual adversaries
5. Claude writes approved prompts to `.adversarial-spec-gauntlet/approved-prompts.json`
6. Approved prompts are passed to generate_attacks() via the `prompts` parameter
```

#### 1.4 User Review Gate

Claude presents generated prompts conversationally:

```
Generated Adversary Prompts
═══════════════════════════════════════

PARA (paranoid_security):
  Tone: [fixed tone excerpt]
  Scope additions: "This is a public API with auth. Enumerate every
    input vector. Check token validation on all endpoints. Look up
    OWASP top 10 for Python/FastAPI."
  Status: active

BURN (burned_oncall):
  Tone: [fixed tone excerpt]
  Scope additions: "External dependency on Redis + S3. Check timeout
    configs, retry policies, circuit breaker patterns. What happens
    when Redis is down?"
  Status: active

MINI (minimalist):  [MERGED from lazy_developer + prior_art_scout]
  Tone: [fixed tone excerpt]
  Scope additions: "FastAPI has built-in validation, Pydantic models,
    dependency injection. Check if spec reinvents any of these."
  Status: active

...

[Approve all] [Edit specific] [Skip specific] [Regenerate all]
```

User responds in natural language. Claude updates the prompt set accordingly.

#### 1.5 Skipping Adversaries by Scope

Some adversaries become irrelevant for certain scopes:

| Scope | Candidates to skip |
|-------|-------------------|
| local-only CLI tool | PARA (no attack surface), FLOW (no external data flow) |
| Pure library (no I/O) | PARA, BURN (no runtime ops), FLOW |
| Internal refactor | PARA (attack surface unchanged), AUDT (no new external deps) |

**Skipping is always a user decision**, not automatic. Claude recommends skips with reasoning; user confirms.

#### 1.6 Prompt State Artifact

Approved prompts are persisted so `generate_attacks()` can consume them:

**File:** `.adversarial-spec-gauntlet/approved-prompts.json`

```json
{
  "spec_hash": "a1b2c3d4e5f6",
  "scope": {
    "exposure": "public-internet",
    "domain": "user-facing-api",
    "risk_signals": ["auth", "payments"],
    "stack": ["python", "fastapi"]
  },
  "prompts": {
    "paranoid_security": {
      "prefix": "PARA",
      "status": "approved",
      "full_persona": "You see threats EVERYWHERE. For THIS spec, pay attention to..."
    },
    "minimalist": {
      "prefix": "MINI",
      "status": "skipped",
      "skip_reason": "User skipped: internal refactor only."
    }
  },
  "generated_at": "2026-03-21T16:30:00Z"
}
```

**`spec_hash` generation:** SHA-256 hex digest of the raw spec file contents (UTF-8 encoded), truncated to first 12 characters. Matches the existing `spec_hash` convention used in gauntlet checkpoint filenames. Claude generates this by running `sha256sum <spec-file> | cut -c1-12` via the Bash tool — Claude cannot natively compute SHA-256 hashes, and LLM-generated hashes are hallucinations.

**`status` enum:** `approved` | `skipped`. `full_persona` required for `approved`, `null` for `skipped`. `skip_reason` required for `skipped`, `null` for `approved`.

**Spec hash mismatch handling:** If the caller finds `approved-prompts.json` but the spec hash doesn't match, `run_gauntlet()` emits a warning to stderr and halts with a clear message: "Approved prompts are stale (spec changed since generation). Re-run Arm Adversaries to regenerate prompts, or pass `--force-static-fallback` to proceed with static personas." Silent fallback to static personas is NOT acceptable — it silently disables the entire dynamic prompt feature after any spec revision, which is the exact failure mode this redesign targets.

#### 1.7 Integration with `run_gauntlet()` and `generate_attacks()`

**`run_gauntlet()` in `orchestrator.py` is the integration point.** It owns:

1. Loading `approved-prompts.json` (if it exists)
2. Validating `spec_hash` — mismatch → halt with actionable error ("re-run Arm Adversaries or pass `--force-static-fallback`"). Silent fallback is not acceptable.
3. Resolving all adversary names via `resolve_adversary_name()` and **deduplicating** — if a user specifies both `lazy_developer` and `minimalist`, both resolve to `minimalist` and the duplicate must be removed
4. Filtering the resolved+deduped list to remove any adversary with `status: "skipped"` — **skipped adversaries must not appear in the list passed to `generate_attacks()`, or they will execute via static fallback**
5. Extracting a flat `dict[str, str]` from approved entries: `{name: entry["full_persona"]}`
6. Passing the filtered `adversaries` list AND the flat `prompts` dict to `generate_attacks()`
7. If zero adversaries remain after filtering → hard stop with `ValueError`

**`generate_attacks()` in `phase_1_attacks.py`** gains one optional parameter:

```python
def generate_attacks(
    spec: str,
    adversaries: list[str],
    models: list[str] | str,
    config: GauntletConfig,
    prompts: dict[str, str] | None = None,  # NEW: {adversary_name: full_persona_text}
) -> tuple[list[Concern], dict[str, float], dict[str, str]]:
```

**Behavior:**
- If `prompts` is provided and contains a key for the adversary, use that persona text
- If `prompts` is `None` or missing the adversary key, fall back to `ADVERSARIES[resolve_adversary_name(key)].persona` (current behavior)
- `generate_attacks()` assumes the `adversaries` list is already filtered — it does NOT read or parse `approved-prompts.json` directly
- Zero-length `adversaries` list is a hard stop with `ValueError`

**No changes to:** system prompt template construction, model dispatch, concern parsing, or any downstream phases.

---

## 2. Roster Optimization

### Problem

Empirical findings from 2 gauntlet runs:

| Gap | Evidence |
|-----|----------|
| **PREV + LAZY overlap** | Both challenge complexity. Combined 0/23 accepted concerns in BracketBattleAI gauntlet. Their findings overlap almost entirely. |
| **PEDA + ASSH overlap** | Both find correctness bugs. ASSH's hostile tone produces *different* findings but the *category* overlaps with PEDA's edge-case analysis. |
| **Scalability gap** | No primary adversary for throughput, fan-out, concurrency limits, thundering herds. BURN touches it but focuses on operability. |
| **Recovery gap** | No adversary focuses specifically on recovery path correctness. BURN + FLOW share this but neither owns it. Explicitly assign recovery to `burned_oncall`. |

### Changes

#### 2.1 Merge: PREV + LAZY -> `minimalist`

**New adversary:** `minimalist` (prefix: `MINI`)

Combines:
- LAZY's "prove this complexity is necessary" challenge
- PREV's "check if this already exists in the codebase/ecosystem" search

**Tone:** The pragmatic senior dev who's seen over-engineering kill projects. Not hostile (that's ASSH's job), but relentlessly practical. "Show me why the simple version doesn't work."

**Focus areas:**
- Unnecessary abstraction layers
- Reinventing framework builtins
- Existing code/SDK that already does this
- Over-scoped APIs (building for hypothetical future)

**Impact on concern IDs:** New prefix `MINI` for new runs. Old `LAZY-*` and `PREV-*` IDs remain valid in historical data. No migration needed.

#### 2.2 Add: `traffic_engineer`

**New adversary:** `traffic_engineer` (prefix: `TRAF`)

Fills the scalability gap.

**Tone:** The performance engineer who's been paged at 3 AM because a fan-out storm took down production. Thinks in terms of request rates, queue depths, and thundering herds.

**Focus areas:**
- Fan-out amplification (1 request triggers N downstream)
- Thundering herd on cache expiry / cold start
- Unbounded pagination / scan operations
- Connection pool exhaustion under load
- Hot partition / hot key patterns
- Concurrency limits vs expected throughput

**Valid dismissal:** Must cite specific mitigation: rate limiter config, backpressure mechanism, bounded queue with overflow policy.

**Invalid dismissal:** "We'll scale later", "That's a lot of traffic" (how much? what's the limit?), "The cloud handles it" (which service? what's its limit?).

#### 2.3 Differentiate: PEDA vs ASSH

Don't merge (they produce different findings via different tones), but sharpen their briefs:
- **PEDA** focuses on *data-level* correctness: types, nullability, encoding, precision, schema constraints, boundary values
- **ASSH** focuses on *design-level* correctness: abstraction leaks, API contract violations, state machine gaps, invariant violations

Update their `focus_areas` in the template to make this split explicit. No name/prefix changes.

#### 2.4 Explicit recovery ownership

`burned_oncall` explicitly owns: degraded mode, recovery paths, failover/failback, circuit breakers, retry loops, partial recovery correctness. This was previously shared with FLOW but neither owned it. Add to `burned_oncall`'s `focus_areas`.

#### 2.5 Updated Gauntlet Roster (9 adversaries)

| # | Name | Prefix | Primary Category | Notes |
|---|------|--------|-----------------|-------|
| 1 | `paranoid_security` | PARA | Security | Unchanged |
| 2 | `burned_oncall` | BURN | Operability / Failure Modes | Recovery ownership explicit (recovery is a subset of Failure Modes) |
| 3 | `minimalist` | MINI | Design Debt | **NEW** — merged PREV + LAZY |
| 4 | `pedantic_nitpicker` | PEDA | Correctness (data-level) | Sharpened focus |
| 5 | `asshole_loner` | ASSH | Correctness (design-level) | Sharpened focus |
| 6 | `assumption_auditor` | AUDT | Underspecification | Unchanged |
| 7 | `information_flow_auditor` | FLOW | Underspecification / Failure Modes | Unchanged |
| 8 | `architect` | ARCH | Design Debt / Underspecification | Unchanged |
| 9 | `traffic_engineer` | TRAF | Scalability | **NEW** |

**Special phases (unchanged):**
- Pre-gauntlet: `existing_system_compatibility` (COMP)
- Final boss: `ux_architect` (UXAR)

#### 2.6 Adversary-to-Taxonomy Coverage Matrix

| Taxonomy Category | Primary | Secondary |
|-------------------|---------|-----------|
| Correctness Bugs | PEDA, ASSH | — |
| Race Conditions | PEDA, FLOW | AUDT |
| Failure Modes | BURN | FLOW |
| Security | PARA | — |
| Operability | BURN | — |
| Scalability | **TRAF** | BURN |
| Design Debt | MINI, ARCH | ASSH |
| Underspecification | FLOW, AUDT | ARCH |

Every category now has a primary adversary. No gaps.

---

## 3. Synthesis Taxonomy Enforcement

### Problem

The phase doc now mandates the 8-category taxonomy, but the gauntlet pipeline code doesn't enforce it. The taxonomy exists only in `05-gauntlet.md` prose. If Claude doesn't read that section (context eviction, different session), synthesis falls back to ad-hoc theming.

### Design

#### 3.1 Taxonomy as Code

Add to `core_types.py`:

```python
SYNTHESIS_CATEGORIES: list[str] = [
    "Correctness Bugs",
    "Race Conditions",
    "Failure Modes",
    "Security",
    "Operability",
    "Scalability",
    "Design Debt",
    "Underspecification",
]
```

#### 3.2 Extraction Script

Add `scripts/gauntlet/synthesis_extract.py` — a code-only tool (no LLM calls) that extracts concerns into a compact format for one-pass synthesis:

```bash
uv run python scripts/gauntlet/synthesis_extract.py \
  --run-log .adversarial-spec-gauntlet/run-TIMESTAMP-HASH.json \
  --output .adversarial-spec-gauntlet/synthesis-input-HASH.txt
```

The `--run-log` takes the final gauntlet run log produced by `save_gauntlet_run()` — this is the most reliable source of truth containing evaluations, verdicts, and full concern details. Claude runs this script autonomously during the synthesis step.

**Output format:** One line per concern, exactly:
```
[{id}] {adversary} | {severity} | verdict={pipeline_verdict} | {text}
```

Text is the full concern text with newlines replaced by spaces (no truncation). The previous 150-char truncation design was rejected because it loses the specific details (variable names, section references, numeric values) that Claude needs for accurate categorization. One-line-per-concern keeps the format scannable while preserving full content. For a typical gauntlet run (100-200 concerns × ~200 chars each), this produces a ~40-80K token synthesis input — well within Claude's context budget.

Example:
```
[BURN-a3f7c912] burned_oncall | high | verdict=accepted | Redis outage handling is underspecified and can produce cross-instance split-brain when the primary goes down and two secondaries both promote themselves to primary before the sentinel quorum resolves.
[PEDA-940f4d7c] pedantic_nitpicker | medium | verdict=deferred | HTTP header injection via query fingerprint in ETag — unsanitized query params stuffed into the ETag value without encoding, allowing cache poisoning via crafted query strings.
```

Newlines within concern text replaced with spaces. All concerns included regardless of verdict. Output sorted by concern ID for deterministic ordering. Prepended with the synthesis prompt header (Section 3.3).

**What it does NOT do:** Make LLM calls, filter concerns, or assign categories. Those are Claude's job during synthesis.

#### 3.3 Synthesis Prompt Header

The extraction script prepends this to the output file:

```
You are synthesizing gauntlet results into the standard taxonomy.

Categories (use EXACTLY these — do not invent new ones):
1. Correctness Bugs — implementation contradictions, data integrity, logic errors
2. Race Conditions — concurrency, ordering, lease violations
3. Failure Modes — recovery cascades, degraded mode, cold start
4. Security — injection, enumeration, PII leakage, auth bypass
5. Operability — monitoring, deployment, retention, memory budgets
6. Scalability — fan-out storms, thundering herds, unbounded operations
7. Design Debt — over-scoping, modularity, unnecessary complexity
8. Underspecification — missing details that block implementation

For each concern: assign ONE primary category, verdict (accept/acknowledge/dismiss), one-line summary.
Group by category in output. Do NOT pre-filter by pipeline verdict — evaluate ALL concerns.
```

---

## 4. Checkpoint Guardrails

### Problem

The BracketBattleAI contradiction report proved that spec-internal contradictions are introduced during the *incorporation* step — when debate/gauntlet findings are merged into the spec. 7 of 10 contradictions were created by incorporating gauntlet concerns into detail sections without updating summary sections. The most dangerous (§5.1/§8.4 infinite retry loop) was created by a gauntlet fix that was correct in isolation but created a composition bug with existing behavior.

The full gauntlet runs once, after debate consensus. By that point, 10+ rounds of incorporation may have introduced contradictions that compound with each revision. The gauntlet adversaries are designed to find architectural flaws, not editorial regressions.

### Design: Two-Tier Adversary System

The adversary system splits into two tiers:

| Property | Guardrails (Tier 1) | Gauntlet Adversaries (Tier 2) |
|----------|-------------------|------------------------------|
| **When** | After every substantive spec revision | Once, after debate consensus |
| **Cost** | 1 cheap model call each (3 total) | N adversaries × M models |
| **What they find** | Editorial regressions, drift, orphaned references | Architectural flaws, security holes, scalability limits |
| **Depth** | Document-level cross-referencing | Design-level analysis |
| **Run by** | Claude inline during debate phase | `generate_attacks()` pipeline |
| **Blocking** | Findings must be resolved before next round | Findings incorporated in finalize phase |

#### 4.1 Guardrail Adversaries

Three guardrail adversaries run as a "mini-gauntlet" after each spec revision:

##### `consistency_auditor` (CONS)

**Purpose:** Cross-section reference integrity. Catches contradictions introduced by revision.

**Checks:**
- Summary sections vs detail sections (do they agree?)
- Function/type names match between definition and usage sites
- Numeric values that appear in multiple places are arithmetically consistent (latency budgets, retry counts, TTLs, batch sizes)
- Scope definitions that appear in multiple places use the same boundaries
- Phase/commit descriptions match what's actually specified in each phase
- Inline comments and docs match the formal definitions they reference

**Tone:** Technical editor who's been burned by specs that contradict themselves. Doesn't care about architecture quality — only cares about internal consistency.

**Prompt:** CONS uses a static prompt (see `guardrail-prompts.md`) that does NOT reference which sections changed. It audits the entire spec for cross-section contradictions every time. This is intentional — knowing which sections changed risks anchoring the check and missing downstream contradictions in unchanged sections.

**Valid finding:** Section A says X, section B says not-X, and both are about the same thing.
**Invalid finding:** Style preferences, missing sections, architectural opinions.

##### `scope_creep_detector` (SCOPE)

**Purpose:** Catches scope drift that accumulates over multiple debate rounds.

**Checks:**
- Are non-goals still non-goals? (Has anything listed in non-goals appeared in the spec body?)
- Has the problem statement changed from the original requirements?
- Are there new sections that weren't in the original roadmap and weren't explicitly approved?
- Has the spec grown beyond the original user stories?
- Are there features that no user story justifies?

**Tone:** The project manager who's seen feature creep kill projects. "Is this still the same project we started?"

**Prompt structure:** "Here is the original problem statement / requirements: [from session]. Here is the current spec. Identify any scope that has crept in — features, sections, or requirements that weren't in the original scope and weren't explicitly approved as additions."

**Input:** Requires access to the original requirements summary (from session file) alongside the current spec.

**Valid finding:** Feature X appears in the spec but isn't in any user story and wasn't an explicit scope addition.
**Invalid finding:** Legitimate scope additions that were discussed and approved during debate.

##### `requirements_tracer` (TRACE)

**Purpose:** Verifies spec-vs-roadmap coverage after revisions.

**Checks:**
- Does every user story from the roadmap still have coverage in the spec?
- Has any user story's implementation been revised away, contradicted, or orphaned?
- Are there acceptance criteria from the roadmap that the spec no longer satisfies?
- Do test cases still map to spec sections?

**Tone:** QA lead checking traceability matrix. "Can I still trace every requirement to an implementation?"

**Prompt structure:** "Here are the user stories and acceptance criteria from the roadmap: [from manifest]. Here is the current spec. For each user story, confirm it still has coverage. Report any stories that are orphaned, contradicted, or whose acceptance criteria are no longer met by the spec."

**Input:** Requires access to the roadmap manifest alongside the current spec.

**Valid finding:** User story US-3 required X, but the spec revision in §9 removed the section that implemented X.
**Invalid finding:** Suggestions for new user stories, or complaints about implementation quality.

#### 4.2 When Guardrails Run

**Trigger:** After every substantive spec revision during the debate phase. "Substantive" means changes to requirements, architecture, data models, or behavior — not typo fixes or formatting.

**Integration point:** The debate phase doc (`03-debate.md`) already has a "synthesize and revise" step after each round. Guardrails are added as a mandatory sub-step:

```
After incorporating Round N critiques into the spec:

1. Run checkpoint guardrails (CONS, SCOPE, TRACE)
2. If any findings:
   a. Fix contradictions (CONS) before proceeding
   b. Present scope additions (SCOPE) for user approval or removal
   c. Restore orphaned coverage (TRACE) or explicitly descope with user approval
3. If CONS fix introduces a new contradiction (detected on re-run), defer to user after 2 attempts — do not loop indefinitely
4. Only after guardrails pass (or user explicitly overrides): proceed to Round N+1
```

**Cost model:**
- 3 model calls per checkpoint
- CONS: spec (~5-20K tokens) + prompt (~500 tokens) = ~5.5-20.5K per call
- SCOPE: spec (~5-20K) + original requirements (~2-10K) + prompt (~500) = ~7.5-30.5K per call
- TRACE: spec (~5-20K) + roadmap/acceptance criteria (~2-10K) + prompt (~500) = ~7.5-30.5K per call
- Use a cheap/free model (Gemini Flash, or Claude inline if spec fits in context)
- Total: ~20-80K input tokens per checkpoint, ~3K output tokens
- For a 5-round debate: ~100-400K additional tokens total

#### 4.3 Invocation Contract

Guardrails are invoked by Claude conversationally — no Python script wraps them. Claude:

1. Reads the guardrail prompt from `guardrail-prompts.md` (CONS, SCOPE, or TRACE)
2. Assembles the model input:
   - **CONS:** prompt + current spec text
   - **SCOPE:** prompt + original requirements (from session file `requirements_summary`) + current spec text
   - **TRACE:** prompt + roadmap manifest (user stories + acceptance criteria) + current spec text
3. Sends the assembled input to a model via `debate.py critique --model <model> --system-prompt <guardrail-prompt>` or, if the spec fits in Claude's own context, evaluates inline without an external call
4. Presents findings to the user in the format below (§4.4)

**No new Python tooling is needed.** The existing `debate.py critique` command supports `--system-prompt` for custom system prompts. Alternatively, Claude can make the model call inline if the spec + requirements fit within context.

**Session file dependency:** SCOPE and TRACE require data from the session file. If `requirements_summary` (SCOPE) or the roadmap manifest (TRACE) is missing from the session, Claude warns the user and skips that guardrail rather than running it without the external input — running SCOPE without the original requirements would produce false positives.

#### 4.4 Guardrail Output Format

Guardrails produce lightweight, actionable output — not the full gauntlet concern format:

```
Checkpoint Guardrails — Post-Round 3
═══════════════════════════════════════

CONS (consistency_auditor): 2 findings
  1. §5.1 says ensureLeaderboardSnapshot() checks existence only,
     but §8.4 falls through to it expecting validation. → CONTRADICTION
  2. §15 latency budget: 5s + 3s ≠ 5s. → ARITHMETIC ERROR

SCOPE (scope_creep_detector): 1 finding
  1. §10.8 CTA behavior not in any user story. Added in R2 without
     explicit scope approval. → SCOPE ADDITION (needs approval)

TRACE (requirements_tracer): 0 findings
  All user stories have coverage. ✓

[Fix CONS findings] [Approve/remove SCOPE additions] [Proceed to R4]
```

#### 4.5 Guardrails Do NOT

- Run during gauntlet attack phases (gauntlet adversaries handle deep analysis). Note: CONS does run after gauntlet fix *incorporation* (§4.8) and in the finalize phase (§4.7) — these are post-gauntlet editorial checks, not attack phases.
- Produce formal `Concern` objects with IDs (they're lightweight inline checks)
- Block the user from overriding (user can always say "proceed anyway")
- Make architectural judgments (that's the gauntlet's job)
- Run CONS on the first draft (CONS compares sections against each other within the same spec — only meaningful after revision introduces cross-section drift). **SCOPE and TRACE CAN run on the first draft** because they compare the spec against external inputs (requirements and roadmap, respectively), which exist before the first draft is written.

#### 4.6 Guardrail Adversary Registration

Guardrail adversaries are registered separately from gauntlet adversaries. They use the existing `Adversary` dataclass (not `AdversaryTemplate`) because their prompts are static — no scope-aware generation needed.

```python
# Guardrails use Adversary (static prompts)
GUARDRAILS: dict[str, Adversary] = {
    "consistency_auditor": CONSISTENCY_AUDITOR,
    "scope_creep_detector": SCOPE_CREEP_DETECTOR,
    "requirements_tracer": REQUIREMENTS_TRACER,
}

# Gauntlet adversaries use AdversaryTemplate (dynamic prompts)
ADVERSARY_TEMPLATES: dict[str, AdversaryTemplate] = { ... }
```

Guardrail adversaries are never included in `ADVERSARIES` (gauntlet roster) or passed to `generate_attacks()`. They're invoked by Claude during the debate phase, not by the pipeline.

#### 4.7 Finalize Phase Integration

In addition to running during debate, all three guardrails run once more during the finalize phase (`06-finalize.md`) as part of the quality checklist:

> **Final Guardrail Pass (REQUIRED):** After all revisions are complete, run all three guardrails:
> - **CONS:** Cross-reference consistency — every file in implementation plans matches module structure, every function name matches definitions, every numeric claim is arithmetically consistent, every "deferred" item does not also appear as in-scope
> - **SCOPE:** Scope integrity — verify the final spec hasn't drifted beyond the approved requirements, especially after gauntlet fix incorporation which can introduce scope additions disguised as bug fixes
> - **TRACE:** Requirements coverage — verify no user story was orphaned during the finalize revisions; this is the last chance to catch dropped requirements before execution planning

#### 4.8 Gauntlet Fix Interaction Validation

When incorporating gauntlet findings into the spec, Claude must validate interactions before each fix:

1. Identify which other sections/behaviors the fix interacts with
2. Verify the fix doesn't create a new failure mode in combination with existing behavior
3. Run CONS after incorporating the batch of fixes

This addresses the root cause of contradiction #2 (FM-1 + §5.1 composition bug): the fix "don't delete manifest on validation failure" should have triggered the question "what does `ensureLeaderboardSnapshot()` do when a manifest exists?"

---

## 5. Error Handling

| Scenario | Behavior |
|----------|----------|
| `approved-prompts.json` missing when gauntlet runs | Warning + fall back to static personas |
| `approved-prompts.json` spec hash mismatch | Hard stop — print actionable error ("re-run Arm Adversaries or pass `--force-static-fallback`"). Silent fallback silently disables the redesign. |
| Adversary name not in `ADVERSARIES`, `ADVERSARY_TEMPLATES`, or `GUARDRAILS` after alias resolution | Hard error — unknown adversaries indicate roster misconfiguration. Silently reducing coverage is the failure mode this redesign prevents. |
| Legacy name (`lazy_developer`, `prior_art_scout`) | Resolved via `resolve_adversary_name()` → canonical name, proceed |
| `synthesis_extract.py` given empty or invalid run log | Output header only, 0 concerns (exit 0 for empty, exit 2 for invalid schema) |
| User edits prompt to empty string | Treat as skip |
| Zero active adversaries after filtering | Hard stop with clear error |
| CONS model call fails | Hard stop — consistency check is mandatory, retry or switch models |
| SCOPE or TRACE model call fails | Soft stop — warn and require explicit user approval to proceed without |
| Corrupt JSON in any artifact file | Hard crash with ValueError, never silently ignore |
| `get_available_eval_models()` selects gpt-5.3 for evaluation | **Process failure.** gpt-5.3 is cheaper but produces lower-quality verdicts than gpt-5.4. The cost tradeoff is not worth it for evaluation/adjudication where verdict quality matters. Fix: `model_dispatch.py` must prefer `codex/gpt-5.4` over `codex/gpt-5.3-codex` in eval model auto-selection. |
| Gemini returns 0 parsed concerns despite non-empty response | **Parse failure — design-level flaw.** The root cause is NOT the `###` format. The root cause is using deterministic string parsing (`line[0].isdigit()`) on variable LLM output. Fix hierarchy: (1) Use structured output mode (JSON) where the model supports it — both Codex and Gemini do. (2) If structured output unavailable, add LLM extraction fallback for responses that produce 0 parsed concerns from non-empty text. (3) Minimal fix: detect anomaly (non-empty response + 0 concerns = parse failure) and warn/halt rather than silently continuing. Empirically, 6/9 Gemini adversary responses were silently lost in one gauntlet run. |
| Pipeline continues after silent parse failures | **Quality gate missing.** Phase 1 has no validation between "parse responses" and "proceed to Phase 2." When 6/9 Gemini adversary×model pairs returned 0 parsed concerns, the pipeline silently dropped ~25% of expected attack diversity and continued through clustering and evaluation. Fix: after Phase 1 completes, check each adversary×model pair — if response was non-empty but concerns=0, flag as parse failure and halt (or offer to re-parse with fallback). |

---

## 6. Testing Strategy

- **Unit tests for `AdversaryTemplate`:** Verify fixed fields (tone, dismissal rules, rule) are never mutated during prompt assembly
- **Unit tests for `resolve_adversary_name()`:** Verify alias resolution for legacy names; verify unknown names pass through unchanged
- **Unit tests for `synthesis_extract.py`:** Verify all concerns extracted from run log regardless of verdict; verify deterministic sort order; verify exact output format; verify exit codes (0 for success, 2 for invalid schema)
- **Integration test for `run_gauntlet()` with approved prompts:** Verify skipped adversaries are removed from roster before `generate_attacks()` is called; verify approved personas override static fallbacks
- **Integration test for fallback:** Verify `run_gauntlet()` without `approved-prompts.json` uses static personas and full default roster; verify hash mismatch triggers fallback
- **Backward compatibility test:** Verify `resolve_adversary_name("lazy_developer")` → `"minimalist"` and `resolve_adversary_name("prior_art_scout")` → `"minimalist"`
- **Zero-active test:** Verify all adversaries skipped produces hard stop, not empty run
- **Guardrail registration test:** Verify guardrail adversaries are in `GUARDRAILS` dict, not in `ADVERSARIES` or `ADVERSARY_TEMPLATES`
- **Skip-filtering safety test:** Verify a skipped adversary does NOT execute via static fallback — the adversary must be absent from the `adversaries` list passed to `generate_attacks()`

---

## 7. Migration Plan

### 7.1 Code Changes

| File | Change | Risk |
|------|--------|------|
| `scripts/adversaries.py` | Add `AdversaryTemplate` dataclass + `ADVERSARY_TEMPLATES` dict (gauntlet). Add `ADVERSARY_ALIASES` dict + `resolve_adversary_name()`. Add 3 `Adversary` instances + `GUARDRAILS` dict (guardrails). Add `minimalist`, `traffic_engineer` to both `ADVERSARIES` and `ADVERSARY_TEMPLATES`. | Medium |
| `scripts/gauntlet/core_types.py` | Add `SYNTHESIS_CATEGORIES` constant | Low |
| `scripts/gauntlet/orchestrator.py` | Update `run_gauntlet()` to load/validate `approved-prompts.json`, filter skipped adversaries from roster, pass flat `prompts` dict to `generate_attacks()` | Medium |
| `scripts/gauntlet/phase_1_attacks.py` | Add `prompts: dict[str, str] | None = None` param to `generate_attacks()`, use `resolve_adversary_name()` for lookups | Low |
| `scripts/gauntlet/model_dispatch.py` | Fix `get_available_eval_models()` to prefer `codex/gpt-5.4` over `codex/gpt-5.3-codex` — 5.3 produces lower-quality verdicts and the cost savings are not worth it for evaluation | Low |
| `scripts/gauntlet/phase_1_attacks.py` | Replace deterministic concern parser with structured output (JSON mode) for models that support it; add LLM extraction fallback for models that don't; add Phase 1 quality gate that detects non-empty responses with 0 parsed concerns and halts rather than silently continuing | High |
| `scripts/gauntlet/synthesis_extract.py` | New file — extraction CLI reading from run log | Low |
| `phases/03-debate.md` | Add checkpoint guardrails step after each round incorporation | Low |
| `phases/05-gauntlet.md` | Add scope classification + prompt generation/review to Arm Adversaries; add fix interaction validation to post-gauntlet incorporation | Low |
| `phases/06-finalize.md` | Add cross-reference consistency check to quality checklist | Low |

### 7.2 Dual Registry Model

Both registries coexist in `adversaries.py`:

- **`ADVERSARIES: dict[str, Adversary]`** — The runtime registry. Contains canonical adversaries with static `persona` strings. Used as fallback when dynamic prompts are unavailable. Keyed by canonical name only — no aliases in this dict (aliases live in `ADVERSARY_ALIASES`).
- **`ADVERSARY_TEMPLATES: dict[str, AdversaryTemplate]`** — The prompt generation registry. Contains templates with `tone`, `scope_guidelines`, and `focus_areas` for Claude to assemble dynamic prompts. Keyed by canonical name only (no aliases).
- **`ADVERSARY_ALIASES: dict[str, str]`** — Explicit legacy name → canonical name mapping: `{"lazy_developer": "minimalist", "prior_art_scout": "minimalist"}`.

**Resolution function:**

```python
def resolve_adversary_name(name: str) -> str:
    """Resolve legacy or alias names to canonical names."""
    return ADVERSARY_ALIASES.get(name, name)
```

All adversary lookups in `generate_attacks()` and `run_gauntlet()` go through `resolve_adversary_name()` first. This replaces the dict-alias approach (which doesn't preserve prefix lookup) with an explicit resolution layer.

**Design debt note:** Three registries (`ADVERSARIES`, `ADVERSARY_TEMPLATES`, `GUARDRAILS`) sharing the same prefix namespace could be unified into a single registry with a `tier: "gauntlet" | "guardrail"` field. This would eliminate the need for separate lookup paths and the risk of prefix collisions. Deferred because the current split matches the usage boundary (guardrails are invoked by Claude inline, gauntlet adversaries by `generate_attacks()`), and unification adds complexity to the type hierarchy without an immediate functional benefit. Revisit if a fourth registry or cross-tier lookups emerge.

### 7.3 Backward Compatibility

- Old concern IDs (`LAZY-*`, `PREV-*`) remain valid — no historical data migration
- `generate_attacks()` without `prompts` override uses static personas from `ADVERSARIES` (current behavior)
- `ADVERSARY_PREFIXES` updated to include `MINI` and `TRAF`, retain `LAZY` and `PREV` for ID lookups
- Guardrails use `Adversary` dataclass (static prompts), gauntlet uses `AdversaryTemplate` (dynamic prompts) — no changes to existing pipeline code

### 7.4 Deployment

```bash
cp -r skills/adversarial-spec/* ~/.claude/skills/adversarial-spec/
```

No database migrations. No config file changes. Pure code + docs.
