# ZEngine Entity Index

This guide provides a human-readable reference of all items, materials, NPCs, and bespoke world locations currently defined in the game data.

## 1. Weapons
| Name | ID | Description | Slot | Stats | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Iron Sword** | `iron_sword` | A standard-issue blade, notched but reliable. | hand | Atk:+2, Dmg:+3 | sword, metallic |

## 2. Materials
| Name | ID | Description | Tags |
| :--- | :--- | :--- | :--- |
| **Iron Ingot** | `iron_ingot` | A heavy bar of refined iron. | material, metallic, iron |
| **Wooden Plank** | `wooden_plank` | Sturdy timber, cut from a great-tree. | material, wooden |

## 3. Parts
| Name | ID | Description | Stats | Tags |
| :--- | :--- | :--- | :--- | :--- |
| **Iron Blade** | `iron_blade` | A sharp, straight length of iron. | Dmg:+2 | part, blade, metallic, iron |
| **Wooden Hilt** | `wooden_hilt` | A carved handle of wood. | Atk:+1 | part, hilt, wooden |

## 4. Recipes
| ID | Part A Tag | Part B Tag | Result Template |
| :--- | :--- | :--- | :--- |
| **Basic Sword** | `is_blade` | `is_hilt` | `weapons/iron_sword` |

## 5. Consumables
| Name | ID | Description | Effect | Tags |
| :--- | :--- | :--- | :--- | :--- |
| **Healing Potion** | `healing_potion` | A glass vial containing a shimmering red liquid. | heal | consumable, potion |

## 6. Attributes
| ID | Name | Modifier Affects |
| :--- | :--- | :--- |
| `might` | Might | Damage Bonus |
| `finesse` | Finesse | Attack Bonus, Defense Bonus (Evasion) |
| `resolve` | Resolve | Stress Resilience (TBD) |

## 7. NPCs
| Name | ID | Archetype | Key Attributes | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Player** | `hero_standard` | Standard | MGT:12, FIN:12, RES:10 | The primary social actor controlled by the user. |
| **Skirmisher** | `foe_skirmisher` | Skirmisher | FIN:14, RES:8 | A nimble combatant that relies on coordination and precision. |

## 8. Bespoke World Vignettes (Points of Light)
| Name | ID | Archetype | Unique Features |
| :--- | :--- | :--- | :--- |
| **The Wayfarer's Hearth** | `wayfarers_hearth` | Inn | Social Hub, Merchant, Multiple Loot Rooms. |
| **The Cracked Spire** | `cracked_spire` | Ruin | Tactical Tower, Bottleneck Chokes, Multiple Skirmishers. |
| **The Smithy's Refuse** | `smithy_refuse` | Workshop | Crafting Resource Cache, Industrial Yard. |
| **The Hermit's Root** | `hermits_root` | Sanctuary | Organic Moat, Healer NPC, Secluded Garden. |
| **The Lithic Circle** | `lithic_circle` | Mystic | Ancient Menhirs, Votive Offerings, High Discovery Value. |
| **The Hunter's Lean-to** | `hunters_lean_to` | Camp | Wilderness Waypoint, Survival Supplies, Tactical Perimeter. |

---
*Last Updated: 2026-02-27 (v0.23)*
