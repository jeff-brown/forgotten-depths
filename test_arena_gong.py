#!/usr/bin/env python3
"""Test arena and gong functionality."""

import telnetlib
import time

def test_arena_and_gong():
    """Test the arena room and gong functionality."""
    print("Testing Arena and Gong Functionality")
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

    # Test 1: Check current location
    print("\n=== TEST 1: Check Current Location ===")
    send_command("look")

    # Test 2: Try to ring gong from wrong location
    print("\n=== TEST 2: Ring Gong From Wrong Location ===")
    send_command("ring gong")

    # Test 3: Try to go to arena (if implemented)
    print("\n=== TEST 3: Try to Navigate to Arena ===")
    send_command("go arena")  # This might not work if no exit is set up
    send_command("north")
    send_command("south")
    send_command("east")
    send_command("west")

    # Test 4: Manual teleport to arena for testing (if character editing works)
    print("\n=== TEST 4: Check if We Can Ring Without Gong ===")
    send_command("ring")  # Test without parameters

    # Test 5: Try ring command variations
    print("\n=== TEST 5: Try Ring Command Variations ===")
    send_command("ring bronze")
    send_command("ring g")
    send_command("ri gong")
    send_command("ri g")

    # Test 6: Try other invalid ring targets
    print("\n=== TEST 6: Try Invalid Ring Targets ===")
    send_command("ring bell")
    send_command("ring sword")

    tn.write(b"quit\n")
    tn.close()
    print("\nArena and gong test complete!")

if __name__ == "__main__":
    test_arena_and_gong()