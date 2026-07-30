---
status: RATIFIED spec.v1 (G3, Jason, 2026-07-30)
spec_contract: spec.v1
package_role: prose keystone
---

# Spec Record Contract

This package is the ratified spec-record keystone (G3, 2026-07-30). Canonical home:
`adversarial-spec/contracts/` — **ownership ruling (Jason, 2026-07-30): the
adversarial-spec project OWNS spec-system contracts; fizzy-pipeline-mcp mirrors them
as the enforcement arm** (static mirror + `schema_sha256` drift tripwire, no
dependency edge). Edits land here first; consumers refresh their mirrors and must
fail loudly on drift. The five companion JSON Schemas are
the machine contracts; this file defines source bytes, algorithms, ownership,
command behavior, adoption fences, and the limits of mechanical authority.

The contract follows the existing keystone precedent:

- one cross-project authority, pinned rather than copied
  (`Brainquarters/shared-context/test-maturity-record-schema.md:1-23`);
- named enum owners and field-for-field consumers
  (`Brainquarters/shared-context/test-maturity-record-schema.md:52-75`);
- recomputation of stored hashes rather than trust in claimed values
  (`Brainquarters/shared-context/test-maturity-record-schema.md:169-190`); and
- warn/grandfather first, then require behind a named version fence
  (`Brainquarters/shared-context/test-maturity-record-schema.md:322-338`).

## 1. Authority and artifact roles

Authored authority is constrained Markdown. A document's normative units are
the exact Markdown bodies inside `SPEC-CLAIM` blocks. Their JSON headers provide
predetermined, schema-validatable metadata; they do not replace the prose.

`spec compile` is one-way:

```text
canonical constrained Markdown -> disposable, read-only JSON index
```

The index is never an authoring surface and MUST NOT be reverse-imported. A
source/index mismatch fails closed and is repaired only by regenerating the
index from the pinned source.

| File | Version | Role |
|---|---|---|
| `spec-record-contract.md` | `spec.v1` | Source grammar, algorithms, ownership, fences, and authority limits |
| `spec-record.schema.json` | `spec.v1` | Document front matter, `ClaimMeta`, relations, lifecycle, imports |
| `spec-accessor-profile.schema.json` | `profile.v1` | Hash-pinned root, closure, spine, budget, and full-promotion policy |
| `spec-slice-manifest.schema.json` | `slice.v1` | Attestation for one source/index/profile projection |
| `spec-bundle-manifest.schema.json` | `bundle.v1` / `bundle-compose.v1` | Attestation for the ordered bytes one invocation consumed |
| `spec-corpus-replay.schema.json` | `replay.v1` | Signed mappings, revised gates 1–7, fixtures, and backstop parity |

The prose contract explains the schemas. If prose and a schema disagree on an
instance constraint, the schema wins until the package is corrected and
re-ratified. Algorithmic rules that JSON Schema cannot express remain
normative here and are enforced by `spec lint`, `spec verify-*`, or consumer
contract tests.

## 2. Canonical source bytes and grammar

### 2.1 File-level byte rules

A `spec.v1` source MUST:

1. be valid UTF-8, without a byte-order mark;
2. use LF (`0x0a`) line endings only; CR (`0x0d`) and NUL (`0x00`) are forbidden;
3. end in exactly one LF (the preceding content byte MUST NOT also be LF);
4. begin at byte offset zero with exactly one `SPEC-DOC` header;
5. contain no nested or overlapping `SPEC-CLAIM` blocks; and
6. preserve all authored body bytes exactly. Unicode normalization is not
   performed on Markdown prose.

All JSON embedded in markers MUST be I-JSON and MUST reject duplicate object
keys before validation. Its source bytes MUST equal the RFC 8785 JSON
Canonicalization Scheme (JCS) serialization of the parsed value. Consequently,
embedded JSON occupies exactly one physical line; line breaks inside strings
are JSON escapes.

The literal grammar is:

