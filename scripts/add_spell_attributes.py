#!/usr/bin/env python3
"""Add area_of_effect and scales_with_level attributes to all damage spells."""

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

def determine_area_of_effect(spell_id, spell_data):
    """Determine area of effect based on spell properties."""
    # Check range field
    spell_range = spell_data.get('range', 'ranged')

    # Area spells
    if spell_range in ['area', 'self', 'friendly']:
        return 'Area'

    # Single target spells
    if spell_range in ['ranged', 'touch']:
        return 'Single'

    # Default to Single
    return 'Single'

def determine_scales_with_level(spell_data):
    """Determine if spell scales with level."""
    # For now, we'll default to "No" for all spells
    # This can be customized per spell later
    return 'No'

def add_spell_attributes():
    """Add area_of_effect and scales_with_level to all damage spells."""

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

        # Add attributes to each damage spell
        for spell_id, spell_data in spells.items():
            spell_type = spell_data.get('type', '')

            # Only update damage-type spells
            if spell_type == 'damage':
                # Add area_of_effect if not present
                if 'area_of_effect' not in spell_data:
                    spell_data['area_of_effect'] = determine_area_of_effect(spell_id, spell_data)

                # Add scales_with_level if not present
                if 'scales_with_level' not in spell_data:
                    spell_data['scales_with_level'] = determine_scales_with_level(spell_data)

                updated_count += 1
                print(f"  {spell_data.get('name', spell_id)}: area={spell_data['area_of_effect']}, scales={spell_data['scales_with_level']}")

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Updated {file_path}: {updated_count} damage spells")
        print()
        total_updated += updated_count

    print("=" * 60)
    print(f"✓ Total damage spells updated: {total_updated}")

if __name__ == '__main__':
    add_spell_attributes()
