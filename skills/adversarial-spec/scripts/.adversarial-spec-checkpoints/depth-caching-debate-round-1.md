# Depth Array Caching Optimization Spec

## Context

We have two exchange connectors (Polymarket, Kalshi) that maintain local orderbook state and emit updates to Convex. After fixing Polymarket to use Maps (O(1) delta lookups), both connectors now share a pattern:

1. **Internal state**: Map<priceKey, size> for O(1) delta updates
2. **On emit**: Convert Map to sorted array (O(n log n))
3. **Emit frequency**: Per WebSocket message (many per second)

## Problem Statement

With ~100 markets, few deltas each, and 200ms flush intervals:
- **Current**: Every emit converts Map → sorted array (even if unchanged)
- **Cost**: 100 markets × 4 depth arrays × O(n log n) = significant CPU per emit cycle

The user's concern: "we're emitting potentially as often as every 200ms. do we have a tradeoff to consider here?"

## Proposed Solution: Lazy Sorted Array Cache

Add a cached sorted array that invalidates on delta:

```typescript
interface SideBook {
  depthMap: Map<string, number>;     // Source of truth (O(1) updates)
  sortedCache: DepthTuple[] | null;  // null = dirty, needs rebuild
}

// On delta:
depthMap.set(priceStr, size);
sortedCache = null;  // Invalidate

// On emit:
if (sortedCache === null) {
  sortedCache = Array.from(depthMap.entries())
    .map(([p, s]) => [parseFloat(p), s] as DepthTuple)
    .sort((a, b) => b[0] - a[0]);
}
return sortedCache;
```

## Tradeoff Analysis

### Benefits
1. Markets with no deltas since last emit: reuse cached array (O(1))
2. Markets with deltas: one conversion (same as before)
3. Reduces redundant work during low-activity periods

### Costs
1. Additional memory: one cached array per side (4 per market)
2. Cache invalidation overhead: `sortedCache = null` per delta
3. Code complexity: must ensure cache invalidation is never missed

### When This Helps
- Many markets, few deltas per market (user's actual pattern)
- High emit frequency (WebSocket messages)
- Markets that go quiet between price changes

### When This Hurts
- Every market updates every emit cycle (cache always dirty)
- Mostly noise (no real benefit, just added complexity)

## Questions for Debate

1. **Is the complexity worth it?** The simple Map fix already provides O(1) deltas. Adding caching adds failure modes (stale cache if invalidation is missed).

2. **Alternative: Emit throttling?** Instead of caching, could we reduce emit frequency? (e.g., debounce per market)

3. **Memory tradeoff?** Each cached array is ~20-100 DepthTuples × 16 bytes = 0.3-1.6KB per side × 4 sides × 100 markets = 120-640KB total. Acceptable?

4. **Testing complexity?** How do we verify the cache is never stale? Edge cases: rapid deltas, concurrent emits, snapshot resets.

5. **Apply to Kalshi too?** Kalshi already uses Maps internally. Should we add the same caching pattern for consistency?

## Success Criteria

- No increase in emit latency p99
- Reduced CPU usage during low-activity periods
- Zero tolerance for stale cache bugs (would cause incorrect prices)