"""Command handler for processing player commands."""

import asyncio
import random
import json
from typing import Optional, Dict, Any, Tuple


class CommandHandler:
    """Handles parsing and execution of player commands."""

    def __init__(self, game_engine):
        """Initialize the command handler with reference to the game engine.

        Args:
            game_engine: The AsyncGameEngine instance this handler belongs to
        """
        self.game_engine = game_engine
        self.logger = game_engine.logger

    async def handle_player_command(self, player_id: int, command: str, params: str):
        """Handle a command from a player."""
        if not self.game_engine.player_manager.is_player_connected(player_id):
            return

        # Handle command asynchronously
        asyncio.create_task(self._process_player_command(player_id, command, params))

    async def _process_player_command(self, player_id: int, command: str, params: str):
        """Process a player command asynchronously."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)

        # Handle login process
        if not player_data.get('authenticated'):
            await self._handle_login_process(player_id, command, params)
            return

        # Handle game commands
        await self._handle_game_command(player_id, command, params)

    async def _handle_login_process(self, player_id: int, input_text: str, _params: str):
        """Handle the login process for a player."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        login_state = player_data.get('login_state', 'username_prompt')

        if login_state == 'username_prompt':
            # Skip empty username
            if not input_text.strip():
                await self.game_engine.connection_manager.send_message(player_id, "Username: ", add_newline=False)
                return

            # Store username and ask for password
            player_data['username'] = input_text.strip()
            player_data['login_state'] = 'password_prompt'
            await self.game_engine.connection_manager.send_message(player_id, "Password: ", add_newline=False)

        elif login_state == 'password_prompt':
            # Authenticate user
            username = player_data.get('username', '')
            password = input_text.strip()

            if self.game_engine.player_manager.authenticate_player(username, password):
                player_data['authenticated'] = True
                player_data['login_state'] = 'authenticated'
                await self.game_engine.connection_manager.send_message(player_id, f"Welcome back, {username}!")

                # Load character or prompt for character creation
                await self._handle_character_selection(player_id, username)
            else:
                await self.game_engine.connection_manager.send_message(player_id, "Invalid credentials. Try again.")
                await self.game_engine.connection_manager.send_message(player_id, "Username: ")
                player_data['login_state'] = 'username_prompt'

    def _migrate_character_data(self, character: dict):
        """Migrate old character data to new format.

        Args:
            character: Character dict to migrate (modified in place)
        """
        # Sync health field from current_hit_points if missing
        if 'health' not in character and 'current_hit_points' in character:
            character['health'] = character['current_hit_points']
            print(f"[MIGRATION] Set health to {character['health']}")

        # Sync mana field from current_mana if missing
        if 'mana' not in character and 'current_mana' in character:
            character['mana'] = character['current_mana']
            print(f"[MIGRATION] Set mana to {character['mana']}")

        # Ensure max_hit_points exists
        if 'max_hit_points' not in character:
            # Calculate from constitution
            constitution = character.get('constitution', 15)
            character['max_hit_points'] = constitution * 5 + 5  # Base calculation
            print(f"[MIGRATION] Set max_hit_points to {character['max_hit_points']}")

        # Ensure max_mana exists
        if 'max_mana' not in character:
            intellect = character.get('intellect', 15)
            character['max_mana'] = intellect * 3 + 3  # Base calculation
            print(f"[MIGRATION] Set max_mana to {character['max_mana']}")

    async def _handle_character_selection(self, player_id: int, username: str):
        """Handle character selection/creation."""
        # Try to load existing character data first
        if self.game_engine.player_storage:
            print(f"[DEBUG] Attempting to load character for '{username}'")
            existing_character = self.game_engine.player_storage.load_character_data(username)
            if existing_character:
                # Migrate old character data to new format
                self._migrate_character_data(existing_character)

                # Load existing character
                print(f"[DEBUG] Character loaded for '{username}': level {existing_character.get('level')}, gold {existing_character.get('gold')}")
                self.game_engine.player_manager.set_player_character(player_id, existing_character)
                await self.game_engine.connection_manager.send_message(player_id, f"Welcome back! Character '{username}' loaded successfully!")
                await self.game_engine._send_room_description(player_id, detailed=True)
                return
            else:
                print(f"[DEBUG] No existing character found for '{username}', creating new one")

        # No existing character found, create a new one
        # Get starting room from world manager
        starting_room = self.game_engine.world_manager.get_default_starting_room()

        character = {
            'name': username,
            'room_id': starting_room,
            'species': 'Human',  # Default race
            'class': 'Fighter',  # Default class
            'level': 1,
            'experience': 0,
            'rune': 'None',

            # Stats
            'intellect': 15,
            'wisdom': 15,
            'strength': 15,
            'constitution': 15,
            'dexterity': 15,
            'charisma': 15,
        }

        # Calculate max hit points based on constitution with randomness
        # Formula: (Constitution * 5) + random(1-10) + level bonus
        import random
        constitution = character['constitution']
        base_hp = constitution * 5
        random_hp = random.randint(1, 10)
        level_bonus = (character['level'] - 1) * 5  # +5 HP per level after 1st
        max_hp = base_hp + random_hp + level_bonus

        # Calculate max mana based on intellect
        intellect = character['intellect']
        base_mana = intellect * 3
        random_mana = random.randint(1, 5)
        max_mana = base_mana + random_mana

        character.update({
            # Health and Mana
            'max_hit_points': max_hp,
            'health': max_hp,  # Use 'health' for combat system compatibility
            'current_hit_points': max_hp,  # Keep for backward compatibility
            'max_mana': max_mana,
            'mana': max_mana,  # Use 'mana' for combat system compatibility
            'current_mana': max_mana,  # Keep for backward compatibility
            'status': 'Healthy',
            'armor_class': 0,

            # Equipment slots
            'equipped': {
                'weapon': None,      # Equipped weapon item
                'armor': None,       # Equipped armor item
            },
            'encumbrance': 0,
            'max_encumbrance': 0,  # Will be calculated based on strength

            # Inventory and Currency
            'inventory': [],  # List of items
            'gold': 100,  # Starting gold
        })

        # Calculate initial encumbrance based on starting gold and strength
        self.game_engine.player_manager.update_encumbrance(character)

        self.game_engine.player_manager.set_player_character(player_id, character)

        await self.game_engine.connection_manager.send_message(player_id, f"Character '{username}' loaded successfully!")
        await self.game_engine._send_room_description(player_id, detailed=True)

    async def _handle_game_command(self, player_id: int, command: str, params: str):
        """Handle a game command from an authenticated player."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        # Handle commands directly like the simple server
        original_command = f"{command} {params}".strip()
        full_command = f"{command} {params}".strip().lower()
        character = player_data['character']

        # Empty command refreshes the basic UI
        if not command:
            # Just show the basic room description
            await self.game_engine._send_room_description(player_id, detailed=False)
            return

        if command in ['quit', 'q']:
            await self.game_engine.connection_manager.send_message(player_id, "Goodbye!")
            await self.game_engine.connection_manager.disconnect_player(player_id)
            return

        elif command in ['look', 'l']:
            if params:
                # Look at specific target
                await self._handle_look_at_target(player_id, params)
            else:
                # Look around the room
                await self.game_engine._send_room_description(player_id, detailed=True)

        elif command in ['help', '?']:
            help_text = """
