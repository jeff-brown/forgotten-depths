#!/usr/bin/env python3
"""Simple telnet client to test MUD connection."""

import socket
import time
import sys

def test_mud_connection():
    """Test connection to MUD server."""
    print("Connecting to MUD server...")

    try:
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 4000))

        # Receive welcome message
        response = sock.recv(1024).decode('utf-8')
        print("Server:", response.strip())

        # Send username
        username = "testuser"
        print(f"Sending username: {username}")
        sock.send(f"{username}\n".encode('utf-8'))
        time.sleep(0.5)

        # Receive response
        response = sock.recv(1024).decode('utf-8')
        print("Server:", response.strip())

        # Send commands
        commands = ["look", "help", "exits"]

        for cmd in commands:
            print(f"\nSending command: {cmd}")
            sock.send(f"{cmd}\n".encode('utf-8'))
            time.sleep(0.5)

            # Receive response
            try:
                response = sock.recv(4096).decode('utf-8')
                if response:
                    print("Server response:")
                    print(response.strip())
                else:
                    print("No response received")
            except Exception as e:
                print(f"Error receiving response: {e}")
                break

        # Quit
        print("\nSending quit command...")
        sock.send("quit\n".encode('utf-8'))
        time.sleep(0.5)

        response = sock.recv(1024).decode('utf-8')
        print("Server:", response.strip())

        sock.close()
        print("\nConnection closed.")

    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    test_mud_connection()