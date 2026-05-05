---
name: godot-script-task
description: Script Agent skill for GDScript writing and verification. Invoke at START and END of every script task. Enforces godot-docs lookup, node_inventory cross-check, find_symbols syntax gate, and post-attach scene_save.
---

# Godot Script Task Skill

**Invoke at START and END of every task.**

First: invoke `godot-task-verify` base skill.

---

## Pre-Task Checklist

```
[ ] 1. Verify node_inventory is present in handoff
        → If missing: STOP. Return MISSING_NODE_INVENTORY.
          Never guess node paths — broken @onready refs fail at runtime, not parse time.

[ ] 2. editor_state() — readiness must be "ready"

[ ] 3. scene_open(path) if not current scene; re-check readiness after
        → scene_get_hierarchy() — confirm every node_path in node_inventory
          exists in the live tree before writing any script.
          Mismatch = return INVALID_NODE_PATH, route back to MCP Agent.

[ ] 4. Query godot-docs for any unfamiliar Godot class, method, or signal
        → mcp__godot-docs__search(query="ClassName", mode="keyword")
          mcp__godot-docs__search(query="conceptual question", mode="semantic")
          Do this BEFORE writing code. Prevents inventing non-existent methods.
          mode="keyword" for exact names; mode="semantic" for concepts.

[ ] 5. Check for FILE_CONFLICT on target script path
        → script_manage(op="read", params={"script_path": "res://path/to/script.gd"})
          Success response = file exists → use script_patch for targeted edits, not full overwrite.
          Error response with "not found" in message = safe to create with script_create.
```

---

## Post-Task Checklist (Verification Gate)

```
[ ] 1. script_manage(op="read", params={"script_path": "res://..."})
        → Read back what landed on disk.
          Confirm @onready paths match node_inventory entries exactly.
          Confirm all required methods are present.
          Confirm all signals declared before use.

[ ] 2. script_manage(op="find_symbols", params={"script_path": "res://..."})
        → Returns methods the GDScript parser found.
          Count must match methods_required count. If a method is missing:
          syntax error or indentation fault — check for mixed tabs/spaces (Pitfall S1).

[ ] 3. script_attach(node_path="/root/RootNodeName", script_path="res://...")
        → node_path uses live tree format with /root/ prefix.
          Dirties scene in memory — scene_save required after.

[ ] 4. node_get_properties(path="/root/RootNodeName")
        → Confirm "script" property equals the expected res:// path.
          Catches silent no-ops where script_attach targeted wrong node.

[ ] 5. scene_save()
        → Persist script attachment to disk. Attachment lives only in editor memory until saved.

[ ] 6. signal_manage(op="list", params={"node_path": "/root/RootNodeName"})
        → Confirm signals declared in script are registered on the live node.
          Catches silent parse failures that don't surface as log errors.

[ ] 7. Invoke base skill headless verification gate
        → project_run(autosave=False) + logs_read()
          Watch for: "Invalid @onready", "signal not found", null reference errors.
```

---

## Script Agent Pitfalls Digest

| # | Pitfall | Guard |
|---|---------|-------|
| S1 | Mixed tabs/spaces — parser error on apparently valid line | `script_manage(op="find_symbols")` returns fewer methods than expected |
| S2 | `@onready` on a non-node value (`@onready var health: int = 100`) — assigns null | Only use `@onready` for scene node refs; init primitives in `_ready()` |
| S3 | Signal handler type mismatch (`signal foo(x: int)` handler receives `float`) — crash at emit | Declaration and all handlers must use identical parameter types |
| S4 | `script_create` without follow-up `script_attach` — file exists but node has no script | Verify `node_get_properties` shows script property set after attach |
| S5 | `$` NodePath with extra slash (`$/Sprite2D`) — invalid GDScript | Correct: `$Sprite2D` (no slash); root self-reference: use `self`, not `$` |
| S6 | `ui_left`/`ui_right` map to arrow keys only, not WASD by default | Use dedicated `move_left`/`move_right` actions or add WASD to InputMap |

---

## Feedback Logging

This skill logs all invocations to `.claude/skills/godot-script-task/skill_runs.jsonl` for monitoring.

**At invocation start:**
```
from skill_logging import SkillLogger
logger = SkillLogger("godot-script-task", ".claude/skills/godot-script-task")
logger.log_invocation(agent="script", version="1.1", session_id=environ.get("CLAUDE_SESSION_ID"))
```

**During execution, for each verification check:**
```
logger.increment_checks()           # Passed
logger.increment_checks(failed=True)  # Failed
```

**At completion:**
```
logger.log_completion(task_passed=True)  # or False
```

See `docs/SKILL_FEEDBACK.md` for logging schema and analytics.
