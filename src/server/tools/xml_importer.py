"""XML importer for Ether MUD world data."""

import xml.etree.ElementTree as ET
import json
import os
import sys
from typing import Dict, List, Optional
from pathlib import Path

# Add parent directories to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

try:
    from server.game.world.graph import EdgeType
except ImportError:
    # Define EdgeType locally if import fails
    from enum import Enum
    class EdgeType(Enum):
        NORMAL = "normal"
        DOOR = "door"
        HIDDEN = "hidden"


class EtherXMLImporter:
    """Imports Ether MUD XML data into our graph-based system."""

    def __init__(self):
        """Initialize the importer."""
        self.rooms = {}
        self.descriptions = {}
        self.connections = {}
        self.areas = {}

        # Map Ether directions to our system
        self.direction_map = {
            'NORTH': 'north',
            'SOUTH': 'south',
            'EAST': 'east',
            'WEST': 'west',
            'NORTHEAST': 'northeast',
            'NORTHWEST': 'northwest',
            'SOUTHEAST': 'southeast',
            'SOUTHWEST': 'southwest',
            'UP': 'up',
            'DOWN': 'down'
        }

        # Map terrain types to area information
        self.terrain_map = {
            'DUNGEON1': 'dungeon_level_1',
            'DUNGEON2': 'dungeon_level_2',
            'TOWN': 'town',
            'FOREST': 'forest',
            'MOUNTAIN': 'mountain',
            'CAVE': 'cave',
            'WATER': 'water'
        }

    def parse_room_descriptions(self, desc_file_path: str):
        """Parse room descriptions from XML file."""
        print(f"Parsing room descriptions from {desc_file_path}...")

        try:
            tree = ET.parse(desc_file_path)
            root = tree.getroot()

            # Find all room description entries
            for entry in root.findall('.//entry'):
                room_id_elem = entry.find('int')
                desc_elem = entry.find('string')

                if room_id_elem is not None and desc_elem is not None:
                    room_id = int(room_id_elem.text)
                    description = desc_elem.text.strip() if desc_elem.text else ""

                    # Clean up the description
                    description = description.replace('\n', ' ').replace('  ', ' ')
                    self.descriptions[room_id] = description

            print(f"   ✓ Loaded {len(self.descriptions)} room descriptions")

        except Exception as e:
            print(f"   ✗ Error parsing descriptions: {e}")

    def parse_world_file(self, world_file_path: str):
        """Parse the main world XML file."""
        print(f"Parsing world data from {world_file_path}...")

        try:
            tree = ET.parse(world_file_path)
            root = tree.getroot()

            rooms_element = root.find('__rooms')
            if rooms_element is None:
                print("   ✗ No rooms section found in XML")
                return

            # Parse each room entry
            for entry in rooms_element.findall('entry'):
                room_id_elem = entry.find('int')
                room_elem = entry.find('org.tdod.ether.taimpl.cosmos.DefaultRoom')

                if room_id_elem is not None and room_elem is not None:
                    room_id = int(room_id_elem.text)
                    self._parse_room(room_id, room_elem)

            print(f"   ✓ Loaded {len(self.rooms)} rooms")
            print(f"   ✓ Found {sum(len(exits) for exits in self.connections.values())} connections")

        except Exception as e:
            print(f"   ✗ Error parsing world file: {e}")

    def _parse_room(self, room_id: int, room_elem):
        """Parse a single room element."""
        # Get basic room data
        desc_id_elem = room_elem.find('__defaultDescription')
        alt_desc_id_elem = room_elem.find('__altDescription')
        terrain_elem = room_elem.find('__terrain')
        flags_elem = room_elem.find('__roomFlags')

        desc_id = int(desc_id_elem.text) if desc_id_elem is not None else 0
        terrain = terrain_elem.text if terrain_elem is not None else 'DUNGEON1'
        flags = int(flags_elem.text) if flags_elem is not None else 0

        # Get description from our parsed descriptions
        description = self.descriptions.get(desc_id, f"Room {room_id}")
        title = self._generate_title_from_description(description)

        # Determine area from terrain
        area_id = self.terrain_map.get(terrain, 'unknown_area')

        # Create room data
        room_data = {
            'id': f"room_{room_id}",
            'title': title,
            'description': description,
            'area_id': area_id,
            'terrain': terrain,
            'is_safe': self._is_safe_room(flags),
            'light_level': self._get_light_level(terrain),
            'original_id': room_id
        }

        self.rooms[f"room_{room_id}"] = room_data

        # Parse exits
        exits_elem = room_elem.find('__exits')
        if exits_elem is not None:
            self.connections[f"room_{room_id}"] = {}

            for exit_elem in exits_elem.findall('org.tdod.ether.taimpl.cosmos.DefaultExit'):
                self._parse_exit(f"room_{room_id}", exit_elem)

        # Track areas
        if area_id not in self.areas:
            self.areas[area_id] = {
                'id': area_id,
                'name': area_id.replace('_', ' ').title(),
                'description': f"Area containing {terrain.lower()} terrain",
                'rooms': []
            }

        self.areas[area_id]['rooms'].append(f"room_{room_id}")

    def _parse_exit(self, from_room: str, exit_elem):
        """Parse a single exit element."""
        to_room_elem = exit_elem.find('__toRoom')
        direction_elem = exit_elem.find('__exitDirection')
        door_elem = exit_elem.find('__door')

        if to_room_elem is None or direction_elem is None:
            return

        to_room_id = int(to_room_elem.text)
        direction = direction_elem.text

        # Skip exits to negative room IDs (probably special areas)
        if to_room_id < 0:
            return

        # Convert direction to our format
        our_direction = self.direction_map.get(direction, direction.lower())
        to_room = f"room_{to_room_id}"

        # Basic exit data
        exit_data = {
            'to_room': to_room,
            'direction': our_direction
        }

        # Check for doors/locks
        if door_elem is not None:
            door_class = door_elem.get('class', '')
            if 'ItemKeyDoor' in door_class:
                # This is a locked door requiring a key
                exit_data['type'] = 'door'
                exit_data['locked'] = True

                # Try to extract key information
                v0_elem = door_elem.find('__v0')
                if v0_elem is not None:
                    exit_data['key'] = f"key_{v0_elem.text}"
            else:
                exit_data['type'] = 'door'

        self.connections[from_room][our_direction] = to_room

    def _generate_title_from_description(self, description: str) -> str:
        """Generate a room title from the description."""
        if not description:
            return "Unknown Room"

        # Take first sentence and clean it up
        first_sentence = description.split('.')[0]

        # Common patterns to create titles
        if "You are in" in first_sentence:
            title = first_sentence.replace("You are in", "").strip()
        elif "You are standing" in first_sentence:
            title = first_sentence.replace("You are standing", "").strip()
        elif "You stand" in first_sentence:
            title = first_sentence.replace("You stand", "").strip()
        else:
            # Take first 50 characters
            title = first_sentence[:50]

        # Clean up and capitalize
        title = title.strip(' .').title()
        if not title:
            title = "Mysterious Location"

        return title

    def _is_safe_room(self, flags: int) -> bool:
        """Determine if room is safe based on flags."""
        # This would need to be adjusted based on the actual flag meanings
        # For now, assume rooms with flag 2 might be safe rooms
        return flags == 2

    def _get_light_level(self, terrain: str) -> float:
        """Get light level based on terrain."""
        light_levels = {
            'TOWN': 1.0,
            'DUNGEON1': 0.3,
            'DUNGEON2': 0.2,
            'CAVE': 0.1,
            'FOREST': 0.7,
            'MOUNTAIN': 0.8,
            'WATER': 0.6
        }
        return light_levels.get(terrain, 0.5)

    def create_enhanced_connections(self) -> List[Dict]:
        """Create enhanced connections with door/lock information."""
        enhanced = []

        for from_room, exits in self.connections.items():
            for direction, to_room in exits.items():
                # Look for door information in the original data
                # This would be expanded based on actual door parsing
                connection = {
                    'from': from_room,
                    'to': to_room,
                    'direction': direction,
                    'type': 'normal',
                    'weight': 1.0
                }
                enhanced.append(connection)

        return enhanced

    def export_to_json(self, output_dir: str):
        """Export the parsed data to JSON files compatible with our system."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create world directory structure
        world_dir = output_path / 'world'
        rooms_dir = world_dir / 'rooms'
        areas_dir = world_dir / 'areas'

        world_dir.mkdir(exist_ok=True)
        rooms_dir.mkdir(exist_ok=True)
        areas_dir.mkdir(exist_ok=True)

        print(f"Exporting data to {output_dir}...")

        # Export individual room files
        for room_id, room_data in self.rooms.items():
            room_file = rooms_dir / f"{room_id}.json"
            with open(room_file, 'w', encoding='utf-8') as f:
                json.dump(room_data, f, indent=2, ensure_ascii=False)

        print(f"   ✓ Exported {len(self.rooms)} room files")

        # Export area files
        for area_id, area_data in self.areas.items():
            area_file = areas_dir / f"{area_id}.json"
            with open(area_file, 'w', encoding='utf-8') as f:
                json.dump(area_data, f, indent=2, ensure_ascii=False)

        print(f"   ✓ Exported {len(self.areas)} area files")

        # Export connections
        connections_data = {
            'rooms': self.connections,
            'enhanced_connections': self.create_enhanced_connections()
        }

        connections_file = world_dir / 'connections.json'
        with open(connections_file, 'w', encoding='utf-8') as f:
            json.dump(connections_data, f, indent=2)

        print(f"   ✓ Exported connections file")

        # Export statistics
        stats = {
            'total_rooms': len(self.rooms),
            'total_areas': len(self.areas),
            'total_connections': sum(len(exits) for exits in self.connections.values()),
            'terrain_distribution': {},
            'area_sizes': {}
        }

        # Calculate terrain distribution
        for room_data in self.rooms.values():
            terrain = room_data.get('terrain', 'UNKNOWN')
            stats['terrain_distribution'][terrain] = stats['terrain_distribution'].get(terrain, 0) + 1

        # Calculate area sizes
        for area_id, area_data in self.areas.items():
            stats['area_sizes'][area_id] = len(area_data['rooms'])

        stats_file = output_path / 'import_stats.json'
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

        print(f"   ✓ Exported import statistics")
        return stats

    def import_ether_world(self, ether_area_dir: str, output_dir: str):
        """Complete import process for Ether world data."""
        print("=== Ether MUD World Import ===")
        print()

        ether_path = Path(ether_area_dir)

        # Parse room descriptions first
        desc_file = ether_path / 'world_room_desc.xml'
        if desc_file.exists():
            self.parse_room_descriptions(str(desc_file))
        else:
            print(f"   ⚠ Room descriptions file not found: {desc_file}")

        # Parse main world file
        world_file = ether_path / 'world1.xml'
        if world_file.exists():
            self.parse_world_file(str(world_file))
        else:
            print(f"   ✗ World file not found: {world_file}")
            return None

        # Export to our format
        stats = self.export_to_json(output_dir)

        print()
        print("=== Import Summary ===")
        print(f"Rooms imported: {stats['total_rooms']}")
        print(f"Areas created: {stats['total_areas']}")
        print(f"Connections: {stats['total_connections']}")
        print()
        print("Terrain distribution:")
        for terrain, count in stats['terrain_distribution'].items():
            print(f"  {terrain}: {count} rooms")
        print()
        print("Area sizes:")
        for area_id, size in sorted(stats['area_sizes'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {area_id}: {size} rooms")

        return stats


def main():
    """Main function to run the import."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python xml_importer.py <ether_area_dir> <output_dir>")
        print("Example: python xml_importer.py /path/to/ether/area ./data/imported_world")
        sys.exit(1)

    ether_dir = sys.argv[1]
    output_dir = sys.argv[2]

    importer = EtherXMLImporter()
    importer.import_ether_world(ether_dir, output_dir)


if __name__ == '__main__':
    main()