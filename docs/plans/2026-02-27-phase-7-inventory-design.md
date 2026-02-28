# Phase 7 Design: Inventory and Items (v0.17)

## 1. Overview
Phase 7 introduces a data-driven Inventory and Item system using a "Pure ECS" approach. Items are full ECS entities managed via unidirectional relationship tags (`IsCarrying`, `IsEquipped`). This architecture supports complex crafting (lineage), moddable anatomy (multi-headed species), and future building construction.

## 2. Architectural Principles (Power of 10 Compliance)
- **Defensive State Access:** All item lookups and relation queries must handle `None` or missing entities gracefully (Rule #5).
- **Deterministic Logic:** Item transactions (pickup/drop) are atomic operations with explicit success/failure returns (Rule #7).
- **Modular Functions:** The `ItemFactory` and `EquipSystem` will be decomposed into discrete functions under 120 lines (Rule #4).
- **No Hardcoding:** All item stats, costs, and behaviors are loaded from TOML templates (Hard Limit #4).

## 3. ECS Components & Relations

### Components (Data Containers)
- **`ItemIdentity`**: `id: str`, `name: str`, `description: str`, `template_origin: str`.
- **`ItemTag`**: Marker component for filtering.
- **`Quantity`**: `amount: int`, `max_stack: int` (for stackable consumables).
- **`Equippable`**: `slot_type: str` (e.g., "head", "hand", "torso").
- **`ItemStats`**: `attack_bonus: int`, `damage_bonus: int`, `protection: int`.
- **`Anatomy` (Actor-side)**: `available_slots: List[str]` (e.g., `["head", "head", "hand", "hand"]`).
- **`Lineage`**: Stores metadata of "parent" entities used in crafting for inherited properties.

### Relations (Graph Edges)
- **`IsCarrying` (Actor → Item)**: The primary inventory relationship. Items in this relation have no `Position` component.
- **`IsEquipped` (Actor → Item)**: Indicates the item is actively wielded/worn. Must be a subset of `IsCarrying`.

## 4. Data Flow & Systems

### The "Transaction" Pattern
- **Pickup (Floor → Inventory)**:
    1. Verify Actor is at Item's `Position`.
    2. Remove `Position` from Item.
    3. Add `IsCarrying` relation (Actor → Item).
- **Equip (Inventory → Slot)**:
    1. Verify Item is in `IsCarrying` relation.
    2. Check Actor's `Anatomy` for an open slot matching Item's `Equippable.slot_type`.
    3. Add `IsEquipped` relation (Actor → Item).
- **Drop (Inventory → Floor)**:
    1. Remove `IsEquipped` and `IsCarrying` relations.
    2. Add `Position` component to Item matching Actor's current `(x, y)`.

### Item Factory
The `ItemFactory` loads TOML blueprints and assembles entities. It supports **Lineage-Based Crafting** by merging component data from multiple templates (e.g., a "Hilt" template + "Banana" template = "Banana Scimitar").

## 5. Testing & Validation
- **Atomic Tests**: Verify that picking up an item correctly removes its spatial existence and adds the relation.
- **Anatomy Tests**: Ensure a two-headed NPC can equip two helmets but a one-headed PC cannot.
- **Stacking Tests**: Verify that adding a potion to an existing stack increments `Quantity` rather than creating a new entity.
