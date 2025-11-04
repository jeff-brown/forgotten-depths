#!/usr/bin/env python3
"""Update drain and enhancement spells with proper effect data."""

import json
from pathlib import Path

# Spell files to update
SPELL_FILES = {
    'warlock': 'data/spells/warlock_spells.json',
    'multi_class': 'data/spells/multi_class_spells.json'
}

# Spell effect configurations from the table
SPELL_EFFECTS = {
    # Drain spells (warlock)
    'igadani': {
        'type': 'drain',
        'effect': 'drain_agility',
        'effect_amount': '-2d5',  # -2 to -10
        'area_of_effect': 'Single'
    },
    'rodani': {
        'type': 'drain',
        'effect': 'drain_physique',
        'effect_amount': '-2d5',  # -2 to -10
        'area_of_effect': 'Single'
    },
    'tsudani': {
        'type': 'drain',
        'effect': 'drain_stamina',
        'effect_amount': '-2d5',  # -2 to -10
        'area_of_effect': 'Single'
    },
    'poradani': {
        'type': 'drain',
        'effect': 'drain_body',
        'effect_amount': '-1d5',  # -1 to -5
        'area_of_effect': 'Single'
    },
    'jinasudani': {
        'type': 'drain',
        'effect': 'drain_mental',
        'effect_amount': '-1d5',  # -1 to -5
        'area_of_effect': 'Single'
    },

    # Enhancement spells (multi-class)
    'yari': {
        'type': 'enhancement',
        'effect': 'ac_bonus',
        'effect_amount': '+4',
        'area_of_effect': 'Single',
        'bonus_amount': 4,
        'duration': 600
    },
    'yarimaru': {
        'type': 'enhancement',
        'effect': 'ac_bonus',
        'effect_amount': '+2',
        'area_of_effect': 'Area',
        'bonus_amount': 2,
        'duration': 600
    },
    'igatok': {
        'type': 'enhancement',
        'effect': 'enhance_agility',
        'effect_amount': '+5d4',  # +5 to +20
        'area_of_effect': 'Single'
    },
    'rotok': {
        'type': 'enhancement',
        'effect': 'enhance_physique',
        'effect_amount': '+5d4',  # +5 to +20
        'area_of_effect': 'Single'
    },
    'tsutok': {
        'type': 'enhancement',
        'effect': 'enhance_stamina',
        'effect_amount': '+5d4',  # +5 to +20
        'area_of_effect': 'Single'
    },
    'poratok': {
        'type': 'enhancement',
        'effect': 'enhance_body',
        'effect_amount': '+2d5',  # +2 to +10
        'area_of_effect': 'Single'
    },
    'jinasutok': {
        'type': 'enhancement',
        'effect': 'enhance_mental',
        'effect_amount': '+2d5',  # +2 to +10
        'area_of_effect': 'Single'
    },
}

def update_drain_enhancement_spells():
    """Update drain and enhancement spells with proper effects."""

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

        # Update spells with effect data
        for spell_id, effect_data in SPELL_EFFECTS.items():
            if spell_id in spells:
                spell = spells[spell_id]

                # Update type
                spell['type'] = effect_data['type']

                # Update effect
                if 'effect' not in spell or spell.get('effect') != effect_data['effect']:
                    spell['effect'] = effect_data['effect']

                # Update effect_amount
                spell['effect_amount'] = effect_data['effect_amount']

                # Update area_of_effect
                spell['area_of_effect'] = effect_data['area_of_effect']

                # Add bonus_amount and duration for AC bonus spells
                if 'bonus_amount' in effect_data:
                    spell['bonus_amount'] = effect_data['bonus_amount']
                if 'duration' in effect_data:
                    spell['duration'] = effect_data['duration']

                updated_count += 1
                print(f"  {spell.get('name', spell_id)}: type={effect_data['type']}, effect={effect_data['effect']}, amount={effect_data['effect_amount']}, area={effect_data['area_of_effect']}")

        # Write back to file if changes were made
        if updated_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            print(f"✓ Updated {file_path}: {updated_count} spells")
            print()
            total_updated += updated_count

    print("=" * 60)
    print(f"✓ Total drain/enhancement spells updated: {total_updated}")
    print("\nDrain spells (5):")
    print("  - igadani, rodani, tsudani (single stat -2 to -10)")
    print("  - poradani, jinasudani (multi-stat -1 to -5)")
    print("\nEnhancement spells (7):")
    print("  - yari, yarimaru (armor bonus)")
    print("  - igatok, rotok, tsutok (single stat +5 to +20)")
    print("  - poratok, jinasutok (multi-stat +2 to +10)")

if __name__ == '__main__':
    update_drain_enhancement_spells()
