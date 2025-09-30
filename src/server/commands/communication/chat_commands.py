"""Communication commands for player chat and interaction."""

from ..base_command import BaseCommand
from typing import List

class SayCommand(BaseCommand):
    """Command for speaking to players in the same room."""

    def __init__(self):
        super().__init__("say", ["'"])
        self.description = "Say something to players in the room"
        self.usage = "say <message>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the say command."""
        if not args:
            return "What would you like to say?"

        message = " ".join(args)
        return self._broadcast_to_room(player, message)

    def _broadcast_to_room(self, player: 'Player', message: str) -> str:
        """Broadcast a message to all players in the room."""
        pass

class TellCommand(BaseCommand):
    """Command for private messages to specific players."""

    def __init__(self):
        super().__init__("tell", ["whisper", "t"])
        self.description = "Send a private message to another player"
        self.usage = "tell <player> <message>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the tell command."""
        if len(args) < 2:
            return "Usage: tell <player> <message>"

        target_name = args[0]
        message = " ".join(args[1:])
        return self._send_private_message(player, target_name, message)

    def _send_private_message(self, sender: 'Player', target_name: str, message: str) -> str:
        """Send a private message to another player."""
        pass

class ChatCommand(BaseCommand):
    """Command for global chat channel."""

    def __init__(self):
        super().__init__("chat", ["ooc"])
        self.description = "Send a message to the global chat channel"
        self.usage = "chat <message>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the chat command."""
        if not args:
            return "What would you like to say on chat?"

        message = " ".join(args)
        return self._broadcast_global(player, message)

    def _broadcast_global(self, player: 'Player', message: str) -> str:
        """Broadcast a message to all connected players."""
        pass

class EmoteCommand(BaseCommand):
    """Command for performing emotes/actions."""

    def __init__(self):
        super().__init__("emote", ["me", ":"])
        self.description = "Perform an emote or action"
        self.usage = "emote <action>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the emote command."""
        if not args:
            return "What would you like to emote?"

        action = " ".join(args)
        return self._perform_emote(player, action)

    def _perform_emote(self, player: 'Player', action: str) -> str:
        """Perform an emote visible to players in the room."""
        pass