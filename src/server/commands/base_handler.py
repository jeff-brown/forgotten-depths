"""Base handler class for command modules."""

from typing import Optional, Dict, Any


class BaseCommandHandler:
    """Base class for all command handler modules.

    Provides access to common game systems and utilities.
    """

    def __init__(self, game_engine):
        """Initialize the base handler.

        Args:
            game_engine: The AsyncGameEngine instance
        """
        self.game_engine = game_engine
        self.logger = game_engine.logger

    # Convenience properties for accessing game systems
    @property
    def connection_manager(self):
        """Access to the connection manager."""
        return self.game_engine.connection_manager

    @property
    def player_manager(self):
        """Access to the player manager."""
        return self.game_engine.player_manager

    @property
    def world_manager(self):
        """Access to the world manager."""
        return self.game_engine.world_manager

    @property
    def combat_system(self):
        """Access to the combat system."""
        return self.game_engine.combat_system

    @property
    def vendor_system(self):
        """Access to the vendor system."""
        return self.game_engine.vendor_system

    @property
    def item_manager(self):
        """Access to the item manager."""
        return self.game_engine.item_manager

    @property
    def quest_manager(self):
        """Access to the quest manager."""
        return self.game_engine.quest_manager

    @property
    def config_manager(self):
        """Access to the config manager."""
        return self.game_engine.config_manager

    # Helper methods for common operations
    def get_player_data(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player data by player ID."""
        return self.player_manager.get_player_data(player_id)

    def get_character(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get character data for a player."""
        player_data = self.get_player_data(player_id)
        if player_data:
            return player_data.get('character')
        return None

    async def send_message(self, player_id: int, message: str):
        """Send a message to a player."""
        await self.connection_manager.send_message(player_id, message)

    async def broadcast_to_room(self, room_id: str, message: str, exclude_player: Optional[int] = None):
        """Broadcast a message to all players in a room."""
        await self.connection_manager.broadcast_to_room(room_id, message, exclude_player)
