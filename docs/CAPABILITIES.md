# Agent-System Capabilities

Comprehensive reference for the agent-system package's specialized agents, skill system, and learning integration.

## Overview

The agent-system package provides a portable Claude agent coordination system designed for Godot game development. It orchestrates 4 specialized agents with enforced skill verification gates and structured task handoffs.

**What's built-in:**
- 4 domain-specialized agents (Orchestrator, MCP, Script, QC)
- Skill verification gates (pre/post execution validation)
- Structured task handoff schema
- Per-agent model routing
- Graceful degradation defaults

**What's optional (external):**
- AKC HTTP service — remote pattern-driven learning via REST API. Not required.

**What's local and wired:**
- `learning_integration.py` — updates `kb/patterns.jsonl` after each QC-approved task via the `record-task-outcome` skill. Runs locally with no external service needed. Activated when the Orchestrator invokes `record-task-outcome` after QC passes.

**To activate:** `pip install -e packages/agent-system` from the project root.

## 4 Specialized Agents

### 1. Orchestrator Agent

**Role:** Task decomposition and routing

- Receives high-level game development requests
- Decomposes tasks into scene work (MCP) and script work
- Routes to specialized agents (MCP Agent, Script Agent, QC Agent)
- Controls concurrent agent execution and task prioritization
- Manages orchestrator_hooks for AKC learning integration (when enabled)
- Decides pattern recommendation strategy based on KB maturity (when AKC available)

**Key Responsibilities:**
- Scene architecture planning
- Agent task handoff and dependency management
- Learning delta triggering via `trigger_learning_delta()`
- Gold-tier pattern preferential routing when KB is mature

**Environment:** Claude API (claude-opus-4-7 by default)

**Related Modules:**
- `agent_system/agents/orchestrator/prompt.md` — system prompt
- `agent_system/orchestrator_hooks.py` — learning integration entry point

### 2. MCP Agent

**Role:** Scene and node creation

- Creates and configures Godot scenes (`.tscn` files)
- Manages node hierarchy and properties
- Implements physics layers, collision setup
- Creates animations and visual components
- Uses godot-ai MCP server for editor access

**Key Responsibilities:**
- Scene composition and structure
- Node property configuration
- Visual component implementation
- Physics and collision setup
- Animation orchestration

**Capabilities:**
- `scene_get_hierarchy()` — inspect scene tree
- `node_create()` — create new nodes
- `node_set_property()` — configure properties
- `script_create()` — add scripts to nodes
- `project_run()` — test scenes

**Related Modules:**
- `agent_system/agents/mcp/prompt.md` — system prompt
- `agent_system/agents/mcp/model/haiku-4.5.md` — model-specific guidelines

### 3. Script Agent

**Role:** GDScript logic implementation

- Writes GDScript source code
- Implements game mechanics (movement, combat, AI)
- Integrates with orchestrator_hooks for learning
- Validates script compilation
- Uses task_result builder for learning integration

**Key Responsibilities:**
- Gameplay logic implementation
- Signal and callback handling
- Performance-critical code
- Pattern application from KB
- Learning integration compliance

**Capabilities:**
- Write GDScript with proper structure
- Use patterns from AKC service
- Build task_result for learning
- Handle fallback when akc-service unavailable
- Integrate with Godot's type system

**Related Modules:**
- `agent_system/agents/script/prompt.md` — system prompt
- `agent_system/agent_learning_utils.py` — task result builder

### 4. QC/Architecture Agent

**Role:** Quality assurance and consistency validation

- Validates scene architecture correctness
- Checks physics layer assignments
- Verifies naming conventions
- Ensures learning integration compliance
- Validates task_result structure

**Key Responsibilities:**
- Architecture review
- Naming convention enforcement
- Physics layer registry validation
- Collision setup correctness
- Script compilation checks
- Learning result validation

