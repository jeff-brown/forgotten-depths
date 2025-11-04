"""Async-compatible commands for the MUD."""

import asyncio
from typing import List

from .base_command import BaseCommand


class AsyncLookCommand(BaseCommand):
    """Async version of the look command."""

    def __init__(self):
        super().__init__("look", ["l", "examine"])
        self.description = "Look at your surroundings or an object"
        self.usage = "look [target]"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the look command."""
        if not args:
            return self._look_room(player)
        else:
            target = " ".join(args)
            return self._look_at_target(player, target)

    def _look_room(self, player: 'Player') -> str:
        """Look at the current room."""
        if not player.character or not player.character.room_id:
            return "You are in a void..."

        # This would typically get the room from the world manager
        # For now, return a basic description
        return f"You are in {player.character.room_id}. The room appears normal."

    def _look_at_target(self, player: 'Player', target: str) -> str:
        """Look at a specific target."""
        return f"You don't see '{target}' here."


class AsyncSayCommand(BaseCommand):
    """Async version of the say command."""

    def __init__(self):
        super().__init__("say", ["'"])
        self.description = "Say something to players in the room"
        self.usage = "say <message>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the say command."""
        if not args:
            return "What would you like to say?"

        message = " ".join(args)

        # Schedule the async broadcast
        if hasattr(player, 'connection') and hasattr(player.connection, 'connection_manager'):
            # This would broadcast to other players in the room
            # For now, just return a confirmation
            pass

        return f"You say: {message}"


class AsyncHelpCommand(BaseCommand):
    """Async version of the help command."""

    def __init__(self):
        super().__init__("help", ["?", "commands"])
        self.description = "Show available commands"
        self.usage = "help [command]"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the help command."""
        if args:
            command_name = args[0]
            return f"Help for '{command_name}': Not implemented yet."

        # Return basic help
        help_text = """
