# Checkpoint: Prior Art Scout Concern Explosion Fix

**Date:** 2026-01-31
**Session:** Prior Art Scout Concern Explosion
**Status:** Complete

## Problem

`prior_art_scout` generated 713 concerns in prediction-prime gauntlet run, while all other adversaries combined generated only 96 (7.4x ratio).

## Root Causes Found

### 1. Naive Line-by-Line Parser
The parser at `gauntlet.py:2229-2237` treated every line starting with a digit or dash as a separate concern. This fragmented structured output:

```
1. **Security Risk**: SQL injection possible
   - Attack vector: User input not sanitized
   - Impact: Full database compromise
```

Became 4 "concerns" instead of 1.

### 2. Model Repetition
The model output contained summary sections that repeated 35-37 times. 17 unique "summary" items appeared 35-37x each, accounting for 603 of the 713 entries.

### 3. Quality Impact
Frontier models were evaluating fragments like "Attack vector: User input not sanitized" as standalone concerns - leading to "Evaluation failed" or hallucinated reasoning.

## Fixes Applied

### Parser Fix (gauntlet.py:2227-2270)
- Groups numbered items with their sub-bullets into single concerns
- Uses `flush_concern()` pattern to accumulate lines
- Adds deduplication via `seen_texts` set

**Before:** 13 fragments from 4 real concerns
**After:** 4 real concerns

### Big Picture Synthesis (Phase 2)
New phase asks model to synthesize across ALL concerns:
- Real issues (the 2-4 things that matter)
- Hidden connections between adversaries
- What's missing (blind spots)
- Meta-concern tying everything together
- High-signal concerns for attention

### Phase Renumbering
Removed confusing `.5` versions:

| Phase | Name |
|-------|------|
| 1 | Attack Generation |
| 2 | Big Picture Synthesis (NEW) |
| 3 | Self-Filtering |
| 4 | Evaluation |
| 5 | Rebuttals |
| 6 | Final Adjudication |
| 7 | Final Boss |

## Files Changed

- `skills/adversarial-spec/scripts/gauntlet.py`
  - Parser fix at lines 2227-2270
  - BigPictureSynthesis dataclass
  - `generate_big_picture_synthesis()` function
  - Phase 2 integration in `run_gauntlet()`
  - All phase number updates

## Deployment

Changes are live in `~/.claude/skills/adversarial-spec/scripts/gauntlet.py` (same file via hard link).

## Next Steps

1. Test the fix by running a gauntlet on a real spec
2. Verify concern counts are reasonable (not 10x inflated)
3. Review Big Picture Synthesis output for usefulness
