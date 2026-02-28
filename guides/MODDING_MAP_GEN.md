# Modder's Guide: Tuning Map Generation

ZEngine's world generation is driven by a multi-layered procedural system. This guide explains how to modify the environment, biomes, and handcrafted structures.

## 1. Tuning Biomes (`data/biomes.toml`)

Biomes are the broadest layer of world-gen. They are selected based on global **Temperature** and **Humidity** noise (0.0 to 1.0).

### Parameters:
| Key | Description |
| :--- | :--- |
| `temp_range` | `[min, max]` values (0.0–1.0) where this biome can appear. |
| `hum_range` | `[min, max]` values (0.0–1.0) for humidity. |
| `tree_density` | Probability (0.0–1.0) of a 'tree' tile spawning in wilderness. |
| `grass_density`| Probability of a 'grass' tile. |
| `water_density`| Probability of a 'water' tile. |
| `rubble_density`| Probability of a 'wall' (rubble) tile. |
| `colors` | RGB values for specific tile types (e.g., `grass = [30, 80, 30]`). |

**Example:** To make a "Frozen Forest," create a biome with a `temp_range` of `[0.0, 0.2]` and high `tree_density`.

---

## 2. Handcrafted Vignettes (`data/world/chunks/`)

Vignettes (Bespoke Chunks) are handcrafted ASCII "stamps" placed into the world via the **Regional Blueprint**.

### Creating a New Template:
1. Create a new `.toml` file in `data/world/chunks/`.
2. **Define the ID:** Must match the filename.
3. **The ASCII Map:** Use characters to define the layout:
   - `#` : Wall
   - `.` : Floor
   - `~` : Water
   - `+` : Door (Placeholder for interactable entity)
4. **Define Spawns:** lx/ly are *local* coordinates relative to the top-left of the ASCII stamp.

```toml
id = "my_custom_shrine"
name = "Hidden Shrine"
map = """
  ###  
  #.#  
  #+#  
"""
[[spawns]]
type = "item"
id = "consumables/healing_potion"
lx = 2
ly = 1
```

---

## 3. Global Engine Tuning (`world/generator.py`)

If you are comfortable with Python, you can tune the core engine constants in `WorldBiomeEngine` and `ChunkManager`:

- **Noise Scale:** In `WorldBiomeEngine.get_biome`, the `scale` variable (default `0.05`) determines how large biomes are. 
  - *Lower scale (0.01)* = Massive, continent-sized biomes.
  - *Higher scale (0.2)* = Small, patchy biomes.
- **POI Density:** In `ChunkManager._generate_chunk`, the `poi_count` (default `randint(1, 2)` per 4x4 region) determines how many settlements exist.
- **Road Frequency:** In `_generate_chunk`, the `rng.random() < 0.5` check determines how often roads appear next to settlements.

---
*Vignette revivification in progress (v0.23)*
