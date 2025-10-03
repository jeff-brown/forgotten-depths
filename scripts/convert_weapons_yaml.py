#!/usr/bin/env python3
"""Convert weapons.yaml to Forgotten Depths items.json format."""

import json
import yaml
from pathlib import Path

def convert_weapon_item(weapon_id, weapon_data):
    """Convert a single weapon item from YAML to JSON format."""
    # Get basic properties
    short_name = weapon_data.get('type', f'weapon_{weapon_id}')
    long_name = weapon_data.get('long', short_name)
    min_damage = weapon_data.get('min_damage', 1)
    max_damage = weapon_data.get('max_damage', 2)
    weight = weapon_data.get('weight', 10)
    value = weapon_data.get('value', 10)
    level = weapon_data.get('level', 1)
    effect = weapon_data.get('effect', '')
    magic_type = weapon_data.get('magic_type', 0)
    ranged_1 = weapon_data.get('ranged_1', 0)
    ranged_2 = weapon_data.get('ranged_2', 0)

    # Create item ID from type name
    item_id = short_name.lower().replace(' ', '_')

    # Determine weapon type and material
    type_to_category = {
        'dagger': ('dagger', 'steel'),
        'quarterstaff': ('staff', 'wood'),
        'shortsword': ('sword', 'steel'),
        'mace': ('mace', 'iron'),
        'warhammer': ('hammer', 'iron'),
        'longsword': ('sword', 'steel'),
        'battleax': ('axe', 'steel'),
        'battleaxe': ('axe', 'steel'),
        'morningstar': ('mace', 'iron'),
        'broadsword': ('sword', 'steel'),
        'flail': ('flail', 'iron'),
        'halberd': ('polearm', 'steel'),
        'greatsword': ('sword', 'steel'),
        'short bow': ('bow', 'wood'),
        'long bow': ('bow', 'wood'),
        'crossbow': ('crossbow', 'wood'),
        'great bow': ('bow', 'wood'),
        'sling': ('sling', 'leather'),
        'blowgun': ('blowgun', 'wood'),
        'stick': ('club', 'wood'),
        'wooden mallet': ('hammer', 'wood'),
    }

    # Magical weapons
    if 'mithril' in short_name:
        weapon_type, material = 'sword', 'mithril'
    elif 'dark' in short_name and 'sword' in short_name:
        weapon_type, material = 'sword', 'darksteel'
    elif 'rimeax' in short_name:
        weapon_type, material = 'axe', 'enchanted_steel'
    elif 'pyrehammer' in short_name:
        weapon_type, material = 'hammer', 'enchanted_steel'
    elif 'levinblade' in short_name:
        weapon_type, material = 'sword', 'enchanted_steel'
    elif 'elven bow' in short_name:
        weapon_type, material = 'bow', 'enchanted_wood'
    elif 'dwarven' in short_name:
        weapon_type, material = 'axe', 'dwarven_steel'
    elif 'demon sword' in short_name:
        weapon_type, material = 'sword', 'demonic'
    elif 'animate sword' in short_name:
        weapon_type, material = 'sword', 'animated'
    elif 'crystalline' in short_name:
        weapon_type, material = 'sword', 'crystal'
    elif 'glowing' in short_name and 'sword' in short_name:
        weapon_type, material = 'sword', 'enchanted_steel'
    elif 'flaming' in short_name and 'staff' in short_name:
        weapon_type, material = 'staff', 'enchanted_wood'
    elif 'flaming' in short_name and 'greatsword' in short_name:
        weapon_type, material = 'sword', 'enchanted_steel'
    elif 'smouldering' in short_name and 'axe' in short_name:
        weapon_type, material = 'axe', 'enchanted_steel'
    elif 'smouldering' in short_name and 'spear' in short_name:
        weapon_type, material = 'polearm', 'enchanted_steel'
    elif 'bardiche' in short_name:
        weapon_type, material = 'polearm', 'enchanted_steel'
    elif 'sabre' in short_name:
        weapon_type, material = 'sword', 'enchanted_steel'
    # Natural weapons (monster attacks)
    elif any(x in short_name for x in ['claws', 'talons', 'teeth', 'bite', 'tentacle',
                                        'branch', 'vines', 'fists', 'beak', 'tusks',
                                        'mouth', 'maw', 'mandibles', 'horns', 'tendrils',
                                        'pincers', 'nails']):
        weapon_type, material = 'natural', 'bone'
    # Other weapons
    elif 'sceptre' in short_name:
        weapon_type, material = 'mace', 'darksteel'
    elif 'bone hammer' in short_name:
        weapon_type, material = 'hammer', 'bone'
    elif 'club' in short_name:
        weapon_type, material = 'club', 'wood'
    elif 'spear' in short_name:
        weapon_type, material = 'polearm', 'steel'
    elif 'rod' in short_name:
        weapon_type, material = 'staff', 'crystal'
    else:
        weapon_type, material = type_to_category.get(short_name, ('weapon', 'steel'))

    # Create proper capitalized name
    if long_name.startswith('a '):
        display_name = long_name[2:].title()
    elif long_name.startswith('an '):
        display_name = long_name[3:].title()
    else:
        display_name = long_name.title()

    # Create descriptive text based on weapon type
    descriptions = {
        'dagger': f"A small, sharp {display_name.lower()} perfect for quick strikes.",
        'quarterstaff': f"A sturdy wooden staff useful for both offense and defense.",
        'shortsword': f"A versatile short blade favored by adventurers.",
        'mace': f"A heavy mace designed to crush armor and bone.",
        'warhammer': f"A powerful warhammer that delivers devastating blows.",
        'longsword': f"A well-balanced longsword with excellent reach.",
        'battleax': f"A fearsome battle axe capable of cleaving through armor.",
        'morningstar': f"A spiked morningstar that inflicts brutal wounds.",
        'broadsword': f"A wide-bladed broadsword with deadly cutting power.",
        'flail': f"A weighted flail that strikes with unpredictable force.",
        'halberd': f"A long polearm combining axe, spike, and hook.",
        'greatsword': f"A massive two-handed sword wielded by the strongest warriors.",
        'rimeax': f"A frost-enchanted axe that unleashes {effect} on impact.",
        'pyrehammer': f"A flame-wreathed hammer that delivers {effect} with each strike.",
        'levinblade': f"A lightning-charged blade that releases {effect} upon hitting foes.",
        'short bow': f"A compact bow suitable for hunting and skirmishing.",
        'long bow': f"A powerful longbow with excellent range and accuracy.",
        'crossbow': f"A mechanical crossbow that fires deadly bolts.",
        'great bow': f"An oversized bow requiring great strength to draw.",
        'elven bow': f"An elegant elven bow imbued with magical energy, releasing {effect}.",
        'sling': f"A simple leather sling for hurling stones.",
        'blowgun': f"A hollow tube for launching poisoned darts silently.",
        'mithril sword': f"A legendary blade forged from gleaming mithril.",
        'darksword': f"A shadowy blade that seems to absorb light.",
        'stick': f"A crude wooden stick with minimal offensive capability.",
        'wooden mallet': f"A simple wooden mallet used as an improvised weapon.",
        'dwarven battleax': f"A masterwork battleaxe forged in the deep halls by dwarven smiths.",
        'demon sword': f"An unholy blade wreathed in {effect}, forged in the depths of hell.",
        'animate sword': f"A sentient blade that channels {effect} through its wielder.",
        'glowing sword': f"A radiant sword that emanates holy light.",
        'crystalline sword': f"A blade of pure crystal that refracts light into deadly rainbows.",
        'flaming greatsword': f"A massive greatsword wreathed in perpetual flames.",
        'smouldering great axe': f"An enormous axe that smolders with barely contained fire.",
        'smouldering great spear': f"A legendary spear crackling with volcanic heat.",
        'glowing bardiche': f"A polearm that shines with divine radiance.",
        'huge glowing sabre': f"An oversized sabre pulsing with magical energy.",
    }

    # Natural weapon descriptions
    natural_descriptions = {
        'tentacle': "A writhing appendage that grasps and crushes.",
        'thorny branch': "A gnarled branch covered in wicked thorns.",
        'gnashing teeth': "Sharp teeth designed for tearing flesh.",
        'huge gnashing teeth': "Massive fangs capable of rending armor.",
        'big pointy teeth': "Needle-sharp teeth that pierce deeply.",
        'burning claws': "Claws wreathed in hellfire.",
        'choking vines': "Thick vines that constrict and suffocate.",
        'demonic claws': "Cursed talons that rend both flesh and soul.",
        'shadow claws': "Ephemeral claws formed from pure darkness.",
        'claws': "Sharp claws for slashing attacks.",
        'wicked claws': "Cruelly curved claws that inflict grievous wounds.",
        'razor sharp talons': "Talons honed to a razor's edge.",
        'yellowish nails': "Diseased nails that carry infection.",
        'hellish claws': "Infernal claws burning with unholy fire.",
        'vicious bite': "A powerful bite attack.",
        'tendrils': "Grasping tendrils that entangle prey.",
        'pincers': "Crushing pincers like those of a giant crab.",
        'gaping mouth': "A cavernous maw filled with teeth.",
        'toothy maw': "A tooth-lined mouth built for devouring.",
        'mandibles': "Insectoid mandibles that scissor together.",
        'curved horns': "Powerful horns for goring attacks.",
        'wicked bite': "A bite attack that tears deeply.",
        'savage bite': "A ferocious bite that maims.",
        'tusks': "Sharp tusks for gouging.",
        'clenched fists': "Massive fists that pummel foes.",
        'hooked beak': "A sharp, hooked beak for rending.",
        'talons': "Sharp talons for gripping and tearing.",
        'huge talons': "Enormous talons capable of seizing large prey.",
        'enormous talons': "Colossal talons that can crush stone.",
        'crystalline talons': "Razor-sharp talons formed from magical crystal.",
        'gaping maw': "A massive mouth that swallows prey whole.",
    }

    # Use specific description if available, otherwise generic
    if short_name in descriptions:
        description = descriptions[short_name]
    elif short_name in natural_descriptions:
        description = natural_descriptions[short_name]
    else:
        description = f"{display_name} used for combat."

    # Build damage string in dice notation (XdY+Z format)
    # Convert min/max damage to dice notation
    damage_range = max_damage - min_damage + 1

    # Try to find a reasonable dice representation
    # Common dice: d2, d3, d4, d6, d8, d10, d12, d20
    dice_sizes = [2, 3, 4, 6, 8, 10, 12, 20, 100]

    best_match = None
    for die_size in dice_sizes:
        for num_dice in range(1, 21):  # Try up to 20 dice
            for bonus in range(-10, 100):  # Try bonuses from -10 to +99
                calc_min = num_dice + bonus
                calc_max = (num_dice * die_size) + bonus

                if calc_min == min_damage and calc_max == max_damage:
                    best_match = (num_dice, die_size, bonus)
                    break
            if best_match:
                break
        if best_match:
            break

    if best_match:
        num_dice, die_size, bonus = best_match
        if bonus > 0:
            damage = f"{num_dice}d{die_size}+{bonus}"
        elif bonus < 0:
            damage = f"{num_dice}d{die_size}{bonus}"
        else:
            damage = f"{num_dice}d{die_size}"
    else:
        # Fallback to simple range notation if no dice match found
        damage = f"{min_damage}-{max_damage}"

    # Build the item object
    item = {
        "name": display_name,
        "type": "weapon",
        "weight": weight / 10,  # Convert to more reasonable weight
        "base_value": value,
        "description": description,
        "properties": {
            "damage": damage,
            "weapon_type": weapon_type,
            "material": material,
            "required_level": level
        }
    }

    # Add magical properties if present
    if magic_type > 0 or effect:
        item["properties"]["magical"] = True
    if effect and effect not in description:
        item["properties"]["effect"] = effect

    # Add ranged properties if ranged weapon
    if ranged_1 > 0 or ranged_2 > 0:
        item["properties"]["ranged"] = True
        if ranged_1 > 0:
            item["properties"]["min_range"] = ranged_1
        if ranged_2 > 0:
            item["properties"]["max_range"] = ranged_2

    return item_id, item

