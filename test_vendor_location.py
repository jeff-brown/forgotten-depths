#!/usr/bin/env python3
"""Test to check current room ID."""

import telnetlib
import time

print("Testing room ID...")

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

# Look around to see current room
print("\nLooking around:")
tn.write(b"look\n")
time.sleep(1)
response = tn.read_very_eager()
print(response.decode('utf-8'))

tn.write(b"quit\n")
tn.close()
print("Test complete!")