"""
Combat Command Handler

Handles commands for combat:
- attack - Attack a target
- shoot/fire - Ranged combat (same room or cross-room)
- flee - Flee from combat
- retrieve - Retrieve spent ammunition
"""

from ..base_handler import BaseCommandHandler


class CombatCommandHandler(BaseCommandHandler):
    """Handler for combat commands."""

    async def handle_attack_command(self, player_id: int, target_name: str):
        """Handle attack command."""
        await self.game_engine.combat_system.handle_attack_command(player_id, target_name)

    async def handle_shoot_command(self, player_id: int, params: str):
        """Handle shoot/fire command for ranged weapons.

        Supports:
        - shoot <target> - shoot target in current room
        - shoot <target> <direction> - shoot target in adjacent room
        - shoot <direction> <target> - alternate syntax for cross-room
        """
        if not params:
            await self.game_engine.connection_manager.send_message(player_id, "Shoot what?")
            return

        # Parse params to check for direction
        parts = params.strip().split()
        directions = ['north', 'n', 'south', 's', 'east', 'e', 'west', 'w',
                     'northeast', 'ne', 'northwest', 'nw', 'southeast', 'se',
                     'southwest', 'sw', 'up', 'u', 'down', 'd']

        target_name = None
        direction = None

        # Check for "shoot <direction> <target>" format
        if parts[0].lower() in directions:
            direction = parts[0].lower()
            target_name = " ".join(parts[1:]) if len(parts) > 1 else None
        # Check for "shoot <target> <direction>" format
        elif len(parts) > 1 and parts[-1].lower() in directions:
            direction = parts[-1].lower()
            target_name = " ".join(parts[:-1])
        # Just "shoot <target>" (same room)
        else:
            target_name = params

        if direction:
            # Cross-room shooting
            await self.game_engine.combat_system.handle_shoot_command_cross_room(
                player_id, target_name, direction
            )
        else:
            # Same-room shooting
            await self.game_engine.combat_system.handle_shoot_command(player_id, target_name)

    async def handle_flee_command(self, player_id: int):
        """Handle flee command."""
        await self.game_engine.combat_system.handle_flee_command(player_id)

    async def handle_retrieve_ammo(self, player_id: int):
        """Handle retrieving spent ammunition from the current room."""
        await self.game_engine.combat_system.handle_retrieve_ammo(player_id)
