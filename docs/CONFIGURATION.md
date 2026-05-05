# Configuration Guide

How to configure agent-system for different scenarios, environments, and use cases.

## Quick Start

### 1. Install the Package

```bash
cd /Users/ducph/godot/my-demon/packages/agent-system
pip install -e .
```

### 2. Create .env File

```bash
# In the agent-system root directory or your project root
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 3. Load Configuration

```python
from agent_system import load_config

config = load_config()
# config.model, config.timeout, config.max_retries, etc.
```

---

## Environment Variables

Configuration is loaded from environment variables with `.env` file fallback.

### 5 Configuration Fields

| Variable | Type | Default | Valid Range | Purpose |
|----------|------|---------|-------------|---------|
| `AGENT_SYSTEM_MODEL` | string | `claude-opus-4-7` | `claude-*` pattern | Claude model to use |
| `AGENT_SYSTEM_TIMEOUT` | integer | `30` | > 0 seconds | Agent task timeout |
| `AGENT_SYSTEM_MAX_RETRIES` | integer | `3` | 0-10 | Retry attempts on failure |
| `AKC_SERVICE_SAFETY_LEVEL` | integer | `1` | 0, 1, or 2 | KB safety enforcement |
| `AKC_SERVICE_URL` | string | `http://localhost:8000` | Valid URL | AKC service endpoint |

### Precedence

Configuration is loaded in this order (highest to lowest priority):

1. **Environment variables** — set directly in shell or CI/CD
2. **.env file** — `AGENT_SYSTEM_MODEL=...` entries
3. **Defaults** — hardcoded fallback values

Example: If `AGENT_SYSTEM_TIMEOUT=60` is set in shell, it overrides any `.env` entry.

---

## Configuration Examples

### Example 1: Development (Local AKC)

**.env file:**
```env
# Local development pointing at localhost AKC service
AGENT_SYSTEM_MODEL=claude-haiku-4-5-20251001
AGENT_SYSTEM_TIMEOUT=60
AGENT_SYSTEM_MAX_RETRIES=5
AKC_SERVICE_SAFETY_LEVEL=0
AKC_SERVICE_URL=http://localhost:8000
```

**Why these settings:**
- Haiku model for faster iteration
- 60s timeout for debugging
- 5 retries for flaky local services
- Safety level 0 (permissive) for development
- Localhost for quick feedback

### Example 2: Production (Remote AKC)

**.env file:**
```env
# Production with remote AKC service
AGENT_SYSTEM_MODEL=claude-opus-4-7
AGENT_SYSTEM_TIMEOUT=30
AGENT_SYSTEM_MAX_RETRIES=3
AKC_SERVICE_SAFETY_LEVEL=2
AKC_SERVICE_URL=http://akc-prod.example.com:8000
```

**Why these settings:**
- Opus model for best quality
- 30s timeout (production constraint)
- 3 retries (avoiding cascading failures)
- Safety level 2 (strictest validation)
- Remote AKC endpoint

### Example 3: CI/CD Pipeline

**GitHub Actions example (.github/workflows/test.yml):**
```yaml
env:
  AGENT_SYSTEM_MODEL: claude-haiku-4-5-20251001
  AGENT_SYSTEM_TIMEOUT: 45
  AGENT_SYSTEM_MAX_RETRIES: 2
  AKC_SERVICE_SAFETY_LEVEL: 1
  AKC_SERVICE_URL: http://localhost:8000

steps:
  - name: Install agent-system
    run: pip install -e packages/agent-system[test]
  
  - name: Run tests
    run: pytest packages/agent-system/tests/
```

**Why these settings:**
- Haiku model for speed
- 45s timeout (CI environment is slower than local)
- 2 retries (avoid flakiness)
- Safety level 1 (balanced)
- Localhost (AKC mock or real service in CI)

### Example 4: Godot Editor Integration

**In Godot project `.env` (or set in editor environment):**
```env
AGENT_SYSTEM_MODEL=claude-opus-4-7
AGENT_SYSTEM_TIMEOUT=120
AGENT_SYSTEM_MAX_RETRIES=3
AKC_SERVICE_SAFETY_LEVEL=1
AKC_SERVICE_URL=http://localhost:8000
```

**Why these settings:**
- Opus model for complex scene decisions
- 120s timeout (longer for editor interaction)
- 3 retries (handle temporary connection issues)
- Safety level 1 (standard)
- Localhost (development AKC)

---

## AgentConfig Class

The `AgentConfig` dataclass represents loaded configuration.

### Definition

