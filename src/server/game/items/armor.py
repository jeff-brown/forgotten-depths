"""Armor class for protective items."""

from .item import Item, ItemType
from enum import Enum

class ArmorType(Enum):
    """Types of armor."""
    HELMET = "helmet"
    CHEST = "chest"
    LEGS = "legs"
    BOOTS = "boots"
    GLOVES = "gloves"
    SHIELD = "shield"

class Armor(Item):
    """Represents an armor item."""

    def __init__(self, item_id: str, name: str, description: str):
        """Initialize armor."""
        super().__init__(item_id, name, description)
        self.item_type = ItemType.ARMOR
        self.armor_type = ArmorType.CHEST
        self.defense = 5
        self.magic_resistance = 0
        self.durability = 100
        self.max_durability = 100
        self.equipped = False

    def get_defense(self) -> int:
        """Get the defense value of this armor."""
        if self.is_broken():
            return 0
        return self.defense

    def is_broken(self) -> bool:
        """Check if the armor is broken."""
        return self.durability <= 0

    def repair(self, amount: int = None):
        """Repair the armor."""
        if amount is None:
            self.durability = self.max_durability
        else:
            self.durability = min(self.max_durability, self.durability + amount)

    def degrade(self, amount: int = 1):
        """Degrade the armor's durability."""
        self.durability = max(0, self.durability - amount)

    def equip(self):
        """Equip this armor."""
        self.equipped = True

    def unequip(self):
        """Unequip this armor."""
        self.equipped = False