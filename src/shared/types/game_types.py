"""Common type definitions used throughout the game."""

from enum import Enum
from typing import Dict, List, Optional, Union, NamedTuple, Tuple
from dataclasses import dataclass

class Direction(Enum):
    """Cardinal and ordinal directions."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    UP = "up"
    DOWN = "down"

class MessageType(Enum):
    """Types of messages that can be sent."""
    SYSTEM = "system"
    CHAT = "chat"
    TELL = "tell"
    SAY = "say"
    EMOTE = "emote"
    COMBAT = "combat"
    ERROR = "error"
    INFO = "info"

class ItemSlot(Enum):
    """Equipment slots for items."""
    WEAPON = "weapon"
    SHIELD = "shield"
    HELMET = "helmet"
    CHEST = "chest"
    LEGS = "legs"
    BOOTS = "boots"
    GLOVES = "gloves"
    RING = "ring"
    NECKLACE = "necklace"

@dataclass
class Position:
    """Represents a position in the game world."""
    area_id: str
    room_id: str
    x: Optional[int] = None
    y: Optional[int] = None
    z: Optional[int] = None

@dataclass
class Stats:
    """Character statistics."""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

@dataclass
class Health:
    """Health and mana information."""
    current_health: int = 100
    max_health: int = 100
    current_mana: int = 50
    max_mana: int = 50

class CommandResult(NamedTuple):
    """Result of a command execution."""
    success: bool
    message: str
    data: Optional[Dict] = None

class CombatResult(NamedTuple):
    """Result of a combat action."""
    damage_dealt: int
    target_killed: bool
    message: str
    effects: List[str] = []

@dataclass
class GameMessage:
    """A message to be sent to a player."""
    content: str
    message_type: MessageType = MessageType.INFO
    sender: Optional[str] = None
    target: Optional[str] = None
    timestamp: Optional[float] = None

PlayerID = str
CharacterID = str
RoomID = str
AreaID = str
ItemID = str
NPCID = str

Coordinates = Tuple[int, int, int]