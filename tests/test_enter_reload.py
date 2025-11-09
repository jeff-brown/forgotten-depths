#!/usr/bin/env python3
"""Test script to verify Enter key UI reload functionality."""

import socket
import time
import sys

def test_enter_reload():
    """Test that pressing Enter reloads the UI."""
    print("Testing Enter Key UI Reload Feature")
    print("=" * 60)

    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', 4002))
        print("✓ Connected to server on port 4002")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False

    # Helper function to read all available data
    def read_response(wait_time=0.5):
        time.sleep(wait_time)
        sock.settimeout(0.5)
        response = ""
        try:
            while True:
                data = sock.recv(1024).decode('utf-8')
                if not data:
                    break
                response += data
        except socket.timeout:
            pass
        return response

    # Get welcome message
    welcome = read_response()
    print(f"\n1. Welcome message received:\n{welcome[:50]}...")

    # Send username
    sock.send(b"testuser\n")
    login_response = read_response()
    print(f"\n2. Logged in as 'testuser'")

    # Test 1: Send empty command (Enter key)
    print("\n3. Testing Enter key (empty command)...")
    sock.send(b"\n")  # Just a newline - simulates pressing Enter
    ui_response = read_response(1.0)

    # Check if UI header is present
    if "===" in ui_response and "testuser" in ui_response:
        print("✓ UI header with username displayed")
    else:
        print("✗ UI header not found")

    if "Exits:" in ui_response:
        print("✓ Exits information displayed")
    else:
        print("✗ Exits information not found")

    print(f"\nActual response:\n{ui_response}")

    # Test 2: Send another empty command to verify consistency
    print("\n4. Testing Enter key again...")
    sock.send(b"\n")
    ui_response2 = read_response(1.0)

    if "===" in ui_response2:
        print("✓ UI reload works consistently")
    else:
        print("✗ UI reload not consistent")

    # Clean up
    sock.send(b"quit\n")
    read_response()
    sock.close()

    print("\n" + "=" * 60)
    print("Test completed!")
    return True

if __name__ == "__main__":
    success = test_enter_reload()
    sys.exit(0 if success else 1)