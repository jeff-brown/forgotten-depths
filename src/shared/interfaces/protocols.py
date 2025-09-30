"""Protocol definitions for type hints and interfaces."""

from typing import Protocol, Any, Dict, List, Optional
from abc import abstractmethod

class Saveable(Protocol):
    """Protocol for objects that can be saved to persistent storage."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary for saving."""
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Saveable':
        """Create object from dictionary data."""
        ...

class Updatable(Protocol):
    """Protocol for objects that can be updated each game tick."""

    @abstractmethod
    def update(self) -> None:
        """Update the object for one game tick."""
        ...

class Messageable(Protocol):
    """Protocol for objects that can receive messages."""

    @abstractmethod
    def send_message(self, message: str, message_type: str = "info") -> None:
        """Send a message to this object."""
        ...

class Moveable(Protocol):
    """Protocol for objects that can move between rooms."""

    @abstractmethod
    def move_to_room(self, room_id: str) -> bool:
        """Move to a specified room."""
        ...

    @abstractmethod
    def get_current_room(self) -> Optional[str]:
        """Get the current room ID."""
        ...

class Interactable(Protocol):
    """Protocol for objects that can be interacted with."""

    @abstractmethod
    def interact(self, actor: Any, action: str, **kwargs) -> str:
        """Handle interaction with this object."""
        ...

    @abstractmethod
    def get_description(self, observer: Any = None) -> str:
        """Get description of this object."""
        ...

class Useable(Protocol):
    """Protocol for items that can be used."""

    @abstractmethod
    def use(self, user: Any, target: Any = None) -> bool:
        """Use this item."""
        ...

    @abstractmethod
    def can_use(self, user: Any) -> bool:
        """Check if this item can be used by the user."""
        ...

class Equipable(Protocol):
    """Protocol for items that can be equipped."""

    @abstractmethod
    def equip(self, character: Any) -> bool:
        """Equip this item to a character."""
        ...

    @abstractmethod
    def unequip(self, character: Any) -> bool:
        """Unequip this item from a character."""
        ...

    @abstractmethod
    def can_equip(self, character: Any) -> bool:
        """Check if this item can be equipped by the character."""
        ...

class Combatant(Protocol):
    """Protocol for entities that can participate in combat."""

    @abstractmethod
    def attack(self, target: 'Combatant') -> int:
        """Attack a target and return damage dealt."""
        ...

    @abstractmethod
    def take_damage(self, amount: int, damage_type: str = "physical") -> bool:
        """Take damage and return True if killed."""
        ...

    @abstractmethod
    def is_alive(self) -> bool:
        """Check if this combatant is alive."""
        ...

    @abstractmethod
    def get_health(self) -> tuple[int, int]:
        """Get current and max health."""
        ...

class CommandHandler(Protocol):
    """Protocol for objects that can handle commands."""

    @abstractmethod
    def handle_command(self, command: str, args: List[str], sender: Any) -> str:
        """Handle a command and return the result."""
        ...

    @abstractmethod
    def can_handle_command(self, command: str, sender: Any) -> bool:
        """Check if this handler can process the command."""
        ...

class DataStore(Protocol):
    """Protocol for data storage backends."""

    @abstractmethod
    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save data with the given key."""
        ...

    @abstractmethod
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data by key."""
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data by key."""
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...

class EventHandler(Protocol):
    """Protocol for event handling."""

    @abstractmethod
    def handle_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle an event."""
        ...

    @abstractmethod
    def subscribe_to_events(self, event_types: List[str]) -> None:
        """Subscribe to specific event types."""
        ...

class NetworkConnection(Protocol):
    """Protocol for network connections."""

    @abstractmethod
    def send(self, data: str) -> bool:
        """Send data through the connection."""
        ...

    @abstractmethod
    def receive(self) -> Optional[str]:
        """Receive data from the connection."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect the connection."""
        ...