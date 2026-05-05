# Error Handling & Robustness

Comprehensive guide to error handling, fallback behavior, and resilience in agent-system.

## Design Philosophy

Agent-system is designed with **fail-safe defaults**: when services are unavailable or timeouts occur, the system returns safe default values rather than raising exceptions. This allows game development to continue even when external services fail.

### Principles

1. **Never raise in user-facing methods** — All public APIs return safe defaults
2. **Log warnings** — Failures are logged for debugging but don't stop execution
3. **Async fallback** — Long operations fallback to non-blocking async when needed
4. **Graceful degradation** — System works without external services, just with reduced capability

---

## AKC Service Unavailability

When the AKC HTTP service is down, the system gracefully degrades.

### How It Works

```python
from agent_system.akc_http_client import AKCClient

client = AKCClient(base_url="http://localhost:8000", timeout_sec=0.15)

# If service is down, these return safe defaults (never raise)
patterns = client.query_patterns("task", "entity", "component")  # Returns []
stats = client.get_stats()                                       # Returns {}
result = client.record_outcome({"task_id": "t1"})                # Returns {}
available = client.is_available()                                # Returns False
```

### Safe Defaults by Method

| Method | Returns | On Error |
|---|---|---|
| `is_available()` | `bool` | `False` (service down) |
| `query_patterns()` | `list[dict]` | `[]` (no patterns) |
| `record_outcome()` | `dict` | `{}` (empty response) |
| `get_stats()` | `dict` | `{}` (no stats) |

### Handling Service Down

```python
from agent_system.akc_http_client import AKCClient

def execute_task_safely(task_id: str) -> dict:
    """Execute task with graceful fallback."""
    
    client = AKCClient()
    
    # Check service availability (50ms timeout)
    if client.is_available():
        # Service is up — use patterns
        patterns = client.query_patterns(task_id, "player", "health")
        use_patterns = True
    else:
        # Service is down — continue without patterns
        patterns = []
        use_patterns = False
    
    # Execute agent (works either way)
    print(f"Executing task: patterns_available={use_patterns}")
    
    agent_result = execute_agent(task_id, patterns)
    
    return {
        "task_id": task_id,
        "result": agent_result,
        "patterns_used": use_patterns,
        "fallback": not use_patterns
    }
```

---

## HTTP Timeout Handling

All HTTP operations have short, non-blocking timeouts to prevent hangs.

### Timeout Values

| Operation | Timeout | Purpose |
|---|---|---|
| Health check | 50ms | Quick availability check |
| Pattern query | 150ms | Pattern retrieval (high tolerance) |
| Outcome recording | 150ms | Result submission (high tolerance) |
| Statistics | 150ms | Metrics retrieval (high tolerance) |

### Why Short Timeouts?

- **Agent deadline**: Claude tasks have timeout constraints (30-120s)
- **Prevent cascade failures**: Long waits cause upstream timeouts
- **Quick fallback**: Detect failures early and switch to defaults
- **Non-blocking**: Fast feedback for agent execution

### Timeout Behavior

```python
from agent_system.akc_http_client import AKCClient
import requests

client = AKCClient()

# If service is slow:
patterns = client.query_patterns("task", "entity", "component")

# What happens:
# 1. Request sent with 150ms timeout
# 2. If service doesn't respond by 150ms: catch timeout, return []
# 3. Agent continues with empty pattern list
# 4. No exception raised, no agent hangs
```

### Handling Timeout Errors

```python
from agent_system.akc_http_client import AKCClient
import logging

logger = logging.getLogger(__name__)

client = AKCClient()

# Timeouts are logged but don't propagate
patterns = client.query_patterns("task", "entity", "component")

# If timeout occurred, logger has a warning (check logs):
# WARNING:agent_system.akc_http_client:AKC query timeout for task task
```

---

## Configuration Validation Errors

The `load_config()` function validates all configuration and raises `ConfigValidationError` on failure.

### Validation Rules

| Field | Valid | Invalid |
|---|---|---|
| `model` | `claude-opus-4-7` | `gpt-4` (not claude-*) |
| `timeout` | `30` | `-1` (not positive) |
| `max_retries` | `3` | `11` (> 10) |
| `safety_level` | `0, 1, 2` | `3` (invalid) |
| `akc_url` | Any string | (no validation) |

### Handling Validation Errors

```python
from agent_system import load_config, ConfigValidationError

try:
    config = load_config()
except ConfigValidationError as e:
    print(f"Configuration error: {e}")
    # Handle gracefully:
    # 1. Use defaults
    # 2. Prompt user to fix .env
    # 3. Exit with clear error message
```

### Safe Config Loading

```python
from agent_system import load_config, ConfigValidationError, AgentConfig

def load_config_safe() -> AgentConfig:
    """Load config with fallback to defaults."""
    
    try:
        return load_config()
    except ConfigValidationError as e:
        print(f"Config validation failed: {e}")
        print(f"Using default config:")
        
        # Return defaults
        return AgentConfig(
            model="claude-opus-4-7",
            timeout=30,
            max_retries=3,
            safety_level=1,
            akc_url="http://localhost:8000"
        )
```

