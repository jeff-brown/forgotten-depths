#!/usr/bin/env python3
"""Administrative tools for Forgotten Depths MUD."""

import sys
import os
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def list_players(db_path: str):
    """List all players in the database."""
    from server.persistence.database import Database

    db = Database(db_path)
    db.connect()

    players = db.execute_query("SELECT id, name, email, created_at FROM players ORDER BY created_at")

    print(f"{'ID':<5} {'Name':<20} {'Email':<30} {'Created'}")
    print("-" * 70)

    for player in players:
        created = player['created_at'][:19] if player['created_at'] else 'Unknown'
        print(f"{player['id']:<5} {player['name']:<20} {player['email'] or 'N/A':<30} {created}")

    print(f"\nTotal players: {len(players)}")
    db.disconnect()

def list_characters(db_path: str, player_name: str = None):
    """List characters, optionally filtered by player."""
    from server.persistence.database import Database

    db = Database(db_path)
    db.connect()

    if player_name:
        query = """
            SELECT c.id, c.name, c.level, c.room_id, p.name as player_name
            FROM characters c
            JOIN players p ON c.player_id = p.id
            WHERE p.name = ?
            ORDER BY c.created_at
        """
        characters = db.execute_query(query, (player_name,))
    else:
        query = """
            SELECT c.id, c.name, c.level, c.room_id, p.name as player_name
            FROM characters c
            JOIN players p ON c.player_id = p.id
            ORDER BY c.created_at
        """
        characters = db.execute_query(query)

    print(f"{'ID':<5} {'Character':<20} {'Player':<20} {'Level':<7} {'Room'}")
    print("-" * 80)

    for char in characters:
        print(f"{char['id']:<5} {char['name']:<20} {char['player_name']:<20} {char['level']:<7} {char['room_id'] or 'None'}")

    print(f"\nTotal characters: {len(characters)}")
    db.disconnect()

def delete_player(db_path: str, player_name: str, confirm: bool = False):
    """Delete a player and all their characters."""
    from server.persistence.database import Database

    if not confirm:
        response = input(f"Are you sure you want to delete player '{player_name}' and all their characters? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            return

    db = Database(db_path)
    db.connect()

    # Get player ID
    player_result = db.execute_query("SELECT id FROM players WHERE name = ?", (player_name,))
    if not player_result:
        print(f"Player '{player_name}' not found.")
        db.disconnect()
        return

    player_id = player_result[0]['id']

    # Delete character items
    db.execute_update("""
        DELETE FROM character_items
        WHERE character_id IN (SELECT id FROM characters WHERE player_id = ?)
    """, (player_id,))

    # Delete characters
    char_count = db.execute_update("DELETE FROM characters WHERE player_id = ?", (player_id,))

    # Delete player
    player_count = db.execute_update("DELETE FROM players WHERE id = ?", (player_id,))

    print(f"Deleted player '{player_name}' and {char_count} characters.")
    db.disconnect()

def backup_database(db_path: str, backup_path: str = None):
    """Create a backup of the database."""
    import shutil
    from datetime import datetime

    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backups/mud_backup_{timestamp}.db"

    # Ensure backup directory exists
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)

    try:
        shutil.copy2(db_path, backup_path)
        print(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

def show_database_stats(db_path: str):
    """Show database statistics."""
    from server.persistence.database import Database

    db = Database(db_path)
    db.connect()

    # Get table counts
    stats = {}
    tables = ['players', 'characters', 'character_items']

    for table in tables:
        result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
        stats[table] = result[0]['count']

    # Get database size
    db_file = Path(db_path)
    if db_file.exists():
        size_mb = db_file.stat().st_size / (1024 * 1024)
    else:
        size_mb = 0

    print("DATABASE STATISTICS")
    print("=" * 30)
    print(f"Database file: {db_path}")
    print(f"File size: {size_mb:.2f} MB")
    print()
    print("Table counts:")
    for table, count in stats.items():
        print(f"  {table}: {count}")

    db.disconnect()

def verify_world_data():
    """Verify world data integrity."""
    try:
        from scripts.create_world import load_world_data, validate_world_data

        world_data = load_world_data()
        errors = validate_world_data(world_data)

        if errors:
            print("WORLD DATA VALIDATION ERRORS:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("World data validation passed!")
            return True

    except Exception as e:
        print(f"Error validating world data: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Forgotten Depths MUD Admin Tools")
    parser.add_argument("--db-path", default="data/mud.db",
                       help="Path to database file")

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List players command
    subparsers.add_parser('list-players', help='List all players')

    # List characters command
    chars_parser = subparsers.add_parser('list-characters', help='List characters')
    chars_parser.add_argument('--player', help='Filter by player name')

    # Delete player command
    delete_parser = subparsers.add_parser('delete-player', help='Delete a player')
    delete_parser.add_argument('player_name', help='Name of player to delete')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')

    # Backup database command
    backup_parser = subparsers.add_parser('backup', help='Backup database')
    backup_parser.add_argument('--output', help='Backup file path')

    # Database stats command
    subparsers.add_parser('stats', help='Show database statistics')

    # Verify world data command
    subparsers.add_parser('verify-world', help='Verify world data integrity')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Execute command
    try:
        if args.command == 'list-players':
            list_players(args.db_path)

        elif args.command == 'list-characters':
            list_characters(args.db_path, args.player)

        elif args.command == 'delete-player':
            delete_player(args.db_path, args.player_name, args.force)

        elif args.command == 'backup':
            backup_database(args.db_path, args.output)

        elif args.command == 'stats':
            show_database_stats(args.db_path)

        elif args.command == 'verify-world':
            verify_world_data()

    except Exception as e:
        print(f"Error executing command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()