```python
from dataclasses import dataclass

@dataclass
class AgentConfig:
    model: str              # Claude model (e.g., "claude-opus-4-7")
    timeout: int            # Seconds
    max_retries: int        # 0-10 range
    safety_level: int       # 0, 1, or 2
    akc_url: str            # HTTP endpoint
```

### Usage

```python
from agent_system import load_config, ConfigValidationError

try:
    config = load_config()
    
    # Access fields
    print(f"Model: {config.model}")
    print(f"Timeout: {config.timeout}s")
    print(f"Max retries: {config.max_retries}")
    print(f"AKC URL: {config.akc_url}")
    
except ConfigValidationError as e:
    # Handle invalid configuration
    print(f"Configuration error: {e}")
    sys.exit(1)
```

---

## Validation & Error Handling

### Validation Rules

Each field is validated when `load_config()` is called.

| Field | Validation | Error Message |
|---|---|---|
| `model` | Must match `claude-*` pattern | `model must match claude-* pattern` |
| `timeout` | Must be positive integer | `timeout must be positive integer` |
| `max_retries` | Must be 0-10 integer | `max_retries must be 0-10` |
| `safety_level` | Must be 0, 1, or 2 | `safety_level must be 0, 1, or 2` |
| `akc_url` | String (no validation) | — |

### Catching Validation Errors

```python
from agent_system import load_config, ConfigValidationError

try:
    config = load_config()
except ConfigValidationError as e:
    # Handle specific validation failure
    if "model" in str(e):
        print(f"Invalid model: {e}")
        config = AgentConfig(
            model="claude-opus-4-7",  # Use default
            timeout=30,
            max_retries=3,
            safety_level=1,
            akc_url="http://localhost:8000"
        )
    else:
        raise
```

---

## Default Values

When an environment variable is not set, the default is used.

```python
_DEFAULTS = {
    "model": "claude-opus-4-7",
    "timeout": 30,
    "max_retries": 3,
    "safety_level": 1,
    "akc_url": "http://localhost:8000",
}
```

### When Defaults Are Used

1. **Environment variable not set** — use default
2. **Environment variable is empty string** — use default
3. **.env file missing** — use default
4. **python-dotenv not installed** — only env vars available, use defaults

### Verifying Current Configuration

```python
import os
from agent_system import load_config

config = load_config()

# See what was loaded
print(f"Model: {config.model}")
print(f"  from env: {os.getenv('AGENT_SYSTEM_MODEL', 'NOT SET')}")
print()
print(f"AKC URL: {config.akc_url}")
print(f"  from env: {os.getenv('AKC_SERVICE_URL', 'NOT SET')}")
```

---

## .env File Format

### Minimal .env.example

```env
# Claude model to use for agent tasks
AGENT_SYSTEM_MODEL=claude-opus-4-7

# Timeout in seconds for agent task execution
AGENT_SYSTEM_TIMEOUT=30

# Maximum retry attempts (0-10)
AGENT_SYSTEM_MAX_RETRIES=3

# AKC service safety enforcement level (0=permissive, 1=standard, 2=strict)
AKC_SERVICE_SAFETY_LEVEL=1

# URL of AKC service for pattern retrieval and outcome recording
AKC_SERVICE_URL=http://localhost:8000
```

### Expanded .env.example (with Comments)

```env
# ─── AGENT CONFIGURATION ────────────────────────────────────────────────────
# Configure Claude models, timeouts, and retry behavior for agent tasks.

# Claude model version to use for all agent execution
# Valid values: claude-opus-4-7, claude-sonnet-4-5, claude-haiku-4-5-20251001
AGENT_SYSTEM_MODEL=claude-opus-4-7

# Maximum seconds an agent task can run before timeout
# Recommended:
#   - Development: 60-120 (allow debugging)
#   - Production: 30-45 (prevent hangs)
#   - CI/CD: 45-60 (slower environment)
AGENT_SYSTEM_TIMEOUT=30

# Number of retries on task failure
# Range: 0 (no retries) to 10 (max)
# Recommended:
#   - Development: 5 (handle flaky services)
#   - Production: 3 (standard)
#   - CI/CD: 2 (avoid cascading failures)
AGENT_SYSTEM_MAX_RETRIES=3

# ─── AKC SERVICE CONFIGURATION ──────────────────────────────────────────────
# Configure connection to the Agent Knowledge Collective (AKC) service
# for pattern retrieval and learning integration.

# Safety enforcement level for KB pattern recommendations
# 0 = Permissive (dev only) — use all patterns regardless of confidence
# 1 = Standard (default) — prefer high-confidence patterns
# 2 = Strict (production) — enforce minimum confidence thresholds
AKC_SERVICE_SAFETY_LEVEL=1

# AKC service HTTP endpoint
# Examples:
#   - http://localhost:8000 (local development)
#   - http://akc-prod.example.com:8000 (production)
#   - http://192.168.1.100:8000 (network service)
AKC_SERVICE_URL=http://localhost:8000
```

