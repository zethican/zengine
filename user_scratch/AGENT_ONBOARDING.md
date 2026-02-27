# ZEngine — Agent Onboarding Script

**Use this prompt to open every new ZEngine session.**
Paste it as your first message before describing any task.

---

## Opening Ritual

```
You are working on ZEngine — a social ecology simulator / party-based roguelike
in Python 3.14.3. Design is complete. Implementation has not begun.

Before responding, read the following files in order:
  1. CONTEXT.md              — canonical project state and all design decisions
  2. engine/combat.py        — canonical event bus, modifier system, combat stub
  3. DESIGN_VARIABLES.md     — all configurable parameters with current defaults

Then confirm you have read them by stating:
  - Current phase
  - The three open threads that must be resolved before Phase 1
  - One agent hard limit you will not violate this session

Do not write any code until I describe a task.
```

---

## What You Are Working With

| File                  | Role                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------- |
| `CONTEXT.md`          | Single source of truth. All decisions live here.                                      |
| `engine/combat.py`    | Canonical implementation stub. EventBus, Combatant, Modifier, CombatEngine.           |
| `DESIGN_VARIABLES.md` | Every configurable parameter. Log undocumented values here — never hardcode silently. |
| `FUTURE.md`           | Post-MVP deferred systems. Do not architect toward these during MVP phases.           |
| `DO_NOT_TOUCH.md`     | Locked files for current phase. Check before editing anything.                        |

---

## Hard Limits (memorize these)

1. No direct inter-layer state mutation — all Dungeon→Social changes via Chronicle events.
2. No Chronicle entry modification after inscription — corrections are new entries.
3. No vitality caching during MVP — stub field present, must not be read or written.
4. No hardcoded ability or event behavior — TOML data and tag subscriptions only.
5. No NumPy outside spatial layer and lighting.
6. Grammar tables are never agent-generated — read only.
7. Undocumented design variables go in `DESIGN_VARIABLES.md` — never silent defaults.
8. Post-MVP systems: note in `FUTURE.md`, implement the simpler MVP version.
9. Never mutate `Combatant.hp` directly — always `Combatant.apply_damage()`.
10. Never use raw strings as event keys — use `EVT_*` constants from `engine/combat.py`.
11. Never instantiate a global `EventBus` — pass the instance at construction.

---

## Closing Ritual

```
Before ending this session:
  1. Note any new design variables encountered in DESIGN_VARIABLES.md.
  2. Note any post-MVP considerations in FUTURE.md.
  3. Confirm the current phase gate status has not changed,
     or describe what changed and why.
  4. Update CONTEXT.md if any decisions were made or closed doors added.
```

---

## Phase Status (as of v0.2)

**Current phase: 0**
Exit criteria: CONTEXT.md committed, opening/closing templates tested.

Open threads blocking Phase 1:

- Social Layer catch-up tick count at session boundary
- AP pool size
- Movement allocation (speed-derived distance)