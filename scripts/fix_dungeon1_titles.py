#!/usr/bin/env python3
"""Fix dungeon1 room titles by removing 'You are in a' and trailing periods."""

import json
import os
from pathlib import Path
import re

def clean_title(title):
    """Clean up a room title."""
    if not title:
        return title

    # Remove "You are in a" (case insensitive)
    title = re.sub(r'^You are in a\s+', '', title, flags=re.IGNORECASE)

    # Remove "You are in an" (case insensitive)
    title = re.sub(r'^You are in an\s+', '', title, flags=re.IGNORECASE)

    # Remove "You are in the" (case insensitive)
    title = re.sub(r'^You are in the\s+', '', title, flags=re.IGNORECASE)

    # Remove "You are in" (case insensitive)
    title = re.sub(r'^You are in\s+', '', title, flags=re.IGNORECASE)

    # Remove "You are" (case insensitive)
    title = re.sub(r'^You are\s+', '', title, flags=re.IGNORECASE)

    # Remove trailing period
    title = title.rstrip('.')

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    return title

def main():
    """Main function to fix all dungeon1 room titles."""
    dungeon_dir = Path('data/world/rooms/dungeon1')

    if not dungeon_dir.exists():
        print(f"Error: {dungeon_dir} does not exist")
        return

    fixed_count = 0
    unchanged_count = 0

    # Process all JSON files in the dungeon1 directory
    for room_file in dungeon_dir.glob('*.json'):
        try:
            # Read the room data
            with open(room_file, 'r') as f:
                room_data = json.load(f)

            # Get original title
            original_title = room_data.get('title', '')

            # Clean the title
            new_title = clean_title(original_title)

            # Update if changed
            if new_title != original_title:
                room_data['title'] = new_title

                # Write back to file
                with open(room_file, 'w') as f:
                    json.dump(room_data, f, indent=2)

                print(f"✓ {room_file.name}")
                print(f"  OLD: {original_title}")
                print(f"  NEW: {new_title}")
                print()
                fixed_count += 1
            else:
                unchanged_count += 1

        except Exception as e:
            print(f"Error processing {room_file}: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} room titles")
    print(f"Unchanged: {unchanged_count}")
    print(f"Total: {fixed_count + unchanged_count}")

if __name__ == '__main__':
    main()