Available Commands:
==================
look (l)        - Look around or examine target
help (?)        - Show this help
exits           - Show exits
stats (st)      - Show character stats
inventory (i)   - Show inventory
get <item>      - Pick up an item
drop <item>     - Drop an item
list            - Show vendor wares
buy <item>      - Buy from vendor
sell <item>     - Sell to vendor

Combat Commands:
===============
attack <target> - Attack a target
flee            - Try to flee from combat

Movement:
=========
north (n)       - Go north
south (s)       - Go south
east (e)        - Go east
west (w)        - Go west
up (u)          - Go up
down (d)        - Go down
quit (q)        - Quit the game
"""
            await self.game_engine.connection_manager.send_message(player_id, help_text)

        elif command == 'exits':
            exits = self.game_engine.world_manager.get_exits_from_room(character['room_id'])
            if exits:
                await self.game_engine.connection_manager.send_message(player_id, f"Available exits: {', '.join(exits.keys())}")
            else:
                await self.game_engine.connection_manager.send_message(player_id, "No exits available.")

        elif command in ['stats', 'score', 'st']:
            await self._handle_stats_command(player_id, character)

        elif command in ['inventory', 'inv', 'i']:
            await self._handle_inventory_command(player_id, character)

        elif command == 'get' and params:
            # Pick up an item from the room
            await self._handle_get_item(player_id, params)

        elif command == 'get':
            # Get command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to get?")

        elif command == 'drop' and params:
            # Drop an item from inventory
            await self._handle_drop_item(player_id, params)

        elif command == 'drop':
            # Drop command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to drop?")

        elif command in ['equip', 'eq'] and params:
            # Equip an item from inventory
            await self._handle_equip_item(player_id, params)

        elif command in ['equip', 'eq']:
            # Equip command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to equip?")

        elif command == 'unequip' and params:
            # Unequip an item to inventory
            await self._handle_unequip_item(player_id, params)

        elif command == 'unequip':
            # Unequip command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to unequip?")

        elif command in ['buy', 'sell'] and params:
            # Handle buying/selling with vendors
            await self._handle_trade_command(player_id, command, params)

        elif command in ['list', 'wares']:
            # Show vendor inventory if in vendor room
            # Support "list" or "list <vendor_name>"
            await self._handle_list_vendor_items(player_id, params if params else None)

        elif command in ['ring', 'ri'] and params:
            # Handle ring command for special items like the gong
            await self._handle_ring_command(player_id, params)

        elif command in ['ring', 'ri'] and not params:
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to ring?")

        # Combat commands
        elif command in ['attack', 'att', 'a', 'kill']:
            if not params:
                await self.game_engine.connection_manager.send_message(player_id, "Attack what?")
            else:
                await self._handle_attack_command(player_id, params)

        elif command in ['flee', 'run']:
            await self._handle_flee_command(player_id)

        elif command in ['north', 'n', 'south', 's', 'east', 'e', 'west', 'w',
                        'northeast', 'ne', 'northwest', 'nw', 'southeast', 'se',
                        'southwest', 'sw', 'up', 'u', 'down', 'd']:
            await self.game_engine._move_player(player_id, command)

        else:
            # Treat unknown commands as speech/chat messages
            username = player_data.get('username', 'Someone')
            room_id = character.get('room_id')

            # Broadcast message to others in the room
            await self.game_engine._notify_room_except_player(room_id, player_id, f"From {username}: {original_command}\n")

            # Confirm to sender
            await self.game_engine.connection_manager.send_message(player_id, "-- Message sent --")

    async def _handle_stats_command(self, player_id: int, character: dict):
        """Display character statistics."""
        char = character
        stats_text = f"""
