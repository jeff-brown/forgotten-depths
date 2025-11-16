#!/usr/bin/env python3
"""Async version of the server startup script."""

import sys
import os
import argparse
import asyncio
import yaml
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def load_config(config_file: str) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Configuration file {config_file} not found!")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
        sys.exit(1)

def setup_logging(config: dict):
    """Setup logging based on configuration."""
    from server.utils.logger import get_logger

    logger = get_logger()
    logger.info("Async logging initialized")

def initialize_database(db_config: dict):
    """Initialize the database."""
    from server.persistence.database import Database

    # Use DB_PATH env var if set, otherwise use config file
    db_path = os.environ.get('DB_PATH') or db_config.get('database', {}).get('path', 'data/mud.db')

    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    db = Database(db_path)
    db.connect()
    print(f"Database initialized at {db_path}")
    return db

async def start_async_server(config: dict, database):
    """Start the async MUD server."""
    from server.core.async_game_engine import AsyncGameEngine

    host = config.get('network', {}).get('host', 'localhost')
    port = config.get('network', {}).get('port', 4000)

    # Create and configure game engine
    game_engine = AsyncGameEngine()
    game_engine.initialize_database(database)

    print(f"Starting async MUD server on {host}:{port}")

    try:
        await game_engine.start(host, port)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        await game_engine.stop()

    return game_engine

async def start_web_client(config: dict):
    """Start the web client if enabled."""
    web_config = config.get('web', {})
    if not web_config.get('enabled', True):
        return

    try:
        from client.web_client.app import app, socketio

        host = web_config.get('host', '0.0.0.0')
        port = web_config.get('port', 8080)
        debug = web_config.get('debug', False)

        print(f"Starting web client on {host}:{port}")

        # Run in a separate thread since Flask-SocketIO isn't fully async
        import threading
        web_thread = threading.Thread(
            target=lambda: socketio.run(app, debug=debug, host=host, port=port),
            daemon=True
        )
        web_thread.start()

    except ImportError:
        print("Web client dependencies not available. Install flask and flask-socketio to enable web client.")

async def main():
    """Main async function."""
    parser = argparse.ArgumentParser(description="Start Async Forgotten Depths MUD Server")
    parser.add_argument("--config", "-c", default="config/server.yaml",
                       help="Path to server configuration file")
    parser.add_argument("--db-config", default="config/database.yaml",
                       help="Path to database configuration file")
    parser.add_argument("--web-only", action="store_true",
                       help="Start only the web client")
    parser.add_argument("--no-web", action="store_true",
                       help="Don't start the web client")

    args = parser.parse_args()

    # Change to the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Load configurations
    server_config = load_config(args.config)
    db_config = load_config(args.db_config)

    # Setup logging
    setup_logging(server_config)

    if args.web_only:
        # Start only web client
        await start_web_client(server_config)
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down web client...")
    else:
        # Initialize database
        database = initialize_database(db_config)

        try:
            # Start web client if enabled and not disabled
            if not args.no_web:
                await start_web_client(server_config)

            # Start the main MUD server (this will run until stopped)
            await start_async_server(server_config, database)

        finally:
            if database:
                database.disconnect()

def run():
    """Run the async main function."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    run()