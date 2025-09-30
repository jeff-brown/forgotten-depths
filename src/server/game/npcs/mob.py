"""Mob class for hostile NPCs."""

from .npc import NPC
from typing import Optional
import random

class Mob(NPC):
    """Represents a hostile NPC that can fight players."""

    def __init__(self, npc_id: str, name: str, description: str):
        """Initialize a mob."""
        super().__init__(npc_id, name, description)
        self.friendly = False
        self.can_talk = False

        self.level = 1
        self.health = 50
        self.max_health = 50
        self.damage_min = 5
        self.damage_max = 10
        self.experience_reward = 25
        self.gold_reward = (1, 10)

        self.stats = {
            'strength': 12,
            'dexterity': 10,
            'constitution': 12,
            'intelligence': 8,
            'wisdom': 10,
            'charisma': 6
        }

        self.strength = self.stats['strength']
        self.dexterity = self.stats['dexterity']
        self.constitution = self.stats['constitution']
        self.intelligence = self.stats['intelligence']
        self.wisdom = self.stats['wisdom']
        self.charisma = self.stats['charisma']

        self.initiative = self.dexterity + random.randint(1, 6)

        self.aggressive = True
        self.combat_target: Optional['Character'] = None

    def attack(self, target: 'Character') -> int:
        """Attack a target and return damage dealt."""
        damage = random.randint(self.damage_min, self.damage_max)
        return damage

    def take_damage(self, amount: int) -> bool:
        """Take damage and return True if mob dies."""
        self.health = max(0, self.health - amount)
        return self.health <= 0

    def is_alive(self) -> bool:
        """Check if the mob is alive."""
        return self.health > 0

    def get_loot(self) -> dict:
        """Generate loot when the mob dies."""
        gold = random.randint(*self.gold_reward)
        return {
            'gold': gold,
            'experience': self.experience_reward,
            'items': []
        }

    def respawn(self):
        """Respawn the mob to full health."""
        self.health = self.max_health
        self.combat_target = None

    def update(self):
        """Update mob behavior each tick."""
        if self.aggressive and self.combat_target is None:
            pass