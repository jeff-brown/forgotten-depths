#!/usr/bin/env python3
"""Convert armor.yaml to Forgotten Depths items.json format."""

import json
import yaml
from pathlib import Path

def convert_armor_item(armor_id, armor_data):
    """Convert a single armor item from YAML to JSON format."""
    # Get basic properties
    short_name = armor_data.get('short', f'armor_{armor_id}')
    long_name = armor_data.get('long', short_name)
    ac = armor_data.get('ac', 0)
    weight = armor_data.get('weight', 10)
    value = armor_data.get('value', 10)
    level = armor_data.get('level', 1)
    armor_type = armor_data.get('type', 'armor')

    # Create item ID from short name
    item_id = short_name.lower().replace(' ', '_')

    # Map armor type to material and armor class
    type_to_material = {
        'cloak': 'cloth',
        'robes': 'cloth',
        'cuirass': 'leather',
        'breastplate': 'steel',
        'ringmail': 'iron',
        'chainmail': 'iron',
        'scalemail': 'steel',
        'bandmail': 'steel',
        'platemail': 'steel',
        'banded': 'steel',
        'plate': 'steel'
    }

    material = type_to_material.get(armor_type, 'leather')

    # Determine armor type category
    if armor_type in ['cloak', 'robes']:
        armor_category = 'light'
    elif armor_type in ['cuirass', 'leather']:
        armor_category = 'light'
    elif armor_type in ['breastplate', 'ringmail', 'chainmail', 'scalemail']:
        armor_category = 'medium'
    else:
        armor_category = 'heavy'

    # Create proper capitalized name
    if long_name.startswith('a '):
        display_name = long_name[2:].title()
    elif long_name.startswith('an '):
        display_name = long_name[3:].title()
    else:
        display_name = long_name.title()

    # Build the item object
    item = {
        "name": display_name,
        "type": "armor",
        "weight": weight / 10,  # Convert to more reasonable weight
        "base_value": value,
        "description": f"{display_name} providing {ac} armor class.",
        "properties": {
            "armor_class": ac,
            "armor_type": armor_category,
            "material": material,
            "required_level": level
        }
    }

    return item_id, item

def main():
    """Main conversion function."""
    # Paths
    armor_yaml = Path('data/items/armor.yaml')
    items_json = Path('data/items/items.json')

    # Read armor YAML
    print(f"Reading {armor_yaml}...")
    with open(armor_yaml, 'r') as f:
        armor_data = yaml.safe_load(f)

    print(f"Found {len(armor_data)} armor items")

    # Read existing items.json
    print(f"Reading {items_json}...")
    with open(items_json, 'r') as f:
        items_data = json.load(f)

    # Convert armor items
    converted_count = 0
    skipped_count = 0

    for armor_id, armor_info in armor_data.items():
        item_id, item = convert_armor_item(armor_id, armor_info)

        # Check if already exists
        if item_id in items_data['items']:
            print(f"Skipping {item_id} (already exists)")
            skipped_count += 1
            continue

        # Add to items
        items_data['items'][item_id] = item
        converted_count += 1
        print(f"Added: {item_id} - {item['name']} (AC: {item['properties']['armor_class']})")

    # Write back to items.json
    print(f"\nWriting updated items to {items_json}...")
    with open(items_json, 'w') as f:
        json.dump(items_data, f, indent=2)

    print(f"\n=== Conversion Summary ===")
    print(f"Armor items converted: {converted_count}")
    print(f"Items skipped (already exist): {skipped_count}")
    print(f"Total items in items.json: {len(items_data['items'])}")
    print("\nConversion complete!")

if __name__ == '__main__':
    main()
