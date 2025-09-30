#!/usr/bin/env python3
"""Main entry point for Forgotten Depths MUD - Async Version."""

import sys
import os
import asyncio
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def main():
    """Main async entry point."""
    # Import and run the async start server script
    from scripts.start_async_server import main as start_async_server_main

    # Change to project directory
    os.chdir(Path(__file__).parent)

    try:
        await start_async_server_main()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def run():
    """Run the async main function."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    run()