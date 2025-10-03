#!/usr/bin/env python3
"""Convert spells.yaml to Forgotten Depths spells.json format."""

import json
import yaml
from pathlib import Path

def convert_spell(spell_id, spell_data):
    """Convert a single spell from YAML to JSON format."""
    # Get basic properties
    name = spell_data.get('name', f'spell_{spell_id}')
    desc = spell_data.get('desc', '')
    spell_type = spell_data.get('type', 1)
    cost = spell_data.get('cost', 5)
    min_effect = spell_data.get('min_spell_effect', 0)
    max_effect = spell_data.get('max_spell_effect', 0)
    target = spell_data.get('target', 4)
    mana_level = spell_data.get('mana', 1)

    # Spell properties - ensure all are integers, handle string values
    def safe_int(value, default=0):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    armor_increase = safe_int(spell_data.get('armor_increase', 0))
    cure_poison = safe_int(spell_data.get('cure_poison', 0))
    increase_stat = safe_int(spell_data.get('increase_stat', 0))
    decrease_stat = safe_int(spell_data.get('decrease_stat', 0))
    life_steal = safe_int(spell_data.get('life_steal', 0))
    mana_drain = safe_int(spell_data.get('mana_drain', 0))
    poison_effect = safe_int(spell_data.get('poison_effect', 0))
    hurt_moral = safe_int(spell_data.get('hurt_moral', 0))
    based_on_level = safe_int(spell_data.get('based_on_level', 0))

    # Create spell ID from name
    spell_id_str = name.lower().replace(' ', '_')

    # Map spell types to categories
    # Type: 1=damage, 2=area damage, 3=heal, 4=buff, 5=debuff, 6=regen
    type_mapping = {
        1: 'damage',
        2: 'damage',  # area damage
        3: 'heal',
        4: 'buff',
        5: 'debuff',
        6: 'heal',  # regen
    }

    spell_category = type_mapping.get(spell_type, 'damage')

    # Map target to range
    # Target: 1=self, 2=friendly, 3=area, 4=enemy
    target_mapping = {
        1: 'self',
        2: 'friendly',
        3: 'area',
        4: 'ranged',
    }

    spell_range = target_mapping.get(target, 'ranged')

    # Determine spell school based on description and type
    schools = {
        'ice': 'evocation',
        'frost': 'evocation',
        'cold': 'evocation',
        'fire': 'evocation',
        'flame': 'evocation',
        'lightning': 'evocation',
        'thunder': 'evocation',
        'heal': 'restoration',
        'cure': 'restoration',
        'regen': 'restoration',
        'shield': 'abjuration',
        'armor': 'abjuration',
        'protect': 'abjuration',
        'poison': 'necromancy',
        'death': 'necromancy',
        'drain': 'necromancy',
        'darkness': 'necromancy',
        'light': 'evocation',
        'dispel': 'abjuration',
        'strength': 'transmutation',
        'weak': 'transmutation',
    }

    school = 'evocation'
    desc_lower = desc.lower()
    for keyword, school_name in schools.items():
        if keyword in desc_lower or keyword in name.lower():
            school = school_name
            break

    # Determine damage type
    damage_types = {
        'ice': 'cold',
        'frost': 'cold',
        'cold': 'cold',
        'fire': 'fire',
        'flame': 'fire',
        'lightning': 'lightning',
        'thunder': 'thunder',
        'poison': 'poison',
        'acid': 'acid',
        'thorn': 'piercing',
        'shadow': 'necrotic',
        'death': 'necrotic',
        'light': 'radiant',
        'holy': 'radiant',
    }

    damage_type = 'force'
    for keyword, dmg_type in damage_types.items():
        if keyword in desc_lower or keyword in name.lower():
            damage_type = dmg_type
            break

    # Create proper capitalized name
    display_name = name.title()

    # Build damage/heal dice notation
    if min_effect > 0 and max_effect > 0:
        damage_range = max_effect - min_effect + 1
        # Try to find dice representation
        dice_sizes = [2, 3, 4, 6, 8, 10, 12, 20, 100]

        best_match = None
        for die_size in dice_sizes:
            for num_dice in range(1, 21):
                for bonus in range(-10, 100):
                    calc_min = num_dice + bonus
                    calc_max = (num_dice * die_size) + bonus

                    if calc_min == min_effect and calc_max == max_effect:
                        best_match = (num_dice, die_size, bonus)
                        break
                if best_match:
                    break
            if best_match:
                break

        if best_match:
            num_dice, die_size, bonus = best_match
            if bonus > 0:
                effect_dice = f"{num_dice}d{die_size}+{bonus}"
            elif bonus < 0:
                effect_dice = f"{num_dice}d{die_size}{bonus}"
            else:
                effect_dice = f"{num_dice}d{die_size}"
        else:
            effect_dice = f"{min_effect}-{max_effect}"
    else:
        effect_dice = None

    # Build the spell object
    spell = {
        "name": display_name,
        "description": desc.capitalize() if desc else f"A {spell_category} spell.",
        "type": spell_category,
        "school": school,
        "level": mana_level,
        "mana_cost": cost,
        "range": spell_range,
        "cooldown": 0,
        "requires_target": target == 4
    }

    # Add type-specific properties
    if spell_category == 'damage' and effect_dice:
        spell["damage"] = effect_dice
        spell["damage_type"] = damage_type

    if spell_category == 'heal' and effect_dice:
        spell["heal_amount"] = effect_dice

    if armor_increase > 0:
        spell["effect"] = "ac_bonus"
        spell["bonus_amount"] = armor_increase
        spell["duration"] = 600

    if cure_poison > 0:
        spell["effect"] = "cure_poison"

    if increase_stat > 0:
        spell["effect"] = "stat_boost"
        spell["stat"] = "strength"  # Could be mapped from data
        spell["bonus_amount"] = increase_stat
        spell["duration"] = 600

    if decrease_stat > 0:
        spell["effect"] = "stat_penalty"
        spell["penalty_amount"] = decrease_stat
        spell["duration"] = 600

    if life_steal > 0:
        spell["life_steal"] = True

    if mana_drain > 0:
        spell["mana_drain"] = mana_drain

    if poison_effect > 0:
        spell["poison_damage"] = poison_effect

    return spell_id_str, spell

