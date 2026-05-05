# Troubleshooting Guide

Solutions to common issues when using agent-system.

---

## Issue: "akc_http_client timeout"

### Symptoms
- Pattern queries slow
- Frequent `AKC query timeout` warnings in logs
- Agent tasks slower than expected

### Root Causes
1. AKC service is running but slow
2. Network latency to AKC service
3. Timeout value too short (150ms default)
4. AKC service is overloaded

### Diagnosis Steps

```bash
# 1. Check if service is running
curl -I http://localhost:8000/akc/v1/health

# 2. Measure network latency
ping localhost  # Should be < 5ms on local machine

# 3. Check service logs
tail -f /path/to/akc-service.log

# 4. Verify timeout setting
python -c "from agent_system import load_config; print(load_config().akc_url)"
```

### Solutions

**Option 1: Verify service is running**
```bash
# Start AKC service if needed
python -m akc_service.main --port 8000

# Verify it responds
curl http://localhost:8000/akc/v1/health
# Should return 200 OK
```

**Option 2: Check network connectivity**
```bash
# From Godot project directory
python -c "
from agent_system.akc_http_client import AKCClient
client = AKCClient(base_url='http://localhost:8000')
print('AKC available:', client.is_available())
"
```

**Option 3: Increase timeout (if needed)**
```env
# .env
AGENT_SYSTEM_TIMEOUT=60
AKC_SERVICE_URL=http://localhost:8000
```

Then restart your agent tasks.

**Option 4: Check service performance**
```bash
# Monitor AKC service resource usage
python -c "
from agent_system.akc_http_client import AKCClient
client = AKCClient()
stats = client.get_stats()
print('AKC Stats:', stats)
"
```

---

## Issue: "Config not loading"

### Symptoms
- `ConfigValidationError` raised when loading config
- "model must match claude-* pattern" error
- "timeout must be positive integer" error

### Root Causes
1. .env file has invalid values
2. Environment variables set incorrectly
3. .env file not found or not loaded
4. Invalid field types (string instead of int, etc.)

### Diagnosis Steps

```bash
# 1. Check if .env exists
ls -la /path/to/.env

# 2. View .env contents
cat /path/to/.env

# 3. Check environment variables
echo "AGENT_SYSTEM_MODEL=$AGENT_SYSTEM_MODEL"
echo "AGENT_SYSTEM_TIMEOUT=$AGENT_SYSTEM_TIMEOUT"
echo "AKC_SERVICE_SAFETY_LEVEL=$AKC_SERVICE_SAFETY_LEVEL"

# 4. Test load_config directly
python -c "
from agent_system import load_config, ConfigValidationError
import os
print('Env vars:')
for key in ['AGENT_SYSTEM_MODEL', 'AGENT_SYSTEM_TIMEOUT', 'AKC_SERVICE_SAFETY_LEVEL']:
    print(f'  {key}: {os.getenv(key, \"NOT SET\")}')

try:
    config = load_config()
    print('Config loaded successfully')
except ConfigValidationError as e:
    print(f'Config error: {e}')
"
```

### Solutions

**Solution 1: Create valid .env file**
```bash
# Create from example
cp .env.example .env

# Or create manually
cat > .env << 'EOF'
AGENT_SYSTEM_MODEL=claude-opus-4-7
AGENT_SYSTEM_TIMEOUT=30
AGENT_SYSTEM_MAX_RETRIES=3
AKC_SERVICE_SAFETY_LEVEL=1
AKC_SERVICE_URL=http://localhost:8000
EOF
```

**Solution 2: Fix invalid values**

| Error | Invalid | Valid |
|-------|---------|-------|
| `model must match claude-* pattern` | `gpt-4` | `claude-opus-4-7` |
| `timeout must be positive integer` | `-1` or `abc` | `30` (positive integer) |
| `max_retries must be 0-10` | `11` or `-1` | `3` (0-10) |
| `safety_level must be 0, 1, or 2` | `5` | `1` |

