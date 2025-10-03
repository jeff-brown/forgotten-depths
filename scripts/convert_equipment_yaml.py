#!/usr/bin/env python3
"""Convert equipment.yaml to Forgotten Depths items.json format."""

import json
import yaml
from pathlib import Path

def convert_equipment_item(equip_id, equip_data):
    """Convert a single equipment item from YAML to JSON format."""
    # Get basic properties
    item_type = equip_data.get('type', f'item_{equip_id}')
    long_name = equip_data.get('long', item_type)
    weight = equip_data.get('weight', 1)
    value = equip_data.get('value', 1)
    level = equip_data.get('level', 0)
    equip_type = equip_data.get('equip_type', 'supply')
    equip_sub_type = equip_data.get('equip_sub_type', 'none')
    effect = equip_data.get('effect', '')
    charges = equip_data.get('charges', 0)
    min_value = equip_data.get('min_value_range', 0)
    max_value = equip_data.get('max_value_range', 0)

    # Create item ID from type name
    item_id = item_type.lower().replace(' ', '_')

    # Create proper capitalized name
    if long_name.startswith('a '):
        display_name = long_name[2:].title()
    elif long_name.startswith('an '):
        display_name = long_name[3:].title()
    elif long_name.startswith('some '):
        display_name = long_name[5:].title()
    else:
        display_name = long_name.title()

    # Determine item type category
    type_mapping = {
        'supply': 'tool',
        'potion': 'consumable',
        'key': 'key',
        'minor magic item': 'magic_item',
        'major magic item': 'magic_item',
        'supply weapon': 'weapon',
        'ranged weapon ammo': 'ammunition',
        'ammo container': 'container',
        'thrown weapon container': 'container',
    }

    item_category = type_mapping.get(equip_type, 'misc')

    # Create descriptions based on item type
    descriptions = {
        'torch': "A wooden torch that provides light in dark places.",
        'rope': "Fifty feet of sturdy hemp rope.",
        'ration of food': "Preserved rations suitable for travel.",
        'waterskin': "A leather waterskin for carrying water.",
        'glowstone': "A magical stone that emanates a soft, eternal light.",
        'heartstone': "A mystical stone that can recall you to safety.",
        'rue potion': "A minor healing potion that restores a small amount of health.",
        'amaranth potion': "A healing potion that restores moderate health.",
        'anemone potion': "A powerful healing potion that restores significant health.",
        'verbena potion': "A potion that cures poison.",
        'yarrow potion': "A potion that restores a small amount of mana.",
        'rowan potion': "A potion that temporarily increases strength.",
        'hyssop potion': "A potion that temporarily increases dexterity.",
        'vervain potion': "A potion that grants temporary invisibility.",
        'horn of frost': "A magical horn that unleashes a blast of frost when sounded.",
        'wand of lightning': "A wand that channels bolts of lightning at your foes.",
        'rod of flame': "A powerful rod that projects blasts of searing flame.",
        'runestaff': "An ancient staff inscribed with powerful runes.",
        'dart': "A small throwing dart.",
        'knife': "A small throwing knife.",
        'spear': "A throwing spear.",
        'axe': "A throwing axe.",
        'arrow': "A wooden arrow with steel tip.",
        'quiver': "A leather quiver for holding arrows.",
        'soulstone': "A rare gem that can capture and hold souls.",
        'manastone': "A crystalline stone that greatly restores mana.",
        'zarynthium potion': "An extremely potent healing potion.",
        'dragon ring': "An ornate ring bearing the mark of dragons.",
        'gome ring': "A mysterious ring of unknown origin.",
        'strato ring': "A ring associated with the upper realms.",
        'pink rose': "A delicate pink rose, preserved by magic.",
        'white rose': "A pristine white rose that never wilts.",
        'red rose': "A vibrant red rose with magical properties.",
        'black rose': "A dark rose that emanates an aura of shadow.",
        'wynharp': "A legendary musical instrument of great power.",
        'rod of power': "An artifact of immense magical power.",
        'flame crystal': "A crystal that burns with eternal flame.",
        'ice crystal': "A crystal frozen in perpetual winter.",
        'case': "A case for storing darts.",
        'stone': "A smooth stone suitable for slinging.",
        'pouch': "A leather pouch for carrying sling stones.",
        'blowdart': "A small poisoned dart for blowguns.",
        'tube': "A tube for storing blowdarts.",
        'small barrel': "A small wooden barrel for storing water.",
        'preserved rations': "Well-preserved food suitable for long journeys.",
    }

    # Keys get special handling
    if equip_type == 'key':
        key_materials = {
            'iron key': 'iron',
            'copper key': 'copper',
            'brass key': 'brass',
            'bronze key': 'bronze',
            'silver key': 'silver',
            'electrum key': 'electrum',
            'gold key': 'gold',
            'platinum key': 'platinum',
            'pearl key': 'pearl',
            'onyx key': 'onyx',
            'jade key': 'jade',
            'ruby key': 'ruby',
            'opal key': 'opal',
            'tigereye key': 'tigereye',
            'quartz key': 'quartz',
            'topaz key': 'topaz',
            'stone key': 'stone',
        }

        material = key_materials.get(item_type, 'metal')
        description = f"A {display_name.lower()} that unlocks specific doors."
    else:
        description = descriptions.get(item_type, f"{display_name} for adventuring.")

    # Build the item object
    item = {
        "name": display_name,
        "type": item_category,
        "weight": weight / 10,  # Convert to more reasonable weight
        "base_value": value,
        "description": description,
        "properties": {
            "required_level": level
        }
    }

    # Add specific properties based on item type
    if equip_sub_type == 'heal' and max_value > 0:
        item["properties"]["restore_health"] = f"{min_value}-{max_value}"

    if equip_sub_type in ['minor mana boost', 'major mana boost']:
        item["properties"]["restore_mana"] = 50 if equip_sub_type == 'major mana boost' else 10

    if equip_sub_type in ['strength boost', 'dexterity boost']:
        item["properties"]["boost_duration"] = max_value
        if equip_sub_type == 'strength boost':
            item["properties"]["strength_bonus"] = 1
        else:
            item["properties"]["dexterity_bonus"] = 1

    if equip_sub_type == 'cure poison':
        item["properties"]["cure_poison"] = True

    if equip_sub_type == 'invisibility':
        item["properties"]["invisibility_duration"] = max_value

    if equip_sub_type == 'light':
        item["properties"]["light_radius"] = 30
        item["properties"]["burn_time"] = 240

    if equip_sub_type == 'eternal light':
        item["properties"]["light_radius"] = 30
        item["properties"]["eternal"] = True

    if equip_sub_type == 'recall':
        item["properties"]["recall"] = True

    if equip_sub_type == 'wand':
        item["properties"]["charges"] = charges
        item["properties"]["magical"] = True
        if effect:
            item["properties"]["effect"] = effect
        if max_value > 0:
            item["properties"]["damage"] = f"{min_value}-{max_value}"

    if equip_sub_type in ['runestaff', 'rod of power', 'flame crystal', 'soulstone']:
        item["properties"]["magical"] = True
        if effect:
            item["properties"]["effect"] = effect

    if equip_type in ['supply weapon', 'ranged weapon ammo']:
        item["type"] = "weapon"
        if max_value > 0:
            item["properties"]["damage"] = f"{min_value}-{max_value}"
        item["properties"]["weapon_type"] = "thrown" if equip_type == 'supply weapon' else "ammunition"
        item["properties"]["material"] = "steel"

    if equip_type in ['ammo container', 'thrown weapon container']:
        item["properties"]["capacity"] = charges

    if equip_sub_type in ['food', 'water']:
        if equip_sub_type == 'food':
            item["properties"]["nutrition"] = max_value // 60 if max_value > 0 else 20
        else:
            item["properties"]["hydration"] = max_value // 30 if max_value > 0 else 30
        if charges > 0:
            item["properties"]["charges"] = charges

    return item_id, item

