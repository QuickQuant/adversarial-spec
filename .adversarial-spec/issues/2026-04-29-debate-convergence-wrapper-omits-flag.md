# Debate Convergence Wrapper Omits Flag

## Failure

Round 3 for session `adv-spec-202604291604-dispatch-cost-tracker-unify` completed with both managed critic models terminal and agreed:

- `claude-cli/claude-opus-4-7`: completed, agreed, 0 findings
- `gemini-cli/gemini-3.1-pro-preview`: completed, agreed, 0 findings

The phase convergence rule is satisfied: Claude plus all external models agree and no findings remain.

However, `pipeline_advance_debate_round` returned `convergence: false` and wrote `extensions.debate.last_converged=false`.

## Root Cause

The underlying Fizzy function `/home/jason/PycharmProjects/fizzy-pipeline-mcp/src/fizzy_pipeline_mcp/pipeline.py::advance_debate_round` accepts a `convergence: bool = False` parameter and records it into the round history.

The MCP wrapper `/home/jason/PycharmProjects/fizzy-pipeline-mcp/src/fizzy_pipeline_mcp/server.py::pipeline_advance_debate_round` does not expose or forward a `convergence` argument, so MCP callers cannot declare convergence through the canonical round-advance tool.

## Short-Term Workaround

Use `pipeline_patch_state` after a successful round advance to patch only the convergence state for the already-recorded round:

- `extensions.debate.last_converged=true`
- the matching round history entry's `convergence=true`

Do not alter critic outcomes, round numbers, spec paths, or checklist state.

## Permanent Fix

Update the MCP wrapper contract to expose `convergence: bool = False` and forward it to `advance_debate_round`. Add a regression test that calls the MCP wrapper with `convergence=true` and verifies both `last_converged` and the round history entry are true.
