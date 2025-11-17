# Starter Areas (No Rune Required)

**Import Order**: 1
**Recommended Level Range**: 1-15
**Total Areas**: 10
**Total Rooms**: 657

## Description

Beginning areas accessible to all players. Includes classic dungeon progression (Levels 1-3) and surface exploration (Forest, Mountains, Swamp).

## Intended Progression Path

**IMPORTANT**: All starter areas connect to **Town** (negative room IDs -90 to -98), which was NOT included in the World1 export. Towns use negative room numbers and are in a separate data structure.

The actual progression:

```
Dungeon Level 1 (51 rooms, IDs 1-51)
        ↓ (exit: up → room -98)
      TOWN (negative room IDs)
        ↑ (exit: northeast → room -90)
Mountains Area (51 rooms, IDs 183-233)
        ↓
Mountains Cave Area (82 rooms, IDs 3015-3096)
        ↓
Forest Area (90 rooms, IDs 234-323) - CENTRAL HUB
     /       \
Tower Area   Swamp Area
(74 rooms)   (99 rooms)
             /
    Ruined Town (20 rooms)
         |
    Cellar Area (59 rooms)
```

Then continue: Dungeons 2 → 3, which stay underground.

### Connection Notes

**External Connections (to Town - negative room IDs):**
- Dungeon Level 1 (room 1) has exit **up → room -98** (TOWN)
- Mountains Area (room 183 "outside the town gates") has exit **northeast → room -90** (TOWN)
- Forest Area (likely also connects to TOWN)

**Internal Structure:**
- **Dungeon Chain**: Level 1 ↔ Level 2 ↔ Level 3 (classic vertical progression)
- **Mountain Chain**: Mountains → Caves → Forest (surface exploration)
- **Forest Hub**: Central hub with 4 connections (Mountains, Caves, Tower, Swamp)
- **Swamp Branch**: Forest → Swamp → Ruined Town → Cellar
- **Tower Branch**: Forest → Tower (returns to Forest)

## Areas in This Tier

### Classic Dungeon Progression (182 rooms)
- **Dungeon Level 1** (51 rooms) - `21_dungeon_level_1.json` - Starting dungeon
- **Dungeon Level 2** (56 rooms) - `20_dungeon_level_2.json` - Mid dungeon
- **Dungeon Level 3** (75 rooms) - `17_dungeon_level_3.json` - Deep dungeon

### Mountain Wilderness (133 rooms)
- **Mountains Area** (51 rooms) - `22_mountains_area.json` - Mountain paths
- **Mountains Cave Area** (82 rooms) - `16_mountains_cave_area.json` - Cave system

### Forest Hub & Branches (342 rooms)
- **Forest Area** (90 rooms) - `15_forest_area.json` - **Central hub** (4 connections)
- **Tower Area** (74 rooms) - `18_tower_area.json` - Tower dungeon
- **Swamp Area** (99 rooms) - `14_swamp_area.json` - Swamp wilderness
- **Ruined Town** (20 rooms) - `25_ruined_town.json` - Abandoned settlement
- **Cellar Area** (59 rooms) - `19_cellar_area.json` - Underground cellars

## Migration Notes

### Import Order
Import this tier **first** - required for all players to start the game.

### Recommended Sub-Order
1. **Dungeon Levels 1-3** - Core tutorial content
2. **Mountains + Caves** - Secondary starting path
3. **Forest Area** - Central hub (connects everything)
4. **Tower + Swamp chains** - Exploration branches

### Access Control
No rune checks required - accessible to all players.

### Critical Migration Notes

**Town Connections (Negative Room IDs):**
- Town already exists in the game with **negative room IDs**
- Two starter areas have exits to Town:
  - **Dungeon Level 1** (room 1): exit up → room -98 (Town)
  - **Mountains Area** (room 183): exit northeast → room -90 (Town)
- Exit room IDs may need adjustment later to match actual town room IDs

**No Missing Connections:**
- Dungeons, Mountains, and Forest do NOT directly connect to each other
- They ALL connect through the central Town hub (negative room IDs)
- This is the **correct design** - town is the central meeting point

### Connection Verification

**Internal connections (all verified):**
- ✓ Dungeon Level 1 ↔ Dungeon Level 2
- ✓ Dungeon Level 2 ↔ Dungeon Level 3
- ✓ Mountains Area ↔ Mountains Cave Area
- ✓ Mountains Cave Area ↔ Forest Area
- ✓ Mountains Area ↔ Forest Area
- ✓ Forest Area ↔ Tower Area
- ✓ Forest Area ↔ Swamp Area
- ✓ Swamp Area ↔ Ruined Town
- ✓ Ruined Town ↔ Cellar Area

**External connections (to Town with negative room IDs):**
- ✓ Dungeon Level 1 (room 1) → Town (room -98)
- ✓ Mountains Area (room 183) → Town (room -90)

### Testing Checklist
- [ ] All rooms load correctly
- [ ] Dungeon 1 → Town connection works (exit up to room -98)
- [ ] Mountains → Town connection works (exit northeast to room -90)
- [ ] Dungeon 1-2-3 internal progression works
- [ ] Mountains → Caves → Forest chain works
- [ ] Forest hub connects to all 4 neighbors (Mountains, Caves, Tower, Swamp)
- [ ] Tower branch: Forest → Tower → Forest
- [ ] Swamp branch: Forest → Swamp → Ruined Town → Cellar
- [ ] NPCs spawn correctly in lairs
- [ ] Triggers function (teleporters, traps, etc.)
- [ ] (Later) Update town exit room IDs if needed

---

*Generated from World1 export data*
