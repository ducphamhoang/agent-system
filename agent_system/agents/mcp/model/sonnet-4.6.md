# MCP Agent — Sonnet 4.6 Calibration Layer

**Model:** Claude Sonnet 4.6  
**Version:** 1.0  
**Focus:** Deep scene reasoning, hierarchical planning, multi-pass validation

## Reasoning & Scene Understanding

- Analyze scene requirements deeply before node creation.
- Validate collision layers, physics bodies, and animation states upfront.
- Document node hierarchy rationale: why each parent-child relationship.
- Use Sonnet's spatial reasoning for complex node layouts.

## Planning & Batch Operations

- Plan full scene graph before MCP calls (don't iterative-add nodes).
- Batch node_create calls by hierarchy level: root → containers → entities → colliders.
- Wait for all creations before setting properties.
- Pre-compute all property values; avoid subsequent corrections.

## Validation & Quality

- Validate against PhysicsLayers.gd collision registry before physics setup.
- Check animation frame counts vs. sprite sheet dimensions.
- Verify shader compatibility with GL Compatibility renderer.
- Document each node's role in scene handoff to Script Agent.

## Tool Efficiency

- Use scene_get_hierarchy to understand existing structure before modifications.
- Batch property sets by node: one set_property call per node with multiple props.
- Capture screenshots after major hierarchy changes for documentation.
- Log all node IDs to memory for Script Agent reference.
