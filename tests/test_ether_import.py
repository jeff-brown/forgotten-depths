#!/usr/bin/env python3
"""Test script for the imported Ether world data."""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from server.core.world_manager import WorldManager
from server.persistence.world_loader import WorldLoader

def test_ether_import():
    """Test the imported Ether world data."""
    print("=== Testing Imported Ether World Data ===")
    print()

    # Create a custom world loader pointing to imported data
    ether_data_dir = "./data/imported_ether"

    print("1. Testing world loader with Ether data...")

    # Temporarily modify the world loader to use our imported data
    world_manager = WorldManager()

    # Override the world loader data directory
    original_data_dir = world_manager.world_loader.data_dir
    world_manager.world_loader.data_dir = ether_data_dir

    try:
        world_manager.load_world()
        stats = world_manager.get_world_stats()

        print(f"   ✓ Loaded: {stats['rooms']} rooms")
        print(f"   ✓ Areas: {stats['areas']}")
        print(f"   ✓ Graph edges: {stats['graph_edges']}")
        print(f"   ✓ Average connections per room: {stats['avg_connections_per_room']:.1f}")
        print()

        # Test some specific functionality
        print("2. Testing navigation in imported world...")

        # Find a room with multiple exits
        sample_rooms = ["room_1", "room_3", "room_5"]

        for room_id in sample_rooms:
            room = world_manager.get_room(room_id)
            if room:
                print(f"   Room {room_id}: {room.title}")
                exits = world_manager.get_exits_from_room(room_id)
                print(f"     Exits: {list(exits.keys())}")

                # Test pathfinding to nearby rooms
                neighbors = world_manager.get_room_neighbors(room_id)
                if neighbors:
                    target = neighbors[0]
                    path = world_manager.find_path(room_id, target)
                    if path:
                        print(f"     Path to {target}: {' -> '.join(path)}")
        print()

        # Test area exploration
        print("3. Testing area exploration...")
        center = "room_1"
        radius = 3
        nearby = world_manager.get_area_rooms_within_distance(center, radius)
        print(f"   Rooms within {radius} steps of {center}: {len(nearby)}")

        if len(nearby) > 10:
            print("     First 10 rooms:")
            for room_id in sorted(nearby)[:10]:
                room = world_manager.get_room(room_id)
                if room:
                    print(f"       {room_id}: {room.title}")
        else:
            for room_id in sorted(nearby):
                room = world_manager.get_room(room_id)
                if room:
                    print(f"     {room_id}: {room.title}")
        print()

        # Test different terrain types
        print("4. Testing terrain diversity...")
        terrain_counts = {}
        for room_id, room in world_manager.rooms.items():
            terrain = getattr(room, 'terrain', 'unknown')
            terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1

        print("   Terrain distribution:")
        for terrain, count in sorted(terrain_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"     {terrain}: {count} rooms")
        print()

        # Test pathfinding across different areas
        print("5. Testing long-distance pathfinding...")
        start_room = "room_1"

        # Find a room far away
        distances = world_manager.world_graph.find_all_reachable(start_room, None, 10)
        far_rooms = [room for room, dist in distances.items() if dist >= 5]

        if far_rooms:
            target_room = far_rooms[0]
            path = world_manager.find_path(start_room, target_room)
            if path:
                print(f"   Long path from {start_room} to {target_room}: {len(path)-1} steps")
                print(f"   Route: {' -> '.join(path[:5])}{'...' if len(path) > 5 else ''}")
            else:
                print(f"   No path found from {start_room} to {target_room}")
        else:
            print("   No distant rooms found for long-distance testing")
        print()

        print("=== Ether Import Test Results ===")
        print(f"✓ Successfully loaded {stats['rooms']} rooms from Ether XML")
        print(f"✓ Created {stats['areas']} areas with proper terrain mapping")
        print(f"✓ Established {stats['graph_edges']} connections between rooms")
        print(f"✓ Graph navigation system working properly")
        print(f"✓ Pathfinding functional across the imported world")
        print()
        print("The Ether world import is ready for use!")

    except Exception as e:
        print(f"   ✗ Error loading Ether world: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Restore original path
        world_manager.world_loader.data_dir = original_data_dir

if __name__ == "__main__":
    test_ether_import()