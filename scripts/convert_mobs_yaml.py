#!/usr/bin/env python3
"""Convert mobs.yaml to Forgotten Depths monsters.json format."""

import json
import random
import yaml
from pathlib import Path

def convert_mob(mob_id, mob_data):
    """Convert a single mob from YAML to JSON format."""
    # Get basic properties
    name = mob_data.get('name', f'mob_{mob_id}')
    description = mob_data.get('description', '')
    level = mob_data.get('level', 1)
    hit_dice = mob_data.get('hit_dice', 1)
    armor = mob_data.get('armor', 0)
    gold = mob_data.get('gold', 0)
    treasure = mob_data.get('treasure', 0)
    combat_skill = mob_data.get('combat_skill', 50)
    spell_skill = mob_data.get('spell_skill', 0)
    morale = mob_data.get('morale', 0)
    regeneration = mob_data.get('regeneration', 0)
    can_track = mob_data.get('can_track', 0)
    num_attacks = mob_data.get('num_attacks', 1)

    # Damage ranges
    min_weapon_damage = mob_data.get('min_weapon_damage', 1)
    max_weapon_damage = mob_data.get('max_weapon_damege', mob_data.get('max_weapon_damage', 2))

    # Special attacks and spells
    special_attacks = mob_data.get('special_attacks', [])
    special_attack_percentage = mob_data.get('special_attack_percentage', 0)
    min_special_damage = mob_data.get('min_special_damage', 0)
    max_special_damage = mob_data.get('max_special_damage', 0)

    spells = mob_data.get('spells', [])
    min_spell = mob_data.get('min_spell', 0)
    max_spell = mob_data.get('max_spell', 0)

    # Determine mob type
    mob_type = mob_data.get('type', name.lower().replace(' ', '_'))
    subtype = mob_data.get('subtype', 0)
    terrain = mob_data.get('terrain', 0)

    # Create monster ID from name
    monster_id = name.lower().replace(' ', '_')

    # Create proper capitalized name
    display_name = name.title()

    # Calculate health based on hit dice (roughly 10 HP per hit die)
    health = max(10, hit_dice * 10)

    # Calculate experience reward based on level
    experience_reward = level * 10

    # Determine if aggressive (higher morale = more aggressive, but default to true for most mobs)
    aggressive = morale >= 0

    # Calculate speed (normalized to 1.0 average)
    # Higher combat skill might indicate faster movement
    speed = 1.0 if combat_skill >= 50 else 0.8

    # Build damage string in dice notation
    damage_range = max_weapon_damage - min_weapon_damage + 1
    dice_sizes = [2, 3, 4, 6, 8, 10, 12, 20, 100]

    best_match = None
    for die_size in dice_sizes:
        for num_dice in range(1, 21):
            for bonus in range(-10, 100):
                calc_min = num_dice + bonus
                calc_max = (num_dice * die_size) + bonus

                if calc_min == min_weapon_damage and calc_max == max_weapon_damage:
                    best_match = (num_dice, die_size, bonus)
                    break
            if best_match:
                break
        if best_match:
            break

    if best_match:
        num_dice, die_size, bonus = best_match
        if bonus > 0:
            damage_dice = f"{num_dice}d{die_size}+{bonus}"
        elif bonus < 0:
            damage_dice = f"{num_dice}d{die_size}{bonus}"
        else:
            damage_dice = f"{num_dice}d{die_size}"
    else:
        damage_dice = f"{min_weapon_damage}-{max_weapon_damage}"

    # Determine gold reward range
    if gold > 0:
        gold_min = max(0, gold - 5)
        gold_max = gold + 10
        gold_reward = [gold_min, gold_max]
    else:
        gold_reward = [0, 0]

    # Build the monster object
    monster = {
        "id": monster_id,
        "name": display_name,
        "description": description if description else f"A {display_name.lower()}.",
        "type": "monster",
        "level": level,
        "health": health,
        "max_health": health,
        "damage_min": min_weapon_damage,
        "damage_max": max_weapon_damage,
        "armor": armor,
        "experience_reward": experience_reward,
        "gold_reward": gold_reward,
        "aggressive": aggressive,
        "speed": speed
    }

    # Add special abilities if present
    abilities = []

    if special_attacks and any(special_attacks):
        # Filter out empty strings and zeros
        valid_attacks = [a for a in special_attacks if a and a != '']
        if valid_attacks:
            abilities.extend(valid_attacks)

    if regeneration > 0:
        abilities.append("regeneration")

    if can_track > 0:
        abilities.append("tracking")

    if num_attacks > 1:
        abilities.append("multiattack")

    if abilities:
        monster["abilities"] = abilities

    # Add resistances/weaknesses based on mob type
    if 'undead' in mob_type or 'skeleton' in name.lower() or 'zombie' in name.lower() or 'ghost' in name.lower():
        monster["type"] = "undead"
        monster["resistances"] = ["poison", "fear"]
        monster["weaknesses"] = ["holy"]

    if 'demon' in name.lower() or 'devil' in name.lower():
        monster["type"] = "demon"
        monster["resistances"] = ["fire", "poison"]
        monster["weaknesses"] = ["holy"]

    if 'dragon' in name.lower():
        monster["type"] = "dragon"
        monster["resistances"] = ["fear"]

    if 'plant' in mob_type or any(x in name.lower() for x in ['vine', 'orchid', 'flower', 'tree']):
        monster["type"] = "plant"

    if 'animal' in mob_type or any(x in name.lower() for x in ['wolf', 'bear', 'rat', 'spider', 'snake']):
        monster["type"] = "animal"

    # Add spell casting if present
    if spell_skill > 0 and spells and any(s for s in spells if s and s != 0):
        monster["spellcaster"] = True
        monster["spell_skill"] = spell_skill

    # Add loot table based on monster type and level
    loot_table = []

    # Define item pools
    low_weapons = ['stick', 'wooden_mallet', 'rusty_dagger', 'dagger', 'quarterstaff']
    mid_weapons = ['shortsword', 'mace', 'short_sword', 'rusty_sword', 'spear', 'knife']
    high_weapons = ['longsword', 'battleax', 'warhammer', 'broadsword', 'flail', 'halberd', 'morningstar']
    epic_weapons = ['greatsword', 'enchanted_blade', 'mithril_sword', 'rimeax', 'pyrehammer', 'levinblade']

    low_armor = ['cloth_robe', 'leather_armor', 'cloak']
    mid_armor = ['ringmail', 'scalemail', 'chainmail', 'cuirass']
    high_armor = ['bandmail', 'platemail', 'breastplate', 'dwarven_scalemail']
    epic_armor = ['dragonscale', 'demonhide', 'champion_armor']

    healing_potions = ['rue_potion', 'amaranth_potion', 'anemone_potion', 'zarynthium_potion']
    mana_potions = ['yarrow_potion', 'manastone']
    buff_potions = ['rowan_potion', 'hyssop_potion', 'vervain_potion', 'verbena_potion']

    low_scrolls = ['scroll_magic_missile', 'scroll_shield', 'scroll_cure_wounds']
    high_scrolls = ['scroll_fireball', 'scroll_lightning_bolt', 'scroll_heal']

    wands = ['horn_of_frost', 'wand_of_lightning', 'rod_of_flame', 'runestaff', 'rod_of_power']

    keys = ['iron_key', 'copper_key', 'brass_key', 'bronze_key', 'silver_key',
            'electrum_key', 'gold_key', 'platinum_key', 'pearl_key', 'onyx_key',
            'jade_key', 'ruby_key', 'opal_key', 'tigereye_key', 'quartz_key', 'topaz_key', 'stone_key']

    rings = ['dragon_ring', 'gome_ring', 'strato_ring', 'ancient_ring']
    roses = ['pink_rose', 'white_rose', 'red_rose', 'black_rose']

    food_items = ['bread', 'cheese', 'dried_meat', 'ration_of_food', 'preserved_rations']

    natural_weapons = ['claws', 'wicked_claws', 'demonic_claws', 'burning_claws', 'shadow_claws',
                       'talons', 'razor_sharp_talons', 'huge_talons', 'enormous_talons', 'crystalline_talons',
                       'gnashing_teeth', 'huge_gnashing_teeth', 'big_pointy_teeth',
                       'tentacle', 'tendrils', 'pincers', 'thorny_branch', 'choking_vines']

    crystals = ['flame_crystal', 'ice_crystal', 'soul_gem', 'soulstone']
    materials = ['bone_fragment', 'dark_essence', 'tattered_cloth', 'small_bone']

    # Common drops for all monsters with gold
    if gold > 0:
        loot_table.append({"item_id": "ancient_coin", "chance": 0.3})

    # Type-specific loot with much more variety
    if monster["type"] == "plant":
        loot_table.extend([
            {"item_id": "thorny_branch", "chance": 0.5},
            {"item_id": "choking_vines", "chance": 0.4},
            {"item_id": "cooking_herbs", "chance": 0.4},
            {"item_id": "tendrils", "chance": 0.3}
        ])
        if level >= 2:
            loot_table.append({"item_id": "verbena_potion", "chance": 0.25})

    elif monster["type"] == "undead":
        loot_table.extend([
            {"item_id": "bone_fragment", "chance": 0.7},
            {"item_id": "dark_essence", "chance": 0.3},
            {"item_id": "small_bone", "chance": 0.4}
        ])
        if level >= 3:
            loot_table.extend([
                {"item_id": random.choice(low_weapons), "chance": 0.15},
                {"item_id": "scroll_cure_wounds", "chance": 0.2}
            ])
        if level >= 5:
            loot_table.extend([
                {"item_id": "soul_gem", "chance": 0.2},
                {"item_id": random.choice(mid_armor), "chance": 0.15}
            ])
        if level >= 7:
            loot_table.extend([
                {"item_id": "black_rose", "chance": 0.1},
                {"item_id": random.choice(high_weapons), "chance": 0.12}
            ])

    elif monster["type"] == "demon":
        loot_table.extend([
            {"item_id": "dark_essence", "chance": 0.6},
            {"item_id": random.choice(['hellish_claws', 'demonic_claws', 'burning_claws']), "chance": 0.4},
            {"item_id": "flame_crystal", "chance": 0.3}
        ])
        if level >= 5:
            loot_table.extend([
                {"item_id": "soul_gem", "chance": 0.3},
                {"item_id": random.choice(wands), "chance": 0.2}
            ])
        if level >= 10:
            loot_table.extend([
                {"item_id": "soulstone", "chance": 0.25},
                {"item_id": "demon_sword", "chance": 0.15},
                {"item_id": "black_sceptre", "chance": 0.12}
            ])
        if level >= 15:
            loot_table.extend([
                {"item_id": "demonhide", "chance": 0.2},
                {"item_id": random.choice(epic_weapons), "chance": 0.18}
            ])

    elif monster["type"] == "dragon":
        loot_table.extend([
            {"item_id": "dragonscale", "chance": 0.8},
            {"item_id": "dragon_ring", "chance": 0.4},
            {"item_id": random.choice(crystals), "chance": 0.5}
        ])
        if level >= 5:
            loot_table.extend([
                {"item_id": random.choice(high_weapons), "chance": 0.3},
                {"item_id": random.choice(healing_potions[1:]), "chance": 0.4}
            ])
        if level >= 10:
            loot_table.extend([
                {"item_id": "enchanted_blade", "chance": 0.5},
                {"item_id": "manastone", "chance": 0.4},
                {"item_id": random.choice(high_armor), "chance": 0.3}
            ])
        if level >= 20:
            loot_table.extend([
                {"item_id": random.choice(epic_weapons), "chance": 0.4},
                {"item_id": random.choice(epic_armor), "chance": 0.35},
                {"item_id": "soulstone", "chance": 0.3}
            ])

    elif monster["type"] == "animal":
        if 'wolf' in name.lower():
            loot_table.extend([
                {"item_id": "wolf_pelt", "chance": 0.8},
                {"item_id": "wolf_fang", "chance": 0.5},
                {"item_id": "raw_meat", "chance": 0.6},
                {"item_id": "claws", "chance": 0.3}
            ])
        elif 'rat' in name.lower():
            loot_table.extend([
                {"item_id": "rat_tail", "chance": 0.5},
                {"item_id": "small_bone", "chance": 0.3},
                {"item_id": "gnashing_teeth", "chance": 0.2}
            ])
        elif 'bear' in name.lower():
            loot_table.extend([
                {"item_id": "raw_meat", "chance": 0.9},
                {"item_id": "bone_fragment", "chance": 0.5},
                {"item_id": "wicked_claws", "chance": 0.4},
                {"item_id": random.choice(food_items), "chance": 0.3}
            ])
        elif any(x in name.lower() for x in ['spider', 'scorpion']):
            loot_table.extend([
                {"item_id": "pincers", "chance": 0.6},
                {"item_id": "mandibles", "chance": 0.4},
                {"item_id": "verbena_potion", "chance": 0.3}
            ])
        elif any(x in name.lower() for x in ['snake', 'asp', 'anaconda']):
            loot_table.extend([
                {"item_id": "gnashing_teeth", "chance": 0.5},
                {"item_id": "verbena_potion", "chance": 0.4},
                {"item_id": "big_pointy_teeth", "chance": 0.3}
            ])
        elif any(x in name.lower() for x in ['lion', 'tiger', 'leopard']):
            loot_table.extend([
                {"item_id": "raw_meat", "chance": 0.8},
                {"item_id": "wicked_claws", "chance": 0.6},
                {"item_id": "razor_sharp_talons", "chance": 0.4}
            ])
        elif any(x in name.lower() for x in ['bird', 'crane', 'owl', 'griffon']):
            loot_table.extend([
                {"item_id": "talons", "chance": 0.6},
                {"item_id": "hooked_beak", "chance": 0.4},
                {"item_id": random.choice(roses), "chance": 0.15}
            ])
        else:
            loot_table.extend([
                {"item_id": "raw_meat", "chance": 0.5},
                {"item_id": "bone_fragment", "chance": 0.4},
                {"item_id": random.choice(food_items), "chance": 0.2}
            ])

    # Humanoid monsters (orcs, goblins, kobolds, gnolls, etc.)
    elif any(x in name.lower() for x in ['orc', 'kobold', 'gnoll', 'hobgoblin', 'goblin']):
        loot_table.extend([
            {"item_id": "goblin_ear", "chance": 0.5},
            {"item_id": "tattered_cloth", "chance": 0.4},
            {"item_id": random.choice(food_items), "chance": 0.3}
        ])
        if level >= 1:
            loot_table.append({"item_id": random.choice(low_weapons), "chance": 0.25})
        if level >= 2:
            loot_table.extend([
                {"item_id": random.choice(low_armor), "chance": 0.2},
                {"item_id": random.choice(keys[:5]), "chance": 0.15}
            ])
        if level >= 4:
            loot_table.extend([
                {"item_id": random.choice(mid_weapons), "chance": 0.2},
                {"item_id": "rope", "chance": 0.2}
            ])
        if 'warlord' in name.lower() or 'chief' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(high_weapons), "chance": 0.35},
                {"item_id": random.choice(mid_armor), "chance": 0.3},
                {"item_id": random.choice(keys[5:10]), "chance": 0.25}
            ])
        if 'shaman' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(low_scrolls), "chance": 0.4},
                {"item_id": random.choice(mana_potions), "chance": 0.3},
                {"item_id": random.choice(buff_potions), "chance": 0.25}
            ])

    # Lizard folk
    elif any(x in name.lower() for x in ['lizard']):
        loot_table.extend([
            {"item_id": "bone_fragment", "chance": 0.5},
            {"item_id": "tattered_cloth", "chance": 0.3},
            {"item_id": random.choice(['spear', 'knife']), "chance": 0.3}
        ])
        if level >= 3:
            loot_table.extend([
                {"item_id": random.choice(mid_weapons), "chance": 0.2},
                {"item_id": "scalemail", "chance": 0.15}
            ])
        if 'warlord' in name.lower() or 'chief' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(high_weapons), "chance": 0.3},
                {"item_id": random.choice(healing_potions), "chance": 0.25}
            ])

    # Giants
    elif 'giant' in name.lower():
        loot_table.extend([
            {"item_id": "huge_club", "chance": 0.4},
            {"item_id": "bone_fragment", "chance": 0.5},
            {"item_id": random.choice(food_items), "chance": 0.4}
        ])
        if 'stone' in name.lower():
            loot_table.extend([
                {"item_id": "stone", "chance": 0.7},
                {"item_id": random.choice(high_weapons), "chance": 0.3}
            ])
        elif 'ice' in name.lower():
            loot_table.extend([
                {"item_id": "ice_crystal", "chance": 0.7},
                {"item_id": "frost_rod", "chance": 0.25}
            ])
        elif 'flame' in name.lower() or 'fire' in name.lower():
            loot_table.extend([
                {"item_id": "flame_crystal", "chance": 0.7},
                {"item_id": "pyrehammer", "chance": 0.2},
                {"item_id": "flaming_greatsword", "chance": 0.2}
            ])
        elif 'forest' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(['thorny_branch', 'choking_vines']), "chance": 0.5},
                {"item_id": "cooking_herbs", "chance": 0.4}
            ])
        if level >= 5:
            loot_table.extend([
                {"item_id": random.choice(high_armor), "chance": 0.25},
                {"item_id": random.choice(healing_potions[1:]), "chance": 0.3}
            ])
        if level >= 10:
            loot_table.extend([
                {"item_id": random.choice(rings), "chance": 0.3},
                {"item_id": random.choice(keys[8:13]), "chance": 0.25}
            ])
        if 'warlord' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(epic_weapons), "chance": 0.4},
                {"item_id": random.choice(high_armor), "chance": 0.35}
            ])

    # Elemental creatures
    elif 'elemental' in name.lower():
        if 'ice' in name.lower():
            loot_table.extend([
                {"item_id": "ice_crystal", "chance": 0.9},
                {"item_id": "rimeax", "chance": 0.3},
                {"item_id": "frost_rod", "chance": 0.35}
            ])
        elif 'flame' in name.lower() or 'fire' in name.lower():
            loot_table.extend([
                {"item_id": "flame_crystal", "chance": 0.9},
                {"item_id": "pyrehammer", "chance": 0.3},
                {"item_id": "flaming_staff", "chance": 0.25}
            ])
        elif 'stone' in name.lower():
            loot_table.extend([
                {"item_id": "stone", "chance": 0.9},
                {"item_id": random.choice(high_weapons), "chance": 0.3}
            ])
        loot_table.extend([
            {"item_id": "manastone", "chance": 0.6},
            {"item_id": "soulstone", "chance": 0.4},
            {"item_id": random.choice(wands), "chance": 0.35}
        ])

    # Dwarven enemies
    elif 'dwarven' in name.lower() or 'dwarf' in name.lower():
        loot_table.extend([
            {"item_id": "bone_fragment", "chance": 0.4},
            {"item_id": random.choice(keys[:7]), "chance": 0.3}
        ])
        if 'guard' in name.lower() or 'warrior' in name.lower() or 'captain' in name.lower():
            loot_table.extend([
                {"item_id": "dwarven_scalemail", "chance": 0.35},
                {"item_id": "dwarven_battleax", "chance": 0.3},
                {"item_id": random.choice(high_weapons), "chance": 0.25},
                {"item_id": random.choice(healing_potions[1:]), "chance": 0.3}
            ])
        if 'smith' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(keys[:10]), "chance": 0.5},
                {"item_id": "warhammer", "chance": 0.4},
                {"item_id": "bronze_gong", "chance": 0.2}
            ])
        if 'sorceror' in name.lower() or 'archmage' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(wands), "chance": 0.4},
                {"item_id": random.choice(high_scrolls), "chance": 0.35},
                {"item_id": "manastone", "chance": 0.4},
                {"item_id": random.choice(buff_potions), "chance": 0.3}
            ])
        if 'warlord' in name.lower() or 'leutenant' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(epic_weapons), "chance": 0.4},
                {"item_id": random.choice(epic_armor), "chance": 0.35},
                {"item_id": random.choice(rings), "chance": 0.4}
            ])
        if level >= 25:
            loot_table.extend([
                {"item_id": random.choice(keys[8:15]), "chance": 0.35},
                {"item_id": random.choice(rings), "chance": 0.3}
            ])

    # Elven enemies
    elif 'elven' in name.lower() or 'elf' in name.lower():
        loot_table.extend([
            {"item_id": "elven_bow", "chance": 0.5},
            {"item_id": random.choice(roses), "chance": 0.3},
            {"item_id": random.choice(healing_potions[1:]), "chance": 0.35}
        ])
        if 'scout' in name.lower():
            loot_table.extend([
                {"item_id": "arrow", "chance": 0.6},
                {"item_id": "quiver", "chance": 0.4},
                {"item_id": random.choice(mid_weapons), "chance": 0.25}
            ])
        if 'warrior' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(high_weapons), "chance": 0.4},
                {"item_id": random.choice(mid_armor), "chance": 0.3},
                {"item_id": "enchanted_blade", "chance": 0.25}
            ])
        if 'champion' in name.lower():
            loot_table.extend([
                {"item_id": "enchanted_blade", "chance": 0.6},
                {"item_id": "champion_armor", "chance": 0.5},
                {"item_id": random.choice(epic_weapons), "chance": 0.35}
            ])
        if 'warlord' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(epic_weapons), "chance": 0.5},
                {"item_id": random.choice(epic_armor), "chance": 0.4},
                {"item_id": random.choice(rings), "chance": 0.45}
            ])
        if level >= 30:
            loot_table.extend([
                {"item_id": random.choice(keys[10:]), "chance": 0.3},
                {"item_id": "manastone", "chance": 0.25}
            ])

    # Mages and spellcasters
    elif any(x in name.lower() for x in ['mage', 'warlock', 'sorceress', 'sorceror', 'shaman', 'wizard', 'archmage']):
        loot_table.extend([
            {"item_id": random.choice(mana_potions), "chance": 0.6},
            {"item_id": random.choice(low_scrolls), "chance": 0.5},
            {"item_id": random.choice(buff_potions), "chance": 0.4},
            {"item_id": random.choice(['cloth_robe', 'robes', 'blue_robes', 'violet_robes']), "chance": 0.3}
        ])
        if level >= 4:
            loot_table.extend([
                {"item_id": random.choice(wands), "chance": 0.3},
                {"item_id": random.choice(high_scrolls), "chance": 0.25}
            ])
        if level >= 8:
            loot_table.extend([
                {"item_id": "runestaff", "chance": 0.35},
                {"item_id": "manastone", "chance": 0.4}
            ])
        if level >= 15:
            loot_table.extend([
                {"item_id": "rod_of_power", "chance": 0.25},
                {"item_id": random.choice(keys[10:]), "chance": 0.3}
            ])

    # Warriors and fighters
    elif any(x in name.lower() for x in ['warrior', 'fighter', 'swordsman', 'swordswoman', 'knight', 'champion', 'warlord', 'chieftain']):
        loot_table.extend([
            {"item_id": random.choice(mid_weapons), "chance": 0.4},
            {"item_id": random.choice(mid_armor), "chance": 0.3},
            {"item_id": random.choice(healing_potions), "chance": 0.35}
        ])
        if level >= 5:
            loot_table.extend([
                {"item_id": random.choice(high_weapons), "chance": 0.35},
                {"item_id": random.choice(high_armor), "chance": 0.3}
            ])
        if level >= 10:
            loot_table.extend([
                {"item_id": "enchanted_blade", "chance": 0.3},
                {"item_id": random.choice(healing_potions[2:]), "chance": 0.3}
            ])
        if level >= 15:
            loot_table.extend([
                {"item_id": "champion_armor", "chance": 0.25},
                {"item_id": random.choice(epic_weapons), "chance": 0.25}
            ])
        if 'champion' in name.lower():
            loot_table.extend([
                {"item_id": "enchanted_blade", "chance": 0.7},
                {"item_id": "champion_armor", "chance": 0.6},
                {"item_id": random.choice(rings), "chance": 0.4}
            ])

    # Bandits and brigands
    elif any(x in name.lower() for x in ['bandit', 'brigand', 'nomad', 'barbarian']):
        loot_table.extend([
            {"item_id": "tattered_cloth", "chance": 0.5},
            {"item_id": random.choice(low_weapons), "chance": 0.4},
            {"item_id": random.choice(food_items), "chance": 0.5},
            {"item_id": random.choice(keys[:5]), "chance": 0.2}
        ])
        if level >= 3:
            loot_table.extend([
                {"item_id": random.choice(mid_weapons), "chance": 0.3},
                {"item_id": random.choice(low_armor), "chance": 0.25}
            ])
        if level >= 5:
            loot_table.extend([
                {"item_id": "ancient_coin", "chance": 0.7},
                {"item_id": random.choice(keys[3:8]), "chance": 0.3}
            ])

    # Special/mythical creatures
    elif any(x in name.lower() for x in ['centaur', 'satyr', 'minotaur', 'cyclops', 'ogre', 'troll']):
        loot_table.extend([
            {"item_id": "bone_fragment", "chance": 0.5},
            {"item_id": "raw_meat", "chance": 0.4},
            {"item_id": random.choice(low_weapons), "chance": 0.3}
        ])
        if level >= 3:
            loot_table.extend([
                {"item_id": random.choice(mid_weapons), "chance": 0.3},
                {"item_id": random.choice(food_items), "chance": 0.4}
            ])
        if level >= 5:
            loot_table.extend([
                {"item_id": random.choice(rings), "chance": 0.25},
                {"item_id": random.choice(keys[5:10]), "chance": 0.2}
            ])
        if 'chief' in name.lower() or 'lord' in name.lower():
            loot_table.extend([
                {"item_id": random.choice(high_weapons), "chance": 0.4},
                {"item_id": random.choice(high_armor), "chance": 0.3}
            ])

    # Default loot for monsters without specific type
    if not loot_table or len(loot_table) <= 2:
        loot_table.extend([
            {"item_id": "bone_fragment", "chance": 0.4},
            {"item_id": "tattered_cloth", "chance": 0.3},
            {"item_id": random.choice(materials), "chance": 0.25}
        ])
        if level >= 2:
            loot_table.append({"item_id": random.choice(low_weapons), "chance": 0.2})

    # Add level-appropriate potions and treasures
    if level >= 2:
        loot_table.append({"item_id": random.choice(healing_potions[:1]), "chance": 0.3})
    if level >= 5:
        loot_table.append({"item_id": random.choice(healing_potions[:2]), "chance": 0.25})
    if level >= 10:
        loot_table.extend([
            {"item_id": random.choice(healing_potions[1:3]), "chance": 0.2},
            {"item_id": random.choice(keys[5:10]), "chance": 0.15}
        ])
    if level >= 15:
        loot_table.extend([
            {"item_id": random.choice(healing_potions[2:]), "chance": 0.15},
            {"item_id": random.choice(keys[8:]), "chance": 0.2}
        ])
    if level >= 20:
        loot_table.extend([
            {"item_id": random.choice(healing_potions[2:]), "chance": 0.2},
            {"item_id": random.choice(rings), "chance": 0.15},
            {"item_id": random.choice(wands), "chance": 0.12}
        ])
    if level >= 30:
        loot_table.extend([
            {"item_id": "soulstone", "chance": 0.15},
            {"item_id": random.choice(epic_weapons), "chance": 0.12},
            {"item_id": random.choice(epic_armor), "chance": 0.1}
        ])

    if loot_table:
        monster["loot_table"] = loot_table

    return monster_id, monster

