"""Manages the game world state and updates."""

import asyncio
from typing import Dict, Optional, List

from ...persistence.world_loader import WorldLoader
from .room import Room
from .area import Area
from .graph import WorldGraph, GraphEdge, EdgeType
from ...utils.logger import get_logger
from ...utils.colors import (
    announcement, monster_spawn, error_message, info_message,
    Colors, RGBColors, wrap_color, light_level_to_factor
)


class WorldManager:
    """Manages the game world, areas, rooms, and their states."""

    def __init__(self, game_engine=None):
        """Initialize the world manager."""
        self.areas: Dict[str, Area] = {}
        self.rooms: Dict[str, Room] = {}
        self.npcs: Dict[str, 'NPC'] = {}
        self.items: Dict[str, 'Item'] = {}
        self.barriers: Dict[str, Dict] = {}  # Store barrier definitions
        self.world_graph = WorldGraph()
        self.logger = get_logger()
        self.world_loader = WorldLoader()
        self.game_engine = game_engine
        self.rooms_data: Dict = {}  # Store raw room data for admin commands

    def load_world(self):
        """Load the world data from files."""
        self.logger.info("Loading world data...")

        try:
            # Load raw data from JSON files
            areas_data = self.world_loader.load_areas()
            rooms_data = self.world_loader.load_rooms()
            items_data = self.world_loader.load_items()
            npcs_data = self.world_loader.load_npcs()
            barriers_data = self.world_loader.load_barriers()

            # Store rooms_data for later use (e.g., admin commands)
            self.rooms_data = rooms_data

            # Create room objects
            self._create_rooms(rooms_data)

            # Create area objects
            self._create_areas(areas_data)

            # Setup room connections from room exit data
            self._setup_connections_from_rooms(rooms_data)

            # Build world graph from room exit data
            self._build_world_graph_from_rooms(rooms_data)

            # Load items, NPCs, and barriers
            self._load_items(items_data)
            self._load_npcs(npcs_data)
            self._load_barriers(barriers_data)

            # Initialize room items (place items from room JSON into rooms)
            self._initialize_room_items(rooms_data)

            # Initialize room NPCs (place NPCs from room JSON into rooms)
            self._initialize_room_npcs(rooms_data)

            # Validate graph
            issues = self.world_graph.validate_graph()
            if issues:
                self.logger.warning(f"Graph validation issues: {issues}")

            graph_stats = self.world_graph.get_graph_stats()
            self.logger.info(f"World loaded: {len(self.areas)} areas, {len(self.rooms)} rooms, {graph_stats['edges']} connections")

        except Exception as e:
            import traceback
            self.logger.error(f"Failed to load world: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Create a basic default world
            self._create_default_world()

    def _create_rooms(self, rooms_data: Dict):
        """Create room objects from data."""
        self.logger.info(f"[DOOR] WorldManager: Creating rooms from {len(rooms_data)} room data entries")

        # Check if dungeon1_1 is in the data
        if 'dungeon1_1' in rooms_data:
            self.logger.info(f"[DOOR] WorldManager: dungeon1_1 found in rooms_data")
            if 'locked_exits' in rooms_data['dungeon1_1']:
                self.logger.info(f"[DOOR] WorldManager: dungeon1_1 locked_exits in data: {rooms_data['dungeon1_1']['locked_exits']}")
            else:
                self.logger.info(f"[DOOR] WorldManager: dungeon1_1 MISSING locked_exits in rooms_data!")

        for room_id, room_data in rooms_data.items():
            room = Room(
                room_id=room_data.get('id', room_id),
                title=room_data.get('title', 'Unknown Room'),
                description=room_data.get('description', 'A mysterious place.')
            )

            # Set additional properties
            if 'area_id' in room_data:
                room.area_id = room_data['area_id']
            if 'is_safe' in room_data:
                room.is_safe = room_data['is_safe']
            if 'is_starting_room' in room_data:
                room.is_starting_room = room_data['is_starting_room']
            if 'light_level' in room_data:
                room.light_level = room_data['light_level']

            # Set lair properties - support both old and new formats
            # Old format: is_lair, lair_monster, respawn_time
            if 'is_lair' in room_data:
                room.is_lair = room_data['is_lair']
            if 'lair_monster' in room_data:
                room.lair_monster = room_data['lair_monster']
            if 'respawn_time' in room_data:
                room.respawn_time = room_data['respawn_time']

            # New format: lairs array with multiple spawns
            if 'lairs' in room_data:
                room.lairs = room_data['lairs']

            # NPCs will be populated later in _initialize_room_npcs
            # (don't set room.npcs here, it will be replaced with actual NPC objects)

            # Load locked exits (legacy system)
            if 'locked_exits' in room_data:
                room.locked_exits = room_data['locked_exits']
                self.logger.info(f"[DOOR] Loaded locked_exits for room '{room_id}': {list(room.locked_exits.keys())}")
                for direction, lock_info in room.locked_exits.items():
                    self.logger.info(f"[DOOR]   - {direction}: requires '{lock_info.get('required_key')}'")

            # Load barriers (new unified system)
            if 'barriers' in room_data:
                room.barriers = room_data['barriers']
                self.logger.info(f"[BARRIER] Loaded barriers for room '{room_id}': {list(room.barriers.keys())}")
                for direction, barrier_info in room.barriers.items():
                    barrier_id = barrier_info.get('barrier_id')
                    locked = barrier_info.get('locked', True)
                    self.logger.info(f"[BARRIER]   - {direction}: barrier_id='{barrier_id}', locked={locked}")

            # Store raw data for NPC and item references
            room._raw_data = room_data

            self.rooms[room_id] = room

    def _create_areas(self, areas_data: Dict):
        """Create area objects from data."""
        for area_id, area_data in areas_data.items():
            area = Area(
                area_id=area_data.get('id', area_id),
                name=area_data.get('name', 'Unknown Area'),
                description=area_data.get('description', 'A mysterious area.')
            )

            # Add rooms to area based on two methods:
            # 1. If area_data has explicit 'rooms' list, use that
            if 'rooms' in area_data:
                for room_id in area_data['rooms']:
                    if room_id in self.rooms:
                        area.add_room(self.rooms[room_id])
            else:
                # 2. Otherwise, find rooms by their area_id field
                for room_id, room in self.rooms.items():
                    # Get area_id from room's raw data
                    room_area_id = getattr(room, '_raw_data', {}).get('area_id')
                    if room_area_id == area_id:
                        area.add_room(room)

            self.areas[area_id] = area

    def _setup_connections_from_rooms(self, rooms_data: Dict):
        """Setup connections between rooms from room exit data."""
        for room_id, room_data in rooms_data.items():
            if room_id not in self.rooms:
                continue

            room = self.rooms[room_id]
            exits = room_data.get('exits', {})

            for direction, target_room_id in exits.items():
                if target_room_id in self.rooms:
                    from .exit import Exit
                    exit_obj = Exit(target_room_id, direction)
                    room.add_exit(direction, exit_obj)

    def _load_items(self, items_data: Dict):
        """Load item definitions."""
        # For now, just store the data
        # Items will be instantiated when needed
        self.items = items_data

    def _load_npcs(self, npcs_data: Dict):
        """Load NPC definitions."""
        # Store the raw NPC data for game engine use
        self.npcs = npcs_data
        self.logger.info(f"Loaded {len(npcs_data)} NPC definitions")

        # Log quest-giver NPCs
        quest_givers = [npc_id for npc_id, npc_data in npcs_data.items() if npc_data.get('type') == 'quest_giver']
        if quest_givers:
            self.logger.info(f"Quest-giver NPCs: {', '.join(quest_givers)}")

    def _load_barriers(self, barriers_data: Dict):
        """Load barrier definitions from barriers.json."""
        self.barriers = barriers_data
        self.logger.info(f"Loaded {len(barriers_data)} barrier definitions")

        # Log barrier types
        barrier_types = {}
        for barrier_id, barrier_data in barriers_data.items():
            barrier_type = barrier_data.get('type', 'unknown')
            barrier_types[barrier_type] = barrier_types.get(barrier_type, 0) + 1

        self.logger.info(f"Barrier types: {', '.join(f'{k}={v}' for k, v in barrier_types.items())}")

    def _initialize_room_items(self, rooms_data: Dict):
        """Initialize items in rooms from room data."""
        items_placed = 0

        for room_id, room_data in rooms_data.items():
            if 'items' not in room_data:
                continue

            items_list = room_data['items']
            if not items_list:
                continue

            self.logger.debug(f"[ITEMS] Processing room '{room_id}' with {len(items_list)} items, type={type(items_list)}")

            for item_entry in items_list:
                self.logger.debug(f"[ITEMS]   Processing item_entry: {item_entry}, type={type(item_entry)}")

                # Handle both dict format {"item_id": "...", "quantity": N} and string format
                if isinstance(item_entry, dict):
                    item_id = item_entry.get('item_id')
                    quantity = item_entry.get('quantity', 1)
                    self.logger.debug(f"[ITEMS]   Dict format: item_id='{item_id}', quantity={quantity}")
                else:
                    # Old format: just a string item_id
                    item_id = item_entry
                    quantity = 1
                    self.logger.debug(f"[ITEMS]   String format: item_id='{item_id}'")

                if not item_id:
                    self.logger.warning(f"Invalid item entry in room '{room_id}': {item_entry}")
                    continue

                # Look up the full item data
                if item_id in self.items:
                    item_data = self.items[item_id].copy()

                    # IMPORTANT: Ensure the item has an 'id' field for inventory checking
                    if 'id' not in item_data:
                        item_data['id'] = item_id

                    # Add item to the room through game engine's item manager
                    if self.game_engine and hasattr(self.game_engine, 'item_manager'):
                        # Add the item 'quantity' times
                        for _ in range(quantity):
                            self.game_engine.item_manager.add_item_to_room(room_id, item_data)
                            items_placed += 1
                        self.logger.info(f"[DOOR] Placed {quantity}x item '{item_id}' ({item_data.get('name', item_id)}) with id='{item_data.get('id')}' in room '{room_id}'")
                    else:
                        self.logger.warning(f"Cannot place item '{item_id}' in room '{room_id}' - item manager not available")
                else:
                    self.logger.warning(f"Item '{item_id}' referenced in room '{room_id}' not found in items.json")

        self.logger.info(f"Initialized {items_placed} items in rooms")

    def _initialize_room_npcs(self, rooms_data: Dict):
        """Initialize NPCs in rooms from room data."""
        from ..npcs.npc import NPC
        npcs_placed = 0

        for room_id, room_data in rooms_data.items():
            if 'npcs' not in room_data:
                continue

            npc_ids = room_data['npcs']
            if not npc_ids:
                continue

            room = self.rooms.get(room_id)
            if not room:
                self.logger.warning(f"Room '{room_id}' not found in self.rooms, skipping NPCs")
                continue

            # Clear the string list and replace with actual NPC objects
            room.npcs = []

            for npc_id in npc_ids:
                # Look up the full NPC data
                if npc_id in self.npcs:
                    npc_data = self.npcs[npc_id]

                    # Get description (check long_description first, then description)
                    description = npc_data.get('long_description') or npc_data.get('description', 'A mysterious figure.')

                    # Create NPC object
                    npc = NPC(
                        npc_id=npc_data.get('id', npc_id),
                        name=npc_data.get('name', 'Unknown NPC'),
                        description=description
                    )

                    # Set additional properties
                    npc.room_id = room_id
                    if 'type' in npc_data:
                        npc.npc_type = npc_data['type']
                    if 'dialogue' in npc_data:
                        npc.dialogue = npc_data.get('dialogue', {})
                    if 'quests' in npc_data:
                        npc.quests = npc_data['quests']

                    # Add NPC object to room
                    room.npcs.append(npc)
                    npcs_placed += 1
                else:
                    self.logger.warning(f"NPC '{npc_id}' referenced in room '{room_id}' not found in self.npcs")

        self.logger.info(f"Initialized {npcs_placed} NPCs in rooms")

    def _create_default_world(self):
        """Create a minimal default world if loading fails."""
        self.logger.warning("Creating default world due to load failure")

        # Create a basic room with generic naming
        default_room = Room(
            room_id="default_starting_room",
            title="Starting Location",
            description="A basic starting location. This room was created as a fallback."
        )
        default_room.is_safe = True
        default_room.is_starting_room = True
        self.rooms["default_starting_room"] = default_room

        # Create a default area
        default_area = Area(
            area_id="default_area",
            name="Default Area",
            description="A basic area created as fallback."
        )
        default_area.add_room(default_room)
        self.areas["default_area"] = default_area

    def get_room(self, room_id: str) -> Optional[Room]:
        """Get a room by its ID."""
        return self.rooms.get(room_id)

    def get_area(self, area_id: str) -> Optional[Area]:
        """Get an area by its ID."""
        return self.areas.get(area_id)

    def get_all_rooms(self) -> List[Room]:
        """Get all rooms in the world."""
        return list(self.rooms.values())

    def get_all_areas(self) -> List[Area]:
        """Get all areas in the world."""
        return list(self.areas.values())

    async def update_world(self):
        """Update world state for one tick - async version."""
        try:
            # Update all areas
            for area in self.areas.values():
                await self._update_area(area)

            # Update all rooms
            for room in self.rooms.values():
                await self._update_room(room)

        except Exception as e:
            self.logger.error(f"Error updating world: {e}")

    async def _update_area(self, area: Area):
        """Update a single area."""
        # Area-level updates (weather, events, etc.)
        pass

    async def _update_room(self, room: Room):
        """Update a single room."""
        # Room-level updates (NPCs, items, etc.)
        await self._update_room_npcs(room)
        await self._update_room_items(room)

    async def _update_room_npcs(self, room: Room):
        """Update NPCs in a room."""
        for npc in room.npcs:
            if hasattr(npc, 'update'):
                # If NPC has async update, await it
                if asyncio.iscoroutinefunction(npc.update):
                    await npc.update()
                else:
                    npc.update()

    async def _update_room_items(self, room: Room):
        """Update items in a room."""
        # Handle item decay, respawning, etc.
        pass

    def get_starting_room(self) -> Optional[Room]:
        """Get the default starting room for new players."""
        starting_room_id = self.get_default_starting_room()
        return self.get_room(starting_room_id) if starting_room_id else None

    def get_default_starting_room(self) -> Optional[str]:
        """Get the default starting room ID for new players."""
        # Look for world-specific configuration or metadata
        if hasattr(self, 'world_config') and self.world_config.get('starting_room'):
            room_id = self.world_config['starting_room']
            if self.get_room(room_id):
                return room_id

        # Look for a room marked as a starting room
        for room_id, room in self.rooms.items():
            if hasattr(room, 'is_starting_room') and room.is_starting_room:
                return room_id

        # Look for safe rooms as potential starting points
        for room_id, room in self.rooms.items():
            if hasattr(room, 'is_safe') and room.is_safe:
                return room_id

        # Fall back to any available room
        if self.rooms:
            return next(iter(self.rooms.keys()))
        return None

    def find_rooms_by_area(self, area_id: str) -> List[Room]:
        """Find all rooms in a specific area."""
        area = self.get_area(area_id)
        if area:
            return area.get_all_rooms()
        return []

    def get_room_count(self) -> int:
        """Get the total number of rooms."""
        return len(self.rooms)

    def get_area_count(self) -> int:
        """Get the total number of areas."""
        return len(self.areas)

    async def save_world_state(self):
        """Save current world state (for dynamic content)."""
        # This would save things like:
        # - Item positions
        # - NPC states
        # - Dynamic room changes
        pass

    def _build_world_graph_from_rooms(self, rooms_data: Dict):
        """Build the world navigation graph from room exit data."""
        # Add all rooms to the graph
        for room_id in self.rooms:
            self.world_graph.add_room(room_id)

        # Add connections as graph edges from room exits
        for room_id, room_data in rooms_data.items():
            if room_id not in self.rooms:
                continue

            exits = room_data.get('exits', {})
            for direction, target_room_id in exits.items():
                if target_room_id in self.rooms:
                    # Create graph edge
                    edge = GraphEdge(
                        from_room=room_id,
                        to_room=target_room_id,
                        direction=direction,
                        edge_type=EdgeType.NORMAL,
                        weight=1.0
                    )
                    self.world_graph.add_edge(edge)

            # IMPORTANT: Also add locked exits to the graph so they can be checked during movement
            # The movement command will check if they're locked and handle key logic
            locked_exits = room_data.get('locked_exits', {})
            if locked_exits:
                self.logger.info(f"[DOOR] Adding {len(locked_exits)} locked exits to graph for room '{room_id}'")
                for direction in locked_exits.keys():
                    # Get the destination from the regular exits
                    target_room_id = exits.get(direction)
                    if target_room_id and target_room_id in self.rooms:
                        # Note: We already added this exit above, just logging
                        self.logger.info(f"[DOOR]   - Locked exit '{direction}' already in graph (points to '{target_room_id}')")
                    else:
                        self.logger.warning(f"[DOOR]   - Locked exit '{direction}' has no matching exit in 'exits'!")

    def find_path(self, start: str, goal: str, character: 'Character' = None) -> Optional[List[str]]:
        """Find a path between two rooms using the world graph."""
        return self.world_graph.find_path_dijkstra(start, goal, character)

    def find_shortest_path(self, start: str, goal: str, character: 'Character' = None) -> Optional[List[str]]:
        """Find the shortest path between two rooms."""
        return self.world_graph.find_path_astar(start, goal, character)

    def get_room_neighbors(self, room_id: str, character: 'Character' = None) -> List[str]:
        """Get all rooms directly connected to this room."""
        edges = self.world_graph.get_neighbors(room_id, character)
        return [edge.to_room for edge in edges]

    def get_exits_from_room(self, room_id: str, character: 'Character' = None) -> Dict[str, str]:
        """Get available exits from a room with their directions."""
        exits = {}
        edges = self.world_graph.get_neighbors(room_id, character)
        for edge in edges:
            if edge.direction:
                exits[edge.direction] = edge.to_room
        return exits

    def can_travel(self, from_room: str, to_room: str, character: 'Character' = None) -> bool:
        """Check if travel between two rooms is possible."""
        edges = self.world_graph.get_neighbors(from_room, character)
        return any(edge.to_room == to_room for edge in edges)

    def get_area_rooms_within_distance(self, center: str, distance: int, character: 'Character' = None) -> List[str]:
        """Get all rooms within a certain distance of a center room."""
        return self.world_graph.get_area_rooms(center, distance, character)

    def get_world_stats(self) -> Dict:
        """Get statistics about the world."""
        graph_stats = self.world_graph.get_graph_stats()
        return {
            'areas': len(self.areas),
            'rooms': len(self.rooms),
            'items_defined': len(self.items),
            'npcs_defined': len(self.npcs),
            'graph_edges': graph_stats['edges'],
            'avg_connections_per_room': graph_stats['avg_connections']
        }

    def get_npc_data(self, npc_id: str) -> Optional[Dict]:
        """Get NPC data by ID from preloaded data."""
        return self.npcs.get(npc_id)

    def is_npc_hostile(self, npc_id: str) -> bool:
        """Check if an NPC is hostile using preloaded data."""
        npc_data = self.get_npc_data(npc_id)
        if npc_data:
            return npc_data.get('hostile', False)
        # Default to non-hostile if no data found
        return False

    def get_npc_display_name(self, npc_id: str) -> str:
        """Get the display name for an NPC from preloaded data."""
        npc_data = self.get_npc_data(npc_id)
        if npc_data and 'name' in npc_data:
            return npc_data['name']
        # Fallback to converted ID if no name field
        self.logger.warning(f"NPC {npc_id} not found in loaded NPC data")
        return npc_id.replace('_', ' ')

    async def send_room_description_for_room(self, player_id: int, room_id: str, current_player_id: int, detailed: bool = False):
        """Send the description of a specific room (for looking in a direction).

        Args:
            player_id: ID of the player to send the description to
            room_id: ID of the room to describe
            current_player_id: ID to use for filtering "who is here" (usually same as player_id)
            detailed: Whether to send detailed description
        """
        room = self.get_room(room_id)

        if room:
            # Get effective light level (room base only, player isn't in this room)
            light_level = self.calculate_effective_light_level(room_id)
            dim_factor = light_level_to_factor(light_level)

            if detailed:
                # Send detailed description for look command
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"\n{wrap_color(room.description, RGBColors.BOLD_YELLOW, dim_factor)}{Colors.BOLD_WHITE}"
                )
            else:
                # Send basic description - generate from room title
                basic_desc = self._generate_basic_description(room)
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"\n{wrap_color(basic_desc, RGBColors.BOLD_YELLOW, dim_factor)}{Colors.BOLD_WHITE}"
                )

            # Generate who/what is here
            who_here = self.generate_who_is_here(current_player_id, room_id, dim_factor)
            await self.game_engine.connection_manager.send_message(player_id, f"{who_here}\n")
            items_description = self.game_engine.item_manager.get_room_items_description(room_id, dim_factor)
            await self.game_engine.connection_manager.send_message(player_id, f"{items_description}\n")

            # Show spent ammunition if any
            ammo_description = self.game_engine.combat_system.get_spent_ammo_description(room_id, dim_factor)
            if ammo_description:
                await self.game_engine.connection_manager.send_message(player_id, f"{ammo_description}\n")
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("\nYou can't see anything in that direction.")
            )

    async def send_room_description(self, player_id: int, detailed: bool = False):
        """Send the description of the player's current room."""
        # Get player data through game engine
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room = self.get_room(character['room_id'])

        if room:
            # Get effective light level (room base + player light sources)
            room_id = character['room_id']
            light_level = self.calculate_effective_light_level(room_id)
            dim_factor = light_level_to_factor(light_level)

            if detailed:
                # Send detailed description for look command
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"\n{wrap_color(room.description, RGBColors.BOLD_YELLOW, dim_factor)}{Colors.BOLD_WHITE}"
                )
            else:
                # Send basic description - generate from room title
                basic_desc = self._generate_basic_description(room)
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"\n{wrap_color(basic_desc, RGBColors.BOLD_YELLOW, dim_factor)}{Colors.BOLD_WHITE}"
                )

            # Generate who/what is here
            who_here = self.generate_who_is_here(player_id, character['room_id'], dim_factor)
            await self.game_engine.connection_manager.send_message(player_id, f"{who_here}\n")
            items_description = self.game_engine.item_manager.get_room_items_description(character['room_id'], dim_factor)
            await self.game_engine.connection_manager.send_message(player_id, f"{items_description}\n")

            # Show spent ammunition if any
            ammo_description = self.game_engine.combat_system.get_spent_ammo_description(character['room_id'], dim_factor)
            if ammo_description:
                await self.game_engine.connection_manager.send_message(player_id, f"{ammo_description}\n")
        else:
            if detailed:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("\nYou are in a void...")
                )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("\nYou are in the void.")
                )
            await self.game_engine.connection_manager.send_message(
                player_id,
                wrap_color("There is nobody here.", Colors.MAGENTA) + Colors.BOLD_WHITE
            )
            # In void, there are no items on floor
            await self.game_engine.connection_manager.send_message(
                player_id,
                wrap_color("There is nothing on the floor.", Colors.BOLD_CYAN) + "\n" + Colors.BOLD_WHITE
            )

    def calculate_effective_light_level(self, room_id: str) -> float:
        """Calculate the effective light level in a room.

        Takes into account:
        - Base room light level
        - Lit light sources carried by players in the room

        Args:
            room_id: The room ID

        Returns:
            Effective light level (0.0-1.0), capped at 1.0
        """
        room = self.get_room(room_id)
        if not room:
            return 1.0

        # Start with base room light level
        base_light = getattr(room, '_raw_data', {}).get('light_level', 1.0)
        base_factor = light_level_to_factor(base_light)

        # Add brightness from lit light sources
        additional_light = 0.0

        # Check all players in the room
        for player_id, player_data in self.game_engine.player_manager.get_all_connected_players().items():
            if (player_data.get('character') and
                player_data['character'].get('room_id') == room_id):

                # Check their inventory for lit light sources
                inventory = player_data['character'].get('inventory', [])
                for item in inventory:
                    if (item.get('is_light_source', False) and
                        item.get('is_lit', False)):

                        # Add the brightness from this light source
                        brightness = item.get('properties', {}).get('brightness', 0.5)
                        additional_light += brightness

        # Combine base and additional light, cap at 1.0
        effective_light = min(1.0, base_factor + additional_light)
        return effective_light

    def _generate_basic_description(self, room):
        """Generate a basic description from room title."""
        title = room.title.lower()
        return f"You are in the {title}."

    def generate_who_is_here(self, current_player_id: int, room_id: str, dim_factor: float = 1.0) -> str:
        """Generate description of who/what is in the room.

        Args:
            current_player_id: The player viewing the room
            room_id: The room ID
            dim_factor: Light level dimming factor (0.0-1.0)
        """
        npcs = []
        mobs = []
        other_players = []

        # Get NPCs and mobs from room data - check multiple sources
        room = self.get_room(room_id)

        # Try to get NPCs from the room object
        if room and hasattr(room, 'npcs') and room.npcs:
            # If it's a list of NPC objects
            if hasattr(room.npcs[0], 'name') if room.npcs else False:
                # NPCs are already NPC objects with display names
                for npc in room.npcs:
                    display_name = npc.name
                    # Check hostility using npc_id
                    is_hostile = self.is_npc_hostile(npc.npc_id)

                    if is_hostile:
                        mobs.append(f"a {display_name}")
                    else:
                        npcs.append(display_name)
            else:
                # If it's a list of NPC IDs (legacy support)
                for npc_id in room.npcs:
                    # Get the proper display name from NPC data
                    display_name = self.get_npc_display_name(npc_id)

                    # Check if this NPC has data with hostility flag
                    is_hostile = self.is_npc_hostile(npc_id)

                    if is_hostile:
                        mobs.append(f"a {display_name}")
                    else:
                        npcs.append(display_name)

        # Get other players in the same room (exclude invisible players)
        for player_id, player_data in self.game_engine.player_manager.get_all_connected_players().items():
            if (player_id != current_player_id and
                player_data.get('character') and
                player_data['character'].get('room_id') == room_id):
                # Check if player is invisible
                character = player_data['character']
                active_effects = character.get('active_effects', [])
                is_invisible = any(
                    effect.get('effect') in ['invisible', 'invisibility']
                    for effect in active_effects
                )
                # Only show player if they're not invisible
                if not is_invisible:
                    username = player_data.get('username', f'player_{player_id}')
                    other_players.append(username)

        # Build the description
        entities = []

        # Add NPCs first
        if npcs:
            if len(npcs) == 1:
                entities.append(wrap_color(f"{npcs[0]} is here.", RGBColors.BOLD_GREEN, dim_factor))
            else:
                npc_list = ", ".join(npcs[:-1]) + f" and {npcs[-1]}"
                entities.append(wrap_color(f"{npc_list} are here.", RGBColors.BOLD_GREEN, dim_factor))

        # Add spawned mobs from gong rings
        spawned_mobs = []
        if room_id in self.game_engine.room_mobs:
            for mob in self.game_engine.room_mobs[room_id]:
                mob_name = mob.get('name', 'unknown creature')
                spawned_mobs.append(f"a {mob_name}")

        # Combine regular mobs and spawned mobs
        all_mobs = mobs + spawned_mobs
        if all_mobs:
            if len(all_mobs) == 1:
                entities.append(wrap_color(f"There is {all_mobs[0]} here.", RGBColors.BOLD_GREEN, dim_factor))
            else:
                mob_list = ", ".join(all_mobs[:-1]) + f" and {all_mobs[-1]}"
                entities.append(wrap_color(f"There are {mob_list} here.", RGBColors.BOLD_GREEN, dim_factor))

        # Add other players
        if other_players:
            if len(other_players) == 1:
                entities.append(wrap_color(f"{other_players[0]} is here.", RGBColors.BOLD_MAGENTA, dim_factor))
            elif len(other_players) == 2:
                entities.append(wrap_color(f"{other_players[0]} and {other_players[1]} are here with you.", RGBColors.BOLD_MAGENTA, dim_factor))
            else:
                player_list = ", ".join(other_players[:-1]) + f" and {other_players[-1]}"
                entities.append(wrap_color(f"{player_list} are here with you.", RGBColors.BOLD_MAGENTA, dim_factor))

        # Return combined description or default
        if entities:
            return "\n".join(entities) + Colors.BOLD_WHITE
        else:
            # In very dark rooms, use dimmed magenta
            return wrap_color("There is nobody here.", RGBColors.MAGENTA, dim_factor) + Colors.BOLD_WHITE

    async def handle_look_at_target(self, player_id: int, target_name: str):
        """Handle looking at specific targets like NPCs and mobs."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Check for spawned mobs first
        if room_id in self.game_engine.room_mobs:
            for mob in self.game_engine.room_mobs[room_id]:
                mob_name = mob.get('name', '').lower()
                if self._matches_target(target_name.lower(), mob_name):
                    # Found a spawned mob
                    description = mob.get('description', f"This is {mob['name']}.")

                    # Add health status for hostile mobs
                    health_status = ""
                    if mob.get('type') == 'hostile':
                        # Try current_hit_points first, fallback to health for compatibility
                        health = mob.get('current_hit_points', mob.get('health', 100))
                        max_health = mob.get('max_hit_points', mob.get('max_health', 100))
                        health_percent = (health / max_health) * 100

                        if health_percent >= 90:
                            health_status = f"\n{mob['name']} appears to be in excellent health."
                        elif health_percent >= 70:
                            health_status = f"\n{mob['name']} has some minor wounds."
                        elif health_percent >= 50:
                            health_status = f"\n{mob['name']} is moderately wounded."
                        elif health_percent >= 25:
                            health_status = f"\n{mob['name']} is badly wounded."
                        else:
                            health_status = f"\n{mob['name']} is critically wounded."

                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        description + health_status
                    )
                    return

        # Check for room NPCs
        room = self.get_room(room_id)
        if room:
            room_npcs = []

            # Get NPCs from room data
            if hasattr(room, 'npcs') and room.npcs:
                room_npcs.extend(room.npcs)
            if hasattr(room, '_raw_data') and room._raw_data and 'npcs' in room._raw_data:
                room_npcs.extend(room._raw_data['npcs'])

            # Check each NPC
            for npc_id in room_npcs:
                npc_data = self.get_npc_data(npc_id)
                if npc_data:
                    npc_name = npc_data.get('name', npc_id).lower()

                    # Check name and keywords
                    if (self._matches_target(target_name.lower(), npc_name) or
                        self._matches_npc_keywords(target_name.lower(), npc_data)):

                        # Get description - prefer long_description, fall back to description or short_description
                        description = (npc_data.get('long_description') or
                                     npc_data.get('description') or
                                     npc_data.get('short_description') or
                                     f"This is {npc_data.get('name', npc_id)}.")

                        await self.game_engine.connection_manager.send_message(player_id, description)
                        return

        # Check for other players
        for other_player_id, other_player_data in self.game_engine.player_manager.get_all_connected_players().items():
            if (other_player_id != player_id and
                other_player_data.get('character') and
                other_player_data['character'].get('room_id') == room_id):

                other_username = other_player_data.get('username', f'player_{other_player_id}')
                if self._matches_target(target_name.lower(), other_username.lower()):
                    await self.game_engine.connection_manager.send_message(player_id,
                        f"You look at {other_username}. They are another adventurer like yourself.")
                    return

        # Target not found
        await self.game_engine.connection_manager.send_message(player_id, f"You don't see '{target_name}' here.")

    def _matches_target(self, search_term: str, target_name: str) -> bool:
        """Check if search term matches target name (supports partial matching)."""
        # Exact match
        if search_term == target_name:
            return True

        # Partial match from beginning of words
        words = target_name.split()
        for word in words:
            if word.startswith(search_term):
                return True

        # Check if search term is contained in the full name
        if search_term in target_name:
            return True

        return False

    def _matches_npc_keywords(self, search_term: str, npc_data: dict) -> bool:
        """Check if search term matches any NPC keywords."""
        keywords = npc_data.get('keywords', [])
        for keyword in keywords:
            if self._matches_target(search_term, keyword.lower()):
                return True
        return False

    async def handle_ring_gong(self, player_id: int, room_id: str):
        """Ring the gong in an arena and spawn a random mob based on arena configuration."""
        import random
        import json
        import time

        # Get arena configuration for this room
        arena_config = self.game_engine.config_manager.get_arena_by_room(room_id)
        if not arena_config:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("There is no gong here to ring.")
            )
            return

        # Check cooldown
        cooldown_seconds = arena_config.get('gong_cooldown', 0)
        if cooldown_seconds > 0:
            last_use = self.game_engine.gong_cooldowns.get(room_id, 0)
            time_since_last = time.time() - last_use
            if time_since_last < cooldown_seconds:
                remaining = int(cooldown_seconds - time_since_last)
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"The gong is still resonating from its last use. Wait {remaining} more seconds.")
                )
                return

        # Check max active mobs in arena
        max_mobs = arena_config.get('max_active_mobs', 3)
        current_mobs = len(self.game_engine.room_mobs.get(room_id, []))
        if current_mobs >= max_mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The arena is already crowded with {current_mobs} creatures. Defeat some before summoning more!")
            )
            return

        # Get mob pool from arena configuration
        mob_pool = arena_config.get('mob_pool', [])
        if not mob_pool:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("The gong rings out, but no creatures answer its call.")
            )
            self.logger.error(f"[ARENA] Arena {arena_config.get('arena_id')} has no mob pool configured")
            return

        # Select a random mob from the pool using weights
        total_weight = sum(entry.get('weight', 1) for entry in mob_pool)
        roll = random.uniform(0, total_weight)
        cumulative = 0
        selected_mob_id = None

        for entry in mob_pool:
            cumulative += entry.get('weight', 1)
            if roll <= cumulative:
                selected_mob_id = entry['id']
                break

        if not selected_mob_id:
            selected_mob_id = mob_pool[0]['id']  # Fallback to first

        # Load the monster data
        monsters = self.game_engine._load_all_monsters()
        if not monsters or selected_mob_id not in monsters:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("The gong rings out, but something went wrong with the ancient magic...")
            )
            self.logger.error(f"[ARENA] Monster {selected_mob_id} not found in monster data")
            return

        monster = monsters[selected_mob_id]
        self.logger.info(f"[ARENA] Selected {monster.get('name')} from pool of {len(mob_pool)} options")

        # Send atmospheric message
        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message("You strike the bronze gong with your fist. The deep, resonant tone echoes through the arena, "
                        "reverberating off the ancient stone walls. The sound seems to call forth something from the depths...")
        )

        # Add a brief delay for dramatic effect
        await asyncio.sleep(2)

        # Announce the mob spawn
        mob_name = monster.get('name', 'Unknown Creature')
        await self.game_engine.player_manager.notify_room_except_player(
            room_id, player_id,
            monster_spawn(f"\nSuddenly, a {mob_name} emerges from the shadows, drawn by the gong's call! "
                         f"It looks ready for battle!")
        )

        # Also send the message to the player who rang the gong
        await self.game_engine.connection_manager.send_message(
            player_id,
            monster_spawn(f"\nSuddenly, a {mob_name} emerges from the shadows, drawn by the gong's call! "
                         f"It looks ready for battle!")
        )

        # Use centralized spawn logic
        spawned_mob = self.game_engine.spawn_mob(
            room_id,
            monster.get('id', 'unknown'),
            monster,
            spawned_by_gong=True,
            arena_id=arena_config.get('arena_id')
        )

        # Record cooldown timestamp
        self.game_engine.gong_cooldowns[room_id] = time.time()

        self.logger.info(f"[ARENA] {mob_name} spawned in {room_id} by player {player_id} (arena: {arena_config.get('arena_id')})")
        self.logger.info(f"[ARENA DEBUG] Spawned mob loot_table: {spawned_mob.get('loot_table', 'ERROR')}")