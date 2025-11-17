# World1 Migration Plan

**Generated**: November 16, 2025
**Total Areas**: 25
**Total Rooms**: 4,064
**Status**: Ready for migration

## Overview

This document provides a complete migration plan for importing World1 areas into Forgotten Depths. All areas have been analyzed, organized by rune requirement, and documented with connection information.

## Preparation Complete

✅ **Extracted** all 4,065 rooms from 27 World1 export files
✅ **Clustered** rooms into 25 thematic areas based on manual zone assignment
✅ **Analyzed** connections between areas (exits, teleporters, rune gates)
✅ **Documented** rune progression system (6 tiers: no rune, white, yellow, green, blue, violet)
✅ **Organized** area files into rune-based directories with migration notes

## Directory Structure

All area files organized in: `config/temp/world1_areas/`

```
0_no_rune_starter/     (10 areas, 657 rooms)   - Priority 1: Core starter content
1_white_rune/          (3 areas, 546 rooms)    - Priority 2: First progression gate
2_yellow_rune/         (2 areas, 342 rooms)    - Priority 3: Mid-level content
3_green_rune/          (1 area, 500 rooms)     - Priority 4: Labyrinth challenge
4_blue_rune/           (6 areas, 852 rooms)    - Priority 5: High-level content
5_violet_rune/         (3 areas, 1,167 rooms)  - Priority 6: End-game content
```

Each directory contains:
- Area JSON files ready for import
- README.md with migration notes and testing checklists
- Connection information and rune requirements

## Migration Order

### Phase 1: Starter Content (Priority 1)
**Directory**: `0_no_rune_starter/`
**Areas**: 10
**Rooms**: 657

Import order within tier:
1. Dungeon Level 1 (51 rooms) - Starting point
2. Dungeon Level 2 (56 rooms)
3. Dungeon Level 3 (75 rooms)
4. Mountains Area (51 rooms) - Connects to town
5. Mountains Cave Area (82 rooms)
6. Forest Area (90 rooms) - Central hub
7. Tower Area (74 rooms)
8. Swamp Area (99 rooms)
9. Ruined Town (20 rooms)
10. Cellar Area (59 rooms)

**Critical Notes**:
- Dungeons and Mountains connect to existing Town (negative room IDs -98, -90)
- Forest Area is central hub with 4 connections
- All areas form connected network

### Phase 2: White Rune Content (Priority 2)
**Directory**: `1_white_rune/`
**Areas**: 3
**Rooms**: 546

1. Sewers Area (178 rooms)
2. Desert Area (101 rooms)
3. Stoneworks Area (267 rooms)

**Implementation Notes**:
- Define white_rune item in `data/items/quest_items.json`
- Implement rune check at area boundaries
- Add visual indicators for rune-gated exits

### Phase 3: Yellow Rune Content (Priority 3)
**Directory**: `2_yellow_rune/`
**Areas**: 2
**Rooms**: 342

1. Flagstone Area (299 rooms)
2. Flagworks Area (43 rooms)

**Connection**: Flagstone connects to Cellar (starter area)

### Phase 4: Green Rune Content (Priority 4)
**Directory**: `3_green_rune/`
**Areas**: 1
**Rooms**: 500

1. Labyrinth Area (500 rooms)

**Special Handling**:
- Entrance from Tunnel Area (Blue Rune)
- **No normal exit** - requires teleporter or quest escape
- May need to implement escape mechanism before import

### Phase 5: Blue Rune Content (Priority 5)
**Directory**: `4_blue_rune/`
**Areas**: 6
**Rooms**: 852

1. Natural Caverns Area (313 rooms)
2. Sweltering Passages Area (143 rooms)
3. Ledge Area (136 rooms)
4. Granite Corridor Area (127 rooms)
5. Valley Area (100 rooms) - Hub for this tier
6. Tunnel Area (33 rooms) - Entrance to Labyrinth

**Network Structure**: Valley acts as hub connecting this tier

