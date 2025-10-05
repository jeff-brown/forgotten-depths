#!/usr/bin/env python3
"""Update monster types based on their names."""

import json
from pathlib import Path

def infer_type(name):
    """Infer monster type from name."""
    name_lower = name.lower()

    # Undead
    if any(word in name_lower for word in ['skeleton', 'zombie', 'ghoul', 'wraith', 'shade', 'crypt']):
        return 'undead'

    # Dragons
    if 'dragon' in name_lower:
        return 'dragon'

    # Demons
    if any(word in name_lower for word in ['demon', 'demoness', 'imp', 'affreet', 'hellhound']):
        return 'demon'

    # Elementals
    if 'elemental' in name_lower:
        return 'elemental'

    # Plants
    if any(word in name_lower for word in ['vine', 'orchid', 'ivy', 'creeper', 'shrub']):
        return 'plant'

    # Beasts/Animals (wild creatures)
    if any(word in name_lower for word in [
        'rat', 'wolf', 'bear', 'spider', 'bat', 'toad', 'slug', 'scorpion',
        'beetle', 'alligator', 'asp', 'anaconda', 'boar', 'leopard',
        'ape', 'lion', 'worm', 'crane', 'octopod', 'rabbit', 'bunny',
        'lizard', 'monkey', 'owl', 'squirrel', 'frog', 'fox', 'hyena',
        'tiger', 'jackal', 'warhound'
    ]):
        return 'beast'

    # Giants
    if any(word in name_lower for word in ['giant', 'giantess', 'cyclops']):
        return 'giant'

    # Magical creatures
    if any(word in name_lower for word in ['griffon', 'gargoyle', 'chimera', 'hydra']):
        return 'magical_creature'

    # Humanoid races and civilized creatures
    if any(word in name_lower for word in [
        'orc', 'goblin', 'kobold', 'gnoll', 'hobgoblin', 'troll', 'ogre',
        'minotaur', 'centaur', 'satyr', 'brigand', 'barbarian', 'bandit',
        'nomad', 'swordsman', 'swordswoman', 'warlock', 'sorceress', 'sorceror',
        'knight', 'warrior', 'guard', 'captain', 'warlord', 'chieftain',
        'shaman', 'wizard', 'mage', 'archmage', 'dwarven', 'dwarf',
        'elven', 'elf', 'smith', 'magmaman', 'larochet', 'larochess'
    ]):
        return 'humanoid'

    # Default to monster for anything else
    return 'monster'

def load_all_monsters():
    """Load all monsters from type-specific JSON files."""
    monsters = []
    mobs_dir = Path("data/mobs")

    # Load monsters from type-specific files
    if mobs_dir.exists():
        for monster_file in mobs_dir.glob("*.json"):
            try:
                with open(monster_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    type_monsters = config.get('monsters', [])
                    monsters.extend(type_monsters)
            except Exception as e:
                print(f"Warning: Could not load monsters from {monster_file}: {e}")

    # Fallback to legacy monsters.json if no type files found
    if not monsters:
        legacy_file = Path("data/npcs/monsters.json")
        if legacy_file.exists():
            with open(legacy_file, 'r', encoding='utf-8') as f:
                monsters = json.load(f)

    return monsters

def save_monsters_by_type(monsters):
    """Save monsters to type-specific files."""
    from collections import defaultdict

    # Group by type
    monsters_by_type = defaultdict(list)
    for monster in monsters:
        monster_type = monster.get('type', 'unknown')
        monsters_by_type[monster_type].append(monster)

    # Save each type
    mobs_dir = Path("data/mobs")
    mobs_dir.mkdir(parents=True, exist_ok=True)
    for monster_type, type_monsters in monsters_by_type.items():
        output_file = mobs_dir / f"{monster_type}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"monsters": type_monsters}, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(type_monsters)} monsters to {output_file}")

def main():
    # Read the monsters
    monsters = load_all_monsters()

    # Update each monster's type based on their name
    updated_count = 0
    for monster in monsters:
        old_type = monster.get('type', 'unknown')
        new_type = infer_type(monster['name'])

        if old_type != new_type:
            monster['type'] = new_type
            updated_count += 1
            print(f"Updated {monster['id']}: '{old_type}' -> '{new_type}' (name: {monster['name']})")
        else:
            print(f"Kept {monster['id']}: '{new_type}' (name: {monster['name']})")

    # Save back to type-specific files
    print(f"\nUpdated {updated_count} monster types")
    print(f"Total monsters: {len(monsters)}")
    print("\nSaving monsters to type-specific files...")
    save_monsters_by_type(monsters)

if __name__ == "__main__":
    main()
