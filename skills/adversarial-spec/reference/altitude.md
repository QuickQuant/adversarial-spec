# Altitude — the single reference

Altitude is the one idea that scales every other knob in the pipeline. A change
has a **blast-radius altitude** — how far a mistake propagates — and rigor scales
to it: **DOWN with altitude, but NEVER to zero.** This page states the whole model
once, and names where each invariant is enforced in code so the doc and
`pipeline.py` cannot drift. Phases 1, 4, 5, and 7 link here instead of restating
fragments; `phases/00-triage.md` applies it.

## 1. The three levels

| altitude | what it is | floor it always owes |
|---|---|---|
| **component** | a leaf with a *local* failure surface — a mistake is caught and contained at the unit boundary | unit / component verification |
| **subsystem** | a cohesive unit several components depend on; the contract is expensive to reverse | component + **integration / conformance** |
| **system** | crosses a process/repo boundary, **or** a mistake has **irreversible external consequences a code revert can't undo** | component + subsystem + **end-to-end** + consequence-safety guardrails + manual go-live gate |

**What makes something `system` is irreversibility/blast, not a domain.** Production
data loss, destructive or one-way operations, irreversible outbound effects on
third parties or users (sent comms, external state mutations) all qualify. *Moving
real money is one instance, not the definition* — most changes that touch nothing
irreversible and stay inside one repo are **not** system.

## 2. The forcing rule (state this WHERE you pick the root)

**Pick the highest-blast item in the change. That item's altitude is the root.**

Equivalently: *any* system-altitude node ⇒ the root must be `system`. This single
rule determines the whole tree shape, so it belongs at the decision point (triage),
not as a downstream surprise. It is enforced as the `ROOT_NOT_SYSTEM` reject — but
by then you've already drawn the tree wrong.

| blast radius | legal root altitude | minimum tree shape |
|---|---|---|
| system (full V) | `system` | system → ≥1 subsystem → ≥1 component each |
| subsystem | `subsystem` | subsystem → ≥2 components |
| component | `component` | a single leaf component node (no children) |

Rigor scaling down is the **feature**, not a loophole: a component-altitude change
pays no system tax (no ConOps refs, no system verification, no subsystem
decomposition) — but still owes its component floor.

## 3. Two edges — never conflated

- **`decomposes_into`** — WHAT contains WHAT (composition; the V-model tree).
  Drives the bottom-up V&V closure and altitude-inversion detection.
- **`depends_on`** — WHAT finishes before WHAT (execution order; scheduling only,
  no V&V state). A sibling may depend on a sibling without being its child.

Each tree node has exactly one `parent` of *strictly higher* altitude (except the
single root). Lower-than-or-equal child altitude is the `ALTITUDE_INVERSION` reject.

## 4. Verification obligations (right arm) — a pure function of altitude

| altitude | verification obligations |
|---|---|
| `component` | `component_verification` |
| `subsystem` | `component_verification` + `subsystem_verification` |
| `system` | `component_verification` + `subsystem_verification` + `system_verification` |

