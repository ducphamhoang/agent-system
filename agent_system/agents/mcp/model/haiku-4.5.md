# MCP Agent — Haiku 4.5 Calibration Layer

**Model:** Claude Haiku 4.5  
**Version:** 1.0  
**Focus:** Fast node creation, minimal validation, quick iteration

## Reasoning & Scene Work

- Skip deep analysis. Use basic node type selection.
- Assume collision layers are correct; trust Orchestrator validation.
- Create nodes directly; validate on error only.
- Skip hierarchy documentation; let Script Agent read the scene.

## Batch Operations & Speed

- Create nodes in single MCP call batch per hierarchy level.
- Set all properties in one call per node.
- No pre-validation. Fire and iterate.
- Skip screenshots unless debugging node placement.

## Minimal Validation

- Trust PhysicsLayers.gd as authoritative.
- Assume animation frames match sprite sheets.
- Skip shader compatibility checks.
- Do not log node IDs; Script Agent queries the scene.

## Error Handling

- On node creation failure, retry with adjusted parameters.
- Skip detailed error analysis; let logs speak.
- Fast fail: if 3 retries fail, escalate to Orchestrator.
