#!/usr/bin/env python3
"""Populate dungeon lair rooms with level-appropriate monsters."""

import json
import random
from pathlib import Path

# Level ranges for each dungeon
DUNGEON_LEVELS = {
    'dungeon1': (1, 10),
    'dungeon2': (5, 15),
    'dungeon3': (10, 20)
}

def get_monsters_by_level():
    """Load monsters and organize by level."""
    with open('data/npcs/monsters.json', 'r') as f:
        monsters = json.load(f)

    # Group monsters by level
    monsters_by_level = {}
    for monster in monsters:
        level = monster.get('level', 1)
        if level not in monsters_by_level:
            monsters_by_level[level] = []
        monsters_by_level[level].append(monster)

    return monsters_by_level

def get_appropriate_monster(monsters_by_level, min_level, max_level, lair_description):
    """Get an appropriate monster for a lair based on level range and description."""
    # Get all monsters within the level range
    candidates = []
    for level in range(min_level, max_level + 1):
        if level in monsters_by_level:
            candidates.extend(monsters_by_level[level])

    if not candidates:
        print(f"Warning: No monsters found for level range {min_level}-{max_level}")
        return None

    # Try to match based on description keywords
    lair_lower = lair_description.lower()

    # Thematic matching
    theme_keywords = {
        'undead': ['crypt', 'tomb', 'grave', 'skeleton', 'bone', 'death'],
        'demon': ['demon', 'devil', 'infernal', 'hellish'],
        'dragon': ['dragon', 'hoard', 'treasure', 'enormous', 'huge tapestry'],
        'giant': ['giant', 'enormous', 'huge', 'stone giant'],
        'plant': ['garden', 'vine', 'plant', 'flower'],
        'animal': ['den', 'nest', 'burrow'],
    }

    # Specific monster keywords
    specific_keywords = {
        'minotaur': ['minotaur', 'labyrinth', 'maze'],
        'troll': ['troll', 'bridge'],
        'ogre': ['ogre'],
        'cyclops': ['cyclops'],
        'centaur': ['centaur'],
        'satyr': ['satyr'],
        'hydra': ['hydra', 'pool', 'water'],
        'spider': ['spider', 'web'],
        'wolf': ['wolf', 'pack'],
        'bear': ['bear', 'cave'],
    }

    # First try specific keywords
    for monster_key, keywords in specific_keywords.items():
        if any(keyword in lair_lower for keyword in keywords):
            matching = [m for m in candidates if monster_key in m['id'].lower()]
            if matching:
                return random.choice(matching)

    # Then try thematic matching
    for monster_type, keywords in theme_keywords.items():
        if any(keyword in lair_lower for keyword in keywords):
            matching = [m for m in candidates if m.get('type') == monster_type]
            if matching:
                return random.choice(matching)

    # If no thematic match, prefer higher-level monsters for lairs
    # Sort by level (descending) and pick from top third
    candidates.sort(key=lambda m: m.get('level', 1), reverse=True)
    top_candidates = candidates[:max(1, len(candidates) // 3)]

    return random.choice(top_candidates)

def populate_lairs():
    """Populate all dungeon lairs with appropriate monsters."""
    monsters_by_level = get_monsters_by_level()

    for dungeon_name, (min_level, max_level) in DUNGEON_LEVELS.items():
        print(f"\n=== Processing {dungeon_name.upper()} (Levels {min_level}-{max_level}) ===")

        # Find all lair rooms for this dungeon
        dungeon_dir = Path(f'data/world/rooms/{dungeon_name}')
        if not dungeon_dir.exists():
            print(f"Warning: Directory {dungeon_dir} not found")
            continue

        lair_count = 0
        for room_file in dungeon_dir.glob('*.json'):
            with open(room_file, 'r') as f:
                room = json.load(f)

            # Skip non-lair rooms
            if not room.get('is_lair', False):
                continue

            lair_count += 1
            description = room.get('description', '')
            title = room.get('title', '')

            # Get appropriate monster
            monster = get_appropriate_monster(
                monsters_by_level,
                min_level,
                max_level,
                f"{title} {description}"
            )

            if monster:
                # Update the lair_monster field
                old_monster = room.get('lair_monster', 'none')
                room['lair_monster'] = monster['id']

                # Write back to file
                with open(room_file, 'w') as f:
                    json.dump(room, f, indent=2)

                print(f"  {room['id']}: {title[:40]}...")
                print(f"    → {monster['name']} (Level {monster['level']})")
            else:
                print(f"  {room['id']}: Could not find suitable monster")

        print(f"\nPopulated {lair_count} lairs in {dungeon_name}")

if __name__ == '__main__':
    populate_lairs()
    print("\n=== Lair population complete! ===")