def main():
    """Main conversion function."""
    # Paths
    equipment_yaml = Path('data/items/equipment.yaml')
    items_json = Path('data/items/items.json')

    # Read equipment YAML
    print(f"Reading {equipment_yaml}...")
    with open(equipment_yaml, 'r') as f:
        equipment_data = yaml.safe_load(f)

    print(f"Found {len(equipment_data)} equipment items")

    # Read existing items.json
    print(f"Reading {items_json}...")
    with open(items_json, 'r') as f:
        items_data = json.load(f)

    # Convert equipment items
    converted_count = 0
    skipped_count = 0

    for equip_id, equip_info in equipment_data.items():
        item_id, item = convert_equipment_item(equip_id, equip_info)

        # Check if already exists
        if item_id in items_data['items']:
            print(f"Skipping {item_id} (already exists)")
            skipped_count += 1
            continue

        # Add to items
        items_data['items'][item_id] = item
        converted_count += 1
        print(f"Added: {item_id} - {item['name']}")

    # Write back to items.json
    print(f"\nWriting updated items to {items_json}...")
    with open(items_json, 'w') as f:
        json.dump(items_data, f, indent=2)

    print(f"\n=== Conversion Summary ===")
    print(f"Equipment items converted: {converted_count}")
    print(f"Items skipped (already exist): {skipped_count}")
    print(f"Total items in items.json: {len(items_data['items'])}")
    print("\nConversion complete!")

if __name__ == '__main__':
    main()
