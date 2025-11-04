# Elven Tree Town

**Location**: `data/world/rooms/legacy_town/elven_tree_town/`  
**Room Count**: 28 rooms  
**Source**: Ether MUD Engine Town Area

## Overview

An extensive tree-based elven settlement, the largest of the four towns with 28 interconnected rooms.

This sprawling elven community is built among ancient trees, featuring:
- **Tree-based Architecture**: Structures integrated with living trees
- **Elevated Platforms**: Multiple levels connected by staircases and bridges
- **Natural Integration**: Seamless blend of construction and nature
- **Extensive Layout**: The most rooms of any town, providing varied locations

As the largest settlement, this elven town offers the most exploration opportunities and likely contains the most diverse range of facilities and services.

## Room List

- legacy_town_25
- legacy_town_26
- legacy_town_27
- legacy_town_28
- legacy_town_29
- legacy_town_30
- legacy_town_31
- legacy_town_32
- legacy_town_33
- legacy_town_34
- legacy_town_35
- legacy_town_36
- legacy_town_37
- legacy_town_38
- legacy_town_39
- legacy_town_40
- legacy_town_41
- legacy_town_42
- legacy_town_43
- legacy_town_44
- legacy_town_45
- legacy_town_46
- legacy_town_47
- legacy_town_48
- legacy_town_49
- legacy_town_50
- legacy_town_51
- legacy_town_52


## World Connections

Multiple connections throughout the tree network.

## Integration Status

**Status**: Not yet integrated into main game world

These rooms are converted and ready but not yet connected to the existing game world. Integration requires:

1. Mapping NPC vnums to actual NPC definitions
2. Creating area definition for Elven Tree Town
3. Implementing barrier/door systems
4. Creating connection points to/from existing world
5. Testing all shops and services

## Technical Details

- **Area ID Pattern**: `legacy_{town_type}`
- **Room ID Pattern**: `legacy_town_{number}`
- **NPC Pattern**: `legacy_npc_{vnum}`
- **Format**: Matches current game room JSON schema
- **Terrain**: All rooms marked as "town" terrain
