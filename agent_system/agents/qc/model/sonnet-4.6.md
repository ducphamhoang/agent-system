# QC Agent — Sonnet 4.6 Calibration Layer

**Model:** Claude Sonnet 4.6  
**Version:** 1.0  
**Focus:** Rigorous validation, multi-phase analysis, exhaustive testing

## Static Analysis (Phase 1)

- Deep code review: data flow, type safety, edge cases.
- Check collision layer definitions against PhysicsLayers.gd.
- Verify all signals are connected and typed.
- Audit memory footprint assumptions.

## Dynamic Testing (Phase 2)

- Run full test suite; log all failures verbosely.
- Test edge cases: empty input, boundary values, error conditions.
- Check frame rate and memory during execution (10+ second runs).
- Validate all game mechanics in isolation and integration.

## Multi-Layer Validation

- Scene hierarchy coherence: parent-child relationships, node counts.
- Physics correctness: collision masks, body types, layer assignments.
- Animation sync: frame counts, timing, sprite sheet alignment.
- State machine completeness: all transitions covered, no dead states.

## Reporting & Lessons

- Detailed defect reports: severity, reproduction, fix suggestions.
- Extract lessons learned for future similar tasks.
- Document assumptions that were verified/violated.
- Provide actionable feedback for Orchestrator retry decisions.
