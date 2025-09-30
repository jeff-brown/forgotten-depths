"""Movement commands for navigating the world."""

from ..base_command import BaseCommand
from typing import List

class MoveCommand(BaseCommand):
    """Command for moving between rooms."""

    def __init__(self):
        """Initialize the move command."""
        super().__init__("go", ["move", "walk"])
        self.description = "Move in a direction"
        self.usage = "go <direction>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the move command."""
        if not args:
            return "Which direction would you like to go?"

        direction = args[0].lower()
        return self._move_player(player, direction)

    def _move_player(self, player: 'Player', direction: str) -> str:
        """Move the player in the specified direction."""
        pass

class NorthCommand(BaseCommand):
    """Shortcut command for moving north."""

    def __init__(self):
        super().__init__("north", ["n"])
        self.description = "Move north"
        self.usage = "north"

    def execute(self, player: 'Player', args: List[str]) -> str:
        move_cmd = MoveCommand()
        return move_cmd._move_player(player, "north")

class SouthCommand(BaseCommand):
    """Shortcut command for moving south."""

    def __init__(self):
        super().__init__("south", ["s"])
        self.description = "Move south"
        self.usage = "south"

    def execute(self, player: 'Player', args: List[str]) -> str:
        move_cmd = MoveCommand()
        return move_cmd._move_player(player, "south")

class EastCommand(BaseCommand):
    """Shortcut command for moving east."""

    def __init__(self):
        super().__init__("east", ["e"])
        self.description = "Move east"
        self.usage = "east"

    def execute(self, player: 'Player', args: List[str]) -> str:
        move_cmd = MoveCommand()
        return move_cmd._move_player(player, "east")

class WestCommand(BaseCommand):
    """Shortcut command for moving west."""

    def __init__(self):
        super().__init__("west", ["w"])
        self.description = "Move west"
        self.usage = "west"

    def execute(self, player: 'Player', args: List[str]) -> str:
        move_cmd = MoveCommand()
        return move_cmd._move_player(player, "west")

class LookCommand(BaseCommand):
    """Command for examining the current room or objects."""

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
        pass

    def _look_at_target(self, player: 'Player', target: str) -> str:
        """Look at a specific target."""
        pass