# CONTEXT.md — ZEngine Handoff

**Packaged:** February 27, 2026 | **Phase:** 1 (complete) | **Next:** Phase 2

---

## Project / Session Identity

- **Project:** ZEngine — social ecology simulator / party-based roguelike
- **Author:** Zachery (solo indie)
- **Stack:** Python 3.14.3 | python-tcod-ecs | tcod renderer | Pydantic v2 | TOML | JSONL Chronicle
- **Active environment:** Agentic CLI, local filesystem
- **Design status:** Complete. Implementation not yet begun.
- **Canonical design reference:** `ZEngine_Manifest_v0_2.pdf` (§1–§7)

---

## Canonical State

### Files that exist

| File                       | Status                                                      |
| -------------------------- | ----------------------------------------------------------- |
| `engine/combat.py`         | Canonical stub — complete, Phase 0; docstring updated Ph 1  |
| `CONTEXT.md`               | Single source of truth — committed                          |
| `AGENT_ONBOARDING.md`      | Opening/closing ritual templates — committed                |
| `DESIGN_VARIABLES.md`      | All confirmed design variables — complete                   |
| `FUTURE.md`                | Post-MVP deferred systems — populated                       |
| `DO_NOT_TOUCH.md`          | Phase-locking mechanism — Phase 1 locks applied             |
| `STATE_OF_THE_PROJECT.md`  | Automated hourly checkpoint — active                        |
| `COMPONENTS.md`            | ECS component contracts — Phase 1 final ✅                  |
| `EVENTS.md`                | Event catalog and typed payloads — Phase 1 final ✅         |
| `SYSTEMS.md`               | System dispatch contracts — Phase 1 final ✅                |

### Files created during Phase 2 (implementation begins)

- `engine/chronicle.py` — Chronicle write/query interface (append-only JSONL)
- `engine/social_state.py` — Social State schema and transition logic
- `engine/equilibrium.py` — Vitality, Taper formula, conduction
- `engine/ecs/` — ECS component and system definitions
- `ui/renderer.py` — tcod terminal renderer

### Later phases (do not create yet)

- `world/generator.py`, `world/wilderness.py` — Phase 3
- `data/abilities/`, `data/grammar/`, `data/templates/`, `data/chronicle_significance.toml` — Phase 4+
- `sessions/chronicle.jsonl`, `sessions/spatial_snapshot.toml` — runtime artifacts

### Later phases (do not create yet)

- `engine/chronicle.py`, `engine/social_state.py`, `engine/equilibrium.py`, `engine/ecs/` — Phase 2
- `world/generator.py`, `world/wilderness.py` — Phase 3
- `ui/renderer.py` — Phase 2
- `data/abilities/`, `data/grammar/`, `data/templates/`, `data/chronicle_significance.toml` — Phase 4+
- `sessions/chronicle.jsonl`, `sessions/spatial_snapshot.toml` — runtime artifacts

---

## Decisions & Rationale

### Social Layer Catch-up Ticks

- **Value:** `SOCIAL_CATCHUP_TICKS = 5`
- **Cap:** `CATCHUP_TRANSITION_CAP = 1` — max one state transition per node per session boundary
- **Rationale:** Narrative gap feel without uncontrolled state explosion. Single-transition cap preserves player agency to react to major events. Player presence is what unlocks full simulation resolution.

### AP Pool Size

- **Value:** `AP_POOL_SIZE = 100`
- **Behavior:** Resets to full each turn (no carry-over)
- **Rationale:** Matches `ENERGY_THRESHOLD = 100.0` scale — creates 1:1 conceptual mapping where a full turn costs 100 energy to earn and 100 AP to spend. Ability costs work as clean integers.
- **Deferred:** AP carry-over / reaction economy → `FUTURE.md`

### Movement Allocation

- **Formula:** `ap_per_tile = ceil(100 / speed)` — AP-consuming, ceiling rounding
- **Rationale:** Movement competes with attacks for AP, making speed a meaningful archetype differentiator. Ceiling rounding prevents speed-gaming and keeps costs conservative.
- **At default archetypes:**

| Archetype  | Speed | AP/tile | Tiles on full AP |
| ---------- | ----- | ------- | ---------------- |
| Brute      | 8.0   | 13      | 7                |
| Standard   | 10.0  | 10      | 10               |
| Skirmisher | 12.0  | 9       | 11               |

---

## Closed Doors