def main():
    """Main conversion function."""
    # Paths
    mobs_yaml = Path('data/items/mobs.yaml')
    monsters_json = Path('data/npcs/monsters.json')

    # Read mobs YAML
    print(f"Reading {mobs_yaml}...")
    with open(mobs_yaml, 'r') as f:
        mobs_data = yaml.safe_load(f)

    print(f"Found {len(mobs_data)} mobs")

    # Read existing monsters.json
    print(f"Reading {monsters_json}...")
    with open(monsters_json, 'r') as f:
        existing_monsters = json.load(f)

    # Convert to dict for easier checking
    existing_dict = {m['id']: m for m in existing_monsters}

    # Convert mob items
    converted_count = 0
    skipped_count = 0
    new_monsters = []

    for mob_id, mob_info in mobs_data.items():
        monster_id, monster = convert_mob(mob_id, mob_info)

        # Check if already exists
        if monster_id in existing_dict:
            print(f"Skipping {monster_id} (already exists)")
            skipped_count += 1
            continue

        # Add to monsters
        new_monsters.append(monster)
        converted_count += 1
        print(f"Added: {monster_id} - {monster['name']} (Level {monster['level']}, Damage: {monster['damage_min']}-{monster['damage_max']})")

    # Combine existing and new monsters
    all_monsters = existing_monsters + new_monsters

    # Write back to monsters.json
    print(f"\nWriting updated monsters to {monsters_json}...")
    with open(monsters_json, 'w') as f:
        json.dump(all_monsters, f, indent=2)

    print(f"\n=== Conversion Summary ===")
    print(f"Mobs converted: {converted_count}")
    print(f"Mobs skipped (already exist): {skipped_count}")
    print(f"Total monsters in monsters.json: {len(all_monsters)}")
    print("\nConversion complete!")

if __name__ == '__main__':
    main()