### Common Validation Failures

**Problem: Invalid model name**
```python
# .env: AGENT_SYSTEM_MODEL=gpt-4
# Error: "model must match claude-* pattern"
# Fix: Use Claude model (claude-opus-4-7, claude-haiku-4-5-20251001, etc.)
```

**Problem: Negative timeout**
```python
# .env: AGENT_SYSTEM_TIMEOUT=-1
# Error: "timeout must be positive integer"
# Fix: Use positive value (30, 60, 120, etc.)
```

**Problem: Invalid safety level**
```python
# .env: AKC_SERVICE_SAFETY_LEVEL=5
# Error: "safety_level must be 0, 1, or 2"
# Fix: Use 0 (permissive), 1 (standard), or 2 (strict)
```

---

## Task Validation Errors

The `validate_task_result()` function checks that task results conform to the required schema.

### Required Fields

```python
from agent_system import validate_task_result

# Valid task result
task_result = {
    "schema_version": "1.0",
    "task_id": "task-001",
    "status": "success",  # or "failed"
    "timestamp": "2026-05-05T10:30:00Z",
    "akc_context": {
        "akc_enabled": True,
        "knowledge_patterns_active": ["pat-001"],
        "confidence_scores": {"pat-001": 0.85},
        "pattern_outcomes": {"pat-001": {"used": True, "success": True}}
    }
}

# Validate
if validate_task_result(task_result):
    print("Task result is valid")
else:
    print("Task result is missing required fields")
```

### Validation Failures

```python
from agent_system import validate_task_result, build_task_result

# Example 1: Invalid status
result = {
    "schema_version": "1.0",
    "task_id": "task-001",
    "status": "running",  # INVALID: must be "success" or "failed"
    "timestamp": "2026-05-05T10:30:00Z",
    "akc_context": {}
}
assert not validate_task_result(result)  # False

# Example 2: Missing akc_context
result = {
    "schema_version": "1.0",
    "task_id": "task-001",
    "status": "success",
    "timestamp": "2026-05-05T10:30:00Z"
    # MISSING: akc_context
}
assert not validate_task_result(result)  # False

# Example 3: Using build_task_result ensures validity
result = build_task_result(
    task_id="task-001",
    status="success",
    active_patterns=["pat-001"],
    akc_enabled=True
)
assert validate_task_result(result)  # True
```

---

## Learning Integration Timeouts

The `call_learning_with_timeout()` function handles learning with timeouts and async fallback.

### Timeout Behavior

```python
from agent_system import call_learning_with_timeout, build_task_result

task_result = build_task_result(
    task_id="task-001",
    status="success"
)

# Call learning with 30s timeout
learning_result = call_learning_with_timeout(
    task_result,
    timeout_sec=30
)

# Possible results:
# 1. Sync success:
#    {"status": "sync_complete", "patterns_updated": 2}
#
# 2. Timeout (falls back to async):
#    {"status": "timeout_fallback_async", "pid": 12345}
#
# 3. Error (falls back to async):
#    {"status": "error_fallback_async", "error": "...", "pid": 12345}
#
# NOTE: call_learning_with_timeout() NEVER raises — always returns a dict
```

### Handling Learning Failures

```python
from agent_system import call_learning_with_timeout, build_task_result

task_result = build_task_result(task_id="task-001", status="success")

# Call learning (always succeeds, may use fallback)
learning_result = call_learning_with_timeout(task_result)

# Check status
if learning_result["status"] == "sync_complete":
    # Learning succeeded synchronously
    print(f"Updated {learning_result['patterns_updated']} patterns")
elif "fallback_async" in learning_result["status"]:
    # Learning fell back to async (due to timeout or error)
    pid = learning_result.get("pid")
    print(f"Learning delegated to async process (PID {pid})")
else:
    # Unexpected status
    print(f"Unexpected learning status: {learning_result}")
```

---

## Concurrent Agent Execution

When multiple agents run concurrently, thread safety is important.

### Thread-Safe Patterns

```python
import concurrent.futures
from agent_system.akc_http_client import AKCClient

def execute_agents_concurrently(tasks: list) -> dict:
    """Execute multiple agent tasks concurrently with safety."""
    
    # AKCClient uses requests.Session which is thread-safe
    client = AKCClient()
    
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        
        for task_id, task_desc in tasks:
            # Submit each task
            future = executor.submit(
                execute_agent_task,
                task_id=task_id,
                task_desc=task_desc,
                client=client  # Thread-safe client
            )
            futures[future] = task_id
        
        # Collect results
        for future in concurrent.futures.as_completed(futures):
            task_id = futures[future]
            try:
                result = future.result()
                results[task_id] = result
            except Exception as e:
                results[task_id] = {"error": str(e)}
    
    return results


def execute_agent_task(task_id: str, task_desc: str, client: AKCClient) -> dict:
    """Execute single agent task (thread-safe)."""
    
    # Query patterns (thread-safe)
    patterns = client.query_patterns(task_id, "entity", "component")
    
    # Execute agent
    agent_result = execute_agent(task_id, task_desc, patterns)
    
    # Record outcome (thread-safe)
    client.record_outcome({
        "task_id": task_id,
        "status": agent_result["status"]
    })
    
    return agent_result
```

