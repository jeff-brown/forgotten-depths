#!/usr/bin/env python3
"""Simple test for inventory commands."""

import telnetlib
import time

print("Simple inventory test...")

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

# Test help first to see if new commands are listed
print("\nTesting help command:")
tn.write(b"help\n")
time.sleep(1)
response = tn.read_very_eager()
print(response.decode('utf-8'))

tn.write(b"quit\n")
tn.close()
print("Test complete!")