### Loading .env File Manually

If `python-dotenv` is installed:

```python
from dotenv import load_dotenv
load_dotenv('/path/to/.env')  # Loads into os.environ

from agent_system import load_config
config = load_config()
```

The `load_config()` function automatically calls `load_dotenv()` if the package is installed.

---

## Godot Project Setup

To use agent-system in a Godot project:

### Step 1: Create Project .env

```bash
# In your Godot project root
cat > .env << 'EOF'
AGENT_SYSTEM_MODEL=claude-opus-4-7
AGENT_SYSTEM_TIMEOUT=120
AGENT_SYSTEM_MAX_RETRIES=3
AKC_SERVICE_SAFETY_LEVEL=1
AKC_SERVICE_URL=http://localhost:8000
EOF
```

### Step 2: Install agent-system

```bash
# From Godot project root, install into global Python
pip install -e packages/agent-system

# Or in a virtual environment
python -m venv venv
source venv/bin/activate
pip install -e packages/agent-system
```

### Step 3: Configure Godot Editor

Option A: Set environment before running Godot:
```bash
export AGENT_SYSTEM_MODEL=claude-opus-4-7
godot --path /Users/ducph/godot/my-demon
```

Option B: Create launcher script:
```bash
#!/bin/bash
source /Users/ducph/godot/my-demon/.env
godot --path /Users/ducph/godot/my-demon
```

### Step 4: Access in GDScript

GDScript cannot directly import Python, but agents can call Python subprocesses:

```gdscript
# In GDScript — spawn agent task in subprocess
var process = OS.create_process("python3", [
    "-c",
    "from agent_system import load_config; print(load_config().model)"
])
```

---

## Safety Levels Explained

### Level 0: Permissive (Development Only)

- Use all patterns regardless of confidence
- No minimum confidence threshold
- Useful for testing and experimentation
- **DO NOT use in production**

```python
# Level 0 behavior
if safety_level == 0:
    # Accept patterns with any confidence
    recommended_patterns = all_patterns  # Even confidence < 0.50
```

### Level 1: Standard (Default, Recommended)

- Prefer high-confidence patterns (>= 0.70)
- Use production-tier and above
- Fallback to experimental if necessary
- **Recommended for most use cases**

```python
# Level 1 behavior
if safety_level == 1:
    # Prefer patterns with confidence >= 0.70
    gold = [p for p in patterns if p.confidence >= 0.85]
    if gold:
        return gold
    production = [p for p in patterns if p.confidence >= 0.70]
    if production:
        return production
    # Use experimental as fallback
    return experimental_patterns
```

### Level 2: Strict (Production, Mature KB Only)

- Only use gold-tier patterns (confidence >= 0.85)
- Require patterns to be tested in production
- Fallback to safe defaults if no gold patterns
- **Recommended for production with mature KB**

```python
# Level 2 behavior
if safety_level == 2:
    # Only accept high-confidence gold-tier patterns
    gold = [p for p in patterns if p.confidence >= 0.85]
    if gold:
        return gold
    # Otherwise return empty (use safe defaults)
    return []
```

---

## Troubleshooting Configuration

### "Config not loading" — diagnostic steps

1. **Check environment variables:**
   ```bash
   echo $AGENT_SYSTEM_MODEL
   echo $AKC_SERVICE_URL
   ```

2. **Verify .env file exists and is readable:**
   ```bash
   ls -la /path/to/.env
   cat /path/to/.env
   ```

3. **Test load_config() directly:**
   ```python
   import os
   from agent_system import load_config, ConfigValidationError
   
   # Check what's available
   print("Environment variables:")
   for key in ['AGENT_SYSTEM_MODEL', 'AGENT_SYSTEM_TIMEOUT', 'AKC_SERVICE_URL']:
       print(f"  {key}: {os.getenv(key, 'NOT SET')}")
   
   # Try loading
   try:
       config = load_config()
       print(f"Config loaded: model={config.model}")
   except ConfigValidationError as e:
       print(f"Validation error: {e}")
   ```

4. **Check python-dotenv installation:**
   ```bash
   python -c "import dotenv; print(dotenv.__version__)"
   ```

---

## See Also

- [CAPABILITIES.md](CAPABILITIES.md) — Agent and skill system overview
- [ERROR_HANDLING.md](ERROR_HANDLING.md) — Handling configuration failures
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common issues and solutions
