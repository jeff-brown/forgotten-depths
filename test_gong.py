#!/usr/bin/env python3
"""Test gong to see debug output."""
import time
import socket

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

# Login
sock.send(b"tester\n")
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
    print(read_all())

# Ring gong
sock.send(b"ring gong\n")
time.sleep(3)
print(read_all())

sock.close()
