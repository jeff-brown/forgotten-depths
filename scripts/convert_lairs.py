#!/usr/bin/env python3
"""Convert old lair format to new list format."""

import json
import sys
from pathlib import Path

def convert_lair_format(file_path):
    """Convert a room file from old lair format to new format."""
    with open(file_path, 'r') as f:
        room_data = json.load(f)

    # Check if this uses old format
    if room_data.get('is_lair') and 'lair_monster' in room_data:
        print(f"Converting {file_path}")

        # Extract old format data
        mob_id = room_data['lair_monster']
        respawn_time = room_data.get('respawn_time', 300)

        # Remove old format fields
        del room_data['is_lair']
        del room_data['lair_monster']
        if 'respawn_time' in room_data:
            del room_data['respawn_time']

        # Add new format
        room_data['lairs'] = [
            {
                "mob_id": mob_id,
                "respawn_time": respawn_time,
                "max_mobs": 1
            }
        ]

        # Write back to file
        with open(file_path, 'w') as f:
            json.dump(room_data, f, indent=2)

        print(f"  ✓ Converted to lairs array format")
        return True
    else:
        print(f"Skipping {file_path} - already in new format or no lair")
        return False

def main():
    """Convert all lair rooms."""
    # Find all rooms with old lair format
    rooms_dir = Path("data/world/rooms")

    converted = 0
    for json_file in rooms_dir.rglob("*.json"):
        if convert_lair_format(json_file):
            converted += 1

    print(f"\n✓ Converted {converted} lair rooms to new format")

if __name__ == "__main__":
    main()
