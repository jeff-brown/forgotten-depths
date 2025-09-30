"""Graph-based navigation system for MUD world."""

import heapq
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class EdgeType(Enum):
    """Types of edges between rooms."""
    NORMAL = "normal"           # Standard movement
    DOOR = "door"              # Requires door to be unlocked
    HIDDEN = "hidden"          # Secret passages
    CLIMB = "climb"            # Requires climbing
    SWIM = "swim"              # Requires swimming
    FLY = "fly"                # Requires flying
    TELEPORT = "teleport"      # Magical transportation
    ONE_WAY = "one_way"        # Can only go one direction


@dataclass
class GraphEdge:
    """Represents a connection between two rooms in the world graph."""

    from_room: str
    to_room: str
    edge_type: EdgeType = EdgeType.NORMAL
    weight: float = 1.0        # Travel cost/time
    direction: str = ""        # Compass direction if applicable
    requirements: List[str] = field(default_factory=list)  # Skills/items required
    is_locked: bool = False
    key_required: Optional[str] = None
    hidden: bool = False
    description: str = ""

    def can_traverse(self, character: 'Character') -> bool:
        """Check if a character can traverse this edge."""
        if self.is_locked and not self._has_key(character):
            return False

        if self.hidden and not self._can_detect_hidden(character):
            return False

        # Check requirements (skills, items, etc.)
        for requirement in self.requirements:
            if not self._meets_requirement(character, requirement):
                return False

        return True

    def _has_key(self, character: 'Character') -> bool:
        """Check if character has required key."""
        if not self.key_required:
            return True
        # TODO: Check character's inventory for key
        return False

    def _can_detect_hidden(self, character: 'Character') -> bool:
        """Check if character can detect hidden passages."""
        # TODO: Check character's perception/search skills
        return True

    def _meets_requirement(self, character: 'Character', requirement: str) -> bool:
        """Check if character meets a specific requirement."""
        # TODO: Implement skill/item checking
        return True


