"""Graph-based navigation commands for the MUD."""

from typing import List
from .base_command import BaseCommand


class PathCommand(BaseCommand):
    """Find and display a path to a destination."""

    def __init__(self):
        super().__init__("path", ["route", "directions"])
        self.description = "Find a path to a destination room"
        self.usage = "path <destination_room_id>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the path command."""
        if not args:
            return "Path to where? Usage: path <destination>"

        if not player.character or not player.character.room_id:
            return "You are nowhere, so you can't find a path anywhere."

        destination = args[0]

        # Get world manager from game engine
        from server.core.async_game_engine import AsyncGameEngine
        if not hasattr(player, '_game_engine'):
            return "Navigation system not available."

        world_manager = player._game_engine.world_manager

        # Check if destination exists
        if not world_manager.get_room(destination):
            return f"Unknown destination: {destination}"

        # Find path
        path = world_manager.find_path(player.character.room_id, destination, player.character)

        if not path:
            return f"No path found to {destination}."

        if len(path) == 1:
            return "You are already at your destination!"

        # Format path display
        path_str = " -> ".join(path)
        steps = len(path) - 1

        result = f"Path to {destination} ({steps} steps):\n"
        result += f"Route: {path_str}\n\n"

        # Show turn-by-turn directions
        result += "Directions:\n"
        for i in range(len(path) - 1):
            current_room = path[i]
            next_room = path[i + 1]

            # Get the direction for this step
            exits = world_manager.get_exits_from_room(current_room, player.character)
            direction = None
            for dir_name, room_id in exits.items():
                if room_id == next_room:
                    direction = dir_name
                    break

            if direction:
                result += f"{i + 1}. Go {direction}\n"
            else:
                result += f"{i + 1}. Move to {next_room}\n"

        return result


class GotoCommand(BaseCommand):
    """Automatically move to a destination using pathfinding."""

    def __init__(self):
        super().__init__("goto", ["travel", "go"])
        self.description = "Automatically travel to a destination room"
        self.usage = "goto <destination_room_id>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the goto command."""
        if not args:
            return "Go to where? Usage: goto <destination>"

        if not player.character or not player.character.room_id:
            return "You are nowhere, so you can't go anywhere."

        destination = args[0]

        # Get world manager
        from server.core.async_game_engine import AsyncGameEngine
        if not hasattr(player, '_game_engine'):
            return "Navigation system not available."

        world_manager = player._game_engine.world_manager

        # Check if destination exists
        if not world_manager.get_room(destination):
            return f"Unknown destination: {destination}"

        # Find path
        path = world_manager.find_path(player.character.room_id, destination, player.character)

        if not path:
            return f"No path found to {destination}."

        if len(path) == 1:
            return "You are already at your destination!"

        # For now, just show the first step (in a real implementation,
        # this might trigger automatic movement)
        current_room = path[0]
        next_room = path[1]

        exits = world_manager.get_exits_from_room(current_room, player.character)
        direction = None
        for dir_name, room_id in exits.items():
            if room_id == next_room:
                direction = dir_name
                break

        if direction:
            return f"To reach {destination}, first go {direction}. ({len(path) - 1} steps remaining)"
        else:
            return f"To reach {destination}, move to {next_room}. ({len(path) - 1} steps remaining)"


