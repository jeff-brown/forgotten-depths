"""AI behavior system for NPCs."""

from enum import Enum
from typing import List, Optional
import random

class AIState(Enum):
    """AI states for NPCs."""
    IDLE = "idle"
    PATROL = "patrol"
    COMBAT = "combat"
    FLEEING = "fleeing"
    RETURNING = "returning"

class AIBehavior:
    """Handles AI behavior for NPCs."""

    def __init__(self, npc: 'NPC'):
        """Initialize AI behavior."""
        self.npc = npc
        self.state = AIState.IDLE
        self.patrol_rooms: List[str] = []
        self.home_room: Optional[str] = None
        self.current_patrol_index = 0
        self.action_cooldown = 0

    def update(self):
        """Update AI behavior."""
        if self.action_cooldown > 0:
            self.action_cooldown -= 1
            return

        if self.state == AIState.IDLE:
            self._handle_idle()
        elif self.state == AIState.PATROL:
            self._handle_patrol()
        elif self.state == AIState.COMBAT:
            self._handle_combat()
        elif self.state == AIState.FLEEING:
            self._handle_fleeing()

    def _handle_idle(self):
        """Handle idle state behavior."""
        if self.patrol_rooms and random.random() < 0.1:
            self.state = AIState.PATROL

    def _handle_patrol(self):
        """Handle patrol behavior."""
        if not self.patrol_rooms:
            self.state = AIState.IDLE
            return

        if random.random() < 0.3:
            next_room = self.patrol_rooms[self.current_patrol_index]
            self.npc.move_to_room(next_room)
            self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_rooms)
            self.action_cooldown = random.randint(3, 8)

    def _handle_combat(self):
        """Handle combat behavior."""
        pass

    def _handle_fleeing(self):
        """Handle fleeing behavior."""
        pass

    def set_patrol_route(self, rooms: List[str]):
        """Set the patrol route for this NPC."""
        self.patrol_rooms = rooms

    def enter_combat(self, target: 'Character'):
        """Enter combat with a target."""
        self.state = AIState.COMBAT