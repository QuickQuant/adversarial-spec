## Document Types

Ask the user which type of document they want to produce:

### Spec (Unified Specification)

**Two pathways:** `spec` (for creating new things) and `debug` (for fixing existing things).

The `spec` pathway has three depth levels that control required sections:

| Depth | Focus | When to Use |
|-------|-------|-------------|
| `product` | User value, stakeholders, success metrics | Product planning, stakeholder alignment |
| `technical` | Architecture, APIs, data models | Engineering implementation |
| `full` | All of the above | Complete journey from requirements to implementation |

**CLI usage:**
```bash
# Product-focused spec (like old PRD)
adversarial-spec critique --doc-type spec --depth product

# Technical spec (like old tech spec)
adversarial-spec critique --doc-type spec --depth technical

# Full spec (both product and technical)
adversarial-spec critique --doc-type spec --depth full
```

**Legacy flags (deprecated, will be removed in v2.0):**
- `--doc-type prd` → `--doc-type spec --depth product`
- `--doc-type tech` → `--doc-type spec --depth technical`

#### Spec Structure by Depth

**Product depth** (stakeholder-focused):
- Executive Summary
- Problem Statement / Opportunity
- Target Users / Personas
- User Stories / Use Cases
- Functional Requirements
- Non-Functional Requirements
- Success Metrics / KPIs
- Scope (In/Out)
- Dependencies
- Risks and Mitigations

**Technical depth** (engineering-focused):
- Overview / Context
- Goals and Non-Goals
- **Getting Started** (REQUIRED - bootstrap workflow)
- System Architecture
- Component Design
- API Design (endpoints, request/response schemas)
- Data Models / Database Schema
- Infrastructure Requirements
- Security Considerations
- Error Handling Strategy
- Performance Requirements / SLAs
- Observability (logging, metrics, alerting)
- Testing Strategy
- Deployment Strategy
- Migration Plan (if applicable)
- Open Questions / Future Considerations

**Full depth**: All sections from both product and technical.

#### Critique Criteria by Depth

**Product depth:**
1. Clear problem definition with evidence
2. Well-defined user personas with real pain points
3. User stories follow proper format (As a... I want... So that...)
4. Measurable success criteria
5. Explicit scope boundaries
6. Realistic risk assessment

**Technical depth:**
1. **Getting Started section exists** - Clear bootstrap workflow
2. Clear architectural decisions with rationale
3. Complete API contracts (not just endpoints, but full schemas)
4. Data model handles all identified use cases
5. Security threats identified and mitigated
6. Error scenarios enumerated with handling strategy
7. Performance targets are specific and measurable
8. Deployment is repeatable and reversible
9. No ambiguity an engineer would need to resolve

**Full depth:** All criteria from both.

**CRITICAL for Round 1:** Before technical critique, verify:
- All roadmap user stories have corresponding spec sections
- "Getting Started" section exists (technical/full depth)
- Success criteria are testable

### Debug Investigation

Structured investigation document for diagnosing and fixing bugs in existing systems. Uses adversarial debate to ensure evidence-based diagnosis and proportional fixes.

**When to use:**
- Bug reports with unclear root cause
- Performance issues requiring investigation
- Intermittent failures needing systematic diagnosis
- Any situation where you need to understand and fix existing code

**Philosophy: Evidence → Hypothesis → Fix**

The fix might be 1 line or 100 lines—what matters is that it's proportional to the actual problem and justified by evidence. A 1-line bug deserves a 1-line fix. A systemic issue may genuinely need architectural changes. The debate ensures we don't skip steps.

**Structure (Formal Schema):**
- **Symptoms**: User-visible behavior, timing (always/intermittent/under load), when it started, blast radius
- **Expected vs Actual Behavior**: Table comparing expected vs actual for each scenario
- **Evidence Gathered**: Logs with timestamps and interpretation, timings, error messages, reproduction steps
- **Hypotheses**: Ranked by (likelihood × ease of verification), with evidence for/against each
- **Diagnostic Plan**: Immediate checks (<5 min), targeted logging to add, tests to run
- **Root Cause**: File, line, issue description, why it happened, why initial hypotheses were wrong (if applicable)
- **Proposed Fix**: Changes required (table with file, change, lines), before/after code, justification for approach
- **Verification**: Steps to confirm fix, regression checks, log confirmation
- **Prevention**: Test case to add, documentation updates, similar bugs to check

