# Godot Integration Guide

How to integrate agent-system into Godot 4.6 projects for AI-driven game development.

## Overview

Agent-system is designed to coordinate 4 specialized Claude agents for Godot development:
- **Orchestrator** — Decomposes game tasks
- **MCP Agent** — Creates scenes (requires godot-ai MCP server)
- **Script Agent** — Writes GDScript logic
- **QC Agent** — Validates architecture and code quality

This guide covers integrating agent-system into your Godot project workflow.

---

## Installation in Godot Project

### Step 1: Install Package

```bash
# From Godot project root
cd /Users/ducph/godot/my-demon

# Install agent-system in editable mode
pip install -e packages/agent-system

# Verify installation
python -c "from agent_system import load_config; print(load_config().model)"
```

### Step 2: Configure Environment

Create `.env` file in Godot project root:

```bash
cat > .env << 'EOF'
# Agent configuration
AGENT_SYSTEM_MODEL=claude-opus-4-7
AGENT_SYSTEM_TIMEOUT=120
AGENT_SYSTEM_MAX_RETRIES=3

# AKC service configuration
AKC_SERVICE_SAFETY_LEVEL=1
AKC_SERVICE_URL=http://localhost:8000
EOF
```

### Step 3: Verify Setup

```bash
# Load configuration
python -c "
from agent_system import load_config
config = load_config()
print(f'Model: {config.model}')
print(f'Timeout: {config.timeout}s')
print(f'AKC URL: {config.akc_url}')
"
```

---

## Using AKCClient from Python

The AKCClient provides HTTP access to the AKC service for pattern retrieval and outcome recording.

### Basic Usage

```python
from agent_system.akc_http_client import AKCClient
from agent_system import load_config

# Load configuration
config = load_config()

# Create AKC client
client = AKCClient(base_url=config.akc_url, timeout_sec=0.15)

# Check if service is available
if client.is_available():
    # Query patterns for a game component
    patterns = client.query_patterns(
        task_id="player-health-system-v1",
        entity="player",
        component="HealthComponent"
    )
    
    print(f"Found {len(patterns)} patterns:")
    for pattern in patterns:
        print(f"  - {pattern.get('id')}: confidence={pattern.get('confidence')}")
    
    # Use patterns to influence task...
    
    # Later, record the task outcome
    task_result = {
        "task_id": "player-health-system-v1",
        "status": "success",
        "timestamp": "2026-05-05T10:30:00Z",
        "akc_context": {
            "akc_enabled": True,
            "knowledge_patterns_active": [p.get("id") for p in patterns],
            "pattern_outcomes": {
                patterns[0]["id"]: {"used": True, "success": True}
            }
        }
    }
    
    result = client.record_outcome(task_result)
    print(f"Outcome recorded: {result}")
else:
    print("AKC service not available — using fallback defaults")
    patterns = []
```

### Error Handling

All AKCClient methods return safe defaults on error (never raise):

```python
from agent_system.akc_http_client import AKCClient

client = AKCClient()

# These never raise exceptions, even if service is down
patterns = client.query_patterns("task", "entity", "component")
# Returns [] if service unavailable

result = client.record_outcome({"task_id": "task"})
# Returns {} if service unavailable

stats = client.get_stats()
# Returns {} if service unavailable

available = client.is_available()
# Returns False if service unavailable (50ms timeout)
```

---

## Calling Agents from Godot

Since Godot's GDScript runs in the C++ runtime, agents (which run in Claude via Python/HTTP) are called via subprocess.

### Example: Orchestrator Agent Task

