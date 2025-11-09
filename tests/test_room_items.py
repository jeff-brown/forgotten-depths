#!/usr/bin/env python3
"""Test room item system - drop and pickup functionality."""

import telnetlib
import time

def test_room_items():
    """Test dropping and picking up items from room floor."""
    print("Testing Room Item System (Drop/Get)")
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

    # Test 1: Check initial room state
    print("\n=== TEST 1: Initial Room State ===")
    send_command("")  # Press enter to see room description

    # Test 2: Get an item first
    print("\n=== TEST 2: Get Item ===")
    send_command("get arrow")
    send_command("inventory")

    # Test 3: Drop the item
    print("\n=== TEST 3: Drop Item ===")
    send_command("drop arrow")

    # Test 4: Check room description shows dropped item
    print("\n=== TEST 4: Room Description with Item ===")
    send_command("")  # Press enter to reload room description

    # Test 5: Pick up the dropped item
    print("\n=== TEST 5: Pick Up Dropped Item ===")
    send_command("get arrow")
    send_command("inventory")

    # Test 6: Check room is clean again
    print("\n=== TEST 6: Room Clean After Pickup ===")
    send_command("")  # Press enter to reload room description

    # Test 7: Drop multiple items
    print("\n=== TEST 7: Multiple Items ===")
    send_command("get sword")
    send_command("get bread")
    send_command("inventory")
    send_command("drop arrow")
    send_command("drop sword")
    send_command("")  # Check room with multiple items

    # Test 8: Pick up one of multiple items
    print("\n=== TEST 8: Partial Pickup ===")
    send_command("get sword")
    send_command("")  # Check room with remaining item
    send_command("inventory")

    tn.write(b"quit\n")
    tn.close()
    print("\nRoom item system test complete!")

if __name__ == "__main__":
    test_room_items()