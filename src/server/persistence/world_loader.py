"""World data loading and management."""

import json
import os
from typing import Dict, List, Any

class WorldLoader:
    """Loads world data from files."""

    def __init__(self, data_directory: str = "data"):
        """Initialize the world loader."""
        self.data_dir = data_directory

    def load_areas(self) -> Dict[str, Any]:
        """Load all area data."""
        areas = {}
        areas_dir = os.path.join(self.data_dir, "world", "areas")

        if not os.path.exists(areas_dir):
            return areas

        for filename in os.listdir(areas_dir):
            if filename.endswith('.json'):
                area_id = filename[:-5]
                file_path = os.path.join(areas_dir, filename)
                with open(file_path, 'r') as f:
                    areas[area_id] = json.load(f)

        return areas

    def load_rooms(self) -> Dict[str, Any]:
        """Load all room data from individual JSON files and subdirectories."""
        rooms = {}
        rooms_dir = os.path.join(self.data_dir, "world", "rooms")

        if not os.path.exists(rooms_dir):
            return rooms

        # Walk through all files and subdirectories
        for root, dirs, files in os.walk(rooms_dir):
            for filename in files:
                if filename.endswith('.json'):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r') as f:
                            room_data = json.load(f)
                            # Use the 'id' field from the JSON as the key
                            room_id = room_data.get('id', filename[:-5])
                            rooms[room_id] = room_data

                            # Debug logging for locked doors
                            if 'locked_exits' in room_data:
                                print(f"[DOOR] WorldLoader: Found locked_exits in '{room_id}' from file {filename}")
                                print(f"[DOOR] WorldLoader: locked_exits data: {room_data['locked_exits']}")
                    except Exception as e:
                        print(f"Error loading room file {file_path}: {e}")
                        continue

        print(f"[DOOR] WorldLoader: Loaded {len(rooms)} total rooms")
        # Check if dungeon1_1 is in the rooms
        if 'dungeon1_1' in rooms:
            print(f"[DOOR] WorldLoader: dungeon1_1 loaded successfully")
            if 'locked_exits' in rooms['dungeon1_1']:
                print(f"[DOOR] WorldLoader: dungeon1_1 HAS locked_exits: {rooms['dungeon1_1']['locked_exits']}")
            else:
                print(f"[DOOR] WorldLoader: dungeon1_1 MISSING locked_exits!")
        else:
            print(f"[DOOR] WorldLoader: dungeon1_1 NOT FOUND in loaded rooms!")

        return rooms

    def load_items(self) -> Dict[str, Any]:
        """Load all item data."""
        items = {}
        items_dir = os.path.join(self.data_dir, "items")

        if not os.path.exists(items_dir):
            return items

        for filename in os.listdir(items_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(items_dir, filename)
                with open(file_path, 'r') as f:
                    item_data = json.load(f)
                    if isinstance(item_data, list):
                        for item in item_data:
                            items[item['id']] = item
                    elif isinstance(item_data, dict):
                        # Check if this dict has an 'items' key (nested structure)
                        if 'items' in item_data:
                            items.update(item_data['items'])
                        else:
                            items.update(item_data)

        return items

    def load_npcs(self) -> Dict[str, Any]:
        """Load all NPC data from data/npcs directory."""
        npcs = {}
        npcs_dir = os.path.join(self.data_dir, "npcs")

        if not os.path.exists(npcs_dir):
            return npcs

        for filename in os.listdir(npcs_dir):
            # Skip monster files (they're now in data/mobs)
            if filename.startswith('monsters'):
                continue
            if filename.endswith('.json'):
                file_path = os.path.join(npcs_dir, filename)
                with open(file_path, 'r') as f:
                    npc_data = json.load(f)
                    if isinstance(npc_data, list):
                        for npc in npc_data:
                            npcs[npc['id']] = npc
                    elif isinstance(npc_data, dict) and 'id' in npc_data:
                        # Single NPC file
                        npcs[npc_data['id']] = npc_data
                    elif isinstance(npc_data, dict):
                        # Multiple NPCs in one file
                        npcs.update(npc_data)

        return npcs

    def load_connections(self) -> Dict[str, Any]:
        """Load room connections data."""
        connections_file = os.path.join(self.data_dir, "world", "connections.json")

        if not os.path.exists(connections_file):
            return {}

        with open(connections_file, 'r') as f:
            return json.load(f)

    def save_world_data(self, world_type: str, data: Dict[str, Any]):
        """Save world data to files."""
        if world_type == "rooms":
            self._save_rooms(data)
        elif world_type == "areas":
            self._save_areas(data)
        elif world_type == "items":
            self._save_items(data)
        elif world_type == "npcs":
            self._save_npcs(data)

    def _save_rooms(self, rooms: Dict[str, Any]):
        """Save room data to individual files."""
        rooms_dir = os.path.join(self.data_dir, "world", "rooms")
        os.makedirs(rooms_dir, exist_ok=True)

        for room_id, room_data in rooms.items():
            file_path = os.path.join(rooms_dir, f"{room_id}.json")
            with open(file_path, 'w') as f:
                json.dump(room_data, f, indent=2)

    def _save_areas(self, areas: Dict[str, Any]):
        """Save area data to individual files."""
        areas_dir = os.path.join(self.data_dir, "world", "areas")
        os.makedirs(areas_dir, exist_ok=True)

        for area_id, area_data in areas.items():
            file_path = os.path.join(areas_dir, f"{area_id}.json")
            with open(file_path, 'w') as f:
                json.dump(area_data, f, indent=2)

    def _save_items(self, items: Dict[str, Any]):
        """Save item data to files."""
        items_dir = os.path.join(self.data_dir, "items")
        os.makedirs(items_dir, exist_ok=True)

        weapons = {k: v for k, v in items.items() if v.get('type') == 'weapon'}
        armor = {k: v for k, v in items.items() if v.get('type') == 'armor'}
        consumables = {k: v for k, v in items.items() if v.get('type') == 'consumable'}

        if weapons:
            with open(os.path.join(items_dir, "weapons.json"), 'w') as f:
                json.dump(list(weapons.values()), f, indent=2)

        if armor:
            with open(os.path.join(items_dir, "armor.json"), 'w') as f:
                json.dump(list(armor.values()), f, indent=2)

        if consumables:
            with open(os.path.join(items_dir, "consumables.json"), 'w') as f:
                json.dump(list(consumables.values()), f, indent=2)

    def _save_npcs(self, npcs: Dict[str, Any]):
        """Save NPC data to files."""
        npcs_dir = os.path.join(self.data_dir, "npcs")
        os.makedirs(npcs_dir, exist_ok=True)

        monsters = {k: v for k, v in npcs.items() if v.get('type') == 'monster'}
        vendors = {k: v for k, v in npcs.items() if v.get('type') == 'vendor'}

        if monsters:
            with open(os.path.join(npcs_dir, "monsters.json"), 'w') as f:
                json.dump(list(monsters.values()), f, indent=2)

        if vendors:
            with open(os.path.join(npcs_dir, "vendors.json"), 'w') as f:
                json.dump(list(vendors.values()), f, indent=2)