#!/usr/bin/env python3
"""Generate spell scroll items for all spells in the game."""

import json
from pathlib import Path

# Spell files to process (organized by caster class)
SPELL_FILES = [
    'data/spells/sorcerer_spells.json',
    'data/spells/warlock_spells.json',
    'data/spells/cleric_spells.json',
    'data/spells/druid_spells.json',
    'data/spells/multi_class_spells.json'
]

OUTPUT_FILE = 'data/items/spell_scroll.json'

def calculate_scroll_value(spell_level, spell_mana_cost):
    """Calculate base value for a spell scroll based on level and mana cost."""
    # Base value increases exponentially with level
    # Level 1: ~50-100, Level 9: ~1000+
    base = 30 + (spell_level ** 2) * 10
    # Add mana cost factor
    mana_factor = spell_mana_cost * 0.5
    return int(base + mana_factor)

def calculate_min_intelligence(spell_level):
    """Calculate minimum intelligence requirement."""
    # Level 1-2: 10 INT, Level 3-4: 12 INT, Level 5-6: 14 INT, etc.
    return 10 + ((spell_level - 1) // 2) * 2

def generate_scroll_items():
    """Generate spell scroll items from all spell definitions."""
    all_scrolls = {}

    for spell_file in SPELL_FILES:
        file_path = Path(spell_file)
        if not file_path.exists():
            print(f"Warning: {spell_file} not found, skipping...")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            spells = data.get('spells', {})

            for spell_id, spell_data in spells.items():
                spell_name = spell_data.get('name', spell_id.title())
                spell_level = spell_data.get('level', 1)
                spell_school = spell_data.get('school', 'evocation')
                spell_mana_cost = spell_data.get('mana_cost', 10)
                spell_description = spell_data.get('description', 'A magical spell')

                # Create scroll ID
                scroll_id = f"scroll_{spell_id}"

                # Calculate scroll value
                base_value = calculate_scroll_value(spell_level, spell_mana_cost)

                # Calculate requirements
                min_intelligence = calculate_min_intelligence(spell_level)
                min_level = max(1, spell_level - 1)  # Can learn spell 1 level early

                # Create scroll item
                scroll_item = {
                    "name": f"Scroll of {spell_name}",
                    "type": "spell_scroll",
                    "weight": 0.1,
                    "base_value": base_value,
                    "description": f"A scroll inscribed with the {spell_name} spell. {spell_description}. Reading it will teach you the spell permanently.",
                    "properties": {
                        "spell_id": spell_id,
                        "spell_level": spell_level,
                        "spell_school": spell_school,
                        "consumable": True,
                        "requirements": {
                            "min_level": min_level,
                            "min_intelligence": min_intelligence
                        }
                    }
                }

                all_scrolls[scroll_id] = scroll_item
                print(f"Created scroll for {spell_name} (Level {spell_level}, {spell_school})")

    # Sort scrolls by spell level then alphabetically
    sorted_scrolls = dict(sorted(
        all_scrolls.items(),
        key=lambda x: (x[1]['properties']['spell_level'], x[0])
    ))

    # Write to output file
    output = {
        "items": sorted_scrolls
    }

    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Generated {len(sorted_scrolls)} spell scrolls")
    print(f"✓ Written to {OUTPUT_FILE}")

    # Print statistics
    by_level = {}
    for scroll_id, scroll_data in sorted_scrolls.items():
        level = scroll_data['properties']['spell_level']
        by_level[level] = by_level.get(level, 0) + 1

    print("\nScrolls by level:")
    for level in sorted(by_level.keys()):
        print(f"  Level {level}: {by_level[level]} scrolls")

if __name__ == '__main__':
    generate_scroll_items()