class WorldGraph:
    """Graph representation of the MUD world for navigation."""

    def __init__(self):
        """Initialize an empty world graph."""
        self.rooms: Set[str] = set()
        self.edges: Dict[str, List[GraphEdge]] = {}
        self.reverse_edges: Dict[str, List[GraphEdge]] = {}

    def add_room(self, room_id: str):
        """Add a room to the graph."""
        self.rooms.add(room_id)
        if room_id not in self.edges:
            self.edges[room_id] = []
        if room_id not in self.reverse_edges:
            self.reverse_edges[room_id] = []

    def add_edge(self, edge: GraphEdge):
        """Add an edge between two rooms."""
        # Ensure rooms exist
        self.add_room(edge.from_room)
        self.add_room(edge.to_room)

        # Add edge to forward mapping
        self.edges[edge.from_room].append(edge)

        # Add edge to reverse mapping for efficient pathfinding
        self.reverse_edges[edge.to_room].append(edge)

    def remove_edge(self, from_room: str, to_room: str):
        """Remove an edge between two rooms."""
        if from_room in self.edges:
            self.edges[from_room] = [e for e in self.edges[from_room]
                                   if e.to_room != to_room]

        if to_room in self.reverse_edges:
            self.reverse_edges[to_room] = [e for e in self.reverse_edges[to_room]
                                         if e.from_room != from_room]

    def get_neighbors(self, room_id: str, character: 'Character' = None) -> List[GraphEdge]:
        """Get all traversable neighbors from a room."""
        if room_id not in self.edges:
            return []

        if character is None:
            return self.edges[room_id]

        return [edge for edge in self.edges[room_id] if edge.can_traverse(character)]

    def get_exits_by_direction(self, room_id: str) -> Dict[str, GraphEdge]:
        """Get exits organized by direction."""
        exits = {}
        if room_id in self.edges:
            for edge in self.edges[room_id]:
                if edge.direction:
                    exits[edge.direction.lower()] = edge
        return exits

    def find_path_dijkstra(self, start: str, goal: str, character: 'Character' = None) -> Optional[List[str]]:
        """Find shortest path using Dijkstra's algorithm."""
        if start not in self.rooms or goal not in self.rooms:
            return None

        distances = {room: float('inf') for room in self.rooms}
        distances[start] = 0
        previous = {}
        unvisited = [(0, start)]
        visited = set()

        while unvisited:
            current_distance, current = heapq.heappop(unvisited)

            if current in visited:
                continue

            visited.add(current)

            if current == goal:
                # Reconstruct path
                path = []
                while current in previous:
                    path.append(current)
                    current = previous[current]
                path.append(start)
                return list(reversed(path))

            for edge in self.get_neighbors(current, character):
                neighbor = edge.to_room
                distance = current_distance + edge.weight

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current
                    heapq.heappush(unvisited, (distance, neighbor))

        return None

    def find_path_astar(self, start: str, goal: str, character: 'Character' = None,
                       heuristic_func=None) -> Optional[List[str]]:
        """Find shortest path using A* algorithm with heuristic."""
        if start not in self.rooms or goal not in self.rooms:
            return None

        if heuristic_func is None:
            # Default heuristic (can be improved with actual coordinates)
            heuristic_func = lambda x, y: 0

        open_set = [(0, start)]
        came_from = {}
        g_score = {room: float('inf') for room in self.rooms}
        g_score[start] = 0
        f_score = {room: float('inf') for room in self.rooms}
        f_score[start] = heuristic_func(start, goal)

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return list(reversed(path))

            for edge in self.get_neighbors(current, character):
                neighbor = edge.to_room
                tentative_g_score = g_score[current] + edge.weight

                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + heuristic_func(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None

    def find_all_reachable(self, start: str, character: 'Character' = None,
                          max_distance: int = None) -> Dict[str, int]:
        """Find all rooms reachable from start room within max_distance."""
        if start not in self.rooms:
            return {}

        distances = {start: 0}
        queue = [(start, 0)]

        while queue:
            current_room, current_distance = queue.pop(0)

            if max_distance is not None and current_distance >= max_distance:
                continue

            for edge in self.get_neighbors(current_room, character):
                neighbor = edge.to_room
                new_distance = current_distance + 1

                if neighbor not in distances or new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    queue.append((neighbor, new_distance))

        return distances

    def get_area_rooms(self, center: str, radius: int, character: 'Character' = None) -> List[str]:
        """Get all rooms within a certain radius of a center room."""
        reachable = self.find_all_reachable(center, character, radius)
        return [room for room, distance in reachable.items() if distance <= radius]

    def find_shortest_path_length(self, start: str, goal: str, character: 'Character' = None) -> int:
        """Find the length of the shortest path between two rooms."""
        path = self.find_path_dijkstra(start, goal, character)
        return len(path) - 1 if path else -1

    def get_room_connections_count(self, room_id: str) -> int:
        """Get the number of connections from a room."""
        return len(self.edges.get(room_id, []))

    def get_graph_stats(self) -> Dict[str, int]:
        """Get statistics about the world graph."""
        total_edges = sum(len(edges) for edges in self.edges.values())
        return {
            'rooms': len(self.rooms),
            'edges': total_edges,
            'avg_connections': total_edges / len(self.rooms) if self.rooms else 0
        }

    def validate_graph(self) -> List[str]:
        """Validate the graph and return any issues found."""
        issues = []

        # Check for orphaned rooms
        for room in self.rooms:
            if not self.edges.get(room) and not self.reverse_edges.get(room):
                issues.append(f"Room {room} has no connections")

        # Check for missing destination rooms
        for room_id, edges in self.edges.items():
            for edge in edges:
                if edge.to_room not in self.rooms:
                    issues.append(f"Edge from {room_id} points to non-existent room {edge.to_room}")

        return issues