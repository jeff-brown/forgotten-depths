"""Main game engine that coordinates all game systems."""

import time
import threading
from typing import Optional, Dict, Any

from ..networking.connection_manager import ConnectionManager
from ..commands.base_command import CommandManager
from .world_manager import WorldManager
from .event_system import EventSystem
from ..persistence.database import Database
from ..persistence.player_storage import PlayerStorage
from ..utils.logger import get_logger
from ...shared.constants.game_constants import GAME_TICK_RATE


class GameEngine:
    """Central game engine that manages all game systems and coordinates updates."""

    def __init__(self):
        """Initialize the game engine."""
        self.logger = get_logger()
        self.running = False
        self.tick_rate = GAME_TICK_RATE

        # Core systems
        self.event_system = EventSystem()
        self.connection_manager = ConnectionManager()
        self.command_manager = CommandManager()
        self.world_manager = WorldManager()

        # Database and persistence
        self.database: Optional[Database] = None
        self.player_storage: Optional[PlayerStorage] = None

        # Player management
        self.connected_players: Dict[int, Any] = {}

        # Setup system connections
        self._setup_connections()

    def _setup_connections(self):
        """Setup connections between systems."""
        # Connect connection manager to game events
        self.connection_manager.on_player_connect = self._handle_player_connect
        self.connection_manager.on_player_disconnect = self._handle_player_disconnect
        self.connection_manager.on_player_command = self._handle_player_command

        # Subscribe to events
        self.event_system.subscribe('player_connected', self._on_player_connected)
        self.event_system.subscribe('player_disconnected', self._on_player_disconnected)
        self.event_system.subscribe('player_command', self._on_player_command)

    def initialize_database(self, database: Database):
        """Initialize database connection."""
        self.database = database
        self.player_storage = PlayerStorage(database)
        self.logger.info("Database initialized")

    def start(self, host: str = "localhost", port: int = 4000):
        """Start the game engine."""
        if self.running:
            self.logger.warning("Game engine is already running")
            return

        self.running = True
        self.logger.info("Starting game engine")

        # Initialize world
        self.world_manager.load_world()

        # Start connection manager
        self.connection_manager.initialize(host, port, self.event_system)
        self.connection_manager.start_server(host, port)

        # Start main game loop
        self._start_game_loop()

    def stop(self):
        """Stop the game engine."""
        if not self.running:
            return

        self.logger.info("Stopping game engine")
        self.running = False

        # Stop connection manager
        self.connection_manager.stop_server()

        # Save all player data
        self._save_all_players()

        # Disconnect database
        if self.database:
            self.database.disconnect()

    def _start_game_loop(self):
        """Start the main game loop in a separate thread."""
        game_thread = threading.Thread(target=self._game_loop, daemon=True)
        game_thread.start()

    def _game_loop(self):
        """Main game loop."""
        last_tick = time.time()

        while self.running:
            current_time = time.time()

            # Check if it's time for a tick
            if current_time - last_tick >= self.tick_rate:
                self.tick()
                last_tick = current_time

            # Small sleep to prevent busy waiting
            time.sleep(0.01)

    def tick(self):
        """Process one game tick."""
        try:
            # Update world
            self.world_manager.update_world()

            # Process any pending events
            # (Events are handled automatically by the event system)

            # Update NPCs, combat, etc.
            self._update_npcs()
            self._update_combat()

        except Exception as e:
            self.logger.error(f"Error in game tick: {e}")

    def _update_npcs(self):
        """Update all NPCs."""
        # This would update NPC AI, movement, etc.
        pass

    def _update_combat(self):
        """Update combat encounters."""
        # This would handle ongoing combat
        pass

    def _handle_player_connect(self, player_id: int):
        """Handle a new player connection."""
        self.logger.info(f"Player {player_id} connected")

        # Initialize player session
        self.connected_players[player_id] = {
            'player_id': player_id,
            'connection_time': time.time(),
            'authenticated': False,
            'character': None,
            'login_state': 'username_prompt'
        }

        # Send initial prompts
        self.connection_manager.send_message(player_id, "Welcome to Forgotten Depths!")
        self.connection_manager.send_message(player_id, "Username: ")

    def _handle_player_disconnect(self, player_id: int):
        """Handle a player disconnection."""
        self.logger.info(f"Player {player_id} disconnected")

        if player_id in self.connected_players:
            player_data = self.connected_players[player_id]

            # Save character if authenticated
            if player_data.get('character') and player_data.get('authenticated'):
                self._save_player_character(player_id, player_data['character'])

            # Clean up
            del self.connected_players[player_id]

    def _handle_player_command(self, player_id: int, command: str, params: str):
        """Handle a command from a player."""
        if player_id not in self.connected_players:
            return

        player_data = self.connected_players[player_id]

        # Handle login process
        if not player_data.get('authenticated'):
            self._handle_login_process(player_id, command, params)
            return

        # Handle game commands
        self._handle_game_command(player_id, command, params)

    def _handle_login_process(self, player_id: int, input_text: str, params: str):
        """Handle the login process for a player."""
        player_data = self.connected_players[player_id]
        login_state = player_data.get('login_state', 'username_prompt')

        if login_state == 'username_prompt':
            # Store username and ask for password
            player_data['username'] = input_text.strip().capitalize()
            player_data['login_state'] = 'password_prompt'
            self.connection_manager.send_message(player_id, "Password: ")

        elif login_state == 'password_prompt':
            # Authenticate user
            username = player_data.get('username', '')
            password = input_text.strip()

            if self._authenticate_player(username, password):
                player_data['authenticated'] = True
                player_data['login_state'] = 'authenticated'
                self.connection_manager.send_message(player_id, f"Welcome back, {username}!")

                # Load character or prompt for character creation
                self._handle_character_selection(player_id, username)
            else:
                self.connection_manager.send_message(player_id, "Invalid credentials. Try again.")
                self.connection_manager.send_message(player_id, "Username: ")
                player_data['login_state'] = 'username_prompt'

    def _handle_character_selection(self, player_id: int, username: str):
        """Handle character selection/creation."""
        # This would load existing characters or prompt for creation
        # For now, create a simple character and put them in the starting room

        from ..game.player.character import Character

        character = Character(f"{username}_char")
        character.room_id = self.world_manager.get_default_starting_room()

        player_data = self.connected_players[player_id]
        player_data['character'] = character

        # Send them to the world
        self.connection_manager.send_message(player_id, "Welcome to the world!")
        self._send_room_description(player_id)

    def _handle_game_command(self, player_id: int, command: str, params: str):
        """Handle a game command from an authenticated player."""
        player_data = self.connected_players.get(player_id)
        if not player_data or not player_data.get('character'):
            return

        # Create a player object for the command manager
        from ..game.player.player import Player

        player = Player(player_data.get('username', f"player_{player_id}"))
        player.character = player_data['character']

        # Get connection for sending messages
        connection = self.connection_manager.get_connection(player_id)
        if connection:
            player.connection = connection

        # Execute command
        result = self.command_manager.execute_command(player, f"{command} {params}".strip())

        if result:
            self.connection_manager.send_message(player_id, result)

    def _authenticate_player(self, username: str, password: str) -> bool:
        """Authenticate a player."""
        if not self.player_storage:
            # For development, allow any credentials
            return True

        player_id = self.player_storage.authenticate_player(username, password)
        return player_id is not None

    def _send_room_description(self, player_id: int):
        """Send the description of the player's current room."""
        player_data = self.connected_players.get(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room = self.world_manager.get_room(character.room_id)

        if room:
            description = room.get_description(character)
            self.connection_manager.send_message(player_id, description)
        else:
            self.connection_manager.send_message(player_id, "You are in a void...")

    def _save_player_character(self, player_id: int, character):
        """Save a player's character."""
        if self.player_storage:
            try:
                # This would need the actual player ID from database
                # For now, just log that we would save
                self.logger.info(f"Would save character for player {player_id}")
            except Exception as e:
                self.logger.error(f"Failed to save character for player {player_id}: {e}")

    def _save_all_players(self):
        """Save all connected players."""
        for player_id, player_data in self.connected_players.items():
            if player_data.get('character') and player_data.get('authenticated'):
                self._save_player_character(player_id, player_data['character'])

    def _on_player_connected(self, data):
        """Event handler for player connection."""
        self.logger.debug(f"Player connected event: {data}")

    def _on_player_disconnected(self, data):
        """Event handler for player disconnection."""
        self.logger.debug(f"Player disconnected event: {data}")

    def _on_player_command(self, data):
        """Event handler for player command."""
        self.logger.debug(f"Player command event: {data}")

    def get_connected_player_count(self) -> int:
        """Get the number of connected players."""
        return len(self.connected_players)

    def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a connected player."""
        return self.connected_players.get(player_id)