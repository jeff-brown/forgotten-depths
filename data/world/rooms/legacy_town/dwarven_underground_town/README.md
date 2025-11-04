# Dwarven Underground Town

**Location**: `data/world/rooms/legacy_town/dwarven_underground_town/`  
**Room Count**: 13 rooms  
**Source**: Ether MUD Engine Town Area

## Overview

A majestic underground settlement carved from living rock by master dwarven craftsmen.

This subterranean town showcases dwarven engineering and artistry:
- **Town Square**: Central cavern with vaulted ceilings rising into near-darkness
- **Four Fountain Plazas**: Ornate fountains in NE, SE, SW, and NW positions
- **Stone Architecture**: Carved walls depicting dwarven life and history
- **Oil Lamp Lighting**: Even spacing provides adequate illumination
- **Stone Benches**: Well-crafted seating throughout the square

The town is characterized by its impressive stonework and careful lighting design, creating a functional and beautiful underground community. Connects east to the surface (room 1457).

## Room List

- legacy_town_53
- legacy_town_54
- legacy_town_55
- legacy_town_56
- legacy_town_57
- legacy_town_58
- legacy_town_59
- legacy_town_60
- legacy_town_61
- legacy_town_62
- legacy_town_63
- legacy_town_64
- legacy_town_65


## World Connections

East exit connects to surface world (room 1457).

## Integration Status

**Status**: Not yet integrated into main game world

These rooms are converted and ready but not yet connected to the existing game world. Integration requires:

1. Mapping NPC vnums to actual NPC definitions
2. Creating area definition for Dwarven Underground Town
3. Implementing barrier/door systems
4. Creating connection points to/from existing world
5. Testing all shops and services

## Technical Details

- **Area ID Pattern**: `legacy_{town_type}`
- **Room ID Pattern**: `legacy_town_{number}`
- **NPC Pattern**: `legacy_npc_{vnum}`
- **Format**: Matches current game room JSON schema
- **Terrain**: All rooms marked as "town" terrain
