#!/usr/bin/env python3
"""Debug script to check world loading."""

import sys
sys.path.insert(0, 'src')

from server.persistence.world_loader import WorldLoader
from server.game.world.world_manager import WorldManager

# Load world data
loader = WorldLoader()
print("Loading world data...")
rooms_data = loader.load_rooms()
print(f"Loaded {len(rooms_data)} rooms from files")

# Check town_square specifically
if 'town_square' in rooms_data:
    town_square = rooms_data['town_square']
    print(f"\ntown_square data:")
    print(f"  ID: {town_square.get('id')}")
    print(f"  Title: {town_square.get('title')}")
    print(f"  Exits: {town_square.get('exits', {})}")
else:
    print("\nERROR: town_square not found in rooms_data!")

# Create world manager and load world
print("\n" + "="*50)
print("Creating WorldManager and loading world...")
world_manager = WorldManager()
world_manager.load_world()

# Check if town_square room exists
if 'town_square' in world_manager.rooms:
    room = world_manager.rooms['town_square']
    print(f"\ntown_square room object:")
    print(f"  ID: {room.room_id}")
    print(f"  Title: {room.title}")
    print(f"  Exits on room object: {list(room.exits.keys())}")

    # Check graph
    print(f"\nChecking world graph...")
    edges = world_manager.world_graph.get_neighbors('town_square')
    print(f"  Graph edges from town_square: {len(edges)}")
    for edge in edges:
        print(f"    - {edge.direction} -> {edge.to_room}")

    # Check get_exits_from_room
    exits = world_manager.get_exits_from_room('town_square')
    print(f"\nget_exits_from_room('town_square'): {exits}")
else:
    print("\nERROR: town_square not found in world_manager.rooms!")

# List all loaded rooms
print(f"\nTotal rooms loaded: {len(world_manager.rooms)}")
print(f"Sample room IDs: {list(world_manager.rooms.keys())[:10]}")
