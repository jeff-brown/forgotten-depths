#!/usr/bin/env python3
"""Debug drop system to see what's happening."""

import telnetlib
import time

print("Debug Drop Test")

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

# Get an item
print("\nGetting arrow...")
tn.write(b"get arrow\n")
time.sleep(0.5)
response = tn.read_very_eager()
print(response.decode('utf-8'))

# Drop the item
print("\nDropping arrow...")
tn.write(b"drop arrow\n")
time.sleep(0.5)
response = tn.read_very_eager()
print(response.decode('utf-8'))

# Check room immediately after drop
print("\nChecking room after drop...")
tn.write(b"\n")  # Press enter
time.sleep(0.5)
response = tn.read_very_eager()
print(response.decode('utf-8'))

tn.write(b"quit\n")
tn.close()
print("Debug complete!")