class ExitsCommand(BaseCommand):
    """Show detailed exit information using graph system."""

    def __init__(self):
        super().__init__("exits", ["exit", "ways"])
        self.description = "Show detailed information about available exits"
        self.usage = "exits"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the exits command."""
        if not player.character or not player.character.room_id:
            return "You are nowhere, so there are no exits."

        # Get world manager
        from server.core.async_game_engine import AsyncGameEngine
        if not hasattr(player, '_game_engine'):
            return "Navigation system not available."

        world_manager = player._game_engine.world_manager
        current_room = player.character.room_id

        # Get available exits using graph system
        edges = world_manager.world_graph.get_neighbors(current_room, player.character)

        if not edges:
            return "There are no exits from here."

        result = "Available exits:\n"
        result += "=" * 20 + "\n"

        for edge in edges:
            direction = edge.direction or "???"
            destination = edge.to_room

            # Get destination room details
            dest_room = world_manager.get_room(destination)
            dest_title = dest_room.title if dest_room else destination

            # Format exit info
            result += f"{direction.upper():>8} - {dest_title} ({destination})"

            # Add special info about the exit
            if edge.edge_type.value != "normal":
                result += f" [{edge.edge_type.value}]"

            if edge.is_locked:
                result += " [LOCKED]"

            if edge.hidden:
                result += " [HIDDEN]"

            if edge.requirements:
                result += f" (requires: {', '.join(edge.requirements)})"

            result += "\n"

        return result


class MapCommand(BaseCommand):
    """Show a local area map using graph distances."""

    def __init__(self):
        super().__init__("map", ["area", "vicinity"])
        self.description = "Show nearby rooms within walking distance"
        self.usage = "map [radius]"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the map command."""
        if not player.character or not player.character.room_id:
            return "You are nowhere, so there's no map to show."

        # Parse radius argument
        radius = 2  # default
        if args:
            try:
                radius = int(args[0])
                if radius < 1 or radius > 5:
                    return "Map radius must be between 1 and 5."
            except ValueError:
                return "Invalid radius. Use a number between 1 and 5."

        # Get world manager
        from server.core.async_game_engine import AsyncGameEngine
        if not hasattr(player, '_game_engine'):
            return "Navigation system not available."

        world_manager = player._game_engine.world_manager
        current_room = player.character.room_id

        # Get rooms within radius
        nearby_rooms = world_manager.get_area_rooms_within_distance(
            current_room, radius, player.character
        )

        if not nearby_rooms:
            return "No nearby rooms found."

        result = f"Local Area Map (radius {radius}):\n"
        result += "=" * 30 + "\n"

        # Sort by distance
        distances = world_manager.world_graph.find_all_reachable(
            current_room, player.character, radius
        )

        sorted_rooms = sorted(nearby_rooms, key=lambda r: distances.get(r, 999))

        for room_id in sorted_rooms:
            distance = distances.get(room_id, 0)
            room = world_manager.get_room(room_id)

            if room:
                marker = ">>> " if room_id == current_room else f"[{distance}] "
                result += f"{marker}{room.title} ({room_id})\n"

        return result


class NearbyCommand(BaseCommand):
    """Find nearby rooms with specific criteria."""

    def __init__(self):
        super().__init__("nearby", ["near", "around"])
        self.description = "Find nearby rooms or search for specific room types"
        self.usage = "nearby [search_term] [max_distance]"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the nearby command."""
        if not player.character or not player.character.room_id:
            return "You are nowhere, so there's nothing nearby."

        search_term = ""
        max_distance = 3

        if args:
            search_term = args[0].lower()
            if len(args) > 1:
                try:
                    max_distance = int(args[1])
                    if max_distance < 1 or max_distance > 10:
                        return "Search distance must be between 1 and 10."
                except ValueError:
                    return "Invalid distance. Use a number between 1 and 10."

        # Get world manager
        from server.core.async_game_engine import AsyncGameEngine
        if not hasattr(player, '_game_engine'):
            return "Navigation system not available."

        world_manager = player._game_engine.world_manager
        current_room = player.character.room_id

        # Get rooms within distance
        nearby_rooms = world_manager.get_area_rooms_within_distance(
            current_room, max_distance, player.character
        )

        # Filter by search term if provided
        matching_rooms = []
        for room_id in nearby_rooms:
            if room_id == current_room:
                continue

            room = world_manager.get_room(room_id)
            if room:
                if not search_term or (
                    search_term in room.title.lower() or
                    search_term in room.description.lower() or
                    search_term in room_id.lower()
                ):
                    matching_rooms.append(room_id)

        if not matching_rooms:
            if search_term:
                return f"No rooms matching '{search_term}' found within {max_distance} steps."
            else:
                return f"No rooms found within {max_distance} steps."

        # Get distances for sorting
        distances = world_manager.world_graph.find_all_reachable(
            current_room, player.character, max_distance
        )

        matching_rooms.sort(key=lambda r: distances.get(r, 999))

        result = f"Nearby rooms"
        if search_term:
            result += f" matching '{search_term}'"
        result += f" (within {max_distance} steps):\n"
        result += "=" * 40 + "\n"

        for room_id in matching_rooms:
            distance = distances.get(room_id, 0)
            room = world_manager.get_room(room_id)

            if room:
                result += f"[{distance}] {room.title} ({room_id})\n"

        return result


def get_navigation_commands():
    """Get all navigation commands."""
    return [
        PathCommand(),
        GotoCommand(),
        ExitsCommand(),
        MapCommand(),
        NearbyCommand()
    ]