Example fix:
```env
# WRONG
AGENT_SYSTEM_MODEL=gpt-4
AGENT_SYSTEM_TIMEOUT=abc

# CORRECT
AGENT_SYSTEM_MODEL=claude-opus-4-7
AGENT_SYSTEM_TIMEOUT=30
```

**Solution 3: Verify python-dotenv is installed**
```bash
python -c "import dotenv; print(dotenv.__version__)"

# If not installed:
pip install python-dotenv
```

**Solution 4: Load .env before loading config**
```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env into os.environ

from agent_system import load_config
config = load_config()
```

---

## Issue: "Skills not found"

### Symptoms
- Skill execution fails with "skill not found"
- `godot-mcp-task` or other skills unavailable
- Error referencing `.claude/skills/` directory

### Root Causes
1. Godot project not initialized with Claude Code
2. Skills not checked into git
3. Wrong working directory
4. Skills directory has wrong structure

### Diagnosis Steps

```bash
# 1. Check if .claude directory exists
ls -la /Users/ducph/godot/my-demon/.claude/

# 2. List available skills
ls -la /Users/ducph/godot/my-demon/.claude/skills/

# 3. Verify skill structure
ls -la /Users/ducph/godot/my-demon/.claude/skills/godot-mcp-task/

# 4. Check if skills are tracked in git
cd /Users/ducph/godot/my-demon
git ls-files .claude/skills/
```

### Solutions

**Solution 1: Initialize Claude Code in project**
```bash
cd /Users/ducph/godot/my-demon

# Initialize Claude Code (creates .claude directory)
# This should have been done during project setup
# Verify it exists:
test -d .claude && echo ".claude directory exists" || echo ".claude missing"
```

**Solution 2: Verify skills are installed**
```bash
# Check if skills directory has content
ls -R .claude/skills/

# Expected structure:
# .claude/skills/
#   godot-mcp-task/
#   godot-script-task/
#   godot-orchestrator-gate/
#   godot-task-verify/
```

**Solution 3: Reinitialize skills if missing**
```bash
# Check git status
git status

# If skills not tracked, add them:
git add .claude/skills/
git commit -m "Add Godot agent skills"
```

**Solution 4: Use absolute paths when calling skills**
```python
from pathlib import Path

skills_dir = Path("/Users/ducph/godot/my-demon/.claude/skills")
assert (skills_dir / "godot-mcp-task").exists(), "Skills not found"

# Or check via Skill tool
from Skill import Skill
Skill(skill="godot-mcp-task")  # Raises if not found
```

---

## Issue: "Skill execution timeout"

### Symptoms
- Skill returns "timeout" status
- `godot-mcp-task` or `godot-script-task` slow
- Agent tasks blocked waiting for skill result

### Root Causes
1. Godot editor not responding
2. MCP server (godot-ai) not accessible
3. Scene/script being edited is complex
4. Timeout value too short

### Diagnosis Steps

```bash
# 1. Check if Godot editor is running
ps aux | grep godot

# 2. Verify godot-ai MCP server is running
curl http://127.0.0.1:8000/mcp

# 3. Check Godot editor logs
tail -f ~/.godot/editor_logs/

# 4. Test MCP server connectivity
python -c "
import requests
try:
    response = requests.head('http://127.0.0.1:8000/mcp', timeout=1)
    print(f'MCP server status: {response.status_code}')
except Exception as e:
    print(f'MCP server error: {e}')
"
```

### Solutions

**Solution 1: Ensure Godot editor is running**
```bash
# Start Godot with MCP server
godot --path /Users/ducph/godot/my-demon

# Verify it's accessible
curl http://127.0.0.1:8000/mcp
# Should return 200 OK
```

**Solution 2: Verify godot-ai MCP server**
```bash
# Check if godot-ai is installed
python -c "import godot_ai; print(godot_ai.__version__)"

# Start MCP server (if not auto-started)
python -m godot_ai.server --port 8000
```

**Solution 3: Increase skill timeout**
```python
# In agent configuration or skill settings
# Increase timeout for complex scenes
AGENT_SYSTEM_TIMEOUT=120  # Increase from 30s to 120s
```

