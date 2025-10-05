"""Telnet server implementation for MUD connections using the existing mud.py."""

import socket
import threading
import time
from typing import Optional, Callable, Dict, Any, List

from .mud import Mud
from ..utils.logger import get_logger
from ..core.event_system import EventSystem
from ...shared.constants.game_constants import WELCOME_MESSAGE, GOODBYE_MESSAGE


class TelnetServer:
    """Enhanced telnet server that integrates the existing Mud class with our architecture."""

    def __init__(self, host: str = "localhost", port: int = 4000):
        """Initialize the telnet server."""
        self.host = host
        self.port = port
        self.running = False
        self.logger = get_logger()

        # Create the underlying mud server
        self.mud = Mud()
        self._reconfigure_mud_socket()

        # Event system for integration
        self.event_system: Optional[EventSystem] = None

        # Callbacks for game events
        self.on_player_connect: Optional[Callable[[int], None]] = None
        self.on_player_disconnect: Optional[Callable[[int], None]] = None
        self.on_player_command: Optional[Callable[[int, str, str], None]] = None

        # Player session data
        self.player_sessions: Dict[int, Dict[str, Any]] = {}

    def _reconfigure_mud_socket(self):
        """Reconfigure the mud server to use our host and port."""
        # Close the default socket
        if self.mud._listen_socket:
            self.mud._listen_socket.close()

        # Create new socket with our configuration
        self.mud._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mud._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mud._listen_socket.bind((self.host, self.port))
        self.mud._listen_socket.setblocking(False)
        self.mud._listen_socket.listen(5)

        self.logger.info(f"Configured MUD server for {self.host}:{self.port}")

    def set_event_system(self, event_system: EventSystem):
        """Set the event system for publishing game events."""
        self.event_system = event_system

    def start(self):
        """Start the telnet server."""
        if self.running:
            self.logger.warning("Server is already running")
            return

        self.running = True
        self.logger.info(f"Starting telnet server on {self.host}:{self.port}")

        # Send welcome message to new players
        self._send_welcome_to_new_players()

        # Main server loop
        try:
            while self.running:
                self.mud.update()

                # Handle new players
                self._handle_new_players()

                # Handle disconnected players
                self._handle_disconnected_players()

                # Handle player commands
                self._handle_player_commands()

                # Small sleep to prevent busy waiting
                time.sleep(0.01)

        except KeyboardInterrupt:
            self.logger.info("Server interrupted by user")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the telnet server."""
        if not self.running:
            return

        self.logger.info("Stopping telnet server")
        self.running = False

        # Send goodbye message to all connected players
        for player_id in list(self.player_sessions.keys()):
            self.send_message(player_id, GOODBYE_MESSAGE)

        # Shutdown the mud server
        self.mud.shutdown()

    def _handle_new_players(self):
        """Handle newly connected players."""
        new_players = self.mud.get_new_players()

        for player_id in new_players:
            self.logger.info(f"New player connected: {player_id}")

            # Initialize player session
            self.player_sessions[player_id] = {
                'connected_at': time.time(),
                'authenticated': False,
                'character': None,
                'last_activity': time.time()
            }

            # Send welcome message
            self.send_message(player_id, WELCOME_MESSAGE)
            self.send_message(player_id, "Please enter your username:")

            # Notify game system
            if self.on_player_connect:
                self.on_player_connect(player_id)

            # Publish event
            if self.event_system:
                self.event_system.publish('player_connected', {'player_id': player_id})

    def _handle_disconnected_players(self):
        """Handle disconnected players."""
        disconnected_players = self.mud.get_disconnected_players()

        for player_id in disconnected_players:
            self.logger.info(f"Player disconnected: {player_id}")

            # Clean up session data
            if player_id in self.player_sessions:
                session = self.player_sessions[player_id]
                del self.player_sessions[player_id]

                # Notify game system
                if self.on_player_disconnect:
                    self.on_player_disconnect(player_id)

                # Publish event
                if self.event_system:
                    self.event_system.publish('player_disconnected', {
                        'player_id': player_id,
                        'session_duration': time.time() - session.get('connected_at', time.time())
                    })

    def _handle_player_commands(self):
        """Handle commands from players."""
        commands = self.mud.get_commands()

        for player_id, command, params in commands:
            if player_id not in self.player_sessions:
                continue

            # Update last activity
            self.player_sessions[player_id]['last_activity'] = time.time()

            self.logger.debug(f"Player {player_id} command: {command} {params}")

            # Handle quit command specially
            if command.lower() in ['quit', 'exit', 'logout']:
                self.send_message(player_id, GOODBYE_MESSAGE)
                self.mud.get_disconnect(player_id)
                continue

            # Notify game system
            if self.on_player_command:
                self.on_player_command(player_id, command, params)

            # Publish event
            if self.event_system:
                self.event_system.publish('player_command', {
                    'player_id': player_id,
                    'command': command,
                    'params': params,
                    'timestamp': time.time()
                })

    def send_message(self, player_id: int, message: str):
        """Send a message to a specific player."""
        try:
            self.mud.send_message(player_id, message)
        except Exception as e:
            self.logger.error(f"Failed to send message to player {player_id}: {e}")

    def broadcast_message(self, message: str, exclude_player: Optional[int] = None):
        """Send a message to all connected players."""
        for player_id in self.player_sessions:
            if exclude_player is None or player_id != exclude_player:
                self.send_message(player_id, message)

    def send_message_to_room(self, message: str, room_id: str, exclude_player: Optional[int] = None):
        """Send a message to all players in a specific room."""
        for player_id, session in self.player_sessions.items():
            character = session.get('character')
            if character and getattr(character, 'room_id', None) == room_id:
                if exclude_player is None or player_id != exclude_player:
                    self.send_message(player_id, message)

    def get_connected_players(self) -> List[int]:
        """Get list of all connected player IDs."""
        return list(self.player_sessions.keys())

    def get_player_session(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get session data for a player."""
        return self.player_sessions.get(player_id)

    def update_player_session(self, player_id: int, **kwargs):
        """Update session data for a player."""
        if player_id in self.player_sessions:
            self.player_sessions[player_id].update(kwargs)

    def disconnect_player(self, player_id: int, message: Optional[str] = None):
        """Gracefully disconnect a player."""
        if message:
            self.send_message(player_id, message)
        self.mud.get_disconnect(player_id)

    def _send_welcome_to_new_players(self):
        """Send welcome message format - can be customized."""
        pass

    def get_player_count(self) -> int:
        """Get the number of connected players."""
        return len(self.player_sessions)

    def is_player_connected(self, player_id: int) -> bool:
        """Check if a player is currently connected."""
        return player_id in self.player_sessions