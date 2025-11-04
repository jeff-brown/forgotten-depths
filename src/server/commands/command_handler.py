"""Command handler for processing player commands."""

import asyncio
import random
import json
import time
from typing import Optional, Dict, Any, Tuple
from ..utils.colors import (
    service_message, item_found, error_message,
    info_message, success_message, announcement,
    Colors, wrap_color
)


class CommandHandler:
    """Handles parsing and execution of player commands."""

    def __init__(self, game_engine):
        """Initialize the command handler with reference to the game engine.

        Args:
            game_engine: The AsyncGameEngine instance this handler belongs to
        """
        self.game_engine = game_engine
        self.logger = game_engine.logger

    def _get_stamina_hp_bonus(self, stamina: int) -> int:
        """Get HP bonus based on stamina (constitution) value.

        Args:
            stamina: The character's stamina/constitution stat

        Returns:
            HP bonus value
        """
        # More generous scaling: constitution directly contributes to HP
        # This ensures even low-con characters get decent HP gains
        if stamina >= 50:
            return 25
        elif stamina >= 45:
            return 22
        elif stamina >= 40:
            return 20
        elif stamina >= 35:
            return 18
        elif stamina >= 30:
            return 15
        elif stamina >= 25:
            return 13
        elif stamina >= 20:
            return 11
        elif stamina >= 18:
            return 10
        elif stamina >= 16:
            return 9
        elif stamina >= 14:
            return 8
        elif stamina >= 12:
            return 7
        elif stamina >= 10:
            return 6
        elif stamina >= 8:
            return 5
        else:
            return 4

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
            player_data['username'] = input_text.strip().capitalize()
            player_data['login_state'] = 'password_prompt'
            await self.game_engine.connection_manager.send_message(player_id, "Password: ", add_newline=False)

        elif login_state == 'password_prompt':
            # Authenticate user
            username = player_data.get('username', '')
            password = input_text.strip()

            # Check if user is already logged in
            if self.game_engine.player_manager.is_user_already_logged_in(username):
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"User '{username}' is already logged in!")
                )
                await self.game_engine.connection_manager.send_message(player_id, "\nUsername: ", add_newline=False)
                player_data['login_state'] = 'username_prompt'
                return

            if self.game_engine.player_manager.authenticate_player(username, password):
                player_data['authenticated'] = True
                player_data['login_state'] = 'authenticated'

                # Track this user as logged in
                self.game_engine.player_manager.logged_in_usernames[username] = player_id
                self.game_engine.logger.info(f"User '{username}' logged in successfully")

                # Load character or prompt for character creation
                # (welcome message will be sent in _handle_character_selection)
                await self._handle_character_selection(player_id, username)
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("Invalid credentials. Try again.")
                )
                await self.game_engine.connection_manager.send_message(player_id, "\nUsername: ", add_newline=False)
                player_data['login_state'] = 'username_prompt'

    def _migrate_character_data(self, character: dict):
        """Migrate old character data to new format.

        Args:
            character: Character dict to migrate (modified in place)
        """
        # Migration: Sync current_hit_points from legacy health field if missing
        if 'current_hit_points' not in character and 'health' in character:
            character['current_hit_points'] = character['current_hit_points']
            del character['current_hit_points']  # Remove old field
            print(f"[MIGRATION] Set current_hit_points to {character['current_hit_points']}")

        # Sync mana field from current_mana if missing
        if 'mana' not in character and 'current_mana' in character:
            character['current_mana'] = character['current_mana']
            print(f"[MIGRATION] Set mana to {character['current_mana']}")

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
                print(f"[DEBUG] Player {player_id} - Character loaded for '{username}': level {existing_character.get('level')}, gold {existing_character.get('gold')}")
                self.game_engine.player_manager.set_player_character(player_id, existing_character)
                await self.game_engine.connection_manager.send_message(player_id, f"Welcome back! Character '{username}' loaded successfully!")
                await self.game_engine._send_room_description(player_id, detailed=True)

                # Send vendor greeting if in a vendor room
                room_id = existing_character.get('room_id')
                if room_id and hasattr(self.game_engine, 'vendor_system'):
                    await self.game_engine.vendor_system.send_vendor_greeting(player_id, room_id)
                return
            else:
                print(f"[DEBUG] No existing character found for '{username}', creating new one")

        # No existing character found, start character creation flow
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        player_data['creating_character'] = True
        player_data['char_creation_step'] = 'race'

        # Welcome new players with intro text
        username = player_data.get('username', 'Adventurer')
        await self.game_engine.connection_manager.send_message(player_id, f"\nWelcome, {username}!\n")

        # Send intro text for new players
        intro_text = """
The world ended in fire and shadow.

One thousand years ago, something ancient stirred in the depths beneath the world.
The Ending, they call it now - though few remember the true name of what crawled
up from below. Cities fell in days. Kingdoms burned. Magic itself twisted and broke.

The old world is gone. Only ruins remain.

But humanity endures. In fortified settlements and guarded towns, life continues
under the watchful eye of the Tower. The Sorceress keeps the darkness at bay,
they say. Her soldiers patrol the roads. Her law keeps order.

You are a survivor in this broken world. Whether you seek glory, revenge, knowledge,
or simply another day of life, your path begins here - in Haven's Edge, a frontier
town on the border between civilization and the wild wastes beyond.

The depths still hunger. The Tower still watches.

What will you become?
"""
        await self.game_engine.connection_manager.send_message(player_id, intro_text)

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
            with open('data/player/races.json', 'r') as f:
                return json.load(f)
        except:
            # Fallback to default
            return {"human": {"name": "Human", "description": "Versatile humans", "base_stats": {"strength": 10, "dexterity": 10, "constitution": 10, "intellect": 10, "wisdom": 10, "charisma": 10}}}

    def _load_classes(self):
        """Load class definitions from JSON."""
        import json
        import os
        try:
            with open('data/player/classes.json', 'r') as f:
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
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message("Invalid choice. Try again.")
                    )
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
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message("Invalid choice. Try again.")
                    )
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

        # Clear creation flags IMMEDIATELY to prevent race conditions
        player_data['creating_character'] = False
        player_data['char_creation_step'] = None

        races = self._load_races()
        classes = self._load_classes()
        race_data = races.get(selected_race, races['human'])
        class_data = classes.get(selected_class, classes['fighter'])

        # Get starting room from world manager
        starting_room = self.game_engine.world_manager.get_default_starting_room()

        # Roll random stats using configured ranges from game_settings
        import random
        stat_ranges = self.game_engine.config_manager.get_setting('player', 'starting_stats', default={})

        def roll_stat(stat_name):
            """Roll a stat within the configured min/max range."""
            stat_config = stat_ranges.get(stat_name, {})
            if isinstance(stat_config, dict) and 'min' in stat_config and 'max' in stat_config:
                return random.randint(stat_config['min'], stat_config['max'])
            # Fallback to 3d6 if no config
            return sum(random.randint(1, 6) for _ in range(3))

        base_stats = {
            'strength': roll_stat('strength'),
            'dexterity': roll_stat('dexterity'),
            'constitution': roll_stat('constitution'),
            'vitality': roll_stat('vitality'),
            'intellect': roll_stat('intelligence'),
            'wisdom': roll_stat('wisdom'),
            'charisma': roll_stat('charisma')
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

        # Calculate max hit points using vitality formula
        # Formula: baseVitality + raceModifier + classModifier + staminaBonus
        # Base vitality roll (8-20)
        base_vitality = random.randint(8, 20)

        # Race vitality modifier
        race_vitality_mod = race_data.get('stat_modifiers', {}).get('vitality', 0)

        # Class vitality modifier
        class_vitality_mod = class_data.get('stat_modifiers', {}).get('vitality', 0)

        # Stamina (constitution) HP bonus lookup table
        constitution = character['constitution']
        stamina_hp_bonus = self._get_stamina_hp_bonus(constitution)

        # Final calculation (minimum 8 HP)
        max_hp = max(8, base_vitality + race_vitality_mod + class_vitality_mod + stamina_hp_bonus)

        # Calculate max mana with class modifier
        intellect = character['intellect']
        mana_modifier = class_data.get('mana_modifier', 1.0)
        base_mana = intellect * 3
        random_mana = random.randint(1, 5)
        max_mana = int((base_mana + random_mana) * mana_modifier)

        character.update({
            # Health and Mana
            'max_hit_points': max_hp,
            'current_hit_points': max_hp,
            'max_mana': max_mana,
            'current_mana': max_mana,
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

        # Set character
        self.game_engine.player_manager.set_player_character(player_id, character)

        # Show character stats
        stats_msg = f"\n=== Character Created ===\n"
        stats_msg += f"Race: {character['species']}\n"
        stats_msg += f"Class: {character['class']}\n\n"
        stats_msg += f"STR: {character['strength']}  DEX: {character['dexterity']}  CON: {character['constitution']}  VIT: {character.get('vitality', 0)}\n"
        stats_msg += f"INT: {character['intellect']}  WIS: {character['wisdom']}  CHA: {character['charisma']}\n\n"
        stats_msg += f"HP: {max_hp}  Mana: {max_mana}\n"

        await self.game_engine.connection_manager.send_message(player_id, stats_msg)
        await self.game_engine.connection_manager.send_message(player_id, f"\nYour journey begins now!\n")
        await self.game_engine._send_room_description(player_id, detailed=True)

        # Send vendor greeting if spawned in a vendor room
        room_id = character.get('room_id')
        if room_id and hasattr(self.game_engine, 'vendor_system'):
            await self.game_engine.vendor_system.send_vendor_greeting(player_id, room_id)

        # Save the new character to database
        if self.game_engine.player_storage:
            self.game_engine.player_storage.save_character_data(username, character)

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
                # Check if params is a direction first
                await self._handle_look_command(player_id, params)
            else:
                # Look around the room
                await self.game_engine._send_room_description(player_id, detailed=True)

        elif command == 'gaze' and params:
            # Handle special room actions like "gaze mirror"
            await self._handle_special_action(player_id, command, params)

        elif command in ['map', 'worldmap']:
            # Show map of areas and rooms
            await self._handle_map_command(player_id, character, params)

        elif command in ['help', '?']:
            help_text = """
Available Commands:
==================
look (l)           - Look around or examine target
gaze <target>      - Gaze at a target for detailed examination
help (?)           - Show this help
exits (ex)         - Show exits
map [area]         - Show world map or detailed area map

Character Info:
==============
stats (st)         - Show character stats
health (he)        - Show hit points, mana, and status
experience (xp)    - Show level, experience, and rune
inventory (inv,i)  - Show inventory
spellbook (sb)     - Show learned spells
unlearn <spell>    - Remove a spell from your spellbook (forget)
reroll             - Reroll stats (level 1, 0 XP only)
train              - Level up at a trainer

Items & Equipment:
=================
get <item>         - Pick up an item
drop <item>        - Drop an item
eat <item>         - Eat food
drink <item>       - Drink beverage (dr, quaff)
read <item>        - Read a scroll to learn a spell (study)
equip <item>       - Equip weapon or armor (eq)
unequip <item>     - Unequip weapon or armor
put <item>         - Put item in container (store, stow)
ring <item>        - Manage rings (ri)
light <item>       - Light a torch, lantern, or candle (ignite)
extinguish <item>  - Extinguish a light source (douse, snuff)
fill <item>        - Fill a lantern with lamp oil (refill)

Traps & Locks:
=============
search             - Search for traps in current room (detect)
disarm             - Disarm a detected trap (disable)

Vendors & Services:
==================
list               - Show vendor wares (wares)
buy <item>         - Buy from vendor (b)
sell <item>        - Sell to vendor
rent/rest          - Rent a room at inn (restores HP/MP, cost scales with level)
heal               - Receive healing from healer (if available)

Combat Commands:
===============
attack <target>    - Attack a target (att, a, kill)
cast <spell>       - Cast a spell (c)
shoot <target>     - Shoot with ranged weapon (fire, sh)
retrieve           - Retrieve spent ammunition (recover, gather)
flee               - Try to flee from combat (run)

Quests & NPCs:
=============
quest              - Show quest log (quests, questlog)
talk <npc>         - Talk to an NPC (speak)
accept <quest>     - Accept a quest from NPC
abandon <quest>    - Abandon a quest

Movement:
=========
north (n)          - Go north
south (s)          - Go south
east (e)           - Go east
west (w)           - Go west
northeast (ne)     - Go northeast
northwest (nw)     - Go northwest
southeast (se)     - Go southeast
southwest (sw)     - Go southwest
up (u)             - Go up
down (d)           - Go down
buy passage        - Buy passage across the great lake (requires rune, 100 gold)

Class Abilities:
===============
Rogue:
  picklock         - Pick a locked door
  backstab         - Next attack deals massive damage
  shadow_step      - Become harder to hit for a duration
  poison_blade     - Poison your weapon for multiple attacks

Fighter:
  power_attack     - Next attack deals more damage but less accurate
  cleave           - Attack multiple enemies at once
  dual_wield       - Fight with two weapons
  shield_bash      - Bash with shield to stun enemy
  battle_cry       - Boost damage for a duration

Ranger:
  track            - Track creatures in nearby rooms
  tame <creature>  - Tame a creature as a companion
  pathfind <dest>  - Find path to destination
  forage           - Search for food and supplies
  camouflage       - Hide from enemies
  multishot        - Fire arrows at multiple targets
  call_of_the_wild - Summon a wild companion

System:
======
quit (q)           - Quit the game

Admin Commands (Debug):
======================
givegold <amt>     - Give yourself gold
giveitem <id>      - Give yourself an item
givexp <amt>       - Give yourself experience
setstat <stat> <n> - Set a stat (str/dex/con/vit/int/wis/cha)
setlevel <level>   - Set your level (auto-adjusts HP/mana)
sethealth <hp>     - Set health (or 'sethealth full')
setmana <mana>     - Set mana (or 'setmana full')
godmode            - Toggle god mode (99 stats, level 50, 9999 HP/mana)
condition <type>   - Apply condition: poison, hungry, thirsty, starving, dehydrated, paralyzed
mobstatus          - Show all mobs and their flags
teleport <room>    - Teleport to a room (or 'teleport <player> <room>')
respawnnpc <id>    - Respawn an NPC
completequest <id> - Mark a quest as complete
"""
            await self.game_engine.connection_manager.send_message(player_id, help_text)

        elif command in ['exits', 'ex']:
            exits = self.game_engine.world_manager.get_exits_from_room(character['room_id'])
            if exits:
                await self.game_engine.connection_manager.send_message(player_id, f"Available exits: {', '.join(exits.keys())}")
            else:
                await self.game_engine.connection_manager.send_message(player_id, "No exits available.")

        elif command in ['stats', 'score', 'st']:
            await self._handle_stats_command(player_id, character)

        elif command in ['health', 'he']:
            await self._handle_health_command(player_id, character)

        elif command in ['experience', 'xp']:
            await self._handle_experience_command(player_id, character)

        elif command == 'reroll':
            await self._handle_reroll_command(player_id, character)

        elif command == 'train':
            await self._handle_train_command(player_id, character)

        elif command in ['inventory', 'inv', 'i']:
            await self._handle_inventory_command(player_id, character)

        elif command in ['spellbook', 'spells', 'sb']:
            await self._handle_spellbook_command(player_id, character)

        elif command in ['unlearn', 'forget'] and params:
            await self._handle_unlearn_spell_command(player_id, character, params)

        elif command in ['unlearn', 'forget']:
            await self.game_engine.connection_manager.send_message(player_id, "Unlearn what spell? Use 'spellbook' to see your spells.")

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

        elif command in ['light', 'ignite'] and params:
            # Light a light source (torch, lantern, etc.)
            await self._handle_light_command(player_id, params)

        elif command in ['light', 'ignite']:
            # Light command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to light?")

        elif command in ['extinguish', 'douse', 'snuff'] and params:
            # Extinguish a lit light source
            await self._handle_extinguish_command(player_id, params)

        elif command in ['extinguish', 'douse', 'snuff']:
            # Extinguish command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to extinguish?")

        elif command in ['fill', 'refill'] and params:
            # Fill/refill a lantern with oil
            await self._handle_fill_command(player_id, params)

        elif command in ['fill', 'refill']:
            # Fill command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to fill?")

        elif command in ['search', 'detect']:
            # Search for traps in current room
            await self._handle_search_traps_command(player_id, character)

        elif command in ['disarm', 'disable']:
            # Disarm a detected trap
            await self._handle_disarm_trap_command(player_id, character)

        elif command in ['buy', 'b'] and params and params.lower() in ['passage']:
            # Handle buying passage across the great lake
            await self._handle_buy_passage(player_id, character)

        elif command in ['buy', 'b', 'sell'] and params:
            # Handle buying/selling with vendors
            await self._handle_trade_command(player_id, command, params)

        elif command in ['list', 'wares']:
            # Show vendor inventory if in vendor room
            # Support "list" or "list <vendor_name>"
            await self._handle_list_vendor_items(player_id, params if params else None)

        elif command in ['rent', 'rest', 'sleep']:
            # Rent a room at the inn to restore HP/MP
            await self._handle_rent_room(player_id, character)

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

        elif command in ['put', 'store', 'stow'] and params:
            # Put item in container
            await self._handle_put_command(player_id, character, params)

        elif command in ['put', 'store', 'stow']:
            await self.game_engine.connection_manager.send_message(player_id, "Usage: put <item> in <container>")

        # Combat commands
        elif command in ['attack', 'att', 'a', 'kill']:
            if not params:
                await self.game_engine.connection_manager.send_message(player_id, "Attack what?")
            else:
                await self._handle_attack_command(player_id, params)

        elif command in ['shoot', 'fire', 'sh']:
            if not params:
                await self.game_engine.connection_manager.send_message(player_id, "Shoot what?")
            else:
                await self._handle_shoot_command(player_id, params)

        elif command in ['retrieve', 'recover', 'gather']:
            # Retrieve spent ammunition (arrows, bolts, etc.)
            await self._handle_retrieve_ammo(player_id)

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

        elif command in ['abandon', 'drop'] and params:
            await self._handle_abandon_quest(player_id, character, params)

        elif command in ['abandon', 'drop']:
            await self.game_engine.connection_manager.send_message(player_id, "What quest would you like to abandon? Usage: abandon <quest_id>")

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

        elif command == 'setstat' and params:
            await self._handle_admin_set_stat(player_id, character, params)

        elif command == 'setstat':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: setstat <stat_name> <value>\nStats: strength, dexterity, constitution, vitality, intellect, wisdom, charisma")

        elif command == 'setlevel' and params:
            await self._handle_admin_set_level(player_id, character, params)

        elif command == 'setlevel':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: setlevel <level>")

        elif command == 'setmana' and params:
            await self._handle_admin_set_mana(player_id, character, params)

        elif command == 'setmana':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: setmana <current> [max] OR setmana full")

        elif command == 'sethealth' and params:
            await self._handle_admin_set_health(player_id, character, params)

        elif command == 'sethealth':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: sethealth <current> [max] OR sethealth full")

        elif command in ['godmode', 'god']:
            await self._handle_admin_god_mode(player_id, character)

        elif command == 'condition' and params:
            await self._handle_admin_condition_command(player_id, character, params)

        elif command == 'condition':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: condition <type>\nTypes: poison, hungry, thirsty, starving, dehydrated, paralyzed")

        else:
            # Check if this is a class ability command
            ability = self.game_engine.ability_system.get_ability_by_command(character, command)
            if ability:
                # Execute the ability
                await self._handle_ability_command(player_id, character, ability, params)
            else:
                # Treat unknown commands as speech/chat messages
                username = player_data.get('username', 'Someone')
                room_id = character.get('room_id')

                # Broadcast message to others in the room
                await self.game_engine._notify_room_except_player(room_id, player_id, f"From {username}: {original_command}\n")

                # Confirm to sender
                await self.game_engine.connection_manager.send_message(player_id, "-- Message sent --")

    async def _handle_health_command(self, player_id: int, character: dict):
        """Display health, mana, and status."""
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

        # Check for active effects (debuffs/DOT effects)
        active_effects = char.get('active_effects', [])
        for effect in active_effects:
            effect_type = effect.get('type', effect.get('effect', ''))
            if effect_type == 'poison':
                status_conditions.append("Poisoned")
            elif effect_type == 'burning':
                status_conditions.append("Burning")
            elif effect_type == 'bleeding':
                status_conditions.append("Bleeding")
            elif effect_type == 'acid':
                status_conditions.append("Acid Burned")
            elif effect_type == 'paralyze':
                status_conditions.append("Paralyzed")
            elif effect_type == 'charm':
                status_conditions.append("Charmed")
            elif effect_type == 'stat_drain':
                status_conditions.append("Drained")

        # Use existing status or build from conditions
        if status_conditions:
            status = ", ".join(status_conditions)
        else:
            status = char.get('status', 'Healthy')

        # Check if class uses magic
        player_class = char.get('class', 'fighter')
        class_uses_magic = self._class_uses_magic(player_class)

        # Build mana line only if class uses magic
        if class_uses_magic:
            current_mana = int(char.get('current_mana', char.get('current_mana', 10)))
            max_mana = int(char.get('max_mana', 10))
            mana_value = wrap_color(f"{current_mana} / {max_mana}", Colors.BOLD_WHITE)
            mana_line = f"{wrap_color('Mana:', Colors.BOLD_CYAN)}          {mana_value}\n"
        else:
            mana_line = ""

        current_hp = int(char.get('current_hit_points', 20))
        max_hp = int(char.get('max_hit_points', 20))
        hp_value = wrap_color(f"{current_hp} / {max_hp}", Colors.BOLD_WHITE)

        health_text = f"""
{wrap_color('Hit Points:', Colors.BOLD_CYAN)}    {hp_value}
{mana_line}{wrap_color('Status:', Colors.BOLD_CYAN)}        {wrap_color(status, Colors.BOLD_WHITE)}
{Colors.BOLD_WHITE}"""
        await self.game_engine.connection_manager.send_message(
            player_id,
            health_text
        )

    async def _handle_experience_command(self, player_id: int, character: dict):
        """Display experience, level, and rune."""
        char = character

        # Calculate XP progress
        current_level = char.get('level', 1)
        current_xp = char.get('experience', 0)
        xp_for_next = self.calculate_xp_for_level(current_level + 1)
        xp_remaining = xp_for_next - current_xp

        experience_text = f"""
{wrap_color('Level:', Colors.BOLD_CYAN)}         {wrap_color(str(char['level']), Colors.BOLD_YELLOW)}
{wrap_color('Experience:', Colors.BOLD_CYAN)}    {wrap_color(f"{char['experience']}/{xp_for_next}", Colors.BOLD_WHITE)} ({xp_remaining} to next level)
{wrap_color('Rune:', Colors.BOLD_CYAN)}          {wrap_color(char['rune'].title(), Colors.BOLD_WHITE)}
{Colors.BOLD_WHITE}"""
        await self.game_engine.connection_manager.send_message(
            player_id,
            experience_text
        )

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

        # Check for active effects (debuffs/DOT effects)
        active_effects = char.get('active_effects', [])
        for effect in active_effects:
            effect_type = effect.get('type', effect.get('effect', ''))
            if effect_type == 'poison':
                status_conditions.append("Poisoned")
            elif effect_type == 'burning':
                status_conditions.append("Burning")
            elif effect_type == 'bleeding':
                status_conditions.append("Bleeding")
            elif effect_type == 'acid':
                status_conditions.append("Acid Burned")
            elif effect_type == 'paralyze':
                status_conditions.append("Paralyzed")
            elif effect_type == 'charm':
                status_conditions.append("Charmed")
            elif effect_type == 'stat_drain':
                status_conditions.append("Drained")

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

        # Check if class uses magic
        player_class = char.get('class', 'fighter')
        class_uses_magic = self._class_uses_magic(player_class)

        # Build mana line only if class uses magic
        if class_uses_magic:
            current_mana = int(char.get('current_mana', char.get('current_mana', 10)))
            max_mana = int(char.get('max_mana', 10))
            mana_value = wrap_color(f"{current_mana} / {max_mana}", Colors.BOLD_WHITE)
            mana_line = f"{wrap_color('Mana:', Colors.BOLD_CYAN)}          {mana_value}\n"
        else:
            mana_line = ""

        # Pre-calculate HP values
        current_hp = int(char.get('current_hit_points', 20))
        max_hp = int(char.get('max_hit_points', 20))
        hp_value = wrap_color(f"{current_hp} / {max_hp}", Colors.BOLD_WHITE)

        # Colorize stats display
        stats_text = f"""
{wrap_color('Name:', Colors.BOLD_CYAN)}          {wrap_color(char['name'], Colors.BOLD_WHITE)}
{wrap_color('Species:', Colors.BOLD_CYAN)}       {wrap_color(char['species'], Colors.BOLD_WHITE)}
{wrap_color('Class:', Colors.BOLD_CYAN)}         {wrap_color(char['class'], Colors.BOLD_WHITE)}
{wrap_color('Level:', Colors.BOLD_CYAN)}         {wrap_color(str(char['level']), Colors.BOLD_YELLOW)}
{wrap_color('Experience:', Colors.BOLD_CYAN)}    {wrap_color(f"{char['experience']}/{xp_for_next}", Colors.BOLD_WHITE)} ({xp_remaining} to next level)
{wrap_color('Rune:', Colors.BOLD_CYAN)}          {wrap_color(char['rune'].title(), Colors.BOLD_WHITE)}

{wrap_color('Intellect:', Colors.BOLD_CYAN)}     {wrap_color(str(char['intellect']), Colors.BOLD_WHITE)}
{wrap_color('Wisdom:', Colors.BOLD_CYAN)}        {wrap_color(str(char['wisdom']), Colors.BOLD_WHITE)}
{wrap_color('Strength:', Colors.BOLD_CYAN)}      {wrap_color(str(char['strength']), Colors.BOLD_WHITE)}
{wrap_color('Constitution:', Colors.BOLD_CYAN)}  {wrap_color(str(char['constitution']), Colors.BOLD_WHITE)}
{wrap_color('Dexterity:', Colors.BOLD_CYAN)}     {wrap_color(str(char['dexterity']), Colors.BOLD_WHITE)}
{wrap_color('Charisma:', Colors.BOLD_CYAN)}      {wrap_color(str(char['charisma']), Colors.BOLD_WHITE)}

{wrap_color('Hit Points:', Colors.BOLD_CYAN)}    {hp_value}
{mana_line}{wrap_color('Status:', Colors.BOLD_CYAN)}        {wrap_color(status, Colors.BOLD_WHITE)}
{wrap_color('Armor Class:', Colors.BOLD_CYAN)}   {wrap_color(str(self.get_effective_armor_class(char)), Colors.BOLD_WHITE)}

{wrap_color('Weapon:', Colors.BOLD_CYAN)}        {wrap_color(char['equipped']['weapon']['name'] if char['equipped']['weapon'] else 'Fists', Colors.BOLD_WHITE)}
{wrap_color('Armor:', Colors.BOLD_CYAN)}         {wrap_color(char['equipped']['armor']['name'] if char['equipped']['armor'] else 'None', Colors.BOLD_WHITE)}
{wrap_color('Encumbrance:', Colors.BOLD_CYAN)}   {wrap_color(f"{char['encumbrance']} / {char['max_encumbrance']}", Colors.BOLD_WHITE)}
{wrap_color('Gold:', Colors.BOLD_CYAN)}          {wrap_color(str(char['gold']), Colors.BOLD_YELLOW)}
{Colors.BOLD_WHITE}"""
        await self.game_engine.connection_manager.send_message(
            player_id,
            stats_text
        )

    async def _handle_inventory_command(self, player_id: int, character: dict):
        """Display player inventory."""
        char = character
        inventory_text = f"{wrap_color('You are carrying:', Colors.BOLD_CYAN)}\n"
        if char['inventory']:
            for i, item in enumerate(char['inventory'], 1):
                item_name = item['name']

                # Add quantity if item has more than 1
                quantity = item.get('quantity', 1)
                if quantity > 1:
                    item_name += f" {wrap_color(f'({quantity})', Colors.BOLD_GREEN)}"

                # Add lit/unlit status for light sources
                if item.get('is_light_source', False):
                    if item.get('is_lit', False):
                        time_remaining = item.get('time_remaining', 0)
                        minutes = int(time_remaining // 60)
                        seconds = int(time_remaining % 60)
                        item_name += f" {wrap_color('(lit', Colors.BOLD_YELLOW)}{wrap_color(f' - {minutes}m {seconds}s', Colors.BOLD_GREEN)}{wrap_color(')', Colors.BOLD_YELLOW)}"
                    else:
                        item_name += f" {wrap_color('(unlit)', Colors.BOLD_WHITE)}"

                # Add container contents summary
                if item.get('type') == 'container':
                    contents = item.get('contents', [])
                    if contents:
                        # Show total quantity of items in container
                        for content_item in contents:
                            content_quantity = content_item.get('quantity', 1)
                            content_name = content_item.get('name', 'items')
                            item_name += f" {wrap_color(f'({content_quantity} {content_name})', Colors.BOLD_GREEN)}"
                    else:
                        item_name += f" {wrap_color('(empty)', Colors.BOLD_WHITE)}"

                inventory_text += f"  {wrap_color(str(i) + '.', Colors.BOLD_WHITE)} {wrap_color(item_name, Colors.BOLD_WHITE)}\n"
        else:
            inventory_text += f"  {wrap_color('Nothing.', Colors.BOLD_WHITE)}\n"

        # Show equipped items
        inventory_text += f"\n{wrap_color('--- Equipped ---', Colors.BOLD_YELLOW)}\n"
        weapon = char['equipped']['weapon']
        armor = char['equipped']['armor']
        inventory_text += f"{wrap_color('Weapon:', Colors.BOLD_CYAN)} {wrap_color(weapon['name'] if weapon else 'None', Colors.BOLD_WHITE)}\n"
        inventory_text += f"{wrap_color('Armor:', Colors.BOLD_CYAN)}  {wrap_color(armor['name'] if armor else 'None', Colors.BOLD_WHITE)}\n"

        inventory_text += f"\n{wrap_color('Gold:', Colors.BOLD_CYAN)} {wrap_color(str(char['gold']), Colors.BOLD_YELLOW)}{Colors.BOLD_WHITE}"
        await self.game_engine.connection_manager.send_message(
            player_id,
            inventory_text
        )

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
            if item:
                # Check encumbrance before picking up
                current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
                item_weight = item.get('weight', 0)
                max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)

                if current_encumbrance + item_weight > max_encumbrance:
                    # Put the item back on the floor since we can't pick it up
                    self.game_engine.item_manager.add_item_to_room(room_id, item)
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message(f"You cannot pick up {item['name']} - you are carrying too much! ({current_encumbrance + item_weight:.1f}/{max_encumbrance})")
                    )
                    return

                # Found item on floor, pick it up
                character['inventory'].append(item)

                # Update encumbrance
                self.game_engine.player_manager.update_encumbrance(character)

                await self.game_engine.connection_manager.send_message(
                    player_id,
                    item_found(f"You pick up the {item['name']}.")
                )

                # Notify others in the room
                username = player_data.get('username', 'Someone')
                await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} picks up a {item['name']}.")
                return

        # Item not found on floor or in config
        await self.game_engine.connection_manager.send_message(
            player_id,
            error_message(f"You don't see a {item_name} here.")
        )

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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
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

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"Ok, you dropped your {dropped_item['name'].lower()}.")
        )

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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just eat the first one
            pass  # item_to_eat and item_index are already set to the first match

        # Check if item is food
        item_type = item_to_eat.get('type', '')
        if item_type != 'food':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't eat {item_to_eat['name']}!")
            )
            return

        # Get nutrition value (default 30 if not specified)
        nutrition = item_to_eat.get('nutrition', 30)

        # Restore hunger
        current_hunger = character.get('hunger', 100)
        new_hunger = min(100, current_hunger + nutrition)
        character['hunger'] = new_hunger

        # Decrement quantity or remove item from inventory
        current_quantity = item_to_eat.get('quantity', 1)
        if current_quantity > 1:
            # Decrement quantity
            item_to_eat['quantity'] = current_quantity - 1
        else:
            # Remove item entirely if it's the last one
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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just drink the first one
            pass  # item_to_drink and item_index are already set to the first match

        # Check if item is a drink or consumable
        item_type = item_to_drink.get('type', '')
        if item_type not in ['drink', 'potion', 'consumable']:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't drink {item_to_drink['name']}!")
            )
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

            current_health = character.get('current_hit_points', 0)
            max_health = character.get('max_hit_points', 100)
            new_health = min(max_health, current_health + health_amount)

            character['current_hit_points'] = new_health

            messages.append(f"You restore {health_amount} health! (HP: {new_health}/{max_health})")

        # Handle mana restoration
        if 'restore_mana' in properties:
            restore_mana = properties['restore_mana']
            mana_amount = int(restore_mana)

            current_mana = character.get('current_mana', character.get('current_mana', 0))
            max_mana = character.get('max_mana', 50)
            new_mana = min(max_mana, current_mana + mana_amount)

            character['current_mana'] = new_mana
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

        # Decrement quantity or remove item from inventory
        current_quantity = item_to_drink.get('quantity', 1)
        if current_quantity > 1:
            # Decrement quantity
            item_to_drink['quantity'] = current_quantity - 1
        else:
            # Remove item entirely if it's the last one
            character['inventory'].pop(item_index)

        # Send all messages
        await self.game_engine.connection_manager.send_message(
            player_id,
            "\n".join(messages)
        )

    async def _handle_light_command(self, player_id: int, item_name: str):
        """Handle lighting a light source (torch, lantern, candle)."""
        from ..utils.colors import success_message, error_message, announcement

        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find light source in inventory
        item_to_light, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
            )
            return

        # Check if item is a light source
        if not item_to_light.get('is_light_source', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't light {item_to_light['name']}.")
            )
            return

        # Check if already lit
        if item_to_light.get('is_lit', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_light['name']} is already lit!")
            )
            return

        # Check if it's depleted
        properties = item_to_light.get('properties', {})
        time_remaining = item_to_light.get('time_remaining', properties.get('max_duration', 0))

        if time_remaining <= 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_light['name']} has burned out and can't be lit.")
            )
            return

        # For lanterns, check if they need oil
        fuel_type = properties.get('fuel_type', 'none')
        if fuel_type == 'lamp_oil':
            fuel_charges = properties.get('fuel_charges', 0)
            if fuel_charges <= 0:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"The {item_to_light['name']} needs oil. Use 'fill lantern' with lamp oil in your inventory.")
                )
                return

        # Light the item
        item_to_light['is_lit'] = True
        if 'time_remaining' not in item_to_light:
            item_to_light['time_remaining'] = properties.get('max_duration', 600)

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You light the {item_to_light['name']}. It illuminates the area around you.")
        )

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(
                room_id, player_id,
                announcement(f"{username} lights a {item_to_light['name']}, casting light in the darkness.")
            )

    async def _handle_extinguish_command(self, player_id: int, item_name: str):
        """Handle extinguishing a lit light source."""
        from ..utils.colors import success_message, error_message

        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find light source in inventory
        item_to_extinguish, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
            )
            return

        # Check if item is a light source
        if not item_to_extinguish.get('is_light_source', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't extinguish {item_to_extinguish['name']}.")
            )
            return

        # Check if actually lit
        if not item_to_extinguish.get('is_lit', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_extinguish['name']} isn't lit.")
            )
            return

        # Extinguish the item
        item_to_extinguish['is_lit'] = False

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You extinguish the {item_to_extinguish['name']}. The light fades away.")
        )

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(
                room_id, player_id,
                f"{username} extinguishes their {item_to_extinguish['name']}, plunging the area into darkness."
            )

    async def _handle_fill_command(self, player_id: int, item_name: str):
        """Handle filling a lantern with lamp oil."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find lantern to fill
        item_to_fill, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, use the first one
            pass  # item_to_fill and item_index are already set to the first match

        # Check if item is a light source that can be refilled
        if not item_to_fill.get('is_light_source', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't fill {item_to_fill['name']}.")
            )
            return

        properties = item_to_fill.get('properties', {})
        fuel_type = properties.get('fuel_type', 'none')

        if fuel_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_fill['name']} doesn't need fuel.")
            )
            return

        if fuel_type != 'lamp_oil':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_fill['name']} requires {fuel_type}, which you don't have.")
            )
            return

        # Find lamp oil in inventory
        oil_item, oil_index, oil_match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, 'lamp_oil')

        if oil_match_type == 'none':
            # Try alternate names
            oil_item, oil_index, oil_match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, 'oil')

        if oil_match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have any lamp oil to fill it with.")
            )
            return

        # Check if the oil item is actually lamp oil
        if oil_item.get('id', '') != 'lamp_oil':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have any lamp oil to fill it with.")
            )
            return

        # Get fuel charges from the oil
        oil_properties = oil_item.get('properties', {})
        fuel_to_add = oil_properties.get('fuel_charges', 1800)

        # Add fuel to the lantern
        current_fuel = properties.get('fuel_charges', 0)
        max_duration = properties.get('max_duration', 1800)

        # Initialize properties dict if it doesn't exist
        if 'properties' not in item_to_fill:
            item_to_fill['properties'] = {}

        # Add fuel (cap at max_duration)
        new_fuel = min(current_fuel + fuel_to_add, max_duration)
        item_to_fill['properties']['fuel_charges'] = new_fuel

        # If the lantern was depleted, reset time_remaining
        if item_to_fill.get('time_remaining', 0) <= 0:
            item_to_fill['time_remaining'] = new_fuel
        else:
            # Add to existing time_remaining
            item_to_fill['time_remaining'] = min(item_to_fill.get('time_remaining', 0) + fuel_to_add, max_duration)

        # Reset warning flags
        item_to_fill['_warned_60'] = False
        item_to_fill['_warned_10'] = False

        # Decrement quantity or remove the oil flask from inventory
        current_quantity = oil_item.get('quantity', 1)
        if current_quantity > 1:
            # Decrement quantity
            oil_item['quantity'] = current_quantity - 1
        else:
            # Remove item entirely if it's the last one
            inventory.pop(oil_index)

        # Calculate time in minutes
        minutes = int(new_fuel // 60)

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You fill the {item_to_fill['name']} with lamp oil. It now has {minutes} minutes of fuel.")
        )

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(
                room_id, player_id,
                f"{username} fills their {item_to_fill['name']} with lamp oil."
            )

    async def _handle_search_traps_command(self, player_id: int, character: dict):
        """Handle searching for traps in current room."""
        # Check if player is a rogue
        player_class = character.get('class', '').lower()
        if player_class != 'rogue':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Only rogues have the skills to search for traps.")
            )
            return

        room_id = character.get('room_id')
        if not room_id:
            return

        result = self.game_engine.trap_system.search_for_traps(player_id, room_id)

        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message(result)
        )

        # Notify others in the room
        username = self.game_engine.player_manager.get_player_data(player_id).get('username', 'Someone')
        await self.game_engine.player_manager.notify_room_except_player(
            room_id, player_id,
            f"{username} carefully searches the area for traps."
        )

    async def _handle_disarm_trap_command(self, player_id: int, character: dict):
        """Handle disarming a detected trap."""
        # Check if player is a rogue
        player_class = character.get('class', '').lower()
        if player_class != 'rogue':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Only rogues have the skills to disarm traps.")
            )
            return

        room_id = character.get('room_id')
        if not room_id:
            return

        # Disarm the first detected trap
        result = self.game_engine.trap_system.disarm_trap(player_id, room_id, 0)

        # Determine message type based on result
        if "successfully" in result:
            msg = success_message(result)
        elif "fumble" in result or "trigger" in result:
            msg = error_message(result)
        else:
            msg = info_message(result)

        await self.game_engine.connection_manager.send_message(player_id, msg)

        # Notify others in the room on success
        if "successfully" in result:
            username = self.game_engine.player_manager.get_player_data(player_id).get('username', 'Someone')
            await self.game_engine.player_manager.notify_room_except_player(
                room_id, player_id,
                f"{username} carefully disarms a trap."
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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just read the first one
            pass  # item_to_read and item_index are already set to the first match

        # Check if item is a spell scroll
        item_type = item_to_read.get('type', '')
        if item_type != 'spell_scroll':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't read {item_to_read['name']} to learn a spell!")
            )
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
        player_intelligence = character.get('intellect', 10)

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

        # Get spell data to check class restrictions
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})
        spell = spell_data.get(spell_id, {})

        if not spell:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Error: Spell data not found for {spell_id}!"
            )
            return

        # Check class restriction
        player_class = character.get('class', '').lower()
        spell_class_restriction = spell.get('class_restriction', '').lower()

        if spell_class_restriction and spell_class_restriction != player_class:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Only {spell_class_restriction}s can learn {spell.get('name', spell_id)}!"
            )
            return

        # Check spell level restrictions based on class
        spell_level = spell.get('level', 1)

        # Get max spell level from class data
        classes_data = self.game_engine.config_manager.game_data.get('classes', {})
        class_info = classes_data.get(player_class, {})
        max_spell_level = class_info.get('max_spell_level', 99)  # Default to 99 (no restriction)

        if max_spell_level > 0 and spell_level > max_spell_level:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"As a {character.get('class', 'adventurer')}, you can only learn spells up to level {max_spell_level}. {spell.get('name', spell_id)} is level {spell_level}."
            )
            return

        # Learn the spell!
        if 'spellbook' not in character:
            character['spellbook'] = []

        character['spellbook'].append(spell_id)

        # Remove scroll from inventory
        character['inventory'].pop(item_index)

        # Send success message (spell data already loaded above)
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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name} to equip.")
            )
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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You cannot equip the {item_to_equip['name']}.")
            )
            return

        # Check level requirement
        item_properties = item_to_equip.get('properties', {})
        required_level = item_properties.get('required_level', 0)
        character_level = character.get('level', 1)

        if character_level < required_level:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You must be level {required_level} to equip the {item_to_equip['name']}. (You are level {character_level})")
            )
            return

        # Check class requirement
        allowed_classes = item_properties.get('allowed_classes', None)
        if allowed_classes:
            character_class = character.get('class', 'fighter').lower()
            if character_class not in allowed_classes:
                class_list = ", ".join([c.capitalize() for c in allowed_classes])
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"Only {class_list} can equip the {item_to_equip['name']}."
                )
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
            armor_class = equipped_item.get('properties', {}).get('armor_class', 0)
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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name} equipped.")
            )
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in equipped_items if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"'{item_name}' matches multiple equipped items: {match_list}. Please be more specific.")
            )
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

    async def _handle_put_command(self, player_id: int, character: dict, params: str):
        """Handle putting an item into a container.

        Usage: put <item> in <container>
                put all <item> in <container>
                put <quantity> <item> in <container>
        """
        # Parse the command
        if ' in ' not in params.lower():
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Usage: put <item> in <container>, put all <item> in <container>, or put <quantity> <item> in <container>")
            )
            return

        parts = params.split(' in ', 1)
        item_part = parts[0].strip()
        container_name = parts[1].strip()

        if not item_part or not container_name:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Usage: put <item> in <container>, put all <item> in <container>, or put <quantity> <item> in <container>")
            )
            return

        # Check for quantity or "all" prefix
        put_all = False
        specific_quantity = None
        item_name = item_part

        # Check for "all" prefix
        if item_part.lower().startswith('all '):
            put_all = True
            item_name = item_part[4:].strip()
        else:
            # Check for numeric quantity prefix (e.g., "3 arrow")
            parts_item = item_part.split(None, 1)
            if len(parts_item) >= 2 and parts_item[0].isdigit():
                specific_quantity = int(parts_item[0])
                item_name = parts_item[1]

        inventory = character.get('inventory', [])

        # Find the container first
        container, container_index, container_match_type = self.game_engine.item_manager.find_item_by_partial_name(
            inventory, container_name
        )

        if container_match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {container_name}.")
            )
            return
        elif container_match_type == 'multiple':
            matches = [item['name'] for item in inventory if container_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"'{container_name}' matches multiple items: {match_list}. Please be more specific.")
            )
            return

        # Verify it's actually a container
        if container.get('type') != 'container':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {container['name']} is not a container.")
            )
            return

        # Check container capacity
        container_props = container.get('properties', {})
        max_capacity = container_props.get('max_capacity', 20)
        contents = container.get('contents', [])
        current_capacity = sum(item.get('quantity', 1) for item in contents)

        if put_all or specific_quantity:
            # Find all matching items in inventory (by item ID for stackable items)
            items_to_put = []
            target_item_id = None

            for i, item in enumerate(inventory):
                if i == container_index:
                    continue  # Skip the container itself

                # Get item name and id safely
                item_name_str = item.get('name', '')
                item_id_str = item.get('id', '')

                # Check if item matches by name or id
                if item_name.lower() in item_name_str.lower() or item_id_str.lower() == item_name.lower():
                    if target_item_id is None:
                        target_item_id = item_id_str
                    # Only match items with the same ID (so all arrows stack together)
                    if item_id_str == target_item_id:
                        items_to_put.append((item, i))

            if not items_to_put:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You don't have any {item_name}.")
                )
                return

            # Calculate total quantity available
            total_available = sum(item.get('quantity', 1) for item, _ in items_to_put)

            # Determine how much to transfer
            if specific_quantity:
                # User specified exact amount
                if specific_quantity > total_available:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message(f"You only have {total_available} {items_to_put[0][0]['name']}, not {specific_quantity}.")
                    )
                    return
                quantity_to_put = specific_quantity
            else:
                # User said "all"
                quantity_to_put = total_available

            # Check capacity and adjust if needed
            space_available = max_capacity - current_capacity
            if quantity_to_put > space_available:
                if put_all:
                    # Auto-adjust for "all" command
                    quantity_to_put = space_available
                    if quantity_to_put <= 0:
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            error_message(f"The {container['name']} is full. (Capacity: {current_capacity}/{max_capacity})")
                        )
                        return
                else:
                    # User specified exact amount that won't fit
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message(f"The {container['name']} only has room for {space_available} more items. (Capacity: {current_capacity}/{max_capacity})")
                    )
                    return

            # Add to container (stack with existing if present)
            item_id = items_to_put[0][0].get('id')
            existing_item = None
            for content_item in contents:
                if content_item.get('id') == item_id:
                    existing_item = content_item
                    break

            if existing_item:
                # Stack with existing item
                existing_item['quantity'] = existing_item.get('quantity', 1) + quantity_to_put
            else:
                # Add new item to contents
                if 'contents' not in container:
                    container['contents'] = []
                new_item = items_to_put[0][0].copy()
                new_item['quantity'] = quantity_to_put
                container['contents'].append(new_item)

            # Remove from inventory
            remaining_to_remove = quantity_to_put
            for item, idx in reversed(items_to_put):
                if remaining_to_remove <= 0:
                    break

                item_qty = item.get('quantity', 1)

                if item_qty <= remaining_to_remove:
                    # Remove entire stack
                    if idx < container_index:
                        character['inventory'].pop(idx)
                        container_index -= 1
                    else:
                        character['inventory'].pop(idx)
                    remaining_to_remove -= item_qty
                else:
                    # Partial removal from stack
                    item['quantity'] = item_qty - remaining_to_remove
                    remaining_to_remove = 0

            item_display_name = items_to_put[0][0]['name']
            if put_all and quantity_to_put < total_available:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    success_message(f"You put {quantity_to_put} {item_display_name} in your {container['name']} ({total_available - quantity_to_put} remaining, container full).")
                )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    success_message(f"You put {quantity_to_put} {item_display_name} in your {container['name']}.")
                )

        else:
            # Single item logic
            # Find the item to put
            item_to_put, item_index, item_match_type = self.game_engine.item_manager.find_item_by_partial_name(
                inventory, item_name
            )

            if item_match_type == 'none':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You don't have a {item_name}.")
                )
                return
            elif item_match_type == 'multiple':
                matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
                match_list = ", ".join(matches)
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
                )
                return

            # Can't put a container in itself
            if item_index == container_index:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You can't put something inside itself.")
                )
                return

            item_quantity = item_to_put.get('quantity', 1)

            if current_capacity + item_quantity > max_capacity:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"The {container['name']} is full. (Capacity: {current_capacity}/{max_capacity})")
                )
                return

            # Check if container already has this item type (for stacking)
            item_id = item_to_put.get('id')
            existing_item = None
            for content_item in contents:
                if content_item.get('id') == item_id:
                    existing_item = content_item
                    break

            if existing_item:
                # Stack with existing item
                existing_item['quantity'] = existing_item.get('quantity', 1) + item_quantity
            else:
                # Add new item to contents
                if 'contents' not in container:
                    container['contents'] = []
                container['contents'].append(item_to_put.copy())

            # Remove from inventory
            if container_index < item_index:
                character['inventory'].pop(item_index)
            else:
                character['inventory'].pop(item_index)

            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You put {item_quantity} {item_to_put['name']} in your {container['name']}.")
            )

        # Notify others in the room
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(
                room_id, player_id,
                f"{username} puts something in their {container['name']}."
            )

    async def _handle_trade_command(self, player_id: int, action: str, params: str):
        """Handle buy/sell commands with vendors.

        Supports:
        - buy <item> - buy from first vendor
        - buy <quantity> <item> - buy multiple items
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
        quantity = 1

        # Check for "from <vendor>" or "to <vendor>"
        if ' from ' in params.lower():
            parts = params.lower().split(' from ', 1)
            item_name = parts[0].strip()
            vendor_name = parts[1].strip()
        elif ' to ' in params.lower():
            parts = params.lower().split(' to ', 1)
            item_name = parts[0].strip()
            vendor_name = parts[1].strip()

        # Check for quantity at the beginning (e.g., "20 arrows" or "5 potions")
        if action == 'buy':
            parts = item_name.split(None, 1)
            if len(parts) == 2 and parts[0].isdigit():
                quantity = int(parts[0])
                item_name = parts[1]

        # Find the vendor
        if vendor_name:
            vendor = self.game_engine.vendor_system.find_vendor_by_name(room_id, vendor_name)
            if not vendor:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"There is no vendor named '{vendor_name}' here.")
                )
                return
        else:
            vendor = self.game_engine.vendor_system.get_vendor_in_room(room_id)
            if not vendor:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("There is no vendor here to trade with.")
                )
                return

        if action == 'buy':
            await self._handle_buy_item(player_id, vendor, item_name, quantity)
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
            # Check if player is in an arena room (configured in game settings)
            arena_config = self.game_engine.config_manager.get_arena_by_room(room_id)
            if not arena_config:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("There is no gong here to ring.")
                )
                return

            # Ring the gong and spawn a mob (delegates to world_manager)
            await self.game_engine.world_manager.handle_ring_gong(player_id, room_id)
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You cannot ring {target}.")
            )

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
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"There is no vendor named '{vendor_name}' here.")
                )
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
                        info_message(f"There are multiple vendors here: {', '.join(vendor_names)}. Use 'list <vendor name>' to see a specific vendor's wares.")
                    )
                    return
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("There is no vendor here.")
                )
                return

        inventory_text = f"{vendor['name']} has the following items for sale:\n"
        for i, item_entry in enumerate(vendor['inventory'], 1):
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config:
                item_name = item_config['name']
                # Calculate price from base_value and vendor's sell_markup
                base_value = item_config.get('base_value', 0)
                sell_markup = vendor.get('sell_markup', 1.2)
                price = int(base_value * sell_markup)
                inventory_text += f"  {i}. {item_name} - {price} gold\n"
            else:
                # Try to get price from item_entry, fallback to 0
                price = item_entry.get('price', 0)
                inventory_text += f"  {i}. {item_id} (unknown item) - {price} gold\n"

        await self.game_engine.connection_manager.send_message(player_id, inventory_text)

    async def _handle_buy_item(self, player_id: int, vendor: dict, item_name: str, quantity: int = 1):
        """Handle buying an item from a vendor.

        Args:
            player_id: The player making the purchase
            vendor: The vendor dict
            item_name: Name of the item to buy
            quantity: Number of items to buy (default 1)
        """
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        character = player_data['character']

        # Validate quantity
        if quantity < 1:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You must buy at least 1 item.")
            )
            return

        # Find the item in vendor inventory using multi-pass approach:
        # Pass 1: Try exact match on full name
        # Pass 2: Try matching on individual words (for "Scroll of X" items)
        # Pass 3: Try word boundary partial match (word starts with search term)
        # Pass 4: Fall back to substring match as last resort
        item_found_id = None
        item_price = None
        item_stock = None

        # First pass: Look for exact match
        for item_entry in vendor['inventory']:
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config and item_name.lower() == item_config['name'].lower():
                item_found_id = item_id
                # Calculate price from base_value and vendor's sell_markup
                base_value = item_config.get('base_value', 0)
                sell_markup = vendor.get('sell_markup', 1.2)
                item_price = int(base_value * sell_markup)
                item_stock = item_entry.get('stock', -1)
                break

        # Second pass: Try matching individual words (exact word match)
        if not item_found_id:
            for item_entry in vendor['inventory']:
                item_id = item_entry['item_id']
                item_config = self.game_engine.config_manager.get_item(item_id)
                if item_config:
                    item_words = item_config['name'].lower().split()
                    if item_name.lower() in item_words:
                        item_found_id = item_id
                        base_value = item_config.get('base_value', 0)
                        sell_markup = vendor.get('sell_markup', 1.2)
                        item_price = int(base_value * sell_markup)
                        item_stock = item_entry.get('stock', -1)
                        break

        # Third pass: Try word boundary match (word starts with search term)
        if not item_found_id:
            for item_entry in vendor['inventory']:
                item_id = item_entry['item_id']
                item_config = self.game_engine.config_manager.get_item(item_id)
                if item_config:
                    item_words = item_config['name'].lower().split()
                    if any(word.startswith(item_name.lower()) for word in item_words):
                        item_found_id = item_id
                        base_value = item_config.get('base_value', 0)
                        sell_markup = vendor.get('sell_markup', 1.2)
                        item_price = int(base_value * sell_markup)
                        item_stock = item_entry.get('stock', -1)
                        break

        # Fourth pass: Substring match as last resort
        if not item_found_id:
            for item_entry in vendor['inventory']:
                item_id = item_entry['item_id']
                item_config = self.game_engine.config_manager.get_item(item_id)
                if item_config and item_name.lower() in item_config['name'].lower():
                    item_found_id = item_id
                    # Calculate price from base_value and vendor's sell_markup
                    base_value = item_config.get('base_value', 0)
                    sell_markup = vendor.get('sell_markup', 1.2)
                    item_price = int(base_value * sell_markup)
                    item_stock = item_entry.get('stock', -1)
                    break

        if not item_found_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"{vendor['name']} doesn't have {item_name} for sale.")
            )
            return

        # Create proper item instance to get the real name
        item_instance = self.game_engine.config_manager.create_item_instance(item_found_id, item_price)
        if not item_instance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Error creating item.")
            )
            return

        # Check if vendor has enough stock (stock of -1 means unlimited)
        if item_stock != -1 and item_stock < quantity:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"{vendor['name']} only has {item_stock} {item_instance['name']} in stock.")
            )
            return

        # Calculate total cost
        total_price = item_price * quantity

        # Check if player has enough gold
        if character['gold'] < total_price:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have enough gold. {quantity} {item_instance['name']} costs {total_price} gold. (You have {character['gold']} gold)")
            )
            return

        # Check encumbrance before buying
        current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
        item_weight = item_instance.get('weight', 0) * quantity
        gold_weight_change = -total_price / 100.0  # Losing gold reduces weight
        max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)

        if current_encumbrance + item_weight + gold_weight_change > max_encumbrance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You cannot carry {quantity} {item_instance['name']} - you are carrying too much!")
            )
            return

        # Complete the purchase
        character['gold'] -= total_price

        # Add items to inventory (stack if possible)
        if quantity == 1:
            character['inventory'].append(item_instance)
        else:
            # Create a single item with quantity field
            item_instance['quantity'] = quantity
            character['inventory'].append(item_instance)

        # Reduce vendor stock (if not unlimited)
        self.game_engine.vendor_system.reduce_vendor_stock(vendor, item_found_id, quantity)

        # Update encumbrance (accounts for gold weight change and new items)
        self.game_engine.player_manager.update_encumbrance(character)

        if quantity == 1:
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You buy {item_instance['name']} for {item_price} gold.")
            )
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You buy {quantity} {item_instance['name']} for {total_price} gold.")
            )

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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name} to sell.")
            )
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

    async def _handle_look_command(self, player_id: int, params: str):
        """Handle look command - check if it's a direction or a target."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        current_room = character['room_id']

        # Map short directions to full names
        direction_map = {
            'n': 'north', 's': 'south', 'e': 'east', 'w': 'west',
            'ne': 'northeast', 'nw': 'northwest',
            'se': 'southeast', 'sw': 'southwest',
            'u': 'up', 'd': 'down'
        }

        # Normalize the direction
        target_lower = params.lower().strip()
        full_direction = direction_map.get(target_lower, target_lower)

        # Get available exits
        exits = self.game_engine.world_manager.get_exits_from_room(current_room, character)

        # Check if the params matches a direction
        if full_direction in exits:
            # It's a valid direction - show the adjacent room
            destination_room_id = exits[full_direction]

            # Send message about looking in that direction
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You look {full_direction}...\n"
            )

            # Show the room description for that direction
            await self.game_engine.world_manager.send_room_description_for_room(
                player_id,
                destination_room_id,
                character.get('id', player_id),
                detailed=True
            )
            return

        # Not a direction, treat as a target (NPC, mob, item, etc.)
        await self._handle_look_at_target(player_id, params)

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
                    # Check if the target player is invisible
                    active_effects = other_character.get('active_effects', [])
                    is_invisible = any(
                        effect.get('effect') in ['invisible', 'invisibility']
                        for effect in active_effects
                    )
                    if is_invisible:
                        # Can't see invisible players
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            error_message("You don't see that here.")
                        )
                        return
                    # Found a visible player - generate detailed description
                    description = self._generate_player_description(other_character)
                    await self.game_engine.connection_manager.send_message(player_id, description)
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

                    # Get current and max health (mobs use 'health' and 'max_health')
                    current_health = mob.get('health', mob.get('current_hit_points', 100))
                    max_health = mob.get('max_health', mob.get('max_hit_points', 100))

                    # Show health status if mob is damaged
                    if current_health < max_health:
                        health_percent = (current_health / max_health) * 100
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
        await self.game_engine.connection_manager.send_message(
            player_id,
            error_message(f"You don't see {target_name} here.")
        )

    async def _handle_special_action(self, player_id: int, command: str, params: str):
        """Handle special room actions like 'gaze mirror'."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Get room data
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            return

        # Check if room has special_actions defined
        room_data = self.game_engine.world_manager.rooms_data.get(room_id, {})
        special_actions = room_data.get('special_actions', {})

        # Build the full action string
        action_key = f"{command} {params}".strip()

        if action_key in special_actions:
            action_data = special_actions[action_key]
            action_type = action_data.get('type')
            action_message = action_data.get('message', '')

            if action_type == 'self_inspect':
                # Show the action message first
                if action_message:
                    await self.game_engine.connection_manager.send_message(player_id, action_message)

                # Generate and send player's own description
                description = self._generate_player_description(character)
                await self.game_engine.connection_manager.send_message(player_id, description)
            else:
                # Generic action - just show the message
                if action_message:
                    await self.game_engine.connection_manager.send_message(player_id, action_message)
        else:
            from ..utils.colors import error_message
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't {command} {params} here.")
            )

    def _generate_player_description(self, character: dict) -> str:
        """Generate a detailed description of a player based on their stats, class, race, and equipment."""
        name = character.get('name', 'Someone')

        # Get stats with effective bonuses
        from ..game.combat.combat_system import CombatSystem
        charisma = CombatSystem.get_effective_stat(character, 'charisma', 10)
        strength = CombatSystem.get_effective_stat(character, 'strength', 10)
        intelligence = CombatSystem.get_effective_stat(character, 'intelligence', 10)
        wisdom = CombatSystem.get_effective_stat(character, 'wisdom', 10)
        dexterity = CombatSystem.get_effective_stat(character, 'dexterity', 10)

        # Get species (race) and class
        race = character.get('species', character.get('race', 'human')).capitalize()
        char_class = character.get('class', 'fighter').capitalize()

        # Build description starting with name and charisma
        msg = f"{name} is a "

        # Charisma description
        if charisma >= 20:
            msg += "stunningly attractive"
        elif charisma >= 10:
            msg += "somewhat attractive"
        else:
            msg += "rather plain looking"

        # Strength + race + class
        if strength >= 20:
            msg += f" and powerfully built {race} {char_class}"
        elif strength >= 10:
            msg += f" and moderately built {race} {char_class}"
        else:
            msg += f" and slightly built {race} {char_class}"

        # Wisdom
        if wisdom >= 20:
            msg += ", with a worldly air about them"
        elif wisdom < 10:
            msg += ", with an inexperienced look about them"
        else:
            msg += ""

        msg += "."

        # Dexterity
        if dexterity >= 20:
            msg += " You notice that their movements are very quick and agile."
        elif dexterity < 10:
            msg += " You notice that their movements are rather slow and clumsy."

        # Intelligence
        if intelligence >= 20:
            msg += " They have a bright look in their eyes."
        elif intelligence < 10:
            msg += " They have a dull look in their eyes."

        # Equipment
        equipped = character.get('equipped', {})
        weapon = equipped.get('weapon')
        armor = equipped.get('armor')

        weapon_name = weapon.get('name', 'their fists') if weapon else 'their fists'
        armor_name = armor.get('name', 'plain clothes') if armor else 'plain clothes'

        msg += f" They are wearing {armor_name} and are armed with {weapon_name}."

        # Health status
        health = character.get('current_hit_points', character.get('max_health', 100))
        max_health = character.get('max_health', 100)
        health_percent = int((health / max_health) * 100)

        if health_percent < 25:
            msg += " They are sorely wounded."
        elif health_percent < 50:
            msg += " They seem to be moderately wounded."
        elif health_percent < 75:
            msg += " They appear to be wounded."
        elif health_percent < 100:
            msg += " They look as if they are lightly wounded."
        else:
            msg += " They seem to be in good physical condition."

        # Add rune description (only if player has a rune)
        rune = character.get('rune', '')
        if rune and rune not in [None, 'None', '']:
            rune_str = str(rune).strip()
            if rune_str:
                msg += f" You also notice a distinctive {rune_str.title()} rune inscribed on their forehead."

        return msg

    async def _handle_attack_command(self, player_id: int, target_name: str):
        """Handle attack command."""
        await self.game_engine.combat_system.handle_attack_command(player_id, target_name)

    async def _handle_shoot_command(self, player_id: int, params: str):
        """Handle shoot/fire command for ranged weapons.

        Supports:
        - shoot <target> - shoot target in current room
        - shoot <target> <direction> - shoot target in adjacent room
        - shoot <direction> <target> - alternate syntax for cross-room
        """
        if not params:
            await self.game_engine.connection_manager.send_message(player_id, "Shoot what?")
            return

        # Parse params to check for direction
        parts = params.strip().split()
        directions = ['north', 'n', 'south', 's', 'east', 'e', 'west', 'w',
                     'northeast', 'ne', 'northwest', 'nw', 'southeast', 'se',
                     'southwest', 'sw', 'up', 'u', 'down', 'd']

        target_name = None
        direction = None

        # Check for "shoot <direction> <target>" format
        if parts[0].lower() in directions:
            direction = parts[0].lower()
            target_name = " ".join(parts[1:]) if len(parts) > 1 else None
        # Check for "shoot <target> <direction>" format
        elif len(parts) > 1 and parts[-1].lower() in directions:
            direction = parts[-1].lower()
            target_name = " ".join(parts[:-1])
        # Just "shoot <target>" (same room)
        else:
            target_name = params

        if direction:
            # Cross-room shooting
            await self.game_engine.combat_system.handle_shoot_command_cross_room(
                player_id, target_name, direction
            )
        else:
            # Same-room shooting
            await self.game_engine.combat_system.handle_shoot_command(player_id, target_name)

    async def _handle_flee_command(self, player_id: int):
        """Handle flee command."""
        await self.game_engine.combat_system.handle_flee_command(player_id)

    async def _handle_buy_passage(self, player_id: int, character: dict):
        """Handle buying passage across the great lake between docks.

        Requirements:
        1. Player must have a rune (not 'None')
        2. Player must have enough gold (configurable cost)
        3. Player must be at valid dock location (mhv_docks or lht_docks)

        Events during voyage:
        - Rats may eat food (configurable chance)
        - Player may be robbed (configurable chance, random gold amount)
        """
        room_id = character.get('room_id')

        # Define dock locations and their destinations
        dock_routes = {
            'mhv_docks': 'lht_docks',  # Main human village docks -> Lakeside human town docks
            'lht_docks': 'mhv_docks'   # Lakeside human town docks -> Main human village docks
        }

        # Check if player is at a valid dock
        if room_id not in dock_routes:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You can only buy passage from the docks."
            )
            return

        # Check if player has a rune
        rune = character.get('rune', 'None')
        if not rune or rune == 'None' or rune == '' or str(rune).lower() == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                "Sorry, by decree of the guild masters, no one shall venture across the great lake who does not bear a rune upon their brow."
            )
            return

        # Get configuration settings
        cost = self.game_engine.config_manager.get_setting('ship_passage', 'cost', default=100)
        rat_chance = self.game_engine.config_manager.get_setting('ship_passage', 'rat_event_chance', default=0.15)
        robbery_chance = self.game_engine.config_manager.get_setting('ship_passage', 'robbery_event_chance', default=0.10)
        robbery_min = self.game_engine.config_manager.get_setting('ship_passage', 'robbery_gold_min', default=10)
        robbery_max = self.game_engine.config_manager.get_setting('ship_passage', 'robbery_gold_max', default=50)

        # Check if player has enough gold
        player_gold = character.get('gold', 0)
        if player_gold < cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Sorry, you cannot afford passage across the great lake! (Cost: {cost} gold, You have: {player_gold} gold)"
            )
            return

        # Deduct gold
        character['gold'] -= cost

        # Notify player and others in departure room
        player_name = character.get('name', 'Someone')
        await self.game_engine.connection_manager.send_message(
            player_id,
            "You buy passage across the great lake and board a ship..."
        )
        await self.game_engine._notify_room_except_player(
            room_id,
            player_id,
            f"{player_name} hands a small purse of coins to a ship's captain and boards a ship..."
        )

        # Random events during voyage
        import random

        # Rat event - eats food
        if random.random() < rat_chance:
            # Find a food item in inventory
            inventory = character.get('inventory', [])
            food_items = [item for item in inventory if item.get('type') == 'food']

            if food_items:
                # Remove a random food item
                food_to_remove = random.choice(food_items)
                inventory.remove(food_to_remove)
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"While aboard the ship your {food_to_remove.get('name', 'food')} was eaten by rats!"
                )

        # Robbery event - steal gold
        if random.random() < robbery_chance:
            # Calculate random amount to steal (but don't steal more than player has)
            max_steal = min(character.get('gold', 0), robbery_max)
            if max_steal >= robbery_min:
                stolen_amount = random.randint(robbery_min, max_steal)
                character['gold'] -= stolen_amount
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"While aboard the ship you seem to have been robbed! (Lost {stolen_amount} gold)"
                )

        # Teleport to destination
        destination_room_id = dock_routes[room_id]
        character['room_id'] = destination_room_id

        # Notify players at destination
        await self.game_engine._notify_room_except_player(
            destination_room_id,
            player_id,
            f"{player_name} has just arrived on a ship from across the great lake."
        )

        # Show room description to player
        await self.game_engine.world_manager.send_room_description(player_id, detailed=True)

    async def _handle_retrieve_ammo(self, player_id: int):
        """Handle retrieving spent ammunition from the current room."""
        await self.game_engine.combat_system.handle_retrieve_ammo(player_id)

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
        healer_obj = None
        for npc_obj in npcs_in_room:
            # Get NPC data from world manager using the NPC object's ID
            npc_data = self.game_engine.world_manager.get_npc_data(npc_obj.npc_id)
            print(f"[HEAL DEBUG] Checking NPC {npc_obj.npc_id}: {npc_data}")
            if npc_data:
                print(f"[HEAL DEBUG] NPC services: {npc_data.get('services', [])}")
                if 'healer' in npc_data.get('services', []):
                    healer_npc = npc_data
                    healer_obj = npc_obj
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
                    f"{healer_obj.name} doesn't seem to offer healing services."
                )
                return

            message = f"\n{healer_obj.name} offers the following healing services:\n\n"
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
        current_health = character.get('current_hit_points', 0)
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
            character['current_hit_points'] = max_health
        else:
            actual_heal = min(heal_amount, max_health - current_health)
            character['current_hit_points'] = min(current_health + heal_amount, max_health)

        # Deduct gold
        character['gold'] = player_gold - cost

        # Send message
        await self.game_engine.connection_manager.send_message(
            player_id,
            service_message(f"{healer_obj.name} channels healing energy into you. You are healed for {int(actual_heal)} HP!\nYou paid {cost} gold.\n\nHealth: {int(character['current_hit_points'])} / {int(max_health)}")
        )

    async def _handle_rent_room(self, player_id: int, character: dict):
        """Handle renting a room at an inn to restore HP and mana."""
        room_id = character.get('room_id')

        # Get room object
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            await self.game_engine.connection_manager.send_message(player_id, "You are nowhere!")
            return

        # Get NPCs in the room
        npcs_in_room = room.npcs if hasattr(room, 'npcs') else []

        # Find an innkeeper NPC
        innkeeper_npc = None
        innkeeper_obj = None
        for npc_obj in npcs_in_room:
            # Get NPC data from world manager using the NPC object's ID
            npc_data = self.game_engine.world_manager.get_npc_data(npc_obj.npc_id)
            if npc_data:
                # Check if NPC has innkeeper in services or is type innkeeper
                if 'innkeeper' in npc_data.get('services', []) or 'rooms' in npc_data.get('services', []):
                    innkeeper_npc = npc_data
                    innkeeper_obj = npc_obj
                    break

        if not innkeeper_npc:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "There is no innkeeper here. You must find an inn to rent a room."
            )
            return

        # Calculate room cost based on player level (base 10 gold + 5 gold per level)
        player_level = character.get('level', 1)
        room_cost = 10 + (player_level * 5)

        # Check if player has enough gold
        player_gold = character.get('gold', 0)
        if player_gold < room_cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't have enough gold to rent a room. A room costs {room_cost} gold, but you only have {player_gold} gold."
            )
            return

        # Check if player needs rest
        current_health = character.get('current_hit_points', 0)
        max_health = character.get('max_hit_points', current_health)
        current_mana = character.get('current_mana', character.get('current_mana', 0))
        max_mana = character.get('max_mana', current_mana)

        if current_health >= max_health and current_mana >= max_mana:
            # Get already rested message from NPC dialogue
            dialogue = innkeeper_npc.get('dialogue', {})
            already_rested_msg = dialogue.get('rent_already_rested', "You look well-rested already! Perhaps come back when you're weary.")
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"{innkeeper_obj.name} says: \"{already_rested_msg}\""
            )
            return

        # Restore HP and mana to full
        health_restored = max_health - current_health
        mana_restored = max_mana - current_mana

        character['current_hit_points'] = max_health
        character['current_mana'] = max_mana
        character['current_mana'] = max_mana  # For backward compatibility

        # Deduct gold
        character['gold'] = player_gold - room_cost

        # Get dialogue from NPC data
        dialogue = innkeeper_npc.get('dialogue', {})
        rent_accept = dialogue.get('rent_accept', "Wonderful! Let me show you to your room.")
        rent_description = dialogue.get('rent_description', "You follow the innkeeper up a creaky wooden staircase to a cozy room with a soft bed and a washbasin. The sheets are clean and the pillows are plump. You rest deeply through the night...")

        # Send atmospheric message
        message = f"{innkeeper_obj.name} says: \"{rent_accept}\"\n\n"
        message += f"{rent_description}\n\n"

        if health_restored > 0:
            message += f"You wake feeling refreshed and healed! (+{int(health_restored)} HP)\n"
        if mana_restored > 0:
            message += f"Your magical energy has been fully restored! (+{int(mana_restored)} Mana)\n"

        message += f"\nYou paid {room_cost} gold for the room.\n"
        message += f"Health: {int(character['current_hit_points'])} / {int(max_health)}\n"
        message += f"Mana: {int(character['current_mana'])} / {int(max_mana)}\n"
        message += f"Gold: {int(character['gold'])}"

        await self.game_engine.connection_manager.send_message(player_id, service_message(message))

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
                self.game_engine.logger.warning(f"Spell '{spell_id}' not found in spell_data for spellbook display")
                lines.append(f"{spell_id} (spell data not found)")
                lines.append("")
                continue

            # Get cooldown info
            cooldowns = character.get('spell_cooldowns', {})
            cooldown_remaining = cooldowns.get(spell_id, 0)

            # Format spell entry - with safe defaults
            name = spell.get('name', spell_id)
            level = spell.get('level', '?')
            mana = spell.get('mana_cost', '?')
            spell_type = spell.get('type', 'unknown')

            # Type-specific info
            type_info = ""
            if spell_type == 'damage':
                damage = spell.get('damage', '?')
                damage_type = spell.get('damage_type', 'physical')
                type_info = f"Damage: {damage} ({damage_type})"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'heal':
                effect = spell.get('effect', 'heal_hit_points')
                if effect == 'heal_hit_points':
                    heal = spell.get('heal_amount', '?')
                    type_info = f"Healing: {heal} HP"
                elif effect == 'cure_poison':
                    type_info = "Cures poison"
                elif effect == 'cure_hunger':
                    type_info = "Cures hunger"
                elif effect == 'cure_thirst':
                    type_info = "Quenches thirst"
                elif effect == 'cure_paralysis':
                    type_info = "Cures paralysis"
                elif effect == 'cure_drain':
                    type_info = "Restores drained stats"
                elif effect == 'regeneration':
                    type_info = "Regeneration over time"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'buff':
                effect = spell.get('effect', 'unknown')
                duration = spell.get('duration', 0)
                bonus = spell.get('bonus_amount', 0)
                if effect == 'ac_bonus':
                    type_info = f"Armor Class +{bonus} ({duration} seconds)"
                elif effect == 'invisible':
                    type_info = f"Invisibility ({duration} seconds)"
                else:
                    type_info = f"Effect: {effect} ({duration} seconds)"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'enhancement':
                effect = spell.get('effect', 'unknown')
                effect_amount = spell.get('effect_amount', '?')
                effect_map = {
                    'enhance_agility': 'Dexterity',
                    'enhance_dexterity': 'Dexterity',
                    'enhance_strength': 'Strength',
                    'enhance_constitution': 'Constitution',
                    'enhance_physique': 'Constitution',
                    'enhance_vitality': 'Vitality',
                    'enhance_stamina': 'Vitality',
                    'enhance_mental': 'INT/WIS/CHA',
                    'enhance_body': 'STR/DEX/CON'
                }
                stat_name = effect_map.get(effect, effect)
                type_info = f"Enhances {stat_name} by {effect_amount}"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'drain':
                damage = spell.get('damage', '?')
                damage_type = spell.get('damage_type', 'force')
                effect = spell.get('effect', None)
                type_info = f"Damage: {damage} ({damage_type})"
                if effect:
                    effect_amount = spell.get('effect_amount', '?')
                    duration = spell.get('effect_duration', '?')
                    effect_map = {
                        'drain_mana': 'Mana',
                        'drain_health': 'Health',
                        'drain_agility': 'Dexterity',
                        'drain_physique': 'Constitution',
                        'drain_stamina': 'Vitality',
                        'drain_mental': 'INT/WIS/CHA',
                        'drain_body': 'STR/DEX/CON'
                    }
                    drain_name = effect_map.get(effect, effect)
                    type_info += f" + Drains {drain_name} by {effect_amount} ({duration} rounds)"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'debuff':
                effect = spell.get('effect', 'unknown')
                duration = spell.get('effect_duration', '?')
                damage = spell.get('damage', None)
                if effect == 'paralyze':
                    type_info = f"Paralyzes target ({duration} rounds)"
                elif effect == 'charm':
                    type_info = f"Charms target, preventing attacks ({duration} rounds)"
                else:
                    type_info = f"Effect: {effect} ({duration} rounds)"
                if damage:
                    damage_type = spell.get('damage_type', 'force')
                    type_info += f" + Damage: {damage} ({damage_type})"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'summon':
                type_info = "Summons a creature"

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

    async def _handle_unlearn_spell_command(self, player_id: int, character: dict, spell_input: str):
        """Handle unlearning/forgetting a spell."""
        from ..utils.colors import error_message, success_message

        spellbook = character.get('spellbook', [])

        if not spellbook:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Your spellbook is empty. You don't know any spells to unlearn.")
            )
            return

        # Load spell data
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})

        # Find the spell by matching spell_input against spell IDs or spell names
        spell_id = None
        spell_name = None
        spell_input_lower = spell_input.lower()

        # First, try exact match on spell ID
        if spell_input_lower in spellbook:
            spell_id = spell_input_lower
            spell = spell_data.get(spell_id, {})
            spell_name = spell.get('name', spell_id)
        else:
            # Try partial match on spell name or ID
            matches = []
            for sid in spellbook:
                spell = spell_data.get(sid, {})
                sname = spell.get('name', sid)

                # Check if input matches spell ID or name (case insensitive, partial match)
                if spell_input_lower in sid.lower() or spell_input_lower in sname.lower():
                    matches.append((sid, sname))

            if len(matches) == 0:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You don't know a spell called '{spell_input}'. Use 'spellbook' to see your spells.")
                )
                return
            elif len(matches) == 1:
                spell_id, spell_name = matches[0]
            else:
                # Multiple matches - show options
                lines = [error_message(f"Multiple spells match '{spell_input}':")]
                for sid, sname in matches:
                    lines.append(f"  - {sname} ({sid})")
                lines.append("Please be more specific.")
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "\n".join(lines)
                )
                return

        # Remove the spell from spellbook
        character['spellbook'].remove(spell_id)

        # Also remove any active cooldown for this spell
        if 'spell_cooldowns' in character and spell_id in character['spell_cooldowns']:
            del character['spell_cooldowns'][spell_id]

        # Send success message
        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You have forgotten the spell: {spell_name}")
        )

        # Notify room
        room_id = character.get('room_id')
        await self.game_engine.player_manager.notify_room_except_player(
            room_id,
            player_id,
            f"{character.get('name', 'Someone')} concentrates deeply, erasing knowledge of a spell from their mind."
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

        # Check class restriction and spell level restrictions
        player_class = character.get('class', '').lower()
        spell_class_restriction = spell.get('class_restriction', '').lower()

        if spell_class_restriction and spell_class_restriction != player_class:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Only {spell_class_restriction}s can cast {spell['name']}."
            )
            return

        # Check spell level restrictions based on class
        spell_level = spell.get('level', 1)

        # Get max spell level from class data
        classes_data = self.game_engine.config_manager.game_data.get('classes', {})
        class_info = classes_data.get(player_class, {})
        max_spell_level = class_info.get('max_spell_level', 99)  # Default to 99 (no restriction)

        if max_spell_level > 0 and spell_level > max_spell_level:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"As a {character.get('class', 'adventurer')}, you can only cast spells up to level {max_spell_level}. {spell['name']} is level {spell_level}."
            )
            return

        # Check if player is paralyzed
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "You are paralyzed and cannot cast spells!"
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

        # Check if player is magically fatigued (all spell types cause fatigue)
        if self._is_spell_fatigued(player_id):
            fatigue_time = self._get_spell_fatigue_remaining(player_id)
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You are too magically exhausted to cast spells! Wait {fatigue_time:.1f} more seconds."
            )
            return

        # Validate target BEFORE consuming resources (mana and fatigue)
        # This prevents wasting resources on invalid targets
        if spell.get('requires_target', False):
            if not target_name:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You need a target to cast {spell['name']}. Use: cast {spell['name']} <target>"
                )
                return

            # Check if target exists
            room_id = character.get('room_id')
            target = await self.game_engine.combat_system.find_combat_target(room_id, target_name)

            if not target:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You don't see '{target_name}' here."
                )
                return

        # Check for duplicate buff/enhancement (before mana consumption)
        if spell['type'] in ['buff', 'enhancement']:
            # For self-cast buffs (no target specified and not AOE)
            area_of_effect = spell.get('area_of_effect', 'Single')
            if not target_name and area_of_effect != 'Area':
                spell_name = spell.get('name', 'Unknown')
                effect = spell.get('effect', 'unknown')

                # Initialize active_effects if it doesn't exist
                if 'active_effects' not in character:
                    character['active_effects'] = []

                active_effects = character['active_effects']

                for existing_effect in active_effects:
                    existing_spell_id = existing_effect.get('spell_id')
                    existing_effect_name = existing_effect.get('effect')

                    if existing_spell_id == spell_name or existing_effect_name == effect:
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            f"You are already under the effect of {spell_name}!"
                        )
                        return

        # Check mana
        mana_cost = spell['mana_cost']
        current_mana = character.get('current_mana', 0)

        if current_mana < mana_cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't have enough mana to cast {spell['name']}. (Need {mana_cost}, have {current_mana})"
            )
            return

        # Deduct mana
        character['current_mana'] = current_mana - mana_cost

        # Apply spell fatigue for ALL spell types (prevents spam casting)
        # Cooldown acts as a multiplier: 0 = 10s, 1 = 10s, 2 = 20s, 3 = 30s, etc.
        cooldown = spell.get('cooldown', 0)
        multiplier = max(1, cooldown)  # Minimum 1x for cooldown 0 or 1
        self._apply_spell_fatigue(player_id, multiplier)

        # Set cooldown (no longer used for fatigue, kept for potential future use)
        if spell.get('cooldown', 0) > 0:
            if 'spell_cooldowns' not in character:
                character['spell_cooldowns'] = {}
            character['spell_cooldowns'][spell_id] = spell['cooldown']

        # Check for spell failure
        caster_level = character.get('level', 1)
        caster_intelligence = character.get('intellect', 10)
        spell_min_level = spell.get('level', 1)

        failure_chance = self._calculate_player_spell_failure_chance(
            caster_level, caster_intelligence, spell_min_level
        )

        if random.random() < failure_chance:
            # Spell failed!
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You attempt to cast {spell['name']}, but the spell fizzles and fails!"
            )
            room_id = character.get('room_id')
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')}'s spell fizzles and fails!"
            )
            # Note: Mana was already consumed and fatigue already applied
            return

        # Apply spell effect based on type
        room_id = character.get('room_id')

        if spell['type'] == 'damage':
            await self._cast_damage_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] == 'heal':
            await self._cast_heal_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] == 'drain':
            await self._cast_drain_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] == 'debuff':
            await self._cast_debuff_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] in ['buff', 'enhancement']:
            await self._cast_buff_spell(player_id, character, spell, room_id, target_name)

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

            # Create temporary entities for hit calculation
            class TempCharacter:
                def __init__(self, char_data):
                    self.name = char_data['name']
                    self.level = char_data.get('level', 1)
                    self.strength = char_data.get('strength', 10)
                    self.dexterity = char_data.get('dexterity', 10)
                    self.constitution = char_data.get('constitution', 10)
                    self.intelligence = char_data.get('intellect', 10)
                    self.wisdom = char_data.get('wisdom', 10)
                    self.charisma = char_data.get('charisma', 10)

            class TempMob:
                def __init__(self, mob_data):
                    self.name = mob_data.get('name', 'Unknown')
                    self.level = mob_data.get('level', 1)
                    self.strength = 12
                    self.dexterity = 10
                    self.constitution = 12
                    self.intelligence = 8
                    self.wisdom = 10
                    self.charisma = 6

            temp_char = TempCharacter(character)
            temp_mob = TempMob(target)

            # Import damage calculator
            from ..game.combat.damage_calculator import DamageCalculator

            # Check spell hit (spells use INT for accuracy instead of DEX)
            mob_armor = target.get('armor_class', 0)
            base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)

            # For spells, swap INT/WIS for DEX in hit calculation
            saved_dex = temp_char.dexterity
            temp_char.dexterity = temp_char.intelligence  # Use INT for spell accuracy

            outcome = DamageCalculator.check_attack_outcome(temp_char, temp_mob, mob_armor, base_hit_chance)

            # Restore original DEX
            temp_char.dexterity = saved_dex

            if outcome['result'] == 'miss':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but it misses {target['name']}!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')}'s {spell['name']} misses {target['name']}!"
                )
                return
            elif outcome['result'] == 'dodge':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but {target['name']} dodges it!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{target['name']} dodges {character.get('name', 'Someone')}'s {spell['name']}!"
                )
                return
            elif outcome['result'] == 'deflect':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but {target['name']}'s defenses deflect it!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{target['name']}'s defenses deflect {character.get('name', 'Someone')}'s {spell['name']}!"
                )
                return

            # Spell hit! Roll damage
            damage_roll = spell.get('damage', '1d6')
            base_damage = self._roll_dice(damage_roll)

            # Apply level scaling if spell supports it
            caster_level = character.get('level', 1)
            damage = self._calculate_scaled_spell_value(base_damage, spell, caster_level)

            # Apply damage
            target['health'] -= damage

            # Apply poison DOT if damage type is poison
            damage_type = spell.get('damage_type', 'magical')
            poison_message = ""
            if damage_type == 'poison':
                poison_duration = spell.get('poison_duration', 5)
                poison_damage = spell.get('poison_damage', '1d2')

                # Initialize poison_effects if needed
                if 'poison_effects' not in target:
                    target['poison_effects'] = []

                # Add poison effect
                target['poison_effects'].append({
                    'duration': poison_duration,
                    'damage': poison_damage,
                    'caster_id': player_id,
                    'spell_name': spell['name']
                })
                poison_message = f" {target['name']} is poisoned!"

            # Send messages
            from ..utils.colors import spell_cast
            spell_msg = f"You cast {spell['name']}! It strikes {target['name']} for {int(damage)} {damage_type} damage!{poison_message}"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(spell_msg, damage_type=damage_type, spell_type=spell.get('type'))
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
                mob_participant_id = self.game_engine.combat_system.get_mob_identifier(target)
                await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)
            else:
                # Mob survived - set/update aggro on the caster
                if 'aggro_target' not in target:
                    target['aggro_target'] = player_id
                    target['aggro_room'] = room_id
                    self.game_engine.logger.debug(f"[AGGRO] {target['name']} is now aggro'd on player {player_id} (spell attack)")
                # Update aggro timestamp if this is the current aggro target
                if target.get('aggro_target') == player_id:
                    import time
                    target['aggro_last_attack'] = time.time()

        else:
            # Area spell (no specific target needed) - hits all mobs in the room
            mobs_in_room = self.game_engine.room_mobs.get(room_id, [])

            if not mobs_in_room:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but there are no enemies to affect!"
                )
                return

            # Roll damage once for the spell
            damage_roll = spell.get('damage', '1d6')
            base_damage = self._roll_dice(damage_roll)

            # Apply level scaling if spell supports it
            caster_level = character.get('level', 1)
            damage = self._calculate_scaled_spell_value(base_damage, spell, caster_level)

            # Send cast message to caster
            from ..utils.colors import spell_cast
            damage_type = spell.get('damage_type', 'magical')
            spell_msg = f"You cast {spell['name']}! A wave of {damage_type} energy fills the room!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(spell_msg, damage_type=damage_type, spell_type=spell.get('type'))
            )

            # Notify room
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} casts {spell['name']}! A wave of {spell.get('damage_type', 'magical')} energy fills the room!"
            )

            # Track defeated mobs to remove after loop
            defeated_mobs = []

            # Apply damage to all mobs
            for mob in mobs_in_room[:]:  # Create copy to avoid modification during iteration
                # Apply damage
                mob['health'] -= damage

                # Apply poison DOT if damage type is poison
                poison_message = ""
                if damage_type == 'poison':
                    poison_duration = spell.get('poison_duration', 5)
                    poison_damage = spell.get('poison_damage', '1d2')

                    # Initialize poison_effects if needed
                    if 'poison_effects' not in mob:
                        mob['poison_effects'] = []

                    # Add poison effect
                    mob['poison_effects'].append({
                        'duration': poison_duration,
                        'damage': poison_damage,
                        'caster_id': player_id,
                        'spell_name': spell['name']
                    })
                    poison_message = " (poisoned!)"

                # Send damage message
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"  {mob['name']} takes {int(damage)} {spell.get('damage_type', 'magical')} damage!{poison_message}"
                )

                # Check if mob died
                if mob['health'] <= 0:
                    defeated_mobs.append(mob)
                else:
                    # Mob survived - set aggro on the caster
                    if 'aggro_target' not in mob:
                        mob['aggro_target'] = player_id
                        mob['aggro_room'] = room_id
                        self.game_engine.logger.debug(f"[AGGRO] {mob['name']} is now aggro'd on player {player_id} (AOE spell)")
                    # Update aggro timestamp
                    if mob.get('aggro_target') == player_id:
                        import time
                        mob['aggro_last_attack'] = time.time()

            # Handle defeated mobs
            for mob in defeated_mobs:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"  {mob['name']} has been defeated!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"  {mob['name']} has been defeated!"
                )

                # Handle loot, gold, and experience
                await self.game_engine.combat_system.handle_mob_loot_drop(player_id, mob, room_id)

                # Remove mob from room
                mob_participant_id = self.game_engine.combat_system.get_mob_identifier(mob)
                await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)

    async def _cast_heal_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a healing spell or status cure spell."""
        from ..utils.colors import spell_cast

        # Check if this is a status cure spell instead of HP healing
        effect = spell.get('effect', 'heal_hit_points')

        if effect == 'cure_poison':
            # This is a cure poison spell, not a healing spell
            await self._cast_cure_poison_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect == 'cure_hunger':
            # Cure hunger spell
            await self._cast_cure_hunger_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect == 'cure_thirst':
            # Cure thirst spell
            await self._cast_cure_thirst_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect == 'cure_paralysis':
            # Cure paralysis spell
            await self._cast_cure_paralysis_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect == 'cure_drain':
            # Cure drain spell
            await self._cast_cure_drain_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect in ['cure_sleep', 'cure_blind']:
            # Other status cure effects - implement later if needed
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"The {effect} effect is not yet implemented."
            )
            return

        # This is a regular HP healing spell
        # Roll healing amount
        heal_roll = spell.get('heal_amount', '1d8')
        base_heal = self._roll_dice(heal_roll)

        # Apply level scaling if spell supports it
        caster_level = character.get('level', 1)
        heal_amount = self._calculate_scaled_spell_value(base_heal, spell, caster_level)

        # Check if this is an AOE heal
        area_of_effect = spell.get('area_of_effect', 'Single')

        if area_of_effect == 'Area':
            # AOE heal - heal all players in the room
            healed_players = []

            # Get all connected players
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room
                if other_character.get('room_id') != room_id:
                    continue

                # Get current and max health
                current_health = other_character.get('current_hit_points', 0)
                max_health = other_character.get('max_hit_points', 100)

                # Skip if already at full health
                if current_health >= max_health:
                    continue

                # Apply healing
                actual_heal = min(heal_amount, max_health - current_health)
                other_character['current_hit_points'] = min(current_health + heal_amount, max_health)

                # Send message to healed player
                if other_player_id == player_id:
                    heal_msg = f"You cast {spell['name']}! You are healed for {int(actual_heal)} HP.\nHealth: {int(other_character['current_hit_points'])} / {int(max_health)}"
                else:
                    heal_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! You are healed for {int(actual_heal)} HP.\nHealth: {int(other_character['current_hit_points'])} / {int(max_health)}"

                await self.game_engine.connection_manager.send_message(
                    other_player_id,
                    spell_cast(heal_msg, spell_type='heal')
                )

                healed_players.append(other_character.get('name', 'Someone'))

            # Notify room about the AOE heal
            if healed_players:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, and healing energy washes over the room!"
            else:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, but no one needs healing!"

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

        else:
            # Single-target heal
            # Determine target
            if spell.get('requires_target', False) and target_name:
                # Find target player by name
                target_player_id = None
                target_character = None

                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    other_character = other_conn_data.get('character')
                    if not other_character:
                        continue

                    # Check if player is in same room and name matches
                    if other_character.get('room_id') == room_id:
                        if other_character.get('name', '').lower() == target_name.lower():
                            target_player_id = other_player_id
                            target_character = other_character
                            break

                if not target_character:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You don't see '{target_name}' here."
                    )
                    return
            else:
                # Default to self-healing
                target_player_id = player_id
                target_character = character

            # Get current and max health
            current_health = target_character.get('current_hit_points', 0)
            max_health = target_character.get('max_hit_points', 100)

            # Check if target is already at full health
            if current_health >= max_health:
                if target_player_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']}, but you are already at full health!"
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are already at full health!"
                    )
                return

            # Apply healing
            actual_heal = min(heal_amount, max_health - current_health)
            target_character['current_hit_points'] = min(current_health + heal_amount, max_health)

            # Send messages
            if target_player_id == player_id:
                # Self-heal
                heal_msg = f"You cast {spell['name']}! You are healed for {int(actual_heal)} HP.\nHealth: {int(target_character['current_hit_points'])} / {int(max_health)}"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(heal_msg, spell_type='heal')
                )

                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')} casts {spell['name']} and glows with healing energy!"
                )
            else:
                # Healing another player
                caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! They are healed for {int(actual_heal)} HP."
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(caster_msg, spell_type='heal')
                )

                target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! You are healed for {int(actual_heal)} HP.\nHealth: {int(target_character['current_hit_points'])} / {int(max_health)}"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    spell_cast(target_msg, spell_type='heal')
                )

                # Notify other players in room (exclude caster and target)
                notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, who glows with healing energy!"
                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    if other_player_id == player_id or other_player_id == target_player_id:
                        continue
                    other_character = other_conn_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            notify_msg
                        )

    async def _cast_cure_poison_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure poison spell - removes poison DOT effects from target(s)."""
        from ..utils.colors import spell_cast

        # Check if this is an AOE cure
        area_of_effect = spell.get('area_of_effect', 'Single')

        if area_of_effect == 'Area':
            # AOE cure poison - cure all players in the room
            cured_players = []

            # Get all connected players in the room
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room
                if other_character.get('room_id') != room_id:
                    continue

                # Check if player has poison effects
                if 'poison_effects' in other_character and other_character['poison_effects']:
                    # Clear all poison effects
                    poison_count = len(other_character['poison_effects'])
                    other_character['poison_effects'] = []
                    cured_players.append(other_character.get('name', 'Someone'))

                    # Notify the cured player
                    if other_player_id == player_id:
                        cure_msg = f"You cast {spell['name']}! You are cured of {poison_count} poison effect(s)!"
                    else:
                        cure_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! You are cured of {poison_count} poison effect(s)!"

                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        spell_cast(cure_msg, spell_type='heal')
                    )

            # Notify room
            if cured_players:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, and a purifying mist washes over the room!"
            else:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, but no one is poisoned!"

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

        else:
            # Single-target cure poison
            # Determine target
            if spell.get('requires_target', False) and target_name:
                # Find target player by name
                target_player_id = None
                target_character = None

                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    other_character = other_conn_data.get('character')
                    if not other_character:
                        continue

                    # Check if player is in same room and name matches
                    if other_character.get('room_id') == room_id:
                        if other_character.get('name', '').lower() == target_name.lower():
                            target_player_id = other_player_id
                            target_character = other_character
                            break

                if not target_character:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You don't see '{target_name}' here."
                    )
                    return
            else:
                # Default to self-curing
                target_player_id = player_id
                target_character = character

            # Check if target has poison effects
            if 'poison_effects' not in target_character or not target_character['poison_effects']:
                if target_player_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']}, but you are not poisoned!"
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are not poisoned!"
                    )
                return

            # Clear poison effects
            poison_count = len(target_character['poison_effects'])
            target_character['poison_effects'] = []

            # Send messages
            if target_player_id == player_id:
                # Self-cure
                cure_msg = f"You cast {spell['name']}! You are cured of {poison_count} poison effect(s)!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(cure_msg, spell_type='heal')
                )

                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')} casts {spell['name']} and a green aura surrounds them!"
                )
            else:
                # Curing another player
                caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! They are cured of {poison_count} poison effect(s)!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(caster_msg, spell_type='heal')
                )

                target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! You are cured of {poison_count} poison effect(s)!"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    spell_cast(target_msg, spell_type='heal')
                )

                # Notify other players in room (exclude caster and target)
                notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, who is cured of poison!"
                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    if other_player_id == player_id or other_player_id == target_player_id:
                        continue
                    other_character = other_conn_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            notify_msg
                        )

    async def _cast_cure_hunger_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure hunger spell - restores hunger to full for target(s)."""
        from ..utils.colors import spell_cast

        # Check if this is an AOE cure
        area_of_effect = spell.get('area_of_effect', 'Single')

        if area_of_effect == 'Area':
            # AOE cure hunger - cure all players in the room
            cured_players = []

            # Get all connected players in the room
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room
                if other_character.get('room_id') != room_id:
                    continue

                # Restore hunger to full
                current_hunger = other_character.get('hunger', 100)
                if current_hunger < 100:
                    other_character['hunger'] = 100
                    cured_players.append(other_character.get('name', 'Someone'))

                    # Notify the cured player
                    if other_player_id == player_id:
                        cure_msg = f"You cast {spell['name']}! Your hunger is completely satisfied!"
                    else:
                        cure_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your hunger is completely satisfied!"

                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        spell_cast(cure_msg, spell_type='heal')
                    )

            # Notify room
            if cured_players:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, and a brownish mist fills the room!"
            else:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, but no one is hungry!"

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

        else:
            # Single-target cure hunger
            # Determine target
            if spell.get('requires_target', False) and target_name:
                # Find target player by name
                target_player_id = None
                target_character = None

                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    other_character = other_conn_data.get('character')
                    if not other_character:
                        continue

                    # Check if player is in same room and name matches
                    if other_character.get('room_id') == room_id:
                        if other_character.get('name', '').lower() == target_name.lower():
                            target_player_id = other_player_id
                            target_character = other_character
                            break

                if not target_character:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You don't see '{target_name}' here."
                    )
                    return
            else:
                # Default to self-curing
                target_player_id = player_id
                target_character = character

            # Check if target is hungry
            current_hunger = target_character.get('hunger', 100)
            if current_hunger >= 100:
                if target_player_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']}, but you are not hungry!"
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are not hungry!"
                    )
                return

            # Restore hunger to full
            target_character['hunger'] = 100

            # Send messages
            if target_player_id == player_id:
                # Self-cure
                cure_msg = f"You cast {spell['name']}! Your hunger is completely satisfied!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(cure_msg, spell_type='heal')
                )

                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')} casts {spell['name']} and a brownish aura surrounds them!"
                )
            else:
                # Curing another player
                caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! Their hunger is completely satisfied!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(caster_msg, spell_type='heal')
                )

                target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your hunger is completely satisfied!"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    spell_cast(target_msg, spell_type='heal')
                )

                # Notify other players in room (exclude caster and target)
                notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, satisfying their hunger!"
                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    if other_player_id == player_id or other_player_id == target_player_id:
                        continue
                    other_character = other_conn_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            notify_msg
                        )

    async def _cast_cure_thirst_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure thirst spell - restores thirst to full for target(s)."""
        from ..utils.colors import spell_cast

        # Check if this is an AOE cure
        area_of_effect = spell.get('area_of_effect', 'Single')

        if area_of_effect == 'Area':
            # AOE cure thirst - cure all players in the room
            cured_players = []

            # Get all connected players in the room
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room
                if other_character.get('room_id') != room_id:
                    continue

                # Restore thirst to full
                current_thirst = other_character.get('thirst', 100)
                if current_thirst < 100:
                    other_character['thirst'] = 100
                    cured_players.append(other_character.get('name', 'Someone'))

                    # Notify the cured player
                    if other_player_id == player_id:
                        cure_msg = f"You cast {spell['name']}! Your thirst is completely quenched!"
                    else:
                        cure_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your thirst is completely quenched!"

                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        spell_cast(cure_msg, spell_type='heal')
                    )

            # Notify room
            if cured_players:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, and a cool blue mist fills the room!"
            else:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, but no one is thirsty!"

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

        else:
            # Single-target cure thirst
            # Determine target
            if spell.get('requires_target', False) and target_name:
                # Find target player by name
                target_player_id = None
                target_character = None

                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    other_character = other_conn_data.get('character')
                    if not other_character:
                        continue

                    # Check if player is in same room and name matches
                    if other_character.get('room_id') == room_id:
                        if other_character.get('name', '').lower() == target_name.lower():
                            target_player_id = other_player_id
                            target_character = other_character
                            break

                if not target_character:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You don't see '{target_name}' here."
                    )
                    return
            else:
                # Default to self-curing
                target_player_id = player_id
                target_character = character

            # Check if target is thirsty
            current_thirst = target_character.get('thirst', 100)
            if current_thirst >= 100:
                if target_player_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']}, but you are not thirsty!"
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are not thirsty!"
                    )
                return

            # Restore thirst to full
            target_character['thirst'] = 100

            # Send messages
            if target_player_id == player_id:
                # Self-cure
                cure_msg = f"You cast {spell['name']}! Your thirst is completely quenched!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(cure_msg, spell_type='heal')
                )

                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')} casts {spell['name']} and a cool blue aura surrounds them!"
                )
            else:
                # Curing another player
                caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! Their thirst is completely quenched!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(caster_msg, spell_type='heal')
                )

                target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your thirst is completely quenched!"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    spell_cast(target_msg, spell_type='heal')
                )

                # Notify other players in room (exclude caster and target)
                notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, quenching their thirst!"
                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    if other_player_id == player_id or other_player_id == target_player_id:
                        continue
                    other_character = other_conn_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            notify_msg
                        )

    async def _cast_cure_paralysis_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure paralysis spell - removes paralysis effects from target."""
        from ..utils.colors import spell_cast, error_message

        # Determine target
        if spell.get('requires_target', False) and target_name:
            # Find target player by name
            target_player_id = None
            target_character = None

            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room and name matches
                if other_character.get('room_id') == room_id:
                    if other_character.get('name', '').lower() == target_name.lower():
                        target_player_id = other_player_id
                        target_character = other_character
                        break

            if not target_character:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You don't see '{target_name}' here.")
                )
                return
        else:
            # Default to self-curing
            target_player_id = player_id
            target_character = character

        # Check if target has paralysis effects
        if 'active_effects' not in target_character:
            target_character['active_effects'] = []

        # Remove paralysis effects (check both 'paralyze' and 'paralyzed')
        original_count = len(target_character['active_effects'])
        target_character['active_effects'] = [
            effect for effect in target_character['active_effects']
            if effect.get('type') not in ['paralyze', 'paralyzed'] and effect.get('effect') not in ['paralyze', 'paralyzed']
        ]
        effects_removed = original_count - len(target_character['active_effects'])

        if effects_removed == 0:
            # Target is not paralyzed
            if target_player_id == player_id:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but you are not paralyzed!"
                )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are not paralyzed!"
                )
            return

        # Send messages
        if target_player_id == player_id:
            # Self-cure
            cure_msg = f"You cast {spell['name']}! You can move freely again!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(cure_msg, spell_type='heal')
            )

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} casts {spell['name']} and their paralysis fades!"
            )
        else:
            # Curing another player
            caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! They can move freely again!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(caster_msg, spell_type='heal')
            )

            target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! You can move freely again!"
            await self.game_engine.connection_manager.send_message(
                target_player_id,
                spell_cast(target_msg, spell_type='heal')
            )

            # Notify other players in room (exclude caster and target)
            notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, freeing them from paralysis!"
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                if other_player_id == player_id or other_player_id == target_player_id:
                    continue
                other_character = other_conn_data.get('character')
                if other_character and other_character.get('room_id') == room_id:
                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        notify_msg
                    )

    async def _cast_cure_drain_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure drain spell - removes stat drain effects from target."""
        from ..utils.colors import spell_cast, error_message

        # Determine target
        if spell.get('requires_target', False) and target_name:
            # Find target player by name
            target_player_id = None
            target_character = None

            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room and name matches
                if other_character.get('room_id') == room_id:
                    if other_character.get('name', '').lower() == target_name.lower():
                        target_player_id = other_player_id
                        target_character = other_character
                        break

            if not target_character:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You don't see '{target_name}' here.")
                )
                return
        else:
            # Default to self-curing
            target_player_id = player_id
            target_character = character

        # Check if target has drain effects
        if 'active_effects' not in target_character:
            target_character['active_effects'] = []

        # Remove drain effects and restore stats
        original_count = len(target_character['active_effects'])
        drained_effects = [
            effect for effect in target_character['active_effects']
            if effect.get('type') == 'stat_drain' or 'drain' in effect.get('effect', '')
        ]

        # Restore drained stats
        for drain_effect in drained_effects:
            effect_type = drain_effect.get('effect', '')
            drain_amount = drain_effect.get('effect_amount', 0)

            # Restore the stats that were drained
            if 'drain' in effect_type:
                # Map drain effects to stats and restore them
                if effect_type == 'drain_agility':
                    target_character['dexterity'] = target_character.get('dexterity', 10) + drain_amount
                elif effect_type == 'drain_physique':
                    target_character['constitution'] = target_character.get('constitution', 10) + drain_amount
                elif effect_type == 'drain_stamina':
                    target_character['vitality'] = target_character.get('vitality', 10) + drain_amount
                elif effect_type == 'drain_mental':
                    # Restore all mental stats
                    target_character['intelligence'] = target_character.get('intelligence', 10) + drain_amount
                    target_character['intellect'] = target_character.get('intellect', 10) + drain_amount
                    target_character['wisdom'] = target_character.get('wisdom', 10) + drain_amount
                    target_character['charisma'] = target_character.get('charisma', 10) + drain_amount
                elif effect_type == 'drain_body':
                    # Restore all physical stats
                    target_character['strength'] = target_character.get('strength', 10) + drain_amount
                    target_character['dexterity'] = target_character.get('dexterity', 10) + drain_amount
                    target_character['constitution'] = target_character.get('constitution', 10) + drain_amount

        # Remove all drain effects
        target_character['active_effects'] = [
            effect for effect in target_character['active_effects']
            if effect.get('type') != 'stat_drain' and 'drain' not in effect.get('effect', '')
        ]
        effects_removed = len(drained_effects)

        if effects_removed == 0:
            # Target has no drain effects
            if target_player_id == player_id:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but you have no drained stats!"
                )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they have no drained stats!"
                )
            return

        # Send messages
        if target_player_id == player_id:
            # Self-cure
            cure_msg = f"You cast {spell['name']}! Your drained stats are restored!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(cure_msg, spell_type='heal')
            )

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} casts {spell['name']} and their strength returns!"
            )
        else:
            # Curing another player
            caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! Their drained stats are restored!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(caster_msg, spell_type='heal')
            )

            target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your drained stats are restored!"
            await self.game_engine.connection_manager.send_message(
                target_player_id,
                spell_cast(target_msg, spell_type='heal')
            )

            # Notify other players in room (exclude caster and target)
            notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, restoring their vitality!"
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                if other_player_id == player_id or other_player_id == target_player_id:
                    continue
                other_character = other_conn_data.get('character')
                if other_character and other_character.get('room_id') == room_id:
                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        notify_msg
                    )

    async def _cast_drain_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a drain spell that does damage and drains resources or stats."""
        from ..utils.colors import spell_cast, error_message

        # Drain spells require a target
        if not target_name:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You need a target to cast {spell['name']}. Use: cast {spell['name']} <target>")
            )
            return

        # Find target using combat system's method
        target = await self.game_engine.combat_system.find_combat_target(room_id, target_name)

        if not target:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't see '{target_name}' here.")
            )
            return

        # Roll damage
        damage_roll = spell.get('damage', '1d6')
        base_damage = self._roll_dice(damage_roll)

        # Apply level scaling if spell supports it
        caster_level = character.get('level', 1)
        damage = self._calculate_scaled_spell_value(base_damage, spell, caster_level)

        # Get damage type
        damage_type = spell.get('damage_type', 'force')
        effect = spell.get('effect', 'unknown')

        # Create temporary entities for hit calculation (same as damage spell)
        class TempCharacter:
            def __init__(self, char_data):
                self.name = char_data['name']
                self.level = char_data.get('level', 1)
                self.strength = char_data.get('strength', 10)
                self.dexterity = char_data.get('dexterity', 10)
                self.constitution = char_data.get('constitution', 10)
                self.intelligence = char_data.get('intellect', 10)
                self.wisdom = char_data.get('wisdom', 10)
                self.charisma = char_data.get('charisma', 10)

        class TempMob:
            def __init__(self, mob_data):
                self.name = mob_data.get('name', 'Unknown')
                self.level = mob_data.get('level', 1)
                self.strength = 12
                self.dexterity = 10
                self.constitution = 12
                self.intelligence = 8
                self.wisdom = 10
                self.charisma = 6

        temp_char = TempCharacter(character)
        temp_mob = TempMob(target)

        # Import damage calculator
        from ..game.combat.damage_calculator import DamageCalculator

        # Check spell hit (spells use INT for accuracy)
        mob_armor = target.get('armor_class', 0)
        base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)

        # For spells, swap INT/WIS for DEX in hit calculation
        saved_dex = temp_char.dexterity
        temp_char.dexterity = temp_char.intelligence

        outcome = DamageCalculator.check_attack_outcome(temp_char, temp_mob, mob_armor, base_hit_chance)

        # Restore original DEX
        temp_char.dexterity = saved_dex

        if outcome['result'] == 'miss':
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cast {spell['name']}, but it misses {target['name']}!"
            )
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')}'s {spell['name']} misses {target['name']}!"
            )
            return
        elif outcome['result'] == 'dodge':
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cast {spell['name']}, but {target['name']} dodges it!"
            )
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{target['name']} dodges {character.get('name', 'Someone')}'s {spell['name']}!"
            )
            return

        # Apply damage to target
        current_health = target.get('current_hit_points', target.get('max_hit_points', 20))
        new_health = max(0, current_health - damage)
        target['current_hit_points'] = new_health

        # Handle drain effects based on effect type
        drain_message = ""

        if effect == 'drain_mana':
            # Roll drain amount
            effect_amount_roll = spell.get('effect_amount', '-1d2')
            drain_amount = abs(self._roll_dice(effect_amount_roll))

            # Drain mana from target and give to caster
            target_current_mana = target.get('current_mana', 0)
            actual_drain = min(drain_amount, target_current_mana)

            if actual_drain > 0:
                target['current_mana'] = max(0, target_current_mana - actual_drain)
                caster_current_mana = character.get('current_mana', 0)
                caster_max_mana = character.get('max_mana', 50)
                character['current_mana'] = min(caster_current_mana + actual_drain, caster_max_mana)
                drain_message = f" You drain {int(actual_drain)} mana!"

        elif effect == 'drain_health':
            # Life steal - heal the caster for the damage dealt
            if spell.get('life_steal', False):
                caster_current_hp = character.get('current_hit_points', 0)
                caster_max_hp = character.get('max_hit_points', 100)
                heal_amount = min(damage, caster_max_hp - caster_current_hp)
                if heal_amount > 0:
                    character['current_hit_points'] = min(caster_current_hp + heal_amount, caster_max_hp)
                    drain_message = f" You absorb {int(heal_amount)} HP!"

        elif effect in ['drain_agility', 'drain_physique', 'drain_stamina', 'drain_mental', 'drain_body']:
            # Stat drain effects - apply debuff that reduces stats over time
            effect_amount_roll = spell.get('effect_amount', '-1d5')
            drain_amount = abs(self._roll_dice(effect_amount_roll))

            # Initialize active_effects if needed
            if 'active_effects' not in target:
                target['active_effects'] = []

            # Add drain debuff (lasts for duration, reducing stats)
            drain_duration = spell.get('effect_duration', 10)  # Default 10 ticks
            target['active_effects'].append({
                'type': 'stat_drain',
                'effect': effect,
                'duration': drain_duration,
                'effect_amount': drain_amount,
                'caster_id': player_id
            })

            # Apply immediate stat reduction
            self._apply_drain_effect(target, effect, drain_amount)
            drain_message = f" {target['name']}'s stats are drained by {drain_amount}!"

        # Send message to caster
        spell_msg = f"You cast {spell['name']}! It strikes {target['name']} for {int(damage)} {damage_type} damage!{drain_message}"
        await self.game_engine.connection_manager.send_message(
            player_id,
            spell_cast(spell_msg, damage_type=damage_type, spell_type='drain')
        )

        # Notify room
        await self.game_engine.player_manager.notify_room_except_player(
            room_id,
            player_id,
            f"{character.get('name', 'Someone')}'s {spell['name']} strikes {target['name']}!"
        )

        # Check if mob died
        if new_health <= 0:
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

            # Handle loot, gold, and experience (must be called before handle_mob_death)
            await self.game_engine.combat_system.handle_mob_loot_drop(player_id, target, room_id)

            # Remove mob from room
            mob_participant_id = self.game_engine.combat_system.get_mob_identifier(target)
            await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)
        else:
            # Mob survived - set/update aggro on the caster
            if 'aggro_target' not in target:
                target['aggro_target'] = player_id
                target['aggro_room'] = room_id
                self.game_engine.logger.debug(f"[AGGRO] {target['name']} is now aggro'd on player {player_id} (drain spell)")
            # Update aggro timestamp if this is the current aggro target
            if target.get('aggro_target') == player_id:
                import time
                target['aggro_last_attack'] = time.time()

    async def _cast_debuff_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a debuff spell (paralyze, slow, etc.) on target(s)."""
        from ..utils.colors import spell_cast

        effect = spell.get('effect', 'unknown')
        effect_duration = spell.get('effect_duration', 5)
        area_of_effect = spell.get('area_of_effect', 'Single')

        # Check if spell requires target
        if spell.get('requires_target', False) and not target_name:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You must specify a target for this spell."
            )
            return

        # Roll damage if the spell has a damage component
        damage = 0
        damage_type = spell.get('damage_type', 'force')
        if 'damage' in spell:
            damage_roll = spell.get('damage', '0')
            damage = self._roll_dice(damage_roll)

        targets_affected = []

        if area_of_effect == 'Area':
            # AOE debuff - affect all mobs in the room
            mobs = self.game_engine.room_mobs.get(room_id, [])

            for mob in mobs:
                # Apply damage if any
                if damage > 0:
                    current_health = mob.get('current_hit_points', mob.get('health', mob.get('max_hit_points', 20)))
                    new_health = max(0, current_health - damage)

                    if 'current_hit_points' in mob:
                        mob['current_hit_points'] = new_health
                    if 'health' in mob:
                        mob['health'] = new_health

                # Apply debuff effect
                if 'active_effects' not in mob:
                    mob['active_effects'] = []

                mob['active_effects'].append({
                    'type': effect,
                    'duration': effect_duration,
                    'effect': effect,
                    'effect_amount': spell.get('effect_amount', 0),
                    'caster_id': player_id
                })

                targets_affected.append(mob['name'])

                # Check if mob died from damage
                if damage > 0 and new_health <= 0:
                    mob_participant_id = self.game_engine.combat_system.get_mob_identifier(mob)
                    await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)

            if targets_affected:
                effect_name = effect.replace('_', ' ').title()
                damage_msg = f" dealing {damage} damage" if damage > 0 else ""
                spell_msg = f"You cast {spell['name']}! {effect_name} affects all enemies{damage_msg}!"

                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(spell_msg, spell_type='debuff')
                )

                # Notify room
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')} casts {spell['name']}! {', '.join(targets_affected)} are affected!"
                )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "There are no targets in range."
                )

        else:
            # Single target debuff
            if not target_name:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "You must specify a target."
                )
                return

            # Find the target mob
            target = None
            mobs = self.game_engine.room_mobs.get(room_id, [])

            for mob in mobs:
                if target_name.lower() in mob.get('name', '').lower():
                    target = mob
                    break

            if not target:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You don't see {target_name} here."
                )
                return

            # Apply damage if any
            if damage > 0:
                current_health = target.get('current_hit_points', target.get('health', target.get('max_hit_points', 20)))
                max_health = target.get('max_hit_points', target.get('max_health', 20))
                new_health = max(0, current_health - damage)

                if 'current_hit_points' in target:
                    target['current_hit_points'] = new_health
                if 'health' in target:
                    target['health'] = new_health

            # Apply debuff effect
            if 'active_effects' not in target:
                target['active_effects'] = []

            target['active_effects'].append({
                'type': effect,
                'duration': effect_duration,
                'effect': effect,
                'effect_amount': spell.get('effect_amount', 0),
                'caster_id': player_id
            })

            effect_name = effect.replace('_', ' ').title()
            damage_msg = ""
            if damage > 0:
                damage_msg = f" dealing {damage} {damage_type} damage and"

            spell_msg = f"You cast {spell['name']} on {target['name']}!{damage_msg} {effect_name}!"

            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(spell_msg, spell_type='debuff')
            )

            # Notify room
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')}'s {spell['name']} strikes {target['name']}!"
            )

            # Check if mob died from damage
            if damage > 0 and new_health <= 0:
                mob_participant_id = self.game_engine.combat_system.get_mob_identifier(target)
                await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)

    async def _cast_buff_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a buff/enhancement spell on self or target player(s)."""
        from ..utils.colors import spell_cast, error_message

        effect = spell.get('effect', 'unknown')
        duration = spell.get('duration', 0)
        spell_type = spell.get('type', 'buff')
        area_of_effect = spell.get('area_of_effect', 'Single')
        spell_name = spell.get('name', 'Unknown')

        # Calculate effect amount for enhancement spells
        effect_amount = 0
        if spell_type == 'enhancement':
            effect_amount_roll = spell.get('effect_amount', '0')
            if effect_amount_roll and effect_amount_roll != '0':
                # Strip leading + or - sign if present
                effect_amount_roll_str = str(effect_amount_roll).lstrip('+')
                effect_amount = self._roll_dice(effect_amount_roll_str)
            else:
                effect_amount = spell.get('bonus_amount', 0)
        else:
            effect_amount = spell.get('bonus_amount', 0)

        # Determine targets
        targets = []

        if area_of_effect == 'Area':
            # AOE buff - affect all players in the room (including caster)
            for other_player_id, other_player_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_player_data.get('character')
                if other_character and other_character.get('room_id') == room_id:
                    targets.append((other_player_id, other_character, other_player_data.get('username', 'Someone')))
        elif target_name:
            # Single target buff on another player
            target_found = False
            for other_player_id, other_player_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_player_data.get('character')
                if other_character and other_character.get('room_id') == room_id:
                    other_username = other_player_data.get('username', '')
                    if target_name.lower() in other_username.lower():
                        targets.append((other_player_id, other_character, other_username))
                        target_found = True
                        break

            if not target_found:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You don't see '{target_name}' here."
                )
                return
        else:
            # Self-buff
            targets.append((player_id, character, character.get('name', 'You')))

        # Apply buff to all targets
        for target_id, target_char, target_name_str in targets:
            # Initialize active_effects if needed
            if 'active_effects' not in target_char:
                target_char['active_effects'] = []

            # Check if target already has this buff/enhancement active
            already_has_buff = False
            for existing_effect in target_char['active_effects']:
                if existing_effect.get('spell_id') == spell_name or existing_effect.get('effect') == effect:
                    already_has_buff = True
                    break

            if already_has_buff:
                # Notify caster that target already has this buff
                if target_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message(f"You are already under the effect of {spell_name}!")
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message(f"{target_name_str} is already under the effect of {spell_name}!")
                    )
                continue  # Skip this target

            # Add the buff
            buff = {
                'spell_id': spell_name,
                'effect': effect,
                'duration': duration,
                'bonus_amount': spell.get('bonus_amount', 0),
                'effect_amount': effect_amount
            }
            target_char['active_effects'].append(buff)

            # Apply immediate effect for enhancements
            if spell_type == 'enhancement' and effect_amount > 0:
                effect_msg = self._apply_enhancement_effect(target_char, effect, effect_amount)

                # Message to caster
                if target_id == player_id:
                    spell_msg = f"You cast {spell['name']}! {effect_msg}"
                else:
                    spell_msg = f"You cast {spell['name']} on {target_name_str}! {effect_msg}"

                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(spell_msg, spell_type='enhancement')
                )

                # Message to target (if different from caster)
                if target_id != player_id:
                    await self.game_engine.connection_manager.send_message(
                        target_id,
                        spell_cast(f"{character.get('name', 'Someone')} casts {spell['name']} on you! {effect_msg}", spell_type='enhancement')
                    )
            else:
                # Regular buff message
                if target_id == player_id:
                    spell_msg = f"You cast {spell['name']}! {spell.get('description', '')}"
                else:
                    spell_msg = f"You cast {spell['name']} on {target_name_str}!"

                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(spell_msg, spell_type=spell_type)
                )

                # Message to target (if different from caster)
                if target_id != player_id:
                    await self.game_engine.connection_manager.send_message(
                        target_id,
                        spell_cast(f"{character.get('name', 'Someone')} casts {spell['name']} on you!", spell_type=spell_type)
                    )

        # Notify room
        if area_of_effect == 'Area':
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} casts {spell['name']}, affecting everyone in the area!"
            )
        elif len(targets) > 0 and targets[0][0] != player_id:
            # Notify other players except caster and target
            for other_player_id, other_player_data in self.game_engine.player_manager.connected_players.items():
                if other_player_id != player_id and other_player_id != targets[0][0]:
                    other_character = other_player_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            f"{character.get('name', 'Someone')} casts {spell['name']} on {targets[0][2]}!"
                        )
        else:
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} casts {spell['name']}!"
            )

    def _apply_drain_effect(self, target: dict, effect: str, amount: int):
        """Apply a drain effect to reduce a target's stats.

        Args:
            target: The target (mob or character) dictionary
            effect: The drain effect type
            amount: The amount to drain (reduce)
        """
        drain_map = {
            'drain_agility': 'dexterity',
            'drain_physique': 'constitution',
            'drain_stamina': 'vitality'
        }

        if effect in drain_map:
            stat_key = drain_map[effect]
            current_value = target.get(stat_key, 10)
            target[stat_key] = max(1, current_value - amount)
        elif effect == 'drain_mental':
            # Drain all mental stats (INT, WIS, CHA)
            target['intelligence'] = max(1, target.get('intelligence', target.get('intellect', 10)) - amount)
            target['intellect'] = max(1, target.get('intellect', 10) - amount)
            target['wisdom'] = max(1, target.get('wisdom', 10) - amount)
            target['charisma'] = max(1, target.get('charisma', 10) - amount)
        elif effect == 'drain_body':
            # Drain all physical stats (STR, DEX, CON)
            target['strength'] = max(1, target.get('strength', 10) - amount)
            target['dexterity'] = max(1, target.get('dexterity', 10) - amount)
            target['constitution'] = max(1, target.get('constitution', 10) - amount)

    def _apply_enhancement_effect(self, character: dict, effect: str, amount: int) -> str:
        """Apply an enhancement effect to a character's stats.

        Args:
            character: The character dictionary
            effect: The enhancement effect type
            amount: The amount to enhance by

        Returns:
            A message describing the effect
        """
        effect_map = {
            'enhance_agility': ('dexterity', 'agility'),
            'enhance_dexterity': ('dexterity', 'dexterity'),
            'enhance_strength': ('strength', 'strength'),
            'enhance_constitution': ('constitution', 'constitution'),
            'enhance_vitality': ('vitality', 'vitality'),
            'enhance_intelligence': ('intellect', 'intelligence'),
            'enhance_wisdom': ('wisdom', 'wisdom'),
            'enhance_charisma': ('charisma', 'charisma'),
            # Aliases for compatibility
            'enhance_physique': ('constitution', 'constitution'),
            'enhance_stamina': ('vitality', 'vitality')
        }

        if effect in effect_map:
            stat_key, stat_name = effect_map[effect]
            old_value = character.get(stat_key, 10)
            character[stat_key] = old_value + amount
            return f"Your {stat_name} increases by {amount}! ({old_value} -> {character[stat_key]})"
        elif effect == 'enhance_mental':
            # Enhance all mental stats (INT, WIS, CHA)
            int_old = character.get('intellect', 10)
            wis_old = character.get('wisdom', 10)
            cha_old = character.get('charisma', 10)
            character['intellect'] = int_old + amount
            character['wisdom'] = wis_old + amount
            character['charisma'] = cha_old + amount
            return f"Your mental faculties sharpen! INT +{amount}, WIS +{amount}, CHA +{amount}"
        elif effect == 'enhance_body':
            # Enhance all physical stats (STR, DEX, CON)
            str_old = character.get('strength', 10)
            dex_old = character.get('dexterity', 10)
            con_old = character.get('constitution', 10)
            character['strength'] = str_old + amount
            character['dexterity'] = dex_old + amount
            character['constitution'] = con_old + amount
            return f"Your body surges with power! STR +{amount}, DEX +{amount}, CON +{amount}"
        elif effect == 'ac_bonus':
            return f"A magical barrier surrounds you, increasing your armor class by {amount}!"
        elif effect == 'invisible':
            return "You fade from view, becoming invisible!"

        return f"You feel the power of the spell course through you!"

    def _roll_dice(self, dice_string: str) -> int:
        """Roll dice from a string like '2d6+3', '1d8', or '-1d5' (negative)."""
        import re

        # Handle negative dice notation (e.g., '-1d5') by stripping the leading minus
        # and making the result negative after rolling
        is_negative = dice_string.strip().startswith('-')
        if is_negative:
            dice_string = dice_string.strip()[1:]  # Remove the leading minus

        # Parse the dice string
        match = re.match(r'(\d+)d(\d+)([+-]\d+)?', dice_string.lower())
        if not match:
            return 0

        num_dice = int(match.group(1))
        die_size = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0

        # Roll the dice
        total = sum(random.randint(1, die_size) for _ in range(num_dice))
        result = total + modifier

        # Apply negative if original string was negative
        return -result if is_negative else result

    def _calculate_scaled_spell_value(self, base_value: int, spell: dict, caster_level: int) -> int:
        """Calculate scaled spell damage or healing based on caster level.

        Args:
            base_value: The base rolled damage or healing value
            spell: The spell data dictionary
            caster_level: The caster's character level

        Returns:
            The scaled value
        """
        scales_with_level = spell.get('scales_with_level', 'No')

        if scales_with_level not in ['Yes', 'yes', True]:
            return base_value

        # Multiplicative scaling: base damage × caster level
        # Example: Level 18 caster with 8 base damage = 8 × 18 = 144 damage
        scaled_value = base_value * caster_level

        return scaled_value

    def _calculate_player_spell_failure_chance(self, caster_level: int, caster_intelligence: int, spell_min_level: int) -> float:
        """Calculate the chance that a player's spell cast will fail.

        Args:
            caster_level: Level of the caster
            caster_intelligence: Intelligence stat of the caster
            spell_min_level: Minimum level required for the spell

        Returns:
            Float between 0.0 and 0.50 representing failure chance (0.10 = 10% chance to fail)
        """
        # Base failure rate: 5%
        base_failure = 0.05

        # Level difference penalty: +10% per level if spell is above caster's level
        level_penalty = 0.0
        if spell_min_level > caster_level:
            level_penalty = (spell_min_level - caster_level) * 0.10

        # Intelligence bonus: reduce failure based on intelligence modifier
        # D&D style: (stat - 10) / 2 = modifier
        intelligence_modifier = (caster_intelligence - 10) / 2
        intelligence_bonus = intelligence_modifier * 0.01  # 1% per modifier point

        # Calculate final failure chance
        failure_chance = base_failure + level_penalty - intelligence_bonus

        # Clamp between 0% and 50% (players are generally more skilled than mobs)
        failure_chance = max(0.0, min(0.50, failure_chance))

        return failure_chance

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

    def _class_uses_magic(self, class_name: str) -> bool:
        """Check if a character class uses magic.

        Args:
            class_name: The name of the class (e.g., 'fighter', 'sorcerer')

        Returns:
            True if the class uses magic, False otherwise
        """
        import json
        from pathlib import Path

        try:
            classes_file = Path("data/player/classes.json")
            with open(classes_file, 'r') as f:
                classes_data = json.load(f)
                class_key = class_name.lower()
                if class_key in classes_data:
                    return classes_data[class_key].get('uses_magic', False)
        except Exception as e:
            self.game_engine.logger.warning(f"Could not load class data: {e}")

        # Default: assume non-magic class
        return False

    def _distribute_stat_points(self, character: dict, points_to_distribute: int) -> dict:
        """Automatically distribute stat points across character stats up to their maximums.

        Args:
            character: The character dictionary
            points_to_distribute: Number of stat points to distribute

        Returns:
            Dictionary of stat name -> amount increased
        """
        import random
        import json
        from pathlib import Path

        # Load race data to get modifiers
        races_file = Path("data/player/races.json")
        race_modifiers = {}
        try:
            with open(races_file, 'r') as f:
                races_data = json.load(f)
                player_race = character.get('race', 'human')
                if player_race in races_data:
                    race_modifiers = races_data[player_race].get('stat_modifiers', {})
        except Exception as e:
            self.game_engine.logger.warning(f"Could not load race modifiers: {e}")

        # Get base stat maximums from config
        starting_stats = self.game_engine.config_manager.get_setting('player', 'starting_stats', default={})

        # Define stat list (map character field names to config names)
        stat_mapping = {
            'strength': 'strength',
            'dexterity': 'dexterity',
            'constitution': 'constitution',
            'vitality': 'vitality',
            'intellect': 'intelligence',  # character uses 'intellect', config uses 'intelligence'
            'wisdom': 'wisdom',
            'charisma': 'charisma'
        }

        # Calculate max for each stat (base max + race modifier)
        stat_maxes = {}
        for char_stat, config_stat in stat_mapping.items():
            base_max = starting_stats.get(config_stat, {}).get('max', 20)
            race_mod = race_modifiers.get(config_stat, 0)
            stat_maxes[char_stat] = base_max + race_mod

        # Track increases
        stat_increases = {stat: 0 for stat in stat_mapping.keys()}

        # Distribute points randomly
        for _ in range(points_to_distribute):
            # Get stats that haven't reached their maximum
            available_stats = [
                stat for stat in stat_mapping.keys()
                if character.get(stat, 10) < stat_maxes[stat]
            ]

            if not available_stats:
                # All stats are at max
                break

            # Randomly pick a stat and increase it
            chosen_stat = random.choice(available_stats)
            character[chosen_stat] = character.get(chosen_stat, 10) + 1
            stat_increases[chosen_stat] += 1

        return stat_increases

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

        # Roll new random stats using configured ranges
        import random
        stat_ranges = self.game_engine.config_manager.get_setting('player', 'starting_stats', default={})

        def roll_stat(stat_name):
            """Roll a stat within the configured min/max range."""
            stat_config = stat_ranges.get(stat_name, {})
            if isinstance(stat_config, dict) and 'min' in stat_config and 'max' in stat_config:
                return random.randint(stat_config['min'], stat_config['max'])
            # Fallback to 3d6 if no config
            return sum(random.randint(1, 6) for _ in range(3))

        old_stats = {
            'strength': character.get('strength', 10),
            'dexterity': character.get('dexterity', 10),
            'constitution': character.get('constitution', 10),
            'vitality': character.get('vitality', 10),
            'intellect': character.get('intellect', 10),
            'wisdom': character.get('wisdom', 10),
            'charisma': character.get('charisma', 10)
        }

        base_stats = {
            'strength': roll_stat('strength'),
            'dexterity': roll_stat('dexterity'),
            'constitution': roll_stat('constitution'),
            'vitality': roll_stat('vitality'),
            'intellect': roll_stat('intelligence'),
            'wisdom': roll_stat('wisdom'),
            'charisma': roll_stat('charisma')
        }

        # Apply race modifiers
        for stat, value in race_data.get('stat_modifiers', {}).items():
            base_stats[stat] = base_stats.get(stat, 10) + value

        # Apply class modifiers
        for stat, value in class_data.get('stat_modifiers', {}).items():
            base_stats[stat] = base_stats.get(stat, 10) + value

        # Update character stats
        character.update(base_stats)

        # This is the REROLL command - should reset HP from scratch
        # Formula: baseVitality + raceModifier + classModifier + staminaBonus
        old_max_hp = character.get('max_hit_points', 0)

        # New base vitality roll (8-20)
        base_vitality = random.randint(8, 20)

        # Race vitality modifier
        race_vitality_mod = race_data.get('stat_modifiers', {}).get('vitality', 0)

        # Class vitality modifier
        class_vitality_mod = class_data.get('stat_modifiers', {}).get('vitality', 0)

        # Stamina (constitution) HP bonus lookup table
        constitution = character['constitution']
        stamina_hp_bonus = self._get_stamina_hp_bonus(constitution)

        # Final calculation (minimum 8 HP) - resets to new value
        max_hp = max(8, base_vitality + race_vitality_mod + class_vitality_mod + stamina_hp_bonus)

        # Recalculate max mana
        intellect = character['intellect']
        mana_modifier = class_data.get('mana_modifier', 1.0)
        base_mana = intellect * 3
        random_mana = random.randint(1, 5)
        max_mana = int((base_mana + random_mana) * mana_modifier)

        # Update HP and mana
        old_max_mana = character.get('max_mana', 0)

        character['max_hit_points'] = max_hp
        character['current_hit_points'] = max_hp
        character['max_mana'] = max_mana
        character['current_mana'] = max_mana

        # Update max encumbrance based on new strength
        self.game_engine.player_manager.update_encumbrance(character)

        # Show before and after stats
        reroll_msg = f"""
