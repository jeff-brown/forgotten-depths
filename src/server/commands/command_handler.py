"""Command handler for processing player commands."""

import asyncio
import random
import json
import time
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

        # Handle character creation (even if authenticated)
        if player_data.get('creating_character'):
            await self._handle_character_creation_input(player_id, command)
            return

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

        # Add hunger and thirst for old characters
        if 'hunger' not in character:
            character['hunger'] = 100
            print(f"[MIGRATION] Set hunger to 100")

        if 'thirst' not in character:
            character['thirst'] = 100
            print(f"[MIGRATION] Set thirst to 100")
            print(f"[MIGRATION] Set max_mana to {character['max_mana']}")

        # Ensure spell-related fields exist
        if 'spellbook' not in character:
            character['spellbook'] = []
            print(f"[MIGRATION] Initialized empty spellbook")

        if 'spell_cooldowns' not in character:
            character['spell_cooldowns'] = {}
            print(f"[MIGRATION] Initialized empty spell_cooldowns")

        if 'active_effects' not in character:
            character['active_effects'] = []
            print(f"[MIGRATION] Initialized empty active_effects")

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

        # No existing character found, start character creation flow
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        player_data['creating_character'] = True
        player_data['char_creation_step'] = 'race'

        await self._show_race_selection(player_id)
        return

    async def _show_race_selection(self, player_id: int):
        """Show race selection menu."""
        races = self._load_races()
        message = "\n=== Choose Your Race ===\n\n"
        for i, (race_id, race_data) in enumerate(races.items(), 1):
            message += f"{i}. {race_data['name']}\n   {race_data['description']}\n\n"
        message += "Enter the number of your choice: "
        await self.game_engine.connection_manager.send_message(player_id, message, add_newline=False)

    async def _show_class_selection(self, player_id: int):
        """Show class selection menu."""
        classes = self._load_classes()
        message = "\n=== Choose Your Class ===\n\n"
        for i, (class_id, class_data) in enumerate(classes.items(), 1):
            message += f"{i}. {class_data['name']}\n   {class_data['description']}\n\n"
        message += "Enter the number of your choice: "
        await self.game_engine.connection_manager.send_message(player_id, message, add_newline=False)

    def _load_races(self):
        """Load race definitions from JSON."""
        import json
        import os
        try:
            with open('data/races.json', 'r') as f:
                return json.load(f)
        except:
            # Fallback to default
            return {"human": {"name": "Human", "description": "Versatile humans", "base_stats": {"strength": 10, "dexterity": 10, "constitution": 10, "intellect": 10, "wisdom": 10, "charisma": 10}}}

    def _load_classes(self):
        """Load class definitions from JSON."""
        import json
        import os
        try:
            with open('data/classes.json', 'r') as f:
                return json.load(f)
        except:
            # Fallback to default
            return {"fighter": {"name": "Fighter", "description": "Martial warrior", "stat_modifiers": {}, "hp_modifier": 1.0, "mana_modifier": 1.0}}

    async def _handle_character_creation_input(self, player_id: int, user_input: str):
        """Handle input during character creation."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        step = player_data.get('char_creation_step')

        if step == 'race':
            races = self._load_races()
            race_list = list(races.keys())
            try:
                choice = int(user_input) - 1
                if 0 <= choice < len(race_list):
                    player_data['selected_race'] = race_list[choice]
                    player_data['char_creation_step'] = 'class'
                    await self._show_class_selection(player_id)
                else:
                    await self.game_engine.connection_manager.send_message(player_id, "Invalid choice. Try again.")
                    await self._show_race_selection(player_id)
            except ValueError:
                await self.game_engine.connection_manager.send_message(player_id, "Please enter a number.")
                await self._show_race_selection(player_id)

        elif step == 'class':
            classes = self._load_classes()
            class_list = list(classes.keys())
            try:
                choice = int(user_input) - 1
                if 0 <= choice < len(class_list):
                    player_data['selected_class'] = class_list[choice]
                    await self._create_character_with_selection(player_id)
                else:
                    await self.game_engine.connection_manager.send_message(player_id, "Invalid choice. Try again.")
                    await self._show_class_selection(player_id)
            except ValueError:
                await self.game_engine.connection_manager.send_message(player_id, "Please enter a number.")
                await self._show_class_selection(player_id)

    async def _create_character_with_selection(self, player_id: int):
        """Create character with selected race and class."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        username = player_data.get('username')
        selected_race = player_data.get('selected_race', 'human')
        selected_class = player_data.get('selected_class', 'fighter')

        races = self._load_races()
        classes = self._load_classes()
        race_data = races.get(selected_race, races['human'])
        class_data = classes.get(selected_class, classes['fighter'])

        # Get starting room from world manager
        starting_room = self.game_engine.world_manager.get_default_starting_room()

        # Roll random stats (3d6 for each stat)
        import random
        def roll_stat():
            return sum(random.randint(1, 6) for _ in range(3))

        base_stats = {
            'strength': roll_stat(),
            'dexterity': roll_stat(),
            'constitution': roll_stat(),
            'intellect': roll_stat(),
            'wisdom': roll_stat(),
            'charisma': roll_stat()
        }

        # Apply race base stats if no random (use race base instead)
        # Apply race modifiers
        for stat, value in race_data.get('stat_modifiers', {}).items():
            base_stats[stat] = base_stats.get(stat, 10) + value

        # Apply class modifiers
        for stat, value in class_data.get('stat_modifiers', {}).items():
            base_stats[stat] = base_stats.get(stat, 10) + value

        character = {
            'name': username,
            'room_id': starting_room,
            'species': race_data['name'],
            'class': class_data['name'],
            'level': 1,
            'experience': 0,
            'rune': 'None',
            **base_stats
        }

        # Calculate max hit points with class modifier
        # Formula: (Constitution * 5) + random(1-10) + level bonus * class HP modifier
        constitution = character['constitution']
        hp_modifier = class_data.get('hp_modifier', 1.0)
        base_hp = constitution * 5
        random_hp = random.randint(1, 10)
        level_bonus = (character['level'] - 1) * 5
        max_hp = int((base_hp + random_hp + level_bonus) * hp_modifier)

        # Calculate max mana with class modifier
        intellect = character['intellect']
        mana_modifier = class_data.get('mana_modifier', 1.0)
        base_mana = intellect * 3
        random_mana = random.randint(1, 5)
        max_mana = int((base_mana + random_mana) * mana_modifier)

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

            # Hunger and Thirst (0-100, 100 = fully fed/hydrated)
            'hunger': 100,
            'thirst': 100,

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

            # Magic
            'spellbook': [],  # Known spells
            'spell_cooldowns': {},  # Spell cooldowns {spell_id: tick_remaining}
            'active_effects': [],  # Active buffs/debuffs

            # Map exploration
            'visited_rooms': {starting_room},  # Track visited rooms for map
        })

        # Give starting spells based on class
        class_spells = {
            'Mage': ['magic_missile', 'shield'],
            'Cleric': ['heal', 'cure_wounds'],
            'Ranger': ['cure_wounds']
        }
        if class_data['name'] in class_spells:
            character['spellbook'] = class_spells[class_data['name']].copy()

        # Calculate initial encumbrance based on starting gold and strength
        self.game_engine.player_manager.update_encumbrance(character)

        # Set character and clear creation flags
        self.game_engine.player_manager.set_player_character(player_id, character)
        player_data['creating_character'] = False
        player_data['char_creation_step'] = None

        # Show character stats
        stats_msg = f"\n=== Character Created ===\n"
        stats_msg += f"Race: {character['species']}\n"
        stats_msg += f"Class: {character['class']}\n\n"
        stats_msg += f"STR: {character['strength']}  DEX: {character['dexterity']}  CON: {character['constitution']}\n"
        stats_msg += f"INT: {character['intellect']}  WIS: {character['wisdom']}  CHA: {character['charisma']}\n\n"
        stats_msg += f"HP: {max_hp}  Mana: {max_mana}\n"

        await self.game_engine.connection_manager.send_message(player_id, stats_msg)
        await self.game_engine.connection_manager.send_message(player_id, f"Welcome to the world, {username}!")
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

        elif command in ['map', 'worldmap']:
            # Show map of areas and rooms
            await self._handle_map_command(player_id, character, params)

        elif command in ['help', '?']:
            help_text = """
Available Commands:
==================
look (l)        - Look around or examine target
help (?)        - Show this help
exits           - Show exits
stats (st)      - Show character stats
reroll          - Reroll stats (level 1, 0 XP only)
train           - Level up at a trainer
inventory (i)   - Show inventory
spellbook (sb)  - Show learned spells
get <item>      - Pick up an item
drop <item>     - Drop an item
eat <item>      - Eat food
drink <item>    - Drink beverage
read <item>     - Read a scroll to learn a spell
equip <item>    - Equip weapon or armor
unequip <item>  - Unequip weapon or armor
list            - Show vendor wares
buy <item>      - Buy from vendor
sell <item>     - Sell to vendor

Combat Commands:
===============
attack <target> - Attack a target
cast <spell>    - Cast a spell
flee            - Try to flee from combat

Movement:
=========
north (n)       - Go north
south (s)       - Go south
east (e)        - Go east
west (w)        - Go west
up (u)          - Go up
down (d)        - Go down
map [area]      - Show world map or detailed area map
quit (q)        - Quit the game

Admin Commands (Debug):
======================
givegold <amt>  - Give yourself gold
giveitem <id>   - Give yourself an item
givexp <amt>    - Give yourself experience
mobstatus       - Show all mobs and their flags
teleport <room> - Teleport to a room (or 'teleport <player> <room>')
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

        elif command == 'reroll':
            await self._handle_reroll_command(player_id, character)

        elif command == 'train':
            await self._handle_train_command(player_id, character)

        elif command in ['inventory', 'inv', 'i']:
            await self._handle_inventory_command(player_id, character)

        elif command in ['spellbook', 'spells', 'sb']:
            await self._handle_spellbook_command(player_id, character)

        elif command in ['cast', 'c'] and params:
            await self._handle_cast_command(player_id, character, params)

        elif command in ['cast', 'c']:
            await self.game_engine.connection_manager.send_message(player_id, "Cast what spell? Use 'spellbook' to see your spells.")

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

        elif command in ['eat', 'consume'] and params:
            # Eat food to restore hunger
            await self._handle_eat_command(player_id, params)

        elif command in ['eat', 'consume']:
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to eat?")

        elif command in ['drink', 'dr', 'quaff'] and params:
            # Drink to restore thirst
            await self._handle_drink_command(player_id, params)

        elif command in ['drink', 'dr', 'quaff']:
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to drink?")

        elif command in ['read', 'study'] and params:
            # Read a scroll to learn a spell
            await self._handle_read_command(player_id, params)

        elif command in ['read', 'study']:
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to read?")

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

        elif command in ['buy', 'b', 'sell'] and params:
            # Handle buying/selling with vendors
            await self._handle_trade_command(player_id, command, params)

        elif command in ['list', 'wares']:
            # Show vendor inventory if in vendor room
            # Support "list" or "list <vendor_name>"
            await self._handle_list_vendor_items(player_id, params if params else None)

        elif command in ['heal', 'healing'] and params:
            # Handle healing at a temple/healer
            await self._handle_heal_command(player_id, params)

        elif command in ['heal', 'healing']:
            # Show healing options
            await self._handle_heal_command(player_id, "list")

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

        # Quest commands
        elif command in ['quest', 'quests', 'questlog']:
            await self._handle_quest_log(player_id, character)

        elif command in ['talk', 'speak'] and params:
            await self._handle_talk_to_npc(player_id, character, params)

        elif command in ['talk', 'speak']:
            await self.game_engine.connection_manager.send_message(player_id, "Who would you like to talk to?")

        elif command == 'accept' and params:
            await self._handle_accept_quest(player_id, character, params)

        elif command == 'accept':
            await self.game_engine.connection_manager.send_message(player_id, "What quest would you like to accept?")

        # Admin commands
        elif command == 'givegold' and params:
            await self._handle_admin_give_gold(player_id, character, params)

        elif command == 'givegold':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: givegold <amount>")

        elif command == 'giveitem' and params:
            await self._handle_admin_give_item(player_id, character, params)

        elif command == 'giveitem':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: giveitem <item_id>")

        elif command == 'givexp' and params:
            await self._handle_admin_give_xp(player_id, character, params)

        elif command == 'givexp':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: givexp <amount>")

        elif command == 'respawnnpc' and params:
            await self._handle_admin_respawn_npc(player_id, character, params)

        elif command == 'respawnnpc':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: respawnnpc <npc_id>")

        elif command == 'completequest' and params:
            await self._handle_admin_complete_quest(player_id, character, params)

        elif command == 'completequest':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: completequest <quest_id>")

        elif command == 'mobstatus':
            await self._handle_admin_mob_status(player_id)

        elif command == 'teleport' and params:
            await self._handle_admin_teleport(player_id, character, params)

        elif command == 'teleport':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: teleport <room_id> OR teleport <player_name> <room_id>")

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

        # Determine status based on hunger/thirst
        hunger = char.get('hunger', 100)
        thirst = char.get('thirst', 100)
        low_threshold = self.game_engine.config_manager.get_setting('player', 'hunger_thirst', 'low_warning_threshold', default=20)
        status_conditions = []

        if hunger <= 0:
            status_conditions.append("Starving")
        elif hunger <= low_threshold:
            status_conditions.append("Hungry")

        if thirst <= 0:
            status_conditions.append("Dehydrated")
        elif thirst <= low_threshold:
            status_conditions.append("Thirsty")

        # Use existing status or build from conditions
        if status_conditions:
            status = ", ".join(status_conditions)
        else:
            status = char.get('status', 'Healthy')

        # Calculate XP progress
        current_level = char.get('level', 1)
        current_xp = char.get('experience', 0)
        xp_for_next = self.calculate_xp_for_level(current_level + 1)
        xp_remaining = xp_for_next - current_xp

        stats_text = f"""