```text
DOCUMENT =
  "<!-- SPEC-DOC\n"
  JCS(DocumentFrontMatter)
  "\n-->\n"
  DOCUMENT_CONTENT

CLAIM_BLOCK =
  "<!-- SPEC-CLAIM\n"
  JCS(ClaimMeta)
  "\n-->\n"
  BODY
  "<!-- /SPEC-CLAIM -->\n"
```

`DOCUMENT_CONTENT` is zero or more editorial Markdown bytes and claim blocks.
`BODY` is one or more UTF-8 bytes, MUST end in LF, and MUST NOT contain a line
whose complete bytes are `<!-- /SPEC-CLAIM -->\n`. The body begins immediately
after the opening marker's `-->\n` and ends immediately before the first byte of
the closing marker. Therefore `body_sha256` includes the body's final LF.
Offsets in a compiled index are zero-based UTF-8 byte offsets expressed as
half-open intervals `[start, end)`, not character or line offsets.

Content outside claim blocks is editorial and non-authoritative. A normative
keyword outside a claim is a lint error, not an implied claim. Marker spelling,
ASCII case, spaces, and LF placement are exact; indentation or alternate HTML
comment forms are invalid.

### 2.2 Document front matter

`DocumentFrontMatter` is validated by
`spec-record.schema.json#/$defs/DocumentFrontMatter`. It MUST include the
version fence:

```json
{"spec_contract":"spec.v1"}
```

The complete object also identifies the spec and revision, pins its predecessor
when one exists, declares hash-pinned imports, and uses
`conflict_rule: "reject-undeclared-or-unresolved"`.

An initial revision sets both `parent_revision` and `parent_index_sha256` to
JSON `null`. Every later revision sets both to non-null values and the parent
index hash MUST resolve. A consumer MUST compare the current and parent indexes
before accepting lifecycle changes.

Each import has a unique alias, qualified authority identity, repository,
immutable full commit, normalized relative path, SHA-256, precedence, and
declared conflict behavior. Precedence sorts higher integer values before lower
values. Equal precedence is legal only where imported claims do not collide or
an operator-signed conflict record resolves the tie. Import cycles,
undeclared identity/hash collisions, and declared-but-unresolved conflicts fail
mechanically.

Discovering an unlisted *semantic* conflict remains an audit/operator duty; a
parser cannot infer semantic contradiction from valid bytes.

### 2.3 Qualified IDs and duplicates

A source claim ID has the lexical form `claim:<local-id>`. Imported endpoints
use `<import-alias>:<exported-id>`. Other registered namespaces include
`concern`, `finding`, `decision`, `oracle`, `probe`, `test`, `interface`,
`component`, and `task`. IDs are case-sensitive ASCII and are never Unicode
normalized.

Duplicate policy is fail-closed:

- a claim ID appearing twice in one source is `DUPLICATE_CLAIM_ID`, even when
  both metadata and bodies are byte-identical;
- import aliases MUST be unique and MUST NOT use the reserved `claim` alias;
- the expanded endpoint graph MUST contain one definition per qualified ID;
- importing the same qualified authority identity or physical
  `(repository, commit, path, sha256)` under multiple aliases is
  `IMPORT_IDENTITY_COLLISION` unless one alias explicitly declares `alias_of`;
  and
- no implementation may silently keep first, keep last, merge, or auto-rename.

Relation arrays, evidence arrays, selectors, and ID sets reject exact duplicate
members. Where an array is defined as a set, its canonical order is ascending
Unicode code-point order of the JCS string form.

## 3. Hashing and canonical JSON

Every digest string is `sha256:` followed by 64 lowercase hexadecimal
characters.

| Digest | Bytes hashed |
|---|---|
| `source_sha256` | Exact canonical source bytes, including the final LF |
| `body_sha256` | Exact `BODY` bytes, including its final LF |
| `schema_sha256` | RFC 8785 JCS of the schema with top-level `$comment` removed |
| `index_sha256` | JCS of the derived index with only its own `index_sha256` field omitted |
| `profile_sha256` | JCS of the profile with only `profile_sha256` omitted |
| slice `manifest_sha256` | JCS of the slice manifest with only `manifest_sha256` omitted |
| bundle `manifest_sha256` | JCS of the bundle manifest with only `manifest_sha256` omitted |
| replay `manifest_sha256` | JCS of the replay artifact with only `manifest_sha256` omitted |
| replay record signature payload | JCS of that record with only `signature` omitted |