Paired left↔right at the SAME altitude (NASA's V): a node's definition artifact at
a level is verified by a verification artifact at that level. Binding a
verification *above* the node's altitude is the `VV_ABOVE_ALTITUDE` reject.
**System _validation_ is deliberately NOT a v4 obligation** — it is a future,
separately-approved migration. v4 is verification-only.

## 5. The superset chain `component ⊂ subsystem ⊂ system`

Each higher altitude is a strict superset of the mandatory left-arm fields of the
one below; lower altitude = strictly fewer required fields, never different ones.

| field | component | subsystem | system |
|---|---|---|---|
| `component_verification` | **req** | req | req |
| `subsystem_verification` | forbidden | **req** | req |
| `system_verification` | forbidden | forbidden | **req** |
| `subsystem_spec_path` | forbidden | **req** | (system_spec_path) |
| `system_spec_path` / `conops_refs` / `user_story_refs` | forbidden | forbidden | **req** |
| `decomposes_into` | forbidden (leaf) | ≥2 children | ≥1 child |
| `parent` | non-null | non-null | null (root) |

(Full field table: Phase 7 §"Per-altitude mini-spec shapes".)

## 6. Rigor that scales — the consumption tables

Altitude is read by three independent scaling tables. They share the altitude key
and the "higher blast ⇒ extra rigor" principle but are **distinct concepts — never
unify them** (different leg, artifact, and lifecycle phase).

**Left-leg spec-critic quorum** — `ALTITUDE_DEBATE_QUORUM` (debate convergence):

| altitude | counting critics | distinct families | rounds |
|---|---|---|---|
| component | 1 | 1 | 1 |
| subsystem | 2 | 2 | 1 |
| system | 2 | 2 | 2 |

**Right-leg code-reviewer quorum** — `ALTITUDE_REVIEW_QUORUM` (V&V discharge):

| altitude | distinct reviewers | human attestation |
|---|---|---|
| component | 1 | no |
| subsystem | 2 | no |
| system | 2 | **yes** |

**Bottom-vertex gauntlet intensity** — `ALTITUDE_GAUNTLET_INTENSITY` (gauntlet
completion gate):

| altitude | min adversaries | min distinct families | min foci | tier (ADVISORY) |
|---|---|---|---|---|
| component | 1 | 1 | 1 | fast |
| subsystem | 2 | 2 | 2 | frontier |
| system | 2 | 2 | 3 | frontier |

The pipeline ENFORCES adversary count, family diversity, and focus count from the
run manifest (`GAUNTLET_INTENSITY_UNMET` names the short dimension) and
CROSS-CHECKS every claimed family against the model registry
(`GAUNTLET_ADVERSARY_FAMILY_MISMATCH` — the manifest cannot forge diversity).
`tier` is advisory dispatcher metadata: `fast` is legal for component
(e.g. `gemini-3-flash`); `frontier` is advised for subsystem/system
(`gemini-3.1-pro-preview`, `codex/gpt-5.4 xhigh`). Persona guidance rides the same
scale: low-blast / local / reversible change → light roster (assumption_auditor +
architect + SDK pass); irreversible external effects, concurrency, hot path, or
shared infrastructure → full slate (all 9 personas).

**The floor is load-bearing (C1 / C5): never zero.** Every quorum floor is ≥1, and
zeroing any of them is a *startup crash*, not a silent bypass (NASA tailoring
S3.11). The component still pays its component-verification floor.

## 6.1 The run-manifest contract (skill writes, pipeline judges)

The enforcement seam (00 OQ5): **pipeline.py never spawns a model — it verifies
artifacts on disk; the skill executes the dispatch.** The gauntlet run manifest is
the durable cross-repo contract. Before `pipeline_mark_gauntlet_complete` on a
v4+ session with a declared altitude, the skill MUST:

1. **Read `session_altitude` off the session card BEFORE dispatching** (it is on
   `pipeline_metadata`; `None` on a grandfathered session ⇒ legacy behavior).
   Size the dispatch from the two tables above — dispatching below quorum wastes
   a full run: the gate rejects it after the models have already been paid for.
2. **Write into the run manifest** (additive to the existing `spec_hash`):
   - `adversaries`: `[{"model": "<registry cli_name>", "family": "<registry family>"}, ...]`
     — families must match what `agents.validate_debate_model(model).family`
     returns; unknown models are rejected (`MODEL_REGISTRY_UNKNOWN`).
   - `foci`: list of attack foci covered by the pass. Default unit: distinct
     system-spec sections. Once the plan declares `concern_refs_schema_version: 2`
     and a loaded tree exists (re-gauntlet), every tree node ≤ session altitude
     must appear — by manifest focus or by a concern's `node_id`.
   - `session_altitude`: echo of the card value (audit trail).
3. **Tag concerns with `level` + `node_id`** when authoring schema-v2 concern
   refs — `load_plan` enforces per-level coverage (`CONCERN_LEVEL_UNCOVERED` /
   `CONCERN_ALTITUDE_NODE_MISMATCH`), so untagged concerns can block the plan
   from loading.

## 7. Complexity ≠ altitude

These are orthogonal — keep them decoupled and you stop double-counting:

- **Altitude (blast radius)** decides *how much rigor* a node earns (this whole
  page). Reversibility / consequence is an **altitude** signal.
- **Complexity** decides *execution shape only* — single agent vs. workstreams,
  task count (Phase 7 §sizing).

**Key complexity off two observable signals: `integrations + unknowns`.** A change
touching many external SDKs with several open design questions is "complex"
regardless of how reversible it is — and a high-blast change can still be *simple*
to execute (one agent, few tasks) while earning *system* rigor. There is no numeric
score; the `≤4 / 5–9 / ≥10` thresholds are retired (they were never backed by a
point rubric). Do **not** feed blast radius / consequence into complexity — that is
altitude's job.

## 8. Where each invariant is ENFORCED  (doc ↔ code anti-drift map)

All in `fizzy-pipeline-mcp/src/fizzy_pipeline_mcp/pipeline.py` unless noted. Fenced
to `_pipeline_version >= 4`; pre-v4 sessions are grandfathered forever.

| invariant | reject / mechanism | location |
|---|---|---|
| valid altitude set | `VALID_ALTITUDES = {component, subsystem, system}` | `pipeline.py:224` |
| root must be system if any system node | `ROOT_NOT_SYSTEM` | `pipeline.py:5089` |
| child altitude strictly below parent | `ALTITUDE_INVERSION` | `pipeline.py:5106` |
| no verification bound above node altitude | `VV_ABOVE_ALTITUDE` | `pipeline.py:4995–5027` |
| `session_altitude` immutable once set | `_ALTITUDE_PROTECTED` (patch_state reject) | `pipeline.py:7478, 7537` |
| left-leg debate quorum | `ALTITUDE_DEBATE_QUORUM` + `DEBATE_ROUNDS_BELOW_ALTITUDE_FLOOR` | `pipeline.py:310, 10944–10950` |
| quorum frozen into per-round state | `begin_debate_round` | `pipeline.py:11314–11321` |
| right-leg review quorum | `ALTITUDE_REVIEW_QUORUM` + `REVIEW_QUORUM_UNMET` (depth-triage Stage 5) | `pipeline.py:296, 8545` |
| bottom-vertex gauntlet intensity | `ALTITUDE_GAUNTLET_INTENSITY` + `GAUNTLET_INTENSITY_UNMET` (mark_gauntlet_complete) | `pipeline.py:332, 8373` |
| manifest family anti-lying | `GAUNTLET_ADVERSARY_FAMILY_MISMATCH` (registry cross-check via `agents.validate_debate_model`) | `pipeline.py:8350` |
| per-level concern coverage (schema v2) | `CONCERN_LEVEL_UNCOVERED` / `CONCERN_ALTITUDE_NODE_MISMATCH` at `load_plan` | `pipeline.py:5184–5256` |
| concern-ref normalization (bare string ⇒ system/root) | `_normalize_concern_ref` | `pipeline.py:8051` |
| schema stamp immutable | `concern_refs_schema_version` in `_ALTITUDE_PROTECTED` | `pipeline.py:7694` |
| re-gauntlet foci = tree nodes ≤ altitude | `GAUNTLET_INTENSITY_UNMET` (uncovered nodes) | `pipeline.py:8416` |
| floors never zero | startup `assert` (both tables) | `pipeline.py:320–323, 337–340` |
| skill-side stand-in (MCP pre–depth-triage-Stage-1) | `mini_spec_emission.self_check_plan()` mirrors the same reject codes | `skills/adversarial-spec/scripts/mini_spec_emission.py` |

> **Maintenance contract:** if a reject code or quorum table changes in
> `pipeline.py`, update the matching row here in the same change. A reviewer can
> diff this table against the code in one pass — that is the whole point of having
> one page.
