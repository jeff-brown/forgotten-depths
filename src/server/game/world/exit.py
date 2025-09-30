"""Exit class representing connections between rooms."""

from typing import Optional

class Exit:
    """Represents a connection between two rooms."""

    def __init__(self, destination_room_id: str, direction: str = ""):
        """Initialize an exit."""
        self.destination_room_id = destination_room_id
        self.direction = direction
        self.is_locked = False
        self.key_required: Optional[str] = None
        self.hidden = False
        self.description = ""

    def can_traverse(self, character: 'Character') -> bool:
        """Check if a character can traverse this exit."""
        if self.is_locked:
            return False
        return True

    def get_description(self) -> str:
        """Get the description of this exit."""
        if self.description:
            return self.description
        return f"You can go {self.direction}."

    def lock(self, key_id: Optional[str] = None):
        """Lock this exit."""
        self.is_locked = True
        self.key_required = key_id

    def unlock(self):
        """Unlock this exit."""
        self.is_locked = False
        self.key_required = None