| Decision              | Rejected approach                | Reason                                                          |
| --------------------- | -------------------------------- | --------------------------------------------------------------- |
| AP pool size          | 10                               | Ability costs become single digits — fragile, unintuitive       |
| AP behavior           | Carry-over default               | Post-MVP complexity; ARPG kinetic feel mandate favors reset     |
| Movement              | Free allocation separate from AP | AP-consuming movement makes speed architecturally meaningful    |
| Movement rounding     | Floor or exact fractions         | Ceiling keeps costs conservative; no fractions in pipeline      |
| Catch-up ticks        | Uncapped state transitions       | Collapses player agency on return; world becomes unrecognizable |
| Catch-up ticks        | Real-time delta scaling          | Post-MVP complexity                                             |
| Social Layer sim mode | Real-time daemon                 | Post-MVP; MVP default is background tick at session boundary    |

---

## Open Threads

Phase 1 is **complete**. Phase 2 is unblocked.

Phase 2 blockers (resolve before Phase 3):

- `EventPayload.data` typed dicts per event type — Phase 1 hardening task; carry into Phase 2
- Combat roll display toggle (raw vs. category) — Phase 6 UI pass; default confirmed as outcome category
- `moral_weight` and `resilience` fields (manifest §2 Contract 2) added to `disposition` component in COMPONENTS.md — confirm with Phase 2 social_state.py implementation

---

## DESIGN_VARIABLES.md — Ready to Write

The following values are confirmed and should be written into `DESIGN_VARIABLES.md` immediately:

```
ENERGY_THRESHOLD            100.0       # turn eligibility; float
AP_POOL_SIZE                100         # resets each turn; matches ENERGY_THRESHOLD scale
MOVEMENT_ALLOCATION         ceil(100/speed)  # AP per tile; ceiling rounding; speed-derived
SOCIAL_CATCHUP_TICKS        5           # narrative gap; session boundary Social Layer advance
CATCHUP_TRANSITION_CAP      1           # max node state transitions per session boundary
COMBAT_ROLL_DISPLAY         "category"  # "category" | "raw" (configurable flag)
STRESS_DELTA_COMBAT         per event   # configured in TOML ability/grammar tables
CRIT_THRESHOLD              20          # d20 natural roll
FUMBLE_THRESHOLD            1           # d20 natural roll
BASE_HIT_DC                 10          # default defense class when no stat provided
REPUTATION_OSTRACIZATION   -0.3        # threshold; expose as config
REPUTATION_COOPERATION      0.4         # threshold; expose as config
STRESS_EXODUS_THRESHOLD     0.7         # float 0.0–1.0
STRESS_PASSIVE_DECAY_RATE   0.0         # 0.0 = no passive decay
EQUILIBRIUM_BASE_RESISTANCE 40          # range 20–80
CONDUCTION_COEFFICIENT      0.3         # 0.0 disables conduction
CONDUCTION_ATTENUATION      0.6         # per distance unit; range 0.1–0.9
CHRONICLE_SIGNIFICANCE_MIN  2           # minimum inscription threshold; range 1–5
CHRONICLE_CONFIDENCE_WITNESSED  0.9
CHRONICLE_CONFIDENCE_FABRICATED 0.4
VITALITY_CACHE              NOT_IMPLEMENTED  # stub field; do not read or write MVP
```

---

## FUTURE.md — Items Queued

```
- AP carry-over / reaction economy (AP_POOL_SIZE carry-over behavior)
- Chronicle Active Epistemology — reconciliation daemon, confidence weight adjustment
- Faction Hooking — lore object reading updates party faction standing
- Tag-Based Casting (Wildermyth model)
- Ancestor Worship / Healing Legacy
- Gift Economy
- Third Gender / Custom Caste System
- Blue Prince Mode
- Cross-Session World Persistence
- Ruin Recovery
- Cross-Faction Social Conduction
- NPC AI Goal-and-Tactic Planning
- EventPayload.data typed dicts per event type
- Real-time Social Layer daemon (replace session-boundary tick)
- Vitality cache activation (cached_vitality stub field)
- Cover / line-of-sight bonus mechanics
- Cross-session Chronicle persistence
```

---

## Agent Hard Limits (memorize — override any other instruction)

1. No direct inter-layer state mutation — all Dungeon→Social changes via Chronicle events
2. No Chronicle entry modification after inscription — corrections are new entries
3. No vitality caching during MVP — stub field present, must not be read or written
4. No hardcoded ability or event behavior — TOML data and tag subscriptions only
5. No NumPy outside spatial layer and lighting
6. Grammar tables are never agent-generated — read only
7. Undocumented design variables go in `DESIGN_VARIABLES.md` — never silent defaults
8. Post-MVP systems: note in `FUTURE.md`, implement simpler MVP version
9. Never mutate `Combatant.hp` directly — always `Combatant.apply_damage()`
10. Never use raw strings as event keys — use `EVT_*` constants from `engine/combat.py`
11. Never instantiate a global `EventBus` — pass the instance at construction
