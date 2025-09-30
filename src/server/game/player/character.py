"""Character class representing player avatars in the game world."""

from typing import Dict, Any, Optional

class Character:
    """Represents a player's character in the game world."""

    def __init__(self, name: str):
        """Initialize a character."""
        self.name = name
        self.level = 1
        self.experience = 0
        self.health = 100
        self.max_health = 100
        self.mana = 50
        self.max_mana = 50
        self.room_id: Optional[str] = None
        self.stats = {
            'strength': 10,
            'dexterity': 10,
            'constitution': 10,
            'intelligence': 10,
            'wisdom': 10,
            'charisma': 10
        }
        self.inventory = None
        self.gold = 100  # Starting gold
        self.initiative = self.stats['dexterity'] + 10

    def take_damage(self, amount: int):
        """Apply damage to the character."""
        self.health = max(0, self.health - amount)

    def heal(self, amount: int):
        """Heal the character."""
        self.health = min(self.max_health, self.health + amount)

    def is_alive(self) -> bool:
        """Check if the character is alive."""
        return self.health > 0

    def gain_experience(self, amount: int):
        """Give experience to the character."""
        self.experience += amount

    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary for saving."""
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create character from dictionary data."""
        pass