Every replay `relation_target_id` is derived, never assigned:

```text
relation_target_id =
  "relation:" + lowercase-hex(
    SHA-256(UTF-8(JCS([source, type, target])))
  )
```

The JCS value is exactly the three-string JSON array shown, in that order, with
no prefix, suffix, separator, or terminal LF outside the JCS bytes. `source` and
`target` are the exact case-sensitive qualified-ID strings and `type` is the
exact relation enum token. The resulting ID matches
`^relation:[0-9a-f]{64}$`; replay verification re-derives it and rejects any
mismatch.

Hashes are always re-derived. A stored mismatch is a validation failure, never
a newer truth. Operational timestamps, local absolute paths, process IDs,
random map order, and filesystem metadata MUST NOT enter source, index,
profile, slice, or bundle hashed projections. Replay signature envelopes may
carry `signed_at`; the algorithm-specific envelope binds that provenance and
the enclosing replay artifact hash covers its exact bytes. Other execution
evidence is non-hashed unless its schema explicitly includes it in an immutable
receipt.

Path inputs MUST use `/`, be relative, contain no empty, `.` or `..` segment,
and resolve beneath the declared artifact root. Verification rejects symlinks
at every traversed path component. Path strings are sorted by their UTF-8 byte
sequence where canonical ordering is required.

## 4. `ClaimMeta`

`ClaimMeta` has stable identity, one provisional semantic kind, registered
roles, three independent axes, drivers, goal references, typed relations,
typed evidence, slice tags, and explicit exception/residue routing.

The independent axes are:

- `normativity`: `normative | descriptive | observation | decision`;
- `lifecycle.state`:
  `draft | live | open | residue | superseded | withdrawn`; and
- `gauntlet_disposition.state`:
  `not_applicable | unreviewed | accepted | acknowledged | dismissed`.

No axis is inferred from another. In particular, lifecycle state is not a
Concern verdict, and a gauntlet disposition does not silently alter
normativity.

Every normative requirement MUST have at least one accepted `realizes`
relation to a goal or a non-null owned exception. This is a structural check
after an operator accepts that the relation is semantically true. Every live
normative obligation MUST have `verified_by` or explicit owned residue.

### 4.1 Relation contract

Relations are stored on their source claim; `target` is a qualified ID and
`target_kind` is mandatory. The direction, legal endpoint kinds, and
cardinalities in `spec-record.schema.json` are normative. `conflicts_with` is
semantically symmetric but stored once, on the lexicographically smaller
qualified endpoint, to preserve deterministic bytes. `supersedes` and `amends`
are many-to-many and may cross import boundaries.

No dangling endpoint, illegal endpoint kind, self-edge, exact duplicate edge,
or cardinality violation is permitted. Relation traversal order is relation
type in schema order, then target qualified ID in ascending Unicode code-point
order.

### 4.2 Lifecycle transitions

`spec lint` compares a revision with its pinned parent and enforces:

| From | Legal next states |
|---|---|
| absent | `draft`, `live`, `open` |
| `draft` | `draft`, `live`, `open`, `withdrawn` |
| `live` | `live`, `residue`, `superseded`, `withdrawn` |
| `open` | `open`, `live`, `residue`, `withdrawn` |
| `residue` | `residue`, `live`, `superseded`, `withdrawn` |
| `superseded` | `superseded` |
| `withdrawn` | `withdrawn` |

Entering `live` requires an authority reference. Entering `residue` requires
owner, disposition, reason, and reference. Entering `superseded` requires an
incoming `supersedes` edge from a non-terminal replacement in the current
graph. Entering `withdrawn` requires an operator decision and reason.
Terminal-state resurrection requires a new ID connected by `supersedes`; it
cannot reuse the old ID.

Changing a live claim's body, kind, normativity, or relation set without an
authored amendment driver is `UNATTRIBUTED_LIVE_CHANGE`. `introduced_in` alone
does not prove transition history.