def main():
    """Main conversion function."""
    # Paths
    weapons_yaml = Path('data/items/weapons.yaml')
    items_json = Path('data/items/items.json')

    # Read weapons YAML
    print(f"Reading {weapons_yaml}...")
    with open(weapons_yaml, 'r') as f:
        weapons_data = yaml.safe_load(f)

    print(f"Found {len(weapons_data)} weapon items")

    # Read existing items.json
    print(f"Reading {items_json}...")
    with open(items_json, 'r') as f:
        items_data = json.load(f)

    # Convert weapon items
    converted_count = 0
    skipped_count = 0

    for weapon_id, weapon_info in weapons_data.items():
        item_id, item = convert_weapon_item(weapon_id, weapon_info)

        # Check if already exists
        if item_id in items_data['items']:
            print(f"Skipping {item_id} (already exists)")
            skipped_count += 1
            continue

        # Add to items
        items_data['items'][item_id] = item
        converted_count += 1
        print(f"Added: {item_id} - {item['name']} (Damage: {item['properties']['damage']})")

    # Write back to items.json
    print(f"\nWriting updated items to {items_json}...")
    with open(items_json, 'w') as f:
        json.dump(items_data, f, indent=2)

    print(f"\n=== Conversion Summary ===")
    print(f"Weapon items converted: {converted_count}")
    print(f"Items skipped (already exist): {skipped_count}")
    print(f"Total items in items.json: {len(items_data['items'])}")
    print("\nConversion complete!")

if __name__ == '__main__':
    main()