=== Stats Rerolled! ===

Old Stats:
STR: {old_stats['strength']}  DEX: {old_stats['dexterity']}  CON: {old_stats['constitution']}  VIT: {old_stats.get('vitality', 0)}
INT: {old_stats['intellect']}  WIS: {old_stats['wisdom']}  CHA: {old_stats['charisma']}
HP: {old_max_hp}  Mana: {old_max_mana}

New Stats:
STR: {character['strength']}  DEX: {character['dexterity']}  CON: {character['constitution']}  VIT: {character.get('vitality', 0)}
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
        mana_per_level = self.game_engine.config_manager.get_setting('player', 'leveling', 'mana_per_level', default=5)
        stat_points = self.game_engine.config_manager.get_setting('player', 'leveling', 'stat_points_per_level', default=2)

        # Load race and class data for modifiers
        races = self._load_races()
        classes = self._load_classes()
        player_race = character.get('species', 'human').lower()
        player_class = character.get('class', 'fighter').lower()
        race_data = races.get(player_race, races.get('human', {}))
        class_data = classes.get(player_class, classes.get('fighter', {}))

        # Increase max HP using vitality formula (same as training)
        # Formula: oldMaxVitality + newRoll + raceModifier + classModifier + staminaBonus
        old_max_hp = character.get('max_hit_points', 100)

        # New base vitality roll (8-20)
        new_vitality_roll = random.randint(8, 20)

        # Race vitality modifier
        race_vitality_mod = race_data.get('stat_modifiers', {}).get('vitality', 0)

        # Class vitality modifier
        class_vitality_mod = class_data.get('stat_modifiers', {}).get('vitality', 0)

        # Stamina (constitution) HP bonus lookup table
        constitution = character.get('constitution', 10)
        stamina_hp_bonus = self._get_stamina_hp_bonus(constitution)

        # Final calculation: old max + new roll + modifiers + stamina bonus (minimum 8 HP gain)
        hp_gain = new_vitality_roll + race_vitality_mod + class_vitality_mod + stamina_hp_bonus
        new_max_hp = old_max_hp + max(8, hp_gain)
        character['max_hit_points'] = new_max_hp

        # Check if class uses magic
        player_class = character.get('class', 'fighter')
        class_uses_magic = self._class_uses_magic(player_class)

        # Increase max mana (only for magic-using classes)
        old_max_mana = character.get('max_mana', 0)
        new_max_mana = old_max_mana
        if class_uses_magic:
            new_max_mana = old_max_mana + mana_per_level
            character['max_mana'] = new_max_mana

        # Fully restore health on level up
        character['current_hit_points'] = new_max_hp

        # Fully restore mana on level up (only for magic-using classes)
        if class_uses_magic:
            character['current_mana'] = new_max_mana

        # Automatically distribute stat points
        stat_increases = self._distribute_stat_points(character, stat_points)

        # Send level up messages
        stat_gains_text = "\n".join([f"  {stat.capitalize()}: +{amount}" for stat, amount in stat_increases.items() if amount > 0])

        # Build mana line only if class uses magic
        mana_line = f"  Max Mana: {old_max_mana} -> {new_max_mana}\n" if class_uses_magic else ""

        level_up_msg = f"""
========================================
         LEVEL UP!
========================================
  Level: {old_level} -> {new_level}
  Max HP: {old_max_hp} -> {new_max_hp}
{mana_line}
  Stat Increases:
{stat_gains_text}
========================================

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
                self.game_engine.player_storage.save_character_data(username, character)

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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Invalid amount. Usage: givegold <amount>")
            )

    async def _handle_admin_give_item(self, player_id: int, character: dict, params: str):
        """Admin command to give an item to the current player."""
        item_id = params.strip().lower()

        # Load items from all JSON files in data/items/
        items = self.game_engine.config_manager.load_items()
        if not items:
            await self.game_engine.connection_manager.send_message(player_id, "[ADMIN] No items found in data/items/")
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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Invalid amount. Usage: givexp <amount>")
            )

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
                mob_hp = mob.get('current_hit_points', 0)
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

        # Choose best starting room: player's current room, or room with most connections
        player_data = self.game_engine.player_manager.get_player_data(player_id)
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
            quest_list.append(f"[{status}] {quest['name']} (ID: {quest_id})")

            if not quest_progress.get('completed'):
                # Show objectives
                for i, objective in enumerate(quest.get('objectives', [])):
                    obj_progress = quest_progress['objectives'].get(i, {})
                    progress = obj_progress.get('progress', 0)
                    required = obj_progress.get('required', 1)
                    quest_list.append(f"  - {progress}/{required} {objective['type']} {objective.get('target', '')}")

            quest_list.append("")

        await self.game_engine.connection_manager.send_message(player_id, "\n".join(quest_list))

    async def _handle_abandon_quest(self, player_id: int, character: dict, quest_id: str):
        """Abandon a quest."""
        quest_id = quest_id.strip()

        if not quest_id:
            await self.game_engine.connection_manager.send_message(player_id, "Usage: abandon <quest_id>")
            await self.game_engine.connection_manager.send_message(player_id, "Use 'quests' to see your active quest IDs.")
            return

        # Check if quest exists
        quest = self.game_engine.quest_manager.get_quest(quest_id)
        if not quest:
            await self.game_engine.connection_manager.send_message(player_id, f"Unknown quest: {quest_id}")
            return

        # Check if player has the quest
        if not self.game_engine.quest_manager.has_quest(character, quest_id):
            await self.game_engine.connection_manager.send_message(player_id, f"You don't have the quest '{quest['name']}'.")
            return

        # Check if quest is completed but not rewarded
        if self.game_engine.quest_manager.is_quest_complete(character, quest_id):
            quest_data = character['quests'][quest_id]
            if not quest_data.get('rewarded', False):
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cannot abandon '{quest['name']}' - it's completed! Return to the quest giver to claim your reward."
                )
                return

        # Abandon the quest
        if self.game_engine.quest_manager.abandon_quest(character, quest_id):
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You have abandoned the quest '{quest['name']}'."
            )
        else:
            await self.game_engine.connection_manager.send_message(player_id, "Failed to abandon quest.")

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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("There is no one here to talk to.")
            )
            return

        # Find NPC in the current room by partial name match
        npc_obj = None
        npc_name_lower = npc_name.lower()
        for npc in room.npcs:
            if npc_name_lower in npc.name.lower() or npc_name_lower in npc.npc_id.lower():
                npc_obj = npc
                break

        if not npc_obj:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"There is no '{npc_name}' here.")
            )
            return

        # Get NPC data from world manager
        npc_data = self.game_engine.world_manager.get_npc_data(npc_obj.npc_id)

        if not npc_data:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"{npc_obj.name} has nothing to say.")
            )
            return

        # Check if NPC has quests
        npc_quests = npc_data.get('quests', [])
        if not npc_quests:
            # For vendors and other NPCs, use default dialogue if available, otherwise greeting
            dialogue = npc_data.get('dialogue', {})

            # Check if this is a vendor (has a shop)
            if npc_data.get('shop') or (npc_data.get('services') and 'shop' in npc_data.get('services', [])):
                # Vendor: use default dialogue
                response = dialogue.get('default', dialogue.get('greeting', f"{npc_data['name']} has nothing to say."))
            else:
                # Regular NPC: use greeting
                response = dialogue.get('greeting', f"{npc_data['name']} has nothing to say.")

            await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{response}\"")
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
                    await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{completed_already}\"")
                else:
                    # Give reward
                    quest_complete_msg = npc_data.get('dialogue', {}).get('quest_complete', "You have completed the quest!")
                    await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{quest_complete_msg}\"")

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
                await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{in_progress}\"")
                return

            # Offer the quest
            can_accept, reason = self.game_engine.quest_manager.can_accept_quest(character, quest_id)
            if not can_accept:
                await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{reason}\"")
                return

            quest_available = npc_data.get('dialogue', {}).get('quest_available', "I have a quest for you.")
            await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{quest_available}\"")
            await self.game_engine.connection_manager.send_message(player_id, f"\nType 'accept {quest_id}' to accept this quest.")
            return

        # No quest interaction needed - show default dialogue for quest givers as fallback
        dialogue = npc_data.get('dialogue', {})
        response = dialogue.get('greeting', f"{npc_data['name']} greets you.")
        await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{response}\"")

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

    async def _handle_ability_command(self, player_id: int, character: dict, ability: dict, params: str):
        """Handle execution of a class ability command.

        Args:
            player_id: The player ID
            character: Character data dictionary
            ability: The ability dictionary
            params: Additional parameters for the ability
        """
        ability_id = ability['id']
        ability_name = ability['name']

        # Execute the ability through the ability system
        result = await self.game_engine.ability_system.execute_active_ability(
            player_id,
            ability,
            target_name=params if params else None
        )

        if not result['success']:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(result['message'])
            )
            return

        # Handle specific ability types
        ability_id = ability['id']

        # Rogue abilities
        if ability_id == 'picklock':
            await self._execute_picklock_ability(player_id, character, ability, params)
        elif ability_id == 'backstab':
            await self._execute_backstab_ability(player_id, character, ability, params)
        elif ability_id == 'shadow_step':
            await self._execute_shadow_step_ability(player_id, character, ability)
        elif ability_id == 'poison_blade':
            await self._execute_poison_blade_ability(player_id, character, ability)
        # Fighter abilities
        elif ability_id == 'power_attack':
            await self._execute_power_attack_ability(player_id, character, ability, params)
        elif ability_id == 'cleave':
            await self._execute_cleave_ability(player_id, character, ability)
        elif ability_id == 'dual_wield':
            await self._execute_dual_wield_ability(player_id, character, ability)
        elif ability_id == 'shield_bash':
            await self._execute_shield_bash_ability(player_id, character, ability, params)
        elif ability_id == 'battle_cry':
            await self._execute_battle_cry_ability(player_id, character, ability)
        # Ranger abilities
        elif ability_id == 'track':
            await self._execute_track_ability(player_id, character, ability)
        elif ability_id == 'tame':
            await self._execute_tame_ability(player_id, character, ability, params)
        elif ability_id == 'pathfind':
            await self._execute_pathfind_ability(player_id, character, ability, params)
        elif ability_id == 'forage':
            await self._execute_forage_ability(player_id, character, ability)
        elif ability_id == 'camouflage':
            await self._execute_camouflage_ability(player_id, character, ability)
        elif ability_id == 'multishot':
            await self._execute_multishot_ability(player_id, character, ability)
        elif ability_id == 'call_of_the_wild':
            await self._execute_call_wild_ability(player_id, character, ability)
        else:
            # Generic ability execution
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You use {ability_name}!")
            )

    async def _execute_picklock_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the picklock ability."""
        # TODO: Implement picklock logic
        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message("You attempt to pick the lock... (Not yet implemented)")
        )

    async def _execute_backstab_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the backstab ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Backstab what? Usage: backstab <target>")
            )
            return

        # Check if in combat
        room_id = character.get('room_id')
        if room_id in self.game_engine.combat_system.active_combats:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You can't backstab while in active combat!")
            )
            return

        # Apply backstab buff for next attack
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        character['active_abilities']['backstab'] = {
            'damage_multiplier': ability['effect']['value'],
            'attacks_remaining': 1
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You prepare a devastating backstab attack!")
        )

        # Now attack the target
        await self._handle_attack_command(player_id, params)

    async def _execute_shadow_step_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the shadow step (stealth) ability."""
        # Apply stealth effect
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        import time
        duration = ability['effect']['duration']
        character['active_abilities']['shadow_step'] = {
            'end_time': time.time() + duration,
            'dodge_bonus': ability['effect']['dodge_bonus']
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You melt into the shadows! (+{int(ability['effect']['dodge_bonus']*100)}% dodge for {duration}s)")
        )

    async def _execute_poison_blade_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the poison blade ability."""
        # Check for poison vial
        inventory = character.get('inventory', [])
        poison_vial = None
        for item in inventory:
            if item.get('id') == 'poison_vial':
                poison_vial = item
                break

        if not poison_vial:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have a poison vial!")
            )
            return

        # Remove poison vial
        inventory.remove(poison_vial)

        # Apply poison effect for next 3 attacks
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        character['active_abilities']['poison_blade'] = {
            'charges': ability['effect']['charges'],
            'damage': ability['effect']['damage'],
            'duration': ability['effect']['duration'],
            'tick_rate': ability['effect']['tick_rate']
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You coat your weapon with deadly poison! (Next {ability['effect']['charges']} attacks)")
        )

    # Fighter Ability Handlers

    async def _execute_power_attack_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the power attack ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Power attack what? Usage: powerattack <target>")
            )
            return

        # Apply power attack buff for next attack
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        character['active_abilities']['power_attack'] = {
            'damage_multiplier': ability['effect']['value'],
            'hit_penalty': ability['effect']['hit_penalty'],
            'attacks_remaining': 1
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You wind up for a devastating power attack!")
        )

        # Now attack the target
        await self._handle_attack_command(player_id, params)

    async def _execute_cleave_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the cleave ability (AoE attack)."""
        room_id = character.get('room_id')
        if not room_id:
            return

        # Get all mobs in the room
        mobs = self.game_engine.room_mobs.get(room_id, [])
        if not mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("There are no enemies to cleave!")
            )
            return

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You swing your weapon in a wide arc, attacking all enemies!")
        )

        # Attack each mob with reduced damage
        damage_mult = ability['effect']['damage_multiplier']
        for mob in mobs[:]:  # Copy list since we might remove mobs
            # Apply cleave buff temporarily
            if 'active_abilities' not in character:
                character['active_abilities'] = {}

            character['active_abilities']['cleave'] = {
                'damage_multiplier': damage_mult,
                'attacks_remaining': 1
            }

            # Attack this mob
            mob_name = mob.get('name', 'creature')
            await self._handle_attack_command(player_id, mob_name)

    async def _execute_dual_wield_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the dual wield toggle ability."""
        # Check if already dual wielding
        current_mode = character.get('dual_wield_mode', False)

        if current_mode:
            # Turn off dual wield
            character['dual_wield_mode'] = False
            await self.game_engine.connection_manager.send_message(
                player_id,
                info_message("You return to single weapon fighting.")
            )
        else:
            # Check if has two weapons equipped
            equipped = character.get('equipped', {})
            main_weapon = equipped.get('weapon')
            off_weapon = equipped.get('off_hand_weapon')

            if not main_weapon:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("You need a weapon equipped to dual wield!")
                )
                return

            # For now, just enable the mode (off-hand weapon can be added later)
            character['dual_wield_mode'] = True
            character['dual_wield_config'] = {
                'main_hand_mult': ability['effect']['main_hand_mult'],
                'off_hand_mult': ability['effect']['off_hand_mult']
            }
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You ready yourself to fight with both hands! (Main: {int(ability['effect']['main_hand_mult']*100)}%, Off: {int(ability['effect']['off_hand_mult']*100)}%)")
            )

    async def _execute_shield_bash_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the shield bash ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Shield bash what? Usage: shieldbash <target>")
            )
            return

        # Check for shield
        equipped = character.get('equipped', {})
        shield = equipped.get('shield')
        if not shield:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have a shield equipped!")
            )
            return

        # Apply shield bash effect
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        character['active_abilities']['shield_bash'] = {
            'damage': ability['effect']['damage'],
            'stun_duration': ability['effect']['stun_duration'],
            'attacks_remaining': 1
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You slam your shield forward!")
        )

        # Attack the target
        await self._handle_attack_command(player_id, params)

    async def _execute_battle_cry_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the battle cry buff ability."""
        # Apply battle cry buff
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        import time
        duration = ability['effect']['duration']
        character['active_abilities']['battle_cry'] = {
            'end_time': time.time() + duration,
            'damage_bonus': ability['effect']['damage_bonus']
        }

        room_id = character.get('room_id')
        username = self.game_engine.player_manager.get_player_data(player_id).get('username', 'Someone')

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You release a mighty battle cry! (+{int(ability['effect']['damage_bonus']*100)}% damage for {duration}s)")
        )

        # Broadcast to room
        await self.game_engine._notify_room_except_player(
            room_id,
            player_id,
            announcement(f"{username} releases a mighty battle cry!")
        )

    # Ranger Ability Handlers

    async def _execute_track_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the track ability."""
        room_id = character.get('room_id')
        if not room_id:
            return

        tracking_range = ability['effect']['range']
        tracked_mobs = []

        # Get current room
        current_room = self.game_engine.world_manager.rooms.get(room_id)
        if not current_room:
            return

        # Check current room
        mobs_here = self.game_engine.room_mobs.get(room_id, [])
        if mobs_here:
            tracked_mobs.append((room_id, "here", mobs_here))

        # Check adjacent rooms within range using BFS
        visited = {room_id}
        queue = [(room_id, 0)]  # (room_id, distance)

        while queue:
            current, distance = queue.pop(0)
            if distance >= tracking_range:
                continue

            room = self.game_engine.world_manager.rooms.get(current)
            if not room:
                continue

            # Check each exit
            for direction, exit_data in room.exits.items():
                next_room_id = exit_data.get('to_room') if isinstance(exit_data, dict) else exit_data
                if next_room_id and next_room_id not in visited:
                    visited.add(next_room_id)
                    queue.append((next_room_id, distance + 1))

                    # Check for mobs in this room
                    mobs_there = self.game_engine.room_mobs.get(next_room_id, [])
                    if mobs_there:
                        tracked_mobs.append((next_room_id, direction, mobs_there))

        if not tracked_mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                info_message("You find no tracks of creatures nearby.")
            )
            return

        # Build tracking report
        report = info_message("You find tracks of the following creatures:\n")
        for room_loc, direction, mobs in tracked_mobs:
            for mob in mobs:
                mob_name = mob.get('name', 'creature')
                mob_level = mob.get('level', 1)
                if direction == "here":
                    report += f"  - {mob_name} (level {mob_level}) is in this room\n"
                else:
                    report += f"  - {mob_name} (level {mob_level}) tracks lead {direction}\n"

        await self.game_engine.connection_manager.send_message(player_id, report)

    async def _execute_tame_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the tame ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Tame what? Usage: tame <creature>")
            )
            return

        # TODO: Implement full taming system
        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message(f"You attempt to tame {params}... (Full taming system not yet implemented)")
        )

    async def _execute_pathfind_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the pathfind ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Pathfind to where? Usage: pathfind <room_id>")
            )
            return

        room_id = character.get('room_id')
        target_room = params.strip()

        # Check if target room exists
        if target_room not in self.game_engine.world_manager.rooms:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"Unknown location: {target_room}")
            )
            return

        # Find path using world graph
        path = self.game_engine.world_manager.world_graph.find_path(room_id, target_room)

        if not path:
            await self.game_engine.connection_manager.send_message(
                player_id,
                info_message(f"You can't find a path to {target_room}.")
            )
            return

        # Convert path to directions
        directions = []
        for i in range(len(path) - 1):
            current = path[i]
            next_room = path[i + 1]
            room = self.game_engine.world_manager.rooms.get(current)
            if room:
                for direction, exit_data in room.exits.items():
                    exit_room = exit_data.get('to_room') if isinstance(exit_data, dict) else exit_data
                    if exit_room == next_room:
                        directions.append(direction)
                        break

        path_str = " -> ".join(directions)
        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"Path to {target_room}: {path_str} ({len(directions)} rooms)")
        )

    async def _execute_forage_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the forage ability."""
        import random

        success_chance = ability['effect']['success_chance']
        if random.random() > success_chance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                info_message("You search the area but find nothing useful.")
            )
            return

        # Generate a random item
        forage_items = [
            {'id': 'bread', 'name': 'Bread'},
            {'id': 'apple', 'name': 'Apple'},
            {'id': 'berries', 'name': 'Berries'},
            {'id': 'healing_herb', 'name': 'Healing Herb'},
        ]

        item = random.choice(forage_items)

        # Add to inventory
        inventory = character.get('inventory', [])
        inventory.append(item)

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You forage and find: {item['name']}")
        )

    async def _execute_camouflage_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the camouflage ability."""
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        import time
        duration = ability['effect']['duration']
        character['active_abilities']['camouflage'] = {
            'end_time': time.time() + duration,
            'breaks_on_attack': ability['effect']['breaks_on_attack']
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You blend into your surroundings! (Hidden for {duration}s)")
        )

    async def _execute_multishot_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the multishot ability."""
        room_id = character.get('room_id')
        if not room_id:
            return

        # Get all mobs in the room
        mobs = self.game_engine.room_mobs.get(room_id, [])
        if not mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("There are no enemies to shoot!")
            )
            return

        max_targets = ability['effect']['max_targets']
        targets = mobs[:max_targets]  # Take up to 3 targets

        # Check ammo
        ammo_cost = ability['effect']['ammo_cost']
        equipped_weapon = character.get('equipped', {}).get('weapon')
        if not equipped_weapon or not equipped_weapon.get('properties', {}).get('ranged'):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You need a ranged weapon equipped!")
            )
            return

        # Check for ammunition (simplified - just check inventory)
        # Full implementation would check specific ammo types

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You fire multiple arrows at {len(targets)} targets!")
        )

        # Shoot each target with reduced damage
        damage_mult = ability['effect']['damage_multiplier']
        for mob in targets:
            # Apply multishot buff
            if 'active_abilities' not in character:
                character['active_abilities'] = {}

            character['active_abilities']['multishot'] = {
                'damage_multiplier': damage_mult,
                'attacks_remaining': 1
            }

            # Shoot this mob
            mob_name = mob.get('name', 'creature')
            await self.game_engine.combat_system.handle_shoot_command(player_id, mob_name)

    async def _execute_call_wild_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the call of the wild (summon pet) ability."""
        # TODO: Implement full pet/companion system
        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message("You call out to the wild! A spirit wolf appears at your side...")
        )
        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message("(Full pet/companion system not yet implemented)")
        )

    # ==================== ADMIN STAT COMMANDS ====================

    async def _handle_admin_set_stat(self, player_id: int, character: dict, params: str):
        """Admin command to set a character stat.

        Usage: setstat <stat_name> <value>
        Stats: strength, dexterity, constitution, vitality, intellect, wisdom, charisma
        """
        parts = params.strip().split()
        if len(parts) != 2:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: setstat <stat_name> <value>\nStats: strength, dexterity, constitution, vitality, intellect, wisdom, charisma"
            )
            return

        stat_name = parts[0].lower()
        try:
            value = int(parts[1])
        except ValueError:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Error: Value must be a number"
            )
            return

        # Map stat names to character keys
        stat_map = {
            'str': 'strength',
            'strength': 'strength',
            'dex': 'dexterity',
            'dexterity': 'dexterity',
            'con': 'constitution',
            'constitution': 'constitution',
            'vit': 'vitality',
            'vitality': 'vitality',
            'int': 'intellect',
            'intellect': 'intellect',
            'intelligence': 'intellect',
            'wis': 'wisdom',
            'wisdom': 'wisdom',
            'cha': 'charisma',
            'charisma': 'charisma'
        }

        stat_key = stat_map.get(stat_name)
        if not stat_key:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Error: Unknown stat '{stat_name}'\nValid stats: strength, dexterity, constitution, vitality, intellect, wisdom, charisma"
            )
            return

        # Clamp value between 1 and 99
        value = max(1, min(99, value))

        old_value = character.get(stat_key, 10)
        character[stat_key] = value

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] {stat_key.capitalize()} set: {old_value} -> {value}"
        )

    async def _handle_admin_set_level(self, player_id: int, character: dict, params: str):
        """Admin command to set character level.

        Usage: setlevel <level>
        """
        try:
            level = int(params.strip())
        except ValueError:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Error: Level must be a number"
            )
            return

        # Clamp level between 1 and 50
        level = max(1, min(50, level))

        old_level = character.get('level', 1)
        character['level'] = level

        # Update max HP and mana based on new level
        # Base HP: 100 + (level * 10)
        # Base Mana: 50 + (level * 5)
        max_hp = 100 + (level * 10)
        max_mana = 50 + (level * 5)

        character['max_hit_points'] = max_hp
        character['max_mana'] = max_mana
        character['current_hit_points'] = max_hp
        character['current_mana'] = max_mana

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Level set: {old_level} -> {level}\nMax HP: {max_hp}, Max Mana: {max_mana}\nHealth and mana restored to full."
        )

    async def _handle_admin_set_mana(self, player_id: int, character: dict, params: str):
        """Admin command to set character mana.

        Usage: setmana <current> [max] OR setmana full
        """
        parts = params.strip().split()

        if parts[0].lower() == 'full':
            max_mana = character.get('max_mana', 50)
            character['current_mana'] = max_mana
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Mana restored to full: {max_mana}"
            )
            return

        try:
            current = int(parts[0])
        except (ValueError, IndexError):
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: setmana <current> [max] OR setmana full"
            )
            return

        # If max value provided, set it
        if len(parts) > 1:
            try:
                max_mana = int(parts[1])
                character['max_mana'] = max(1, max_mana)
            except ValueError:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "[ADMIN] Error: Max mana must be a number"
                )
                return

        character['current_mana'] = max(0, current)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Mana set: {character['current_mana']} / {character.get('max_mana', 50)}"
        )

    async def _handle_admin_set_health(self, player_id: int, character: dict, params: str):
        """Admin command to set character health.

        Usage: sethealth <current> [max] OR sethealth full
        """
        parts = params.strip().split()

        if parts[0].lower() == 'full':
            max_hp = character.get('max_hit_points', 100)
            character['current_hit_points'] = max_hp
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Health restored to full: {max_hp}"
            )
            return

        try:
            current = int(parts[0])
        except (ValueError, IndexError):
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: sethealth <current> [max] OR sethealth full"
            )
            return

        # If max value provided, set it
        if len(parts) > 1:
            try:
                max_hp = int(parts[1])
                character['max_hit_points'] = max(1, max_hp)
            except ValueError:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "[ADMIN] Error: Max health must be a number"
                )
                return

        character['current_hit_points'] = max(1, current)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Health set: {character['current_hit_points']} / {character.get('max_hit_points', 100)}"
        )

    async def _handle_admin_god_mode(self, player_id: int, character: dict):
        """Admin command to toggle god mode (invincibility + max stats).

        Usage: godmode OR god
        """
        # Toggle god mode flag
        current_god_mode = character.get('god_mode', False)
        character['god_mode'] = not current_god_mode

        if character['god_mode']:
            # Enable god mode - set all stats to 99
            character['strength'] = 99
            character['dexterity'] = 99
            character['constitution'] = 99
            character['vitality'] = 99
            character['intellect'] = 99
            character['wisdom'] = 99
            character['charisma'] = 99

            # Set level to 50
            character['level'] = 50
            character['max_hit_points'] = 9999
            character['max_mana'] = 9999
            character['current_hit_points'] = 9999
            character['current_mana'] = 9999

            # Give lots of gold
            character['gold'] = character.get('gold', 0) + 100000

            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] GOD MODE ENABLED!\nAll stats set to 99, Level 50, HP/Mana 9999, +100,000 gold"
            )
        else:
            # Disable god mode
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] God mode disabled. Use 'setstat' and 'setlevel' to adjust stats manually."
            )

    async def _handle_admin_condition_command(self, player_id: int, character: dict, params: str):
        """Admin command to apply various conditions to the player for testing.

        Usage: condition <type>
        Types: poison, hungry, thirsty, paralyzed
        """
        condition = params.strip().lower()

        if condition == 'poison':
            # Add poison effect
            if 'poison_effects' not in character:
                character['poison_effects'] = []

            character['poison_effects'].append({
                'duration': 10,
                'damage': '2d3',
                'caster_id': player_id,
                'spell_name': 'Admin Poison'
            })
            message = "[ADMIN] You have been poisoned! (10 ticks, 2d3 damage per tick)"

        elif condition == 'hungry':
            character['hunger'] = 10
            message = "[ADMIN] You are now very hungry! (Hunger set to 10)"

        elif condition == 'thirsty':
            character['thirst'] = 10
            message = "[ADMIN] You are now very thirsty! (Thirst set to 10)"

        elif condition == 'paralyzed':
            # Add paralysis effect to active_effects
            if 'active_effects' not in character:
                character['active_effects'] = []

            character['active_effects'].append({
                'type': 'paralyzed',
                'duration': 5,
                'effect': 'movement_disabled',
                'effect_amount': 0
            })
            message = "[ADMIN] You have been paralyzed! (5 ticks, movement disabled)"

        elif condition == 'starving':
            character['hunger'] = 0
            message = "[ADMIN] You are now starving! (Hunger set to 0, will take damage)"

        elif condition == 'dehydrated':
            character['thirst'] = 0
            message = "[ADMIN] You are now dehydrated! (Thirst set to 0, will take damage)"

        else:
            message = f"[ADMIN] Unknown condition: {condition}\nValid types: poison, hungry, thirsty, paralyzed, starving, dehydrated"

        await self.game_engine.connection_manager.send_message(player_id, message)

