# agent-system

Portable Claude agent coordination system. Orchestrates 4 specialized agents
(Orchestrator, MCP, Script, QC) with a skill system and AKC HTTP client.

## Quick Start

### 1. Installation

```bash
pip install -e .
```

### 2. Configuration

Create `.env` file:
```env
AGENT_SYSTEM_MODEL=claude-opus-4-7
AGENT_SYSTEM_TIMEOUT=30
AGENT_SYSTEM_MAX_RETRIES=3
AKC_SERVICE_SAFETY_LEVEL=1
AKC_SERVICE_URL=http://localhost:8000
```

### 3. Usage

```python
from agent_system.akc_http_client import AKCClient

client = AKCClient(base_url="http://localhost:8000")
if client.is_available():
    patterns = client.query_patterns(task_id="my-task", entity="player", component="health")
```

## Documentation

Comprehensive guides for every aspect of agent-system:

| Document | Purpose |
|----------|---------|
| **[CAPABILITIES.md](docs/CAPABILITIES.md)** | 4 agents, skill system, AKC client, learning integration, feature matrix |
| **[CONFIGURATION.md](docs/CONFIGURATION.md)** | Environment setup, .env configuration, field validation, defaults |
| **[GODOT_INTEGRATION.md](docs/GODOT_INTEGRATION.md)** | Using in Godot projects, calling agents, fallback patterns |
| **[ERROR_HANDLING.md](docs/ERROR_HANDLING.md)** | Robustness, timeout handling, graceful degradation, concurrent execution |
| **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Common issues and solutions, diagnosis steps, getting help |

### Quick Navigation

- **"What can agent-system do?"** → [CAPABILITIES.md](docs/CAPABILITIES.md)
- **"How do I set up the environment?"** → [CONFIGURATION.md](docs/CONFIGURATION.md)
- **"How do I use it in my Godot project?"** → [GODOT_INTEGRATION.md](docs/GODOT_INTEGRATION.md)
- **"What happens if something fails?"** → [ERROR_HANDLING.md](docs/ERROR_HANDLING.md)
- **"I have a problem. Help!"** → [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## Package Layout

```
agent_system/
  __init__.py                 # Public API exports
  akc_http_client.py          # HTTP client for akc-service
  agent_learning_utils.py     # Task result builder + validator
  orchestrator_hooks.py       # Orchestrator lifecycle hooks + KB integration
  config.py                   # Configuration loading and validation
  agents/                     # 4 agent system prompts and configs
    orchestrator/
    mcp/
    script/
    qc/
  skills/                     # 4 Godot-specific skills
    godot-mcp-task/
    godot-orchestrator-gate/
    godot-script-task/
    godot-task-verify/
  docs/                       # Comprehensive documentation (NEW)
    CAPABILITIES.md
    CONFIGURATION.md
    GODOT_INTEGRATION.md
    ERROR_HANDLING.md
    TROUBLESHOOTING.md

examples/
  minimal_usage.py            # Basic usage example

tests/
  test_config.py
  test_akc_http_client.py
  test_agent_learning_utils.py
```

## Core Components

### 4 Specialized Agents

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Orchestrator** | Task decomposition, routing | Game feature request | Subtasks for MCP, Script, QC agents |
| **MCP Agent** | Scene creation | Scene specification | Godot scenes (.tscn files) |
| **Script Agent** | GDScript writing | Logic specification | GDScript source code (.gd files) |
| **QC Agent** | Architecture validation | Scenes + scripts | Validation report, issues |

### AKCClient

HTTP client for pattern retrieval and outcome recording:

```python
from agent_system.akc_http_client import AKCClient

client = AKCClient(base_url="http://localhost:8000")

# Check availability (50ms timeout)
if client.is_available():
    # Query patterns (150ms timeout)
    patterns = client.query_patterns("task-id", "entity", "component")
    
    # Record outcome
    client.record_outcome({
        "task_id": "task-id",
        "status": "success",
        "akc_context": {...}
    })
```

All methods return safe defaults on timeout/error (never raise).

### Learning Integration

Every agent records task outcomes for knowledge base updates:

```python
from agent_system import build_task_result, call_learning_with_timeout

# Build result with pattern data
result = build_task_result(
    task_id="task-001",
    status="success",
    active_patterns=["pat-001"],
    akc_enabled=True
)

# Call learning with timeout + async fallback
learning_result = call_learning_with_timeout(result, timeout_sec=30)
```

## Configuration

5 environment variables control agent-system:

| Variable | Default | Valid Range |
|----------|---------|-------------|
| `AGENT_SYSTEM_MODEL` | `claude-opus-4-7` | `claude-*` pattern |
| `AGENT_SYSTEM_TIMEOUT` | `30` | > 0 seconds |
| `AGENT_SYSTEM_MAX_RETRIES` | `3` | 0-10 |
| `AKC_SERVICE_SAFETY_LEVEL` | `1` | 0, 1, or 2 |
| `AKC_SERVICE_URL` | `http://localhost:8000` | Valid URL |

See [CONFIGURATION.md](docs/CONFIGURATION.md) for detailed setup.

## Error Handling

Agent-system is designed with **fail-safe defaults**:

- AKC service down? → Returns [] for patterns, continues with defaults
- HTTP timeout? → Returns safe defaults (never raises)
- Config invalid? → Raises `ConfigValidationError` with clear message
- Learning timeout? → Falls back to async update (non-blocking)

See [ERROR_HANDLING.md](docs/ERROR_HANDLING.md) for details.

## Testing

```bash
pip install -e ".[test]"
pytest tests/
```

## Tests

```bash
pytest tests/
pytest tests/test_config.py -v
pytest tests/test_akc_http_client.py -v
```
