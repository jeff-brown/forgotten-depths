#!/usr/bin/env python3
"""Script to start the Forgotten Depths MUD server."""

import sys
import os
import argparse
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
    import logging
    from server.utils.logger import get_logger

    level = config.get('logging', {}).get('level', 'INFO')
    log_file = config.get('logging', {}).get('file', 'logs/server.log')

    # Ensure logs directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = get_logger()
    logger.info("Logging initialized")

def initialize_database(db_config: dict):
    """Initialize the database."""
    from server.persistence.database import Database

    db_path = db_config.get('database', {}).get('path', 'data/mud.db')

    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    db = Database(db_path)
    db.connect()
    print(f"Database initialized at {db_path}")
    return db

def start_game_engine(config: dict, db):
    """Start the game engine."""
    from server.core.game_engine import GameEngine

    engine = GameEngine()
    # Configure engine with settings
    engine.start()
    print("Game engine started")
    return engine

def start_server(config: dict, database):
    """Start the MUD server."""
    from server.core.game_engine import GameEngine

    host = config.get('network', {}).get('host', 'localhost')
    port = config.get('network', {}).get('port', 4000)

    # Create and configure game engine
    game_engine = GameEngine()
    game_engine.initialize_database(database)

    print(f"Starting MUD server on {host}:{port}")

    try:
        game_engine.start(host, port)

        # Keep the main thread alive
        import time
        while game_engine.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        game_engine.stop()

    return game_engine

def start_web_client(config: dict):
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
        socketio.run(app, debug=debug, host=host, port=port)

    except ImportError:
        print("Web client dependencies not available. Install flask and flask-socketio to enable web client.")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Start Forgotten Depths MUD Server")
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
        start_web_client(server_config)
    else:
        # Initialize database
        database = initialize_database(db_config)

        # Start game engine
        game_engine = start_game_engine(server_config, database)

        # Start web client in background if enabled and not disabled
        if not args.no_web:
            import threading
            web_thread = threading.Thread(target=start_web_client, args=(server_config,))
            web_thread.daemon = True
            web_thread.start()

        # Start the main MUD server (this will block)
        try:
            start_server(server_config, database)
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            if database:
                database.disconnect()

if __name__ == "__main__":
    main()