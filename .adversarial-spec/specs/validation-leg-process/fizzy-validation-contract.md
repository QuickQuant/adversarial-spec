# Fizzy System-Validation Gate — Served-Code Contract Extract

> Extracted 2026-06-11 from /home/jason/PycharmProjects/fizzy-pipeline-mcp
> working tree (branch claim-race-in-progress-status) by an Explore agent.
> This is the FIXED contract the skill-side process must satisfy. Verify line
> numbers before citing in debate; behavior is the load-bearing part.

## Tool: `mark_system_validation_complete` (pipeline.py:9139-9346)

```python
async def mark_system_validation_complete(
    client, *, card_id: str, session_id: str, board_id: str | None = None,
    validation_artifact_path: str,   # path to system_validation.json
    conops_path: str,                # path to ConOps / user-intent artifact
) -> dict
```

Returns `{ok, card_id, kind="system_validation", rows, system_validation_artifacts}`.

## Preconditions (fail-closed, in order)

1. `_task_belongs_to_session` → else `SESSION_MISMATCH` (:9177)
2. `altitude == "system"` → else `VV_NOT_OBLIGATED_AT_ALTITUDE` (:9184)
3. `conops_path` readable, ≥50 bytes, suffix .md/.txt/.json → else
   `VALIDATION_ARTIFACTS_INCOMPLETE`; hashed via `_sha256_prefix` (:9191-9197)
4. `validation_artifact_path` readable .json, dict, `kind == "system-validation"`
   → else `VALIDATION_KIND_MISMATCH` (:9215)
5. Artifact `conops_hash` must prefix-match (either direction) the fresh hash of
   `conops_path` → staleness binding (:9232-9243)
6. `rows`: non-empty list of dicts; EVERY row requires non-empty strings
   `conops_ref` (user-story pointer, NOT a test file), `scenario` (end-to-end,
   user terms), `oracle` (how pass/fail judged from user intent), and
   `result ∈ {pass, fail, not-applicable}` (:9245-9282)
7. Any `result == "fail"` → `VV_LEDGER_HAS_FAILURES` with failing refs (:9284)
8. Anti-relabeling: validation rows' `test_targets` must NOT be a strict subset
   of `system_verification_artifacts`' test targets → else
   `VALIDATION_IS_RELABELED_VERIFICATION` (:9293-9315)

## Stored on card (write-once `system_validation_artifacts`, :9318-9328)

`validation_artifact_path`, `conops_path`, `conops_hash`, `row_count`,
`conops_ref_count`, `completed_at`. No per-row evidence field exists in the
contract — evidence lives skill-side.

## Obligation predicate `_node_owes_system_validation` (:8735-8746)

`pipeline_version >= 5 AND altitude == "system"`. v4 grandfathered.
`system_verification_complete` does NOT satisfy it (independence, "C2").

## V-completeness `_node_is_v_complete` (:8749-8766)

Altitude obligations each checked via `VV_COMPLETE_FLAG`; `system_validation`
appended independently if owed and `system_validation_complete is not True`.

## Session-close coverage gate `_check_system_validation_coverage_sync` (:9447-9572)

Runs at Finalization→Completed advance (v5 only):
- Every v5 system node must have `system_validation_complete == True` → else
  `SYSTEM_VALIDATION_MISSING`.
- Extracts ALL `US-\d+` ids (regex `\bUS-\d+\b`, :9438-9439) from the ConOps
  file; every id must appear in ≥1 row with `result == "pass"` (substring match
  on `conops_ref`) → else `UNVALIDATED_USER_STORY` (fails closed if artifacts
  unreadable).

## Schema-3 plan rule (:5045-5048)

A `system_validation` key in any task's verification binding →
`VV_ABOVE_ALTITUDE` ("system_validation is not part of the v4 contract").
Validation closes CARD-SIDE only, never plan-side.

## Where altitude lives

- Session card `pipeline_metadata`: `session_altitude`, `session_altitude_source`,
  `altitude_at_debate_start` (immutable capture at debate start, :6226-6229).
- Task cards: `altitude`, immutable at plan-load (`_ALTITUDE_IMMUTABLE`, :390).
- `CURRENT_PIPELINE_VERSION = 5` (:93).

## Fizzy-side design-doc anchors

- `20-vv-and-validation.md:163,179,184-186` — conops_ref points at roadmap
  user-story ids; hash binding rationale.
- `60-cross-repo-contract.md:6-7` — validation migration hooks.
- `NASA-CROSSWALK-SUPPLEMENT.md:53,261,543-544` — Appx S ConOps outline as the
  intended ConOps shape.
