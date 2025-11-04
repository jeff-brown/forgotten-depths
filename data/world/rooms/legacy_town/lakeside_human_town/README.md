# Lakeside Human Town

**Location**: `data/world/rooms/legacy_town/lakeside_human_town/`  
**Room Count**: 21 rooms  
**Source**: Ether MUD Engine Town Area

## Overview

A larger, more developed human settlement on the shores of the great lake.

This sprawling town offers enhanced services and multiple districts:
- **Multiple Plazas**: North, South, and East plazas connected by tree-lined paths
- **Advanced Shops**: Higher quality equipment, armor, weapons, and magic items
- **Inn**: Full-service inn with rooms and dining
- **Temple**: Religious services and healing
- **Arena**: Combat training facility
- **Docks**: Active port with multiple ship captains for travel
- **Path Network**: Scenic tree-lined paths connecting all areas
- **Sewer Access**: Grated entrance to town sewers (room 844)

The town features improved service levels (level 2) at most shops, indicating better quality goods and services.

## Room List

- legacy_town_68
- legacy_town_69
- legacy_town_70
- legacy_town_71
- legacy_town_72
- legacy_town_73
- legacy_town_74
- legacy_town_75
- legacy_town_76
- legacy_town_77
- legacy_town_78
- legacy_town_79
- legacy_town_80
- legacy_town_81
- legacy_town_82
- legacy_town_83
- legacy_town_84
- legacy_town_85
- legacy_town_86
- legacy_town_87
- legacy_town_88


## World Connections

Docks connect to other lakeside settlements. Sewers provide underground access (room 844).

## Integration Status

**Status**: Not yet integrated into main game world

These rooms are converted and ready but not yet connected to the existing game world. Integration requires:

1. Mapping NPC vnums to actual NPC definitions
2. Creating area definition for Lakeside Human Town
3. Implementing barrier/door systems
4. Creating connection points to/from existing world
5. Testing all shops and services

## Technical Details

- **Area ID Pattern**: `legacy_{town_type}`
- **Room ID Pattern**: `legacy_town_{number}`
- **NPC Pattern**: `legacy_npc_{vnum}`
- **Format**: Matches current game room JSON schema
- **Terrain**: All rooms marked as "town" terrain
