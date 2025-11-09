#!/usr/bin/env python3
"""Simple loot drop test."""
import time
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 4000))
time.sleep(0.5)

# Helper to read with timeout
def read_all(timeout=0.5):
    sock.settimeout(timeout)
    data = []
    try:
        while True:
            chunk = sock.recv(4096).decode('utf-8', errors='ignore')
            if chunk:
                data.append(chunk)
            else:
                break
    except socket.timeout:
        pass
    sock.settimeout(None)
    return ''.join(data)

# Read welcome
print(read_all())

# Login
sock.send(b"testloot\n")
time.sleep(0.5)
print(read_all())

#Password
sock.send(b"\n")
time.sleep(1)
print(read_all())

# Go west to town square
sock.send(b"west\n")
time.sleep(0.8)
print("=== WEST to town square ===")
print(read_all())

# Go south to market square
sock.send(b"south\n")
time.sleep(0.8)
print("=== SOUTH to market square ===")
print(read_all())

# Go west to tavern
sock.send(b"west\n")
time.sleep(0.8)
print("=== WEST to tavern ===")
print(read_all())

# Go north to arena
sock.send(b"north\n")
time.sleep(0.8)
print("=== NORTH to arena ===")
print(read_all())

# Ring gong
sock.send(b"ring gong\n")
time.sleep(1)
print("=== RING GONG ===")
print(read_all())

# Attack 5 times
for i in range(5):
    sock.send(b"a glad\n")
    time.sleep(2)
    print(f"=== ATTACK {i+1} ===")
    print(read_all())

sock.close()