**Critique Criteria:**
1. Evidence before hypothesis - no guessing without data
2. Simple explanations ruled out first - check basics before redesigning
3. Targeted diagnostics - each log answers a specific question
4. Proportional fix - justified by evidence, not by habit
5. Root cause identified - not just symptom masking
6. Verification plan - specific steps to confirm fix

**Anti-patterns flagged:**
- Premature Architecture - proposing abstractions before ruling out simple bugs
- Shotgun Debugging - logging everywhere without hypotheses
- Untested Assumptions - claiming cause without measurement
- Disproportionate Fix - complexity doesn't match evidence
- Scope Creep - "while we're here" improvements

**Security Warning:**
Debug investigations often contain sensitive data. Before submission:
- Scrub logs of PII, API keys, passwords, and credentials
- Remove internal hostnames, IP addresses, and network topology
- Redact customer data
- Follow your organization's data handling policies

Content is sent to LLM providers (OpenAI, Google, etc.). Do not include data that violates corporate policies or regulatory requirements.

**Context Window Guidance:**
Large log files may exceed model context limits. Best practices:
- Include targeted log snippets, not full files
- Focus on logs around the time of the error
- Summarize repetitive patterns rather than including all instances
- Use `grep` or similar to extract relevant lines before inclusion

**Example Debate Flow:**

Round 1 - Initial Investigation:
> User submits: "Orders page takes 60+ seconds to load, sometimes blank"
>
> Model A (codex/gpt-5.3-codex) suggests: "We need a caching layer with TTL and circuit breaker pattern"
>
> Model B (claude) challenges: "Before designing infrastructure, what do the logs show? Have we measured where the 60 seconds is spent?"
>
> Model C (gemini) adds: "The blank page suggests a different issue than slowness. Are these the same bug or two bugs?"

Round 2 - Evidence Gathering:
> Investigation adds: Log shows ORDERS_CB_COMPLETE took 67234ms, breakdown shows AADriver call: 64 seconds
>
> Model A revises: "The 64 seconds is retry overhead. We should add a circuit breaker for AADriver."
>
> Model B challenges: "A full circuit breaker registry is overkill. A simple timestamp check would work. What's the minimal fix?"
>
> Model C adds: "Why is AADriver failing? Is it actually down, or is there a configuration issue?"

Round 3 - Proportional Fix:
> Investigation finds: urllib3 default retry policy causes 3 retries × 10+ seconds = 30+ seconds
>
> Consensus: Proportional fix - disable retries for AADriver (fail fast), add simple timestamp-based skip. ~10 lines total.

**Example invocation:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex,gemini-cli/gemini-3-pro-preview --doc-type debug <<'SPEC_EOF'
# Debug Investigation: Orders Page 60s Load Time

## Symptoms
- Orders page takes 60+ seconds to load
- Sometimes blank entirely
- Started after recent deploy
- Affects all users

## Expected vs Actual Behavior
| Scenario | Expected | Actual |
|----------|----------|--------|
| Load orders page | <2s load time | 60+ seconds |
| Display orders list | Shows all orders | Sometimes blank |

## Evidence Gathered
### Logs
- [10:23:45] ORDERS_CB_COMPLETE took 67234ms
- [10:23:45] "Max retries exceeded connecting to AADriver"

### Timings
- Exchange API calls: 3 seconds total
- AADriver call: 64 seconds (timeout + retries)

## Hypotheses
| # | Hypothesis | Evidence For | Evidence Against | Verification | Effort |
|---|------------|--------------|------------------|--------------|--------|
| 1 | AADriver retry storm | Log shows 64s, retry message | None | Check retry config | 5 min |
| 2 | Database slow | General slowness | Logs show DB queries fast | Query timing | 15 min |
...
SPEC_EOF
```

