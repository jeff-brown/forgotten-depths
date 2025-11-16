"""Asyncio-based telnet server for MUD connections."""

import asyncio
import time
from typing import Optional, Callable, Dict, Any, List

from ..utils.logger import get_logger
from ..core.event_system import EventSystem
from shared.constants.game_constants import WELCOME_MESSAGE, GOODBYE_MESSAGE


class AsyncTelnetConnection:
    """Represents an async telnet connection."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 connection_id: int, server: 'AsyncTelnetServer'):
        self.reader = reader
        self.writer = writer
        self.connection_id = connection_id
        self.server = server
        self.connected = True
        self.buffer = ""
        self.last_activity = time.time()

        # Telnet protocol state
        self._read_state = 1  # NORMAL

        # Get client address
        peername = writer.get_extra_info('peername')
        self.address = peername[0] if peername else "unknown"

    async def send_message(self, message: str, add_newline: bool = True, flush: bool = False):
        """Send a message to the client.

        Args:
            message: The message to send
            add_newline: Whether to add newline/carriage return
            flush: Whether to immediately drain the write buffer (default False for batching)
        """
        if not self.connected:
            return

        try:
            # Ensure message ends with newline and carriage return
            if add_newline and not message.endswith('\n'):
                message += '\n\r'

            self.writer.write(message.encode('latin1'))

            # Only drain if explicitly requested - allows batching multiple messages
            if flush:
                await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            self.server.logger.debug(f"Send error to {self.connection_id}: {e}")
            await self.disconnect()

    async def flush(self):
        """Flush the write buffer to the network."""
        if not self.connected:
            return

        try:
            # Check write buffer size before draining
            buffer_size = self.writer.transport.get_write_buffer_size() if self.writer.transport else 0
            if buffer_size > 1000:
                self.server.logger.warning(f"[BUFFER] Large write buffer for connection {self.connection_id}: {buffer_size} bytes")

            await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            self.server.logger.debug(f"Flush error to {self.connection_id}: {e}")
            await self.disconnect()

    async def disconnect(self):
        """Disconnect the client."""
        if not self.connected:
            return

        self.connected = False
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass

    async def read_loop(self):
        """Main read loop for this connection."""
        try:
            while self.connected:
                # Read data with timeout
                try:
                    data = await asyncio.wait_for(
                        self.reader.read(4096),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue

                if not data:
                    # Client disconnected
                    break

                # Process the received data
                try:
                    decoded_data = data.decode('latin1')
                    message = self._process_telnet_data(decoded_data)

                    if message is not None:  # Allow empty messages (Enter key)
                        self.last_activity = time.time()
                        # Parse command and parameters
                        parts = message.strip().split(' ', 1) if message.strip() else ["", ""]
                        command = parts[0].lower() if parts[0] else ""
                        params = parts[1] if len(parts) > 1 else ""

                        # Notify server of command (including empty commands for UI reload)
                        await self.server._handle_command(self.connection_id, command, params)

                except UnicodeDecodeError:
                    # Skip invalid data
                    continue

        except Exception as e:
            self.server.logger.error(f"Error in read loop for {self.connection_id}: {e}")
        finally:
            await self.disconnect()
            await self.server._handle_disconnect(self.connection_id)

    def _process_telnet_data(self, data: str) -> Optional[str]:
        """Process telnet data and handle protocol commands."""
        # Telnet protocol constants
        TN_INTERPRET_AS_COMMAND = 255
        TN_SUBNEGOTIATION_START = 250
        TN_SUBNEGOTIATION_END = 240
        TN_WILL = 251
        TN_WONT = 252
        TN_DO = 253
        TN_DONT = 254

        READ_STATE_NORMAL = 1
        READ_STATE_COMMAND = 2
        READ_STATE_SUBNEG = 3

        message = None
        state = READ_STATE_NORMAL

        for char in data:
            if state == READ_STATE_NORMAL:
                if ord(char) == TN_INTERPRET_AS_COMMAND:
                    state = READ_STATE_COMMAND
                elif char == '\n':
                    message = self.buffer
                    self.buffer = ""
                elif char == '\x08':  # Backspace
                    self.buffer = self.buffer[:-1]
                elif char != '\r':  # Ignore carriage returns
                    self.buffer += char

            elif state == READ_STATE_COMMAND:
                if ord(char) == TN_SUBNEGOTIATION_START:
                    state = READ_STATE_SUBNEG
                elif ord(char) in (TN_WILL, TN_WONT, TN_DO, TN_DONT):
                    state = READ_STATE_COMMAND  # Expect one more byte
                else:
                    state = READ_STATE_NORMAL

            elif state == READ_STATE_SUBNEG:
                if ord(char) == TN_SUBNEGOTIATION_END:
                    state = READ_STATE_NORMAL

        return message


class AsyncTelnetServer:
    """Asyncio-based telnet server for MUD connections."""

    def __init__(self, host: str = "localhost", port: int = 4000):
        self.host = host
        self.port = port
        self.logger = get_logger()

        # Connection management
        self.connections: Dict[int, AsyncTelnetConnection] = {}
        self.next_id = 0
        self.server: Optional[asyncio.Server] = None
        self.running = False

        # Event system integration
        self.event_system: Optional[EventSystem] = None

        # Callbacks
        self.on_player_connect: Optional[Callable[[int], None]] = None
        self.on_player_disconnect: Optional[Callable[[int], None]] = None
        self.on_player_command: Optional[Callable[[int, str, str], None]] = None

        # Player session data
        self.player_sessions: Dict[int, Dict[str, Any]] = {}

    def set_event_system(self, event_system: EventSystem):
        """Set the event system for publishing events."""
        self.event_system = event_system

    async def start(self):
        """Start the asyncio telnet server."""
        if self.running:
            self.logger.warning("Server is already running")
            return

        self.running = True
        self.logger.info(f"Starting async telnet server on {self.host}:{self.port}")

        try:
            # Start the server
            self.server = await asyncio.start_server(
                self._handle_new_connection,
                self.host,
                self.port
            )

            self.logger.info(f"Server started on {self.host}:{self.port}")

            # Start background tasks
            asyncio.create_task(self._cleanup_task())

            # Serve until stopped
            async with self.server:
                await self.server.serve_forever()

        except asyncio.CancelledError:
            self.logger.info("Server cancelled")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the server."""
        if not self.running:
            return

        self.logger.info("Stopping async telnet server")
        self.running = False

        # Disconnect all clients
        disconnect_tasks = []
        for connection in list(self.connections.values()):
            disconnect_tasks.append(connection.disconnect())

        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        self.connections.clear()
        self.player_sessions.clear()

    async def _handle_new_connection(self, reader: asyncio.StreamReader,
                                   writer: asyncio.StreamWriter):
        """Handle a new client connection."""
        connection_id = self.next_id
        self.next_id += 1

        # Disable Nagle's algorithm for low-latency interactive gameplay
        # Without this, TCP buffers small packets causing 40-200ms delays
        sock = writer.get_extra_info('socket')
        if sock:
            import socket
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        connection = AsyncTelnetConnection(reader, writer, connection_id, self)
        self.connections[connection_id] = connection

        # Initialize session
        self.player_sessions[connection_id] = {
            'connected_at': time.time(),
            'authenticated': False,
            'character': None,
            'last_activity': time.time()
        }

        self.logger.info(f"New connection {connection_id} from {connection.address}")

        # Don't send welcome here - let the game engine handle it

        # Notify callbacks
        if self.on_player_connect:
            self.on_player_connect(connection_id)

        # Publish event
        if self.event_system:
            self.event_system.publish('player_connected', {'player_id': connection_id})

        # Start read loop for this connection
        asyncio.create_task(connection.read_loop())

    async def _handle_disconnect(self, connection_id: int):
        """Handle client disconnection."""
        if connection_id not in self.connections:
            return

        self.logger.info(f"Player {connection_id} disconnected")

        # Get session data
        session = self.player_sessions.get(connection_id, {})

        # Clean up
        if connection_id in self.connections:
            del self.connections[connection_id]
        if connection_id in self.player_sessions:
            del self.player_sessions[connection_id]

        # Notify callbacks
        if self.on_player_disconnect:
            self.on_player_disconnect(connection_id)

        # Publish event
        if self.event_system:
            self.event_system.publish('player_disconnected', {
                'player_id': connection_id,
                'session_duration': time.time() - session.get('connected_at', time.time())
            })

    async def _handle_command(self, connection_id: int, command: str, params: str):
        """Handle a command from a player."""
        if connection_id not in self.player_sessions:
            return

        # Update last activity
        self.player_sessions[connection_id]['last_activity'] = time.time()

        self.logger.debug(f"Player {connection_id} command: {command} {params}")

        # Handle quit specially
        if command in ['quit', 'exit', 'logout']:
            connection = self.connections.get(connection_id)
            if connection:
                await connection.send_message(GOODBYE_MESSAGE)
                await connection.disconnect()
            return

        # Notify callbacks
        if self.on_player_command:
            self.on_player_command(connection_id, command, params)

        # Publish event
        if self.event_system:
            self.event_system.publish('player_command', {
                'player_id': connection_id,
                'command': command,
                'params': params,
                'timestamp': time.time()
            })

    async def send_message(self, player_id: int, message: str, add_newline: bool = True):
        """Send a message to a specific player."""
        connection = self.connections.get(player_id)
        if connection:
            await connection.send_message(message, add_newline)

    async def broadcast_message(self, message: str, exclude_player: Optional[int] = None):
        """Send a message to all connected players."""
        tasks = []
        for player_id, connection in self.connections.items():
            if exclude_player is None or player_id != exclude_player:
                tasks.append(connection.send_message(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_message_to_room(self, message: str, room_id: str,
                                 exclude_player: Optional[int] = None):
        """Send a message to all players in a specific room."""
        tasks = []
        for player_id, session in self.player_sessions.items():
            character = session.get('character')
            if character and getattr(character, 'room_id', None) == room_id:
                if exclude_player is None or player_id != exclude_player:
                    connection = self.connections.get(player_id)
                    if connection:
                        tasks.append(connection.send_message(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def disconnect_player(self, player_id: int, message: Optional[str] = None):
        """Gracefully disconnect a player."""
        connection = self.connections.get(player_id)
        if connection:
            if message:
                await connection.send_message(message)
            await connection.disconnect()

    async def _cleanup_task(self):
        """Background task for cleanup operations."""
        while self.running:
            try:
                current_time = time.time()

                # Check for idle connections (optional)
                idle_timeout = 1800  # 30 minutes
                for player_id, session in list(self.player_sessions.items()):
                    if current_time - session.get('last_activity', current_time) > idle_timeout:
                        self.logger.info(f"Disconnecting idle player {player_id}")
                        await self.disconnect_player(player_id, "Disconnected due to inactivity.")

                # Sleep for cleanup interval
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    # Synchronous interface methods for compatibility
    def get_connected_players(self) -> List[int]:
        """Get list of all connected player IDs."""
        return list(self.connections.keys())

    def get_player_session(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get session data for a player."""
        return self.player_sessions.get(player_id)

    def update_player_session(self, player_id: int, **kwargs):
        """Update session data for a player."""
        if player_id in self.player_sessions:
            self.player_sessions[player_id].update(kwargs)

    def get_player_count(self) -> int:
        """Get the number of connected players."""
        return len(self.connections)

    def is_player_connected(self, player_id: int) -> bool:
        """Check if a player is currently connected."""
        return player_id in self.connections and self.connections[player_id].connected