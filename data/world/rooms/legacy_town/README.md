# Legacy Town Rooms

This directory contains 75 rooms converted from the Ether MUD Engine town area data, organized into four separate towns.

## Source

- Original file: `config/temp/town.json`
- Converted: 2025-10-14
- Format: Ether MUD Engine XML export → JSON

## Directory Structure

```
legacy_town/
├── main_human_village/        (13 rooms)
├── lakeside_human_town/        (21 rooms)
├── dwarven_underground_town/   (13 rooms)
└── elven_tree_town/            (28 rooms)
```

## Towns

### 1. Main Human Village (13 rooms)
Location: `main_human_village/`

The primary human settlement featuring:
- North and south plazas
- Shops: equipment, armor, weapon, magic
- Tavern with private rooms
- Temple
- Arena (connects to dungeon entrance)
- Guild hall with training facilities
- Town vaults

### 2. Lakeside Human Town (21 rooms)
Location: `lakeside_human_town/`

A larger lakeside settlement with:
- Multiple plazas (north, south, east)
- Expanded shop network
- Inn with lodging
- Temple
- Arena
- Docks (with ship captains)
- Path network connecting all areas

### 3. Dwarven Underground Town (13 rooms)
Location: `dwarven_underground_town/`

Underground dwarven settlement featuring:
- Central town square
- Four plaza fountains (NE, SE, SW, NW)
- Carved stone architecture
- Cavern setting with oil lamp lighting

### 4. Elven Tree Town (28 rooms)
Location: `elven_tree_town/`

Tree-based elven settlement (largest town with 28 rooms)

## Format Conversion

### Original Format (Ether MUD)
```json
{
  "room_id": -99,
  "short_description": "You're in the north plaza.",
  "long_description": "...",
  "room_flags": {"raw_value": 1, "decoded_flags": ["safe"]},
  "exits": [{"to_room": -92, "direction": "north"}],
  "npcs": {"vnums": [9, 10]}
}
```

### Converted Format
```json
{
  "id": "legacy_town_99",
  "title": "The North Plaza.",
  "description": "...",
  "area_id": "legacy_human_main",
  "exits": {"north": "legacy_town_92"},
  "is_safe": true,
  "npcs": ["legacy_npc_9", "legacy_npc_10"],
  "legacy_room_id": -99
}
```

## Key Features Preserved

- **Room connections**: All exits preserved with converted room IDs
- **Room flags**: Converted to boolean properties (is_safe, is_dark, is_tavern, etc.)
- **NPCs**: NPC vnums converted to legacy_npc_X format
- **Shops**: Shop types identified (equipment, armor, weapon, magic, inn, temple, etc.)
- **Doors**: Door mechanics preserved with barrier IDs and door types
- **Light levels**: Determined from room flags (bright, dim, dark)
- **Service levels**: Shop quality levels (0=none, 1=basic, 2=advanced, 3=premium)
- **Town affiliations**: Tracked via area_id
- **Terrain**: All marked as "town" terrain

## Door Types

The following door types are preserved:

- **HasRuneDoor**: Requires specific rune to pass
- **MinimumRuneDoor**: Requires minimum rune level
- **PrivateRoomDoor**: Limits number of players (e.g., inn rooms)
- **ItemKeyDoor**: Requires a key item to unlock
- **PuzzleDoor**: Requires puzzle/trigger to open
- **PromoteDoor**: Requires minimum level or class promotion

## Integration Notes

**These rooms are NOT yet connected to the existing game world.** To integrate:

1. Map NPC vnums to actual NPC definitions
2. Map barrier IDs to barrier system
3. Create area definitions for each town
4. Connect to existing world via designated entry/exit points
5. Implement door mechanics for special door types
6. Add room features and items as needed

## File Organization

Each town has:
- Individual room files: `legacy_town_XX.json`
- Index file: `_index.json` with room listing
- Room IDs follow pattern: `legacy_town_XX` (where XX is the absolute value of the original room_id)

## Next Steps

1. Create NPC definitions for legacy_npc_X references
2. Create area definitions for the four towns
3. Implement door/barrier system integration
4. Add connection points to existing world
5. Test room navigation and shop interactions
