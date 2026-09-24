# adversarial-spec

`adversarial-spec` turns an idea, change request, or existing document into an
evidence-backed specification and implementation plan. Independent models
challenge the work; the operator retains every product and approval decision.

The division of labor is deliberate:

- **Adversarial Spec decides what must be true:** requirements, roadmap,
  architecture, concerns, execution plan, and verification evidence.
- **Fizzy Pipeline decides what may move next:** Card lanes, human and machine
  gates, claims, dependencies, independent review, test results, and closeout.

A Phase is a reasoning unit. A lane is board state. They are related, but they
are not a 1:1 state machine.

## Requirements and installation

- Python 3.14 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Claude Code with a writable `~/.claude/skills/` directory
- A configured Fizzy Pipeline MCP for card-backed work

Clone the repository, install its locked environment, and expose the skill to
Claude Code:

```bash
git clone https://github.com/zscole/adversarial-spec.git
cd adversarial-spec
uv sync
mkdir -p ~/.claude/skills
ln -s /absolute/path/to/adversarial-spec/skills/adversarial-spec ~/.claude/skills/adversarial-spec
```

Use an absolute symlink target. The deployed skill is then the repository copy;
source edits are immediately visible without a copy step.

`pyproject.toml` exposes two Python console entry points:

```bash
uv run adversarial-spec --help
uv run gauntlet-check --help
```

The slash command, not either console entry point, owns the end-to-end workflow:

```text
/adversarial-spec <idea-or-document>
```

## Entry and routing

Every invocation starts at the **First Gate** in
[`SKILL.md`](skills/adversarial-spec/SKILL.md). It performs a read-only probe of
the local pointer and staged intake receipts:

1. Resume a valid active Session at its recorded Phase.
2. Recover one unambiguous incomplete Phase 0 handoff without minting a second
   Session or Session Card.
3. With no resumable state, enter
   [Phase 0 triage](skills/adversarial-spec/phases/00-triage.md).

Phase 0 chooses a route, records a candidate Slice North Star and root altitude,
and either stops with a NO-GO result or creates exactly one Session Card plus
local Session state. It does not bootstrap a Session before GO.

The lifecycle then has **eight Phases**:

| Phase | Purpose | Guidance |
|---|---|---|
| 1. Requirements | Resolve the boundary, lock the Slice North Star, and assign requirement IDs. | [`01-init-and-requirements.md`](skills/adversarial-spec/phases/01-init-and-requirements.md) |
| 2. Roadmap | Define milestones, user journeys, test intent, and architecture impact. Exactly one milestone carries the Slice North Star. | [`02-roadmap.md`](skills/adversarial-spec/phases/02-roadmap.md) |
| 3. Debate | Run independent, codebase-grounded critique until the configured convergence gate closes. | [`03-debate.md`](skills/adversarial-spec/phases/03-debate.md) |
| 4. Target architecture | Record architecture decisions and invariants. Skip mode still emits a deliberate stub. | [`04-target-architecture.md`](skills/adversarial-spec/phases/04-target-architecture.md) |
| 5. Gauntlet | Stress the spec and architecture, then disposition every spec Concern. | [`05-gauntlet.md`](skills/adversarial-spec/phases/05-gauntlet.md) |
| 6. Finalize | Run consistency, scope, traceability, contract, and test-adequacy checks; obtain user review. | [`06-finalize.md`](skills/adversarial-spec/phases/06-finalize.md) |
| 7. Execution | Produce, approve, validate, and load the implementation plan. | [`07-execution.md`](skills/adversarial-spec/phases/07-execution.md) |
| 8. Implementation | Implement through plan-backed Task Cards, independent review, testing, and whole-change verification. | [`08-implementation.md`](skills/adversarial-spec/phases/08-implementation.md), [verification subflow](skills/adversarial-spec/phases/09-verification.md) |

Verification is a **Phase 8 subflow**, represented locally as
`current_phase: implementation` and `current_step: verification`. There is no
ninth lifecycle Phase.

### Version 6 decomposition

For pipeline version 6, a board-level Decomposition gate sits between the
roadmap and Debate. It establishes the component tree, responsibility cuts,
interfaces, and unresolved seam evidence before component work fans out. This
is a v6 lane gate, not an additional lifecycle Phase.

The same v6 route has no Target Architecture lane. Phase 4 still runs and emits
its required artifact; a skip-mode artifact travels with the decomposition
record. The board route never authorizes silently omitting Phase 4.

## Durable artifact chain