Available Commands:
===================
look (l)     - Look at your surroundings
say (')      - Say something to other players
help (?)     - Show this help message
quit         - Quit the game
north (n)    - Move north
south (s)    - Move south
east (e)     - Move east
west (w)     - Move west

Vendor Commands:
================
list         - List vendor inventory
buy <item>   - Buy an item from a vendor
sell <item>  - Sell an item to a vendor
value <item> - Check the value of an item

Type 'help <command>' for more information about a specific command.
"""
        return help_text.strip()


class AsyncMoveCommand(BaseCommand):
    """Async version of movement commands."""

    def __init__(self, direction: str, aliases: List[str] = None):
        super().__init__(direction, aliases or [])
        self.direction = direction
        self.description = f"Move {direction}"
        self.usage = direction

    async def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the move command using graph-based navigation."""
        from ...utils.logger import get_logger
        logger = get_logger()

        logger.info(f"[DOOR] AsyncMoveCommand.execute() called for direction '{self.direction}'")

        if not player.character:
            logger.info(f"[DOOR] No character, returning early")
            return "You don't have a character."

        if not player.character.room_id:
            logger.info(f"[DOOR] No room_id, returning early")
            return "You are nowhere, so you can't move anywhere."

        # Check if player is paralyzed (handle both dict and object)
        active_effects = []
        if isinstance(player.character, dict):
            active_effects = player.character.get('active_effects', [])
        elif hasattr(player.character, 'active_effects'):
            active_effects = player.character.active_effects or []

        logger.info(f"[PARALYSIS] Checking paralysis. Character type: {type(player.character)}, active_effects: {active_effects}")

        for effect in active_effects:
            effect_type = effect.get('type') if isinstance(effect, dict) else getattr(effect, 'type', None)
            effect_effect = effect.get('effect') if isinstance(effect, dict) else getattr(effect, 'effect', None)
            logger.info(f"[PARALYSIS] Checking effect: type={effect_type}, effect={effect_effect}")
            if effect_type in ['paralyze', 'paralyzed'] or effect_effect in ['paralyze', 'paralyzed', 'movement_disabled']:
                logger.info(f"[PARALYSIS] BLOCKING MOVEMENT - Player is paralyzed!")
                return "You are paralyzed and cannot move!"

        # Get world manager from game engine
        from server.core.async_game_engine import AsyncGameEngine
        if not hasattr(player, '_game_engine'):
            logger.info(f"[DOOR] No _game_engine, returning early")
            return "Movement system not available."

        world_manager = player._game_engine.world_manager
        current_room = player.character.room_id

        logger.info(f"[DOOR] Current room: '{current_room}'")

        # Get available exits using graph system
        exits = world_manager.get_exits_from_room(current_room, player.character)
        logger.info(f"[DOOR] Available exits from get_exits_from_room: {list(exits.keys())}")

        # Check if the direction exists
        direction_lower = self.direction.lower()
        destination = None

        for exit_dir, room_id in exits.items():
            if exit_dir.lower() == direction_lower:
                destination = room_id
                break

        if not destination:
            # Check for partial matches
            matching_exits = [exit_dir for exit_dir in exits.keys()
                            if exit_dir.lower().startswith(direction_lower)]

            if len(matching_exits) == 1:
                destination = exits[matching_exits[0]]
                direction_lower = matching_exits[0].lower()
            elif len(matching_exits) > 1:
                return f"Ambiguous direction '{self.direction}'. Could be: {', '.join(matching_exits)}"
            else:
                available = ', '.join(exits.keys()) if exits else 'none'
                return f"There's no exit {self.direction}. Available exits: {available}"

        # Get the matched direction for lock checking
        matched_direction = None
        for exit_dir in exits.keys():
            if exit_dir.lower() == direction_lower:
                matched_direction = exit_dir
                break

        # Check if the exit is locked
        old_room = world_manager.get_room(current_room)
        unlock_message = None

        from ...utils.logger import get_logger
        logger = get_logger()

        logger.info(f"[DOOR] === MOVEMENT CHECK START ===")
        logger.info(f"[DOOR] Player attempting to go '{self.direction}' (matched: '{matched_direction}') from room '{current_room}' to '{destination}'")
        logger.info(f"[DOOR] old_room exists: {old_room is not None}, matched_direction: '{matched_direction}'")

        if old_room and matched_direction:
            logger.info(f"[DOOR] Room '{current_room}' locked_exits: {list(old_room.locked_exits.keys())}")
            logger.info(f"[DOOR] Checking if exit '{matched_direction}' is locked")

            if old_room.is_exit_locked(matched_direction):
                required_key = old_room.get_required_key(matched_direction)
                lock_desc = old_room.locked_exits[matched_direction].get('description', 'The way is locked.')

                logger.info(f"[DOOR] Exit '{matched_direction}' IS LOCKED, required key: '{required_key}'")

                # Check if player has the required key
                has_key = False
                logger.info(f"[DOOR] Player character type: {type(player.character)}")
                logger.info(f"[DOOR] Has inventory attr: {hasattr(player.character, 'inventory')}")

                if hasattr(player.character, 'inventory'):
                    logger.info(f"[DOOR] Raw inventory: {player.character.inventory}")
                    inventory_ids = [item.get('id') for item in player.character.inventory]
                    logger.info(f"[DOOR] Extracted inventory IDs: {inventory_ids}")
                    has_key = required_key in inventory_ids
                    logger.info(f"[DOOR] Has required key '{required_key}': {has_key}")
                else:
                    # Try accessing as dict
                    if isinstance(player.character, dict):
                        inv = player.character.get('inventory', [])
                        logger.info(f"[DOOR] Character is dict, inventory: {inv}")
                        inventory_ids = [item.get('id') if isinstance(item, dict) else item for item in inv]
                        logger.info(f"[DOOR] Extracted inventory IDs: {inventory_ids}")
                        has_key = required_key in inventory_ids
                        logger.info(f"[DOOR] Has required key '{required_key}': {has_key}")

                if not has_key:
                    logger.info(f"[DOOR] Player does NOT have key, blocking movement")
                    return f"{lock_desc} You need a {required_key.replace('_', ' ')} to unlock it."

                # Player has the key - unlock the door and continue movement
                logger.info(f"[DOOR] Player HAS key, unlocking exit '{matched_direction}'")
                old_room.unlock_exit(matched_direction)
                logger.info(f"[DOOR] Exit unlocked, locked_exits now: {list(old_room.locked_exits.keys())}")
                unlock_message = f"You use your {required_key.replace('_', ' ')} to unlock the door.\n"
            else:
                logger.info(f"[DOOR] Exit '{matched_direction}' is NOT locked, allowing movement")

        # Check if player can actually travel there
        if not world_manager.can_travel(current_room, destination, player.character):
            return f"You cannot go {self.direction} right now."

        # Move the player
        if not old_room:
            old_room = world_manager.get_room(current_room)
        new_room = world_manager.get_room(destination)

        if not new_room:
            return f"Error: Destination room {destination} not found."

        # Update player location
        if old_room:
            old_room.remove_player(player.character)

        player.character.room_id = destination
        new_room.add_player(player.character)

        # Check if any wandering mobs should follow the player
        await self._check_mob_following(player, current_room, destination, matched_direction)

        # Return the new room description
        result = ""
        if unlock_message:
            result += unlock_message
        result += f"You go {self.direction}.\n\n"
        result += new_room.get_description(player.character)

        logger.info(f"[DOOR] === MOVEMENT CHECK END (SUCCESS) ===")
        return result

    async def _check_mob_following(self, player: 'Player', old_room_id: str, new_room_id: str, direction: str):
        """Check if any wandering mobs should follow the player.

        Args:
            player: The player who just moved
            old_room_id: The room the player left
            new_room_id: The room the player entered
            direction: The direction the player moved
        """
        import random
        from ...utils.logger import get_logger
        logger = get_logger()

        # Get game engine
        if not hasattr(player, '_game_engine'):
            return

        game_engine = player._game_engine

        # Get follow chance from config
        follow_chance = game_engine.config_manager.get_setting('combat', 'mob_follow', 'follow_chance', default=0.4)

        logger.info(f"[FOLLOW] Checking mob following from {old_room_id} to {new_room_id}, follow_chance={follow_chance}")

        # Check if there are any wandering mobs in the old room
        if old_room_id not in game_engine.room_mobs:
            logger.debug(f"[FOLLOW] No mobs in room {old_room_id}")
            return

        logger.info(f"[FOLLOW] Found {len(game_engine.room_mobs[old_room_id])} mobs in old room")

        mobs_to_follow = []

        for mob in game_engine.room_mobs[old_room_id][:]:  # Copy to avoid modification during iteration
            # Only wandering mobs can follow
            if not mob.get('is_wandering'):
                logger.debug(f"[FOLLOW] {mob.get('name')} is not a wandering mob")
                continue

            # Skip if mob is dead
            if mob.get('health', 0) <= 0:
                continue

            # Roll for follow chance
            if random.random() >= follow_chance:
                continue

            # Get the exit from old room
            old_room = game_engine.world_manager.get_room(old_room_id)
            if not old_room:
                continue

            # Check if mob can follow through this exit
            exit_obj = old_room.exits.get(direction)
            if not exit_obj:
                continue

            # Check if exit is locked
            if hasattr(exit_obj, 'is_locked') and exit_obj.is_locked:
                logger.debug(f"[FOLLOW] {mob.get('name')} cannot follow - exit is locked")
                continue

            # Check if destination is a safe room
            dest_room = game_engine.world_manager.get_room(new_room_id)
            if dest_room and hasattr(dest_room, 'is_safe') and dest_room.is_safe:
                logger.debug(f"[FOLLOW] {mob.get('name')} cannot follow - destination is a safe room")
                continue

            # This mob will follow
            mobs_to_follow.append(mob)

        # Move the mobs that are following
        for mob in mobs_to_follow:
            mob_name = mob.get('name', 'Unknown creature')

            # Remove from old room
            if old_room_id in game_engine.room_mobs:
                game_engine.room_mobs[old_room_id] = [m for m in game_engine.room_mobs[old_room_id] if m != mob]

            # Add to new room
            if new_room_id not in game_engine.room_mobs:
                game_engine.room_mobs[new_room_id] = []
            game_engine.room_mobs[new_room_id].append(mob)

            # Notify players in old room
            for player_id, player_data in game_engine.player_manager.connected_players.items():
                if player_data.get('character', {}).get('room_id') == old_room_id:
                    await game_engine.connection_manager.send_message(
                        player_id,
                        f"{mob_name} follows {direction}."
                    )

            # Notify players in new room (including the player who moved)
            for player_id, player_data in game_engine.player_manager.connected_players.items():
                if player_data.get('character', {}).get('room_id') == new_room_id:
                    await game_engine.connection_manager.send_message(
                        player_id,
                        f"{mob_name} follows you into the room!"
                    )

            logger.info(f"[FOLLOW] {mob_name} followed player from {old_room_id} to {new_room_id} via {direction}")


# Factory function to create movement commands
def create_movement_commands():
    """Create all movement commands."""
    return [
        AsyncMoveCommand("north", ["n"]),
        AsyncMoveCommand("south", ["s"]),
        AsyncMoveCommand("east", ["e"]),
        AsyncMoveCommand("west", ["w"]),
        AsyncMoveCommand("northeast", ["ne"]),
        AsyncMoveCommand("northwest", ["nw"]),
        AsyncMoveCommand("southeast", ["se"]),
        AsyncMoveCommand("southwest", ["sw"]),
        AsyncMoveCommand("up", ["u"]),
        AsyncMoveCommand("down", ["d"])
    ]


def get_default_async_commands():
    """Get the default set of async commands."""
    commands = [
        AsyncLookCommand(),
        AsyncSayCommand(),
        AsyncHelpCommand()
    ]

    # Add movement commands
    commands.extend(create_movement_commands())

    # Add navigation commands
    try:
        from .navigation_commands import get_navigation_commands
        commands.extend(get_navigation_commands())
    except ImportError:
        pass  # Navigation commands not available

    # Add vendor commands
    try:
        from .vendor.vendor_commands import get_vendor_commands
        commands.extend(get_vendor_commands())
    except ImportError:
        pass  # Vendor commands not available

    return commands