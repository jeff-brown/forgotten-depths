#!/usr/bin/env python3
"""Manual equipment test - use proper item names."""

import telnetlib
import time

print("Manual Equipment Test")
print("=" * 30)

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

# Test with correct item names from config
print("\n=== Get equipment items ===")
send_command("get short sword")
send_command("get leather armor")
send_command("inventory")

print("\n=== Equip weapon ===")
send_command("equip short sword")
send_command("inventory")

print("\n=== Equip armor ===")
send_command("equip leather armor")
send_command("inventory")

tn.write(b"quit\n")
tn.close()
print("\nManual test complete!")