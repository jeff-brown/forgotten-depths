#!/usr/bin/env python3
"""Simple test script to demonstrate the integrated MUD server."""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_integration():
    """Test basic server integration."""
    from server.core.game_engine import GameEngine
    from server.persistence.database import Database

    print("=== Forgotten Depths MUD Integration Test ===")
    print()

    # Initialize database
    print("1. Initializing database...")
    database = Database("test_mud.db")
    database.connect()
    print("   ✓ Database connected")

    # Initialize game engine
    print("2. Initializing game engine...")
    game_engine = GameEngine()
    game_engine.initialize_database(database)
    print("   ✓ Game engine initialized")

    # Start server
    print("3. Starting server on localhost:4000...")
    try:
        game_engine.start("localhost", 4000)
        print("   ✓ Server started successfully!")
        print()
        print("Server is running. You can now connect with:")
        print("  - Telnet client: telnet localhost 4000")
        print("  - Terminal client: python src/client/terminal_client.py")
        print()
        print("Press Ctrl+C to stop the server...")

        # Keep running until interrupted
        while game_engine.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n4. Shutting down server...")
        game_engine.stop()
        print("   ✓ Server stopped")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        game_engine.stop()

    finally:
        database.disconnect()
        print("   ✓ Database disconnected")

    print()
    print("Integration test completed!")

if __name__ == "__main__":
    test_basic_integration()