```python
# Python script: godot_agents.py
# Place in your Godot project or packages/agent-system/

import json
import subprocess
import sys
from pathlib import Path

def call_orchestrator(task_description: str, context: dict) -> dict:
    """Call Orchestrator agent to decompose a game development task.
    
    Args:
        task_description: High-level task (e.g., "create player movement system")
        context: Game context (scenes, scripts, constraints)
    
    Returns:
        dict with orchestrator response (task decomposition, routing, etc.)
    """
    
    # Prepare request payload
    payload = {
        "agent": "orchestrator",
        "task": task_description,
        "context": context,
        "timeout_sec": 120
    }
    
    # Call Claude via Claude Code subprocess
    # (Real implementation would use Claude SDK)
    cmd = [
        sys.executable,
        "-c",
        f"""
import json
from agent_system import load_config

config = load_config()

# This is where the actual Claude API call happens
# In production, use anthropic SDK with your task
response = {{
    "status": "success",
    "subtasks": [
        {{"agent": "mcp", "task": "create player scene"}},
        {{"agent": "script", "task": "implement movement logic"}}
    ]
}}
print(json.dumps(response))
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        return {"status": "error", "error": result.stderr}


def call_script_agent(task: str) -> dict:
    """Call Script Agent to write GDScript code.
    
    Args:
        task: Script task description
    
    Returns:
        dict with script content, path, and validation results
    """
    
    payload = {
        "agent": "script",
        "task": task,
        "language": "gdscript"
    }
    
    # Similar subprocess call...
    return {"status": "success", "script": "...", "path": "res://..."}
```

### Calling from GDScript

Since GDScript cannot directly call Python, use subprocess:

```gdscript
# In res://scripts/GameDeveloper.gd

extends Node

@export var agent_system_path: String = "packages/agent-system"

func call_agent(agent_type: String, task: String) -> Dictionary:
    """Call an agent via Python subprocess."""
    
    var cmd = [
        "python3",
        "-c",
        _build_agent_call_script(agent_type, task)
    ]
    
    var output = []
    var result = OS.execute(cmd[0], cmd.slice(1), output)
    
    if result == 0:
        var response = JSON.parse_string(output[0])
        return response
    else:
        return {"status": "error", "error": output[0]}


func _build_agent_call_script(agent_type: String, task: String) -> String:
    """Build Python code to call agent."""
    
    return """
import json
from agent_system import load_config

config = load_config()
task_description = %r
agent_type = %r

# Call agent through Claude API
# (Implementation would use real Claude SDK)

response = {
    "status": "success",
    "agent": agent_type,
    "task": task_description
}

print(json.dumps(response))
""" % [task, agent_type]


func _ready() -> void:
    # Call orchestrator to decompose task
    var response = call_agent("orchestrator", "Create a health system for the player")
    
    if response.get("status") == "success":
        print("Task decomposed: ", response.get("subtasks"))
```

---

## Running Agent Tasks

Agent tasks follow a standard lifecycle: preparation, execution, learning integration.

### Task Execution Flow

```python
from agent_system import load_config, build_task_result, call_learning_with_timeout

def run_agent_task(task_id: str, agent_type: str, task_desc: str) -> dict:
    """Execute an agent task with full lifecycle.
    
    Steps:
    1. Prepare task environment
    2. Query AKC for relevant patterns
    3. Execute agent
    4. Validate result
    5. Record learning outcome
    """
    
    from agent_system.akc_http_client import AKCClient
    
    config = load_config()
    akc = AKCClient(base_url=config.akc_url)
    
    # Step 1: Query relevant patterns
    patterns = []
    if akc.is_available():
        patterns = akc.query_patterns(
            task_id=task_id,
            entity="player",
            component="HealthComponent"
        )
    
    # Step 2: Execute agent (pseudo-code)
    print(f"[{agent_type}] Starting: {task_desc}")
    print(f"  Available patterns: {len(patterns)}")
    
    agent_result = {
        "status": "success",
        "output": "...",  # Agent's actual output
        "patterns_used": [p.get("id") for p in patterns]
    }
    
    # Step 3: Build task result for learning
    task_result = build_task_result(
        task_id=task_id,
        status="success" if agent_result["status"] == "success" else "failed",
        active_patterns=[p.get("id") for p in patterns],
        confidence_scores={p.get("id"): p.get("confidence", 0.5) for p in patterns},
        pattern_outcomes={
            p.get("id"): {"used": True, "success": True}
            for p in patterns if p.get("id") in agent_result.get("patterns_used", [])
        },
        akc_enabled=akc.is_available()
    )
    
    # Step 4: Record learning outcome (with timeout and async fallback)
    learning_result = call_learning_with_timeout(task_result, timeout_sec=30)
    
    print(f"  Learning recorded: {learning_result.get('status')}")
    
    return {
        "task_id": task_id,
        "agent_result": agent_result,
        "learning_result": learning_result
    }
```

---

## Handling Fallback When AKC Service Unavailable

The system gracefully degrades when akc-service is down.

### Safe Defaults

