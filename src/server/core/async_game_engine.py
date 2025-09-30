"""Async game engine that coordinates all game systems."""

import asyncio
import random
import time
import json
from typing import Optional, Dict, Any

from ..networking.async_connection_manager import AsyncConnectionManager
from ..commands.base_command import CommandManager
from ..game.world.world_manager import WorldManager
from .event_system import EventSystem
from ..commands.command_handler import CommandHandler
from ..game.vendors.vendor_system import VendorSystem
from ..game.combat.combat_system import CombatSystem
from ..game.items.item_manager import ItemManager
from ..game.player.player_manager import PlayerManager
from ..persistence.database import Database
from ..persistence.player_storage import PlayerStorage
from ..config.config_manager import ConfigManager
from ..utils.logger import get_logger
from ..game.npcs.mob import Mob
from shared.constants.game_constants import GAME_TICK_RATE


class AsyncGameEngine:
    """Async game engine that manages all game systems and coordinates updates."""

    def __init__(self):
        """Initialize the game engine."""
        self.logger = get_logger()
        self.running = False
        self.tick_rate = GAME_TICK_RATE

        # Core systems
        self.event_system = EventSystem()
        self.connection_manager = AsyncConnectionManager()
        self.command_manager = CommandManager()
        self.world_manager = WorldManager(self)
        self.config_manager = ConfigManager()
        self.command_handler = CommandHandler(self)
        self.vendor_system = VendorSystem(self)
        self.combat_system = CombatSystem(self)
        self.item_manager = ItemManager(self)
        self.player_manager = PlayerManager(self)

        # Database and persistence
        self.database: Optional[Database] = None
        self.player_storage: Optional[PlayerStorage] = None


        # Room mob management - tracks spawned mobs in each room
        self.room_mobs: Dict[str, list] = {}

        # Combat management - tracks active combat encounters
        self.active_combats: Dict[str, AsyncCombat] = {}  # room_id -> AsyncCombat
        self.player_combats: Dict[int, str] = {}     # player_id -> room_id with active combat
        self.player_fatigue: Dict[int, Dict[str, Any]] = {}  # player_id -> fatigue info
        self.mob_fatigue: Dict[str, Dict[str, Any]] = {}     # mob_id -> fatigue info

        # Note: Vendor management now handled by VendorSystem

        # Background tasks
        self.game_loop_task: Optional[asyncio.Task] = None
        self.last_auto_save = time.time()
        self.auto_save_interval = 60.0  # Auto-save every 60 seconds

        # Setup system connections
        self._setup_connections()

    def _setup_connections(self):
        """Setup connections between systems."""
        # Connect connection manager to game events
        self.connection_manager.on_player_connect = self.player_manager.handle_player_connect
        self.connection_manager.on_player_disconnect = self.player_manager.handle_player_disconnect
        self.connection_manager.on_player_command = self.command_handler.handle_player_command

        # Subscribe to events
        self.event_system.subscribe('player_connected', self.player_manager.on_player_connected)
        self.event_system.subscribe('player_disconnected', self.player_manager.on_player_disconnected)
        self.event_system.subscribe('player_command', self.player_manager.on_player_command)

    def initialize_database(self, database: Database):
        """Initialize database connection."""
        self.database = database
        self.player_storage = PlayerStorage(database)
        self.logger.info("Database initialized")

    async def start(self, host: str = "localhost", port: int = 4000):
        """Start the async game engine."""
        if self.running:
            self.logger.warning("Game engine is already running")
            return

        self.running = True
        self.logger.info("Starting async game engine")

        try:
            # Initialize world
            self.world_manager.load_world()

            # Load vendor and item data
            self.vendor_system.load_vendors_and_items()

            # Start connection manager
            self.connection_manager.initialize(host, port, self.event_system)

            # Start background tasks
            self.game_loop_task = asyncio.create_task(self._game_loop())

            # Start the server (this will run until stopped)
            await self.connection_manager.start_server(host, port)

        except asyncio.CancelledError:
            self.logger.info("Game engine cancelled")
        except Exception as e:
            self.logger.error(f"Game engine error: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the game engine."""
        if not self.running:
            return

        self.logger.info("Stopping async game engine")
        self.running = False

        # Save all player data FIRST (before canceling anything)
        try:
            if self.database and self.database.connection:
                self.logger.info("Saving all players before shutdown...")
                self.player_manager.save_all_players()
                self.logger.info("All players saved")
        except Exception as e:
            self.logger.error(f"Error saving players during shutdown: {e}")

        # Cancel game loop
        if self.game_loop_task:
            self.game_loop_task.cancel()
            try:
                await self.game_loop_task
            except asyncio.CancelledError:
                pass

        # Stop connection manager
        await self.connection_manager.stop_server()

        # Disconnect database
        if self.database:
            try:
                self.database.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting database: {e}")

    async def _game_loop(self):
        """Main async game loop."""
        last_tick = time.time()

        try:
            while self.running:
                current_time = time.time()

                # Check if it's time for a tick
                if current_time - last_tick >= self.tick_rate:
                    await self.tick()
                    last_tick = current_time

                # Sleep to prevent busy waiting
                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            self.logger.info("Game loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in game loop: {e}")

    async def tick(self):
        """Process one async game tick."""
        try:
            # Update world
            await self.world_manager.update_world()

            # Update NPCs, combat, etc.
            await self._update_npcs()
            await self._update_combat()

            # Auto-save check
            current_time = time.time()
            if current_time - self.last_auto_save >= self.auto_save_interval:
                await self._auto_save_players()
                self.last_auto_save = current_time

        except Exception as e:
            self.logger.error(f"Error in game tick: {e}")

    async def _update_npcs(self):
        """Update all NPCs asynchronously."""
        await self.combat_system.process_mob_ai()

    async def _update_combat(self):
        """Update combat encounters asynchronously."""
        # This would handle ongoing combat
        # For now, just a placeholder
        pass

    async def _auto_save_players(self):
        """Auto-save all connected players with characters."""
        try:
            saved_count = 0
            for player_id, player_data in self.player_manager.connected_players.items():
                if player_data.get('character') and player_data.get('authenticated'):
                    self.player_manager.save_player_character(player_id, player_data['character'])
                    saved_count += 1

            if saved_count > 0:
                self.logger.info(f"Auto-saved {saved_count} player(s)")
        except Exception as e:
            self.logger.error(f"Error during auto-save: {e}")



    async def _move_player(self, player_id: int, direction: str):
        """Move a player in a direction - delegates to player_manager."""
        await self.player_manager.move_player(player_id, direction)


    async def _send_room_description(self, player_id: int, detailed: bool = False):
        """Send the description of the player's current room - delegates to world_manager."""
        await self.world_manager.send_room_description(player_id, detailed)

    def _check_npc_hostility(self, npc_id: str) -> bool:
        """Check if an NPC is hostile using preloaded world manager data."""
        return self.world_manager.is_npc_hostile(npc_id)

    async def _notify_room_except_player(self, room_id: str, exclude_player_id: int, message: str):
        """Send a message to all players in a room except the specified player - delegates to player_manager."""
        await self.player_manager.notify_room_except_player(room_id, exclude_player_id, message)



    def get_connected_player_count(self) -> int:
        """Get the number of connected players."""
        return self.player_manager.get_connected_player_count()

    def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a connected player."""
        return self.player_manager.get_player_info(player_id)


    async def _handle_drop_item(self, player_id: int, item_name: str):
        """Handle dropping an item from inventory - delegates to item_manager."""
        await self.item_manager.handle_drop_item(player_id, item_name)

    async def _handle_equip_item(self, player_id: int, item_name: str):
        """Handle equipping an item from inventory - delegates to item_manager."""
        await self.item_manager.handle_equip_item(player_id, item_name)

    async def _handle_unequip_item(self, player_id: int, item_name: str):
        """Handle unequipping an item to inventory - delegates to item_manager."""
        await self.item_manager.handle_unequip_item(player_id, item_name)

    async def _handle_trade_command(self, player_id: int, action: str, item_name: str):
        """Handle buy/sell commands with vendors."""
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Use vendor system to handle trade
        await self.vendor_system.handle_trade_command(player_id, action, item_name)

    async def _handle_ring_command(self, player_id: int, target: str):
        """Handle ring command for special items like gongs."""
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Check if the target matches "gong" or similar variations
        target_lower = target.lower()
        if target_lower in ['gong', 'g', 'bronze gong', 'bronze']:
            # Check if player is in the arena room
            if room_id != 'arena':
                await self.connection_manager.send_message(player_id, "There is no gong here to ring.")
                return

            # Ring the gong and spawn a mob - delegates to world_manager
            await self.world_manager.handle_ring_gong(player_id, room_id)
        else:
            await self.connection_manager.send_message(player_id, f"You cannot ring {target}.")

    async def _handle_list_vendor_items(self, player_id: int):
        """Show vendor inventory."""
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Use vendor system to handle listing
        await self.vendor_system.handle_list_vendor_items(player_id)



    async def _handle_look_at_target(self, player_id: int, target_name: str):
        """Handle looking at specific targets like NPCs and mobs - delegates to world_manager."""
        await self.world_manager.handle_look_at_target(player_id, target_name)








