# Script Agent — Sonnet 4.6 Calibration Layer

**Model:** Claude Sonnet 4.6  
**Version:** 1.0  
**Focus:** Comprehensive GDScript, type safety, elaborate documentation

## Code Quality & Type Hints

- Always use type hints (func foo(x: int) -> String:).
- Add @export and @onready annotations with explanations.
- Document complex state transitions with detailed comments.
- Use enums for game states; include docstrings for each value.

## Pattern & Architecture

- Implement full signal connection logic (typed signal definitions).
- Plan state machine before writing; document transitions.
- Include error handling for all external API calls (MCP queries, file I/O).
- Design for extensibility: use base classes and composition where possible.

## Code Generation Best Practices

- Generate complete, tested scripts—no stubs.
- Include setup() / _ready() with full initialization.
- Write 100% complete signal handlers; no placeholder comments.
- Add unit test stubs for complex logic.

## Documentation & Explanation

- Include usage examples in docstrings.
- Document assumptions about scene hierarchy (which nodes must exist).
- Explain non-obvious logic with "why" comments, not just "what".
- Provide migration notes if replacing existing scripts.
