## ZEngine Architectural Constraints (The Power of 10)

To ensure ZEngine remains lean, deterministic, and local-first, all code generation must strictly adhere to these rules:

1. **Iterative Logic Over Recursion:** Do not use recursion for anything *other than* FOV, pathfinding, or UI trees. Prefer explicit stacks or queues. This ensures stability in Python and makes the state easier to inspect.

2. **Deterministic Loops:** Every loop (especially in systems processing entities) must have a fixed upper bound or a safety break. No "while True" without an escape condition.

3. **No Dynamic Logic Injection:** Avoid using `exec()` or `eval()`. Engine behavior should be defined by data (JSON/Components) and explicit System logic.

4. **The 120-Line Function Limit:** No function or method should exceed 120 lines. If a feature (like a Map Generator) is complex, decompose it into smaller, discrete sub-steps.

5. **Defensive State Access:** Never assume an Entity or Component exists. Every `get` or `lookup` must handle `None` or missing keys explicitly to prevent runtime crashes.

6. **Smallest Possible Scope:** Declare variables at the point of use. Avoid global engine states; pass the `World` or `Context` object into functions that need it.

7. **Return Value Auditing:** Every function call must have its return value checked. If a function can fail, it must return a status or an Optional that is handled by the caller.

8. **Minimal Dependency Surface:** Prefer Python standard libraries or `tcod`. Avoid adding new external frameworks unless they are essential for local-first operation.

9. **Strict Type/Linter Compliance:** Code must be formatted for clarity and include type hints for core engine methods to assist with AI "self-correction" in future turns.

10. **Assertion-Backed Logic:** Use `assert` statements to verify engine assumptions during development (e.g., `assert tile_in_bounds(x, y)`).

**Audit Directive:** Perform a "Power of 10" audit on every code block before outputting. If the proposed change violates a rule (e.g., it creates a 100-line function), refactor it into compliance first.