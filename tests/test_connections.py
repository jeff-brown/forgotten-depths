#!/usr/bin/env python3
"""Test room connections."""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from server.core.world_manager import WorldManager

def test_connections():
    """Test room connections."""
    print("Testing room connections...")

    # Create world manager and load world
    world_manager = WorldManager()
    world_manager.load_world()

    # Test specific room connections
    test_rooms = ['inn_room_1', 'inn_balcony', 'town_square', 'blacksmith_shop']

    for room_id in test_rooms:
        print(f"\n=== {room_id} ===")
        room = world_manager.get_room(room_id)
        if room:
            print(f"Room found: {room.title}")

            # Get exits using world manager method
            exits = world_manager.get_exits_from_room(room_id)
            print(f"Available exits: {exits}")

            # Test each exit
            for direction, target_room in exits.items():
                target = world_manager.get_room(target_room)
                if target:
                    print(f"  {direction} -> {target_room} ({target.title})")
                else:
                    print(f"  {direction} -> {target_room} (ROOM NOT FOUND!)")
        else:
            print("Room not found!")

if __name__ == "__main__":
    test_connections()