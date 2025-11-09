#!/usr/bin/env python3
"""Test equipment system - equip and unequip functionality."""

import telnetlib
import time

def test_equipment_system():
    """Test equipping and unequipping weapons and armor."""
    print("Testing Equipment System (Equip/Unequip)")
    print("=" * 60)

    # Connect to server
    tn = telnetlib.Telnet("localhost", 4000)
    time.sleep(0.5)

    # Login
    tn.read_very_eager()
    tn.write(b"testuser\n")
    time.sleep(0.3)
    tn.read_very_eager()
    tn.write(b"password\n")
    time.sleep(0.3)
    tn.read_very_eager()

    def send_command(cmd):
        print(f"\n> {cmd}")
        tn.write(f"{cmd}\n".encode())
        time.sleep(0.5)
        response = tn.read_very_eager().decode('utf-8')
        print(response)
        return response

    # Test 1: Check initial state
    print("\n=== TEST 1: Initial Equipment State ===")
    send_command("inventory")
    send_command("stats")

    # Test 2: Get equipment items
    print("\n=== TEST 2: Get Equipment Items ===")
    send_command("get sword")  # Short Sword
    send_command("get leather")  # Leather Armor
    send_command("inventory")

    # Test 3: Equip weapon
    print("\n=== TEST 3: Equip Weapon ===")
    send_command("equip short sword")
    send_command("inventory")
    send_command("stats")

    # Test 4: Equip armor
    print("\n=== TEST 4: Equip Armor ===")
    send_command("equip leather armor")
    send_command("inventory")
    send_command("stats")

    # Test 5: Try to equip non-equipment item
    print("\n=== TEST 5: Try Equip Non-Equipment ===")
    send_command("get bread")
    send_command("equip bread")

    # Test 6: Equip different weapon (should auto-unequip current)
    print("\n=== TEST 6: Auto-Unequip When Equipping ===")
    send_command("get dagger")
    send_command("equip dagger")
    send_command("inventory")

    # Test 7: Unequip weapon
    print("\n=== TEST 7: Unequip Weapon ===")
    send_command("unequip dagger")
    send_command("inventory")
    send_command("stats")

    # Test 8: Unequip armor
    print("\n=== TEST 8: Unequip Armor ===")
    send_command("unequip leather armor")
    send_command("inventory")
    send_command("stats")

    # Test 9: Try to unequip non-equipped item
    print("\n=== TEST 9: Try Unequip Non-Equipped ===")
    send_command("unequip short sword")

    tn.write(b"quit\n")
    tn.close()
    print("\nEquipment system test complete!")

if __name__ == "__main__":
    test_equipment_system()