"""Async connection manager for the MUD server."""

import asyncio
from typing import Dict, List, Optional, Callable

from .async_telnet_server import AsyncTelnetServer
from ..utils.logger import get_logger
from ..core.event_system import EventSystem


class AsyncConnection:
    """Represents an async client connection."""

    def __init__(self, player_id: int, telnet_server: AsyncTelnetServer):
        """Initialize a connection."""
        self.player_id = player_id
        self.telnet_server = telnet_server
        self.connected = True
        self.player = None
        self.character = None

    async def send(self, message: str):
        """Send a message to the client."""
        if self.connected:
            await self.telnet_server.send_message(self.player_id, message)

    async def disconnect(self):
        """Disconnect the client."""
        if self.connected:
            await self.telnet_server.disconnect_player(self.player_id)
            self.connected = False

    def is_connected(self) -> bool:
        """Check if the connection is still active."""
        return self.connected and self.telnet_server.is_player_connected(self.player_id)


class AsyncConnectionManager:
    """Async connection manager using the async telnet server."""

    def __init__(self):
        """Initialize the connection manager."""
        self.telnet_server: Optional[AsyncTelnetServer] = None
        self.connections: Dict[int, AsyncConnection] = {}
        self.logger = get_logger()
        self.running = False

        # Callbacks for higher-level game systems
        self.on_player_connect: Optional[Callable[[int], None]] = None
        self.on_player_disconnect: Optional[Callable[[int], None]] = None
        self.on_player_command: Optional[Callable[[int, str, str], None]] = None

    def initialize(self, host: str = "localhost", port: int = 4000,
                  event_system: Optional[EventSystem] = None):
        """Initialize the telnet server."""
        self.telnet_server = AsyncTelnetServer(host, port)

        if event_system:
            self.telnet_server.set_event_system(event_system)

        # Set up callbacks
        self.telnet_server.on_player_connect = self._handle_player_connect
        self.telnet_server.on_player_disconnect = self._handle_player_disconnect
        self.telnet_server.on_player_command = self._handle_player_command

        self.logger.info(f"Async connection manager initialized for {host}:{port}")

    async def start_server(self, host: str = "localhost", port: int = 4000):
        """Start the async server."""
        if not self.telnet_server:
            self.initialize(host, port)

        if self.running:
            self.logger.warning("Server is already running")
            return

        self.running = True
        self.logger.info("Starting async connection manager")

        # Start the telnet server
        await self.telnet_server.start()

    async def stop_server(self):
        """Stop the server."""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping async connection manager")

        if self.telnet_server:
            await self.telnet_server.stop()

        # Clear all connections
        self.connections.clear()

    def _handle_player_connect(self, player_id: int):
        """Handle a new player connection."""
        connection = AsyncConnection(player_id, self.telnet_server)
        self.connections[player_id] = connection

        self.logger.info(f"New async connection established: player {player_id}")

        # Notify higher-level systems
        if self.on_player_connect:
            self.on_player_connect(player_id)

    def _handle_player_disconnect(self, player_id: int):
        """Handle a player disconnection."""
        if player_id in self.connections:
            connection = self.connections[player_id]
            connection.connected = False
            del self.connections[player_id]

            self.logger.info(f"Async connection closed: player {player_id}")

            # Notify higher-level systems
            if self.on_player_disconnect:
                # Create a task to handle the async disconnect
                asyncio.create_task(self.on_player_disconnect(player_id))

    def _handle_player_command(self, player_id: int, command: str, params: str):
        """Handle a command from a player."""
        # Notify higher-level systems
        if self.on_player_command:
            # Create a task to handle the async command
            asyncio.create_task(self.on_player_command(player_id, command, params))

    def get_connection(self, player_id: int) -> Optional[AsyncConnection]:
        """Get a connection by player ID."""
        return self.connections.get(player_id)

    async def remove_connection(self, player_id: int):
        """Remove a connection."""
        if player_id in self.connections:
            connection = self.connections[player_id]
            await connection.disconnect()

    async def send_message(self, player_id: int, message: str, add_newline: bool = True):
        """Send a message to a specific player."""
        connection = self.get_connection(player_id)
        if connection:
            # Pass through to telnet server
            await self.telnet_server.send_message(player_id, message, add_newline)
        else:
            self.logger.warning(f"Attempted to send message to non-existent player {player_id}")

    async def broadcast(self, message: str, exclude_player: Optional[int] = None):
        """Send a message to all connected clients."""
        if self.telnet_server:
            await self.telnet_server.broadcast_message(message, exclude_player)

    async def broadcast_to_room(self, message: str, room_id: str,
                              exclude_player: Optional[int] = None):
        """Send a message to all players in a specific room."""
        if self.telnet_server:
            await self.telnet_server.send_message_to_room(message, room_id, exclude_player)

    # Synchronous interface methods for compatibility
    def get_connected_players(self) -> List[int]:
        """Get list of all connected player IDs."""
        return list(self.connections.keys())

    def get_player_count(self) -> int:
        """Get the number of connected players."""
        return len(self.connections)

    def is_player_connected(self, player_id: int) -> bool:
        """Check if a player is currently connected."""
        connection = self.get_connection(player_id)
        return connection is not None and connection.is_connected()

    def get_player_session(self, player_id: int) -> Optional[Dict]:
        """Get session data for a player."""
        if self.telnet_server:
            return self.telnet_server.get_player_session(player_id)
        return None

    def update_player_session(self, player_id: int, **kwargs):
        """Update session data for a player."""
        if self.telnet_server:
            self.telnet_server.update_player_session(player_id, **kwargs)