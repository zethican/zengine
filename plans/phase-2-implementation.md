# Phase 2 Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement core engine systems (Social Layer, Equilibrium, and ECS core) based on locked Phase 1 design contracts.

**Architecture:** Reactive ECS-based systems that communicate via a central EventBus. The Social Layer responds to combat events to drive reputation and stress, while Equilibrium manages world-state vitality and NPC migration.

**Tech Stack:** Python 3.14.3, Pydantic v2, python-tcod-ecs.

---

## Key Files & Context
- `engine/combat.py`: Contains the `EventBus` and `CombatEvent` base models.
- `engine/chronicle.py`: The already-implemented append-only journal.
- `engine/social_state.py`: (To be created) Will handle stress and reputation shifts.
- `engine/equilibrium.py`: (To be created) Will handle vitality and world-state dynamics.
- `COMPONENTS.md` & `SYSTEMS.md`: Canonical design contracts for Phase 2.

---

## Implementation Steps

### Task 1: Social State System (Stress Reaction)
**Files:**
- Create: `engine/social_state.py`
- Modify: `engine/combat.py` (replace no-op stubs)
- Test: `tests/test_social_state.py`

**Step 1: Write failing test for stress accumulation on damage**
- Import `SocialStateSystem` and `EventBus`.
- Subscribe to `EVT_ON_DAMAGE`.
- Assert stress increases proportionally to damage amount.

**Step 2: Implement SocialStateSystem and stress logic**
- Subscribe to `EVT_ON_DAMAGE`.
- Use `SocialComponent` to track stress (0.0–1.0).
- Formula: `stress += amount / 100.0`.

**Step 3: Verify and Commit**
- Run `pytest tests/test_social_state.py`.
- `git commit -m "feat: implement basic social stress reaction"`

### Task 2: Equilibrium Taper Formula
**Files:**
- Create: `engine/equilibrium.py`
- Test: `tests/test_equilibrium.py`

**Step 1: Implement compute_migration_risk**
- Use `EQUILIBRIUM_BASE_RESISTANCE = 40`.
- Formula: `taper_threshold = 40 + (living_count * vitality)`.
- Risk: `100 - taper_threshold`.

**Step 2: Verify and Commit**
- Run unit tests for flourishing, stable, and collapsing states.
- `git commit -m "feat: implement equilibrium migration risk formula"`

### Task 3: ECS Component Definitions
**Files:**
- Create: `engine/ecs/components.py`
- Test: `tests/test_ecs_core.py`

**Step 1: Define core components from COMPONENTS.md**
- `CombatVitals` (hp, max_hp, is_dead).
- `ActionEconomy` (action_energy, ap_pool).
- `Position` (x, y).

**Step 2: Verify and Commit**
- Ensure `python-tcod-ecs` registry can query these.
- `git commit -m "feat: define core ECS components"`

---

## Verification & Testing
- **Unit Tests:** Run `pytest tests/` after each task.
- **Smoke Tests:** Run `py engine/social_state.py` if implemented with main block.
- **Contract Check:** Verify against `SYSTEMS.md` dispatch order.
