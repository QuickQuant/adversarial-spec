# Architecture Disaster Analysis: December 2025 WebSocket Order Tracking

**Date:** 2026-02-05
**Author:** Claude (analysis requested by Jason)
**Status:** Pre-debate analysis

---

## Executive Summary

Commit `0eabe10` (Dec 27, 2025) introduced a fundamentally flawed architecture for order tracking that violates the core three-process separation principle of Quarterdeck. The UI process now creates its own exchange connections and runs WebSocket listeners, duplicating AADriver's responsibilities and creating the "unclosed sessions" warnings that triggered this investigation.

---

## Timeline of Changes

| Commit | Date | Changes | Impact |
|--------|------|---------|--------|
| `cd963b9` | Dec 6, 2025 | Improved data transfer, batching, log TTL | **GOOD** - Last clean commit |
| `0eabe10` | Dec 27, 2025 | WebSocket order tracking, Redis storage, funding EMAs | **DISASTER** - Violated architecture |
| `2645455` | Dec 31, 2025 | Added Kraken exchange | Neutral - builds on 0eabe10 |
| `1e264c6` | Jan 8, 2026 | Added Results tab, logging improvements | Neutral - builds on 0eabe10 |
| `07575dd` | Recent | Shelving changes | Neutral |

---

## The Intended Architecture (from onboarding docs)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Dash GUI       │    │  AADriver        │    │  CoinRoutes WS  │
│  (Port 8050)    │◄───│  (Port 8080)     │───►│  (Port 8081)    │
│  MINIMAL LOGIC  │    │  ALL TRADING     │    │  ORDER ROUTING  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                      │
        │                      ▼
        │              ┌──────────────────┐
        │              │  Exchanges       │
        │              │  (Direct API)    │
        └─────────────►│                  │
              ❌ WRONG  └──────────────────┘
```

### Core Principles Violated:

1. **UI should have "minimal processing"** - UI now creates exchange instances
2. **AADriver handles all exchange operations** - UI now directly connects to exchanges
3. **Three-process separation for GIL avoidance** - WebSocket listeners in UI means trading and UI compete for GIL

---

## What Commit 0eabe10 Actually Did

### New Files Created:

| File | Purpose | Problem |
|------|---------|---------|
| `app/callbacks/shared_exchange_instances.py` | Exchange instances for UI | **Created at import time** - caused unclosed sessions |
| `app/services/ws_order_listeners.py` | WebSocket order tracking | **Runs in UI process** - violates separation |
| `app/services/orders_redis.py` | Redis storage for orders | **Managed by UI** - should be AADriver's job |

### Changes to Exchange Files:

Added WebSocket methods to all exchanges:
- `supports_order_websocket() -> bool`
- `start_order_websocket(on_order_update, on_fill) -> bool`
- `stop_order_websocket() -> bool`
- `is_order_websocket_connected() -> bool`

**Assessment:** The exchange methods themselves are correctly designed. The problem is WHERE they're called from (UI instead of AADriver).

### Changes to data_service:

Added funding rate EMA calculations:
- 5-hour fast EMA (half-life decay)
- 72-hour slow EMA (half-life decay)
- 96-hour rolling history buffer

**Assessment:** This is good feature work, unrelated to the architectural violation.

---

## Subsequent Fix Attempts

`shared_exchange_instances.py` was later deleted and replaced with:

**`app/services/ui_exchange_instances.py`** - Lazy initialization pattern

```python
# Good: Lazy init
def get_exchange(name: str) -> Optional[Any]:
    if _is_shutting_down:
        return None
    with _lock:
        if name not in _instances:
            instance = _create_exchange(name)  # Only created on first access
            ...
```

**Assessment:** This fixes the import-time creation bug, BUT the fundamental violation remains: UI still has its own exchange connections separate from AADriver.

---

## The Core Problem: Duplicate Exchange Connections

### Current State:

```
┌──────────────┐                  ┌──────────────┐
│  UI Process  │──────────────────│  Exchanges   │
│  (8050)      │   Connection #1  │              │
└──────────────┘                  └──────────────┘
       ▲                                 ▲
       │                                 │
       │         ┌──────────────┐        │
       │         │  AADriver    │────────┘
       │         │  (8080)      │   Connection #2
       │         └──────────────┘
       │                │
       └────────────────┘
         Fetches data
