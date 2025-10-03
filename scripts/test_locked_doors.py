#!/usr/bin/env python3
"""Test script for locked door system."""

import sys
sys.path.insert(0, 'src')

from server.persistence.world_loader import WorldLoader
from server.game.world.world_manager import WorldManager

# Load world
print("Loading world...")
world_manager = WorldManager()
world_manager.load_world()

# Check dungeon1_1 room
room = world_manager.get_room('dungeon1_1')
if room:
    print(f"\nRoom: {room.title}")
    print(f"Exits: {list(room.exits.keys())}")
    print(f"Locked exits: {list(room.locked_exits.keys())}")

    if room.locked_exits:
        for direction, lock_info in room.locked_exits.items():
            print(f"\n  {direction}:")
            print(f"    Required key: {lock_info.get('required_key')}")
            print(f"    Description: {lock_info.get('description')}")
            print(f"    Is locked: {room.is_exit_locked(direction)}")

    # Test unlocking
    if room.is_exit_locked('northeast'):
        print(f"\n  Testing unlock of 'northeast' exit...")
        required_key = room.get_required_key('northeast')
        print(f"  Required key: {required_key}")

        room.unlock_exit('northeast')
        print(f"  After unlock - is locked: {room.is_exit_locked('northeast')}")
        print(f"  Locked exits now: {list(room.locked_exits.keys())}")

# Check dungeon1_14 room for bronze key
room14 = world_manager.get_room('dungeon1_14')
if room14:
    print(f"\n\nRoom: {room14.title}")
    print(f"Description: {room14.description[:100]}...")
    if hasattr(room14, '_raw_data'):
        items = room14._raw_data.get('items', [])
        print(f"Items in room: {items}")

print("\n✅ Locked door system test complete!")
