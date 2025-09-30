"""Base NPC class for non-player characters."""

from typing import List, Optional

class NPC:
    """Base class for all non-player characters."""

    def __init__(self, npc_id: str, name: str, description: str):
        """Initialize an NPC."""
        self.npc_id = npc_id
        self.name = name
        self.description = description
        self.room_id: Optional[str] = None
        self.dialogue: List[str] = []
        self.friendly = True
        self.can_talk = True
        self.can_trade = False

    def talk_to(self, player: 'Character') -> str:
        """Handle conversation with a player."""
        if not self.can_talk:
            return f"{self.name} doesn't respond."

        if self.dialogue:
            return self.dialogue[0]
        return f"{self.name} says: 'Hello, traveler.'"

    def interact(self, player: 'Character', action: str) -> str:
        """Handle general interaction with a player."""
        if action == "talk":
            return self.talk_to(player)
        return f"You can't {action} with {self.name}."

    def move_to_room(self, room_id: str):
        """Move the NPC to a different room."""
        self.room_id = room_id

    def update(self):
        """Update the NPC (called each game tick)."""
        pass