#!/usr/bin/env python3
"""Start the async MUD server with optimized consolidated Ether world data."""

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
from server.persistence.consolidated_world_loader import ConsolidatedWorldLoader
from server.utils.logger import get_logger


async def start_optimized_ether_server():
    """Start the server with optimized Ether world data."""
    print("=== Forgotten Depths MUD - Optimized Ether World ===")
    print()

    # Setup logging
    logger = get_logger()
    logger.info("Optimized server starting")

    # Initialize database
    print("Initializing database...")
    database = Database("data/ether_optimized_mud.db")
    database.connect()
    print("Database initialized")

    # Initialize game engine with optimized loader
    game_engine = AsyncGameEngine()
    game_engine.initialize_database(database)

    # Replace the world loader with the optimized version
    consolidated_loader = ConsolidatedWorldLoader("./data/consolidated_ether")
    consolidated_loader.set_load_format("auto")  # Use the fastest available format
    game_engine.world_manager.world_loader = consolidated_loader

    # Start server
    host = "localhost"
    port = 4000

    print(f"Starting optimized Ether MUD server on {host}:{port}")
    print("Using fastest available world data format...")
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
        await start_optimized_ether_server()
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