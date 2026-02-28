# DESIGN_VARIABLES.md

**All configurable parameters live here.** Never hardcode silently — log everything.

---

## Core Loop & Turn Mechanics

| Variable                 | Value        | Type  | Notes                                                          |
| ------------------------ | ------------ | ----- | -------------------------------------------------------------- |
| `ENERGY_THRESHOLD`       | 100.0        | float | Turn eligibility threshold; speed accumulates into this pool    |
| `AP_POOL_SIZE`           | 100          | int   | Resets each turn; 1:1 mapped to ENERGY_THRESHOLD for symmetry  |
| `MOVEMENT_ALLOCATION`    | ceil(100/speed) | formula | AP cost per tile; speed-derived; ceiling rounding prevents gaming |

---

## Inventory & Items (Phase 7–9)

| Variable                 | Value        | Type  | Notes                                                          |
| ------------------------ | ------------ | ----- | -------------------------------------------------------------- |
| `AP_COST_PICKUP`         | 10           | int   | AP cost to pick up an item from the floor                      |
| `AP_COST_DROP`           | 10           | int   | AP cost to drop an item from inventory to the floor            |
| `AP_COST_EQUIP`          | 20           | int   | AP cost to equip a carried item                                |
| `AP_COST_CRAFT`          | 30           | int   | AP cost to combine two items                                   |
| `AP_COST_USE`            | 20           | int   | AP cost to use a consumable item                               |

---

## Social Layer (Catch-up & Epistemology)

| Variable                 | Value        | Type  | Notes                                                          |
| ------------------------ | ------------ | ----- | -------------------------------------------------------------- |
| `SOCIAL_CATCHUP_TICKS`   | 5            | int   | Background ticks per session boundary; simulates passage of time |
| `CATCHUP_TRANSITION_CAP` | 1            | int   | Max state transitions per node per catch-up cycle; preserves player agency |

---

## Combat Resolution (2d8 Bell Curve)

| Variable                 | Value        | Type  | Notes                                                          |
| ------------------------ | ------------ | ----- | -------------------------------------------------------------- |
| `CRIT_THRESHOLD`         | 16           | int   | Natural 2d8 roll for critical hit (max)                        |
| `FUMBLE_THRESHOLD`       | 2            | int   | Natural 2d8 roll for fumble (min)                              |
| `BASE_HIT_DC`            | 10           | int   | Default defense class when no modifier provided               |
| `COMBAT_ROLL_DISPLAY`    | "category"   | str   | "category" (fumble/miss/graze/hit/crit) OR "raw" (roll numbers) |

---

## Disposition & Stress System

| Variable                 | Value        | Type  | Notes                                                          |
| ------------------------ | ------------ | ----- | -------------------------------------------------------------- |
| `REPUTATION_OSTRACIZATION` | -0.3       | float | Disposition threshold below which NPC refuses interaction      |
| `REPUTATION_COOPERATION` | 0.4          | float | Disposition threshold for mutual aid behaviors                 |
| `STRESS_EXODUS_THRESHOLD` | 0.7         | float | Party stress ratio; exceeds → NPC considers leaving            |
| `STRESS_PASSIVE_DECAY_RATE` | 0.0       | float | Per-tick decay; 0.0 = no passive decay (stress sticky)        |
| `STRESS_DELTA_COMBAT`    | per event    | config | Configured in TOML ability/grammar tables; not hardcoded      |

---

## Equilibrium & Conduction (NPC Mood Spread)

| Variable                 | Value        | Type  | Notes                                                          |
| ------------------------ | ------------ | ----- | -------------------------------------------------------------- |
| `EQUILIBRIUM_BASE_RESISTANCE` | 40       | int   | Base resistance to mood conduction; range 20–80               |
| `CONDUCTION_COEFFICIENT` | 0.3          | float | Strength of mood spread per unit; 0.0 disables               |
| `CONDUCTION_ATTENUATION` | 0.6          | float | Decay per distance; range 0.1–0.9                             |

---

## Chronicle & Epistemology

| Variable                 | Value        | Type  | Notes                                                          |
| ------------------------ | ------------ | ----- | -------------------------------------------------------------- |
| `CHRONICLE_SIGNIFICANCE_MIN` | 2         | int   | Minimum significance score to be inscribed; range 1–5         |
| `CHRONICLE_CONFIDENCE_WITNESSED` | 0.9   | float | Base confidence when player was present                       |
| `CHRONICLE_CONFIDENCE_FABRICATED` | 0.4  | float | Base confidence for out-of-session NPC rumors                 |

---

## Stub Fields (MVP Phase Restrictions)

| Variable                 | Status              | Reason                                                         |
| ------------------------ | ------------------- | -------------------------------------------------------------- |
| `VITALITY_CACHE`         | NOT_IMPLEMENTED     | Stub field exists; do NOT read or write during MVP            |
| `cached_vitality`        | NOT_IMPLEMENTED     | Phase 2+ feature; currently unused                             |

---

## Notes for Agents

- **AP and Movement:** Confirmed values from CONTEXT.md phase 0 → 1 handoff
- **Social Catch-up:** Tested against narrative feel; single-transition cap prevents uncontrolled world shift
- **Stress System:** No passive decay; stress sticks until explicitly addressed (narrative pressure design)
- **Conduction:** Maps to Caves of Qud emotional resonance model; affects encounter tone without forcing outcomes
- **Chronicle Config:** Extensible; significance and confidence per event type in Phase 4+ TOML files

---

## Undocumented Parameters Encountered

| Variable                 | Value        | Type  | Notes                                                          |
| ------------------------ | ------------ | ----- | -------------------------------------------------------------- |
| `SOCIAL_AUTOPOP_COOLDOWN`| 2000         | int   | Ticks between NPC-initiated dialogue pop-ups                    |
| `RARITY_MAGIC_CHANCE`    | 0.25         | float | Chance for an item to roll Magic tier (1 affix)                |
| `RARITY_RARE_CHANCE`     | 0.05         | float | Chance for an item to roll Rare tier (2 affixes)               |
| `SOCIAL_ENGAGEMENT_RANGE`| 3            | int   | Standard distance for NPC social approach                      |
| `SOCIAL_PROACTIVE_RANGE` | 6            | int   | Social range for merchants or NPCs with rumors                 |
| `MODIFIER_DEFAULT_DURATION`| 100        | int   | Default tick duration for unnamed modifiers                    |
| `FACTION_CONDUCTION_FACTOR`| 0.5        | float | Percentage of reputation shift that propagates to parent faction|