**Solution 4: Simplify complex scenes**

If a skill times out on a specific scene:
- Break scene into smaller parts
- Remove unnecessary nodes
- Cache intermediate results
- Split task into multiple subtasks

---

## Issue: "Import errors"

### Symptoms
- `ImportError: No module named 'agent_system'`
- `ModuleNotFoundError: No module named 'anthropic'`
- `ImportError: cannot import name 'AKCClient'`

### Root Causes
1. agent-system not installed
2. Wrong Python environment
3. Missing dependencies (requests, anthropic)
4. Circular imports in custom code

### Diagnosis Steps

```bash
# 1. Check if agent-system is installed
python -c "import agent_system; print(agent_system.__version__)"

# 2. List installed packages
pip list | grep -E "agent-system|anthropic|requests"

# 3. Check Python path
python -c "import sys; print('\\n'.join(sys.path))"

# 4. Verify installation in correct environment
which python
python --version
```

### Solutions

**Solution 1: Install agent-system**
```bash
# From agent-system directory
cd /Users/ducph/godot/my-demon/packages/agent-system
pip install -e .

# Verify
python -c "from agent_system import AKCClient; print('OK')"
```

**Solution 2: Install missing dependencies**
```bash
# Install core dependencies
pip install requests anthropic python-dotenv

# Or install with test dependencies
pip install -e ".[test]"
```

**Solution 3: Use correct Python environment**
```bash
# If using virtual environment
source venv/bin/activate
python -c "from agent_system import load_config; load_config()"

# If using system Python
python3 -c "from agent_system import load_config; load_config()"
```

**Solution 4: Check for circular imports**

If importing your custom code causes ImportError:
```python
# Bad: circular import
# mycode.py
from agent_system import load_config
from mymodule import some_function

# Good: import at use time
# mycode.py
def my_function():
    from agent_system import load_config
    config = load_config()
```

---

## Issue: "AKC service connection refused"

### Symptoms
- `ConnectionRefusedError` in logs
- `client.is_available()` returns False
- Pattern queries always fail

### Root Causes
1. AKC service not running
2. Wrong URL or port
3. Firewall blocking connection
4. AKC service crashed

### Diagnosis Steps

```bash
# 1. Check if service is running
ps aux | grep akc-service

# 2. Try connecting manually
curl http://localhost:8000/akc/v1/health

# 3. Check firewall
sudo lsof -i :8000

# 4. Verify config URL
python -c "from agent_system import load_config; print(load_config().akc_url)"
```

### Solutions

**Solution 1: Start AKC service**
```bash
# If AKC service is available
python -m akc_service.main --port 8000

# Or start it in background
nohup python -m akc_service.main --port 8000 > akc-service.log 2>&1 &
```

**Solution 2: Fix AKC service URL**
```env
# .env
# If service is on different host/port:
AKC_SERVICE_URL=http://10.0.0.100:8000

# Or if running elsewhere:
AKC_SERVICE_URL=http://akc-prod.example.com:8000
```

**Solution 3: Check firewall**
```bash
# macOS: check if port is listening
sudo lsof -i :8000

# Linux: check if port is open
sudo netstat -tuln | grep 8000

# Allow through firewall if needed
```

**Solution 4: Review AKC service logs**
```bash
# Check service logs for crashes or errors
tail -100 akc-service.log

# Look for:
# - Port already in use
# - Syntax errors
# - Missing dependencies
```

---

## Issue: "Task result validation failed"

### Symptoms
- `validate_task_result()` returns False
- Learning integration rejects task result
- "Invalid task result" error in logs

### Root Causes
1. Missing required fields in task result
2. Invalid status (not "success" or "failed")
3. akc_context is None or invalid
4. Schema version mismatch

### Diagnosis Steps

