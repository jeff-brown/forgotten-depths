"""Weapon class for combat items."""

from .item import Item, ItemType
from enum import Enum

class WeaponType(Enum):
    """Types of weapons."""
    SWORD = "sword"
    AXE = "axe"
    MACE = "mace"
    DAGGER = "dagger"
    BOW = "bow"
    STAFF = "staff"

class Weapon(Item):
    """Represents a weapon item."""

    def __init__(self, item_id: str, name: str, description: str):
        """Initialize a weapon."""
        super().__init__(item_id, name, description)
        self.item_type = ItemType.WEAPON
        self.weapon_type = WeaponType.SWORD
        self.damage_min = 1
        self.damage_max = 4
        self.accuracy = 0.8
        self.critical_chance = 0.05
        self.durability = 100
        self.max_durability = 100

    def get_damage(self) -> int:
        """Calculate damage dealt by this weapon."""
        import random
        return random.randint(self.damage_min, self.damage_max)

    def is_broken(self) -> bool:
        """Check if the weapon is broken."""
        return self.durability <= 0

    def repair(self, amount: int = None):
        """Repair the weapon."""
        if amount is None:
            self.durability = self.max_durability
        else:
            self.durability = min(self.max_durability, self.durability + amount)

    def degrade(self, amount: int = 1):
        """Degrade the weapon's durability."""
        self.durability = max(0, self.durability - amount)