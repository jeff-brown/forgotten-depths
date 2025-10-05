#!/usr/bin/env python3
"""Split spells.json into school-specific files."""

import json
from pathlib import Path
from collections import defaultdict

def main():
    # Read the spells file
    spells_file = Path("data/spells/spells.json")

    if not spells_file.exists():
        print(f"Error: {spells_file} not found")
        return

    with open(spells_file, 'r', encoding='utf-8') as f:
        all_spells = json.load(f)

    # Group spells by school
    spells_by_school = defaultdict(dict)
    for spell_id, spell_data in all_spells.items():
        school = spell_data.get('school', 'unknown')
        spells_by_school[school][spell_id] = spell_data

    # Create output directory (already exists)
    output_dir = Path("data/spells")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write each school to a separate file
    total_written = 0
    for school, school_spells in spells_by_school.items():
        output_file = output_dir / f"{school}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"spells": school_spells}, f, indent=2, ensure_ascii=False)

        print(f"Created {output_file} with {len(school_spells)} spells")
        total_written += len(school_spells)

    # Backup original file
    backup_file = Path("data/spells/spells.json.backup")
    import shutil
    shutil.copy2(spells_file, backup_file)
    print(f"\nBacked up original to {backup_file}")

    print(f"\nTotal spells written: {total_written}")
    print(f"Total schools: {len(spells_by_school)}")
    print(f"Schools: {', '.join(sorted(spells_by_school.keys()))}")

if __name__ == "__main__":
    main()
