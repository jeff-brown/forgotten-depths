#!/usr/bin/env python3
"""Test selling loot items to verify correct pricing."""
import time
import socket
import re

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 4000))
time.sleep(0.5)

def read_all(timeout=0.5):
    sock.settimeout(timeout)
    data = []
    try:
        while True:
            chunk = sock.recv(4096).decode('utf-8', errors='ignore')
            if chunk:
                data.append(chunk)
    except socket.timeout:
        pass
    sock.settimeout(None)
    return ''.join(data)

# Welcome
read_all()

# Login as testsell
sock.send(b"testsell\n")
time.sleep(0.5)
read_all()

# Password
sock.send(b"\n")
time.sleep(1)
print(read_all())

# Go to arena: west -> south -> west -> north
for cmd in [b"west\n", b"south\n", b"west\n", b"north\n"]:
    sock.send(cmd)
    time.sleep(0.8)
    read_all()

# Ring gong
sock.send(b"ring gong\n")
time.sleep(2)
output = read_all()
print(f"=== GONG OUTPUT ===\n{output}")

# Extract mob name from output
mob_match = re.search(r'a (\w+(?:\s+\w+)*) emerges', output, re.IGNORECASE)
if mob_match:
    mob_name = mob_match.group(1).lower()
    print(f"Detected mob: {mob_name}")
else:
    mob_name = "skeleton"
    print(f"Could not detect mob, using default: {mob_name}")

# Attack the mob until it dies (max 20 attacks)
for i in range(20):
    sock.send(f"a {mob_name}\n".encode())
    time.sleep(1.5)
    output = read_all()
    print(f"=== ATTACK {i+1} ===\n{output}")
    if "killed" in output.lower() or "dies" in output.lower():
        print("Mob is dead!")
        break

# Look for items on the ground
time.sleep(1)
sock.send(b"look\n")
time.sleep(0.5)
look_output = read_all()
print(f"=== LOOK ===\n{look_output}")

# Get first item from ground
sock.send(b"get all\n")
time.sleep(0.5)
get_output = read_all()
print(f"=== GET ALL ===\n{get_output}")

# Check inventory
sock.send(b"inventory\n")
time.sleep(0.5)
inv_output = read_all()
print(f"=== INVENTORY ===\n{inv_output}")

# Go back to market square to find vendor: south -> east -> north
for cmd in [b"south\n", b"east\n", b"north\n"]:
    sock.send(cmd)
    time.sleep(0.8)
    read_all()

# List vendor items to confirm we're at a vendor
sock.send(b"list\n")
time.sleep(0.5)
list_output = read_all()
print(f"=== VENDOR LIST ===\n{list_output}")

# Try to sell the first item we picked up
# Extract item name from get_output
item_match = re.search(r"You pick up (.+)\.", get_output)
if item_match:
    item_name = item_match.group(1).strip()
    print(f"\nAttempting to sell: {item_name}")
    sock.send(f"sell {item_name}\n".encode())
    time.sleep(0.5)
    sell_output = read_all()
    print(f"=== SELL OUTPUT ===\n{sell_output}")

    # Extract price from sell output
    price_match = re.search(r"for (\d+) gold", sell_output)
    if price_match:
        price = int(price_match.group(1))
        print(f"\n*** SOLD FOR: {price} gold ***")
else:
    print("No item found to sell")

sock.close()