**Validation Points:**
- Scene hierarchy structure
- Node type appropriateness
- Physics layer consistency (res://constants/PhysicsLayers.gd)
- Skill execution results
- Task result schema compliance (LEARN-01/02/06)

**Related Modules:**
- `agent_system/agents/qc/prompt.md` — system prompt
- `agent_system/agent_learning_utils.py` — validation utilities

---

## Skill System

4 Godot-specific skills live in `.claude/skills/` (tracked in git). All inherit from `godot-task-verify` base.

### Base: godot-task-verify

Provides common verification discipline for all agent tasks:
- Pre-execution checks (environment readiness)
- Post-execution validation (success criteria)
- Error detection and reporting
- Logging and diagnostics

### 1. godot-mcp-task

**Used by:** MCP Agent

**Lifecycle:**
- **Before execution:** Verify Godot editor is accessible via godot-ai MCP server
- **During:** Enable MCP tool logging
- **After:** Validate scene was created with correct structure

**Checks:**
- Editor connectivity
- MCP server health
- Scene file existence and validity
- Node hierarchy matches specification
- No unresolved node references

**Returns:**
- Success/failure status
- Scene path
- Node count
- Validation warnings

### 2. godot-script-task

**Used by:** Script Agent

**Lifecycle:**
- **Before execution:** Verify Godot project structure and script directories exist
- **During:** Enable script compilation checks
- **After:** Validate script syntax and runtime behavior

**Checks:**
- Script file creation
- GDScript syntax validity (parse errors)
- Class inheritance correctness
- Method signature compliance
- No undefined references
- Learning integration compliance (task_result presence)

**Returns:**
- Compilation status
- Script path
- Lines of code
- Integration status

### 3. godot-orchestrator-gate

**Used by:** Orchestrator

**Lifecycle:**
- **Before dispatch:** Validate task decomposition
- **Before accepting results:** Verify all subagent results meet quality criteria

**Checks:**
- Task structure validity
- MCP Agent results (scene integrity)
- Script Agent results (code quality, learning compliance)
- QC Agent validation results
- Concurrent execution safety

**Returns:**
- Dispatch approval/rejection
- Result acceptance/rejection
- Blocking issues list

---

## Feature Matrix

| Capability | Orchestrator | MCP Agent | Script Agent | QC Agent | Skills |
|---|---|---|---|---|---|
| Task decomposition | ✓ | | | | |
| Scene creation | | ✓ | | | ✓ |
| GDScript writing | | | ✓ | | ✓ |
| Learning integration | ✓ | | ✓ | ✓ | ✓ |
| Architecture validation | | | | ✓ | ✓ |
| Pattern queries (AKC) | | ✓ | ✓ | | |
| Outcome recording | ✓ | | | ✓ | |
| Scene verification | | | | ✓ | ✓ |
| Script verification | | | ✓ | ✓ | ✓ |
| Health checks | ✓ | | | | |
| Fallback behavior | ✓ | ✓ | ✓ | | |

---

## AKC HTTP Client

The `AKCClient` class provides safe, timeout-protected communication with the AKC service.

### Methods

| Method | Timeout | Returns | Safe Fallback |
|---|---|---|---|
| `is_available()` | 50ms | `bool` | `False` |
| `query_patterns()` | 150ms | `list[dict]` | `[]` |
| `record_outcome()` | 150ms | `dict` | `{}` |
| `get_stats()` | 150ms | `dict` | `{}` |

### Key Characteristics

- **Non-blocking:** All timeouts return safe defaults, never raise
- **Health check:** 50ms HEAD request to `/akc/v1/health`
- **Pattern queries:** POST to `/akc/v1/query` with task_id, entity, component
- **Outcome recording:** POST to `/akc/v1/record` with full task_result
- **Statistics:** GET to `/akc/v1/stats` for KB metrics
- **Latency tracking:** Extracts `X-AKC-Query-Latency-Ms` header when present

### Usage Example

```python
from agent_system.akc_http_client import AKCClient

# Create client (defaults to localhost:8000)
client = AKCClient(base_url="http://localhost:8000", timeout_sec=0.15)

# Check availability
if client.is_available():
    # Query patterns for a component
    patterns = client.query_patterns(
        task_id="task-001",
        entity="player",
        component="HealthComponent"
    )
    
    # Record task outcome after agent completes
    result = client.record_outcome({
        "task_id": "task-001",
        "status": "success",
        "timestamp": "2026-05-05T10:30:00Z",
        "akc_context": {
            "akc_enabled": True,
            "knowledge_patterns_active": ["pat-001"],
            "pattern_outcomes": {"pat-001": {"used": True, "success": True}}
        }
    })
else:
    # Service unavailable — use fallback defaults
    patterns = []
```

---

## Learning Integration

All agents integrate with the learning system to record task outcomes and update the knowledge base.

### Task Result Schema

Every agent (Orchestrator, MCP, Script, QC) MUST call `call_learning_with_timeout()` after task completion per LEARN-01/02/06.

```python
from agent_system import build_task_result, call_learning_with_timeout

# Build result with pattern outcomes
result = build_task_result(
    task_id="task-001",
    status="success",  # "success" or "failed"
    active_patterns=["player_health_001", "player_movement_002"],
    confidence_scores={
        "player_health_001": 0.85,
        "player_movement_002": 0.72
    },
    pattern_outcomes={
        "player_health_001": {"used": True, "success": True},
        "player_movement_002": {"used": False, "success": None}
    },
    akc_enabled=True
)

# Call learning with timeout and async fallback
learning_result = call_learning_with_timeout(result, timeout_sec=30)
# Returns: {"status": "success"} or 
#          {"status": "timeout_fallback_async", "pid": 12345} or
#          {"status": "error_fallback_async", "error": "...", "pid": 12345}
```

### Learning Flow (AKC-Primary with Fallback)

When `AKC_ENABLED=true`, the flow is:

1. **AKC Primary:** Check `akc.is_available()` (50ms health check)
   - If available → call `akc.record_outcome()` to HTTP endpoint
   - If unavailable → fall through to local JSONL path
2. **Local Fallback:** Update patterns.jsonl via subprocess
   - Hybrid sync/async logic for critical patterns
   - Async by default (non-blocking)
   - Sync for patterns with confidence < 0.50 (safety)
   - Sync timeout >30s falls back to async

When `AKC_ENABLED=false`, skip all learning calls immediately (no subprocess, no HTTP).

```python
from agent_system import build_task_result, call_learning_with_timeout

# All agents call this after task completion
result = build_task_result("task-001", "success", active_patterns=["p1"], akc_enabled=True)
learning_result = call_learning_with_timeout(result, timeout_sec=30)

# Returns:
# - If AKC up: {"status": "akc_recorded", "accepted": True, ...}
# - If AKC down: {"status": "async_spawned", "pid": 12345, ...} (local fallback)
# - If AKC disabled: {"status": "skipped", "reason": "AKC disabled"}
```

### Outcome Validation

```python
from agent_system import validate_task_result

# Validate before recording
if validate_task_result(result):
    # Safe to record
    client.record_outcome(result)
else:
    # Missing required fields
    logger.error("Invalid task result")
```

---

## Configuration

The `AgentConfig` class loads configuration from environment variables with `.env` file fallback.

### Fields

| Field | Env Var | Default | Validation |
|---|---|---|---|
| `model` | `AGENT_SYSTEM_MODEL` | `claude-opus-4-7` | Must match `claude-*` pattern |
| `timeout` | `AGENT_SYSTEM_TIMEOUT` | `30` | Positive integer |
| `max_retries` | `AGENT_SYSTEM_MAX_RETRIES` | `3` | 0-10 range |
| `safety_level` | `AKC_SERVICE_SAFETY_LEVEL` | `1` | 0, 1, or 2 |
| `akc_url` | `AKC_SERVICE_URL` | `http://localhost:8000` | Valid URL |

### Usage

```python
from agent_system import load_config, ConfigValidationError

try:
    config = load_config()
    # config.model, config.timeout, config.max_retries, etc.
except ConfigValidationError as e:
    print(f"Config error: {e}")
```

---

## Orchestrator Lifecycle Hooks

The `orchestrator_hooks.py` module provides integration points for learning loop updates. When `AKC_ENABLED=true`, calls route to the AKC service as the primary backend; when AKC is unavailable or disabled, the local JSONL fallback activates transparently.

### Key Functions

| Function | Purpose | AKC Path | Fallback | Returns |
|---|---|---|---|---|
| `trigger_learning_delta()` | Trigger KB update after task completion | `akc.record_outcome()` POST `/akc/v1/record` | local file write | dict with status, patterns_to_update, blocking flag |
| `get_active_patterns(entity, component, task_id="")` | Query KB for patterns matching entity:component | `akc.query_patterns()` POST `/akc/v1/query` | load local patterns.jsonl | list of {id, confidence, tier} |
| `load_pattern()` | Load specific pattern from patterns.jsonl by ID | — | patterns.jsonl scan | dict or None |
| `should_use_gold_tier_preferentially()` | Decide if KB is mature (>5 gold patterns, avg conf >0.75) | `akc.get_stats()` GET `/akc/v1/stats` | scan patterns.jsonl | bool |

**New in latest release:** `get_active_patterns()` now accepts optional `task_id` parameter (used by AKC endpoint for richer pattern matching). Local JSONL path ignores it. Default value `""` maintains backward compatibility.

### Pattern Confidence Tiers

| Tier | Confidence Range | Behavior |
|---|---|---|
| `gold` | >= 0.85 | High confidence, prefer for recommendations |
| `production` | 0.70-0.84 | Ready for production use |
| `experimental` | 0.50-0.69 | New patterns, use with caution |
| `demoted` | < 0.50 | Low confidence, trigger sync KB updates |

---

## Fallback & Robustness

The system is designed to gracefully degrade when akc-service is unavailable.

### AKC Service Down

- `is_available()` returns `False` (50ms timeout)
- `query_patterns()` returns `[]` (safe empty list)
- `record_outcome()` returns `{}` (safe empty dict)
- Agents continue with fallback defaults
- Learning integration uses async fallback (non-blocking)

### HTTP Timeouts

All HTTP methods have short timeouts (50-150ms) to prevent agent hangs:
- Health check: 50ms
- Pattern query: 150ms
- Outcome recording: 150ms
- Stats request: 150ms

### Config Loading Failures

If config validation fails, `load_config()` raises `ConfigValidationError`:
- Invalid model name (not `claude-*` pattern)
- Non-positive timeout value
- Out-of-range retries (>10)
- Invalid safety level (not 0, 1, or 2)

---

## See Also

- [CONFIGURATION.md](CONFIGURATION.md) — Environment setup and defaults
- [GODOT_INTEGRATION.md](GODOT_INTEGRATION.md) — Using in Godot projects
- [ERROR_HANDLING.md](ERROR_HANDLING.md) — Robustness patterns
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common issues
