#!/usr/bin/env python3
"""Start the async MUD server with the imported Ether world data."""

import asyncio
import signal
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from server.core.async_game_engine import AsyncGameEngine
from server.persistence.database import Database
from server.utils.logger import get_logger


async def start_ether_server():
    """Start the server with Ether world data."""
    print("=== Forgotten Depths MUD - Ether World Edition ===")
    print()

    # Setup logging
    logger = get_logger()
    logger.info("Async logging initialized")

    # Initialize database
    print("Initializing database...")
    database = Database("data/ether_mud.db")
    database.connect()
    print("Database initialized")

    # Initialize game engine
    game_engine = AsyncGameEngine()
    game_engine.initialize_database(database)

    # Override world loader to use Ether data
    game_engine.world_manager.world_loader.data_dir = "./data/imported_ether"

    # Start server
    host = "localhost"
    port = 4000

    print(f"Starting Ether MUD server on {host}:{port}")
    print("Loading massive world from imported Ether XML data...")
    print()

    try:
        # Start the async server
        await game_engine.start(host, port)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await game_engine.stop()
        database.disconnect()
        print("Server stopped")


def handle_signal(signum, frame):
    """Handle shutdown signals."""
    print(f"\nReceived signal {signum}")
    sys.exit(0)


async def main():
    """Main async entry point."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        await start_ether_server()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run():
    """Run the async main function."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    run()