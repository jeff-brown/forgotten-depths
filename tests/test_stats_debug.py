#!/usr/bin/env python3
"""Debug stats command."""

import telnetlib
import time

print("Debug test for stats command...")

# Connect to async server
tn = telnetlib.Telnet("localhost", 4000)
time.sleep(0.5)

# Read welcome
welcome = tn.read_very_eager()
print(f"Welcome: {welcome.decode('utf-8')[:50]}...")

# Login
tn.write(b"testuser\n")
time.sleep(0.5)
response = tn.read_very_eager()
print(f"Username response: {response.decode('utf-8')[:50]}...")

tn.write(b"password\n")
time.sleep(0.5)
response = tn.read_very_eager()
print(f"Password response: {response.decode('utf-8')[:100]}...")

# Test help command first
print("\nTesting 'help' command:")
tn.write(b"help\n")
time.sleep(1)
response = tn.read_very_eager()
print(response.decode('utf-8'))

# Test look command
print("\nTesting 'look' command:")
tn.write(b"look\n")
time.sleep(1)
response = tn.read_very_eager()
print(response.decode('utf-8'))

# Now test stats
print("\nTesting 'stats' command:")
tn.write(b"stats\n")
time.sleep(1)
response = tn.read_very_eager()
print(f"Stats response: '{response.decode('utf-8')}'")

tn.write(b"quit\n")
tn.close()
print("Debug test complete!")