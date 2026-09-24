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
`tier` is advisory dispatcher metadata. Resolve every concrete seat through
`reference/current-models.md`; this page owns only altitude constraints on
count, family diversity, effort class, and focus. Persona guidance rides the
same scale: low-blast / local / reversible change → light roster
(assumption_auditor + architect + SDK pass); irreversible external effects,
concurrency, hot path, or shared infrastructure → full slate (all 9 personas).

**The floor is load-bearing (C1 / C5): never zero.** Every quorum floor is ≥1, and
zeroing any of them is a *startup crash*, not a silent bypass (NASA tailoring
S3.11). The component still pays its component-verification floor.

## 6.1 Run-manifest contract

The skill dispatches models; Fizzy verifies artifacts. Read `session_altitude`
from the session card before dispatch and size the run from §6. For altitude
enforcement, the manifest submitted to `pipeline_mark_gauntlet_complete` must
carry:

- `spec_hash`; and
- when the card declares a valid altitude, non-empty `adversaries` records with
  `{model, family}` plus a `foci` list.

The gate reads `session_altitude` from card metadata. A manifest echo may aid an
audit, but the current gate does not require or validate that echo.

For `concern_refs_schema_version >= 2`, tag concerns with `level` and `node_id`.
On a re-gauntlet with a loaded tree, manifest foci plus concern `node_id` values
must cover every tree node at or below the session altitude.

Right-tool rule: write the run artifacts, then call
`pipeline_mark_gauntlet_complete` with explicit `board_id`; never use
`pipeline_patch_state` to claim or bypass completion.

## 7. What altitude does not decide

Altitude (blast radius) decides *how much rigor* a node earns. It does not decide:

- **Roadmap mode** — Phase 2 chooses inline, one-debate, or iterative roadmap
  discovery.
- **Parallelism** — Phase 7 dependency order decides which cards can start
  together; Phase 8 is always multi-agent self-pickup with independent review.

Do not lower altitude because a change is easy to execute, and do not raise it
because it has many tasks.

## 8. Enforcement map

Runtime authority is
`fizzy-pipeline-mcp/src/fizzy_pipeline_mcp/pipeline.py`; this map names symbols,
not volatile line numbers. Version fences in that module decide grandfathering.

| Invariant | Authority / rejection | Purpose |
|---|---|---|
| Allowed levels and ordering | `VALID_ALTITUDES`, `ALTITUDE_RANK` | Reject unknown levels and define strict parent/child descent. |
| Verification floor | `ALTITUDE_OBLIGATIONS`, `VV_OBLIGATION_RANK`, `VV_ABOVE_ALTITUDE` | Require the right-arm obligations for the node level and reject bindings above it. |
| Root and tree shape | `_validate_altitude_tree`; `ROOT_NOT_SYSTEM`, `ROOT_ALTITUDE_MISMATCH`, `ALTITUDE_INVERSION` | Enforce the declared root, system forcing rule, and strictly lower children. |
| Immutable altitude metadata | `_ALTITUDE_PROTECTED`; `PROTECTED_METADATA_FIELD` | Prevent `pipeline_patch_state` from changing altitude and related schema fields. |
| Debate rigor | `ALTITUDE_DEBATE_QUORUM`, `begin_debate_round`, `DEBATE_ROUNDS_BELOW_ALTITUDE_FLOOR` | Freeze the per-round critic quorum and reject early completion. |
| Review rigor | `ALTITUDE_REVIEW_QUORUM`, `_mark_verification_complete`, `REVIEW_QUORUM_UNMET` | Require distinct reviewers and system-level human attestation. |
| Gauntlet rigor | `ALTITUDE_GAUNTLET_INTENSITY`, `mark_gauntlet_complete`, `GAUNTLET_INTENSITY_UNMET` | Enforce adversary, family, and focus floors. |
| Manifest family integrity | `validate_debate_model`, `GAUNTLET_ADVERSARY_FAMILY_MISMATCH` | Cross-check each claimed model family against the registry. |
| Concern targeting | `_normalize_concern_ref`, `_validate_concern_levels`; `CONCERN_LEVEL_UNCOVERED`, `CONCERN_ALTITUDE_NODE_MISMATCH` | Normalize legacy refs and enforce schema-v2 per-level node coverage. |
| Non-zero floors | import-time assertions on `ALTITUDE_OBLIGATIONS`, `ALTITUDE_DEBATE_QUORUM`, and `ALTITUDE_GAUNTLET_INTENSITY` | Crash at startup instead of permitting a zero-rigor bypass. |
| Skill-side preflight | `mini_spec_emission.self_check_plan()` | Mirror the plan rejects before the live MCP gate. |

When any named symbol or reject changes, update this map in the same change.
