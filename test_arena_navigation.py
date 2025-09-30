#!/usr/bin/env python3
"""Test navigation to the arena and gong functionality."""

import telnetlib
import time

def test_arena_navigation():
    """Test navigating to the arena and using the gong."""
    print("Testing Arena Navigation and Gong")
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

    # Test 1: Check current location and navigate to arena
    print("\n=== TEST 1: Navigate to Arena ===")
    send_command("look")
    send_command("down")  # Go to inn entrance
    send_command("west")  # Go to town square
    send_command("south") # Go to market square
    send_command("west")  # Go to tavern
    send_command("north") # Go to arena (if connection works)

    # Test 2: Check if we're in the arena and try the gong
    print("\n=== TEST 2: Test Gong in Arena ===")
    response = send_command("look")

    if "arena" in response.lower() or "gong" in response.lower():
        print("SUCCESS: We're in the arena!")

        # Test the gong
        send_command("ring gong")
        time.sleep(3)  # Wait for the dramatic effect
        send_command("look")  # Check if mob spawned

        # Test short form
        send_command("ri g")
        time.sleep(3)
        send_command("look")
    else:
        print("FAILED: Could not reach arena or arena doesn't have gong")
        print("Trying ring command anyway to test error handling:")
        send_command("ring gong")

    # Test 3: Navigate back
    print("\n=== TEST 3: Navigate Back ===")
    send_command("south")  # Should go back to tavern
    send_command("look")

    tn.write(b"quit\n")
    tn.close()
    print("\nArena navigation test complete!")

if __name__ == "__main__":
    test_arena_navigation()