Name:          {char['name']}
Species:       {char['species']}
Class:         {char['class']}
Level:         {char['level']}
Experience:    {char['experience']}/{xp_for_next} ({xp_remaining} to next level)
Rune:          {char['rune']}

Intellect:     {char['intellect']}
Wisdom:        {char['wisdom']}
Strength:      {char['strength']}
Constitution:  {char['constitution']}
Dexterity:     {char['dexterity']}
Charisma:      {char['charisma']}

Hit Points:    {int(char.get('health', char.get('current_hit_points', 20)))} / {int(char.get('max_hit_points', 20))}
Mana:          {int(char.get('mana', char.get('current_mana', 10)))} / {int(char.get('max_mana', 10))}
Status:        {status}
Armor Class:   {self.get_effective_armor_class(char)}

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

        # Item not found on floor or in config
        await self.game_engine.connection_manager.send_message(player_id, f"You don't see a {item_name} here.")

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
            # If multiple matches, just drop the first one
            pass  # item_to_drop and item_index are already set to the first match

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

    async def _handle_eat_command(self, player_id: int, item_name: str):
        """Handle eating food to restore hunger."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find food item
        item_to_eat, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name}.")
            return
        elif match_type == 'multiple':
            # If multiple matches, just eat the first one
            pass  # item_to_eat and item_index are already set to the first match

        # Check if item is food
        item_type = item_to_eat.get('type', '')
        if item_type != 'food':
            await self.game_engine.connection_manager.send_message(player_id, f"You can't eat {item_to_eat['name']}!")
            return

        # Get nutrition value (default 30 if not specified)
        nutrition = item_to_eat.get('nutrition', 30)

        # Restore hunger
        current_hunger = character.get('hunger', 100)
        new_hunger = min(100, current_hunger + nutrition)
        character['hunger'] = new_hunger

        # Remove item from inventory
        character['inventory'].pop(item_index)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"You eat {item_to_eat['name']}. Your hunger is restored. (Hunger: {new_hunger:.0f}/100)"
        )

    async def _handle_drink_command(self, player_id: int, item_name: str):
        """Handle drinking to restore thirst or consume potions."""
        import re

        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find drink item
        item_to_drink, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name}.")
            return
        elif match_type == 'multiple':
            # If multiple matches, just drink the first one
            pass  # item_to_drink and item_index are already set to the first match

        # Check if item is a drink or consumable
        item_type = item_to_drink.get('type', '')
        if item_type not in ['drink', 'potion', 'consumable']:
            await self.game_engine.connection_manager.send_message(player_id, f"You can't drink {item_to_drink['name']}!")
            return

        # Initialize messages list
        messages = []
        messages.append(f"You drink {item_to_drink['name']}.")

        # Get item properties
        properties = item_to_drink.get('properties', {})

        # Handle health restoration
        if 'restore_health' in properties:
            restore_health = properties['restore_health']

            # Parse health value (can be integer or dice notation like "4-16")
            if isinstance(restore_health, str):
                # Handle range notation like "4-16" or "32-128"
                if '-' in restore_health:
                    min_val, max_val = map(int, restore_health.split('-'))
                    import random
                    health_amount = random.randint(min_val, max_val)
                else:
                    health_amount = int(restore_health)
            else:
                health_amount = int(restore_health)

            current_health = character.get('health', character.get('current_hit_points', 0))
            max_health = character.get('max_hit_points', 100)
            new_health = min(max_health, current_health + health_amount)

            character['health'] = new_health
            character['current_hit_points'] = new_health

            messages.append(f"You restore {health_amount} health! (HP: {new_health}/{max_health})")

        # Handle mana restoration
        if 'restore_mana' in properties:
            restore_mana = properties['restore_mana']
            mana_amount = int(restore_mana)

            current_mana = character.get('mana', character.get('current_mana', 0))
            max_mana = character.get('max_mana', 50)
            new_mana = min(max_mana, current_mana + mana_amount)

            character['mana'] = new_mana
            character['current_mana'] = new_mana

            messages.append(f"You restore {mana_amount} mana! (Mana: {new_mana}/{max_mana})")

        # Handle cure poison
        if properties.get('cure_poison'):
            # Initialize active_effects if needed
            if 'active_effects' not in character:
                character['active_effects'] = []

            # Remove poison effects
            original_count = len(character['active_effects'])
            character['active_effects'] = [
                effect for effect in character['active_effects']
                if effect.get('effect') != 'poison'
            ]

            if len(character['active_effects']) < original_count:
                messages.append("The poison leaves your body!")
            else:
                messages.append("You feel cleansed, though you weren't poisoned.")

        # Handle stat boost potions
        boost_duration = properties.get('boost_duration', 0)
        if boost_duration > 0:
            # Initialize active_effects if needed
            if 'active_effects' not in character:
                character['active_effects'] = []

            # Strength boost
            if 'strength_bonus' in properties:
                str_bonus = properties['strength_bonus']
                buff = {
                    'spell_id': item_to_drink.get('name', 'Strength Potion'),
                    'effect': 'strength_bonus',
                    'duration': boost_duration,
                    'bonus_amount': str_bonus
                }
                character['active_effects'].append(buff)
                messages.append(f"You feel stronger! (+{str_bonus} STR for {boost_duration} rounds)")

            # Dexterity boost
            if 'dexterity_bonus' in properties:
                dex_bonus = properties['dexterity_bonus']
                buff = {
                    'spell_id': item_to_drink.get('name', 'Dexterity Potion'),
                    'effect': 'dexterity_bonus',
                    'duration': boost_duration,
                    'bonus_amount': dex_bonus
                }
                character['active_effects'].append(buff)
                messages.append(f"You feel more agile! (+{dex_bonus} DEX for {boost_duration} rounds)")

        # Handle invisibility
        if 'invisibility_duration' in properties:
            invis_duration = properties['invisibility_duration']

            # Initialize active_effects if needed
            if 'active_effects' not in character:
                character['active_effects'] = []

            buff = {
                'spell_id': item_to_drink.get('name', 'Invisibility Potion'),
                'effect': 'invisibility',
                'duration': invis_duration,
                'bonus_amount': 1
            }
            character['active_effects'].append(buff)
            messages.append(f"You fade from view! (Invisible for {invis_duration} rounds)")

        # Handle hydration (for drinks)
        hydration = item_to_drink.get('hydration', 0)
        if hydration > 0:
            current_thirst = character.get('thirst', 100)
            new_thirst = min(100, current_thirst + hydration)
            character['thirst'] = new_thirst
            messages.append(f"Your thirst is quenched. (Thirst: {new_thirst:.0f}/100)")

        # Remove item from inventory
        character['inventory'].pop(item_index)

        # Send all messages
        await self.game_engine.connection_manager.send_message(
            player_id,
            "\n".join(messages)
        )

    async def _handle_read_command(self, player_id: int, item_name: str):
        """Handle reading a spell scroll to learn a spell."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find scroll item
        item_to_read, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name}.")
            return
        elif match_type == 'multiple':
            # If multiple matches, just read the first one
            pass  # item_to_read and item_index are already set to the first match

        # Check if item is a spell scroll
        item_type = item_to_read.get('type', '')
        if item_type != 'spell_scroll':
            await self.game_engine.connection_manager.send_message(player_id, f"You can't read {item_to_read['name']} to learn a spell!")
            return

        # Get scroll properties
        properties = item_to_read.get('properties', {})
        spell_id = properties.get('spell_id')

        if not spell_id:
            await self.game_engine.connection_manager.send_message(player_id, f"This scroll doesn't contain a spell!")
            return

        # Check if player already knows the spell
        spellbook = character.get('spellbook', [])
        if spell_id in spellbook:
            await self.game_engine.connection_manager.send_message(player_id, f"You already know this spell!")
            return

        # Check requirements
        requirements = properties.get('requirements', {})
        min_level = requirements.get('min_level', 1)
        min_intelligence = requirements.get('min_intelligence', 0)

        player_level = character.get('level', 1)
        player_intelligence = character.get('intelligence', 10)

        # Check level requirement
        if player_level < min_level:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You must be at least level {min_level} to learn this spell! (You are level {player_level})"
            )
            return

        # Check intelligence requirement
        if player_intelligence < min_intelligence:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You need at least {min_intelligence} Intelligence to learn this spell! (You have {player_intelligence})"
            )
            return

        # Learn the spell!
        if 'spellbook' not in character:
            character['spellbook'] = []

        character['spellbook'].append(spell_id)

        # Remove scroll from inventory
        character['inventory'].pop(item_index)

        # Get spell data for the message
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})
        spell = spell_data.get(spell_id, {})
        spell_name = spell.get('name', spell_id)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"You carefully study the scroll and learn the spell: {spell_name}!"
        )

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
            # If multiple matches, just equip the first one
            pass  # item_to_equip and item_index are already set to the first match

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

        # Update encumbrance (should be same, but recalculate for consistency)
        self.game_engine.player_manager.update_encumbrance(character)

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

        # Update encumbrance
        self.game_engine.player_manager.update_encumbrance(character)

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
        monsters = self.game_engine._load_all_monsters()
        if not monsters:
            await self.game_engine.connection_manager.send_message(player_id, "The gong rings out, but something went wrong with the ancient magic...")
            print(f"[ERROR] Failed to load monsters")
            return

        # Select a random monster
        monsters_list = list(monsters.values())
        if not monsters_list:
            await self.game_engine.connection_manager.send_message(player_id, "The gong rings out, but no creatures answer its call.")
            return

        monster = random.choice(monsters_list)

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
            'damage': monster.get('damage', '1d4'),
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
        item_found_id = None
        item_price = None
        item_stock = None
        for item_entry in vendor['inventory']:
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config and item_name.lower() in item_config['name'].lower():
                item_found_id = item_id
                item_price = item_entry['price']
                item_stock = item_entry.get('stock', -1)
                break

        if not item_found_id:
            await self.game_engine.connection_manager.send_message(player_id, f"{vendor['name']} doesn't have {item_name} for sale.")
            return

        # Create proper item instance to get the real name
        item_instance = self.game_engine.config_manager.create_item_instance(item_found_id, item_price)
        if not item_instance:
            await self.game_engine.connection_manager.send_message(player_id, "Error creating item.")
            return

        # Check if vendor has stock (stock of -1 means unlimited)
        if item_stock == 0:
            await self.game_engine.connection_manager.send_message(player_id, f"{vendor['name']} is out of stock of {item_instance['name']}.")
            return

        # Check if player has enough gold
        if character['gold'] < item_price:
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have enough gold. {item_instance['name']} costs {item_price} gold.")
            return

        # Check encumbrance before buying
        current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
        item_weight = item_instance.get('weight', 0)
        gold_weight_change = -item_price / 100.0  # Losing gold reduces weight
        max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)

        if current_encumbrance + item_weight + gold_weight_change > max_encumbrance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cannot carry {item_instance['name']} - you are carrying too much!"
            )
            return

        # Complete the purchase
        character['gold'] -= item_price
        character['inventory'].append(item_instance)

        # Reduce vendor stock (if not unlimited)
        self.game_engine.vendor_system.reduce_vendor_stock(vendor, item_found_id, 1)

        # Update encumbrance (accounts for gold weight change and new item)
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"You buy {item_instance['name']} for {item_price} gold.")

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

        # Debug logging
        from server.utils.logger import get_logger
        logger = get_logger()
        logger.info(f"[SELL] Searching for '{item_name}' in inventory")
        logger.info(f"[SELL] Inventory has {len(inventory)} items")
        for i, item in enumerate(inventory):
            logger.info(f"[SELL]   {i}: {item}")

        item_to_sell, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        logger.info(f"[SELL] Match result: match_type='{match_type}', item_to_sell={item_to_sell}, item_index={item_index}")

        if match_type == 'none' or item_to_sell is None:
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name} to sell.")
            return
        elif match_type == 'multiple':
            # If multiple matches, just sell the first one
            # This is the standard MUD behavior - "sell bread" sells one bread if you have multiple
            pass  # item_to_sell and item_index are already set to the first match

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

        # Check for NPCs
        room = self.game_engine.world_manager.get_room(room_id)
        if room and room.npcs:
            for npc in room.npcs:
                if target_lower in npc.name.lower() or target_lower in npc.npc_id.lower():
                    description = npc.description
                    await self.game_engine.connection_manager.send_message(player_id, f"You look at {npc.name}: {description}")
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

    async def _handle_heal_command(self, player_id: int, params: str):
        """Handle healing command at a temple/healer."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        character = player_data.get('character', {})
        room_id = character.get('room_id')

        # Get room object
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            await self.game_engine.connection_manager.send_message(player_id, "You are nowhere!")
            return

        # Get NPCs in the room
        npcs_in_room = room.npcs if hasattr(room, 'npcs') else []
        print(f"[HEAL DEBUG] Room: {room_id}, NPCs: {npcs_in_room}")

        # Find a healer NPC
        healer_npc = None
        for npc_id in npcs_in_room:
            npc = self.game_engine.world_manager.npcs.get(npc_id)
            print(f"[HEAL DEBUG] Checking NPC {npc_id}: {npc}")
            if npc:
                print(f"[HEAL DEBUG] NPC services: {npc.get('services', [])}")
                if 'healer' in npc.get('services', []):
                    healer_npc = npc
                    break

        if not healer_npc:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "There is no healer here. You must find a temple or healer to receive healing."
            )
            return

        # Show healing options if "list" or list available healing
        if params.lower() in ['list', 'options', 'help']:
            healing_options = healer_npc.get('healing', {})
            if not healing_options:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"{healer_npc['name']} doesn't seem to offer healing services."
                )
                return

            message = f"\n{healer_npc['name']} offers the following healing services:\n\n"
            for heal_type, heal_data in healing_options.items():
                heal_amount = heal_data.get('heal_amount', 0)
                if heal_amount == 'full':
                    heal_desc = "Full Health"
                else:
                    heal_desc = f"{heal_amount} HP"
                message += f"  {heal_data['name']:20} - {heal_desc:12} ({heal_data['cost']} gold)\n"
            message += f"\nUse 'heal <type>' to receive healing. Example: heal minor"

            await self.game_engine.connection_manager.send_message(player_id, message)
            return

        # Find matching heal type
        healing_options = healer_npc.get('healing', {})
        heal_type = None
        for key in healing_options.keys():
            if params.lower() in key.lower() or key.lower().startswith(params.lower()):
                heal_type = key
                break

        if not heal_type:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"I don't recognize that healing type. Use 'heal list' to see available options."
            )
            return

        heal_data = healing_options[heal_type]
        cost = heal_data['cost']
        heal_amount = heal_data['heal_amount']

        # Check if player has enough gold
        player_gold = character.get('gold', 0)
        if player_gold < cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't have enough gold. {heal_data['name']} costs {cost} gold, but you only have {player_gold} gold."
            )
            return

        # Check if player needs healing
        current_health = character.get('health', 0)
        max_health = character.get('max_hit_points', current_health)

        if current_health >= max_health:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You are already at full health!"
            )
            return

        # Apply healing
        if heal_amount == 'full':
            actual_heal = max_health - current_health
            character['health'] = max_health
        else:
            actual_heal = min(heal_amount, max_health - current_health)
            character['health'] = min(current_health + heal_amount, max_health)

        # Deduct gold
        character['gold'] = player_gold - cost

        # Send message
        await self.game_engine.connection_manager.send_message(
            player_id,
            f"{healer_npc['name']} channels healing energy into you. You are healed for {int(actual_heal)} HP!\nYou paid {cost} gold.\n\nHealth: {int(character['health'])} / {int(max_health)}"
        )

    async def _handle_spellbook_command(self, player_id: int, character: dict):
        """Display the player's spellbook with all known spells."""
        spellbook = character.get('spellbook', [])

        if not spellbook:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "Your spellbook is empty. You haven't learned any spells yet."
            )
            return

        # Load spell data
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})

        # Build spellbook display
        lines = ["=== Your Spellbook ===\n"]

        for spell_id in spellbook:
            spell = spell_data.get(spell_id)
            if not spell:
                continue

            # Get cooldown info
            cooldowns = character.get('spell_cooldowns', {})
            cooldown_remaining = cooldowns.get(spell_id, 0)

            # Format spell entry
            name = spell['name']
            level = spell['level']
            mana = spell['mana_cost']
            spell_type = spell['type']

            # Type-specific info
            type_info = ""
            if spell_type == 'damage':
                damage = spell.get('damage', '?')
                damage_type = spell.get('damage_type', 'physical')
                type_info = f"Damage: {damage} ({damage_type})"
            elif spell_type == 'heal':
                heal = spell.get('heal_amount', '?')
                type_info = f"Healing: {heal}"
            elif spell_type == 'buff':
                effect = spell.get('effect', 'unknown')
                duration = spell.get('duration', 0)
                type_info = f"Effect: {effect} ({duration} rounds)"

            cooldown_text = ""
            if cooldown_remaining > 0:
                cooldown_text = f" [COOLDOWN: {cooldown_remaining} rounds]"

            lines.append(f"{name} (Level {level}) - {mana} mana{cooldown_text}")
            lines.append(f"  {spell['description']}")
            if type_info:
                lines.append(f"  {type_info}")
            lines.append("")

        await self.game_engine.connection_manager.send_message(
            player_id,
            "\n".join(lines)
        )

    async def _handle_cast_command(self, player_id: int, character: dict, params: str):
        """Handle casting a spell."""
        # Parse spell name and optional target from params
        # Format: "cast <spell_name> [target_name]"
        parts = params.strip().split(None, 1)  # Split on first whitespace
        spell_input = parts[0] if parts else ""
        target_name = parts[1] if len(parts) > 1 else None

        # Load spell data
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})
        spellbook = character.get('spellbook', [])

        # Find the spell
        spell_id = None
        spell = None

        # Try exact match first (using underscore version)
        spell_key = spell_input.lower().replace(' ', '_')
        if spell_key in spell_data:
            spell_id = spell_key
            spell = spell_data[spell_id]
        else:
            # Try partial match on spell name
            for sid, s in spell_data.items():
                if spell_input.lower() in s['name'].lower():
                    spell_id = sid
                    spell = s
                    break

        if not spell:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Unknown spell: {spell_input}"
            )
            return

        # Check if player knows this spell
        if spell_id not in spellbook:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't know the spell '{spell['name']}'."
            )
            return

        # Check cooldown
        cooldowns = character.get('spell_cooldowns', {})
        if spell_id in cooldowns and cooldowns[spell_id] > 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"{spell['name']} is still on cooldown ({cooldowns[spell_id]} rounds remaining)."
            )
            return

        # Check if player is magically fatigued (for damage spells only)
        if spell['type'] == 'damage':
            if self._is_spell_fatigued(player_id):
                fatigue_time = self._get_spell_fatigue_remaining(player_id)
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You are too magically exhausted to cast offensive spells! Wait {fatigue_time:.1f} more seconds."
                )
                return

        # Check mana
        mana_cost = spell['mana_cost']
        current_mana = character.get('mana', 0)

        if current_mana < mana_cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't have enough mana to cast {spell['name']}. (Need {mana_cost}, have {current_mana})"
            )
            return

        # Deduct mana
        character['mana'] = current_mana - mana_cost

        # Apply spell fatigue for damage spells
        # Cooldown acts as a multiplier: 0 = 10s, 1 = 10s, 2 = 20s, 3 = 30s, etc.
        if spell['type'] == 'damage':
            cooldown = spell.get('cooldown', 0)
            multiplier = max(1, cooldown)  # Minimum 1x for cooldown 0 or 1
            self._apply_spell_fatigue(player_id, multiplier)

        # Set cooldown (no longer used for fatigue, kept for potential future use)
        if spell.get('cooldown', 0) > 0:
            if 'spell_cooldowns' not in character:
                character['spell_cooldowns'] = {}
            character['spell_cooldowns'][spell_id] = spell['cooldown']

        # Apply spell effect based on type
        room_id = character.get('room_id')

        if spell['type'] == 'damage':
            await self._cast_damage_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] == 'heal':
            await self._cast_heal_spell(player_id, character, spell)
        elif spell['type'] == 'buff':
            await self._cast_buff_spell(player_id, character, spell)

    async def _cast_damage_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a damage spell."""
        # Check if spell requires target
        if spell.get('requires_target', False):
            if not target_name:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You need a target to cast {spell['name']}. Use: cast {spell['name']} <target>"
                )
                return

            # Find target using combat system's method
            target = await self.game_engine.combat_system.find_combat_target(room_id, target_name)

            if not target:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You don't see '{target_name}' here."
                )
                return

            # Roll damage
            damage_roll = spell.get('damage', '1d6')
            damage = self._roll_dice(damage_roll)

            # Apply damage
            target['health'] -= damage

            # Send messages
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cast {spell['name']}! It strikes {target['name']} for {int(damage)} {spell.get('damage_type', 'magical')} damage!"
            )

            # Notify room
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} casts {spell['name']} at {target['name']}!"
            )

            # Check if mob died
            if target['health'] <= 0:
                # Send death message
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"{target['name']} has been defeated!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{target['name']} has been defeated!"
                )

                # Handle loot, gold, and experience
                await self.game_engine.combat_system.handle_mob_loot_drop(player_id, target, room_id)

                # Remove mob from room
                mob_participant_id = f"mob_{target.get('id', 'unknown')}"
                await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)

        else:
            # Area spell (no specific target needed)
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cast {spell['name']}! (Area spells not yet fully implemented)"
            )

    async def _cast_heal_spell(self, player_id: int, character: dict, spell: dict):
        """Cast a healing spell."""
        # Roll healing amount
        heal_roll = spell.get('heal_amount', '1d8')
        heal_amount = self._roll_dice(heal_roll)

        # Get current and max health
        current_health = character.get('health', 0)
        max_health = character.get('max_hit_points', 100)

        # Apply healing
        actual_heal = min(heal_amount, max_health - current_health)
        character['health'] = min(current_health + heal_amount, max_health)

        # Send message
        await self.game_engine.connection_manager.send_message(
            player_id,
            f"You cast {spell['name']}! You are healed for {int(actual_heal)} HP.\nHealth: {int(character['health'])} / {int(max_health)}"
        )

        # Notify room
        room_id = character.get('room_id')
        await self.game_engine.player_manager.notify_room_except_player(
            room_id,
            player_id,
            f"{character.get('name', 'Someone')} casts {spell['name']} and glows with healing energy!"
        )

    async def _cast_buff_spell(self, player_id: int, character: dict, spell: dict):
        """Cast a buff spell."""
        effect = spell.get('effect', 'unknown')
        duration = spell.get('duration', 0)

        # Initialize active_effects if needed
        if 'active_effects' not in character:
            character['active_effects'] = []

        # Add the buff
        buff = {
            'spell_id': spell.get('name', 'Unknown'),
            'effect': effect,
            'duration': duration,
            'bonus_amount': spell.get('bonus_amount', 0)
        }
        character['active_effects'].append(buff)

        # Send message
        await self.game_engine.connection_manager.send_message(
            player_id,
            f"You cast {spell['name']}! {spell['description']}"
        )

        # Notify room
        room_id = character.get('room_id')
        await self.game_engine.player_manager.notify_room_except_player(
            room_id,
            player_id,
            f"{character.get('name', 'Someone')} casts {spell['name']}!"
        )

    def _roll_dice(self, dice_string: str) -> int:
        """Roll dice from a string like '2d6+3' or '1d8'."""
        import re

        # Parse the dice string
        match = re.match(r'(\d+)d(\d+)([+-]\d+)?', dice_string.lower())
        if not match:
            return 0

        num_dice = int(match.group(1))
        die_size = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0

        # Roll the dice
        total = sum(random.randint(1, die_size) for _ in range(num_dice))
        return total + modifier

    def _is_spell_fatigued(self, player_id: int) -> bool:
        """Check if a player is currently spell fatigued."""
        if player_id not in self.game_engine.spell_fatigue:
            return False

        fatigue_info = self.game_engine.spell_fatigue[player_id]
        current_time = time.time()

        if 'fatigue_end_time' not in fatigue_info:
            del self.game_engine.spell_fatigue[player_id]
            return False

        if fatigue_info['fatigue_end_time'] == 0:
            return False

        if current_time >= fatigue_info['fatigue_end_time']:
            del self.game_engine.spell_fatigue[player_id]
            return False

        return True

    def _get_spell_fatigue_remaining(self, player_id: int) -> float:
        """Get remaining spell fatigue time in seconds."""
        if player_id not in self.game_engine.spell_fatigue:
            return 0.0

        fatigue_info = self.game_engine.spell_fatigue[player_id]
        if 'fatigue_end_time' not in fatigue_info:
            return 0.0

        current_time = time.time()
        remaining = fatigue_info['fatigue_end_time'] - current_time
        return max(0.0, remaining)

    def _apply_spell_fatigue(self, player_id: int, multiplier: float = 1.0):
        """Apply spell fatigue to a player.

        Args:
            player_id: The player ID
            multiplier: Fatigue duration multiplier (base 10 seconds * multiplier)
        """
        base_duration = 10.0  # Base fatigue duration in seconds
        duration = base_duration * multiplier

        self.game_engine.spell_fatigue[player_id] = {
            'fatigue_end_time': time.time() + duration
        }

    def get_effective_armor_class(self, character: dict) -> int:
        """Calculate effective armor class including buffs.

        Args:
            character: The character dict

        Returns:
            Total armor class including base AC and buff bonuses
        """
        base_ac = character.get('armor_class', 0)

        # Add bonuses from active buffs
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('effect') == 'ac_bonus':
                base_ac += effect.get('bonus_amount', 0)

        return base_ac

    def calculate_xp_for_level(self, level: int) -> int:
        """Calculate the total XP required to reach a specific level.

        Args:
            level: The target level

        Returns:
            Total XP required to reach that level
        """
        if level <= 1:
            return 0

        base_xp = self.game_engine.config_manager.get_setting('player', 'leveling', 'base_xp_per_level', default=100)
        multiplier = self.game_engine.config_manager.get_setting('player', 'leveling', 'xp_multiplier', default=1.5)

        # Calculate cumulative XP: sum of XP needed for each level
        total_xp = 0
        for lvl in range(2, level + 1):
            xp_for_level = int(base_xp * (multiplier ** (lvl - 2)))
            total_xp += xp_for_level

        return total_xp

    def get_xp_to_next_level(self, character: dict) -> int:
        """Calculate XP needed to reach the next level.

        Args:
            character: The character dict

        Returns:
            XP needed for next level
        """
        current_level = character.get('level', 1)
        current_xp = character.get('experience', 0)

        xp_for_next_level = self.calculate_xp_for_level(current_level + 1)
        return xp_for_next_level - current_xp

    async def _handle_reroll_command(self, player_id: int, character: dict):
        """Handle the reroll command to reroll stats for level 1 characters."""
        # Check if character is level 1
        if character.get('level', 1) != 1:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You can only reroll stats at level 1!"
            )
            return

        # Check if character has gained any experience
        if character.get('experience', 0) > 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You can only reroll stats if you haven't gained any experience yet!"
            )
            return

        # Get race and class data
        races = self._load_races()
        classes = self._load_classes()

        # Find race key from name
        race_key = None
        for key, data in races.items():
            if data['name'] == character.get('species'):
                race_key = key
                break

        # Find class key from name
        class_key = None
        for key, data in classes.items():
            if data['name'] == character.get('class'):
                class_key = key
                break

        if not race_key or not class_key:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "Error: Could not find your race or class data."
            )
            return

        race_data = races[race_key]
        class_data = classes[class_key]

        # Roll new random stats (3d6 for each stat)
        import random
        def roll_stat():
            return sum(random.randint(1, 6) for _ in range(3))

        old_stats = {
            'strength': character.get('strength', 10),
            'dexterity': character.get('dexterity', 10),
            'constitution': character.get('constitution', 10),
            'intellect': character.get('intellect', 10),
            'wisdom': character.get('wisdom', 10),
            'charisma': character.get('charisma', 10)
        }

        base_stats = {
            'strength': roll_stat(),
            'dexterity': roll_stat(),
            'constitution': roll_stat(),
            'intellect': roll_stat(),
            'wisdom': roll_stat(),
            'charisma': roll_stat()
        }

        # Apply race modifiers
        for stat, value in race_data.get('stat_modifiers', {}).items():
            base_stats[stat] = base_stats.get(stat, 10) + value

        # Apply class modifiers
        for stat, value in class_data.get('stat_modifiers', {}).items():
            base_stats[stat] = base_stats.get(stat, 10) + value

        # Update character stats
        character.update(base_stats)

        # Recalculate max hit points
        constitution = character['constitution']
        hp_modifier = class_data.get('hp_modifier', 1.0)
        base_hp = constitution * 5
        random_hp = random.randint(1, 10)
        max_hp = int((base_hp + random_hp) * hp_modifier)

        # Recalculate max mana
        intellect = character['intellect']
        mana_modifier = class_data.get('mana_modifier', 1.0)
        base_mana = intellect * 3
        random_mana = random.randint(1, 5)
        max_mana = int((base_mana + random_mana) * mana_modifier)

        # Update HP and mana
        old_max_hp = character.get('max_hit_points', 0)
        old_max_mana = character.get('max_mana', 0)

        character['max_hit_points'] = max_hp
        character['health'] = max_hp
        character['current_hit_points'] = max_hp
        character['max_mana'] = max_mana
        character['mana'] = max_mana
        character['current_mana'] = max_mana

        # Update max encumbrance based on new strength
        self.game_engine.player_manager.update_encumbrance(character)

        # Show before and after stats
        reroll_msg = f"""
