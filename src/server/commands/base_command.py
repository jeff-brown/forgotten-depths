"""Base command class for all player commands."""

from abc import ABC, abstractmethod
from typing import List

class BaseCommand(ABC):
    """Base class for all commands."""

    def __init__(self, name: str, aliases: List[str] = None):
        """Initialize a command."""
        self.name = name
        self.aliases = aliases or []
        self.description = ""
        self.usage = ""

    @abstractmethod
    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the command."""
        pass

    def can_execute(self, player: 'Player') -> bool:
        """Check if the player can execute this command."""
        return True

    def matches(self, command_name: str) -> bool:
        """Check if this command matches the given name or alias."""
        return (command_name.lower() == self.name.lower() or
                command_name.lower() in [alias.lower() for alias in self.aliases])

class CommandManager:
    """Manages all available commands."""

    def __init__(self):
        """Initialize the command manager."""
        self.commands: List[BaseCommand] = []
        self._load_default_commands()

    def _load_default_commands(self):
        """Load the default set of commands."""
        try:
            from .async_commands import get_default_async_commands
            for command in get_default_async_commands():
                self.register_command(command)
        except ImportError:
            # Fallback if async commands aren't available
            pass

    def register_command(self, command: BaseCommand):
        """Register a new command."""
        self.commands.append(command)

    def execute_command(self, player: 'Player', input_text: str) -> str:
        """Parse and execute a command."""
        if not input_text.strip():
            return "What would you like to do?"

        parts = input_text.strip().split()
        command_name = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        for command in self.commands:
            if command.matches(command_name) and command.can_execute(player):
                return command.execute(player, args)

        return f"Unknown command: {command_name}"

    def get_command_help(self, command_name: str = None) -> str:
        """Get help for a specific command or all commands."""
        if command_name:
            for command in self.commands:
                if command.matches(command_name):
                    return f"{command.name}: {command.description}\nUsage: {command.usage}"
            return f"Unknown command: {command_name}"

        help_text = "Available commands:\n"
        for command in self.commands:
            help_text += f"  {command.name}: {command.description}\n"
        return help_text

    def get_command_list(self) -> List[str]:
        """Get a list of all command names."""
        return [command.name for command in self.commands]

    def get_command_count(self) -> int:
        """Get the number of registered commands."""
        return len(self.commands)