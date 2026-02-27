# STATE_OF_THE_PROJECT.md

**Last Updated:** 2026-02-27 (Phase 1 close-out)

---

## Quick Status Snapshot

| Aspect | Status | Details |
| --- | --- | --- |
| **Current Phase** | 2 (implementation) | Phase 1 contracts complete and locked |
| **Phase 1 Contracts** | ✅ Final | COMPONENTS.md, EVENTS.md, SYSTEMS.md — locked |
| **Design Freeze** | ✅ Locked | All major decisions in CONTEXT.md; closed doors documented |
| **Next Immediate Task** | Phase 2 implementation | engine/chronicle.py first |
| **Active Agent** | Ready | Phase 2 unblocked; no outstanding blockers |

---

## What Exists Right Now

### Documentation (complete)
- ✅ CONTEXT.md — Single source of truth (updated to Phase 2)
- ✅ AGENT_ONBOARDING.md — Agent ritual templates and hard limits
- ✅ DESIGN_VARIABLES.md — All 20 parameters with confirmed values
- ✅ FUTURE.md — 20+ post-MVP deferred items
- ✅ DO_NOT_TOUCH.md — Phase 1 locks applied; Phase 2 targets listed

### Phase 1 Contracts (final — locked)
- ✅ COMPONENTS.md — ECS component taxonomy (8 layers, all fields typed)
- ✅ EVENTS.md — Event catalog and typed payloads (10 EVT_* constants, full dispatch sequence)
- ✅ SYSTEMS.md — System dispatch contracts (16 systems, canonical ordering, Chronicle schema)

### Code (minimal — Phase 0 stub)
- ✅ engine/combat.py — Canonical stub (EventBus, Combatant, Modifier, CombatEngine, FoeFactory)
  - AP_POOL_SIZE = 100 ✅
  - MOVEMENT_ALLOCATION = "ceil(100/speed)" ✅
  - Smoke test passes ✅

### Archive (not in tree)
- 📦 user_scratch/ — Raw content dump (ZEngine_Manifest_v0_2.pdf, MCP_GUIDE.md, etc.)

---

## Phase Gates & Blockers

### Phase 0 → 1 (Complete)
**Status:** ✅ CLOSED

- ✅ Social Layer catch-up ticks → `SOCIAL_CATCHUP_TICKS = 5`
- ✅ AP pool size → `AP_POOL_SIZE = 100`
- ✅ Movement allocation → `ceil(100/speed)` formula confirmed

### Phase 1 Exit Gate
**Status:** ✅ PASSED

- ✅ COMPONENTS.md — complete and peer-reviewed
- ✅ EVENTS.md — complete and peer-reviewed
- ✅ SYSTEMS.md — complete and peer-reviewed
- ✅ Pre-flight audit complete (docstring, CONTEXT.md, moral_weight/resilience gap closed)
- ✅ DO_NOT_TOUCH.md locks applied

### Phase 2 Entry Gate
**Status:** ✅ OPEN — no blockers

**Phase 2 carry-in items (resolve during implementation):**
- `EventPayload.data` typed dicts per event type (Phase 1 hardening task; deferred)
- `moral_weight` and `resilience` in `disposition` component — confirm writer isolation in social_state.py
- Combat roll display toggle — Phase 6 UI pass; default = "category"

---

## Hard Limits (Must Never Violate)

1. No direct inter-layer state mutation — all Dungeon→Social via Chronicle events
2. No Chronicle entry modification after inscription — corrections are new entries
3. No vitality caching during MVP — stub field exists but unused
4. No hardcoded ability behavior — TOML data + tag subscriptions only
5. No NumPy outside spatial layer and lighting
6. Grammar tables read-only — never agent-generated
7. All undocumented parameters → DESIGN_VARIABLES.md (never silent defaults)
8. Post-MVP systems → note in FUTURE.md, implement simpler MVP version
9. Never mutate `Combatant.hp` directly — only via `apply_damage()`
10. Never use raw strings as event keys — use `EVT_*` constants
11. Never global `EventBus` — pass instances at construction

---

## Design Variables (Confirmed)