=== Stats Rerolled! ===

Old Stats:
STR: {old_stats['strength']}  DEX: {old_stats['dexterity']}  CON: {old_stats['constitution']}
INT: {old_stats['intellect']}  WIS: {old_stats['wisdom']}  CHA: {old_stats['charisma']}
HP: {old_max_hp}  Mana: {old_max_mana}

New Stats:
STR: {character['strength']}  DEX: {character['dexterity']}  CON: {character['constitution']}
INT: {character['intellect']}  WIS: {character['wisdom']}  CHA: {character['charisma']}
HP: {max_hp}  Mana: {max_mana}
"""
        await self.game_engine.connection_manager.send_message(player_id, reroll_msg)

    async def _handle_train_command(self, player_id: int, character: dict):
        """Handle the train command to level up."""
        room_id = character.get('room_id')

        # Check if there's a trainer in the room
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You are not in a valid room."
            )
            return

        has_trainer = False
        npcs = room.npcs if hasattr(room, 'npcs') else []

        for npc in npcs:
            # Get NPC data from world manager using npc_id
            npc_data = self.game_engine.world_manager.get_npc_data(npc.npc_id)
            if npc_data:
                services = npc_data.get('services', [])
                if 'trainer' in services or 'level_up' in services:
                    has_trainer = True
                    break

        if not has_trainer:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "There is no trainer here. You must find a trainer to level up."
            )
            return

        # Get current stats
        current_level = character.get('level', 1)
        current_xp = character.get('experience', 0)
        max_level = self.game_engine.config_manager.get_setting('player', 'leveling', 'max_level', default=50)

        # Check if at max level
        if current_level >= max_level:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You have reached the maximum level of {max_level}!"
            )
            return

        # Calculate XP needed for next level
        xp_needed = self.calculate_xp_for_level(current_level + 1)
        xp_remaining = xp_needed - current_xp

        # Check if player has enough XP
        if current_xp < xp_needed:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You need {xp_remaining} more experience to reach level {current_level + 1}. (Current: {current_xp}/{xp_needed})"
            )
            return

        # Level up!
        old_level = current_level
        new_level = current_level + 1
        character['level'] = new_level

        # Get leveling bonuses from config
        hp_per_level = self.game_engine.config_manager.get_setting('player', 'leveling', 'hp_per_level', default=10)
        mana_per_level = self.game_engine.config_manager.get_setting('player', 'leveling', 'mana_per_level', default=5)
        stat_points = self.game_engine.config_manager.get_setting('player', 'leveling', 'stat_points_per_level', default=2)

        # Increase max HP
        old_max_hp = character.get('max_hit_points', 100)
        new_max_hp = old_max_hp + hp_per_level
        character['max_hit_points'] = new_max_hp

        # Increase max mana
        old_max_mana = character.get('max_mana', 50)
        new_max_mana = old_max_mana + mana_per_level
        character['max_mana'] = new_max_mana

        # Fully restore health and mana on level up
        character['health'] = new_max_hp
        character['mana'] = new_max_mana

        # Award stat points
        if 'unspent_stat_points' not in character:
            character['unspent_stat_points'] = 0
        character['unspent_stat_points'] += stat_points

        # Send level up messages
        level_up_msg = f"""
