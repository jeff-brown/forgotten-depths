# Locked Door System

## Overview
The locked door system allows rooms to have exits that require specific keys to unlock.

## Implementation

### Room Configuration
Add a `locked_exits` property to room JSON files:

```json
{
  "id": "dungeon1_1",
  "title": "Dungeon Entrance",
  "exits": {
    "northeast": "dungeon1_13",
    "west": "dungeon1_14"
  },
  "locked_exits": {
    "northeast": {
      "required_key": "bronze_key",
      "description": "The enormous stone door is locked with a bronze mechanism."
    }
  }
}
```

### Key Properties
- **required_key**: The item ID of the key needed to unlock this exit
- **description**: A message shown to the player when they try to use a locked exit without the key

### Behavior

1. **Without the key**: When a player tries to move through a locked exit without the required key:
   ```
   The enormous stone door is locked with a bronze mechanism. You need a bronze key to unlock it.
   ```

2. **With the key**: When a player has the required key in their inventory:
   ```
   You use your bronze key to unlock the door and proceed northeast.
   ```
   - The door is permanently unlocked (for that game session)
   - The key remains in the player's inventory (not consumed)

### Example: Dungeon 1 Bronze Door

**Location**: dungeon1_1 (Dungeon Entrance)
- **Locked Exit**: northeast → dungeon1_13
- **Required Key**: bronze_key
- **Key Location**: dungeon1_14 (west from entrance)

**Player Flow**:
1. Enter dungeon at dungeon1_1
2. Try to go northeast → blocked by locked door
3. Go west to dungeon1_14
4. Pick up bronze_key
5. Return east to dungeon1_1
6. Go northeast → door automatically unlocks and player proceeds

## Adding More Locked Doors

To add a new locked door:

1. **Choose a room** and exit direction
2. **Add locked_exits** to the room JSON:
   ```json
   "locked_exits": {
     "south": {
       "required_key": "iron_key",
       "description": "A heavy iron gate blocks your way."
     }
   }
   ```

3. **Place the key** in a room by adding it to the items array:
   ```json
   "items": ["iron_key"]
   ```

4. **Ensure the key exists** in `data/items/items.json`

## Available Keys

The following keys are available in items.json:
- bronze_key
- brass_key
- copper_key
- iron_key
- silver_key
- electrum_key
- gold_key
- platinum_key
- pearl_key
- onyx_key
- jade_key
- ruby_key
- opal_key
- tigereye_key
- quartz_key
- topaz_key
- stone_key

## Code Files Modified

- `src/server/game/world/room.py`: Added locked_exits support
- `src/server/game/world/world_manager.py`: Load locked_exits from JSON
- `src/server/commands/async_commands.py`: Check for locked exits during movement
- `data/world/rooms/dungeon1/dungeon1_1.json`: First locked door example
- `data/world/rooms/dungeon1/dungeon1_14.json`: Bronze key location
