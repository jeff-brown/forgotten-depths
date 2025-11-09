#!/usr/bin/env python3
"""Test inventory and vendor systems."""

import telnetlib
import time

def test_inventory_vendor():
    """Test inventory and vendor functionality."""
    print("Testing Inventory and Vendor Systems")
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

    # Test inventory
    send_command("inventory")

    # Test getting an item
    send_command("get sword")

    # Check inventory again
    send_command("inventory")

    # Check stats (should show gold)
    send_command("stats")

    # Test vendor - list items
    send_command("list")

    # Buy something
    send_command("buy bread")

    # Check inventory and gold
    send_command("inventory")

    # Sell something
    send_command("sell sword")

    # Final inventory check
    send_command("inventory")

    # Drop an item
    send_command("drop bread")

    # Final check
    send_command("inventory")

    tn.write(b"quit\n")
    tn.close()
    print("\nInventory and vendor test complete!")

if __name__ == "__main__":
    test_inventory_vendor()