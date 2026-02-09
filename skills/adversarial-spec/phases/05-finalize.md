### Step 6: Finalize and Output Document

When ALL opponent models AND you have said `[AGREE]` (and gauntlet is complete or skipped):

**Before outputting, perform a final quality check:**

1. **Completeness**: Verify every section from the document structure is present and substantive
2. **Consistency**: Ensure terminology, formatting, and style are uniform throughout
3. **Clarity**: Remove any ambiguous language that could be misinterpreted
4. **Actionability**: Confirm stakeholders can act on this document without asking follow-up questions

**For Specs (product depth), verify:**
- Executive summary captures the essence in 2-3 paragraphs
- User personas have names, roles, goals, and pain points
- Every user story follows "As a [persona], I want [action] so that [benefit]"
- Success metrics have specific numeric targets and measurement methods
- Scope explicitly lists what is OUT as well as what is IN

**For Specs (technical/full depth), verify:**
- Architecture diagram or description shows all components and their interactions
- Every API endpoint has method, path, request schema, response schema, and error codes
- Data models include field types, constraints, indexes, and relationships
- Security section addresses authentication, authorization, encryption, and input validation
- Performance targets include specific latency, throughput, and availability numbers
- **Getting Started** section exists with clear bootstrap workflow

**For Debug Investigations, verify:**
- Evidence gathered before hypotheses formed (no guessing without data)
- Simple explanations ruled out before complex ones
- Root cause identified with clear evidence chain
- Proposed fix is proportional to the problem (not over-engineered)
- Verification plan exists with specific steps to confirm the fix
- Prevention section identifies tests to add and documentation updates

**Output the final document:**

1. Print the complete, polished document to terminal
2. Write it to the appropriate file:
   - Spec: `spec-output.md`
   - Debug Investigation: `debug-output.md`
3. Print a summary:
   ```
   === Debate Complete ===
   Document: [Product Specification | Technical Specification | Full Specification | Debug Investigation]
   Rounds: N
   Models: [list of opponent models]
   Claude's contributions: [summary of what you added/changed]

   Key refinements made:
   - [bullet points of major changes from initial to final]
   ```
4. If Telegram enabled:
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py send-final --models MODEL_LIST --doc-type TYPE --rounds N <<'SPEC_EOF'
   <final document here>
   SPEC_EOF
   ```
5. Update session with artifact paths (sync both files per Phase Transition Protocol):
   - Detail file (`sessions/<id>.json`): set `spec_path` to the written file path (`"spec-output.md"` or `"debug-output.md"`)
   - If gauntlet was run, also set `gauntlet_concerns_path` to the saved concerns JSON
   - Append journey: `{"time": "ISO8601", "event": "Spec finalized: <path>", "type": "artifact"}`
   - Update both files with `current_phase: "finalize"`, `current_step: "Document finalized, awaiting user review"`
   - Use atomic writes for both files

### Step 7: User Review Period

**After outputting the finalized document, give the user a review period:**

> "The document is finalized and written to `spec-output.md`. Please review it and let me know if you have any feedback, changes, or concerns.
>
> Options:
> 1. **Accept as-is** - Document is complete
> 2. **Request changes** - Tell me what to modify, and I'll update the spec
> 3. **Run another review cycle** - Send the updated spec through another adversarial debate"

**If user requests changes:**
1. Make the requested modifications to the spec
2. Show the updated sections
3. Write the updated spec to file
4. Ask again: "Changes applied. Would you like to accept, make more changes, or run another review cycle?"

**If user wants another review cycle:**
- Proceed to Step 8 (Additional Review Cycles)

**If user accepts:**
- Finalization complete. Ask if they want to proceed to execution planning (Phase 5).

### Step 8: Additional Review Cycles (Optional)

After the user review period, or if explicitly requested:

> "Would you like to run an additional adversarial review cycle for extra validation?"

**If yes:**

1. Ask if they want to use the same models or different ones:
   > "Use the same models (MODEL_LIST), or specify different models for this cycle?"

2. Run the adversarial debate again from Step 3 with the current document as input.

3. Track cycle count separately from round count:
   ```
   === Cycle 2, Round 1 ===
   ```

4. When this cycle reaches consensus, return to Step 7 (User Review Period).

5. Update the final summary to reflect total cycles:
   ```
   === Debate Complete ===
   Document: [Product Specification | Technical Specification | Full Specification | Debug Investigation]
   Cycles: 2
   Total Rounds: 5 (Cycle 1: 3, Cycle 2: 2)
   Models: Cycle 1: [models], Cycle 2: [models]
   Claude's contributions: [summary across all cycles]
   ```

**Use cases for additional cycles:**
- First cycle with faster models (gemini-cli/gemini-3-flash-preview), second cycle with stronger models (codex/gpt-5.3-codex, gemini-cli/gemini-3-pro-preview)
- First cycle for structure and completeness, second cycle for security or performance focus
- Fresh perspective after user-requested changes