def main():
    """Main conversion function."""
    # Paths
    spells_yaml = Path('data/items/spells.yaml')
    spells_json = Path('data/spells.json')

    # Read spells YAML
    print(f"Reading {spells_yaml}...")
    with open(spells_yaml, 'r') as f:
        spells_data = yaml.safe_load(f)

    print(f"Found {len(spells_data)} spells")

    # Read existing spells.json
    print(f"Reading {spells_json}...")
    with open(spells_json, 'r') as f:
        existing_spells = json.load(f)

    # Convert spell items
    converted_count = 0
    skipped_count = 0

    for spell_id, spell_info in spells_data.items():
        spell_id_str, spell = convert_spell(spell_id, spell_info)

        # Check if already exists
        if spell_id_str in existing_spells:
            print(f"Skipping {spell_id_str} (already exists)")
            skipped_count += 1
            continue

        # Add to spells
        existing_spells[spell_id_str] = spell
        converted_count += 1
        print(f"Added: {spell_id_str} - {spell['name']} ({spell['type']})")

    # Write back to spells.json
    print(f"\nWriting updated spells to {spells_json}...")
    with open(spells_json, 'w') as f:
        json.dump(existing_spells, f, indent=2)

    print(f"\n=== Conversion Summary ===")
    print(f"Spells converted: {converted_count}")
    print(f"Spells skipped (already exist): {skipped_count}")
    print(f"Total spells in spells.json: {len(existing_spells)}")
    print("\nConversion complete!")

if __name__ == '__main__':
    main()
