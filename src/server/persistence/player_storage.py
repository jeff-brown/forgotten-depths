"""Player and character data storage."""

import json
import hashlib
from typing import Optional, List, Dict, Any
from .database import Database

class PlayerStorage:
    """Handles saving and loading player data."""

    def __init__(self, database: Database):
        """Initialize player storage."""
        self.db = database

    def create_player(self, name: str, password: str, email: str = None) -> int:
        """Create a new player account."""
        password_hash = self._hash_password(password)
        query = "INSERT INTO players (name, password_hash, email) VALUES (?, ?, ?)"
        self.db.execute_update(query, (name, password_hash, email))
        return self.db.get_last_insert_id()

    def authenticate_player(self, name: str, password: str) -> Optional[int]:
        """Authenticate a player login."""
        password_hash = self._hash_password(password)
        query = "SELECT id FROM players WHERE name = ? AND password_hash = ?"
        result = self.db.execute_query(query, (name, password_hash))
        return result[0]['id'] if result else None

    def get_player(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player data by ID."""
        query = "SELECT * FROM players WHERE id = ?"
        result = self.db.execute_query(query, (player_id,))
        return dict(result[0]) if result else None

    def save_character(self, character: 'Character', player_id: int) -> int:
        """Save character data."""
        stats_json = json.dumps(character.stats)

        if hasattr(character, 'id') and character.id:
            query = '''
                UPDATE characters SET level = ?, experience = ?, health = ?,
                max_health = ?, mana = ?, max_mana = ?, room_id = ?, stats = ?
                WHERE id = ?
            '''
            params = (character.level, character.experience, character.health,
                     character.max_health, character.mana, character.max_mana,
                     character.room_id, stats_json, character.id)
            self.db.execute_update(query, params)
            return character.id
        else:
            query = '''
                INSERT INTO characters
                (player_id, name, level, experience, health, max_health,
                 mana, max_mana, room_id, stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = (player_id, character.name, character.level, character.experience,
                     character.health, character.max_health, character.mana,
                     character.max_mana, character.room_id, stats_json)
            self.db.execute_update(query, params)
            return self.db.get_last_insert_id()

    def load_character(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Load character data by ID."""
        query = "SELECT * FROM characters WHERE id = ?"
        result = self.db.execute_query(query, (character_id,))
        if result:
            char_data = dict(result[0])
            char_data['stats'] = json.loads(char_data['stats'])
            return char_data
        return None

    def get_player_characters(self, player_id: int) -> List[Dict[str, Any]]:
        """Get all characters for a player."""
        query = "SELECT * FROM characters WHERE player_id = ?"
        results = self.db.execute_query(query, (player_id,))
        characters = []
        for row in results:
            char_data = dict(row)
            char_data['stats'] = json.loads(char_data['stats'])
            characters.append(char_data)
        return characters

    def delete_character(self, character_id: int):
        """Delete a character."""
        self.db.execute_update("DELETE FROM character_items WHERE character_id = ?", (character_id,))
        self.db.execute_update("DELETE FROM characters WHERE id = ?", (character_id,))

    def save_character_data(self, username: str, character_data: Dict[str, Any]) -> bool:
        """Save character data as JSON for a player.

        Args:
            username: The player's username
            character_data: The character dict to save

        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Check if database connection is valid
            if not self.db or not self.db.connection:
                print(f"Cannot save character for {username}: database not connected")
                return False

            # Convert character data to JSON (convert sets to lists for JSON serialization)
            character_data_copy = character_data.copy()
            if 'visited_rooms' in character_data_copy and isinstance(character_data_copy['visited_rooms'], set):
                character_data_copy['visited_rooms'] = list(character_data_copy['visited_rooms'])
            character_json = json.dumps(character_data_copy, indent=2)

            # Check if player exists
            check_query = "SELECT id FROM players WHERE name = ?"
            result = self.db.execute_query(check_query, (username,))

            if result:
                # Update existing player
                update_query = "UPDATE players SET character_data = ? WHERE name = ?"
                self.db.execute_update(update_query, (character_json, username))
            else:
                # Insert new player (with empty password hash for dev mode)
                insert_query = "INSERT INTO players (name, password_hash, character_data) VALUES (?, ?, ?)"
                self.db.execute_update(insert_query, (username, '', character_json))

            return True
        except Exception as e:
            print(f"Error saving character data for {username}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_character_data(self, username: str) -> Optional[Dict[str, Any]]:
        """Load character data for a player.

        Args:
            username: The player's username

        Returns:
            Character data dict or None if not found
        """
        try:
            # Check if database connection is valid
            if not self.db or not self.db.connection:
                print(f"Cannot load character for {username}: database not connected")
                return None

            query = "SELECT character_data FROM players WHERE name = ?"
            result = self.db.execute_query(query, (username,))

            if result and len(result) > 0:
                char_data = result[0]['character_data']
                if char_data:
                    character_data = json.loads(char_data)
                    # Convert visited_rooms list back to set
                    if 'visited_rooms' in character_data and isinstance(character_data['visited_rooms'], list):
                        character_data['visited_rooms'] = set(character_data['visited_rooms'])
                    return character_data
            return None
        except Exception as e:
            print(f"Error loading character data for {username}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _hash_password(self, password: str) -> str:
        """Hash a password for storage."""
        return hashlib.sha256(password.encode()).hexdigest()