```python
from agent_system.akc_http_client import AKCClient

client = AKCClient()

# AKC service unavailable?
if not client.is_available():
    print("AKC service not available — using fallback defaults")
    
    # These return safe defaults without raising
    patterns = client.query_patterns("task", "entity", "component")  # Returns []
    stats = client.get_stats()  # Returns {}
    
    # Agents continue with:
    # - No pattern recommendations
    # - Standard fallback strategies
    # - Learning disabled (will retry async)
```

### Graceful Degradation Example

```python
from agent_system.akc_http_client import AKCClient
from agent_system import build_task_result, call_learning_with_timeout

def execute_task_with_fallback(task_id: str) -> dict:
    """Execute task with graceful fallback when AKC unavailable."""
    
    client = AKCClient()
    
    # Query patterns (returns [] if unavailable)
    active_patterns = []
    if client.is_available():
        response = client.query_patterns(task_id, "entity", "component")
        active_patterns = [p.get("id") for p in response]
    
    # Execute agent (works even without patterns)
    print(f"Executing task with {len(active_patterns)} active patterns")
    agent_result = execute_agent(task_id)  # Hypothetical
    
    # Build result (akc_enabled=False if service unavailable)
    task_result = build_task_result(
        task_id=task_id,
        status="success",
        active_patterns=active_patterns,
        akc_enabled=client.is_available()
    )
    
    # Record learning (falls back to async if timeout)
    learning_result = call_learning_with_timeout(task_result)
    
    return {
        "agent_result": agent_result,
        "learning_fallback": learning_result.get("status")
    }
```

---

## Integration Points with Godot Scenes

### 1. Scene Creation (MCP Agent)

The MCP Agent creates Godot scenes using the godot-ai MCP server:

```python
# In orchestrator, route to MCP Agent for scene creation
if task_type == "create_scene":
    response = call_mcp_agent({
        "action": "create_scene",
        "scene_path": "res://scenes/player/Player.tscn",
        "nodes": [
            {"name": "Player", "type": "CharacterBody2D"},
            {"name": "Sprite", "type": "Sprite2D", "parent": "Player"},
            {"name": "CollisionShape2D", "type": "CollisionShape2D", "parent": "Player"}
        ]
    })
    
    # MCP Agent has created the scene; verify it exists
    assert FileAccess.file_exists(response["scene_path"])
```

### 2. Script Implementation (Script Agent)

The Script Agent writes GDScript logic:

```python
# In orchestrator, route to Script Agent for script writing
if task_type == "implement_logic":
    response = call_script_agent({
        "task": "Implement movement and collision for player",
        "target_scene": "res://scenes/player/Player.tscn",
        "script_path": "res://scenes/player/Player.gd"
    })
    
    # Script Agent has created the script; verify compilation
    assert response["compilation_status"] == "success"
```

### 3. Validation (QC Agent)

The QC Agent validates scene architecture and script quality:

```python
# In orchestrator, route to QC Agent for validation
if task_type == "validate_architecture":
    response = call_qc_agent({
        "action": "validate_scene",
        "scene_path": "res://scenes/player/Player.tscn",
        "checks": [
            "node_hierarchy",
            "physics_layers",
            "collision_setup",
            "script_compilation"
        ]
    })
    
    if response["status"] == "valid":
        print("Architecture validated!")
    else:
        print(f"Issues found: {response['issues']}")
```

---

## Common Integration Patterns

### Pattern 1: Task Orchestration

```python
from agent_system import load_config
from agent_system.akc_http_client import AKCClient

def orchestrate_feature(feature_name: str) -> dict:
    """High-level orchestration: decompose feature into agent tasks."""
    
    config = load_config()
    akc = AKCClient(base_url=config.akc_url)
    
    # Step 1: Decompose
    subtasks = call_orchestrator(f"Implement {feature_name}")
    
    results = []
    for subtask in subtasks:
        # Step 2: Execute each subtask
        if subtask["agent"] == "mcp":
            result = call_mcp_agent(subtask)
        elif subtask["agent"] == "script":
            result = call_script_agent(subtask)
        elif subtask["agent"] == "qc":
            result = call_qc_agent(subtask)
        
        results.append(result)
    
    return {"feature": feature_name, "results": results}
```

### Pattern 2: Pattern-Guided Development

