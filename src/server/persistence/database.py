"""Database connection and management."""

import sqlite3
from typing import Dict, Any, List, Optional
import json

class Database:
    """Handles database operations for the MUD."""

    def __init__(self, db_path: str = "mud.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self):
        """Connect to the database."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.create_tables()

    def disconnect(self):
        """Disconnect from the database."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def create_tables(self):
        """Create necessary database tables."""
        cursor = self.connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL DEFAULT '',
                email TEXT,
                character_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                name TEXT UNIQUE NOT NULL,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                mana INTEGER DEFAULT 50,
                max_mana INTEGER DEFAULT 50,
                room_id TEXT DEFAULT 'starting_room',
                stats TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                equipped BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (character_id) REFERENCES characters (id)
            )
        ''')

        # Add character_data column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE players ADD COLUMN character_data TEXT")
            self.connection.commit()
        except sqlite3.OperationalError:
            # Column already exists
            pass

        self.connection.commit()

    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a SELECT query."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        # Store lastrowid for get_last_insert_id()
        self._last_insert_id = cursor.lastrowid
        return cursor.rowcount

    def get_last_insert_id(self) -> int:
        """Get the last inserted row ID."""
        return getattr(self, '_last_insert_id', None)