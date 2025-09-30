"""Player class representing connected users."""

from typing import Optional

class Player:
    """Represents a connected player."""

    def __init__(self, name: str, connection=None):
        """Initialize a player."""
        self.name = name
        self.connection = connection
        self.character: Optional['Character'] = None
        self.logged_in = False

    def send_message(self, message: str):
        """Send a message to the player."""
        if self.connection:
            self.connection.send(message)

    def login(self, character_name: str):
        """Log the player in with a character."""
        pass

    def logout(self):
        """Log the player out."""
        self.logged_in = False

    def execute_command(self, command: str):
        """Execute a command from the player."""
        pass