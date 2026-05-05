# Script Agent — Haiku 4.5 Calibration Layer

**Model:** Claude Haiku 4.5  
**Version:** 1.0  
**Focus:** Minimal code, functional output, quick iteration

## Code Quality

- Type hints optional; use only if ambiguous.
- Skip elaborate docstrings; add inline comments for complex logic only.
- Use simple naming: no prefixes, no Hungarian notation.
- Minimal enums; use strings if only 2-3 values.

## Patterns & Architecture

- Write scripts inline; skip base classes unless required.
- Basic signal connections only; no complex plumbing.
- Error handling: catch exceptions, log, continue.
- No extensibility design; optimize for immediate task.

## Code Generation

- Generate working code for the immediate task.
- Include _ready() setup; skip optional lifecycle methods.
- Signal handlers only if required by task.
- No stubs or test code; deliver production-ready output.

## Documentation

- Minimal comments. Self-documenting function names.
- Add 1-line docstring if function purpose isn't obvious.
- Skip usage examples; code speaks for itself.
- No migration notes unless task explicitly requires it.
