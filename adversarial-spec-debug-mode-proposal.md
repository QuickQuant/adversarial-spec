# Proposal: Add "Debug Investigation" Document Type to Adversarial Spec

## Executive Summary

The adversarial-spec skill is powerful for generating and refining specifications through multi-LLM debate. However, it currently only supports PRD and Tech Spec document types, which are designed for greenfield feature development. This proposal adds a `debug` document type that applies the same adversarial debate process to **diagnosing and fixing bugs in existing systems**.

## The Problem: A Real-World Case Study

### What Happened

A user had a Dash trading application with UI freezing issues:
- Orders page blank/lagging 20+ seconds
- Balances page missing an exchange (Kraken)
- WebSocket reconnection spam in logs

They invoked adversarial-spec to plan fixes. The resulting plan proposed:

**What the plan generated (200+ lines of new code):**
- New `app/services/exchange_health.py` - Thread-safe circuit breaker registry with complex state machine (CLOSED/OPEN/HALF_OPEN/DISABLED states, exponential cooldowns, half-open probes)
- New `app/services/balance_fetch_manager.py` - Shared ThreadPoolExecutor with in-memory cache, atexit handlers, stale marking
- Complete rewrite of balance fetching to use new manager pattern
- Configuration keys, SLAs, security considerations, observability counters

**What actually fixed the problems (~30 lines of targeted changes):**

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Orders page blank | Redis returns bytes, code did `key.split(":")` on bytes | `key.decode() if isinstance(key, bytes) else key` |
| Orders page 60s delay | urllib3 retries AADriver when offline | Simple timestamp-based circuit breaker (10 lines) |
| Kraken missing | API returns Brotli encoding, SDK can't decode | Add header: `Accept-Encoding: gzip, deflate` |
| 7-day filter excluding data | `zrangebyscore` with cutoff vs `zrange` for all | Remove unnecessary time filter |
| WebSocket spam | No backoff on reconnect | Add exponential backoff with jitter |

### The Mismatch

The adversarial-spec process, designed for feature planning, naturally produced an architectural solution. But the actual problems were:
- A bytes vs string bug (1 line fix)
- A missing HTTP header (1 line fix)
- An overly aggressive time filter (1 line fix)
- Missing retry limits (10 line fix)

**The debate process itself was not the problem.** The problem was that the critique criteria were designed for evaluating feature completeness, not debugging effectiveness.

---

## Proposed Solution: `--doc-type debug`

Add a new document type specifically for debugging investigations that uses the adversarial debate to:
1. Challenge assumptions about root cause
2. Prevent premature architectural solutions
3. Enforce evidence-based diagnosis
4. Ensure minimal, targeted fixes

---

## Document Structure: Debug Investigation

```markdown
# Debug Investigation: [Brief Problem Description]

## 1. Symptoms
- What is broken? (user-visible behavior)
- When does it happen? (always, intermittently, under load)
- When did it start? (after deploy, gradually, always)
- What is the blast radius? (one user, all users, one feature)

## 2. Expected vs Actual Behavior
| Scenario | Expected | Actual |
|----------|----------|--------|
| ... | ... | ... |

## 3. Evidence Gathered
### Logs
- [Timestamp] [Level] [Message] - Interpretation
### Timings
- Operation X: expected Yms, actual Zms
### Error Messages
- Exact error text, stack traces
### Reproduction Steps
- Step-by-step to trigger the issue

## 4. Hypotheses
Ranked by: (likelihood × ease of verification)

| # | Hypothesis | Evidence For | Evidence Against | Verification Step | Effort |
|---|------------|--------------|------------------|-------------------|--------|
| 1 | ... | ... | ... | ... | 5 min |
| 2 | ... | ... | ... | ... | 30 min |

## 5. Diagnostic Plan
### Immediate Checks (< 5 min each)
- [ ] Check X log for Y
- [ ] Verify Z is configured correctly
- [ ] Test if A works in isolation

### Targeted Logging to Add
```python
# Location: file.py:123
# Purpose: Verify hypothesis #2
logger.debug(f"Value of X at checkpoint: {x}, type: {type(x)}")
```

### Tests to Run
- [ ] Unit test for isolated component
- [ ] Integration test with mock
- [ ] Manual test with real data

## 6. Root Cause (once found)
### The Bug
- File: `path/to/file.py`
- Line: 123
- Issue: [Clear description]

### Why It Happened
- [Contributing factors, how it slipped through]

### Why Initial Hypotheses Were Wrong (if applicable)
- [What misled the investigation]

## 7. Minimal Fix
### Changes Required
| File | Change | Lines |
|------|--------|-------|
| ... | ... | ~N |

### The Fix
```python
# Before
problematic_code()