Name:          {char['name']}
Species:       {char['species']}
Class:         {char['class']}
Level:         {char['level']}
Experience:    {char['experience']}
Rune:          {char['rune']}

Intellect:     {char['intellect']}
Wisdom:        {char['wisdom']}
Strength:      {char['strength']}
Constitution:  {char['constitution']}
Dexterity:     {char['dexterity']}
Charisma:      {char['charisma']}

Hit Points:    {char.get('health', char.get('current_hit_points', 20))} / {char.get('max_hit_points', 20)}
Mana:          {char.get('mana', char.get('current_mana', 10))} / {char.get('max_mana', 10)}
Status:        {char['status']}
Armor Class:   {char['armor_class']}

Weapon:        {char['equipped']['weapon']['name'] if char['equipped']['weapon'] else 'Fists'}
Armor:         {char['equipped']['armor']['name'] if char['equipped']['armor'] else 'None'}
Encumbrance:   {char['encumbrance']} / {char['max_encumbrance']}
Gold:          {char['gold']}
"""
        await self.game_engine.connection_manager.send_message(player_id, stats_text)

    async def _handle_inventory_command(self, player_id: int, character: dict):
        """Display player inventory."""
        char = character
        inventory_text = f"You are carrying:\n"
        if char['inventory']:
            for i, item in enumerate(char['inventory'], 1):
                inventory_text += f"  {i}. {item['name']}\n"
        else:
            inventory_text += "  Nothing.\n"

        # Show equipped items
        inventory_text += "\n--- Equipped ---\n"
        weapon = char['equipped']['weapon']
        armor = char['equipped']['armor']
        inventory_text += f"Weapon: {weapon['name'] if weapon else 'None'}\n"
        inventory_text += f"Armor:  {armor['name'] if armor else 'None'}\n"

        inventory_text += f"\nGold: {char['gold']}"
        await self.game_engine.connection_manager.send_message(player_id, inventory_text)

    async def _handle_get_item(self, player_id: int, item_name: str):
        """Handle picking up an item from the room."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # First, try to pick up an item from the room floor
        if room_id:
            item, match_type = self.game_engine.item_manager.remove_item_from_room(room_id, item_name)
            if match_type == 'multiple':
                # Handle multiple matches
                room_items = self.game_engine.item_manager.get_room_items(room_id)
                matches = [item['name'] for item in room_items if item_name.lower() in item['name'].lower()]
                match_list = ", ".join(matches)
                await self.game_engine.connection_manager.send_message(player_id, f"'{item_name}' matches multiple items on the floor: {match_list}. Please be more specific.")
                return
            elif item:
                # Check encumbrance before picking up
                current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
                item_weight = item.get('weight', 0)
                max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)

                if current_encumbrance + item_weight > max_encumbrance:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cannot pick up {item['name']} - you are carrying too much! ({current_encumbrance + item_weight:.1f}/{max_encumbrance})"
                    )
                    return

                # Found item on floor, pick it up
                character['inventory'].append(item)

                # Update encumbrance
                self.game_engine.player_manager.update_encumbrance(character)

                await self.game_engine.connection_manager.send_message(player_id, f"You pick up the {item['name']}.")

                # Notify others in the room
                username = player_data.get('username', 'Someone')
                await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} picks up a {item['name']}.")
                return

        # If no item found on floor, try to create item from configuration
        item_id = item_name.lower().replace(' ', '_')
        item = self.game_engine.config_manager.create_item_instance(item_id)

        if not item:
            # Fallback to simple item creation for items not in config
            item = {
                'name': item_name.capitalize(),
                'weight': 1,
                'value': 10
            }

        # Check encumbrance before picking up
        current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
        item_weight = item.get('weight', 0)
        max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)

        if current_encumbrance + item_weight > max_encumbrance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cannot pick up {item['name']} - you are carrying too much! ({current_encumbrance + item_weight:.1f}/{max_encumbrance})"
            )
            return

        character['inventory'].append(item)

        # Update encumbrance
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"You pick up the {item['name']}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} picks up a {item['name']}.")

    async def _handle_drop_item(self, player_id: int, item_name: str):
        """Handle dropping an item from inventory."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']

        # Find item in inventory using partial name matching
        inventory = character.get('inventory', [])
        item_to_drop, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

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
            self.game_engine.item_manager.add_item_to_room(room_id, dropped_item)

        # Update encumbrance
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"Ok, you dropped your {dropped_item['name'].lower()}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} drops a {dropped_item['name']}.")

    async def _handle_equip_item(self, player_id: int, item_name: str):
        """Handle equipping an item from inventory."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find item in inventory using partial name matching
        item_to_equip, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name} to equip.")
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(player_id, f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
            return

        # Determine which slot this item goes in
        item_type = item_to_equip.get('type', 'misc')
        if item_type == 'weapon':
            slot = 'weapon'
        elif item_type == 'armor':
            slot = 'armor'
        else:
            await self.game_engine.connection_manager.send_message(player_id, f"You cannot equip the {item_to_equip['name']}.")
            return

        # Check if slot is already occupied
        equipped_items = character.get('equipped', {})
        if equipped_items.get(slot):
            currently_equipped = equipped_items[slot]
            await self.game_engine.connection_manager.send_message(player_id,
                f"You are already wearing {currently_equipped['name']}. "
                f"You must unequip it first.")
            return

        # Remove from inventory and equip
        equipped_item = character['inventory'].pop(item_index)
        character['equipped'][slot] = equipped_item

        # Update armor class if armor
        if item_type == 'armor':
            armor_class = equipped_item.get('armor_class', 1)
            character['armor_class'] = armor_class

        await self.game_engine.connection_manager.send_message(player_id, f"You equip the {equipped_item['name']}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} equips a {equipped_item['name']}.")

    async def _handle_unequip_item(self, player_id: int, item_name: str):
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
        item_to_unequip, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(equipped_items, item_name)

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

        await self.game_engine.connection_manager.send_message(player_id, f"You unequip your {item_to_unequip['name']}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} unequips their {item_to_unequip['name']}.")

    async def _handle_trade_command(self, player_id: int, action: str, params: str):
        """Handle buy/sell commands with vendors.

        Supports:
        - buy <item> - buy from first vendor
        - buy <item> from <vendor> - buy from specific vendor
        - sell <item> - sell to first vendor
        - sell <item> to <vendor> - sell to specific vendor
        """
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Parse the command to extract item name and optional vendor name
        item_name = params
        vendor_name = None

        # Check for "from <vendor>" or "to <vendor>"
        if ' from ' in params.lower():
            parts = params.lower().split(' from ', 1)
            item_name = parts[0].strip()
            vendor_name = parts[1].strip()
        elif ' to ' in params.lower():
            parts = params.lower().split(' to ', 1)
            item_name = parts[0].strip()
            vendor_name = parts[1].strip()

        # Find the vendor
        if vendor_name:
            vendor = self.game_engine.vendor_system.find_vendor_by_name(room_id, vendor_name)
            if not vendor:
                await self.game_engine.connection_manager.send_message(player_id, f"There is no vendor named '{vendor_name}' here.")
                return
        else:
            vendor = self.game_engine.vendor_system.get_vendor_in_room(room_id)
            if not vendor:
                await self.game_engine.connection_manager.send_message(player_id, "There is no vendor here to trade with.")
                return

        if action == 'buy':
            await self._handle_buy_item(player_id, vendor, item_name)
        elif action == 'sell':
            await self._handle_sell_item(player_id, vendor, item_name)

    async def _handle_ring_command(self, player_id: int, target: str):
        """Handle ring command for special items like gongs."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Check if the target matches "gong" or similar variations
        target_lower = target.lower()
        if target_lower in ['gong', 'g', 'bronze gong', 'bronze']:
            # Check if player is in the arena room
            if room_id != 'arena':
                await self.game_engine.connection_manager.send_message(player_id, "There is no gong here to ring.")
                return

            # Ring the gong and spawn a mob
            await self._ring_gong(player_id, room_id)
        else:
            await self.game_engine.connection_manager.send_message(player_id, f"You cannot ring {target}.")

    async def _ring_gong(self, player_id: int, room_id: str):
        """Ring the gong in the arena and spawn a random mob."""
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
        await self.game_engine._notify_room_except_player(room_id, player_id,
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
            'spawned_by_gong': True
        }

        self.game_engine.room_mobs[room_id].append(spawned_mob)
        self.logger.info(f"[ARENA] {mob_name} spawned in {room_id} by player {player_id}")

    async def _handle_list_vendor_items(self, player_id: int, vendor_name: str = None):
        """Show vendor inventory.

        Args:
            player_id: The player requesting the list
            vendor_name: Optional name of specific vendor to list. If None, lists first vendor.
        """
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Find the vendor
        if vendor_name:
            vendor = self.game_engine.vendor_system.find_vendor_by_name(room_id, vendor_name)
            if not vendor:
                await self.game_engine.connection_manager.send_message(player_id, f"There is no vendor named '{vendor_name}' here.")
                return
        else:
            vendor = self.game_engine.vendor_system.get_vendor_in_room(room_id)
            if not vendor:
                # Check if there are multiple vendors
                vendors = self.game_engine.vendor_system.get_vendors_in_room(room_id)
                if len(vendors) > 1:
                    vendor_names = [v['name'] for v in vendors]
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"There are multiple vendors here: {', '.join(vendor_names)}. Use 'list <vendor name>' to see a specific vendor's wares."
                    )
                    return
                await self.game_engine.connection_manager.send_message(player_id, "There is no vendor here.")
                return

        inventory_text = f"{vendor['name']} has the following items for sale:\n"
        for i, item_entry in enumerate(vendor['inventory'], 1):
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config:
                item_name = item_config['name']
                price = item_entry['price']
                inventory_text += f"  {i}. {item_name} - {price} gold\n"
            else:
                inventory_text += f"  {i}. {item_id} (unknown item) - {item_entry['price']} gold\n"

        await self.game_engine.connection_manager.send_message(player_id, inventory_text)

    async def _handle_buy_item(self, player_id: int, vendor: dict, item_name: str):
        """Handle buying an item from a vendor."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        character = player_data['character']

        # Find the item in vendor inventory
        item_found = None
        item_price = None
        for item_entry in vendor['inventory']:
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config and item_name.lower() in item_config['name'].lower():
                item_found = item_config
                item_price = item_entry['price']
                break

        if not item_found:
            await self.game_engine.connection_manager.send_message(player_id, f"{vendor['name']} doesn't have {item_name} for sale.")
            return

        # Check if player has enough gold
        if character['gold'] < item_price:
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have enough gold. {item_found['name']} costs {item_price} gold.")
            return

        # Check encumbrance before buying
        current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
        item_weight = item_found.get('weight', 0)
        gold_weight_change = -item_price / 100.0  # Losing gold reduces weight
        max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)

        if current_encumbrance + item_weight + gold_weight_change > max_encumbrance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cannot carry {item_found['name']} - you are carrying too much!"
            )
            return

        # Complete the purchase
        character['gold'] -= item_price
        character['inventory'].append(item_found.copy())

        # Update encumbrance (accounts for gold weight change and new item)
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"You buy {item_found['name']} for {item_price} gold.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} buys something from {vendor['name']}.")

    async def _handle_sell_item(self, player_id: int, vendor: dict, item_name: str):
        """Handle selling an item to a vendor."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        character = player_data['character']

        # Find item in player inventory
        inventory = character.get('inventory', [])
        item_to_sell, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name} to sell.")
            return
        elif match_type == 'multiple':
            matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(player_id, f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
            return

        # Calculate sell price (typically half of value)
        sell_price = max(1, item_to_sell.get('value', 10) // 2)

        # Complete the sale
        sold_item = character['inventory'].pop(item_index)
        character['gold'] += sell_price

        # Update encumbrance (accounts for gold weight change and removed item)
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"You sell {sold_item['name']} for {sell_price} gold.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} sells something to {vendor['name']}.")

    async def _handle_look_at_target(self, player_id: int, target_name: str):
        """Handle looking at a specific target."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # First check if it's a player in the room
        target_lower = target_name.lower()
        for other_player_id, other_player_data in self.game_engine.player_manager.get_all_connected_players().items():
            if other_player_id == player_id:
                continue
            other_character = other_player_data.get('character')
            if other_character and other_character.get('room_id') == room_id:
                other_name = other_character.get('name', '').lower()
                if target_lower in other_name or other_name in target_lower:
                    # Found a player
                    await self.game_engine.connection_manager.send_message(player_id, f"You look at {other_character['name']}.")
                    await self.game_engine.connection_manager.send_message(other_player_id, f"{character['name']} looks at you.")
                    return

        # Check for items on the floor
        room_items = self.game_engine.item_manager.get_room_items(room_id)
        for item in room_items:
            if target_lower in item['name'].lower():
                description = item.get('description', f"A {item['name'].lower()}.")
                await self.game_engine.connection_manager.send_message(player_id, f"You examine the {item['name']}: {description}")
                return

        # Check for mobs
        if room_id in self.game_engine.room_mobs:
            for mob in self.game_engine.room_mobs[room_id]:
                if target_lower in mob['name'].lower():
                    description = mob.get('description', f"A {mob['name'].lower()}.")
                    health_status = ""
                    if mob.get('health', 100) < mob.get('max_health', 100):
                        health_percent = (mob['health'] / mob['max_health']) * 100
                        if health_percent > 75:
                            health_status = " It looks slightly wounded."
                        elif health_percent > 50:
                            health_status = " It looks moderately wounded."
                        elif health_percent > 25:
                            health_status = " It looks badly wounded."
                        else:
                            health_status = " It looks near death."

                    await self.game_engine.connection_manager.send_message(player_id, f"You look at the {mob['name']}: {description}{health_status}")
                    return

        # Check for vendors
        vendors = self.game_engine.vendor_system.get_vendors_in_room(room_id)
        for vendor in vendors:
            if target_lower in vendor['name'].lower():
                description = vendor.get('description', f"A merchant named {vendor['name']}.")
                await self.game_engine.connection_manager.send_message(player_id, f"You look at {vendor['name']}: {description}")
                return

        # Check player's inventory
        inventory = character.get('inventory', [])
        for item in inventory:
            if target_lower in item['name'].lower():
                description = item.get('description', f"A {item['name'].lower()}.")
                await self.game_engine.connection_manager.send_message(player_id, f"You examine your {item['name']}: {description}")
                return

        # Nothing found
        await self.game_engine.connection_manager.send_message(player_id, f"You don't see {target_name} here.")

    async def _handle_attack_command(self, player_id: int, target_name: str):
        """Handle attack command."""
        await self.game_engine.combat_system.handle_attack_command(player_id, target_name)

    async def _handle_flee_command(self, player_id: int):
        """Handle flee command."""
        await self.game_engine.combat_system.handle_flee_command(player_id)