```bash
# 1. Check task result structure
python -c "
from agent_system import validate_task_result, build_task_result

# Build a valid result
result = build_task_result(
    task_id='test',
    status='success'
)

# Check what fields are required
print('Valid fields:')
for key in result.keys():
    print(f'  {key}: {type(result[key]).__name__}')

# Validate
print('Valid:', validate_task_result(result))
"

# 2. Check your custom result
python -c "
from agent_system import validate_task_result

my_result = {
    'task_id': 'test',
    'status': 'success'
    # Missing required fields
}

print('Valid:', validate_task_result(my_result))
"
```

### Solutions

**Solution 1: Use build_task_result helper**
```python
from agent_system import build_task_result, validate_task_result

# Always use build_task_result to ensure valid schema
result = build_task_result(
    task_id="task-001",
    status="success",
    active_patterns=["pat-001"],
    confidence_scores={"pat-001": 0.85},
    akc_enabled=True
)

# Automatically valid
assert validate_task_result(result)
```

**Solution 2: Check required fields**
```python
from agent_system import validate_task_result

# Required fields:
required = {
    "schema_version": "1.0",
    "task_id": "task-001",
    "status": "success",  # or "failed"
    "timestamp": "2026-05-05T10:30:00Z",
    "akc_context": {
        "akc_enabled": True,
        "knowledge_patterns_active": [],
        "confidence_scores": {},
        "pattern_outcomes": {}
    }
}

assert validate_task_result(required)
```

**Solution 3: Fix status value**
```python
from agent_system import build_task_result

# WRONG
result = build_task_result(
    task_id="task",
    status="running"  # Invalid!
)
# Raises ValueError: status must be one of {'success', 'failed'}

# CORRECT
result = build_task_result(
    task_id="task",
    status="success"  # or "failed"
)
```

---

## Getting Help

### 1. Check Logs

```bash
# Agent-system logs
find /Users/ducph/godot/my-demon -name "*.log" -type f | head -10

# Learning integration logs
ls -la /Users/ducph/godot/my-demon/agent_system/logs/

# Godot editor logs
ls -la ~/.godot/editor_logs/

# AKC service logs
find . -name "akc-service.log" -o -name "akc_service.log"
```

### 2. Enable Debug Logging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s %(message)s'
)

# Now see detailed debug info
from agent_system import load_config
config = load_config()
```

### 3. Test Configuration

```bash
python -c "
from agent_system import load_config, ConfigValidationError
import os

print('=== Environment ===')
for key in ['AGENT_SYSTEM_MODEL', 'AGENT_SYSTEM_TIMEOUT', 'AKC_SERVICE_URL']:
    print(f'{key}: {os.getenv(key, \"NOT SET\")}')

print('\\n=== Configuration ===')
try:
    config = load_config()
    print(f'Model: {config.model}')
    print(f'Timeout: {config.timeout}s')
    print(f'AKC URL: {config.akc_url}')
except ConfigValidationError as e:
    print(f'Error: {e}')

print('\\n=== AKC Service ===')
from agent_system.akc_http_client import AKCClient
client = AKCClient()
print(f'Available: {client.is_available()}')
"
```

### 4. Report Issues

When reporting an issue, include:
1. Error message and full traceback
2. Configuration (without secrets): model, timeout, safety level
3. Steps to reproduce
4. Relevant logs (last 50 lines)
5. Python version: `python --version`
6. agent-system version: `python -c "import agent_system; print(agent_system.__version__)"`

Example issue report:
```
Subject: AKC query timeout on player:HealthComponent

Steps:
1. Call client.query_patterns("task", "player", "HealthComponent")
2. Wait...
3. Gets timeout after 150ms

Config:
- Model: claude-opus-4-7
- Timeout: 30s
- AKC URL: http://localhost:8000

Error:
WARNING:agent_system.akc_http_client:AKC query timeout for task task

Environment:
- Python 3.11.6
- agent-system 0.1.0
- macOS 14.0
```

---

## See Also

- [CAPABILITIES.md](CAPABILITIES.md) — Feature overview
- [CONFIGURATION.md](CONFIGURATION.md) — Configuration setup
- [ERROR_HANDLING.md](ERROR_HANDLING.md) — Error handling patterns
- [GODOT_INTEGRATION.md](GODOT_INTEGRATION.md) — Integration guide
