# AKC Service Wiring Design

**Date:** 2026-05-05  
**Scope:** Wire `AKC_ENABLED=true` path so agent-system routes to AKC service, with local JSONL as fallback.

---

## Problem

`AKCClient` and `config.akc_enabled` exist but are never used. All three learning functions always take the local JSONL path regardless of `AKC_ENABLED`.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend strategy | AKC-primary, local fallback only | Single source of truth; local JSONL only used when AKC is down |
| Routing placement | Inline in existing functions | No new files; minimal diff |
| Availability check | Live `is_available()` per call | Always accurate; 50ms overhead acceptable |

---

## What Changes

### 1. `AKCClient` — fix endpoint mismatches

Current hardcoded paths don't match the actual AKC service routes:

| `AKCClient` method | Current path | Correct path |
|---|---|---|
| `is_available()` | `HEAD /akc/v1/health` | `HEAD /health` |
| `query_patterns()` | `POST /akc/v1/query` | `POST /guidance` |
| `record_outcome()` | `POST /akc/v1/record` | `POST /outcomes` |
| `get_stats()` | `GET /akc/v1/stats` | `GET /stats` |

### 2. `agent_learning_utils.py` — module-level singleton + routing in `call_learning_with_timeout()`

Add at module level:
```python
from agent_system.config import load_config
from agent_system.akc_http_client import AKCClient

_config = load_config()
_akc = AKCClient(base_url=_config.akc_url)
```

Routing logic in `call_learning_with_timeout()`:
```python
if _config.akc_enabled and _akc.is_available():
    result = _akc.record_outcome(task_result)
    if result:
        return {"status": "akc_recorded", **result}
    # fall through if AKC returned empty
# existing local path unchanged
```

### 3. `orchestrator_hooks.py` — module-level singleton + routing in two functions

Add at module level (same pattern as above).

**`get_active_patterns(entity, component)`** — add `task_id` parameter (new, required by `query_patterns`):
```python
def get_active_patterns(entity: str, component: str, task_id: str = "") -> list:
    if _config.akc_enabled and _akc.is_available():
        raw = _akc.query_patterns(task_id, entity, component)
        if raw:
            return [
                {"id": p["id"], "confidence": p.get("confidence", 0.5), "tier": p.get("tier", "production")}
                for p in raw
            ]
        # fall through if empty
    # existing local JSONL path unchanged
```

**`should_use_gold_tier_preferentially()`**:
```python
if _config.akc_enabled and _akc.is_available():
    stats = _akc.get_stats()
    if stats:
        gold_count = stats.get("high_confidence_count", 0)
        avg_confidence = stats.get("average_confidence", 0.0)
        return gold_count > 5 and avg_confidence > 0.75
    # fall through if empty
# existing local scan unchanged
```

---

## Response Normalization

| AKC call | Local return shape | Normalized to |
|---|---|---|
| `record_outcome()` | varies | `{"status": "akc_recorded", ...rest}` |
| `query_patterns()` | varies | `[{"id", "confidence", "tier"}]` — same as local |
| `get_stats()` | `{"high_confidence_count", "average_confidence", ...}` | same `bool` as local |

---

## Testing

**`tests/test_learning_integration.py`** — 3 new cases:
- `test_akc_enabled_routes_to_akc` — `is_available=True`, `record_outcome` returns non-empty → local path NOT called
- `test_akc_down_falls_back_to_local` — `is_available=False` → local path runs
- `test_akc_returns_empty_falls_back_to_local` — `is_available=True`, `record_outcome` returns `{}` → local path runs

**`tests/test_orchestrator_hooks.py`** — 4 new cases:
- `test_get_active_patterns_akc_path` — `is_available=True`, `query_patterns` returns patterns → normalized shape
- `test_get_active_patterns_fallback` — `is_available=False` → local JSONL
- `test_gold_tier_akc_path` — `get_stats` returns high count → correct bool
- `test_gold_tier_fallback` — `is_available=False` → local scan

All AKC calls mocked. No live service required.

---

## Files Modified

| File | Change |
|---|---|
| `agent_system/akc_http_client.py` | Fix 4 endpoint paths |
| `agent_system/agent_learning_utils.py` | Add singleton, routing in `call_learning_with_timeout()` |
| `agent_system/orchestrator_hooks.py` | Add singleton, routing in `get_active_patterns()` and `should_use_gold_tier_preferentially()`; add `task_id` param to `get_active_patterns()` |
| `tests/test_learning_integration.py` | 3 new test cases |
| `tests/test_orchestrator_hooks.py` | 4 new test cases |

**No new files.**
