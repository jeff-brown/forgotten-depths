#!/usr/bin/env python3
"""Test loot drop functionality."""
import time
import socket
import sys

def send_command(sock, command, delay=0.8):
    """Send a command and wait."""
    print(f"\n>>> {command}")
    sock.send(f"{command}\n".encode())
    time.sleep(delay)
    # Read all available response
    sock.settimeout(0.3)
    responses = []
    while True:
        try:
            data = sock.recv(4096).decode('utf-8', errors='ignore')
            if data:
                responses.append(data)
            else:
                break
        except socket.timeout:
            break
    sock.settimeout(None)
    if responses:
        print(''.join(responses), end='')

def main():
    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 4000))

    # Wait for welcome message
    time.sleep(0.5)
    sock.settimeout(0.5)
    try:
        print(sock.recv(4096).decode('utf-8', errors='ignore'), end='')
    except socket.timeout:
        pass
    sock.settimeout(None)

    # Login
    send_command(sock, "testloot", 1)  # username
    send_command(sock, "", 2)  # password (empty for dev mode)

    # Navigate to arena
    send_command(sock, "west", 1)  # to town square
    send_command(sock, "south", 1)  # to market square
    send_command(sock, "north", 1)  # to arena

    # Ring gong to spawn mob
    send_command(sock, "ring gong", 1)

    # Attack mob multiple times
    for i in range(5):
        send_command(sock, "a glad", 2)

    # Close
    sock.close()

if __name__ == "__main__":
    main()
