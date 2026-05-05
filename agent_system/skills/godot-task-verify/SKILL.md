---
name: godot-task-verify
description: Base verification skill for all Godot pipeline agents. Provides headless run gate, path format reference, editor readiness states, MCP tools quick-reference, and pitfalls digest. Invoke this before any other godot-* skill.
---

# Godot Task Verify — Base Skill

Every agent in the Godot pipeline invokes this skill first. It contains the shared verification gate, tool reference, and pitfalls all roles share.

---

> **Usage note:** Replace `{PROJECT_ROOT}` with the absolute path to your Godot project before deploying these prompts.

## Headless Verification Gate

Run this before reporting success on any task.

```
# MCP path (preferred — editor must be running):
project_run(autosave=False)     ← MUST use autosave=False; True overwrites the scene file
# Then: call editor_state() until readiness != "playing" (poll up to ~5 iterations), then:
logs_read(buffer="all", lines=100)

# Bash fallback (editor not running):
godot --headless --quit-after 3 --path {PROJECT_ROOT}
# macOS log:
cat ~/Library/"Application Support"/Godot/app_userdata/"My Demon"/logs/godot.log
# Linux log:
cat ~/.local/share/godot/app_userdata/"My Demon"/logs/godot.log
```

**Clean run** — at minimum these two lines, with zero `ERROR:` or `WARNING:` lines anywhere:
```
Godot Engine v4.6.x.stable.official...
[godot_ai game_helper] registered mcp capture...
```

Any `ERROR:` or `WARNING:` = **stop. do not report success. fix first.**

---

## Path Format Reference

Four distinct formats exist. Never mix them.

| Format | Example | Used in |
|--------|---------|---------|
| Scene path | `res://entities/heroes/Knight.tscn` | `scene_open`, `scene_save`, `script_create`, `filesystem_manage` |
| Godot tree path | `/root/RootNode/Child` | `node_get_properties(path=...)`, `node_create(parent_path=...)`, `set_property` inside `batch_execute` |
| Scene-relative path | `/RootNode/Child` | Accepted by some read-only tools (check TOOLS.md); `node_get_properties` and `signal_manage` require the full `/root/` tree path |
| GDScript NodePath | `$Child`, `%UniqueNode` | GDScript `@onready` declarations only — never in MCP calls |

**`batch_execute` uses `/root/` tree paths** — e.g. `/root/SkeletonHero/Sprite2D`. This is the live editor tree path, not the runtime autoload singleton. The `node_inventory` that MCP Agent outputs to Script Agent uses `$Sprite2D` (GDScript format) — a separate format used only in generated GDScript source code.

---

## Editor Readiness States

Check `editor_state().readiness` before any write operation.

| State | Action |
|-------|--------|
| `"ready"` | Proceed |
| `"importing"` | Wait 10s and re-check |
| `"playing"` | `project_manage(op="stop")` then re-check |
| `"no_scene"` | If target scene path is known: `scene_open(path)` then re-check. If unknown: STOP and escalate to user. |

---

## MCP Tools Quick-Reference

Authoritative source: `vendor/godot-ai/docs/TOOLS.md`. This table covers verification tools; add new rows as godot-ai gains new tools.

