---
name: godot-orchestrator-gate
description: Orchestrator skill for task classification, pre-dispatch handoff validation, and post-result acceptance gate. Invoke before dispatching any sub-agent AND before accepting any agent result. Prevents wasted sub-agent calls and catches schema errors early.
---

# Godot Orchestrator Gate Skill

**Invoke at two moments:**
1. Before dispatching any sub-agent (Parts A + B)
2. Before accepting any agent result (Part C)

First: invoke `godot-task-verify` base skill.

---

## Part A: Task Classification

Classify before choosing a pipeline. Do NOT default to MCP → Script → QC for every task.

| Task type | Signal phrases | Pipeline |
|-----------|----------------|----------|
| `scene+script` | "create", "add entity", "new scene", "new hero", "new enemy" | MCP → Script → QC |
| `script-only` | "fix bug", "add method", "change logic", "update script" | Orchestrator gathers node_inventory via MCP reads → Script → QC |
| `scene-only` | "restructure nodes", "add child node", "configure collision" | MCP → QC |
| `pure-read` | "explain", "show me", "what does", "list", "describe" | Orchestrator handles directly; no sub-agents |

**For `script-only` tasks** — Orchestrator gathers node_inventory itself:
```
scene_open(path)
scene_get_hierarchy(depth=10)
→ build node_inventory from result
→ pass directly to Script Agent handoff (skip MCP Agent entirely)
```

**Query godot-docs before decomposing any task** involving unfamiliar Godot classes:
```
mcp__godot-docs__search(query="ClassName", mode="keyword")
mcp__godot-docs__search(query="conceptual question", mode="semantic")
```
If godot-docs returns no results for a class mentioned in the task: halt and ask user for clarification before building any handoff.

---

## Part B: Pre-Dispatch Handoff Validation

Before sending a handoff to any agent:

```
[ ] 1. editor_state() — readiness == "ready"
        → "importing": wait 10s, retry
        → "playing": project_manage(op="stop"), retry
        → "no_scene": open target scene if path known; escalate to user if unknown

[ ] 2. autoload_manage(op="list")
        → Confirm PhysicsLayers is registered (required for all collision config)
        → Confirm EventBus is registered (if any signals cross-scene boundaries)
        → Missing autoload = silent null crash at runtime; fix before dispatching

[ ] 3. schema_version == "1.0" in handoff
        → Version mismatch = schema contract broken; do not dispatch

[ ] 4. For MCP handoffs:
        → mcp_subtask.node_structure is non-empty
        → output_scene_path begins with res://
        → All collision_layer/collision_mask values use PhysicsLayers.LAYER_* names (not integers)
        → depends_on_tasks are all complete; if not: halt and list blocking tasks

[ ] 5. For Script handoffs:
        → node_inventory is present and non-empty
        → target_script_path begins with res://
        → target_script_path matches the script field on the root node in node_structure
```

---

## Part C: Post-Result Acceptance Gate

Before accepting any agent result and advancing the pipeline:

```
[ ] 1. result.schema_version == "1.0"
        → Mismatch: agent used wrong schema; do not advance

[ ] 2. result.task_id == handoff.task_id
        → Mismatch: result is from wrong task (context bleed or stale retry); do not advance

[ ] 3. result.status == "success"
        → "partial": treat as failure, route back
        → "failure": route per failure routing table below

[ ] 4. result.errors is empty
        → Any entry: treat as failure regardless of status field value

[ ] 5. result.files_created is non-empty; all paths begin with res://
        → filesystem_manage(op="read_text", params={"path": file_path})
          on each — confirm file exists on disk. Normalize bare paths: prepend res:// if missing.

[ ] 6. For MCP results only:
        → node_inventory is non-empty
        → Every node in handoff.mcp_subtask.node_structure appears in node_inventory by node_name
        → All node_path values use $ prefix: "$" for root, "$NodeName" for children
        → Root node entry has node_path == "$" exactly (not "$RootName")

[ ] 7. For Script results only:
        → methods_implemented contains every name from script_subtask.methods_required[*].name
        → signals_declared contains every signal from script_subtask.signals_to_declare

[ ] 8. For QC results only:
        → phase_1_result.status == "pass"   ← top-level errors[] is insufficient for QC
        → phase_2_result.status == "pass"   ← only if phase 2 was triggered
        → overall_status == "pass"
```

---

## Part D: Failure Routing Table

| Failure | Condition | Route to |
|---------|-----------|----------|
| MCP Agent | Scene structure wrong, node missing, collision layer invalid | MCP Agent (retry with error context) |
| Script Agent | GDSCRIPT_SYNTAX_ERROR | Script Agent (retry) |
| Script Agent | MISSING_NODE_INVENTORY | Verify MCP completed; re-check node_inventory |
| Script Agent | INVALID_NODE_PATH | MCP Agent (regenerate scene/node_inventory) |
| QC Phase 1 | scene_structure, collision_layers | MCP Agent |
| QC Phase 1 | gdscript_syntax, signal_declarations, onready_refs | Script Agent |
| QC Phase 2 | Runtime errors, null refs, signal failures | Script Agent |
| Any | 3rd consecutive failure same task | Escalate to user with full audit trail |

**Retry handoff must include prior context:**
```json
"retry_context": {
  "attempt": 2,
  "prior_errors": ["describe what failed"],
  "files_already_created": ["res://path/to/file.tscn"],
  "nodes_already_in_scene": ["NodeName1", "NodeName2"]
}
```
