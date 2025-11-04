#!/usr/bin/env python3
"""Reorganize spell data files from school-based to class-based organization."""

import json
from pathlib import Path
from collections import defaultdict

# Current spell files organized by school
SPELL_FILES = [
    'data/spells/evocation.json',
    'data/spells/restoration.json',
    'data/spells/necromancy.json',
    'data/spells/transmutation.json',
    'data/spells/abjuration.json',
    'data/spells/illusion.json'
]

# New organization by caster class
OUTPUT_DIR = Path('data/spells')

def reorganize_spells():
    """Reorganize spells by caster class instead of spell school."""

    # Collect all spells
    all_spells = {}

    for spell_file in SPELL_FILES:
        file_path = Path(spell_file)
        if not file_path.exists():
            print(f"Warning: {spell_file} not found, skipping...")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            spells = data.get('spells', {})

            for spell_id, spell_data in spells.items():
                all_spells[spell_id] = spell_data

    print(f"Loaded {len(all_spells)} total spells")

    # Organize by class restriction
    spells_by_class = {
        'sorcerer': {},
        'warlock': {},
        'cleric': {},
        'druid': {},
        'multi_class': {}  # Spells with no class restriction
    }

    for spell_id, spell_data in all_spells.items():
        class_restriction = spell_data.get('class_restriction', '').lower()

        if class_restriction in spells_by_class:
            spells_by_class[class_restriction][spell_id] = spell_data
        elif not class_restriction:
            spells_by_class['multi_class'][spell_id] = spell_data
        else:
            print(f"Warning: Unknown class restriction '{class_restriction}' for spell {spell_id}")
            spells_by_class['multi_class'][spell_id] = spell_data

    # Print statistics
    print("\nSpells by caster type:")
    for class_type, spells in spells_by_class.items():
        print(f"  {class_type.replace('_', ' ').title()}: {len(spells)} spells")

    # Create new spell files organized by class
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for class_type, spells in spells_by_class.items():
        if not spells:
            continue

        # Sort spells by level, then name
        sorted_spells = dict(sorted(
            spells.items(),
            key=lambda x: (x[1].get('level', 1), x[1].get('name', x[0]))
        ))

        output_file = OUTPUT_DIR / f'{class_type}_spells.json'

        output_data = {
            "spells": sorted_spells
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)

        print(f"✓ Created {output_file} with {len(sorted_spells)} spells")

    # Create a summary file showing spell distribution
    summary_file = OUTPUT_DIR / 'spell_organization_summary.txt'
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("SPELL ORGANIZATION SUMMARY\n")
        f.write("=" * 60 + "\n\n")

        for class_type, spells in spells_by_class.items():
            if not spells:
                continue

            f.write(f"\n{class_type.replace('_', ' ').upper()}\n")
            f.write("-" * 60 + "\n")

            # Group by level
            by_level = defaultdict(list)
            for spell_id, spell_data in spells.items():
                level = spell_data.get('level', 1)
                by_level[level].append((spell_id, spell_data.get('name', spell_id)))

            for level in sorted(by_level.keys()):
                spell_list = by_level[level]
                f.write(f"\nLevel {level} ({len(spell_list)} spells):\n")
                for spell_id, spell_name in sorted(spell_list, key=lambda x: x[1]):
                    f.write(f"  - {spell_name} ({spell_id})\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write(f"\nTotal spells: {len(all_spells)}\n")

    print(f"\n✓ Created summary file: {summary_file}")

    # Print migration info
    print("\n" + "=" * 60)
    print("MIGRATION NOTES:")
    print("=" * 60)
    print("\nOld files (school-based):")
    for f in SPELL_FILES:
        print(f"  - {f}")
    print("\nNew files (class-based):")
    print("  - data/spells/sorcerer_spells.json")
    print("  - data/spells/warlock_spells.json")
    print("  - data/spells/cleric_spells.json")
    print("  - data/spells/druid_spells.json")
    print("  - data/spells/multi_class_spells.json")
    print("\nYou can keep the old files as backup or remove them.")
    print("\nDon't forget to update:")
    print("  - scripts/generate_spell_scrolls.py (SPELL_FILES list)")
    print("  - Any other scripts that load spell data")

if __name__ == '__main__':
    reorganize_spells()