```

**Problems:**
1. Two separate connections to each exchange (double API usage)
2. UI and AADriver have different views of orders
3. Race conditions possible between UI WebSocket and AADriver REST
4. "Unclosed sessions" when UI shuts down before exchanges cleanup

### Correct Architecture:

```
┌──────────────┐
│  UI Process  │──────────────────┐
│  (8050)      │   REST only      │
└──────────────┘                  │
                                  ▼
                          ┌──────────────┐
                          │  AADriver    │──────────────►│  Exchanges   │
                          │  (8080)      │   SINGLE      │              │
                          │  /get_orders │   CONNECTION  └──────────────┘
                          │  /get_fills  │
                          └──────────────┘
```

---

## Code Assessment: What Can Be Salvaged

### SALVAGEABLE (good code, wrong location):

| File | What's Good | Required Change |
|------|-------------|-----------------|
| `orders_redis.py` | Well-designed Redis storage, proper schema | Move to AADriver domain, or share |
| `ws_order_listeners.py` | Good WebSocket management, health monitoring | Move to AADriver process |
| Exchange WebSocket methods | Correct interface design | Keep - just call from AADriver |
| Funding EMA calculations | Valuable feature | Keep as-is in data_service |

### SALVAGEABLE (from later commits):

| Commit | Feature | Assessment |
|--------|---------|------------|
| `2645455` | Kraken exchange | Keep - clean exchange implementation |
| `1e264c6` | Results tab | Keep - UI-only feature |

### MUST DISCARD:

| File/Pattern | Why |
|--------------|-----|
| `ui_exchange_instances.py` | UI should not create exchange instances at all |
| UI calling `get_active_orders()` directly on exchanges | Should call AADriver endpoint |
| UI running WebSocket listeners | Should be in AADriver |

---

## Decision Options

### Option A: Minimal Fix (Quick)

Keep current structure, add AADriver endpoints:
1. Add `/get_active_orders` endpoint to AADriver
2. Add `/get_fills` endpoint to AADriver
3. Modify UI to call AADriver instead of direct exchange access
4. Keep Redis in current location (UI-accessible)
5. Delete `ui_exchange_instances.py`

**Pros:** Least code change
**Cons:** WebSocket listeners still in UI (GIL contention), dual Redis access

### Option B: Fork from cd963b9 (Clean Slate)

1. Fork from `cd963b9` (last clean commit)
2. Cherry-pick Kraken exchange from `2645455`
3. Cherry-pick Results tab from `1e264c6`
4. Re-implement order tracking correctly in AADriver:
   - Move `orders_redis.py` to `SORManager/`
   - Move `ws_order_listeners.py` to `SORManager/`
   - Add AADriver endpoints for UI to consume
5. Cherry-pick funding EMA code from `0eabe10`

**Pros:** Clean architecture, no legacy violations
**Cons:** More work, risk of losing other small fixes

### Option C: Move Components (Surgical)

1. Keep current HEAD
2. Move `ws_order_listeners.py` to `SORManager/`
3. Move `orders_redis.py` to `SORManager/` (or keep shared)
4. Add AADriver endpoints
5. Delete `ui_exchange_instances.py`
6. Modify UI to fetch from AADriver only

**Pros:** Preserves all features, systematic refactor
**Cons:** Risk of missing hidden dependencies

---

## Missing AADriver Endpoints

AADriver currently has NO endpoints for:
- `/get_active_orders` - Get open orders across exchanges
- `/get_fills` or `/get_recent_fills` - Get filled orders
- `/get_orders_status` - Get WebSocket health status

These MUST be added for any correct architecture.

---

## Recommendation

**Option C (Move Components)** is recommended because:

1. All features are preserved (Kraken, Results tab, funding EMAs)
2. The code in `orders_redis.py` and `ws_order_listeners.py` is well-designed
3. Only the LOCATION is wrong, not the implementation
4. Systematic approach reduces risk of missing hidden dependencies

However, if time is critical or debugging becomes too complex, **Option B (Fork)** provides a clean slate with known-good architecture.

---

## Files to Review in Debate

1. `app/services/ui_exchange_instances.py` - Delete or keep?
2. `app/services/ws_order_listeners.py` - Move to AADriver?
3. `app/services/orders_redis.py` - Keep in app/services or move?
4. `app/callbacks/Orders_helper_functions.py` - Refactor to call AADriver?
5. `SORManager/AADriver.py` - What endpoints to add?

---

## Next Steps

1. Run adversarial spec debate on this analysis
2. Get consensus on Option A, B, or C
3. Create execution plan based on chosen option
4. Implement fix with proper testing