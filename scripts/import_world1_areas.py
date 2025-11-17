#!/usr/bin/env python3
"""
Import World1 areas into Forgotten Depths.

Converts World1 room format (numeric IDs) to game format (string IDs).
"""

import json
import sys
from pathlib import Path


def convert_room_to_game_format(room, area_name_slug, room_id_to_string_id):
    """Convert World1 room format to game format."""

    room_id = room['room_id']
    string_id = f"{area_name_slug}_{room_id}"

    # Store mapping
    room_id_to_string_id[room_id] = string_id

    # Convert exits to string IDs
    exits = {}
    for exit_info in room.get('exits', []):
        direction = exit_info.get('direction')
        to_room = exit_info.get('to_room')

        if to_room and direction:
            # Will be updated in second pass once all rooms are mapped
            exits[direction] = to_room  # Keep numeric for now

    # Build game room format
    game_room = {
        "id": string_id,
        "title": room.get('short_description', 'An area').strip('.'),
        "description": room.get('long_description', room.get('short_description', 'You see nothing special.')),
        "area_id": area_name_slug,
        "is_safe": False,
        "light_level": 0.5,  # Default, adjust as needed
        "exits": exits
    }

    # Add lairs if present
    if room.get('lairs') and len(room['lairs']) > 0:
        game_room['lairs'] = []
        for lair in room['lairs']:
            # Get vnum from lair (could be mob_vnum or in nested mob object)
            vnum = lair.get('mob_vnum') or lair.get('mob', {}).get('vnum')

            if vnum is not None:
                # Will be converted to proper mob_id by fix_world1_lairs.py
                game_room['lairs'].append({
                    "mob_vnum": vnum,  # Keep vnum for now, will be converted
                    "respawn_time": 300,
                    "max_mobs": lair.get('num_mobs', lair.get('count', 1))
                })
            else:
                # Fallback if no vnum
                game_room['lairs'].append({
                    "mob_id": "unknown",
                    "respawn_time": 300,
                    "max_mobs": lair.get('num_mobs', lair.get('count', 1))
                })

    # Add items if present
    if room.get('items') and len(room['items']) > 0:
        game_room['items'] = []
        for item in room['items']:
            if isinstance(item, dict):
                item_id = item.get('item_id', 'unknown').lower().replace(' ', '_')
                game_room['items'].append(item_id)
            else:
                game_room['items'].append(item.lower().replace(' ', '_'))

    # Add NPCs if present
    npcs_data = room.get('npcs', {})
    if npcs_data.get('npcs') and len(npcs_data['npcs']) > 0:
        game_room['npcs'] = []
        for npc in npcs_data['npcs']:
            npc_id = npc.get('name', 'unknown').lower().replace(' ', '_')
            game_room['npcs'].append(npc_id)

    return game_room


def update_exit_references(game_rooms, room_id_to_string_id, area_name_slug, town_connection_room=None):
    """Update numeric exit references to string IDs."""

    for room in game_rooms:
        updated_exits = {}

        for direction, to_room in room['exits'].items():
            if isinstance(to_room, int):
                if to_room < 0:
                    # Negative room ID - connection to town
                    if town_connection_room:
                        updated_exits[direction] = town_connection_room
                    else:
                        print(f"  Warning: Room {room['id']} has exit to town (room {to_room}) but no town room specified")
                        # Remove this exit for now
                        continue
                elif to_room in room_id_to_string_id:
                    # Internal connection within this import
                    updated_exits[direction] = room_id_to_string_id[to_room]
                else:
                    # Connection to another area - keep numeric for now, will fix later
                    print(f"  Note: Room {room['id']} has exit {direction} to room {to_room} (different area)")
                    updated_exits[direction] = f"FIXME_room_{to_room}"
            else:
                # Already a string ID
                updated_exits[direction] = to_room

        room['exits'] = updated_exits


