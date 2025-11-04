# Trap System

## Overview

The trap system adds danger and strategy to dungeon exploration. Players can encounter three types of traps that deal damage and apply ongoing effects. Traps can be detected and disarmed using the `search` and `disarm` commands.

## Trap Types

### 1. Poison Dart Trap
- **Damage**: 2d6 piercing
- **Effect**: Poison (1d4 damage per tick for 3 ticks)
- **Detection DC**: 12
- **Disarm DC**: 14
- **Description**: Small holes in the walls suggest hidden dart launchers
- **Trigger Message**: "A poisoned dart shoots out from the wall and strikes {target}!"

### 2. Pit Trap
- **Damage**: 3d6 falling
- **Effect**: Prone
- **Detection DC**: 10 (easiest to detect)
- **Disarm DC**: 16 (hardest to disarm)
- **Description**: The floor seems unstable in places
- **Trigger Message**: "{target} falls into a concealed pit trap!"

### 3. Flame Trap
- **Damage**: 4d6 fire
- **Effect**: Burning (1d6 damage per tick for 2 ticks)
- **Detection DC**: 14
- **Disarm DC**: 15
- **Description**: Scorch marks and the smell of oil suggest a fire hazard
- **Trigger Message**: "Flames erupt from the floor, engulfing {target}!"

## How Traps Work

**IMPORTANT**: Only rogues can search for and disarm traps. Other classes will receive an error message if they attempt these actions.

### Triggering

- Traps trigger automatically when a player **exits** a room (not when entering)
- This gives players a chance to search and disarm traps before leaving
- Each trap has a `trigger_chance` (typically 0.3-0.5)
- Players with high Dexterity have better odds of avoiding traps
- Formula: `trigger_chance = base_chance - (dex_modifier * 0.1)`
- Once triggered, a trap resets after `reset_time` seconds (default: 300 = 5 minutes)
- Disarmed traps stay disarmed permanently

### Detection

Use the `search` command to look for traps:
- Wisdom modifier affects success
- Roll: `1d20 + wisdom_modifier >= detection_dc`
- Detected traps are remembered for that room
- Must detect a trap before you can disarm it

### Disarming

Use the `disarm` command to disable a detected trap:
- Dexterity modifier affects success
- Roll: `1d20 + dex_modifier >= disarm_dc`
- **Success**: Trap is permanently disabled
- **Failure (roll 5+)**: Trap doesn't trigger, try again
- **Critical Failure (roll < 5)**: Trap triggers, dealing full damage!

### Ongoing Effects

Some traps apply damage-over-time effects:
- **Poison**: 1d4 damage per game tick for 3 ticks
- **Burning**: 1d6 damage per game tick for 2 ticks
- Effects update automatically each game tick
- Player receives notification when taking effect damage
- Effects wear off after duration expires

## Commands

**Class Restriction**: Only rogues can use the search and disarm commands.

### search
Search for traps in your current room.

**Usage:**
```
search
detect
```

**Class Requirement:** Rogue only

**Output:**
- Success: "You discover a flame trap mechanism beneath the floor tiles!"
- Already detected: "You've already found all the traps you can detect here."
- No traps found: "You search carefully but don't find any traps. (They might still be there!)"

### disarm
Attempt to disarm a detected trap.

**Usage:**
```
disarm
disable
```

**Class Requirement:** Rogue only

**Output:**
- Success: "You successfully disarm the Poison Dart Trap!"
- Failure: "You fail to disarm the Flame Trap, but it doesn't trigger."
- Critical Failure: "You fumble while disarming the trap! [trap triggers]"
- Not detected: "You haven't detected that trap yet. Try searching first."

## Room Configuration

Add traps to room JSON files in the `traps` array:

```json
{
  "id": "dungeon1_5",
  "title": "Huge Cavern",
  "description": "...",
  "traps": [
    {
      "type": "pit",
      "trigger_chance": 0.3,
      "damage_multiplier": 1.0,
      "reset_time": 300
    }
  ]
}
```

**Properties:**
- `type`: "poison_dart", "pit", or "flame"
- `trigger_chance`: Probability of triggering (0.0-1.0)
- `damage_multiplier`: Multiplier for base damage (optional, default 1.0)
- `reset_time`: Seconds before trap resets after triggering (optional, default 300)

## Current Trap Locations

- **dungeon1_5** (Huge Cavern): Pit trap (30% chance)
- **dungeon1_10** (Cave): Poison dart trap (40% chance)
- **dungeon1_20** (Cave): Flame trap (35% chance, 1.2x damage)

## Adding New Trap Types

To add a new trap type, edit `data/traps/traps.json` and add a new entry:

```json
{
  "traps": {
    "your_trap_name": {
      "name": "Display Name",
      "damage": "XdY+Z",
      "damage_type": "piercing|fire|cold|etc",
      "effect": "poison|burning|frozen|etc",
      "effect_duration": 3,
      "effect_damage": "1dX",
      "detection_dc": 12,
      "disarm_dc": 15,
      "description": "What players see when examining the room",
      "trigger_message": "Message when trap triggers on {target}",
      "search_message": "Message when trap is detected"
    }
  }
}
```

The trap system automatically loads all trap types from this file on startup.

## Technical Implementation

### Files Modified

1. **data/traps/traps.json** - Trap type definitions
   - All trap properties (damage, effects, DCs, messages)
   - Easily editable without code changes

2. **src/server/game/traps/trap_system.py** - Core trap system class
   - Loads trap definitions from JSON
   - Trigger checking logic
   - Search and disarm mechanics
   - Damage application
   - Ongoing effect updates

3. **src/server/core/async_game_engine.py** - Game loop integration
   - Line 24: Import TrapSystem
   - Line 49: Initialize trap_system
   - Line 273: Update trap effects each tick

4. **src/server/commands/command_handler.py** - Command handlers
   - Lines 589-595: Search and disarm command routing
   - Lines 1372-1421: Command handler implementations
   - Lines 452-453: Help text

5. **src/server/game/player/player_manager.py** - Movement integration
   - Lines 331-342: Trap trigger check on room exit

6. **data/world/rooms/dungeon1/*.json** - Example trap placements

## Gameplay Tips

1. **Play as a Rogue**: Only rogues can search for and disarm traps - essential for dungeon exploration!
2. **Search When You Enter**: Use `search` as soon as you enter a room to detect traps before leaving
3. **Disarm Before Moving**: Traps trigger when you exit a room, so disarm them first!
4. **High Wisdom**: Improves trap detection chances
5. **High Dexterity**: Improves both trap avoidance and disarming success
6. **Be Careful**: Critical failures on disarm attempts trigger the trap!
7. **Watch Your HP**: Ongoing poison/burning effects can stack up quickly
8. **Healing**: Visit a healer or use healing items to recover from trap damage

## Future Enhancements

1. **More Trap Types**: Acid spray, lightning, net traps, sleeping gas
2. **Trap Complexity**: Some traps require tools or multiple disarm attempts
3. **Environmental Hazards**: Traps that collapse ceilings or flood rooms
4. **Rogue Skills**: Class-specific bonuses for trap detection/disarming
5. **Trap Items**: Portable traps players can set themselves
6. **Multiple Traps**: Rooms with several different traps
7. **Trap Components**: Salvage parts from disarmed traps for crafting
8. **Trap Awareness**: Visual indicators when traps are detected