Artifacts, not conversation history, carry the work forward.

| Producer | Durable result | Next consumer |
|---|---|---|
| Phase 0 | Intake receipt, Session detail, pointer, and Session Card after GO | First Gate recovery and Phase 1 |
| Phase 1 | `requirements_summary`, requirement IDs, locked Slice North Star, root altitude | Roadmap and v6 decomposition |
| Phase 2 | Roadmap manifest or approved inline roadmap, `tests-pseudo.md`, architecture-impact decision | Decomposition and Debate |
| v6 decomposition | Component tree, responsibility/interface records, seam evidence, closure receipt | Component Debate fan-out |
| Phase 3 | Versioned spec draft, critic receipts, synchronized test intent, retained context inventory | Target architecture and Gauntlet |
| Phase 4 | `target-architecture.md`, `architecture-invariants.json`, dry-run evidence, optional middleware candidates | Gauntlet and execution reconciliation |
| Phase 5 | `gauntlet-concerns-*.json`, dispositions, revised spec and tests | Finalization and concern-to-task mapping |
| Phase 6 | Approved `spec-output.md` or `debug-output.md`, plus `tests-spec.md` when applicable | Execution planning |
| Phase 7 | `execution-plan.md`, validated `fizzy-plan.json`, and materialized plan-backed Task Cards | Implementation |
| Phase 8 | Card-level implementation/review/test evidence and a verification report | Fizzy sweep and terminal state |

The machine-facing artifact grammar and ownership boundary live in
[`contracts/spec-record-contract.md`](contracts/spec-record-contract.md).

## Fizzy lanes

The current v6 Session Card route is:

```text
Evaluated Plans → Pre-Roadmap → Decomposition → Debate → Pre-Gauntlet
→ Gauntlet → Reconciliation → Finalization → Completed-Unmapped
```

Key gates include human G1 on entry to Decomposition, machine `d0_closed` on
its exit, Debate readiness plus human G2, fresh architecture context, gauntlet
and reconciliation completion, human G3, and final Task Card closure. Older
Cards remain on their grandfathered route; inspect their metadata rather than
inferring behavior from the current version.

Task Cards use two related paths:

- v6 specification leaves move through `Specifying → Synthesized`; non-leaf
  containers remain in `Decomposed` until their subtree closes.
- Implementation work moves through `New Todo → Review → Untested → Passed Test`
  and then a verified sweep to a completed lane. `Failed Review` returns work to
  its reserved implementer.

## Safety rails

- Pass an explicit `board_id` on every board-scoped call.
- Inspect with `pipeline_lane_state`; call `pipeline_do_next_task` only when
  ready to perform whatever it claims and returns.
- Create Task Cards from an approved plan. Amend the plan, run
  `pipeline_validate_plan`, then `pipeline_load`; never substitute a raw Card.
- Never use `pipeline_patch_state` to skip a fence or manufacture progress.
- Preserve the First Gate recovery rules and all human gates: G1/G2/G3, Phase 4
  decisions, Phase 6 user review, and Phase 7 plan approval.
- An implementer cannot review their own work. A claim is a lease; native
  assignment is display metadata.
- Attach evidence before making completion, test, review, or verification
  claims. A notification or Card comment is an audit record, not proof of a
  successful transition.
- Write Session detail before the pointer, using atomic same-filesystem writes.
  See `SKILL.md` § `Phase Transition Protocol` and § `Fizzy Card Comment Convention`.

## Where to look

| Need | Authority |
|---|---|
| Entry, resume, routing, transitions, comments, decisions, journey records | [`skills/adversarial-spec/SKILL.md`](skills/adversarial-spec/SKILL.md) |
| Phase-local entry, gates, outputs, and handoff | [`skills/adversarial-spec/phases/`](skills/adversarial-spec/phases/) |
| Document types, altitude, context transport, commands, and specialist protocols | [`skills/adversarial-spec/reference/`](skills/adversarial-spec/reference/) |
| Current model assignments and retired routes | [`reference/current-models.md`](skills/adversarial-spec/reference/current-models.md) |
| Spec-record schema, hashes, ownership, and replay gates | [`contracts/spec-record-contract.md`](contracts/spec-record-contract.md) |
| Source-backed codebase orientation | [`.architecture/INDEX.md`](.architecture/INDEX.md) |

Do not copy model assignments or transition machinery into another document.
Point readers to the authority above.

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup and checks, and
[`onboarding/project-practices.md`](onboarding/project-practices.md) for source
navigation and repository-specific conventions.

## License

MIT