### Phase 6: Violet Rune Content (Priority 6)
**Directory**: `5_violet_rune/`
**Areas**: 3
**Rooms**: 1,167 (28.7% of world!)

1. Stone Passages Areas (832 rooms) - Mega-dungeon
2. Deep Forest Area (199 rooms)
3. Elven Area (136 rooms) - Connects back to Mountains (starter)

**Special Handling**:
- Stone Passages has 173 triggers (likely teleporter network)
- Elven Area may be end-game town/services
- Contains over 1/4 of all world content

## Technical Implementation

### 1. Room Import Process

Each area JSON file contains complete room data:

```json
{
  "area_id": 1,
  "area_name": "Dungeon Level 1",
  "terrain": "DUNGEON1",
  "_access_requirements": {
    "rune": "no_rune",
    "description": "Starter areas, no rune required"
  },
  "rooms": [
    {
      "room_id": 1,
      "short_description": "You are inside the dungeon entrance.",
      "long_description": "...",
      "exits": [...],
      "npcs": {...},
      "lairs": [...],
      "triggers": [...]
    }
  ]
}
```

### 2. Rune System Implementation

#### Define Rune Items

Create in `data/items/quest_items.json`:

```json
{
  "white_rune": {
    "name": "White Rune",
    "type": "quest_item",
    "description": "A white crystalline rune that resonates with magical energy.",
    "flags": ["no_drop", "no_sell", "quest_item"]
  },
  "yellow_rune": {...},
  "green_rune": {...},
  "blue_rune": {...},
  "violet_rune": {...}
}
```

#### Access Control

Update world loading to check rune requirements:

```python
def can_enter_area(player, area):
    """Check if player can enter rune-gated area."""
    required_rune = area.get('_access_requirements', {}).get('rune')

    if required_rune == 'no_rune' or required_rune is None:
        return True

    return player.has_item(required_rune)
```

#### Exit Blocking

Update movement handler:

```python
if not can_enter_area(player, target_area):
    rune = target_area['_access_requirements']['rune']
    rune_name = rune.replace('_', ' ').title()
    return f"A shimmering barrier blocks your path. You sense it requires a {rune_name} to pass."
```

### 3. Data Conversion

Room data is already in correct format, but may need:

1. **Terrain mapping**: World1 terrain types → game terrain types
2. **NPC/Mob references**: Update mob IDs to match game's mob definitions
3. **Item references**: Update item IDs to match game's item definitions
4. **Trigger conversion**: Convert World1 triggers to game trigger format

### 4. World Graph Integration

After importing rooms:

```python
# Rebuild world graph to include new rooms
world_manager.world_graph.rebuild()

# Validate all connections
world_manager.world_graph.validate()

# Check for isolated rooms
isolated = world_manager.world_graph.find_isolated_rooms()
```

## Testing Strategy

### Per-Tier Testing

For each tier (0-5), verify:

1. **Room Loading**
   - All rooms load without errors
   - Room descriptions display correctly
   - Terrain types recognized

2. **Exit Connectivity**
   - All exits within tier connect properly
   - Inter-tier exits show rune requirement
   - No broken exits

3. **NPCs and Lairs**
   - Lairs spawn correct mobs
   - Mob counts match lair definitions
   - NPC dialogue works

4. **Triggers**
   - Teleporters function correctly
   - Traps trigger appropriately
   - Treasure spawns work

5. **Rune Gates**
   - Players without rune are blocked
   - Players with rune can pass
   - Error messages display correctly

### Tier-Specific Testing

**Tier 0 (No Rune)**:
- Dungeon 1 → Town connection (room -98)
- Mountains → Town connection (room -90)
- Forest hub connects all 4 neighbors

**Tier 3 (Green Rune - Labyrinth)**:
- Exit mechanism implemented
- Players can escape after completion

**Tier 5 (Violet Rune)**:
- Stone Passages teleporter network (173 triggers)
- Elven Area services functional

## Room ID Ranges by Tier

