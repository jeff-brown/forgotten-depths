#!/usr/bin/env python3
"""Script to reset the database and create fresh tables."""

import sys
import os
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def reset_database(db_path: str, backup: bool = True):
    """Reset the database by removing it and creating fresh tables."""
    from server.persistence.database import Database

    db_file = Path(db_path)

    # Create backup if requested and file exists
    if backup and db_file.exists():
        import shutil
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_file.with_suffix(f".backup_{timestamp}.db")
        shutil.copy2(db_file, backup_path)
        print(f"Database backed up to: {backup_path}")

    # Remove existing database
    if db_file.exists():
        db_file.unlink()
        print(f"Removed existing database: {db_path}")

    # Create new database with fresh tables
    db = Database(db_path)
    db.connect()
    print(f"Created new database: {db_path}")

    db.disconnect()
    print("Database reset complete!")

def create_test_data(db_path: str):
    """Create some test data for development."""
    from server.persistence.database import Database
    from server.persistence.player_storage import PlayerStorage

    db = Database(db_path)
    db.connect()

    player_storage = PlayerStorage(db)

    # Create test player
    try:
        player_id = player_storage.create_player("testuser", "password123", "test@example.com")
        print(f"Created test player with ID: {player_id}")

        # Create test character
        from server.game.player.character import Character
        test_char = Character("TestCharacter")
        test_char.room_id = "town_square"

        char_id = player_storage.save_character(test_char, player_id)
        print(f"Created test character with ID: {char_id}")

    except Exception as e:
        print(f"Error creating test data: {e}")

    db.disconnect()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Reset Forgotten Depths database")
    parser.add_argument("--db-path", default="data/mud.db",
                       help="Path to database file")
    parser.add_argument("--no-backup", action="store_true",
                       help="Don't create backup before reset")
    parser.add_argument("--test-data", action="store_true",
                       help="Create test data after reset")
    parser.add_argument("--force", action="store_true",
                       help="Don't ask for confirmation")

    args = parser.parse_args()

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Confirmation prompt
    if not args.force:
        db_path = Path(args.db_path)
        if db_path.exists():
            response = input(f"This will DELETE the database at {args.db_path}. Continue? (y/N): ")
            if response.lower() != 'y':
                print("Operation cancelled.")
                return
        else:
            print(f"Database {args.db_path} doesn't exist. Creating new one.")

    # Ensure data directory exists
    os.makedirs(os.path.dirname(args.db_path), exist_ok=True)

    try:
        # Reset database
        reset_database(args.db_path, backup=not args.no_backup)

        # Create test data if requested
        if args.test_data:
            print("Creating test data...")
            create_test_data(args.db_path)

        print("Database reset successful!")

    except Exception as e:
        print(f"Error resetting database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()