"""Area class representing collections of rooms."""

from typing import Dict, List

class Area:
    """Represents a collection of related rooms."""

    def __init__(self, area_id: str, name: str, description: str):
        """Initialize an area."""
        self.area_id = area_id
        self.name = name
        self.description = description
        self.rooms: Dict[str, 'Room'] = {}
        self.level_range = (1, 10)

    def add_room(self, room: 'Room'):
        """Add a room to this area."""
        self.rooms[room.room_id] = room

    def get_room(self, room_id: str) -> 'Room':
        """Get a room by ID."""
        return self.rooms.get(room_id)

    def get_all_rooms(self) -> List['Room']:
        """Get all rooms in this area."""
        return list(self.rooms.values())

    def get_players_in_area(self) -> List['Character']:
        """Get all players currently in this area."""
        players = []
        for room in self.rooms.values():
            players.extend(room.players)
        return players