## 5. Enum ownership

The listed owner is the only authority allowed to add, remove, or rename a
member. Consumers mirror only with a pinned schema hash and a fail-on-drift
test.

| Enum or registry | Members / scope | Owner |
|---|---|---|
| `spec_contract` | `spec.v1` | This keystone package after G3 |
| `ClaimMeta.kind` | 11 kinds in `spec-record.schema.json` | This package; **provisional until G3** |
| `normativity` | four-axis members in §4 | `spec-record.schema.json` |
| lifecycle states/transitions | six states and §4.2 table | `spec-record.schema.json` + this contract |
| gauntlet disposition | five states in §4 | `spec-record.schema.json` |
| relation types/directions/endpoints/cardinalities | nine relation definitions | `spec-record.schema.json` |
| evidence types | `code`, `probe`, `test_run`, `operator_decision`, `external_contract` | `spec-record.schema.json` |
| roles and slice tags | registered strings, not an open ad-hoc vocabulary | Hash-pinned profile/registry instance selected at G3 |
| profile selectors/traversal/promotion reasons | values in profile schema | `spec-accessor-profile.schema.json` |
| `slice.v1` fields | slice attestation | `spec-slice-manifest.schema.json` |
| bundle component kinds/composition | `bundle-compose.v1` | `spec-bundle-manifest.schema.json` |
| replay mapping/adjudication values | replay records | `spec-corpus-replay.schema.json` |
| probe tracks/status behavior | current Fizzy gauntlet validator | `fizzy-pipeline-mcp` |
| replay expected violation codes | stable fixture labels, mapped to real-validator output | `spec-corpus-replay.schema.json` |

The 11-kind enum and mandatory-spine registry MUST remain marked
`provisional-until-G3`. Freezing requires an operator-reviewed kind/spine
mapping and ambiguity report over at least two independent additional corpora.
G3 freezes both. Any later member or spine-policy change bumps the relevant
contract version; it MUST NOT silently mutate `spec.v1`.

## 6. Accessor profiles and graph-closed slices

A profile instance pins, in machine-readable form:

- root selectors (including invocation-bound roots);
- relation types, traversal direction, and maximum depth;
- mandatory-spine selectors;
- byte/claim/import budgets; and
- fail-closed full-promotion rules.

Every slice manifest MUST include `profile_sha256`; a profile name or
`accessor_version` alone is insufficient identity.

Selection is deterministic:

1. resolve invocation inputs and profile roots;
2. add the mandatory spine;
3. traverse each profile relation in canonical relation/target order;
4. add required imported excerpts and evidence targets;
5. union replay-required targets for the designated consumer;
6. form one render sequence: selected local claim blocks by ascending opening-
   marker byte offset, followed by imported claim blocks grouped by descending
   import precedence and ascending import alias, with each group ordered by
   ascending opening-marker byte offset in the imported source; and
7. render that sequence using the exact `slice-render.v1` layout below.

`slice-render.v1` is byte-exact:

1. A render unit is the complete validated `CLAIM_BLOCK` byte interval from the
   first `<` of `<!-- SPEC-CLAIM\n` through the LF of
   `<!-- /SPEC-CLAIM -->\n`, inclusive. The opening marker, one-line JCS
   `ClaimMeta`, exact `BODY`, and closing marker are included without rewriting.
2. `SPEC-DOC` front matter, editorial Markdown outside claim blocks, and all
   slice/import/bundle wrapper markers, headings, labels, and metadata are
   excluded.
3. Adjacent render units are joined by exactly one additional LF byte (`0x0a`).
   There is no prefix and no suffix. Thus a non-empty render ends with exactly
   the LF already present on its final closing marker; no terminal LF is added.
4. Empty renders are invalid. For `n` units, `render_byte_length` is the sum of
   their exact byte lengths plus `n - 1`; `render_sha256` hashes exactly those
   bytes.
5. An `IncludedImport.render_sha256` and `render_byte_length` cover that
   import's ordered unit subsequence joined by the same one-LF rule, excluding
   separators adjacent to units from other sources.

