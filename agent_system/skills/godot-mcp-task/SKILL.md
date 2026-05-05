---
name: godot-mcp-task
description: MCP Agent skill for Godot scene creation and verification. Invoke at START and END of every scene task. Enforces batch_execute-only scene creation, post-create hierarchy verification, scene_save, and node_inventory accuracy.
---

# Godot MCP Task Skill

**Invoke at START and END of every task.**

First: invoke `godot-task-verify` base skill.

---

## Pre-Task Checklist

```
[ ] 1. editor_state()
        → readiness must be "ready". Handle per readiness state table in godot-task-verify.

[ ] 2. New scene creation: scene_manage(op="create", params={"path": "res://..."}) first
        → scene_open fails on non-existent paths.
          Create the scene file first, then scene_open to make it current.

[ ] 3. scene_open(path=output_scene_path)
        → Re-check editor_state() after — editor briefly enters "importing".
          Proceed only when readiness == "ready".

[ ] 4. Check for FILE_CONFLICT
        → scene_get_hierarchy() to read current state of the now-open scene.
          If nodes exist and task is "create new": do NOT overwrite without explicit instruction.
          If task is "modify existing": document current state before touching anything.

[ ] 5. If modifying existing scene:
        → node_find(query) to locate target nodes by name before mutating.

[ ] 6. Resolve PhysicsLayers BEFORE building batch_execute
        → Read constants/PhysicsLayers.gd:
          WORLD=1, PLAYER=2, MINIONS=3, HEROES=4, COLLECTIBLES=5, HITBOXES=6, HURTBOXES=7
          Convert all "PhysicsLayers.LAYER_X" strings to integers now.
          Never pass string constants into MCP tool call value fields.

[ ] 7. autoload_manage(op="list")
        → Confirm PhysicsLayers, EventBus, and any other autoloads the scene depends on
          are registered before proceeding.
```

---

## Post-Task Checklist (Verification Gate)

```
[ ] 1. scene_get_hierarchy(depth=10, offset=0, limit=100)
        → Operates on currently open scene — no scene_path param.
          Walk full tree. Confirm every node from node_structure exists by name and type.
          Root node type matches spec. All children present.
          If limit=100 is hit and scene may have more nodes: re-call with offset=100.
          If anything missing: STOP. Return failure. Do NOT save.

[ ] 2. node_get_properties(path="/root/RootNodeName")
        → Confirm collision_layer and collision_mask match resolved integers from PhysicsLayers.
          Confirm script property is not null (script is attached).
          node_path uses live tree format: /root/RootNodeName (not $RootNodeName).

[ ] 3. node_get_properties on each Area2D child
        → For HitboxComponent: path="/root/RootNode/HitboxComponent"
          For HurtboxComponent: path="/root/RootNode/HurtboxComponent"
          Verify collision_layer and collision_mask integers match spec.

[ ] 4. signal_manage(op="list", params={"node_path": "/root/RootNode/NodeName"})
        → Only if spec includes signal connections.
          Verify expected signals are declared on the live node.
          Uses live tree path with /root/ prefix.

[ ] 5. scene_save()
        → Explicit save of currently open scene — no path param.
          batch_execute does NOT auto-save. Unsaved scene = invisible to Script + QC agents.
          After save: filesystem_manage(op="read_text", params={"path": "res://..."})
          to confirm file landed on disk (non-empty response = saved).

[ ] 6. Build node_inventory from scene_get_hierarchy output — NOT from the input spec
        → node_inventory is a READ of what was created.
          If a node name differs from the plan, the inventory reflects reality.

[ ] 7. node_inventory format rules:
        → Root node: "node_path": "$"  (dollar sign only)
          Direct child: "node_path": "$Sprite2D"
          Nested child: "node_path": "$Parent/Child"
          NEVER: "/root/NodeName" or "$/NodeName" — wrong formats for node_inventory

[ ] 8. Invoke base skill headless verification gate
        → project_run(autosave=False) + logs_read()
          Must see clean run signature before reporting success.
```

---

## batch_execute Rules

- Always use `batch_execute` for multi-node scenes. No individual `node_create` calls.
- Inside `batch_execute`, use plugin command names: `create_node`, `set_property`, `attach_script`, `delete_node`
- Node paths inside `batch_execute` use live tree format: `/root/NodeName/Child`
- Create the script file (`script_create`) BEFORE `batch_execute` if `attach_script` is in the batch
- `batch_execute` stops on first error — partial writes may have landed; verify scene state after any failure
- Always call `scene_save()` after `batch_execute`

---

## MCP Agent Pitfalls Digest

| # | Pitfall | Guard |
|---|---------|-------|
| M1 | `scene_get_hierarchy` or `scene_save` called with a `scene_path` argument — these tools take no path param | Both operate on the currently open scene; use `scene_open` first |
| M2 | `scene_open` on a non-existent path fails — must create scene file first | `scene_manage(op="create")` before `scene_open` for new scenes |
| M3 | `batch_execute` using MCP tool names (`node_create`) instead of plugin names (`create_node`) | See command mapping table in godot-task-verify |
| M4 | `batch_execute` stops but scene not saved — other agents read stale file | `scene_save()` after every `batch_execute`; verify with `filesystem_manage` |
| M5 | PhysicsLayers string constants in MCP value fields — Godot receives a string, not an integer | Resolve all constants to integers before `batch_execute`: WORLD=1, PLAYER=2, MINIONS=3, HEROES=4, COLLECTIBLES=5, HITBOXES=6, HURTBOXES=7 |
| M6 | `node_get_properties` and `signal_manage` called without `/root/` prefix — wrong results | Use `/root/NodeName` (not `/NodeName`) for these tools |

---

## Feedback Logging

This skill logs all invocations to `.claude/skills/godot-mcp-task/skill_runs.jsonl` for monitoring.

**At invocation start:**
```
from skill_logging import SkillLogger
logger = SkillLogger("godot-mcp-task", ".claude/skills/godot-mcp-task")
logger.log_invocation(agent="mcp", version="1.1", session_id=environ.get("CLAUDE_SESSION_ID"))
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
