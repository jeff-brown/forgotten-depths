#!/usr/bin/env python3
"""Debug script to test equipment command parsing."""

import telnetlib
import time

def test_equip_debug():
    """Test equip command specifically."""
    print("Testing Equip Command Debug")
    print("=" * 40)

    # Connect to server
    tn = telnetlib.Telnet("localhost", 4000)
    time.sleep(0.5)

    # Login
    tn.read_very_eager()
    tn.write(b"debuguser\n")
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

    # Test commands that should work vs not work
    print("\n=== Test working commands ===")
    send_command("inventory")  # Should work
    send_command("look")       # Should work
    send_command("drop")       # Should give parameter error but not chat

    print("\n=== Test equip commands ===")
    send_command("equip")      # Should give parameter error but not chat
    send_command("equip test") # Should try to equip something

    print("\n=== Test other commands ===")
    send_command("get")        # Should give parameter error but not chat
    send_command("unknown")    # Should become chat message

    tn.write(b"quit\n")
    tn.close()
    print("\nDebug test complete!")

if __name__ == "__main__":
    test_equip_debug()