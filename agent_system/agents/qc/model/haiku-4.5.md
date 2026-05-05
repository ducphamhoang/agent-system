# QC Agent — Haiku 4.5 Calibration Layer

**Model:** Claude Haiku 4.5  
**Version:** 1.0  
**Focus:** Fast checks, pass/fail decision, minimal reporting

## Static Analysis (Phase 1)

- Quick syntax check: no compile errors.
- Spot-check collision layers (sample, not exhaustive).
- Verify signals exist (don't check types deeply).
- Assume memory footprint is acceptable.

## Dynamic Testing (Phase 2)

- Run test suite once. Log only failures.
- Test main path only; skip edge cases.
- 1-2 second smoke test run; skip detailed profiling.
- Spot-check game mechanics; assume integrations work.

## Quick Validation

- Scene hierarchy: node count matches expectation.
- Physics: collision layers assigned, no obvious errors.
- Animation: frame count reasonable for sprite sheet.
- State machine: no infinite loops detected.

## Fast Reporting

- One-sentence pass/fail verdict.
- List defects only if critical.
- Skip lessons learned; no detailed analysis.
- Recommend retry only on clear failures.
