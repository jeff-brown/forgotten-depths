"""Manages the game world state and updates."""

import asyncio
from typing import Dict, Optional, List

from ...persistence.world_loader import WorldLoader
from .room import Room
from .area import Area
from .graph import WorldGraph, GraphEdge, EdgeType
from ...utils.logger import get_logger


class WorldManager:
    """Manages the game world, areas, rooms, and their states."""

    def __init__(self, game_engine=None):
        """Initialize the world manager."""
        self.areas: Dict[str, Area] = {}
        self.rooms: Dict[str, Room] = {}
        self.npcs: Dict[str, 'NPC'] = {}
        self.items: Dict[str, 'Item'] = {}
        self.world_graph = WorldGraph()
        self.logger = get_logger()
        self.world_loader = WorldLoader()
        self.game_engine = game_engine

    def load_world(self):
        """Load the world data from files."""
        self.logger.info("Loading world data...")

        try:
            # Load raw data from JSON files
            areas_data = self.world_loader.load_areas()
            rooms_data = self.world_loader.load_rooms()
            items_data = self.world_loader.load_items()
            npcs_data = self.world_loader.load_npcs()
            connections_data = self.world_loader.load_connections()

            # Create room objects
            self._create_rooms(rooms_data)

            # Create area objects
            self._create_areas(areas_data)

            # Setup room connections
            self._setup_connections(connections_data)

            # Build world graph
            self._build_world_graph(connections_data)

            # Load items and NPCs
            self._load_items(items_data)
            self._load_npcs(npcs_data)

            # Validate graph
            issues = self.world_graph.validate_graph()
            if issues:
                self.logger.warning(f"Graph validation issues: {issues}")

            graph_stats = self.world_graph.get_graph_stats()
            self.logger.info(f"World loaded: {len(self.areas)} areas, {len(self.rooms)} rooms, {graph_stats['edges']} connections")

        except Exception as e:
            self.logger.error(f"Failed to load world: {e}")
            # Create a basic default world
            self._create_default_world()

    def _create_rooms(self, rooms_data: Dict):
        """Create room objects from data."""
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

            # Add rooms to area
            if 'rooms' in area_data:
                for room_id in area_data['rooms']:
                    if room_id in self.rooms:
                        area.add_room(self.rooms[room_id])

            self.areas[area_id] = area

    def _setup_connections(self, connections_data: Dict):
        """Setup connections between rooms."""
        # Process basic room connections
        rooms_connections = connections_data.get('rooms', {})

        for room_id, exits in rooms_connections.items():
            if room_id not in self.rooms:
                continue

            room = self.rooms[room_id]
            for direction, target_room_id in exits.items():
                if target_room_id in self.rooms:
                    from .exit import Exit
                    exit_obj = Exit(target_room_id, direction)
                    room.add_exit(direction, exit_obj)

        # Process enhanced connections
        enhanced_connections = connections_data.get('enhanced_connections', [])

        for connection in enhanced_connections:
            from_room_id = connection.get('from')
            to_room_id = connection.get('to')
            direction = connection.get('direction')

            if (from_room_id in self.rooms and
                to_room_id in self.rooms and
                direction):

                from_room = self.rooms[from_room_id]
                from .exit import Exit
                exit_obj = Exit(to_room_id, direction)

                # Add any special properties to the exit
                if 'type' in connection:
                    exit_obj.connection_type = connection['type']
                if 'weight' in connection:
                    exit_obj.weight = connection['weight']
                if 'locked' in connection:
                    exit_obj.locked = connection['locked']
                if 'key' in connection:
                    exit_obj.key = connection['key']
                if 'requirements' in connection:
                    exit_obj.requirements = connection['requirements']
                if 'description' in connection:
                    exit_obj.description = connection['description']

                from_room.add_exit(direction, exit_obj)

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

    def _build_world_graph(self, connections_data: Dict):
        """Build the world navigation graph."""
        # Add all rooms to the graph
        for room_id in self.rooms:
            self.world_graph.add_room(room_id)

        # Add connections as graph edges
        rooms_connections = connections_data.get('rooms', {})
        for room_id, exits in rooms_connections.items():
            if room_id not in self.rooms:
                continue

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

        # Check for enhanced connection data with edge types
        if 'enhanced_connections' in connections_data:
            enhanced = connections_data['enhanced_connections']
            for conn in enhanced:
                edge = GraphEdge(
                    from_room=conn['from'],
                    to_room=conn['to'],
                    direction=conn.get('direction', ''),
                    edge_type=EdgeType(conn.get('type', 'normal')),
                    weight=conn.get('weight', 1.0),
                    requirements=conn.get('requirements', []),
                    is_locked=conn.get('locked', False),
                    key_required=conn.get('key', None),
                    hidden=conn.get('hidden', False),
                    description=conn.get('description', '')
                )
                self.world_graph.add_edge(edge)

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
        return npc_id.replace('_', ' ')

    async def send_room_description(self, player_id: int, detailed: bool = False):
        """Send the description of the player's current room."""
        # Get player data through game engine
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room = self.get_room(character['room_id'])

        if room:
            if detailed:
                # Send detailed description for look command
                await self.game_engine.connection_manager.send_message(player_id, f"\n{room.description}")
            else:
                # Send basic description - generate from room title
                basic_desc = self._generate_basic_description(room)
                await self.game_engine.connection_manager.send_message(player_id, f"\n{basic_desc}\n")

            # Generate who/what is here
            who_here = self.generate_who_is_here(player_id, character['room_id'])
            await self.game_engine.connection_manager.send_message(player_id, f"{who_here}\n")
            items_description = self.game_engine.item_manager.get_room_items_description(character['room_id'])
            await self.game_engine.connection_manager.send_message(player_id, f"{items_description}\n")
        else:
            if detailed:
                await self.game_engine.connection_manager.send_message(player_id, "\nYou are in a void...")
            else:
                await self.game_engine.connection_manager.send_message(player_id, "\nYou are in the void.")
            await self.game_engine.connection_manager.send_message(player_id, "There is nobody here.")
            # In void, there are no items on floor
            await self.game_engine.connection_manager.send_message(player_id, "There is nothing on the floor.\n")

    def _generate_basic_description(self, room):
        """Generate a basic description from room title."""
        title = room.title.lower()
        return f"You are in the {title}."

    def generate_who_is_here(self, current_player_id: int, room_id: str) -> str:
        """Generate description of who/what is in the room."""
        npcs = []
        mobs = []
        other_players = []

        # Get NPCs and mobs from room data - check multiple sources
        room = self.get_room(room_id)
        room_npcs = []

        # Try to get NPCs from the room object
        if room and hasattr(room, 'npcs') and room.npcs:
            # If it's a list of NPC objects
            if hasattr(room.npcs[0], 'name') if room.npcs else False:
                room_npcs = [npc.name for npc in room.npcs]
            else:
                # If it's a list of NPC IDs
                room_npcs = room.npcs

        # Also try to get NPCs from raw data if available
        if hasattr(room, '_raw_data') and room._raw_data and 'npcs' in room._raw_data:
            room_npcs.extend(room._raw_data['npcs'])

        # Convert NPC IDs to readable names using preloaded data
        for npc_id in room_npcs:
            # Get the proper display name from NPC data
            display_name = self.get_npc_display_name(npc_id)

            # Check if this NPC has data with hostility flag
            is_hostile = self.is_npc_hostile(npc_id)

            if is_hostile:
                mobs.append(f"a {display_name}")
            else:
                npcs.append(display_name)

        # Get other players in the same room
        for player_id, player_data in self.game_engine.player_manager.get_all_connected_players().items():
            if (player_id != current_player_id and
                player_data.get('character') and
                player_data['character'].get('room_id') == room_id):
                username = player_data.get('username', f'player_{player_id}')
                other_players.append(username)

        # Build the description
        entities = []

        # Add NPCs first
        if npcs:
            if len(npcs) == 1:
                entities.append(f"{npcs[0]} is here.")
            else:
                npc_list = ", ".join(npcs[:-1]) + f" and {npcs[-1]}"
                entities.append(f"{npc_list} are here.")

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
                entities.append(f"There is {all_mobs[0]} here.")
            else:
                mob_list = ", ".join(all_mobs[:-1]) + f" and {all_mobs[-1]}"
                entities.append(f"There are {mob_list} here.")

        # Add other players
        if other_players:
            if len(other_players) == 1:
                entities.append(f"{other_players[0]} is here.")
            elif len(other_players) == 2:
                entities.append(f"{other_players[0]} and {other_players[1]} are here with you.")
            else:
                player_list = ", ".join(other_players[:-1]) + f" and {other_players[-1]}"
                entities.append(f"{player_list} are here with you.")

        # Return combined description or default
        if entities:
            return "\n".join(entities)
        else:
            return "There is nobody here."

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
                        health = mob.get('health', 100)
                        max_health = mob.get('max_health', 100)
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

                    await self.game_engine.connection_manager.send_message(player_id, description + health_status)
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
        """Ring the gong in the arena and spawn a random mob."""
        import random
        import json

        # Load available mobs
        try:
            with open('/home/jeffbr/git/jeff-brown/forgotten-depths/data/npcs/monsters.json', 'r') as f:
                monsters_data = json.load(f)
        except Exception as e:
            await self.game_engine.connection_manager.send_message(player_id, "The gong rings out, but something went wrong with the ancient magic...")
            return

        # Select a random monster
        if not monsters_data:
            await self.game_engine.connection_manager.send_message(player_id, "The gong rings out, but no creatures answer its call.")
            return

        monster = random.choice(monsters_data)

        # Send atmospheric message
        await self.game_engine.connection_manager.send_message(player_id,
            "You strike the bronze gong with your fist. The deep, resonant tone echoes through the arena, "
            "reverberating off the ancient stone walls. The sound seems to call forth something from the depths...")

        # Add a brief delay for dramatic effect
        await asyncio.sleep(2)

        # Announce the mob spawn
        mob_name = monster.get('name', 'Unknown Creature')
        await self.game_engine.player_manager.notify_room_except_player(room_id, player_id,
            f"\nSudenly, a {mob_name} emerges from the shadows, drawn by the gong's call! "
            f"It looks ready for battle!")

        # Also send the message to the player who rang the gong
        await self.game_engine.connection_manager.send_message(player_id,
            f"\nSudenly, a {mob_name} emerges from the shadows, drawn by the gong's call! "
            f"It looks ready for battle!")

        # Actually spawn the mob in the room
        if room_id not in self.game_engine.room_mobs:
            self.game_engine.room_mobs[room_id] = []

        # Create a simple mob instance with the monster data
        spawned_mob = {
            'id': monster.get('id', 'unknown'),
            'name': mob_name,
            'type': 'hostile',
            'description': monster.get('description', f'A fierce {mob_name}'),
            'level': monster.get('level', 1),
            'health': monster.get('health', 100),
            'max_health': monster.get('health', 100),
            'damage': monster.get('damage', '1d4'),  # Dice notation or will use damage_min/damage_max
            'damage_min': monster.get('damage_min', 1),
            'damage_max': monster.get('damage_max', 4),
            'armor_class': monster.get('armor', 0),
            'strength': monster.get('strength', 12),
            'dexterity': monster.get('dexterity', 10),
            'experience_reward': monster.get('experience_reward', 25),
            'gold_reward': monster.get('gold_reward', [0, 5]),
            'loot_table': monster.get('loot_table', []),
            'spawned_by_gong': True
        }

        self.game_engine.room_mobs[room_id].append(spawned_mob)
        self.logger.info(f"[ARENA] {mob_name} spawned in {room_id} by player {player_id}")