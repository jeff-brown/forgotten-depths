#!/usr/bin/env python3
"""Test partial name matching functionality."""

import telnetlib
import time

def test_partial_names():
    """Test partial name matching for item commands."""
    print("Testing Partial Name Matching")
    print("=" * 50)

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

    # Set up test items
    print("\n=== Setup: Get test items ===")
    send_command("get short sword")  # "Short Sword"
    send_command("get dagger")       # "Dagger"
    send_command("get leather armor") # "Leather Armor"
    send_command("get cloth robe")   # "Cloth Robe"
    send_command("inventory")

    # Test 1: Partial name matching for equip
    print("\n=== TEST 1: Equip with partial names ===")
    send_command("equip short")      # Should equip "Short Sword"
    send_command("equip leather")    # Should equip "Leather Armor"
    send_command("inventory")

    # Test 2: Unequip with partial names
    print("\n=== TEST 2: Unequip with partial names ===")
    send_command("unequip short")    # Should unequip "Short Sword"
    send_command("unequip leather")  # Should unequip "Leather Armor"
    send_command("inventory")

    # Test 3: Drop with partial names
    print("\n=== TEST 3: Drop with partial names ===")
    send_command("drop short")       # Should drop "Short Sword"
    send_command("drop dag")         # Should drop "Dagger"
    send_command("inventory")
    send_command("")  # Check room

    # Test 4: Get with partial names from floor
    print("\n=== TEST 4: Get with partial names from floor ===")
    send_command("get short")        # Should get "Short Sword" from floor
    send_command("get dag")          # Should get "Dagger" from floor
    send_command("inventory")

    # Test 5: Ambiguous matches (should fail)
    print("\n=== TEST 5: Ambiguous matches ===")
    send_command("get cloth robe")   # Get another cloth item
    send_command("get bread")        # Get bread to create ambiguity
    send_command("inventory")
    send_command("drop cloth")       # "cloth" could match "Cloth Robe"
    send_command("drop c")           # "c" could match "Cloth Robe"

    # Test 6: Exact matches should work even with ambiguity
    print("\n=== TEST 6: Exact matches ===")
    send_command("drop cloth robe")  # Exact match should work
    send_command("inventory")

    # Test 7: Single letter matches
    print("\n=== TEST 7: Single letter matches ===")
    send_command("drop b")           # Should match "Bread" (unique)
    send_command("inventory")

    tn.write(b"quit\n")
    tn.close()
    print("\nPartial name matching test complete!")

if __name__ == "__main__":
    test_partial_names()