| Variable | Value | Notes |
| --- | --- | --- |
| ENERGY_THRESHOLD | 100.0 | Turn eligibility threshold |
| AP_POOL_SIZE | 100 | Resets each turn; matches ENERGY_THRESHOLD scale |
| MOVEMENT_ALLOCATION | ceil(100/speed) | AP per tile; ceiling rounding; speed-derived |
| SOCIAL_CATCHUP_TICKS | 5 | Session boundary advance |
| CATCHUP_TRANSITION_CAP | 1 | Max state transitions per node per session boundary |
| CRIT_THRESHOLD | 20 | d20 natural roll |
| FUMBLE_THRESHOLD | 1 | d20 natural roll |
| BASE_HIT_DC | 10 | Default defense class when no stat provided |
| COMBAT_ROLL_DISPLAY | "category" | fumble/miss/graze/hit/crit |
| REPUTATION_OSTRACIZATION | -0.3 | Threshold; configurable |
| REPUTATION_COOPERATION | 0.4 | Threshold; configurable |
| STRESS_EXODUS_THRESHOLD | 0.7 | float 0.0–1.0 |
| STRESS_PASSIVE_DECAY_RATE | 0.0 | 0.0 = no passive decay |
| EQUILIBRIUM_BASE_RESISTANCE | 40 | Range 20–80 |
| CONDUCTION_COEFFICIENT | 0.3 | 0.0 disables conduction |
| CONDUCTION_ATTENUATION | 0.6 | Per distance unit; range 0.1–0.9 |
| CHRONICLE_SIGNIFICANCE_MIN | 2 | Minimum inscription threshold; range 1–5 |
| CHRONICLE_CONFIDENCE_WITNESSED | 0.9 | |
| CHRONICLE_CONFIDENCE_FABRICATED | 0.4 | |
| VITALITY_CACHE | NOT_IMPLEMENTED | Stub field; do not read or write MVP |

---

## Recent Activity

### Session: 2026-02-27 (Phase 1 Contracts + Close-out)

**Completed:**
- Drafted COMPONENTS.md — 8-layer ECS component taxonomy with full field types, lifecycle, read/write isolation
- Drafted EVENTS.md — 10 EVT_* constants, TypedDict payloads, canonical turn resolution sequence
- Drafted SYSTEMS.md — 16 systems, dispatch ordering, Chronicle entry schema, Equilibrium Taper formula, Legacy Conversion sequence
- Pre-flight audit: closed 4 issues (combat.py docstring, CONTEXT.md stale state, moral_weight/resilience gap in disposition, DO_NOT_TOUCH.md phase update)
- All Phase 1 contracts locked in DO_NOT_TOUCH.md
- Established hourly STATE_OF_THE_PROJECT.md checkpoint (scheduled task: zengine-project-checkpoint)

**Next:** Phase 2 implementation — begin with engine/chronicle.py

### Session: 2026-02-27 (Project Scaffolding)

**Completed:**
- Read all user_scratch files (CONTEXT, AUTHORITATIVE_GROUND_TRUTH, combat.py, MCP_GUIDE, AGENT_ONBOARDING)
- Created root documentation structure (CONTEXT.md, AGENT_ONBOARDING.md, DESIGN_VARIABLES.md, FUTURE.md, DO_NOT_TOUCH.md)
- Copied canonical combat.py stub to engine/combat.py
- Created Phase 1 contract placeholders (COMPONENTS.md, SYSTEMS.md, EVENTS.md)

---

## Upcoming Milestones

### Phase 2 (Active)
- [ ] engine/chronicle.py — Chronicle write/query interface (append-only JSONL)
- [ ] engine/social_state.py — Social State schema and transition logic
- [ ] engine/equilibrium.py — Vitality, Taper formula, conduction
- [ ] engine/ecs/ — ECS component and system definitions
- [ ] ui/renderer.py — tcod terminal renderer
- [ ] Wire combat system into full encounter loop
- [ ] Smoke tests pass for all Phase 2 systems

### Phase 3 (Post-Phase-2)
- [ ] world/generator.py — procedural dungeon/wilderness generation
- [ ] Encounter density driver (legacy actor spawning)

### Phase 4+ (Content & Polish)
- [ ] data/ directory (abilities, grammar, templates, chronicle significance)
- [ ] Sessions management (chronicle.jsonl, spatial_snapshot.toml)

---

## Known Post-MVP Deferrals

See `FUTURE.md` for full list. Key items:
- AP carry-over / reaction economy
- Real-time Social Layer daemon (replace session-boundary tick)
- Vitality caching system
- Chronicle active epistemology (confidence weight reconciliation)
- EventPayload.data typed dicts per event type
- Tag-based casting (Wildermyth model)
- Faction hooking, gift economy, ancestor worship
- Cover / line-of-sight bonus mechanics
- Cross-session Chronicle persistence

---

## How to Use This File

- **Opening new session:** Read this first for 30-second status
- **Mid-session:** Skim to verify phase assumptions
- **Closing session:** Note any progress; file updates automatically every hour

---

## Automated Update Log

| Timestamp | Change | Trigger |
| --- | --- | --- |
| 2026-02-27 16:00 | Initial scaffold | Project setup complete |
| 2026-02-27 (end of session) | Phase 1 close-out — contracts final, locks applied, Phase 2 open | Pre-flight audit complete |

(Auto-updated by scheduled task every hour; user can also request manual refresh)