### Subprocess Safety

```python
import subprocess
import json
from agent_system import build_task_result

def spawn_learning_subprocess(task_result: dict) -> int:
    """Spawn learning subprocess (safe for concurrent calls)."""
    
    # Each call creates a separate subprocess (no shared state)
    proc = subprocess.Popen(
        ["python3", "-c", "from agent_system import call_learning_with_timeout; ..."],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Send task result and return immediately (non-blocking)
    try:
        proc.stdin.write(json.dumps(task_result).encode())
        proc.stdin.close()
    except BrokenPipeError:
        pass  # Process already exited
    
    return proc.pid
```

---

## Logging and Debugging

### Enable Debug Logging

```python
import logging

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s %(message)s'
)

# Enable debug logging for agent-system
logging.getLogger("agent_system").setLevel(logging.DEBUG)

# Now all operations are logged
from agent_system.akc_http_client import AKCClient

client = AKCClient()
patterns = client.query_patterns("task", "entity", "component")

# Logs:
# DEBUG:agent_system.akc_http_client:AKC query latency: 42ms
```

### Logging Levels

| Level | When | Example |
|---|---|---|
| DEBUG | Detailed operation info | `AKC query latency: 42ms` |
| INFO | General operations | `trigger_learning_delta: task=t1, patterns=2` |
| WARNING | Issues but continuing | `AKC query timeout for task task` |
| ERROR | Errors but continuing | `Config validation failed` |
| CRITICAL | System integrity issues | `[CR-05] KB update lost` |

### Learning Integration Logs

The learning integration system logs critical issues with `[CR-XX]` codes:

| Code | Issue | Action |
|---|---|---|
| `[CR-05]` | KB update lost | Learning subprocess failed to spawn |

Monitor logs for these codes to detect KB consistency issues.

---

## Recovering from Common Failures

### Failure: AKC Service Slow

**Symptom:** Queries take >150ms

**Recovery:**
1. Check service health: `client.is_available()`
2. Verify network latency: `ping akc-service-host`
3. Check service logs for bottlenecks
4. System gracefully uses fallback (returns [])

### Failure: Config Not Loading

**Symptom:** `ConfigValidationError` raised

**Recovery:**
1. Check .env file exists: `ls -la .env`
2. Verify syntax: `cat .env`
3. Check for invalid values:
   - Model must start with `claude-`
   - Timeout must be positive integer
   - Safety level must be 0, 1, or 2
4. Reload: `python -c "from agent_system import load_config; load_config()"`

### Failure: Learning Integration Timeout

**Symptom:** `call_learning_with_timeout()` returns fallback_async

**Recovery:**
1. Check KB size: may be too large for sync update
2. Monitor async processes: `ps aux | grep learning`
3. Check logs: `cat agent_system/logs/learning_integration.log`
4. System automatically falls back to async (safe)

### Failure: Skill Execution Timeout

**Symptom:** Skill returns timeout status

**Recovery:**
1. Check environment: editor running? paths correct?
2. Verify skill has access to required resources
3. Increase timeout in configuration (if possible)
4. Check skill logs for actual error

---

## Testing Error Scenarios

### Unit Testing Error Cases

```python
import unittest
from unittest.mock import patch
from agent_system.akc_http_client import AKCClient
from agent_system import load_config, ConfigValidationError

class TestErrorHandling(unittest.TestCase):
    
    @patch("agent_system.akc_http_client.requests.Session.post")
    def test_query_timeout_returns_empty_list(self, mock_post):
        """Test that timeout returns safe default."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        client = AKCClient()
        result = client.query_patterns("task", "entity", "component")
        
        self.assertEqual(result, [])  # Safe default
    
    @patch.dict(os.environ, {"AGENT_SYSTEM_TIMEOUT": "-1"})
    def test_negative_timeout_raises(self):
        """Test that invalid config raises ConfigValidationError."""
        
        with self.assertRaises(ConfigValidationError):
            load_config()
    
    def test_validate_task_result_missing_fields(self):
        """Test task validation catches missing fields."""
        from agent_system import validate_task_result
        
        # Missing akc_context
        result = {
            "schema_version": "1.0",
            "task_id": "t1",
            "status": "success",
            "timestamp": "2026-05-05T10:30:00Z"
        }
        
        self.assertFalse(validate_task_result(result))
```

---

## See Also

- [CAPABILITIES.md](CAPABILITIES.md) — Agent and skill system overview
- [CONFIGURATION.md](CONFIGURATION.md) — Configuration and environment setup
- [GODOT_INTEGRATION.md](GODOT_INTEGRATION.md) — Integration into Godot projects
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common issues and solutions