========================================
         LEVEL UP!
========================================
  Level: {old_level} -> {new_level}
  Max HP: {old_max_hp} -> {new_max_hp}
  Max Mana: {old_max_mana} -> {new_max_mana}
  Stat Points: +{stat_points}
========================================

You have {character['unspent_stat_points']} unspent stat points!
(Note: Stat allocation system coming soon)

Congratulations, {character['name']}! You feel stronger and more capable!
"""

        await self.game_engine.connection_manager.send_message(player_id, level_up_msg)

        # Notify room
        await self.game_engine.player_manager.notify_room_except_player(
            room_id,
            player_id,
            f"{character['name']} has gained a level! They are now level {new_level}!"
        )

        # Save character
        if self.game_engine.player_storage:
            username = self.game_engine.player_manager.get_player_data(player_id).get('username')
            if username:
                self.game_engine.player_storage.save_character(username, character)

    async def _handle_admin_give_gold(self, player_id: int, character: dict, params: str):
        """Admin command to give gold to the current player."""
        try:
            amount = int(params.strip())
            if amount <= 0:
                await self.game_engine.connection_manager.send_message(player_id, "Amount must be positive.")
                return

            # Add gold to character
            current_gold = character.get('gold', 0)
            character['gold'] = current_gold + amount

            # Update encumbrance for gold weight change
            self.game_engine.player_manager.update_encumbrance(character)

            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Added {amount} gold. You now have {character['gold']} gold."
            )

        except ValueError:
            await self.game_engine.connection_manager.send_message(player_id, "Invalid amount. Usage: givegold <amount>")

    async def _handle_admin_give_item(self, player_id: int, character: dict, params: str):
        """Admin command to give an item to the current player."""
        item_id = params.strip().lower()

        # Load item from items.json
        import json
        try:
            with open('data/items/items.json', 'r') as f:
                items_data = json.load(f)
        except Exception as e:
            await self.game_engine.connection_manager.send_message(player_id, f"[ADMIN] Error loading items data: {e}")
            return

        # Get the items dictionary
        items = items_data.get('items', {})
        if not items:
            await self.game_engine.connection_manager.send_message(player_id, "[ADMIN] No items found in items.json")
            return

        # Find the item
        if item_id not in items:
            await self.game_engine.connection_manager.send_message(player_id, f"[ADMIN] Item '{item_id}' not found. Available items: {', '.join(list(items.keys())[:10])}...")
            return

        item_config = items[item_id]

        # Create item instance
        import uuid
        item_instance = {
            'id': str(uuid.uuid4()),
            'item_id': item_id,
            'name': item_config.get('name', item_id),
            'type': item_config.get('type', 'misc'),
            'weight': item_config.get('weight', 0),
        }

        # Add item-specific properties
        if 'damage' in item_config:
            item_instance['damage'] = item_config['damage']
        if 'armor_class' in item_config:
            item_instance['armor_class'] = item_config['armor_class']
        if 'properties' in item_config:
            item_instance['properties'] = item_config['properties']

        # Check encumbrance
        current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
        max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)
        item_weight = item_instance.get('weight', 0)

        if current_encumbrance + item_weight > max_encumbrance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Cannot add item: would exceed max encumbrance ({max_encumbrance})."
            )
            return

        # Add to inventory
        if 'inventory' not in character:
            character['inventory'] = []
        character['inventory'].append(item_instance)

        # Update encumbrance
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Added {item_instance['name']} to your inventory."
        )

    async def _handle_admin_give_xp(self, player_id: int, character: dict, params: str):
        """Admin command to give experience to the current player."""
        try:
            amount = int(params.strip())
            if amount <= 0:
                await self.game_engine.connection_manager.send_message(player_id, "Amount must be positive.")
                return

            # Add experience
            current_xp = character.get('experience', 0)
            character['experience'] = current_xp + amount

            # Check for level up
            current_level = character.get('level', 1)
            xp_for_next = self.calculate_xp_for_level(current_level + 1)

            if character['experience'] >= xp_for_next:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"[ADMIN] Added {amount} XP. You now have {character['experience']} XP.\nYou have enough XP to level up! Find a trainer and use 'train' command."
                )
            else:
                xp_remaining = xp_for_next - character['experience']
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"[ADMIN] Added {amount} XP. You now have {character['experience']} XP. ({xp_remaining} XP until level {current_level + 1})"
                )

        except ValueError:
            await self.game_engine.connection_manager.send_message(player_id, "Invalid amount. Usage: givexp <amount>")

    async def _handle_admin_mob_status(self, player_id: int):
        """Admin command to show all mobs and their status."""
        total_mobs = 0
        wandering_count = 0
        lair_count = 0
        gong_count = 0
        other_count = 0

        status_msg = "[ADMIN] Mob Status Report\n" + "=" * 50 + "\n\n"

        for room_id, mobs in self.game_engine.room_mobs.items():
            if not mobs:
                continue

            room_mob_count = len([m for m in mobs if m is not None])
            if room_mob_count == 0:
                continue

            status_msg += f"Room: {room_id} ({room_mob_count} mobs)\n"

            for mob in mobs:
                if mob is None:
                    continue

                total_mobs += 1
                mob_name = mob.get('name', 'Unknown')
                mob_hp = mob.get('health', 0)
                mob_max_hp = mob.get('max_health', 0)
                mob_level = mob.get('level', 1)

                flags = []
                if mob.get('is_wandering'):
                    flags.append('WANDERING')
                    wandering_count += 1
                elif mob.get('is_lair_mob'):
                    flags.append('LAIR')
                    lair_count += 1
                elif mob.get('spawned_by_gong'):
                    flags.append('GONG')
                    gong_count += 1
                else:
                    flags.append('OTHER')
                    other_count += 1

                flag_str = ', '.join(flags) if flags else 'NONE'
                status_msg += f"  - {mob_name} (Lv{mob_level}) HP:{mob_hp}/{mob_max_hp} [{flag_str}]\n"

            status_msg += "\n"

        status_msg += "=" * 50 + "\n"
        status_msg += f"Total Mobs: {total_mobs}\n"
        status_msg += f"  Wandering: {wandering_count}\n"
        status_msg += f"  Lair: {lair_count}\n"
        status_msg += f"  Gong-spawned: {gong_count}\n"
        status_msg += f"  Other: {other_count}\n"

        movement_chance = self.game_engine.config_manager.get_setting('dungeon', 'wandering_mobs', 'movement_chance', default=0.2)
        enabled = self.game_engine.config_manager.get_setting('dungeon', 'wandering_mobs', 'enabled', default=False)
        status_msg += f"\nWandering System: {'ENABLED' if enabled else 'DISABLED'}\n"
        status_msg += f"Movement Chance: {movement_chance * 100}% per tick\n"

        await self.game_engine.connection_manager.send_message(player_id, status_msg)

    async def _handle_admin_teleport(self, player_id: int, character: dict, params: str):
        """Admin command to teleport self or another player to a room.

        Usage:
            teleport <room_id>              - Teleport yourself
            teleport <player_name> <room_id> - Teleport another player
        """
        parts = params.strip().split(maxsplit=1)

        if len(parts) == 1:
            # Teleport self to room
            target_room_id = parts[0]
            target_player_id = player_id
            target_character = character
            teleporter_name = character.get('name', 'Admin')
        elif len(parts) == 2:
            # Teleport another player to room
            target_player_name = parts[0]
            target_room_id = parts[1]

            # Find target player
            target_player_id = None
            target_character = None

            for pid, pdata in self.game_engine.player_manager.connected_players.items():
                char = pdata.get('character')
                if char and char.get('name', '').lower() == target_player_name.lower():
                    target_player_id = pid
                    target_character = char
                    break

            if not target_player_id:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"[ADMIN] Player '{target_player_name}' not found or not online."
                )
                return

            teleporter_name = character.get('name', 'Admin')
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "Usage: teleport <room_id> OR teleport <player_name> <room_id>"
            )
            return

        # Verify target room exists
        target_room = self.game_engine.world_manager.get_room(target_room_id)
        if not target_room:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Room '{target_room_id}' does not exist."
            )
            return

        # Get old room
        old_room_id = target_character.get('room_id')
        target_name = target_character.get('name', 'Someone')

        # Notify players in old room
        if old_room_id:
            await self.game_engine._notify_room_except_player(
                old_room_id,
                target_player_id,
                f"{target_name} vanishes in a flash of light!"
            )

        # Update character's room
        target_character['room_id'] = target_room_id

        # Notify players in new room
        await self.game_engine._notify_room_except_player(
            target_room_id,
            target_player_id,
            f"{target_name} appears in a flash of light!"
        )

        # Show room description to teleported player
        await self.game_engine.world_manager.send_room_description(target_player_id, detailed=True)

        # Confirm to admin
        if target_player_id == player_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Teleported to {target_room_id} ({target_room.title})"
            )
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Teleported {target_name} to {target_room_id} ({target_room.title})"
            )
            await self.game_engine.connection_manager.send_message(
                target_player_id,
                f"[ADMIN] You have been teleported to {target_room.title} by {teleporter_name}!"
            )

    async def _handle_admin_respawn_npc(self, player_id: int, character: dict, params: str):
        """Admin command to respawn an NPC in its original room.

        Usage: respawnnpc <npc_id>
        """
        npc_id = params.strip()

        if not npc_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: respawnnpc <npc_id>"
            )
            return

        # Check if NPC exists in the world data
        npc_data = self.game_engine.world_manager.get_npc_data(npc_id)
        if not npc_data:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] NPC '{npc_id}' not found in NPC data."
            )
            return

        # Find which room this NPC should be in
        target_room_id = None
        for room_id, room_data in self.game_engine.world_manager.rooms_data.items():
            if 'npcs' in room_data and npc_id in room_data['npcs']:
                target_room_id = room_id
                break

        if not target_room_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Could not find original room for NPC '{npc_id}'."
            )
            return

        # Get the target room
        target_room = self.game_engine.world_manager.get_room(target_room_id)
        if not target_room:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Target room '{target_room_id}' does not exist."
            )
            return

        # Check if NPC already exists in the room
        npc_already_exists = False
        for npc in target_room.npcs:
            if npc.npc_id == npc_id:
                npc_already_exists = True
                break

        if npc_already_exists:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] NPC '{npc_data.get('name', npc_id)}' already exists in room {target_room_id}."
            )
            return

        # Create and add the NPC
        from ..game.npcs.npc import NPC

        description = npc_data.get('long_description') or npc_data.get('description', 'A mysterious figure.')

        npc = NPC(
            npc_id=npc_data.get('id', npc_id),
            name=npc_data.get('name', 'Unknown NPC'),
            description=description
        )

        npc.room_id = target_room_id
        if 'type' in npc_data:
            npc.npc_type = npc_data['type']
        if 'dialogue' in npc_data:
            npc.dialogue = npc_data['dialogue']

        target_room.npcs.append(npc)

        # Notify admin
        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Respawned NPC '{npc_data.get('name', npc_id)}' in room {target_room_id} ({target_room.title})."
        )

        # Notify players in the room
        await self.game_engine._notify_room_except_player(
            target_room_id,
            player_id,
            f"{npc_data.get('name', 'Someone')} appears in a shimmer of magical energy!"
        )

    async def _handle_map_command(self, player_id: int, character: dict, params: str):
        """Show map of areas and rooms with their connections.

        Usage: map [area_id]
        """
        world_manager = self.game_engine.world_manager

        # If params provided, show specific area
        if params:
            area_id = params.strip().lower()
            area = world_manager.areas.get(area_id)

            if not area:
                await self.game_engine.connection_manager.send_message(
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
        world_manager = self.game_engine.world_manager

        lines = ["=== World Map ===\n"]

        for area_id, area in sorted(world_manager.areas.items()):
            room_count = len(area.rooms)
            lines.append(f"{area.name} ({area_id})")
            lines.append(f"  Description: {area.description}")
            lines.append(f"  Rooms: {room_count}")
            lines.append(f"  Level Range: {area.level_range[0]}-{area.level_range[1]}")
            lines.append("")

        lines.append("Use 'map <area_id>' to see detailed room connections for an area")

        await self.game_engine.connection_manager.send_message(
            player_id,
            "\n".join(lines)
        )

    async def _show_area_map(self, player_id: int, area):
        """Show detailed ASCII graphical map of an area with room connections."""
        world_manager = self.game_engine.world_manager

        lines = [f"=== {area.name} ==="]
        lines.append(f"{area.description}\n")

        # Generate ASCII map
        ascii_map = self._generate_ascii_map(area, world_manager, player_id)
        lines.extend(ascii_map)

        await self.game_engine.connection_manager.send_message(
            player_id,
            "\n".join(lines)
        )

    def _generate_ascii_map(self, area, world_manager, player_id):
        """Generate ASCII graphical map of an area."""
        from collections import deque

        # Check if we should filter by explored rooms
        show_only_explored = self.game_engine.config_manager.get_setting('world', 'map_shows_only_explored', default=True)

        # Get player's visited rooms
        visited_rooms = set()
        if show_only_explored:
            player_data = self.game_engine.player_manager.get_player_data(player_id)
            if player_data and player_data.get('character'):
                character = player_data['character']
                visited_rooms = character.get('visited_rooms', set())
                if isinstance(visited_rooms, list):
                    visited_rooms = set(visited_rooms)
                # Always include current room
                current_room = character.get('room_id')
                if current_room:
                    visited_rooms.add(current_room)

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

        # Draw rooms
        for room_id, (x, y) in room_positions.items():
            gx, gy = x - min_x + 5, y - min_y + 2
            room = displayable_rooms[room_id]

            # Determine room marker based on room properties
            room_data = world_manager.rooms_data.get(room_id, {})
            exits = room_data.get('exits', {})

            # Choose marker character
            marker = '*'
            if hasattr(room, 'is_lair') and room.is_lair:
                marker = 'L'
            elif 'up' in exits or 'down' in exits:
                marker = '^'

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
        result.append("Legend: * = room, L = lair, ^ = stairs, | - / \\ = connections")
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

    async def _handle_admin_complete_quest(self, player_id: int, character: dict, params: str):
        """Admin command to manually complete a quest and all its objectives.

        Usage: completequest <quest_id>
        """
        quest_id = params.strip()

        if not quest_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: completequest <quest_id>"
            )
            return

        # Check if quest exists
        quest = self.game_engine.quest_manager.get_quest(quest_id)
        if not quest:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Quest '{quest_id}' not found."
            )
            return

        # Check if player has the quest
        if not self.game_engine.quest_manager.has_quest(character, quest_id):
            # Auto-accept the quest first
            self.game_engine.quest_manager.accept_quest(character, quest_id)
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Auto-accepted quest '{quest['name']}'."
            )

        # Get quest progress
        quest_progress = character['quests'][quest_id]

        # Mark all objectives as complete
        for i, objective in enumerate(quest.get('objectives', [])):
            if i in quest_progress['objectives']:
                obj = quest_progress['objectives'][i]
                obj['progress'] = obj['required']

        # Mark quest as complete
        quest_progress['completed'] = True

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Quest '{quest['name']}' marked as completed. Talk to the quest giver to claim your reward."
        )

    async def _handle_quest_log(self, player_id: int, character: dict):
        """Show the player's quest log."""
        quests = character.get('quests', {})

        if not quests:
            await self.game_engine.connection_manager.send_message(player_id, "You have no active quests.")
            return

        quest_list = ["=== Quest Log ===\n"]

        for quest_id, quest_progress in quests.items():
            quest = self.game_engine.quest_manager.get_quest(quest_id)
            if not quest:
                continue

            status = "COMPLETED" if quest_progress.get('completed') else "IN PROGRESS"
            quest_list.append(f"[{status}] {quest['name']}")

            if not quest_progress.get('completed'):
                # Show objectives
                for i, objective in enumerate(quest.get('objectives', [])):
                    obj_progress = quest_progress['objectives'].get(i, {})
                    progress = obj_progress.get('progress', 0)
                    required = obj_progress.get('required', 1)
                    quest_list.append(f"  - {progress}/{required} {objective['type']} {objective.get('target', '')}")

            quest_list.append("")

        await self.game_engine.connection_manager.send_message(player_id, "\n".join(quest_list))

    async def _handle_talk_to_npc(self, player_id: int, character: dict, npc_name: str):
        """Talk to an NPC to interact with quests."""
        room_id = character.get('room_id')
        if not room_id:
            return

        # Get the player's current room
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            await self.game_engine.connection_manager.send_message(player_id, "You are nowhere.")
            return

        # Check if there are any NPCs in the room
        if not room.npcs:
            await self.game_engine.connection_manager.send_message(player_id, "There is no one here to talk to.")
            return

        # Find NPC in the current room by partial name match
        npc_obj = None
        npc_name_lower = npc_name.lower()
        for npc in room.npcs:
            if npc_name_lower in npc.name.lower() or npc_name_lower in npc.npc_id.lower():
                npc_obj = npc
                break

        if not npc_obj:
            await self.game_engine.connection_manager.send_message(player_id, f"There is no '{npc_name}' here.")
            return

        # Get NPC data from world manager
        npc_data = self.game_engine.world_manager.get_npc_data(npc_obj.npc_id)

        if not npc_data:
            await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} has nothing to say.")
            return

        # Check if NPC has quests
        npc_quests = npc_data.get('quests', [])
        if not npc_quests:
            greeting = npc_data.get('dialogue', {}).get('greeting', f"{npc_data['name']} has nothing to say.")
            await self.game_engine.connection_manager.send_message(player_id, greeting)
            return

        # Handle quest interaction
        for quest_id in npc_quests:
            quest = self.game_engine.quest_manager.get_quest(quest_id)
            if not quest:
                continue

            # Check if player has completed the quest
            if self.game_engine.quest_manager.is_quest_complete(character, quest_id):
                # Check if player has already been rewarded
                if character.get('quests', {}).get(quest_id, {}).get('rewarded'):
                    completed_already = npc_data.get('dialogue', {}).get('quest_completed_already', "I have nothing more for you.")
                    await self.game_engine.connection_manager.send_message(player_id, completed_already)
                else:
                    # Give reward
                    quest_complete_msg = npc_data.get('dialogue', {}).get('quest_complete', "You have completed the quest!")
                    await self.game_engine.connection_manager.send_message(player_id, quest_complete_msg)

                    self.game_engine.quest_manager.give_quest_reward(character, quest_id)

                    # Show rewards
                    rewards = quest.get('rewards', {})
                    reward_msgs = []
                    if 'experience' in rewards:
                        reward_msgs.append(f"You gain {rewards['experience']} experience!")
                    if 'gold' in rewards:
                        reward_msgs.append(f"You receive {rewards['gold']} gold!")
                    if 'rune' in rewards:
                        reward_msgs.append(f"You have been granted the {rewards['rune'].title()} Rune!")

                    if reward_msgs:
                        await self.game_engine.connection_manager.send_message(player_id, "\n".join(reward_msgs))
                return

            # Check if player has the quest
            if self.game_engine.quest_manager.has_quest(character, quest_id):
                in_progress = npc_data.get('dialogue', {}).get('quest_in_progress', "You are working on my quest.")
                await self.game_engine.connection_manager.send_message(player_id, in_progress)
                return

            # Offer the quest
            can_accept, reason = self.game_engine.quest_manager.can_accept_quest(character, quest_id)
            if not can_accept:
                await self.game_engine.connection_manager.send_message(player_id, reason)
                return

            quest_available = npc_data.get('dialogue', {}).get('quest_available', "I have a quest for you.")
            await self.game_engine.connection_manager.send_message(player_id, quest_available)
            await self.game_engine.connection_manager.send_message(player_id, f"\nType 'accept {quest_id}' to accept this quest.")
            return

        # No quest interaction needed
        greeting = npc_data.get('dialogue', {}).get('greeting', f"{npc_data['name']} greets you.")
        await self.game_engine.connection_manager.send_message(player_id, greeting)

    async def _handle_accept_quest(self, player_id: int, character: dict, quest_id: str):
        """Accept a quest."""
        quest_id = quest_id.strip()
        quest = self.game_engine.quest_manager.get_quest(quest_id)

        if not quest:
            await self.game_engine.connection_manager.send_message(player_id, f"Unknown quest: {quest_id}")
            return

        can_accept, reason = self.game_engine.quest_manager.can_accept_quest(character, quest_id)
        if not can_accept:
            await self.game_engine.connection_manager.send_message(player_id, reason)
            return

        if self.game_engine.quest_manager.accept_quest(character, quest_id):
            await self.game_engine.connection_manager.send_message(player_id, f"Quest accepted: {quest['name']}")
            await self.game_engine.connection_manager.send_message(player_id, f"{quest['description']}")
        else:
            await self.game_engine.connection_manager.send_message(player_id, "Failed to accept quest.")
