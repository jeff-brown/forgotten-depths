#!/usr/bin/env python3
"""Test script to verify live combat system with fatigue."""

import asyncio
import telnetlib3

async def test_live_combat():
    """Test the live combat system with real telnet connection."""
    print("Testing Live Combat System")
    print("=" * 40)

    try:
        # Connect to the server
        reader, writer = await telnetlib3.open_connection('localhost', 4000)
        print("✅ Connected to server")

        # Read welcome message
        welcome = await asyncio.wait_for(reader.read(1024), timeout=5.0)
        print(f"Welcome: {welcome.strip()}")

        # Login as guest
        writer.write('guest\n')
        await writer.drain()

        # Wait for response
        response = await asyncio.wait_for(reader.read(1024), timeout=5.0)
        print(f"Login response: {response.strip()}")

        # Look around
        writer.write('look\n')
        await writer.drain()

        response = await asyncio.wait_for(reader.read(1024), timeout=5.0)
        print(f"Look response: {response.strip()}")

        # Try to attack (should fail if no mob)
        writer.write('attack goblin\n')
        await writer.drain()

        response = await asyncio.wait_for(reader.read(1024), timeout=5.0)
        print(f"Attack response: {response.strip()}")

        # Check status command
        writer.write('status\n')
        await writer.drain()

        response = await asyncio.wait_for(reader.read(1024), timeout=5.0)
        print(f"Status response: {response.strip()}")

        # Close connection
        writer.close()
        await writer.wait_closed()
        print("✅ Disconnected from server")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_combat())