A profile never truncates. Any unresolved root, dangling relation, import hash
mismatch, replay target split, or exceeded budget promotes the invocation to
its declared full profile. A `full` profile selects 100% of the canonical
source/import closure and has no limiting budget.

Mandatory-spine policy is registry data, not hard-coded prompt prose. The draft
baseline includes live goals, completion-role claims, invariants, non-goals,
open/residue claims, and trust/irreversible-effect roles. G3 may freeze it only
after the required multi-corpus sweep.

A slice proves one projection. It does not prove what a model or consumer saw
alongside other slices and briefings.

## 7. Bundle composition and verification

A bundle proves the exact ordered bytes delivered to one identified consumer,
seat, and invocation. Its `components` array is the sole composition order.
Components may be verified slice renders, recursively verified child bundles,
or byte-pinned non-spec inputs.

For `bundle-compose.v1`, canonical bundle bytes are:

```text
component[0].bytes
"<!-- SPEC-BUNDLE-BOUNDARY -->\n"
component[1].bytes
...
"<!-- SPEC-BUNDLE-BOUNDARY -->\n"
component[n-1].bytes
```

There is no prefix, suffix, implicit heading, indentation, transcoding, or
template expansion. Every component is canonical UTF-8/LF and ends in exactly
one LF. The separator is the 30 ASCII bytes represented above, inserted
between components only. A one-component bundle equals that component's bytes.
An empty bundle is invalid.

`verify-bundle` resolves all paths under the declared root with symlinks
rejected, verifies each slice render and child bundle artifact recursively,
re-reads every non-spec component, reconstructs the exact bytes, and compares
component lengths/hashes, final byte length, `bundle_sha256`, and manifest hash.
It also re-derives `visible_target_ids`; a claimed visibility set is never
trusted.
Only target IDs re-derived from verified `spec_slice` components are eligible.
For a child bundle, only the recursively re-derived union of its direct or
nested `spec_slice` descendants propagates upward. A `non_spec` component
contributes bytes but contributes no target IDs and can never satisfy Gate 5.

No timestamp participates in composition or hashing. Consumer, seat, and
invocation identities are manifest fields, not bytes injected into the
rendered payload.

Gate 5 evaluates co-visibility per verified bundle:

```text
required_target_set(concern_id)
  subset-of spec_slice_visible_target_ids(seat_bundle_id)
```

The result records the Concern, one designated seat bundle, required, visible,
and missing sets. Its visible set MUST equal the designated verified bundle's
`visible_target_ids`, derived exclusively from verified `spec_slice` components
as defined above; non-spec bytes are ineligible. Passing requires an empty
missing set. Unioning visibility across bundles or slices is forbidden. The
declared full bundle must satisfy every baseline target set.

## 8. Commands and placement

All commands exit non-zero on any error, write outputs atomically, and never
partially replace a prior valid artifact.

```text
spec lint <spec.md> [--parent-index <index.json>]
```

Validates bytes and markers, embedded JCS and schemas, unique IDs, import
identity/hash/precedence, declared conflicts, typed edge endpoints and
cardinality, lifecycle transitions against the pinned parent, owned exceptions,
and live-obligation verification/residue. It reports stable violation codes.

```text
spec compile <spec.md> --index-out <derived.json>
```

Runs lint, then emits a deterministic read-only index containing contract and
schema hashes, `source_sha256`, exact body byte offsets/hashes, canonical typed
edges, imports, and revision chain. Claim order is source byte order; derived
set order follows §3. No timestamp enters the hashed index.

```text
spec slice <spec.md> --index <index.json> --profile <profile.json>
  [--seat <id> | --task <id> | --component <id>]
  --manifest-out <slice.json> --render-out <rendered.md>
```

Verifies source, index, schema, and `profile_sha256`; resolves roots and closure
per §6; promotes rather than truncates; writes exact included/omitted IDs,
imports, render bytes/hash, and invocation inputs.

```text
spec verify-slice <rendered.md> <slice.json>
```

