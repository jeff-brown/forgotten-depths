#!/usr/bin/env python3
"""
Fix lairs in World1 imported rooms to match game format.

Uses the vnum_to_id mapping to convert World1 mob vnums to game mob IDs.
Matches the lair structure used in existing dungeons.
"""

import json
from pathlib import Path


def load_vnum_mapping():
    """Load the vnum to mob ID mapping."""
    with open('data/mobs/_vnum_to_id_map.json', 'r') as f:
        mapping = json.load(f)

    # Convert to int keys for easier lookup
    return {int(k): v['id'] for k, v in mapping.items()}


def fix_lairs_in_room(room_file, vnum_map):
    """Fix lairs in a single room file."""

    with open(room_file, 'r') as f:
        room_data = json.load(f)

    lairs = room_data.get('lairs', [])
    if not lairs:
        return None  # No lairs to fix

    fixed_lairs = []
    changes = []

    for lair in lairs:
        # Check if this is already in correct format (has mob_id and not mob_vnum)
        if 'mob_id' in lair and 'mob_vnum' not in lair:
            # Already correct format, keep as-is
            fixed_lairs.append(lair)
            continue

        # Get the vnum from the lair
        vnum = lair.get('mob_vnum')  # Direct vnum field
        if vnum is None:
            vnum = lair.get('mob', {}).get('vnum')  # Nested mob object

        if vnum is None:
            changes.append(f"  Warning: No vnum found for lair: {lair}")
            fixed_lairs.append(lair)
            continue

        # Look up the mob ID
        mob_id = vnum_map.get(vnum)

        if not mob_id:
            changes.append(f"  Warning: Unknown vnum {vnum}")
            # Keep the lair but mark it
            fixed_lairs.append({
                "mob_id": f"unknown_vnum_{vnum}",
                "respawn_time": 300,
                "max_mobs": lair.get('max_mobs', lair.get('num_mobs', 1))
            })
            continue

        # Create proper lair format matching dungeon1_5.json
        fixed_lair = {
            "mob_id": mob_id,
            "respawn_time": lair.get('respawn_time', 300),  # Keep existing or default to 5 min
            "max_mobs": lair.get('max_mobs', lair.get('num_mobs', 1))
        }

        fixed_lairs.append(fixed_lair)
        changes.append(f"  Fixed: vnum {vnum} -> {mob_id} (max_mobs: {fixed_lair['max_mobs']})")

    if changes:
        # Update the room file
        room_data['lairs'] = fixed_lairs

        with open(room_file, 'w') as f:
            json.dump(room_data, f, indent=2)

        return {
            'file': room_file.name,
            'room_id': room_data.get('id'),
            'changes': changes
        }

    return None


def fix_area_lairs(area_name):
    """Fix all lairs in an area."""

    print("=" * 70)
    print(f"Fixing Lairs in {area_name}")
    print("=" * 70)
    print()

    # Load vnum mapping
    print("Loading vnum to mob ID mapping...")
    vnum_map = load_vnum_mapping()
    print(f"  Loaded {len(vnum_map)} mob mappings")
    print()

    # Find all rooms in area
    area_dir = Path(f'data/world/rooms/{area_name}')

    if not area_dir.exists():
        print(f"Error: Area directory not found: {area_dir}")
        return

    room_files = sorted(area_dir.glob('*.json'))
    print(f"Found {len(room_files)} room files")
    print()

    # Fix lairs in each room
    fixed_rooms = []
    total_changes = 0

    for room_file in room_files:
        result = fix_lairs_in_room(room_file, vnum_map)
        if result:
            fixed_rooms.append(result)
            total_changes += len(result['changes'])

    # Print results
    if fixed_rooms:
        print(f"Fixed lairs in {len(fixed_rooms)} rooms:")
        print()

        for result in fixed_rooms:
            print(f"{result['file']} ({result['room_id']}):")
            for change in result['changes']:
                print(change)
            print()
    else:
        print("No lairs needed fixing (all already in correct format)")

    print("=" * 70)
    print(f"COMPLETE: Fixed {total_changes} lairs in {len(fixed_rooms)} rooms")
    print("=" * 70)
    print()


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fix_world1_lairs.py <area_name>")
        print("\nExamples:")
        print("  python fix_world1_lairs.py mountains_area")
        print("  python fix_world1_lairs.py forest_area")
        print("  python fix_world1_lairs.py mountains_cave_area")
        print("\nOr fix all imported areas:")
        print("  python fix_world1_lairs.py all")
        return

    area_name = sys.argv[1]

    if area_name == 'all':
        # Fix all World1 areas
        areas = ['mountains_area', 'forest_area', 'mountains_cave_area']
        for area in areas:
            fix_area_lairs(area)
            print()
    else:
        fix_area_lairs(area_name)


if __name__ == "__main__":
    main()
