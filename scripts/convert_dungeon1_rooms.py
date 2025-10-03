#!/usr/bin/env python3
"""Convert dungeon1_rooms.json to Forgotten Depths room format."""

import json
import os
from pathlib import Path

# Direction mapping
DIRECTION_MAP = {
    'NORTH': 'north',
    'SOUTH': 'south',
    'EAST': 'east',
    'WEST': 'west',
    'NORTHEAST': 'northeast',
    'NORTHWEST': 'northwest',
    'SOUTHEAST': 'southeast',
    'SOUTHWEST': 'southwest',
    'UP': 'up',
    'DOWN': 'down'
}

def convert_room(room_data, room_id_map):
    """Convert a single room from old format to new format."""
    room_id = f"dungeon1_{room_data['id']}"

    # Get description
    description = room_data.get('defaultLongDescriptionText', 'A dark dungeon room.')
    if not description or description.strip() == '':
        description = room_data.get('altLongDescriptionText', 'A dark dungeon room.')

    # Clean up description (remove extra newlines)
    description = ' '.join(description.split())

    # Generate title from description or use generic
    title_text = room_data.get('defaultDescriptionText', description[:50] if description else 'Dungeon Room')
    if not title_text or title_text.strip() in ['', '0', str(room_data['id'])]:
        title = f"Dungeon Level 1 - Room {room_data['id']}"
    else:
        # Capitalize first letter of each word
        title = title_text.strip().title()
        if len(title) > 60:
            title = f"Dungeon Room {room_data['id']}"

    # Convert exits
    exits = {}
    for exit_data in room_data.get('exits', []):
        to_room = exit_data.get('toRoom')
        direction = exit_data.get('exitDirection', '')

        # Skip invalid exits
        if not to_room or not direction:
            continue

        # Convert direction
        direction_lower = DIRECTION_MAP.get(direction, direction.lower())

        # Map room ID
        target_room_id = f"dungeon1_{to_room}"

        # Store in room_id_map for validation
        if to_room not in room_id_map:
            room_id_map[to_room] = target_room_id

        exits[direction_lower] = target_room_id

    # Check for lairs (respawning mobs)
    lairs = room_data.get('lairs', [])
    is_lair = False
    lair_monster = None
    respawn_time = 300  # Default 5 minutes

    if lairs:
        for lair in lairs:
            mob_id = lair.get('mob', '0')
            num_mobs = lair.get('numberOfMobs', '0')

            # Skip empty lairs
            if mob_id == '0' or num_mobs == '0':
                continue

            is_lair = True
            # We'll need to map old mob IDs to new ones later
            lair_monster = f"dungeon1_mob_{mob_id}"
            break

    # Build room object
    room = {
        'id': room_id,
        'title': title,
        'description': description,
        'area_id': 'dungeon1',
        'is_safe': False,
        'light_level': 0.2,
        'exits': exits
    }

    # Add lair properties if applicable
    if is_lair:
        room['is_lair'] = True
        room['lair_monster'] = lair_monster
        room['respawn_time'] = respawn_time

    return room

def main():
    """Main conversion function."""
    # Paths
    input_file = Path('data/world/rooms/dungeon1_rooms.json')
    output_dir = Path('data/world/rooms/dungeon1')

    # Read input
    print(f"Reading {input_file}...")
    with open(input_file, 'r') as f:
        rooms_data = json.load(f)

    print(f"Found {len(rooms_data)} rooms to convert")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Room ID mapping for validation
    room_id_map = {}

    # Convert all rooms
    converted_rooms = []
    for room_data in rooms_data:
        try:
            room = convert_room(room_data, room_id_map)
            converted_rooms.append(room)
        except Exception as e:
            print(f"Error converting room {room_data.get('id', 'unknown')}: {e}")
            continue

    # Write individual room files
    print(f"\nWriting {len(converted_rooms)} room files to {output_dir}/...")
    for room in converted_rooms:
        room_id = room['id']
        output_file = output_dir / f"{room_id}.json"

        with open(output_file, 'w') as f:
            json.dump(room, f, indent=2)

    # Validate connections
    print("\nValidating room connections...")
    all_room_ids = {r['id'] for r in converted_rooms}
    broken_connections = []

    for room in converted_rooms:
        for direction, target_id in room.get('exits', {}).items():
            if target_id not in all_room_ids and not target_id.startswith('dungeon1_-'):
                broken_connections.append((room['id'], direction, target_id))

    if broken_connections:
        print(f"\nWarning: Found {len(broken_connections)} broken connections:")
        for src, direction, target in broken_connections[:10]:
            print(f"  {src} -> {direction} -> {target}")
        if len(broken_connections) > 10:
            print(f"  ... and {len(broken_connections) - 10} more")
    else:
        print("All connections validated successfully!")

    # Print summary
    print(f"\n=== Conversion Summary ===")
    print(f"Total rooms converted: {len(converted_rooms)}")
    print(f"Rooms with lairs: {sum(1 for r in converted_rooms if r.get('is_lair'))}")
    print(f"Total exits: {sum(len(r.get('exits', {})) for r in converted_rooms)}")
    print(f"\nOutput directory: {output_dir.absolute()}")

    # Create area file
    area_file = Path('data/world/areas/dungeon1.json')
    area_data = {
        'id': 'dungeon1',
        'name': 'Dungeon Level 1',
        'description': 'A dark and dangerous dungeon filled with monsters and treasure.',
        'level_range': [1, 10],
        'is_pvp_enabled': False
    }

    print(f"\nCreating area file: {area_file}")
    area_file.parent.mkdir(parents=True, exist_ok=True)
    with open(area_file, 'w') as f:
        json.dump(area_data, f, indent=2)

    print("\nConversion complete!")

if __name__ == '__main__':
    main()
