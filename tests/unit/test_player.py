"""Unit tests for player-related classes."""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from server.game.player.player import Player
from server.game.player.character import Character
from server.game.player.inventory import Inventory

class TestPlayer(unittest.TestCase):
    """Test cases for Player class."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Player("testuser")

    def test_player_initialization(self):
        """Test player initialization."""
        self.assertEqual(self.player.name, "testuser")
        self.assertIsNone(self.player.character)
        self.assertFalse(self.player.logged_in)

    def test_player_login(self):
        """Test player login functionality."""
        # This would need proper implementation
        pass

class TestCharacter(unittest.TestCase):
    """Test cases for Character class."""

    def setUp(self):
        """Set up test fixtures."""
        self.character = Character("TestChar")

    def test_character_initialization(self):
        """Test character initialization."""
        self.assertEqual(self.character.name, "TestChar")
        self.assertEqual(self.character.level, 1)
        self.assertEqual(self.character.health, 100)
        self.assertEqual(self.character.max_health, 100)
        self.assertTrue(self.character.is_alive())

    def test_take_damage(self):
        """Test damage handling."""
        initial_health = self.character.health
        damage = 25
        self.character.take_damage(damage)
        self.assertEqual(self.character.health, initial_health - damage)

    def test_heal(self):
        """Test healing."""
        self.character.take_damage(50)
        self.character.heal(25)
        self.assertEqual(self.character.health, 75)

    def test_heal_over_max(self):
        """Test healing doesn't exceed max health."""
        self.character.heal(50)
        self.assertEqual(self.character.health, self.character.max_health)

    def test_death(self):
        """Test character death."""
        self.character.take_damage(150)
        self.assertEqual(self.character.health, 0)
        self.assertFalse(self.character.is_alive())

    def test_gain_experience(self):
        """Test experience gain."""
        initial_exp = self.character.experience
        exp_gain = 100
        self.character.gain_experience(exp_gain)
        self.assertEqual(self.character.experience, initial_exp + exp_gain)

class TestInventory(unittest.TestCase):
    """Test cases for Inventory class."""

    def setUp(self):
        """Set up test fixtures."""
        self.inventory = Inventory(max_capacity=5)

    def test_inventory_initialization(self):
        """Test inventory initialization."""
        self.assertEqual(len(self.inventory.items), 0)
        self.assertEqual(self.inventory.max_capacity, 5)
        self.assertEqual(self.inventory.gold, 0)
        self.assertFalse(self.inventory.is_full())

    def test_inventory_capacity(self):
        """Test inventory capacity limits."""
        # Create mock items
        class MockItem:
            def __init__(self, name):
                self.name = name
                self.weight = 1.0

        # Fill inventory to capacity
        for i in range(5):
            item = MockItem(f"item_{i}")
            self.assertTrue(self.inventory.add_item(item))

        # Try to add one more (should fail)
        extra_item = MockItem("extra")
        self.assertFalse(self.inventory.add_item(extra_item))
        self.assertTrue(self.inventory.is_full())

if __name__ == '__main__':
    unittest.main()