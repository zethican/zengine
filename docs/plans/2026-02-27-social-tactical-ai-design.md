# Phase 10 Design: Socially-Aware Tactical AI (v0.19)

## 1. Overview
Phase 10 introduces a "Socially-Aware Tactical AI" driven by **Layered Influence (Dijkstra) Maps**. This system replaces rigid scripting with emergent behavior, where NPCs make decisions based on tactical threats, social affinities, and personal urgency (mental state). 

The goal is a fluid, social ecology where NPCs act as coherent actors who prioritize self-preservation and social relationships over simple "attack-nearest" logic.

## 2. Architecture: The Triple-Map System
The AI brain is divided into global heatmap layers and individual behavioral "mixers."

### 2.1 Global Influence Layers
The `InfluenceMapSystem` generates three global 0.0–1.0 NumPy arrays once per AI tick:
1.  **Threat Map:** Seeds are hostile entities (Reputation < -0.3). Values decrease with distance.
2.  **Affinity Map:** Seeds are friendly entities (Reputation > 0.4). Attracts allies to stay in formation.
3.  **Urgency Map:** Seeds are "Safety Zones" (high distance from threats) and "Resource Zones" (tiles with dropped consumables).

### 2.2 The Behavioral Mixer (BehaviorProfile)
Each NPC possesses a `BehaviorProfile` component that defines how it weights these maps:
- `threat_weight`: Negative values attract (Aggressive), positive values repulse (Cowardly).
- `affinity_weight`: High values cause the NPC to stay near allies.
- `urgency_weight`: Scales dynamically with `Stress` and `HP` loss.

### 2.3 Priority Fallbacks
To prevent "Local Optimum" loops (e.g., getting stuck behind a door), the AI includes a **Prioritization Layer**:
- If a primary goal (e.g., Threat) is unreachable, the AI triggers a **Fallback Routine**.
- The unreachable map's weight is zeroed, and a secondary map (Affinity or Ambient) is amplified to reposition the NPC.

## 3. Action Mapping & Utility
NPCs convert heatmap "Desire Scores" into ECS actions via a **Social Utility** calculation:
- **Move:** Utility = ΔHeat (Target vs. Current).
- **Consumable Use:** Triggered when the `Urgency` score at the current tile exceeds a threshold and a `Usable` item is in inventory.
- **Combat:** Validated against a **Relationship Mask** (Negative actions only for enemies, positive for allies).

## 4. Components & Data
- `BehaviorProfile`: Data-driven weights for map layers.
- `Disposition` (ECS Migration): Stores `reputation`, `stress`, and `resilience` as components.
- `PendingAction`: Canonical queue for the next resolution tick.

## 5. Narrative Inscription
High-utility decisions (e.g., "Ally chose to heal player over attacking") emit `CombatEvents` for the **Chronicle**. This ensures the AI's internal logic is transparent and contributes to the persistent world story.

## 6. Extensibility
The system is designed for "Plug-and-Play" expansion. Adding a new layer (e.g., `LootMap`) only requires:
1.  Adding a new NumPy layer to the global registry.
2.  Adding a `loot_weight` float to the `BehaviorProfile`.

---
*Status: Approved for Implementation (v0.19)*
