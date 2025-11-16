#!/usr/bin/env python3
"""Initialize database if it doesn't exist."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def init_database(db_path: str = "data/mud.db"):
    """Initialize database if it doesn't exist."""
    from server.persistence.database import Database

    db_file = Path(db_path)

    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Check if database exists
    if db_file.exists():
        print(f"Database already exists at {db_path}")
        return

    print(f"Creating new database at {db_path}")

    # Create database with tables
    db = Database(db_path)
    db.connect()
    print("Database tables created successfully")
    db.disconnect()

    print("Database initialization complete!")

if __name__ == "__main__":
    # Use DB_PATH env var, command line arg, or default
    db_path = os.environ.get('DB_PATH') or (sys.argv[1] if len(sys.argv) > 1 else "data/mud.db")
    init_database(db_path)
