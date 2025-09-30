"""Event system for game-wide event handling."""

from typing import Callable, Dict, List

class EventSystem:
    """Manages game events and event handlers."""

    def __init__(self):
        """Initialize the event system."""
        self.handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe a handler to an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def publish(self, event_type: str, data=None):
        """Publish an event to all subscribers."""
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(data)

    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe a handler from an event type."""
        if event_type in self.handlers:
            self.handlers[event_type].remove(handler)