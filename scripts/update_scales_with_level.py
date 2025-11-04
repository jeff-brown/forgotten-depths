#!/usr/bin/env python3
"""Update scales_with_level attribute based on the spell table."""

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

# Spells that scale with level (from the table)
SCALES_WITH_LEVEL = {
    'toradaku': 'Yes',
    'modokidaku': 'Yes',
    'tamikar': 'Yes',
    'yilazi': 'Yes',
    'dobudakidaku': 'Yes',
    'kamazadaku': 'Yes',
    'dakidaku': 'Yes',
    'dumoti': 'Yes',
    'todukar': 'Yes',
    'komasidaku': 'Yes',
    'komizadaku': 'Yes',
}

def update_scales_with_level():
    """Update scales_with_level for specific spells."""

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

        # Update scales_with_level for matching spells
        for spell_id, spell_data in spells.items():
            if spell_id in SCALES_WITH_LEVEL:
                old_value = spell_data.get('scales_with_level', 'No')
                new_value = SCALES_WITH_LEVEL[spell_id]
                spell_data['scales_with_level'] = new_value

                if old_value != new_value:
                    updated_count += 1
                    print(f"  {spell_data.get('name', spell_id)}: {old_value} -> {new_value}")

        # Write back to file if changes were made
        if updated_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            print(f"✓ Updated {file_path}: {updated_count} spells")
            print()
            total_updated += updated_count

    print("=" * 60)
    print(f"✓ Total spells updated: {total_updated}")
    print("\nSpells that now scale with level:")
    for spell_id in sorted(SCALES_WITH_LEVEL.keys()):
        print(f"  - {spell_id}")

if __name__ == '__main__':
    update_scales_with_level()
