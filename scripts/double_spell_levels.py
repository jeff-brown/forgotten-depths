#!/usr/bin/env python3
"""Double the level requirement for all spells."""

import json
from pathlib import Path

# Spell files to update
SPELL_FILES = [
    'data/spells/sorcerer_spells.json',
    'data/spells/warlock_spells.json',
    'data/spells/cleric_spells.json',
    'data/spells/druid_spells.json',
    'data/spells/multi_class_spells.json'
]

def double_spell_levels():
    """Double the level requirement for all spells."""

    total_updated = 0

    for spell_file in SPELL_FILES:
        file_path = Path(spell_file)
        if not file_path.exists():
            print(f"Warning: {spell_file} not found, skipping...")
            continue

        # Load the spell file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        spells = data.get('spells', {})
        updated_count = 0

        # Double the level for each spell
        for spell_id, spell_data in spells.items():
            old_level = spell_data.get('level', 1)
            new_level = old_level * 2
            spell_data['level'] = new_level
            updated_count += 1
            print(f"  {spell_data.get('name', spell_id)}: Level {old_level} -> {new_level}")

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Updated {file_path}: {updated_count} spells")
        print()
        total_updated += updated_count

    print("=" * 60)
    print(f"✓ Total spells updated: {total_updated}")
    print("\nNew level ranges:")
    print("  Old Level 1 -> New Level 2")
    print("  Old Level 2 -> New Level 4")
    print("  Old Level 3 -> New Level 6")
    print("  Old Level 4 -> New Level 8")
    print("  Old Level 5 -> New Level 10")
    print("  Old Level 6 -> New Level 12")
    print("  Old Level 7 -> New Level 14")
    print("  Old Level 8 -> New Level 16")
    print("  Old Level 9 -> New Level 18")

if __name__ == '__main__':
    double_spell_levels()
