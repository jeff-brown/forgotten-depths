"""Base item class for all game items."""

from enum import Enum
from typing import Dict, Any

class ItemType(Enum):
    """Types of items in the game."""
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    TREASURE = "treasure"
    KEY = "key"
    MISC = "misc"

class Item:
    """Base class for all items in the game."""

    def __init__(self, item_id: str, name: str, description: str):
        """Initialize an item."""
        self.item_id = item_id
        self.name = name
        self.description = description
        self.item_type = ItemType.MISC
        self.weight = 1.0
        self.value = 0
        self.stackable = False
        self.quantity = 1

    def use(self, character: 'Character') -> bool:
        """Use the item on a character."""
        return False

    def can_stack_with(self, other_item: 'Item') -> bool:
        """Check if this item can stack with another."""
        return (self.stackable and
                self.item_id == other_item.item_id and
                type(self) == type(other_item))

    def to_dict(self) -> Dict[str, Any]:
        """Convert item to dictionary for saving."""
        return {
            'item_id': self.item_id,
            'name': self.name,
            'description': self.description,
            'item_type': self.item_type.value,
            'weight': self.weight,
            'value': self.value,
            'quantity': self.quantity
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        """Create item from dictionary data."""
        pass