Re-derives source/index/profile pins, roots, closure, exact local/imported claim
blocks, ordering, `slice-render.v1` bytes/hash, and manifest hash.

```text
spec verify-bundle <bundle.bin> <bundle.json>
```

Performs the recursive verification and exact recomposition in §7. This is the
gate-6 determinism primitive.

```text
spec replay-corpus <replay.json> --profiles <dir> --bundles <dir>
```

Verifies operator signatures; rejects lost targets, relations, verdicts,
evidence, or per-bundle co-visibility; executes revised gates 1–6; and consumes
the recorded result of the named gate-7 consumer contract test. It does not
reimplement Fizzy's probe validator.

Placement:

- `lint` and `compile`: debate exit and pre-gauntlet;
- frozen index plus every seat bundle: verify at gauntlet entry;
- Phase 7 load: verify execution slices/bundles;
- Phase 8 Task Card claim: verify the assigned Task Card bundle again; and
- gate 7: a Fizzy consumer contract test imports and runs the real
  `fizzy_pipeline_mcp.pipeline.validate_gauntlet_probes` against keystone-owned
  valid/mutant fixtures. A mirrored validator is forbidden.

## 9. Dependency boundary

Parsing, compilation, graph closure, slicing, manifest verification, bundle
recomposition, and replay primitives live in one separately versioned shared
library. Both consumers pin the library version and schema hashes.

- `adversarial-spec` owns thin CLI UX and orchestration placement.
- `fizzy-pipeline-mcp` owns thin MCP adapters, pipeline gates, and the real
  `validate_gauntlet_probes` consumer test.
- Both applications depend down on the shared library.
- Neither application may import, shell into, vendor, or duplicate the other
  application's parser, slicer, verifier, or replay code.

There is no app-to-app dependency edge.

## 10. Version fence and grandfathering

`spec_contract: "spec.v1"` is the source-format fence. MCP enforcement is also
guarded by the named capability fence `spec_manifest_v1`; G3 assigns its
numeric pipeline-version activation point.

For Cards at or above that fence:

- source, index, profile, slice/bundle, shared-library version, and schema
  hashes are bound in pipeline metadata;
- all payloads at gated transitions must have a verified manifest;
- a missing, stale, unresolvable, or mismatched manifest fails closed; and
- upgrading a Card across the fence is an explicit migration that first
  produces and verifies the required artifacts.

Cards created below the fence remain grandfathered and follow their original
contract. They are not retroactively rejected or silently upgraded. New
artifacts may warn before G3, but no draft may claim enforcement is active.

## 11. Revised replay acceptance gates

The replay schema contains the machine records for these gates:

1. Baseline import: exactly 71 unique Concerns with verdict counts 62 accepted,
   8 acknowledged, and 1 dismissed.
2. Mapping completeness: every Concern maps to claims, relations, and evidence,
   or has an explicit operator-signed acknowledged/dismissed out-of-scope
   disposition; zero silent drops.
3. Guardrail preservation: all 16 CONS, 11 CANON, and 36 TCOV targets are
   represented.
4. Authority preservation: exact normative body hashes plus every import
   precedence, amendment, and supersession edge survive.
5. Per-bundle co-visibility: one designated verified seat bundle contains each
   Concern's complete required target set using only target IDs re-derived from
   verified `spec_slice` components (including recursive descendants);
   `non_spec` components contribute no eligible visibility. The full bundle
   contains all 71 sets. Required, visible, and missing sets are recorded per
   bundle.
6. Bundle determinism: `verify-bundle` succeeds and exact recomposition yields
   identical manifest/component/final hashes across at least three independent
   runs.
7. Consumer placement: the named
   `fizzy.validate_gauntlet_probes.contract` test imports and executes Fizzy's
   real `fizzy_pipeline_mcp.pipeline.validate_gauntlet_probes` over valid and
   mutant fixtures. Missing `probe_id`, dirty or wrong-reason controls,
   duplicate dedupe keys, stale suite hashes, and unvalidated residue handling
   must produce their expected stable fixture codes. `spec replay-corpus`
   records this result but does not decide it.

