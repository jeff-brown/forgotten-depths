# Lighting System

## Overview

The Forgotten Depths lighting system provides dynamic light sources that players can buy, light, and use to illuminate dark areas. Light sources burn over time and eventually deplete, creating an immersive atmosphere and gameplay mechanic.

## Features

### Light Sources

Three types of light sources are available:

1. **Torch** (3 gold)
   - Brightness: 0.6 (60% light)
   - Duration: 10 minutes (600 seconds)
   - Cannot be relit (burns out completely)
   - Cheap and readily available

2. **Candle** (2 gold)
   - Brightness: 0.3 (30% light)
   - Duration: 5 minutes (300 seconds)
   - Cannot be relit
   - Lightweight, minimal illumination

3. **Lantern** (30 gold)
   - Brightness: 0.8 (80% light)
   - Duration: 30 minutes (1800 seconds)
   - Can be refilled with lamp oil
   - Most expensive but most effective

4. **Flask of Lamp Oil** (8 gold)
   - Provides 30 minutes of fuel for lanterns
   - Not yet fully implemented (refilling mechanic)

## How It Works

### Room Lighting Calculation

Each room has a base `light_level` (0.0-1.0 or string like "bright", "dark", "dim"). The effective light level is calculated as:

```
effective_light = min(1.0, base_light_level + sum(lit_light_sources_brightness))
```

- Room with `light_level: 0.1` (very dark) + torch (0.6 brightness) = 0.7 effective light
- Multiple players with light sources stack (capped at 1.0)
- Colors (room descriptions, NPCs, items) are dimmed based on effective light level using RGB color gradients

### Burning Mechanic

- Light sources burn in real-time based on the game tick rate (default: 1 second per tick)
- Players receive warnings:
  - **1 minute remaining**: "Your torch flickers - it will burn out soon!"
  - **10 seconds remaining**: "Your torch is almost out!"
- When depleted:
  - Torches and candles are removed from inventory (turn to ash)
  - Lanterns remain but become unlit (need refueling)
  - Room light level updates immediately
  - Nearby players are notified

## Commands

### light <item>
Light a torch, lantern, or candle from your inventory.

**Usage:**
```
light torch
light lantern
light candle
```

**Requirements:**
- Item must be a light source
- Item must be unlit
- Item must have burn time remaining
- Lanterns must have oil

**Output:**
- Success: "You light the Torch. It illuminates the area around you."
- Already lit: "The Torch is already lit!"
- Depleted: "The Torch has burned out and can't be lit."
- Needs oil: "The Lantern needs oil. Use 'fill lantern' with lamp oil in your inventory."

### extinguish <item>
Put out a lit light source to conserve burn time.

**Usage:**
```
extinguish torch
extinguish lantern
```

**Output:**
- Success: "You extinguish the Torch. The light fades away."
- Not lit: "The Torch isn't lit."

### fill <item>
Fill a lantern with lamp oil to refuel it.

**Usage:**
```
fill lantern
refill lantern
```

**Requirements:**
- Item must be a light source that requires fuel (lanterns)
- Must have a Flask of Lamp Oil in your inventory
- Each flask provides 30 minutes (1800 seconds) of burn time
- Fuel is capped at the lantern's maximum duration (30 minutes)

**Output:**
- Success: "You fill the Lantern with lamp oil. It now has 30 minutes of fuel."
- No oil: "You don't have any lamp oil to fill it with."
- Doesn't need fuel: "The Torch doesn't need fuel."

## Inventory Display

Lit light sources show their status in inventory:

```
You are carrying:
  1. Torch (lit - 8m 32s)
  2. Lantern (unlit)
  3. Candle (lit - 2m 15s)
```

- **(lit - Xm Ys)** - Currently burning with time remaining
- **(unlit)** - Available to light

## Vendor

**Tom Hartwell** (General Store) sells:
- Torch: 3 gold
- Candle: 2 gold
- Lantern: 30 gold
- Flask of Lamp Oil: 8 gold

Location: General Store in Millhaven

## Gameplay Tips

1. **Stock up before dungeon delving**: Dark dungeons (light_level: 0.1-0.3) are nearly impossible to navigate without light
2. **Torches are economical**: For short explorations, torches provide good light at low cost
3. **Lanterns for long expeditions**: More expensive upfront but last 3x longer than torches
4. **Extinguish when not needed**: Save burn time by extinguishing in lit areas
5. **Multiple sources**: Carrying backup torches prevents being stranded in darkness
6. **Group benefits**: All players in a room benefit from each other's light sources

## Technical Implementation

### Files Modified

1. **data/items/tool.json** - Added torch, lantern, candle, lamp_oil items
2. **src/server/commands/command_handler.py** - Added light/extinguish commands and handlers
3. **src/server/game/world/world_manager.py** - Added `calculate_effective_light_level()` method
4. **src/server/core/async_game_engine.py** - Added `_update_light_sources()` to game loop
5. **data/npcs/shopkeeper_tom.json** - Added light sources to vendor inventory

### Item Structure

```json
{
  "torch": {
    "name": "Torch",
    "type": "tool",
    "weight": 1,
    "base_value": 2,
    "is_light_source": true,
    "properties": {
      "brightness": 0.6,
      "max_duration": 600,
      "can_relight": false,
      "fuel_type": "none"
    }
  }
}
```

### Instance Properties

When a light source is lit, these properties are added to the item instance:
- `is_lit`: boolean - Currently providing light
- `time_remaining`: int - Seconds of burn time left
- `_warned_60`: boolean - Whether 1-minute warning was shown
- `_warned_10`: boolean - Whether 10-second warning was shown

## Future Enhancements

1. **Light radius**: Different light sources could illuminate different sized areas
2. **Oil spill mechanic**: Dropping lamp oil could create slippery hazards or fire
3. **Magic light sources**: Spells or enchanted items that provide permanent light
4. **Darkness penalties**: Reduced accuracy/visibility in pitch black areas
5. **Light-based puzzles**: Rooms that require specific light levels to reveal secrets
6. **Wind mechanics**: Outdoor areas where wind can blow out candles/torches
7. **Colored light**: Different colored flames for atmosphere or puzzle mechanics

## Testing

To test the lighting system:

1. Start server: `python main.py`
2. Connect with Python client: `python src/client/terminal_client.py`
3. Buy a torch: `buy torch` (at Tom's General Store)
4. Light it: `light torch`
5. Check inventory: `inv` (should show "Torch (lit - 9m 59s)")
6. Go to a dark room (dungeon areas) and observe:
   - Room description becomes brighter
   - Colors shift from dim to more vibrant
   - When torch burns out, room becomes dark again
7. Test warnings by waiting ~9 minutes (or modify max_duration for faster testing)

### Testing Lantern Refilling

1. Buy a lantern and lamp oil: `buy lantern` and `buy lamp oil`
2. Try to light empty lantern: `light lantern` (should fail - needs oil)
3. Fill the lantern: `fill lantern`
4. Check inventory: lantern should show it has fuel
5. Light the lantern: `light lantern` (should succeed)
6. Extinguish to conserve fuel: `extinguish lantern`
7. Buy more oil and refill: `buy lamp oil` then `fill lantern` (fuel caps at 30 minutes)

## Known Issues

- Light sources in equipped slots don't provide light (only inventory items)
- No "drop lit torch" special behavior (could start fires)