| Tool | Signature | Notes |
|------|-----------|-------|
| `editor_state` | `editor_state()` | Check readiness + current open scene |
| `scene_open` | `scene_open(path)` | Open scene before any read/write |
| `scene_get_hierarchy` | `scene_get_hierarchy(depth=10, offset=0, limit=100)` | Current open scene only — no scene_path param |
| `scene_save` | `scene_save()` | Current open scene only — no scene_path param; not automatic |
| `scene_manage` | `scene_manage(op, params)` — ops: `create`, `save_as`, `get_roots` | Use `create` to make a new scene before opening it |
| `node_get_properties` | `node_get_properties(path="/root/RootNode")` | Uses live tree path with `/root/` prefix |
| `node_find` | `node_find(query)` | Search by name/type in current open scene |
| `node_manage` | `node_manage(op, params)` — ops: `get_children`, `get_groups`, `delete`, `duplicate`, `rename`, `move`, `reparent` | Structural operations |
| `signal_manage` | `signal_manage(op="list", params={"node_path": "/root/Node"})` | Uses live tree path with `/root/` prefix |
| `script_manage` | `script_manage(op, params)` — ops: `read`, `find_symbols`, `detach` | Read source, introspect symbols, detach |
| `script_attach` | `script_attach(node_path, script_path)` | Dirties scene — call `scene_save` after |
| `script_patch` | `script_patch(path, anchor, content)` | `anchor` is a unique string in the file to locate the insertion point; follow with `find_symbols` to verify |
| `script_create` | `script_create(path, template, variables)` | Create new GDScript file |
| `batch_execute` | `batch_execute(commands)` | Stops on first error — partial writes may have landed; verify scene state after any failure |
| `project_run` | `project_run(autosave=False)` | ALWAYS pass `autosave=False` for verification |
| `logs_read` | `logs_read(buffer="all", lines=100)` | Read engine log |
| `filesystem_manage` | `filesystem_manage(op="read_text", params={"path": "res://..."})` | Non-empty response confirms save landed on disk |
| `autoload_manage` | `autoload_manage(op="list")` | Verify autoloads registered before relying on them |

**`batch_execute` command names** — use plugin names inside `batch_execute`, NOT MCP tool names. Only these four operations are listed; check `vendor/godot-ai/docs/TOOLS.md` for any additional supported commands:

| MCP tool | `batch_execute` command |
|----------|------------------------|
| `node_create` | `create_node` |
| `node_set_property` | `set_property` |
| `script_attach` | `attach_script` |
| `node_manage(op="delete")` | `delete_node` |

---

## Pitfalls Digest (Universal)

| # | Pitfall | Guard |
|---|---------|-------|
| P1 | `ext_resource` missing `id=` in `.tscn` — scene fails to parse | Every `[ext_resource]` needs `id="N"`; `ExtResource("N")` must match |
| P2 | UID mismatch — `uid=` in `.tscn` disagrees with `.uid` sidecar | Omit `uid=` if uncertain; path fallback is reliable |
| P3 | Mixed tabs/spaces in `.gd` — parser error on a valid-looking line | (Bash) `cat -A file.gd \| head -5`; tabs show as `^I`; match existing convention |
| P4 | `global_position` set before `add_child` — doesn't stick | Set `position` (local) before tree insertion; `global_position` only after |
| P5 | Physics state mutation in callback — `add_child`/`queue_free` in `_on_area_entered` | Use `call_deferred("add_child", node)` and `call_deferred("queue_free")` |
| P6 | `project_run()` without `autosave=False` — permanently writes in-memory mutations to `.tscn` | Always `project_run(autosave=False)` for verification runs |
| P7 | `AnimatedSprite2D.autoplay` fails silently on instantiated scenes | Always call `play("animation_name")` explicitly in `_ready()` |

Full list: `docs/guidelines/common-pitfalls.md`

---

## Reference Files

- `docs/guidelines/godot-best-practices.md` — component patterns, SOLID, naming conventions
- `docs/guidelines/common-pitfalls.md` — full runtime failure list behind the digest above
- `vendor/godot-ai/docs/TOOLS.md` — authoritative MCP tool signatures

---

## Extension Template

To add a new agent skill, create `.claude/skills/godot-<agent>-task/SKILL.md`:

```
---
name: godot-<agent>-task
description: <one line>
---

## Step 0: Load base skill
Invoke godot-task-verify before proceeding.

## Pre-task checklist
[ ] editor_state() — readiness == "ready"
[ ] ...

## Post-task checklist
[ ] Run base skill headless verification gate (project_run(autosave=False) + logs_read)
[ ] ...

## Pitfalls digest (2-3 items max)
```
