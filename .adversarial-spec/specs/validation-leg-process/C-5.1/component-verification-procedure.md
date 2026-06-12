# C-5.1 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: artifact-sync
Verification scope: static

## What Runs

- No automated command is declared for this exempt node.

## Evidence Required

Artifact evidence is the documented Phase 7 section plus dogfood TC-0.1 cold-read proof.

## Mapped Tests

- Test refs: TC-0.1
- Test files: skills/adversarial-spec/phases/07-execution.md

## Acceptance Criteria Covered

- "Validation leg (system altitude)" section added after execution plan, before pipeline_load; gated on session_altitude=="system" (read via MCP card metadata, US-2)
- Documents order derive-conops -> draft rows -> normalize-rows -> check-rows; ?3 minimal-row standard; ONE good + ONE rejected row example (CB-7 normalize in sequence)
- Records drafted_baseline_hash; anti-hindsight note (rows precede implementation)

## Traceability

- Architecture refs: .architecture/filesystem-map.md, .architecture/structured/components/debate-engine.md
- Concern refs: US-0, CB-7, DD-10, OP-11
- Invariant refs: INV-7, INV-A5