```python
from agent_system.akc_http_client import AKCClient

def develop_with_patterns(entity: str, component: str, task: str) -> dict:
    """Develop using patterns from AKC knowledge base."""
    
    client = AKCClient()
    
    # Query relevant patterns
    patterns = client.query_patterns(
        task_id=task,
        entity=entity,
        component=component
    )
    
    print(f"Found {len(patterns)} patterns for {entity}:{component}")
    
    # Pass patterns to agent
    agent_result = call_script_agent({
        "task": task,
        "recommended_patterns": [p.get("id") for p in patterns],
        "entity": entity,
        "component": component
    })
    
    # Record which patterns were used
    task_result = build_task_result(
        task_id=task,
        status="success",
        active_patterns=[p.get("id") for p in patterns],
        pattern_outcomes={
            patterns[0]["id"]: {"used": True, "success": True}  # Example
        }
    )
    
    call_learning_with_timeout(task_result)
    
    return agent_result
```

### Pattern 3: Fallback to Defaults

```python
from agent_system.akc_http_client import AKCClient

def safe_development(task: str) -> dict:
    """Develop with graceful fallback when AKC unavailable."""
    
    client = AKCClient()
    
    # Query patterns (safe: returns [] if unavailable)
    available_patterns = client.query_patterns("task", "entity", "component") if client.is_available() else []
    
    # Execute with or without patterns
    if available_patterns:
        print(f"Using {len(available_patterns)} patterns")
        agent_result = call_agent_with_patterns(task, available_patterns)
    else:
        print("AKC unavailable — using standard approach")
        agent_result = call_agent_with_defaults(task)
    
    return agent_result
```

---

## Testing Agent Integration

### Unit Tests

```python
# tests/test_agent_integration.py

import unittest
from unittest.mock import patch, MagicMock
from agent_system.akc_http_client import AKCClient
from agent_system import load_config

class TestAgentIntegration(unittest.TestCase):
    
    @patch("agent_system.akc_http_client.requests.Session.post")
    def test_pattern_query_in_task(self, mock_post):
        """Test pattern query during task execution."""
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "patterns": [
                {"id": "pat-001", "confidence": 0.85},
                {"id": "pat-002", "confidence": 0.72}
            ]
        }
        mock_response.headers = {}
        mock_post.return_value = mock_response
        
        # Execute task
        client = AKCClient()
        patterns = client.query_patterns("task", "player", "health")
        
        # Verify patterns were returned
        self.assertEqual(len(patterns), 2)
        self.assertEqual(patterns[0]["id"], "pat-001")
    
    def test_config_loads_for_godot_project(self):
        """Test that config loads correctly in Godot context."""
        
        config = load_config()
        
        # Verify config fields
        self.assertTrue(config.model.startswith("claude-"))
        self.assertGreater(config.timeout, 0)
        self.assertIn(config.safety_level, [0, 1, 2])
        self.assertTrue(config.akc_url.startswith("http"))
```

---

## Debugging & Logging

### Enable Debug Logging

```python
import logging

# Enable debug logging for agent-system
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("agent_system.akc_http_client").setLevel(logging.DEBUG)
logging.getLogger("agent_system.orchestrator_hooks").setLevel(logging.DEBUG)

# Now calls will log details
from agent_system.akc_http_client import AKCClient

client = AKCClient()
patterns = client.query_patterns("task", "entity", "component")
# Logs: "AKC query latency: 42ms"
```

### Verify Configuration

```python
import os
from agent_system import load_config

# Check environment
print("Environment:")
for key in ["AGENT_SYSTEM_MODEL", "AGENT_SYSTEM_TIMEOUT", "AKC_SERVICE_URL"]:
    print(f"  {key}: {os.getenv(key, 'NOT SET')}")

# Load and verify config
config = load_config()
print("\nLoaded config:")
print(f"  model: {config.model}")
print(f"  timeout: {config.timeout}s")
print(f"  akc_url: {config.akc_url}")

# Test AKC connection
from agent_system.akc_http_client import AKCClient
client = AKCClient(base_url=config.akc_url)
print(f"\nAKC service available: {client.is_available()}")
```

---

## See Also

- [CAPABILITIES.md](CAPABILITIES.md) — Agent and skill system details
- [CONFIGURATION.md](CONFIGURATION.md) — Environment and config setup
- [ERROR_HANDLING.md](ERROR_HANDLING.md) — Handling failures gracefully
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common issues and solutions