# After
fixed_code()
```

### Why This Fix and Not Something Bigger
- [Justify minimalism, explain what was NOT done and why]

## 8. Verification
- [ ] Bug no longer reproduces
- [ ] No regressions in related functionality
- [ ] Logs confirm correct behavior

## 9. Prevention
- [ ] Add test case that would have caught this
- [ ] Update documentation if needed
- [ ] Consider if similar bugs exist elsewhere
```

---

## Critique Criteria for Debug Investigations

Models should evaluate debug documents against these criteria:

### 1. Evidence Before Hypothesis
- **FAIL**: Jumping to solutions without reading logs/errors
- **FAIL**: "The problem is probably X" without evidence
- **PASS**: "Log shows X at timestamp Y, which suggests Z"

**Challenge phrase**: "What specific evidence supports this hypothesis?"

### 2. Simple Explanations First
- **FAIL**: Proposing architectural changes before checking for typos, wrong types, missing configs
- **FAIL**: "We need a new service layer" when the issue might be a 1-line bug
- **PASS**: Hypotheses ordered by simplicity, with simple checks done first

**Challenge phrase**: "Have we ruled out simpler explanations like [type errors, missing headers, wrong config values]?"

### 3. Targeted Diagnostics
- **FAIL**: "Add logging everywhere to see what's happening"
- **FAIL**: Shotgun debugging with no clear hypothesis
- **PASS**: "Add this specific log at line X to verify hypothesis Y"

**Challenge phrase**: "What specific question will this diagnostic answer?"

### 4. Minimal Fix Principle
- **FAIL**: Fix introduces new abstractions, services, or patterns
- **FAIL**: Fix is larger than the bug (10-line bug, 200-line fix)
- **FAIL**: Fix includes "improvements" unrelated to the bug
- **PASS**: Fix is proportional to the bug
- **PASS**: Fix changes only what's necessary

**Challenge phrase**: "Is this fix minimal? What would a smaller fix look like?"

### 5. Root Cause vs Symptom
- **FAIL**: Fix addresses symptoms without understanding cause
- **FAIL**: "It works now" without explaining why it was broken
- **PASS**: Clear explanation of the actual bug mechanism

**Challenge phrase**: "Are we fixing the root cause or masking symptoms?"

### 6. Verification Plan
- **FAIL**: "Deploy and see if it's fixed"
- **FAIL**: No way to confirm the fix worked
- **PASS**: Specific steps to verify the fix
- **PASS**: Test case that would have caught the bug

**Challenge phrase**: "How will we know this is actually fixed?"

---

## Anti-Patterns to Flag

The debate should actively challenge these anti-patterns:

### Architecture Astronaut
> "Let's add a circuit breaker registry with state machine..."

**Challenge**: "Have we confirmed the service is actually failing, or is there a simpler bug preventing the call from working?"

### Premature Abstraction
> "We should create a shared executor pool with caching..."

**Challenge**: "What specific bug does this solve? Could we fix that bug without new abstractions?"

### Shotgun Debugging
> "Add logging to all the exchange methods and see what's happening..."

**Challenge**: "What specific hypothesis are we testing? What log line would confirm or deny it?"

### Untested Assumptions
> "The timeout must be causing the delay..."

**Challenge**: "What's the actual timing? Have we measured it?"

### Solution Shopping
> "I've seen this pattern before, we need X..."

**Challenge**: "Is this the same problem, or are we pattern-matching incorrectly?"

### Scope Creep
> "While we're fixing this, we should also refactor..."

**Challenge**: "Is that related to the bug? Can it be a separate change?"

---

## Example Debate Flow

### Round 1: Initial Investigation

**User submits symptoms:**
```
Orders page takes 60+ seconds to load.
Sometimes it's blank entirely.
```

**Model A (gpt-4o) suggests:**
> We need a caching layer with TTL and a circuit breaker pattern for exchange failures.

**Model B (claude) challenges:**
> Before designing infrastructure, what do the logs show? Have we measured where the 60 seconds is spent?

**Model C (gemini) adds:**
> The blank page suggests a different issue than slowness. Are these the same bug or two bugs?

### Round 2: Evidence Gathering

**Investigation adds evidence:**
```
Log shows: ORDERS_CB_COMPLETE took 67234ms
Breakdown:
- Exchange API calls: 3 seconds total
- AADriver call: 64 seconds (timeout + retries)
Log shows: "Max retries exceeded connecting to AADriver"
```

**Model A revises:**
> The 64 seconds is retry overhead. We should add a circuit breaker for AADriver.

**Model B challenges:**
> A full circuit breaker registry is overkill. A simple "skip if failed recently" timestamp check would work. What's the minimal fix?

**Model C adds:**
> Why is AADriver failing at all? Is it actually down, or is there a configuration issue?