The full-context backstop remains until at least two independent corpora each
pass both:

1. mechanical input recall: every operator-signed historical required target
   set is co-visible in one designated sliced-seat bundle; and
2. signed adjudication coverage: every baseline Concern is operator-classified
   as re-found, stronger, or explicitly accounted, with zero unadjudicated or
   degraded output.

Schema arithmetic can establish coverage over signed records. It cannot decide
semantic equivalence, strength, adequacy, corpus representativeness, or
retirement. Backstop retirement is a separate explicit operator-signed
decision after both corpora pass.

## 12. Mechanical versus operator authority

The following R2-c table is reproduced verbatim:

| Subject | Mechanically validatable | Operator judgment required |
|---|---|---|
| Claim boundaries, `kind`, roles, spine | Grammar, enum membership, required fields, deterministic closure | Whether claims are complete/correctly classified and the spine is semantically sufficient |
| Relations, goals, evidence | Endpoint existence/type, cardinality, hashes, locator shape | Whether a relation is true, evidence is relevant, or prose actually satisfies a goal/obligation |
| Imports and precedence | File/revision hashes, acyclicity, declared order, tie rejection | Import completeness, correct authority order, and semantic conflicts not explicitly declared |
| Replay map | 71 uniqueness, 62/8/1 counts, mapped-ID coverage, bundle subset checks | Concern→target/evidence mapping; acknowledged/dismissed disposition correctness |
| Cross-run output parity | Coverage over signed equivalence/adjudication records | Whether a new Concern is equivalent, stronger, or adequately accounted |
| Exceptions and residue | Owner/ref/disposition presence and legal state | Whether the exception is justified and the named owner may accept it |
| Backstop retirement | Two-corpus thresholds over signed records | Corpus representativeness and the final retirement decision |

Rewrite “unlisted upstream conflict fails lint” narrowly: **undeclared hash/identity collisions and declared unresolved conflicts fail mechanically; discovering an unlisted semantic conflict is an audit/operator responsibility.** Likewise, “every requirement realizes a goal” can be structurally checked only after an operator has accepted the relation's meaning.

## 13. Revisit clause: canonical JSON source

`spec.v1` remains constrained Markdown unless a pre-registered, lossless
prototype benchmark passes on multiple representative corpora. A JSON or JSONL
source candidate must:

1. preserve every authored Markdown body byte exactly and remain one-way in
   authority during the experiment;
2. use the same graph, profiles, bundles, and replay maps;
3. strictly beat Markdown on total and median **rendered-slice token count** for
   identical consumer tasks;
4. be non-inferior on blinded edit-task success rate;
5. be non-inferior on merge-conflict frequency and operator resolution effort;
6. pass every replay gate with no target, relation, evidence, co-visibility, or
   signed output-parity degradation; and
7. publish the operator-approved protocol, thresholds, raw measurements, and
   adjudications before results are inspected.

Storage bytes alone are not a criterion. A win on token count without edit,
merge, and replay parity does not reopen the authority decision. Changing the
canonical source after a successful benchmark requires a new contract version
and operator ratification.

## 14. Punch-list accounting and pre-G3 deferrals

| Conclusion punch-list item | Draft disposition |
|---|---|
| Bundle schema, canonical composition, `verify-bundle`, per-bundle gate 5 | **LANDED** in §§7–8 and the bundle/replay schemas |
| Profile hash, UTF-8/LF/JCS/order, parent revision/index | **LANDED** in §§2–6 and the record/profile/slice schemas |
| Shared-library / CLI / MCP boundary; no app-to-app edge | **LANDED** in §9 |
| Signed replay maps, probe fixtures/codes, real consumer contract test | **DEFERRED:** their schemas and placement land here; fixture/map instances and test execution require corpus owners and Fizzy implementation, outside this six-file drafting handoff |
| Two-additional-corpus kind/spine sweep and enum freeze | **DEFERRED:** requires operator-reviewed corpus work; schemas deliberately mark the enum and spine provisional until G3 |
| Verbatim mechanical-vs-operator table | **LANDED** in §12 |

No other conclusion punch-list item is deferred.
