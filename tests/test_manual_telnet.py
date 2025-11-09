#!/usr/bin/env python3
"""Manual test for Enter key reload."""

import telnetlib
import time

# Connect to the server
print("Connecting to MUD server...")
tn = telnetlib.Telnet("localhost", 4002)

# Read welcome message
print("\n=== Welcome Message ===")
welcome = tn.read_until(b"username: ", timeout=2)
print(welcome.decode('utf-8'))

# Send username
print("\n=== Logging in as 'testuser' ===")
tn.write(b"testuser\n")
time.sleep(0.5)

# Read login response
response = tn.read_very_eager()
print(response.decode('utf-8'))

print("\n=== Now pressing Enter (empty line) ===")
# Send just Enter (empty line)
tn.write(b"\n")
time.sleep(1)

# Read response from Enter key
response = tn.read_very_eager()
print("Response after pressing Enter:")
print(response.decode('utf-8'))

print("\n=== Pressing Enter again ===")
# Send Enter again
tn.write(b"\n")
time.sleep(1)

response = tn.read_very_eager()
print("Response after second Enter:")
print(response.decode('utf-8'))

# Send quit
print("\n=== Quitting ===")
tn.write(b"quit\n")
time.sleep(0.5)
response = tn.read_very_eager()
print(response.decode('utf-8'))

tn.close()
print("Test complete!")