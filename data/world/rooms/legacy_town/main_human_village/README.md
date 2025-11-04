# Main Human Village

**Location**: `data/world/rooms/legacy_town/main_human_village/`  
**Room Count**: 13 rooms  
**Source**: Ether MUD Engine Town Area

## Overview

The primary human settlement, serving as the main hub for new adventurers.

This compact but well-organized village features all essential services:
- **North Plaza**: Central gathering area with access to the guild hall
- **South Plaza**: Southern hub with connections to various shops
- **Shops**: Equipment, armor, weapon, and magic shops
- **Tavern**: Village tavern with private upstairs room (max 2 players)
- **Temple**: Healing and resurrection services
- **Arena**: Combat training ground with entrance to dungeons below
- **Guild Hall**: Training facilities for advancing skills
- **Town Vaults**: Secure storage for valuables
- **Docks**: Lake access (connects to Lakeside Human Town)

The village is designed as a starting point, with the arena providing direct access to the dungeon system below.

## Room List

- legacy_town_66
- legacy_town_67
- legacy_town_89
- legacy_town_90
- legacy_town_91
- legacy_town_92
- legacy_town_93
- legacy_town_94
- legacy_town_95
- legacy_town_96
- legacy_town_97
- legacy_town_98
- legacy_town_99


## World Connections

Arena connects down to dungeon entrance (room 1). Docks connect to other settlements.

## Integration Status

**Status**: Not yet integrated into main game world

These rooms are converted and ready but not yet connected to the existing game world. Integration requires:

1. Mapping NPC vnums to actual NPC definitions
2. Creating area definition for Main Human Village
3. Implementing barrier/door systems
4. Creating connection points to/from existing world
5. Testing all shops and services

## Technical Details

- **Area ID Pattern**: `legacy_{town_type}`
- **Room ID Pattern**: `legacy_town_{number}`
- **NPC Pattern**: `legacy_npc_{vnum}`
- **Format**: Matches current game room JSON schema
- **Terrain**: All rooms marked as "town" terrain
