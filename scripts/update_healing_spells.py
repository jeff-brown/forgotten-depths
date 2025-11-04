#!/usr/bin/env python3
"""Update healing spells with proper effect data."""

import json
from pathlib import Path

# Spell files to update
SPELL_FILES = {
    'cleric': 'data/spells/cleric_spells.json',
    'multi_class': 'data/spells/multi_class_spells.json'
}

# Healing spell configurations from the table
HEALING_SPELLS = {
    # Cleric healing spells
    'motu': {
        'type': 'heal',
        'effect': 'heal_hit_points',
        'heal_amount': '10-50',
        'area_of_effect': 'Single',
        'scales_with_level': 'No'
    },
    'kamotu': {
        'type': 'heal',
        'effect': 'heal_hit_points',
        'heal_amount': '16-48',
        'area_of_effect': 'Single',
        'scales_with_level': 'No'
    },
    'gimotu': {
        'type': 'heal',
        'effect': 'heal_hit_points',
        'heal_amount': '20-80',
        'area_of_effect': 'Single',
        'scales_with_level': 'No'
    },
    'kusamotu': {
        'type': 'heal',
        'effect': 'heal_hit_points',
        'heal_amount': '30-150',
        'area_of_effect': 'Single',
        'scales_with_level': 'Yes'
    },
    'motumaru': {
        'type': 'heal',
        'effect': 'heal_hit_points',
        'heal_amount': '10-30',
        'area_of_effect': 'Area',
        'scales_with_level': 'No'
    },
    'kamotumaru': {
        'type': 'heal',
        'effect': 'heal_hit_points',
        'heal_amount': '16-32',
        'area_of_effect': 'Area',
        'scales_with_level': 'No'
    },
    'gimotumaru': {
        'type': 'heal',
        'effect': 'heal_hit_points',
        'heal_amount': '20-60',
        'area_of_effect': 'Area',
        'scales_with_level': 'No'
    },
    'kusamotumaru': {
        'type': 'heal',
        'effect': 'heal_hit_points',
        'heal_amount': '30-120',
        'area_of_effect': 'Area',
        'scales_with_level': 'Yes'
    },

    # Multi-class utility healing spells
    'fadi': {
        'type': 'heal',
        'effect': 'regeneration',
        'heal_amount': '8d2-6',
        'area_of_effect': 'Single',
        'scales_with_level': 'No'
    },
    'kotari': {
        'type': 'heal',
        'effect': 'cure_hunger',
        'area_of_effect': 'Single',
        'scales_with_level': 'No'
    },
    'dobudani': {
        'type': 'heal',
        'effect': 'cure_poison',
        'area_of_effect': 'Single',
        'scales_with_level': 'No'
    },
    'takumi': {
        'type': 'heal',
        'effect': 'cure_paralysis',
        'area_of_effect': 'Single',
        'scales_with_level': 'No'
    },
    'ganazi': {
        'type': 'heal',
        'effect': 'cure_drain',
        'area_of_effect': 'Single',
        'scales_with_level': 'No'
    },
    'dobudanimaru': {
        'type': 'heal',
        'effect': 'cure_poison',
        'area_of_effect': 'Area',
        'scales_with_level': 'No'
    },
    'kotarimaru': {
        'type': 'heal',
        'effect': 'cure_hunger',
        'area_of_effect': 'Area',
        'scales_with_level': 'No'
    },
}

def update_healing_spells():
    """Update healing spells with proper effects."""

    total_updated = 0

    for file_type, spell_file in SPELL_FILES.items():
        file_path = Path(spell_file)
        if not file_path.exists():
            print(f"Warning: {spell_file} not found, skipping...")
            continue

        # Load the spell file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        spells = data.get('spells', {})
        updated_count = 0

        # Update spells with healing data
        for spell_id, heal_data in HEALING_SPELLS.items():
            if spell_id in spells:
                spell = spells[spell_id]

                # Update type
                spell['type'] = heal_data['type']

                # Update effect
                spell['effect'] = heal_data['effect']

                # Update heal_amount if present
                if 'heal_amount' in heal_data:
                    spell['heal_amount'] = heal_data['heal_amount']

                # Update area_of_effect
                spell['area_of_effect'] = heal_data['area_of_effect']

                # Update scales_with_level
                spell['scales_with_level'] = heal_data['scales_with_level']

                updated_count += 1
                heal_info = f"heal={heal_data.get('heal_amount', 'N/A')}" if 'heal_amount' in heal_data else f"effect={heal_data['effect']}"
                print(f"  {spell.get('name', spell_id)}: type={heal_data['type']}, {heal_info}, area={heal_data['area_of_effect']}, scales={heal_data['scales_with_level']}")

        # Write back to file if changes were made
        if updated_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            print(f"✓ Updated {file_path}: {updated_count} spells")
            print()
            total_updated += updated_count

    print("=" * 60)
    print(f"✓ Total healing spells updated: {total_updated}")
    print("\nHealing spell categories:")
    print("  Direct healing (8): motu, kamotu, gimotu, kusamotu, motumaru, kamotumaru, gimotumaru, kusamotumaru")
    print("  Cure effects (5): dobudani (poison), takumi (paralysis), ganazi (drain), dobudanimaru (poison area), kotarimaru (hunger area)")
    print("  Regeneration (1): fadi")
    print("  Cure hunger (1): kotari")
    print("\nSpells that scale with level (2): kusamotu, kusamotumaru")

if __name__ == '__main__':
    update_healing_spells()
