"""Item management system for handling room items and item operations."""

from typing import Dict, List, Tuple, Any, Optional


class ItemManager:
    """Manages room items and item-related operations."""

    def __init__(self, game_engine):
        """Initialize the ItemManager with reference to the game engine.

        Args:
            game_engine: The AsyncGameEngine instance to access connection manager and other systems
        """
        self.game_engine = game_engine

        # Room item management - tracks items on the floor in each room
        self.room_items: Dict[str, List[Dict[str, Any]]] = {}

    def get_room_items(self, room_id: str) -> List[Dict[str, Any]]:
        """Get list of items in a room."""
        if room_id not in self.room_items:
            self.room_items[room_id] = []
        return self.room_items[room_id]

    def add_item_to_room(self, room_id: str, item: Dict[str, Any]) -> None:
        """Add an item to a room's floor."""
        if room_id not in self.room_items:
            self.room_items[room_id] = []
        self.room_items[room_id].append(item)

    def remove_item_from_room(self, room_id: str, item_name: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Remove and return an item from a room's floor by name using partial matching.

        Returns:
            Tuple of (item, match_type) where:
            - item: The removed item dict or None
            - match_type: 'exact', 'unique', 'multiple', or 'none'
        """
        room_items = self.get_room_items(room_id)
        item, index, match_type = self.find_item_by_partial_name(room_items, item_name)

        if match_type in ['exact', 'unique'] and item:
            return room_items.pop(index), match_type
        else:
            return None, match_type

    def find_item_by_partial_name(self, item_list: List[Dict[str, Any]], partial_name: str) -> Tuple[Optional[Dict[str, Any]], int, str]:
        """
        Find an item by partial name matching.

        Args:
            item_list: List of items to search
            partial_name: Partial name to match

        Returns:
            Tuple of (item, index, match_type) where:
            - item: The matched item dict or None
            - index: The index of the item in the list or -1
            - match_type: 'exact', 'unique', 'multiple', or 'none'
        """
        partial_lower = partial_name.lower()
        exact_matches = []
        partial_matches = []

        for i, item in enumerate(item_list):
            item_name_lower = item['name'].lower()

            # Check for exact match first
            if item_name_lower == partial_lower:
                exact_matches.append((item, i))
            # Check for partial match (substring)
            elif partial_lower in item_name_lower:
                partial_matches.append((item, i))

        # Return exact match if found
        if exact_matches:
            item, index = exact_matches[0]
            return item, index, 'exact'

        # Return partial match if unique
        if len(partial_matches) == 1:
            item, index = partial_matches[0]
            return item, index, 'unique'
        elif len(partial_matches) > 1:
            # Multiple matches - return None but indicate multiple
            return None, -1, 'multiple'
        else:
            # No matches
            return None, -1, 'none'

    def get_room_items_description(self, room_id: str) -> str:
        """Get description of items on the floor in a room."""
        room_items = self.get_room_items(room_id)
        if not room_items:
            return "There is nothing on the floor."

        if len(room_items) == 1:
            item = room_items[0]
            article = "an" if item['name'][0].lower() in 'aeiou' else "a"
            return f"There is {article} {item['name'].lower()} lying on the floor."
        else:
            # Multiple items
            item_names = [item['name'].lower() for item in room_items]
            if len(item_names) == 2:
                return f"There are {item_names[0]} and {item_names[1]} lying on the floor."
            else:
                items_str = ", ".join(item_names[:-1]) + f" and {item_names[-1]}"
                return f"There are {items_str} lying on the floor."

    async def handle_drop_item(self, player_id: int, item_name: str) -> None:
        """Handle dropping an item from inventory."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']

        # Find item in inventory using partial name matching
        inventory = character.get('inventory', [])
        item_to_drop, item_index, match_type = self.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name}.")
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(player_id, f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
            return

        # Remove item from inventory
        dropped_item = character['inventory'].pop(item_index)

        # Add item to room
        room_id = character.get('room_id')
        if room_id:
            self.add_item_to_room(room_id, dropped_item)

        # Update encumbrance
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"Ok, you dropped your {dropped_item['name'].lower()}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(room_id, player_id, f"{username} drops a {dropped_item['name']}.")

    async def handle_equip_item(self, player_id: int, item_name: str):
        """Handle equipping an item from inventory."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find the item in inventory using partial name matching
        item_to_equip, item_index, match_type = self.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name} to equip.")
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(player_id, f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
            return

        # Check if item is equippable
        item_type = item_to_equip.get('type')
        if item_type not in ['weapon', 'armor']:
            await self.game_engine.connection_manager.send_message(player_id, f"You can't equip {item_to_equip['name']}.")
            return

        # Determine equipment slot
        if item_type == 'weapon':
            slot = 'weapon'
        elif item_type == 'armor':
            slot = 'armor'

        # Check if something is already equipped in that slot
        currently_equipped = character['equipped'].get(slot)
        if currently_equipped:
            # Unequip current item first
            character['inventory'].append(currently_equipped)
            await self.game_engine.connection_manager.send_message(player_id, f"You unequip your {currently_equipped['name']}.")

        # Equip the new item
        character['equipped'][slot] = item_to_equip
        character['inventory'].pop(item_index)

        # Update armor class if armor
        if item_type == 'armor':
            armor_class = item_to_equip.get('properties', {}).get('armor_class', 0)
            character['armor_class'] = armor_class

        # Update encumbrance (equipped items still count toward weight)
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"You equip the {item_to_equip['name']}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(room_id, player_id, f"{username} equips a {item_to_equip['name']}.")

    async def handle_unequip_item(self, player_id: int, item_name: str):
        """Handle unequipping an item to inventory."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        equipped = character.get('equipped', {})

        # Create a list of equipped items for partial matching
        equipped_items = []
        slot_mapping = {}
        for slot, equipped_item in equipped.items():
            if equipped_item:
                equipped_items.append(equipped_item)
                slot_mapping[equipped_item['name']] = slot

        # Find the equipped item using partial name matching
        item_to_unequip, item_index, match_type = self.find_item_by_partial_name(equipped_items, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name} equipped.")
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in equipped_items if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(player_id, f"'{item_name}' matches multiple equipped items: {match_list}. Please be more specific.")
            return

        # Get the slot to clear
        slot_to_clear = slot_mapping[item_to_unequip['name']]

        # Unequip the item
        character['equipped'][slot_to_clear] = None
        character['inventory'].append(item_to_unequip)

        # Update armor class if armor
        if item_to_unequip.get('type') == 'armor':
            character['armor_class'] = 0  # Reset to base armor class

        # Update encumbrance
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"You unequip your {item_to_unequip['name']}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(room_id, player_id, f"{username} unequips their {item_to_unequip['name']}.")