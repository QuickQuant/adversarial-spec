# Adopt the TMR test ladder and split skill authoring from Fizzy enforcement

## Status

Accepted.

## Context

The liveness-gate work closes a failure where a critical seam had rich prose and
mock-heavy tests but no proof that the happy path ran live or through a named
fault-induced technique. The same discussion also overloaded the happy-path spine
vocabulary: Phase 7 already uses **Architecture Spine** for cross-cutting implementation
patterns, while the test ladder uses **happy-path spine** for a user story's
primary-success test.

## Decision

- Use **Test Maturity Record** (TMR) as the schema-first record for test identity,
  happy-path spine designation, maturity, liveness classification, binding, run
  evidence, and lineage.
- Use the **Maturity Ladder** `nl -> acceptance -> concrete` for evidence
  progression.
- Treat **Liveness** as real data or a named live/fault-induced technique captured
  in run evidence; a mock-only pass is not liveness for a critical seam.
- Qualify the prose term as **happy-path spine**. Machine tokens such as `spine`,
  `spine_of`, `spine_steps`, `spine_step_ref`, `orphaned_spine`, and
  `SpineCoverageChecker` keep their exact names. Phase 7 keeps **Architecture Spine**
  for implementation patterns.
- Split project scope in two: adversarial-spec authors, compiles, audits, and
  drives promotion of TMRs; Fizzy persists/enforces the same fields and owns the
  non-bypassable gauntlet/sweep gates.

## Consequences

- `tests-pseudo.md` is an authoring view. `tmr-registry.json` is the local system
  of record after compile.
- TRACE may report a missing or mislabeled happy-path spine as a traceability
  break, but it must not suggest arbitrary edge/error/unit tests.
- The non-bypassable guarantee depends on the coordinated Fizzy-side gate. This
  skill slice alone is advisory until that cross-project enforcement is live.
