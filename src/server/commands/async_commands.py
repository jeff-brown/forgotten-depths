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

    def execute(self, player: 'Player', args: List[str]) -> str:
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

        # Return the new room description
        result = ""
        if unlock_message:
            result += unlock_message
        result += f"You go {self.direction}.\n\n"
        result += new_room.get_description(player.character)

        logger.info(f"[DOOR] === MOVEMENT CHECK END (SUCCESS) ===")
        return result


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