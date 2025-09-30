#!/usr/bin/env python3
"""Test NPC loading and display."""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from server.core.world_manager import WorldManager

def test_npc_loading():
    """Test that NPCs are loaded and can be displayed."""
    print("Testing NPC loading...")

    # Create world manager and load world
    world_manager = WorldManager()
    world_manager.load_world()

    # Test NPC data loading
    print(f"Loaded {len(world_manager.npcs)} NPCs")
    for npc_id, npc_data in world_manager.npcs.items():
        print(f"  - {npc_id}: {npc_data.get('name', 'No name')}")

    # Test blacksmith shop room
    print("\nTesting blacksmith shop room:")
    blacksmith_room = world_manager.get_room('blacksmith_shop')
    if blacksmith_room:
        print(f"Room found: {blacksmith_room.title}")
        if hasattr(blacksmith_room, '_raw_data') and blacksmith_room._raw_data:
            raw_npcs = blacksmith_room._raw_data.get('npcs', [])
            print(f"Raw NPCs in room: {raw_npcs}")

            # Test NPC display for each NPC in room
            for npc_id in raw_npcs:
                display_name = world_manager.get_npc_display_name(npc_id)
                is_hostile = world_manager.is_npc_hostile(npc_id)
                print(f"  - NPC ID: {npc_id}")
                print(f"    Display Name: {display_name}")
                print(f"    Hostile: {is_hostile}")
    else:
        print("Blacksmith shop room not found!")

    # Test town square room
    print("\nTesting town square room:")
    town_square = world_manager.get_room('town_square')
    if town_square:
        print(f"Room found: {town_square.title}")
        if hasattr(town_square, '_raw_data') and town_square._raw_data:
            raw_npcs = town_square._raw_data.get('npcs', [])
            print(f"Raw NPCs in room: {raw_npcs}")

            # Test NPC display for each NPC in room
            for npc_id in raw_npcs:
                display_name = world_manager.get_npc_display_name(npc_id)
                is_hostile = world_manager.is_npc_hostile(npc_id)
                print(f"  - NPC ID: {npc_id}")
                print(f"    Display Name: {display_name}")
                print(f"    Hostile: {is_hostile}")
    else:
        print("Town square room not found!")

if __name__ == "__main__":
    test_npc_loading()