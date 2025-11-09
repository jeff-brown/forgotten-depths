#!/usr/bin/env python3
"""Working telnet client for MUD server."""

import socket
import time

def connect_to_mud():
    """Connect to MUD with proper authentication."""
    print("=== Connecting to Forgotten Depths MUD ===")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 4000))

        # Receive welcome
        response = sock.recv(1024).decode('utf-8')
        print(response.strip())

        # Send username
        username = "player1"
        print(f"\nEntering username: {username}")
        sock.send(f"{username}\n".encode('utf-8'))
        time.sleep(0.3)

        # Receive username confirmation and password prompt
        response = sock.recv(1024).decode('utf-8')
        print(response.strip())

        # Send password (try empty or "password")
        password = "password"
        print(f"Entering password: {password}")
        sock.send(f"{password}\n".encode('utf-8'))
        time.sleep(0.5)

        # Check response
        response = sock.recv(2048).decode('utf-8')
        print("\nServer response:")
        print(response.strip())

        if "Invalid credentials" in response:
            print("\n❌ Authentication failed. Let me try different credentials...")
            sock.close()
            return False

        # If we get here, try sending commands
        print("\n✅ Connected! Trying MUD commands...")

        commands = ["look", "help", "exits", "quit"]

        for cmd in commands:
            print(f"\n> {cmd}")
            sock.send(f"{cmd}\n".encode('utf-8'))
            time.sleep(0.5)

            response = sock.recv(4096).decode('utf-8')
            if response:
                print(response.strip())

            if cmd == "quit":
                break

        sock.close()
        return True

    except Exception as e:
        print(f"Connection error: {e}")
        return False

def try_different_credentials():
    """Try different username/password combinations."""
    credentials = [
        ("admin", "admin"),
        ("test", "test"),
        ("player", "player"),
        ("", ""),
        ("guest", "guest")
    ]

    for username, password in credentials:
        print(f"\n=== Trying {username}/{password} ===")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 4000))

            # Skip welcome message
            sock.recv(1024)

            # Send credentials
            sock.send(f"{username}\n".encode('utf-8'))
            time.sleep(0.3)
            sock.recv(1024)  # username response

            sock.send(f"{password}\n".encode('utf-8'))
            time.sleep(0.5)

            response = sock.recv(2048).decode('utf-8')

            if "Invalid credentials" not in response:
                print(f"✅ SUCCESS with {username}/{password}!")
                print("Server response:")
                print(response.strip())

                # Try a command
                sock.send("look\n".encode('utf-8'))
                time.sleep(0.5)
                look_response = sock.recv(2048).decode('utf-8')
                print("\nLook command response:")
                print(look_response.strip())

                sock.send("quit\n".encode('utf-8'))
                sock.recv(1024)
                sock.close()
                return True
            else:
                print(f"❌ Failed with {username}/{password}")

            sock.close()

        except Exception as e:
            print(f"Error with {username}/{password}: {e}")

    return False

if __name__ == "__main__":
    print("Attempting to connect to MUD server...")

    # First try
    if not connect_to_mud():
        print("\nFirst attempt failed. Trying different credentials...")
        try_different_credentials()