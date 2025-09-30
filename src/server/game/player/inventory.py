"""Inventory system for player characters."""

from typing import List, Optional

class Inventory:
    """Manages a character's inventory."""

    def __init__(self, max_capacity: int = 20):
        """Initialize an inventory."""
        self.items: List['Item'] = []
        self.max_capacity = max_capacity
        self.gold = 0

    def add_item(self, item: 'Item') -> bool:
        """Add an item to the inventory."""
        if len(self.items) < self.max_capacity:
            self.items.append(item)
            return True
        return False

    def remove_item(self, item: 'Item') -> bool:
        """Remove an item from the inventory."""
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def find_item(self, name: str) -> Optional['Item']:
        """Find an item by name."""
        for item in self.items:
            if item.name.lower() == name.lower():
                return item
        return None

    def get_weight(self) -> float:
        """Get the total weight of items in inventory."""
        return sum(item.weight for item in self.items)

    def is_full(self) -> bool:
        """Check if inventory is at capacity."""
        return len(self.items) >= self.max_capacity