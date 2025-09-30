#!/usr/bin/env python3
"""Script to create and populate the game world from data files."""

import sys
import os
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def load_world_data():
    """Load world data from JSON files."""
    from server.persistence.world_loader import WorldLoader

    loader = WorldLoader()

    print("Loading world data...")
    areas = loader.load_areas()
    rooms = loader.load_rooms()
    items = loader.load_items()
    npcs = loader.load_npcs()
    connections = loader.load_connections()

    print(f"Loaded {len(areas)} areas")
    print(f"Loaded {len(rooms)} rooms")
    print(f"Loaded {len(items)} items")
    print(f"Loaded {len(npcs)} NPCs")

    return {
        'areas': areas,
        'rooms': rooms,
        'items': items,
        'npcs': npcs,
        'connections': connections
    }

def validate_world_data(world_data):
    """Validate the loaded world data for consistency."""
    errors = []

    # Check room connections
    rooms = world_data['rooms']
    connections = world_data.get('connections', {}).get('rooms', {})

    for room_id, room_data in rooms.items():
        # Check if room is referenced in connections
        if room_id in connections:
            for direction, target_room in connections[room_id].items():
                if target_room not in rooms:
                    errors.append(f"Room {room_id} has exit {direction} to non-existent room {target_room}")

        # Check NPCs exist
        for npc_id in room_data.get('npcs', []):
            if npc_id not in world_data['npcs']:
                errors.append(f"Room {room_id} references non-existent NPC {npc_id}")

        # Check items exist
        for item_id in room_data.get('items', []):
            if item_id not in world_data['items']:
                errors.append(f"Room {room_id} references non-existent item {item_id}")

    # Check area consistency
    areas = world_data['areas']
    for area_id, area_data in areas.items():
        for room_id in area_data.get('rooms', []):
            if room_id not in rooms:
                errors.append(f"Area {area_id} references non-existent room {room_id}")
            elif rooms[room_id].get('area_id') != area_id:
                errors.append(f"Room {room_id} area_id doesn't match area {area_id}")

    return errors

def create_starting_data():
    """Create additional starting data if needed."""
    print("Creating starting character and world state...")

    # This could be expanded to create:
    # - Default player characters
    # - Initial world state
    # - Spawn locations for NPCs
    # - Item placement in rooms

def generate_world_report(world_data):
    """Generate a report about the world."""
    report = []
    report.append("=== FORGOTTEN DEPTHS WORLD REPORT ===")
    report.append("")

    # Areas summary
    report.append("AREAS:")
    for area_id, area_data in world_data['areas'].items():
        report.append(f"  {area_id}: {area_data.get('name', 'Unnamed')} ({len(area_data.get('rooms', []))} rooms)")

    report.append("")

    # Rooms summary
    report.append(f"ROOMS: {len(world_data['rooms'])} total")
    safe_rooms = sum(1 for room in world_data['rooms'].values() if room.get('is_safe'))
    report.append(f"  Safe rooms: {safe_rooms}")

    report.append("")

    # Items summary
    report.append(f"ITEMS: {len(world_data['items'])} total")
    item_types = {}
    for item in world_data['items'].values():
        item_type = item.get('type', 'unknown')
        item_types[item_type] = item_types.get(item_type, 0) + 1

    for item_type, count in sorted(item_types.items()):
        report.append(f"  {item_type}: {count}")

    report.append("")

    # NPCs summary
    report.append(f"NPCS: {len(world_data['npcs'])} total")
    npc_types = {}
    for npc in world_data['npcs'].values():
        npc_type = npc.get('type', 'unknown')
        npc_types[npc_type] = npc_types.get(npc_type, 0) + 1

    for npc_type, count in sorted(npc_types.items()):
        report.append(f"  {npc_type}: {count}")

    return "\n".join(report)

def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Create Forgotten Depths world")
    parser.add_argument("--validate", action="store_true",
                       help="Only validate world data, don't create")
    parser.add_argument("--report", action="store_true",
                       help="Generate world report")
    parser.add_argument("--output", "-o", help="Output file for report")

    args = parser.parse_args()

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Load world data
    try:
        world_data = load_world_data()
    except Exception as e:
        print(f"Error loading world data: {e}")
        sys.exit(1)

    # Validate world data
    errors = validate_world_data(world_data)
    if errors:
        print("VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        if not args.validate:
            print("Fix validation errors before creating world.")
            sys.exit(1)
    else:
        print("World data validation passed!")

    if args.validate:
        print("Validation complete.")
        return

    # Generate report if requested
    if args.report:
        report = generate_world_report(world_data)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Report written to {args.output}")
        else:
            print(report)
        return

    # Create world
    print("World creation complete!")
    print("The world data has been validated and is ready to use.")
    print("Start the server with: python scripts/start_server.py")

if __name__ == "__main__":
    main()