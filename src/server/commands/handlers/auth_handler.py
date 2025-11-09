"""
Authentication and Character Creation Command Handler

Handles commands for player authentication and character creation:
- Login process (username/password prompts)
- Character selection/loading
- Character creation flow (race and class selection)
- Character migration for legacy data
"""

import random
from ..base_handler import BaseCommandHandler
from ...utils.colors import error_message
from ...game.player.stats_utils import get_stamina_hp_bonus


class AuthCommandHandler(BaseCommandHandler):
    """Handler for authentication and character creation commands."""

    async def handle_login_process(self, player_id: int, input_text: str, _params: str):
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
                # (welcome message will be sent in handle_character_selection)
                await self.handle_character_selection(player_id, username)
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("Invalid credentials. Try again.")
                )
                await self.game_engine.connection_manager.send_message(player_id, "\nUsername: ", add_newline=False)
                player_data['login_state'] = 'username_prompt'

    def migrate_character_data(self, character: dict):
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

    async def handle_character_selection(self, player_id: int, username: str):
        """Handle character selection/creation."""
        # Try to load existing character data first
        if self.game_engine.player_storage:
            print(f"[DEBUG] Attempting to load character for '{username}'")
            existing_character = self.game_engine.player_storage.load_character_data(username)
            if existing_character:
                # Migrate old character data to new format
                self.migrate_character_data(existing_character)

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

        await self.show_race_selection(player_id)
        return

    async def show_race_selection(self, player_id: int):
        """Show race selection menu."""
        races = self.load_races()
        message = "\n=== Choose Your Race ===\n\n"
        for i, (race_id, race_data) in enumerate(races.items(), 1):
            message += f"{i}. {race_data['name']}\n   {race_data['description']}\n\n"
        message += "Enter the number of your choice: "
        await self.game_engine.connection_manager.send_message(player_id, message, add_newline=False)

    async def show_class_selection(self, player_id: int):
        """Show class selection menu."""
        classes = self.load_classes()
        message = "\n=== Choose Your Class ===\n\n"
        for i, (class_id, class_data) in enumerate(classes.items(), 1):
            message += f"{i}. {class_data['name']}\n   {class_data['description']}\n\n"
        message += "Enter the number of your choice: "
        await self.game_engine.connection_manager.send_message(player_id, message, add_newline=False)

    def load_races(self):
        """Load race definitions from JSON."""
        import json
        import os
        try:
            with open('data/player/races.json', 'r') as f:
                return json.load(f)
        except:
            # Fallback to default
            return {"human": {"name": "Human", "description": "Versatile humans", "base_stats": {"strength": 10, "dexterity": 10, "constitution": 10, "intellect": 10, "wisdom": 10, "charisma": 10}}}

    def load_classes(self):
        """Load class definitions from JSON."""
        import json
        import os
        try:
            with open('data/player/classes.json', 'r') as f:
                return json.load(f)
        except:
            # Fallback to default
            return {"fighter": {"name": "Fighter", "description": "Martial warrior", "stat_modifiers": {}, "hp_modifier": 1.0, "mana_modifier": 1.0}}

    async def handle_character_creation_input(self, player_id: int, user_input: str):
        """Handle input during character creation."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        step = player_data.get('char_creation_step')

        if step == 'race':
            races = self.load_races()
            race_list = list(races.keys())
            try:
                choice = int(user_input) - 1
                if 0 <= choice < len(race_list):
                    player_data['selected_race'] = race_list[choice]
                    player_data['char_creation_step'] = 'class'
                    await self.show_class_selection(player_id)
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message("Invalid choice. Try again.")
                    )
                    await self.show_race_selection(player_id)
            except ValueError:
                await self.game_engine.connection_manager.send_message(player_id, "Please enter a number.")
                await self.show_race_selection(player_id)

        elif step == 'class':
            classes = self.load_classes()
            class_list = list(classes.keys())
            try:
                choice = int(user_input) - 1
                if 0 <= choice < len(class_list):
                    player_data['selected_class'] = class_list[choice]
                    await self.create_character_with_selection(player_id)
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message("Invalid choice. Try again.")
                    )
                    await self.show_class_selection(player_id)
            except ValueError:
                await self.game_engine.connection_manager.send_message(player_id, "Please enter a number.")
                await self.show_class_selection(player_id)

    async def create_character_with_selection(self, player_id: int):
        """Create character with selected race and class."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        username = player_data.get('username')
        selected_race = player_data.get('selected_race', 'human')
        selected_class = player_data.get('selected_class', 'fighter')

        # Clear creation flags IMMEDIATELY to prevent race conditions
        player_data['creating_character'] = False
        player_data['char_creation_step'] = None

        races = self.load_races()
        classes = self.load_classes()
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
        stamina_hp_bonus = get_stamina_hp_bonus(constitution)

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
