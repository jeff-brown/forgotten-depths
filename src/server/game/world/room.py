"""Room class representing locations in the game world."""

from typing import Dict, List, Optional

class Room:
    """Represents a location in the game world."""

    def __init__(self, room_id: str, title: str, description: str):
        """Initialize a room."""
        self.room_id = room_id
        self.title = title
        self.description = description
        self.exits: Dict[str, 'Exit'] = {}
        self.players: List['Character'] = []
        self.npcs: List['NPC'] = []
        self.items: List['Item'] = []

    def add_exit(self, direction: str, exit_obj: 'Exit'):
        """Add an exit to the room."""
        self.exits[direction] = exit_obj

    def get_exit(self, direction: str) -> Optional['Exit']:
        """Get an exit in a direction."""
        return self.exits.get(direction)

    def add_player(self, player: 'Character'):
        """Add a player to the room."""
        if player not in self.players:
            self.players.append(player)

    def remove_player(self, player: 'Character'):
        """Remove a player from the room."""
        if player in self.players:
            self.players.remove(player)

    def add_item(self, item: 'Item'):
        """Add an item to the room."""
        self.items.append(item)

    def remove_item(self, item: 'Item'):
        """Remove an item from the room."""
        if item in self.items:
            self.items.remove(item)

    def get_description(self, player: 'Character') -> str:
        """Get the full description of the room for a player."""
        # Build the room description
        desc_parts = []

        # Title and description
        desc_parts.append(f"\n{self.title}")
        desc_parts.append("=" * len(self.title))
        desc_parts.append(self.description)

        # Exits
        if self.exits:
            exits_list = list(self.exits.keys())
            if len(exits_list) == 1:
                desc_parts.append(f"\nThere is an exit to the {exits_list[0]}.")
            else:
                exits_str = ", ".join(exits_list[:-1]) + f" and {exits_list[-1]}"
                desc_parts.append(f"\nThere are exits to the {exits_str}.")
        else:
            desc_parts.append("\nThere are no obvious exits.")

        # Items
        if self.items:
            if len(self.items) == 1:
                desc_parts.append(f"\nYou see a {self.items[0].name} here.")
            else:
                item_names = [item.name for item in self.items]
                items_str = ", ".join(item_names[:-1]) + f" and a {item_names[-1]}"
                desc_parts.append(f"\nYou see a {items_str} here.")

        # Other players
        other_players = [p for p in self.players if p != player]
        if other_players:
            if len(other_players) == 1:
                desc_parts.append(f"\n{other_players[0].name} is here.")
            else:
                player_names = [p.name for p in other_players]
                players_str = ", ".join(player_names[:-1]) + f" and {player_names[-1]}"
                desc_parts.append(f"\n{players_str} are here.")

        # NPCs
        if self.npcs:
            for npc in self.npcs:
                desc_parts.append(f"\n{npc.name} is here.")

        return "\n".join(desc_parts) + "\n"

    def get_short_description(self) -> str:
        """Get a short description of the room."""
        return f"{self.title}"

    def get_exits_string(self) -> str:
        """Get a formatted string of available exits."""
        if not self.exits:
            return "No exits"
        return ", ".join(self.exits.keys())

    def has_exit(self, direction: str) -> bool:
        """Check if the room has an exit in a direction."""
        return direction.lower() in [d.lower() for d in self.exits.keys()]

    def get_all_contents(self) -> Dict[str, List]:
        """Get all contents of the room."""
        return {
            'players': self.players.copy(),
            'npcs': self.npcs.copy(),
            'items': self.items.copy()
        }

    def is_empty(self) -> bool:
        """Check if the room has no players, NPCs, or items."""
        return not (self.players or self.npcs or self.items)