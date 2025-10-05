#!/usr/bin/env python3
"""Split monsters.json into type-specific files."""

import json
from pathlib import Path
from collections import defaultdict

def main():
    # Read the monsters file
    monsters_file = Path("data/npcs/monsters.json")

    if not monsters_file.exists():
        print(f"Error: {monsters_file} not found")
        return

    with open(monsters_file, 'r', encoding='utf-8') as f:
        monsters = json.load(f)

    # Group monsters by type
    monsters_by_type = defaultdict(list)
    for monster in monsters:
        monster_type = monster.get('type', 'unknown')
        monsters_by_type[monster_type].append(monster)

    # Create output directory
    output_dir = Path("data/mobs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write each type to a separate file
    total_written = 0
    for monster_type, type_monsters in monsters_by_type.items():
        output_file = output_dir / f"{monster_type}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"monsters": type_monsters}, f, indent=2, ensure_ascii=False)

        print(f"Created {output_file} with {len(type_monsters)} monsters")
        total_written += len(type_monsters)

    # Backup original file
    backup_file = Path("data/npcs/monsters.json.backup")
    import shutil
    shutil.copy2(monsters_file, backup_file)
    print(f"\nBacked up original to {backup_file}")

    print(f"\nTotal monsters written: {total_written}")
    print(f"Total types: {len(monsters_by_type)}")
    print(f"Types: {', '.join(sorted(monsters_by_type.keys()))}")

if __name__ == "__main__":
    main()
