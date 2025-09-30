#!/usr/bin/env python3
"""Debug command parsing to see what's happening."""

import telnetlib
import time

print("Debug Command Parsing Test")
print("=" * 40)

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

# Test the commands that are failing
print("\n=== Testing equip command ===")
send_command("get short sword")
send_command("equip short sword")  # This should work
send_command("equip short")        # This should also work but returns "Message sent"

print("\n=== Testing unequip command ===")
send_command("unequip short sword")  # This should work
send_command("unequip short")        # This should also work but returns "Message sent"

tn.write(b"quit\n")
tn.close()
print("\nDebug test complete!")