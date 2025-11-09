#!/usr/bin/env python3
"""Test script to verify character save/load functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from server.persistence.database import Database
from server.persistence.player_storage import PlayerStorage

def test_save_load():
    """Test saving and loading character data."""
    print("=== Testing Character Save/Load ===\n")

    # Initialize database
    db = Database("test_save_load.db")
    db.connect()
    print("✓ Database connected")

    storage = PlayerStorage(db)
    print("✓ PlayerStorage initialized\n")

    # Create test character data
    test_character = {
        'name': 'TestHero',
        'level': 5,
        'experience': 1250,
        'strength': 18,
        'dexterity': 14,
        'constitution': 16,
        'gold': 350,
        'room_id': 'town_square',
        'inventory': [
            {'name': 'Health Potion', 'weight': 1, 'value': 20},
            {'name': 'Short Sword', 'weight': 5, 'value': 50}
        ],
        'equipped': {
            'weapon': {'name': 'Short Sword', 'weight': 5},
            'armor': None
        },
        'health': 75,
        'max_hit_points': 100
    }

    username = "tester"

    # Test save
    print(f"Saving character for '{username}'...")
    success = storage.save_character_data(username, test_character)
    if success:
        print("✓ Character saved successfully\n")
    else:
        print("✗ Failed to save character\n")
        return False

    # Test load
    print(f"Loading character for '{username}'...")
    loaded_character = storage.load_character_data(username)

    if loaded_character:
        print("✓ Character loaded successfully\n")
        print("Loaded character data:")
        print(f"  Name: {loaded_character.get('name')}")
        print(f"  Level: {loaded_character.get('level')}")
        print(f"  Experience: {loaded_character.get('experience')}")
        print(f"  Gold: {loaded_character.get('gold')}")
        print(f"  Room: {loaded_character.get('room_id')}")
        print(f"  Inventory items: {len(loaded_character.get('inventory', []))}")
        print(f"  Health: {loaded_character.get('health')}/{loaded_character.get('max_hit_points')}")

        # Verify data matches
        if (loaded_character['name'] == test_character['name'] and
            loaded_character['level'] == test_character['level'] and
            loaded_character['gold'] == test_character['gold']):
            print("\n✓ All data matches!")
            return True
        else:
            print("\n✗ Data mismatch!")
            return False
    else:
        print("✗ Failed to load character\n")
        return False

if __name__ == "__main__":
    try:
        success = test_save_load()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)