#!/usr/bin/env python3
"""Verify the locked door is configured correctly."""

import json

print("=== LOCKED DOOR VERIFICATION ===\n")

# Check the room JSON file directly
with open('data/world/rooms/dungeon1/dungeon1_1.json', 'r') as f:
    room_data = json.load(f)

print(f"Room ID: {room_data['id']}")
print(f"Room Title: {room_data['title']}")
print(f"\nExits: {list(room_data.get('exits', {}).keys())}")
print(f"Locked Exits: {list(room_data.get('locked_exits', {}).keys())}")

if 'locked_exits' in room_data:
    for direction, lock_info in room_data['locked_exits'].items():
        print(f"\n{direction.upper()} is LOCKED:")
        print(f"  Required Key: {lock_info.get('required_key')}")
        print(f"  Description: {lock_info.get('description')}")
else:
    print("\n❌ ERROR: No locked_exits found in room data!")
    exit(1)

# Check if bronze_key exists
with open('data/items/items.json', 'r') as f:
    items_data = json.load(f)
    items = items_data['items']

if 'bronze_key' in items:
    print(f"\n✅ Bronze Key exists in items.json")
    print(f"   Name: {items['bronze_key']['name']}")
else:
    print("\n❌ ERROR: bronze_key not found in items.json!")
    exit(1)

# Check if bronze_key is in dungeon1_14
with open('data/world/rooms/dungeon1/dungeon1_14.json', 'r') as f:
    room14_data = json.load(f)

if 'bronze_key' in room14_data.get('items', []):
    print(f"\n✅ Bronze Key is in room dungeon1_14")
    print(f"   Room: {room14_data['title']}")
else:
    print(f"\n❌ ERROR: bronze_key not in dungeon1_14 items!")
    exit(1)

print("\n" + "="*50)
print("✅ ALL CHECKS PASSED!")
print("="*50)
print("\nThe locked door system is configured correctly.")
print("IMPORTANT: Restart the game server to load the changes!")
