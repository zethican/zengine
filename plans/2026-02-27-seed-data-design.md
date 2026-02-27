# ZEngine "Minimum Viable Encounter" (MVE) Seed Data Design

**Date:** 2026-02-27
**Topic:** Data-Driven System Integration (Phase 2)

## Overview
This design establishes the minimal TOML-based data set required to transition ZEngine from hardcoded stubs to a data-driven core. It follows Hard Limit #4: "No hardcoded ability or event behavior."

## Directory Structure
```text
data/
├── abilities/
│   └── basic_attack.toml
├── entities/
│   ├── hero_standard.toml
│   └── foe_skirmisher.toml
└── world/
    └── starting_rumors.toml
```

## Schema Definitions

### 1. `abilities/basic_attack.toml`
- `id`: "basic_attack"
- `name`: "Basic Attack"
- `ap_cost`: 50
- `damage_die`: 6
- `damage_bonus`: 2
- `target_type`: "single"

### 2. `entities/hero_standard.toml` / `foe_skirmisher.toml`
- `id`: "hero_standard"
- `name`: "Standard Hero"
- `hp`: 30
- `speed`: 10.0
- `archetype`: "Standard"
- `abilities`: ["basic_attack"]

### 3. `world/starting_rumors.toml`
- `rumors`: [
    { `id`: "pol_keep", `name`: "The Obsidian Keep", `type`: "dungeon", `sig`: 5 },
    { `id`: "pol_camp", `name`: "Hidden Seeker Camp", `type`: "encampment", `sig`: 2 }
  ]

## Integration Logic
- **Ability Lookup:** `action_validator_system` reads `ap_cost` from TOML.
- **Entity Hydration:** `FoeFactory` loads stats from TOML to populate ECS components.
- **World Seeding:** `ChunkManager` initializes with rumors from the manifest.

## Success Criteria
- [ ] `action_validator_system` correctly rejects an attack if TOML `ap_cost` > current `ap_pool`.
- [ ] `FoeFactory` generates a `Combatant` with correct HP/Speed from a TOML template.
- [ ] `ChunkManager` resolves one of the two starting rumors during exploration smoke tests.
