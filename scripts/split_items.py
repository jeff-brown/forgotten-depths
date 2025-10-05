#!/usr/bin/env python3
"""Split items.json into separate files by type."""

import json
import os
from collections import defaultdict

def split_items():
    # Load the main items file
    with open('data/items/items.json', 'r') as f:
        data = json.load(f)

    items = data.get('items', {})

    # Group items by type
    items_by_type = defaultdict(dict)
    for item_id, item_data in items.items():
        item_type = item_data.get('type', 'misc')
        items_by_type[item_type][item_id] = item_data

    # Create directory structure
    items_dir = 'data/items'
    os.makedirs(items_dir, exist_ok=True)

    # Write each type to a separate file
    for item_type, type_items in items_by_type.items():
        filename = f"{items_dir}/{item_type}.json"
        with open(filename, 'w') as f:
            json.dump({"items": type_items}, f, indent=2)
        print(f"Created {filename} with {len(type_items)} items")

    print(f"\nTotal: {len(items)} items split into {len(items_by_type)} files")
    print("\nItem types:")
    for item_type in sorted(items_by_type.keys()):
        print(f"  - {item_type}: {len(items_by_type[item_type])} items")

if __name__ == '__main__':
    split_items()