def import_area(area_file, output_dir, town_connection_room=None):
    """Import a single World1 area."""

    print(f"\nImporting {area_file.name}...")

    with open(area_file, 'r') as f:
        area_data = json.load(f)

    area_name = area_data['area_name']
    area_name_slug = area_name.lower().replace(' ', '_').replace('-', '_')
    room_count = len(area_data['rooms'])

    print(f"  Area: {area_name}")
    print(f"  Rooms: {room_count}")
    print(f"  Output: {output_dir}/{area_name_slug}/")

    # Create output directory
    area_output_dir = output_dir / area_name_slug
    area_output_dir.mkdir(parents=True, exist_ok=True)

    # Track room ID mappings
    room_id_to_string_id = {}
    game_rooms = []

    # First pass: convert all rooms
    for room in area_data['rooms']:
        game_room = convert_room_to_game_format(room, area_name_slug, room_id_to_string_id)
        game_rooms.append(game_room)

    # Second pass: update exit references
    update_exit_references(game_rooms, room_id_to_string_id, area_name_slug, town_connection_room)

    # Write room files
    for game_room in game_rooms:
        room_file = area_output_dir / f"{game_room['id']}.json"
        with open(room_file, 'w') as f:
            json.dump(game_room, f, indent=2)

    print(f"  ✓ Created {len(game_rooms)} room files")

    # Check for external connections
    external_connections = []
    for game_room in game_rooms:
        for direction, to_room in game_room['exits'].items():
            if isinstance(to_room, str) and to_room.startswith('FIXME_'):
                external_connections.append({
                    'from': game_room['id'],
                    'direction': direction,
                    'to': to_room
                })

    if external_connections:
        print(f"\n  External connections found ({len(external_connections)}):")
        for conn in external_connections[:5]:
            print(f"    {conn['from']} --{conn['direction']}--> {conn['to']}")
        if len(external_connections) > 5:
            print(f"    ... and {len(external_connections) - 5} more")

    return {
        'area_name': area_name,
        'area_slug': area_name_slug,
        'room_count': room_count,
        'room_id_map': room_id_to_string_id,
        'external_connections': external_connections
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_world1_areas.py <area_name> [town_connection_room]")
        print("\nExamples:")
        print("  python import_world1_areas.py mountains_area town_square")
        print("  python import_world1_areas.py forest_area")
        print("\nAvailable areas:")
        starter_dir = Path('config/temp/world1_areas/0_no_rune_starter')
        for f in sorted(starter_dir.glob('*.json')):
            with open(f, 'r') as file:
                data = json.load(file)
                print(f"  - {data['area_name'].lower().replace(' ', '_')} ({data['_statistics']['total_rooms']} rooms)")
        return

    area_name_arg = sys.argv[1].lower().replace(' ', '_')
    town_room = sys.argv[2] if len(sys.argv) > 2 else None

    # Find matching area file
    starter_dir = Path('config/temp/world1_areas/0_no_rune_starter')
    area_file = None

    for f in sorted(starter_dir.glob('*.json')):
        with open(f, 'r') as file:
            data = json.load(file)
            if data['area_name'].lower().replace(' ', '_') == area_name_arg:
                area_file = f
                break

    if not area_file:
        print(f"Error: Area '{area_name_arg}' not found")
        return

    # Import the area
    output_dir = Path('data/world/rooms')
    result = import_area(area_file, output_dir, town_room)

    print("\n" + "=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"\nImported: {result['area_name']}")
    print(f"Directory: data/world/rooms/{result['area_slug']}/")
    print(f"Rooms created: {result['room_count']}")

    if result['external_connections']:
        print(f"\n⚠ Warning: {len(result['external_connections'])} external connections need fixing")
        print("These rooms have exits to other areas that haven't been imported yet.")
        print("Search for 'FIXME_room_' in the JSON files and update when those areas are imported.")

    print()


if __name__ == "__main__":
    main()