| Tier | Rune | Room ID Ranges | Notes |
|------|------|----------------|-------|
| 0 | None | 1-501, 3015-3096 | Starter content, scattered ranges |
| 1 | White | 844-1191 | Sewers, Desert, Stoneworks |
| 2 | Yellow | 502-843 | Flagstone areas |
| 3 | Green | 1464-1963 | Labyrinth only |
| 4 | Blue | 2100-2815 | Volcanic/underground network |
| 5 | Violet | 3097-4064 | End-game (includes mega-dungeon) |

## Data Files Reference

| File | Purpose |
|------|---------|
| `config/temp/world1_areas/*/README.md` | Per-tier migration notes |
| `config/temp/world1_areas/*/*.json` | Area data files (25 files) |
| `config/temp/world1_areas/areas_index.json` | Master area index |
| `docs/WORLD1_RUNE_PROGRESSION.md` | Rune system documentation |
| `docs/WORLD1_AREA_CONNECTIONS.md` | Connection analysis |
| `docs/WORLD1_COMPLETE_ANALYSIS.md` | Full zone analysis |

## Rollback Plan

If issues arise during migration:

1. **Database Backup**: Before each tier import, backup `data/mud.db`
2. **Room ID Tracking**: Keep list of imported room IDs per tier
3. **Rollback Script**: Delete rooms by ID range if needed
4. **World Graph Rebuild**: Rebuild after rollback

## Success Criteria

Migration is complete when:

- ✅ All 4,064 rooms imported and loadable
- ✅ All inter-area connections working
- ✅ Rune gate system functional
- ✅ NPCs and lairs spawning correctly
- ✅ All triggers functioning
- ✅ World graph validates without errors
- ✅ Players can navigate all accessible areas
- ✅ No isolated or unreachable rooms

## Post-Migration Tasks

1. **Balance Review**: Check mob levels and loot for each area
2. **Quest Integration**: Add quests that reward runes
3. **Rune Distribution**: Place runes in appropriate locations
4. **NPC Population**: Add quest givers, vendors, trainers
5. **Loot Tables**: Customize drops for each area
6. **Level Ranges**: Set recommended levels per area
7. **Area Descriptions**: Enhance area flavor text
8. **Teleporter Network**: Verify Stone Passages internal teleporters

## Migration Script Template

```python
#!/usr/bin/env python3
"""
Import World1 areas into Forgotten Depths.
"""

import json
from pathlib import Path

def import_tier(tier_number, world_manager):
    """Import all areas from a specific tier."""
    tier_dir = Path(f'config/temp/world1_areas/{tier_number}_*').glob('*.json')

    for area_file in tier_dir:
        with open(area_file, 'r') as f:
            area_data = json.load(f)

        # Import each room
        for room in area_data['rooms']:
            world_manager.add_room(room)

    # Rebuild world graph
    world_manager.world_graph.rebuild()

    # Validate
    world_manager.world_graph.validate()

# Import in order
import_tier(0, world_manager)  # Starter
import_tier(1, world_manager)  # White rune
# ... etc
```

## Timeline Estimate

| Phase | Tier | Areas | Estimated Time | Notes |
|-------|------|-------|----------------|-------|
| 1 | 0 | 10 | 2-3 days | Setup, testing, town connections |
| 2 | 1 | 3 | 1 day | Rune system implementation |
| 3 | 2 | 2 | 0.5 day | Straightforward |
| 4 | 4 | 6 | 1 day | Do before green (dependency) |
| 5 | 3 | 1 | 1 day | Labyrinth exit mechanism |
| 6 | 5 | 3 | 2 days | Large areas, teleporter network |

**Total Estimated Time**: 7-9 days of development + testing

## Notes

- Areas are **ready for import** - all analysis and organization complete
- Room data is in **correct format** - minimal conversion needed
- **Rune system** needs implementation before importing gated tiers
- **Town connections** already exist (negative room IDs)
- **Labyrinth exit** mechanism needs design/implementation
- **Stone Passages teleporters** need testing (173 triggers)

---

**Migration plan completed**: November 16, 2025
**Ready to begin**: Phase 1 (Starter Content Import)
