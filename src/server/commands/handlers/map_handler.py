"""Map command handler for displaying area and room maps."""

from collections import deque
from ..base_handler import BaseCommandHandler


class MapCommandHandler(BaseCommandHandler):
    """Handles map-related commands."""

    async def handle_map_command(self, player_id: int, character: dict, params: str):
        """Show map of areas and rooms with their connections.

        Usage: map [area_id]
        """
        world_manager = self.world_manager

        # If params provided, show specific area
        if params:
            area_id = params.strip().lower()
            area = world_manager.areas.get(area_id)

            if not area:
                await self.send_message(
                    player_id,
                    f"Area '{area_id}' not found. Available areas: {', '.join(world_manager.areas.keys())}"
                )
                return

            # Show detailed map for this area
            await self._show_area_map(player_id, area)
        else:
            # Show overview of all areas
            await self._show_all_areas_map(player_id)

    async def _show_all_areas_map(self, player_id: int):
        """Show overview of all areas."""
        world_manager = self.world_manager

        lines = ["=== World Map ===\n"]

        for area_id, area in sorted(world_manager.areas.items()):
            room_count = len(area.rooms)
            lines.append(f"{area.name} ({area_id})")
            lines.append(f"  Description: {area.description}")
            lines.append(f"  Rooms: {room_count}")
            lines.append(f"  Level Range: {area.level_range[0]}-{area.level_range[1]}")
            lines.append("")

        lines.append("Use 'map <area_id>' to see detailed room connections for an area")

        await self.send_message(player_id, "\n".join(lines))

    async def _show_area_map(self, player_id: int, area):
        """Show detailed ASCII graphical map of an area with room connections."""
        world_manager = self.world_manager

        lines = [f"=== {area.name} ==="]
        lines.append(f"{area.description}\n")

        # Generate ASCII map
        ascii_map = self._generate_ascii_map(area, world_manager, player_id)
        lines.extend(ascii_map)

        await self.send_message(player_id, "\n".join(lines))

    def _generate_ascii_map(self, area, world_manager, player_id):
        """Generate ASCII graphical map of an area."""
        # Check if we should filter by explored rooms
        show_only_explored = self.config_manager.get_setting('world', 'map_shows_only_explored', default=True)

        # Get player's visited rooms (as a list for JSON serialization)
        visited_rooms = []
        if show_only_explored:
            player_data = self.player_manager.get_player_data(player_id)
            if player_data and player_data.get('character'):
                character = player_data['character']
                visited_rooms = character.get('visited_rooms', [])
                # Always include current room
                current_room = character.get('room_id')
                if current_room and current_room not in visited_rooms:
                    visited_rooms.append(current_room)

        # Direction mappings (x, y)
        direction_offsets = {
            'north': (0, -2),
            'south': (0, 2),
            'east': (3, 0),
            'west': (-3, 0),
            'northeast': (3, -2),
            'northwest': (-3, -2),
            'southeast': (3, 2),
            'southwest': (-3, 2),
            'up': (0, 0),  # Special handling needed
            'down': (0, 0),  # Special handling needed
        }

        # Filter rooms based on visited status if config enabled
        displayable_rooms = {}
        for room_id, room in area.rooms.items():
            if not show_only_explored or room_id in visited_rooms:
                displayable_rooms[room_id] = room

        # Layout rooms on a grid
        room_positions = {}  # room_id -> (x, y)
        visited = set()

        # Start with first room
        if not displayable_rooms:
            return ["No explored rooms in this area yet. Explore to reveal the map!"]

        # Choose best starting room: player's current room, or room with most connections
        player_data = self.player_manager.get_player_data(player_id)
        start_room_id = None

        # Try player's current room first
        if player_data and player_data.get('character'):
            current_room = player_data['character'].get('room_id')
            if current_room in displayable_rooms:
                start_room_id = current_room

        # If player not in this area, find room with most connections
        if not start_room_id:
            max_connections = 0
            for room_id in displayable_rooms.keys():
                room_data = world_manager.rooms_data.get(room_id, {})
                exits = room_data.get('exits', {})
                connection_count = len(exits)
                if connection_count > max_connections:
                    max_connections = connection_count
                    start_room_id = room_id

        # Fallback to first room if still not found
        if not start_room_id:
            start_room_id = list(displayable_rooms.keys())[0]

        queue = deque([(start_room_id, 0, 0)])  # (room_id, x, y)
        room_positions[start_room_id] = (0, 0)
        visited.add(start_room_id)

        # BFS to position all rooms
        while queue:
            room_id, x, y = queue.popleft()

            # Get exits from raw room data
            room_data = world_manager.rooms_data.get(room_id, {})
            exits = room_data.get('exits', {})

            for direction, dest_id in exits.items():
                # Skip if destination not in displayable rooms
                if dest_id not in displayable_rooms:
                    continue

                # Skip if already positioned
                if dest_id in visited:
                    continue

                # Calculate position based on direction
                dx, dy = direction_offsets.get(direction.lower(), (0, 0))
                new_x, new_y = x + dx, y + dy

                # Handle position conflicts
                conflict_count = 0
                original_pos = (new_x, new_y)
                while (new_x, new_y) in room_positions.values() and conflict_count < 10:
                    # Offset slightly to avoid overlap
                    new_x = original_pos[0] + (conflict_count % 3) - 1
                    new_y = original_pos[1] + (conflict_count // 3)
                    conflict_count += 1

                room_positions[dest_id] = (new_x, new_y)
                visited.add(dest_id)
                queue.append((dest_id, new_x, new_y))

        # Add any unvisited rooms
        for room_id in displayable_rooms:
            if room_id not in room_positions:
                # Place disconnected rooms to the side
                room_positions[room_id] = (len(room_positions) * 3, 10)

        # Find bounds
        if not room_positions:
            return ["No rooms to display."]

        min_x = min(x for x, y in room_positions.values())
        max_x = max(x for x, y in room_positions.values())
        min_y = min(y for x, y in room_positions.values())
        max_y = max(y for x, y in room_positions.values())

        # Create grid (with padding)
        width = max_x - min_x + 20
        height = max_y - min_y + 10

        grid = [[' ' for _ in range(width)] for _ in range(height)]

        # Draw connections first (so they appear under rooms)
        for room_id, (x, y) in room_positions.items():
            gx, gy = x - min_x + 5, y - min_y + 2

            # Get exits from raw room data
            room_data = world_manager.rooms_data.get(room_id, {})
            exits = room_data.get('exits', {})

            for direction, dest_id in exits.items():
                if dest_id not in room_positions:
                    continue

                dest_x, dest_y = room_positions[dest_id]
                dest_gx, dest_gy = dest_x - min_x + 5, dest_y - min_y + 2

                # Draw connections
                dir_lower = direction.lower()

                if dir_lower == 'north' and dest_gy < gy:
                    for i in range(dest_gy + 1, gy):
                        if 0 <= i < height and 0 <= gx < width:
                            grid[i][gx] = '|'
                elif dir_lower == 'south' and dest_gy > gy:
                    for i in range(gy + 1, dest_gy):
                        if 0 <= i < height and 0 <= gx < width:
                            grid[i][gx] = '|'
                elif dir_lower == 'east' and dest_gx > gx:
                    for i in range(gx + 1, dest_gx):
                        if 0 <= gy < height and 0 <= i < width:
                            grid[gy][i] = '-'
                elif dir_lower == 'west' and dest_gx < gx:
                    for i in range(dest_gx + 1, gx):
                        if 0 <= gy < height and 0 <= i < width:
                            grid[gy][i] = '-'
                elif dir_lower == 'northeast' and dest_gx > gx and dest_gy < gy:
                    # Draw diagonal / going up-right
                    steps = min(dest_gx - gx, gy - dest_gy)
                    for i in range(1, steps):
                        new_x = gx + i
                        new_y = gy - i
                        if 0 <= new_y < height and 0 <= new_x < width:
                            grid[new_y][new_x] = '/'
                elif dir_lower == 'southeast' and dest_gx > gx and dest_gy > gy:
                    # Draw diagonal \ going down-right
                    steps = min(dest_gx - gx, dest_gy - gy)
                    for i in range(1, steps):
                        new_x = gx + i
                        new_y = gy + i
                        if 0 <= new_y < height and 0 <= new_x < width:
                            grid[new_y][new_x] = '\\'
                elif dir_lower == 'southwest' and dest_gx < gx and dest_gy > gy:
                    # Draw diagonal / going down-left
                    steps = min(gx - dest_gx, dest_gy - gy)
                    for i in range(1, steps):
                        new_x = gx - i
                        new_y = gy + i
                        if 0 <= new_y < height and 0 <= new_x < width:
                            grid[new_y][new_x] = '/'
                elif dir_lower == 'northwest' and dest_gx < gx and dest_gy < gy:
                    # Draw diagonal \ going up-left
                    steps = min(gx - dest_gx, gy - dest_gy)
                    for i in range(1, steps):
                        new_x = gx - i
                        new_y = gy - i
                        if 0 <= new_y < height and 0 <= new_x < width:
                            grid[new_y][new_x] = '\\'

        # Get player's current room for highlighting
        current_room_id = None
        if player_data and player_data.get('character'):
            current_room_id = player_data['character'].get('room_id')

        # Draw rooms
        for room_id, (x, y) in room_positions.items():
            gx, gy = x - min_x + 5, y - min_y + 2
            room = displayable_rooms[room_id]

            # Determine room marker based on room properties
            room_data = world_manager.rooms_data.get(room_id, {})
            exits = room_data.get('exits', {})

            # Choose marker character
            # Player's current room gets special '@' marker
            if room_id == current_room_id:
                marker = '@'
            elif hasattr(room, 'is_lair') and room.is_lair:
                marker = 'L'
            elif 'up' in exits or 'down' in exits:
                marker = '^'
            else:
                marker = '*'

            # Place room marker
            if 0 <= gy < height and 0 <= gx < width:
                grid[gy][gx] = marker

        # Convert grid to lines
        result = []
        for row in grid:
            line = ''.join(row).rstrip()
            if line:  # Skip empty lines
                result.append(line)

        # Add legend
        result.append("")
        result.append("Legend: @ = you are here, * = room, L = lair, ^ = stairs, | - / \\ = connections")
        if show_only_explored:
            result.append(f"Explored rooms: {len(displayable_rooms)} / {len(area.rooms)}")
        else:
            result.append(f"Total rooms: {len(displayable_rooms)}")

        return result

    def _generate_simple_list_map(self, area, world_manager):
        """Fallback to simple list when area is too large for ASCII map."""
        lines = ["Area too large for graphical map. Showing list view:\n"]

        sorted_rooms = sorted(area.rooms.values(), key=lambda r: r.room_id)

        for room in sorted_rooms:
            # Get exits from raw room data
            room_data = world_manager.rooms_data.get(room.room_id, {})
            exits = room_data.get('exits', {})
            locked_exits = room_data.get('locked_exits', {})

            lines.append(f"  [{room.room_id}] {room.title}")

            if exits:
                exit_list = []
                for direction, dest_id in sorted(exits.items()):
                    dest_room = world_manager.get_room(dest_id)
                    if dest_room:
                        locked_marker = " (locked)" if direction in locked_exits else ""
                        exit_list.append(f"{direction} -> {dest_room.title}{locked_marker}")

                if exit_list:
                    lines.append(f"    Exits: {', '.join(exit_list)}")
            else:
                lines.append("    Exits: none")

            lines.append("")

        return lines
