#!/usr/bin/env python3
"""Test Enter key reload for async server."""

import telnetlib
import time

print("Testing Async Server Enter Key Reload")
print("=" * 60)

# Connect to the async server
try:
    tn = telnetlib.Telnet("localhost", 4000)
    print("✓ Connected to async server on port 4000")
except Exception as e:
    print(f"✗ Failed to connect: {e}")
    exit(1)

# Wait for welcome message
time.sleep(0.5)
response = tn.read_very_eager()
print(f"\n1. Welcome message:\n{response.decode('utf-8')[:100]}...")

# Send username
print("\n2. Sending username 'testuser'")
tn.write(b"testuser\n")
time.sleep(0.5)

response = tn.read_very_eager()
print(f"Response:\n{response.decode('utf-8')}")

# Send password (simple auth)
print("\n3. Sending password")
tn.write(b"password\n")
time.sleep(0.5)

response = tn.read_very_eager()
print(f"Response:\n{response.decode('utf-8')[:150]}...")

# Test Enter key (empty command)
print("\n4. Testing Enter key (empty command) - should show UI header")
tn.write(b"\n")
time.sleep(1)

response = tn.read_very_eager()
print("Response after pressing Enter:")
print(response.decode('utf-8'))

# Check if UI elements are present
response_str = response.decode('utf-8')
if "===" in response_str:
    print("✓ UI header displayed")
else:
    print("✗ UI header not found")

if "Exits:" in response_str:
    print("✓ Exits information displayed")
else:
    print("✗ Exits information not displayed")

# Test Enter key again
print("\n5. Testing Enter key again")
tn.write(b"\n")
time.sleep(1)

response = tn.read_very_eager()
if "===" in response.decode('utf-8'):
    print("✓ UI reload works consistently")
else:
    print("✗ UI reload not consistent")

# Quit
print("\n6. Quitting")
tn.write(b"quit\n")
time.sleep(0.5)

tn.close()
print("\n" + "=" * 60)
print("Test completed!")