### Round 3: Minimal Fix

**Investigation finds:**
```
AADriver is sometimes offline during development.
urllib3 default retry policy: 3 retries with backoff.
Each retry waits 10+ seconds.
3 retries × 10 seconds = 30+ seconds of waiting.
```

**Consensus:**
> Minimal fix: Disable retries for AADriver calls (fail fast), add simple timestamp-based skip if recently failed. Total: ~10 lines. No new service layers needed.

---

## Implementation Notes

### Script Changes (`debate.py`)

Add `debug` to valid doc types:
```python
DOC_TYPES = ['prd', 'tech', 'debug']
```

Add debug-specific system prompt:
```python
DEBUG_CRITIQUE_PROMPT = """
You are reviewing a debug investigation document. Your role is to:

1. Challenge assumptions - Is there evidence for each hypothesis?
2. Enforce simplicity - Are we checking simple bugs before proposing architecture?
3. Verify diagnostics are targeted - Does each log/test answer a specific question?
4. Ensure minimal fixes - Is the proposed fix proportional to the bug?
5. Distinguish root cause from symptoms - Do we understand WHY it's broken?

Anti-patterns to flag:
- Proposing new services/abstractions before finding the actual bug
- "Add logging everywhere" without specific hypotheses
- Fixing symptoms without understanding root cause
- Scope creep ("while we're here, let's also...")

Your critique should include:
- What evidence is missing?
- What simpler explanations haven't been ruled out?
- Is the fix minimal and proportional?

If the investigation is thorough and the fix is minimal, respond with [AGREE].
"""
```

### Skill Changes (`SKILL.md`)

Add to Document Types section:

```markdown
### Debug Investigation

Structured investigation for diagnosing and fixing bugs in existing systems.

**Structure:**
- Symptoms
- Expected vs Actual Behavior
- Evidence Gathered
- Hypotheses (ranked)
- Diagnostic Plan
- Root Cause
- Minimal Fix
- Verification

**Critique Criteria:**
1. Evidence before hypothesis - no guessing
2. Simple explanations first - check for typos before redesigning
3. Targeted diagnostics - each log answers a specific question
4. Minimal fix - proportional to the bug, no scope creep
5. Root cause identified - not just symptom masking
6. Verification plan - how to confirm it's fixed
```

---

## Success Metrics

A good debug investigation should:

1. **Find the actual bug** - Not propose workarounds for an unknown issue
2. **Minimize fix size** - Lines changed should be proportional to bug complexity
3. **Include evidence** - Every hypothesis backed by logs/measurements
4. **Be reproducible** - Someone else could follow the same investigation
5. **Prevent recurrence** - Include test case or monitoring for the bug

---

## Appendix: The Real Bugs from Our Case Study

For reference, here are the actual bugs found, showing how simple they were:

### Bug 1: Redis Returns Bytes
```python
# Before (broken)
for key in r.scan_iter(match="orders:fills:*"):
    parts = key.split(":")  # FAILS: bytes has no split()

# After (fixed)
for key in r.scan_iter(match="orders:fills:*"):
    key_str = key.decode() if isinstance(key, bytes) else key
    parts = key_str.split(":")
```

### Bug 2: Kraken Brotli Encoding
```python
# Before (broken)
response = session.post(url, headers=headers, data=data)
# Error: "Can not decode content-encoding: br"

# After (fixed)
headers = {
    'Accept-Encoding': 'gzip, deflate',  # Avoid Brotli
    ...
}
response = session.post(url, headers=headers, data=data)
```

### Bug 3: AADriver Retry Storm
```python
# Before (broken - default retries cause 60s delays)
response = requests.get(aadriver_url, timeout=5)

# After (fixed)
session = requests.Session()
session.mount('http://', HTTPAdapter(max_retries=Retry(total=0)))
response = session.get(aadriver_url, timeout=5)
```

### Bug 4: Overly Aggressive Time Filter
```python
# Before (broken - excluded all data)
items = r.zrangebyscore(key, min=seven_days_ago, max='+inf')

# After (fixed - return everything, it's local Redis)
items = r.zrange(key, 0, -1)
```

None of these required new service layers, circuit breaker registries, or architectural changes. They required reading logs, understanding the error, and making minimal targeted fixes.

---

## Conclusion

The adversarial debate process is valuable for debugging - multiple models challenging each other's assumptions can prevent tunnel vision and premature solutions. But the critique criteria must be different from feature planning:

- **PRD/Tech Spec**: "Is this complete? What's missing?"
- **Debug**: "Is this minimal? What simpler explanation exists?"

Adding `--doc-type debug` with appropriate critique criteria will make adversarial-spec useful for the entire software development lifecycle, not just greenfield features.
