"""Combat system that manages all combat-related functionality."""

import time
import random
import asyncio
from typing import Optional, Dict, Any


class CombatSystem:
    """Manages all combat functionality including fatigue, attacks, and combat encounters."""

    def __init__(self, game_engine):
        """Initialize the combat system.

        Args:
            game_engine: Reference to the main game engine for accessing data and methods
        """
        self.game_engine = game_engine
        self.logger = game_engine.logger

        # Combat management - tracks active combat encounters
        self.active_combats: Dict[str, Any] = {}  # room_id -> AsyncCombat
        self.player_combats: Dict[int, str] = {}  # player_id -> room_id with active combat
        self.player_fatigue: Dict[int, Dict[str, Any]] = {}  # player_id -> fatigue info
        self.mob_fatigue: Dict[str, Dict[str, Any]] = {}  # mob_id -> fatigue info

    def is_player_fatigued(self, player_id: int) -> bool:
        """Check if a player is currently fatigued from combat."""
        if player_id not in self.player_fatigue:
            return False

        fatigue_info = self.player_fatigue[player_id]
        current_time = time.time()

        # Check if fatigue data is complete
        if 'fatigue_end_time' not in fatigue_info:
            # Invalid fatigue data, clean up
            del self.player_fatigue[player_id]
            return False

        # If fatigue_end_time is 0, player is not fatigued (just tracking attacks)
        if fatigue_info['fatigue_end_time'] == 0:
            return False

        # Check if fatigue has expired
        if current_time >= fatigue_info['fatigue_end_time']:
            # Fatigue expired, clean up
            del self.player_fatigue[player_id]
            return False

        return True

    def get_player_fatigue_remaining(self, player_id: int) -> float:
        """Get remaining fatigue time for a player in seconds."""
        if player_id not in self.player_fatigue:
            return 0.0

        fatigue_info = self.player_fatigue[player_id]

        # Check if fatigue data is complete
        if 'fatigue_end_time' not in fatigue_info:
            return 0.0

        current_time = time.time()
        remaining = fatigue_info['fatigue_end_time'] - current_time
        return max(0.0, remaining)

    def set_player_fatigue(self, player_id: int, duration: float = 15.0):
        """Set a player as fatigued for the specified duration."""
        self.player_fatigue[player_id] = {
            'fatigue_end_time': time.time() + duration,
            'attacks_remaining': 0
        }

    def get_player_attacks_remaining(self, player_id: int) -> int:
        """Get number of attacks remaining for a player."""
        if player_id not in self.player_fatigue:
            # Player not in combat or not fatigued, calculate max attacks
            player_data = self.game_engine.player_manager.connected_players.get(player_id)
            if player_data and player_data.get('character'):
                level = player_data['character'].get('level', 1)
                return 2 + (level - 1) // 5  # 2 at level 1, +1 every 5 levels
            return 2  # Default

        return self.player_fatigue[player_id].get('attacks_remaining', 0)

    def use_player_attack(self, player_id: int) -> bool:
        """Use one of the player's attacks. Returns True if attack was used successfully."""
        if self.is_player_fatigued(player_id):
            return False

        # Get current attacks remaining
        attacks_remaining = self.get_player_attacks_remaining(player_id)
        if attacks_remaining <= 0:
            return False

        # Use one attack
        attacks_remaining -= 1

        # Always ensure player is tracked in fatigue system
        if attacks_remaining <= 0:
            # Player is now fatigued
            self.set_player_fatigue(player_id)
        else:
            # Update attacks remaining (ensure player is tracked from first attack)
            self.player_fatigue[player_id] = {
                'fatigue_end_time': 0,
                'attacks_remaining': attacks_remaining
            }

        return True

    def is_mob_fatigued(self, mob_id: str) -> bool:
        """Check if a mob is currently fatigued from combat."""
        if mob_id not in self.mob_fatigue:
            return False

        fatigue_info = self.mob_fatigue[mob_id]
        current_time = time.time()

        # If fatigue_end_time is 0, mob is not fatigued (just tracking attacks)
        if fatigue_info['fatigue_end_time'] == 0:
            return False

        # Check if fatigue has expired
        if current_time >= fatigue_info['fatigue_end_time']:
            # Fatigue expired, clean up
            del self.mob_fatigue[mob_id]
            return False

        return True

    def get_mob_fatigue_remaining(self, mob_id: str) -> float:
        """Get remaining fatigue time for a mob in seconds."""
        if mob_id not in self.mob_fatigue:
            return 0.0

        fatigue_info = self.mob_fatigue[mob_id]
        current_time = time.time()
        remaining = fatigue_info['fatigue_end_time'] - current_time
        return max(0.0, remaining)

    def set_mob_fatigue(self, mob_id: str, duration: float = 15.0):
        """Set a mob as fatigued for the specified duration."""
        self.mob_fatigue[mob_id] = {
            'fatigue_end_time': time.time() + duration,
            'attacks_remaining': 0
        }

    def get_mob_attacks_remaining(self, mob_id: str, level: int = 1) -> int:
        """Get number of attacks remaining for a mob."""
        if mob_id not in self.mob_fatigue:
            # Mob not in combat or not fatigued, calculate max attacks
            return 2 + (level - 1) // 5  # 2 at level 1, +1 every 5 levels

        return self.mob_fatigue[mob_id].get('attacks_remaining', 0)

    def use_mob_attack(self, mob_id: str, level: int = 1) -> bool:
        """Use one of the mob's attacks. Returns True if attack was used successfully."""
        if self.is_mob_fatigued(mob_id):
            return False

        # Get current attacks remaining
        attacks_remaining = self.get_mob_attacks_remaining(mob_id, level)
        if attacks_remaining <= 0:
            return False

        # Use one attack
        attacks_remaining -= 1

        # Always ensure mob is tracked in fatigue system from first attack
        if attacks_remaining <= 0:
            # Mob is now fatigued
            self.set_mob_fatigue(mob_id)
        else:
            # Update attacks remaining (ensure mob is tracked from first attack)
            self.mob_fatigue[mob_id] = {
                'fatigue_end_time': 0,
                'attacks_remaining': attacks_remaining
            }

        return True

    def check_npc_hostility(self, npc_id: str) -> bool:
        """Check if an NPC is hostile using preloaded world manager data."""
        return self.game_engine.world_manager.is_npc_hostile(npc_id)

    async def handle_attack_command(self, player_id: int, target_name: str):
        """Handle player attack command using seamless combat system."""
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data:
            return

        character = player_data['character']
        room_id = character['room_id']

        # Check if player is fatigued
        if self.is_player_fatigued(player_id):
            fatigue_time = self.get_player_fatigue_remaining(player_id)
            await self.game_engine.connection_manager.send_message(player_id,
                f"You are too exhausted to attack! Wait {fatigue_time:.1f} more seconds.")
            return

        # Check if player has attacks remaining
        attacks_remaining = self.get_player_attacks_remaining(player_id)
        if attacks_remaining <= 0:
            await self.game_engine.connection_manager.send_message(player_id, "You have no attacks remaining!")
            return

        # Find target
        target = await self.find_combat_target(room_id, target_name)
        if not target:
            await self.game_engine.connection_manager.send_message(player_id, f"You don't see '{target_name}' here.")
            return

        # Check if target is hostile
        if hasattr(target, 'friendly') and target.friendly:
            await self.game_engine.connection_manager.send_message(player_id, f"You cannot attack {getattr(target, 'name', target_name)}!")
            return

        # Execute the attack directly (no combat mode)
        await self.execute_seamless_attack(player_id, target, room_id)

    async def handle_flee_command(self, player_id: int):
        """Handle player flee command - no longer needed in seamless combat."""
        await self.game_engine.connection_manager.send_message(player_id, "There is no combat mode to flee from. You can simply walk away if you're not fatigued.")

    async def find_combat_target(self, room_id: str, target_name: str):
        """Find a valid combat target in the room."""
        # Check spawned mobs first
        room_mobs = self.game_engine.room_mobs.get(room_id, [])
        for mob in room_mobs:
            mob_name = mob.get('name', '')
            if self.game_engine.world_manager._matches_target(target_name.lower(), mob_name.lower()):
                return mob

        # Could also check for other players here if PvP is enabled
        return None

    async def start_async_combat(self, room_id: str, player_id: int, target):
        """Start a new async combat encounter."""
        from .combat_system import AsyncCombat

        # Create new async combat instance
        combat = AsyncCombat()

        # Add player character to combat
        player_data = self.game_engine.player_manager.connected_players[player_id]
        character = player_data['character']

        # Convert character dict to object-like structure for combat
        class CharacterAdapter:
            def __init__(self, char_data):
                self.name = char_data['name']
                self.level = char_data.get('level', 1)
                self.health = char_data.get('current_hit_points', 100)
                self.max_health = char_data.get('max_hit_points', 100)
                self.strength = char_data.get('strength', 10)
                self.dexterity = char_data.get('dexterity', 10)
                self.constitution = char_data.get('constitution', 10)
                self.intelligence = char_data.get('intellect', 10)  # Note: using 'intellect' from character data
                self.wisdom = char_data.get('wisdom', 10)
                self.charisma = char_data.get('charisma', 10)
                self._char_data = char_data

            def take_damage(self, amount):
                self.health = max(0, self.health - amount)
                self._char_data['current_hit_points'] = self.health

            def is_alive(self):
                return self.health > 0

            def gain_experience(self, amount):
                self._char_data['experience'] = self._char_data.get('experience', 0) + amount

        char_adapter = CharacterAdapter(character)

        # Convert mob dict to mob-like object for combat
        class MobAdapter:
            def __init__(self, mob_data):
                self.name = mob_data.get('name', 'Unknown')
                self.level = mob_data.get('level', 1)
                self.health = mob_data.get('health', 100)
                self.max_health = mob_data.get('max_health', 100)
                self.strength = 12
                self.dexterity = 10
                self.constitution = 12
                self.intelligence = 8
                self.wisdom = 10
                self.charisma = 6
                self._mob_data = mob_data

            def take_damage(self, amount):
                self.health = max(0, self.health - amount)
                self._mob_data['health'] = self.health

            def is_alive(self):
                return self.health > 0

        mob_adapter = MobAdapter(target)

        # Add participants to combat
        combat.add_participant(char_adapter, str(player_id))
        combat.add_participant(mob_adapter, f"mob_{target.get('id', 'unknown')}")
        combat.start_combat()

        # Track combat
        self.active_combats[room_id] = combat
        self.player_combats[player_id] = room_id

        # Announce combat start
        target_name = target.get('name', 'the target')
        await self.game_engine.connection_manager.send_message(player_id, f"You attack {target_name}!")
        await self.broadcast_to_room(room_id, f"{character['name']} attacks {target_name}!", exclude_player=player_id)

    async def execute_async_attack(self, player_id: int, target_name: str):
        """Execute an async attack for a player."""
        combat_room = self.player_combats.get(player_id)
        if not combat_room:
            return

        combat = self.active_combats.get(combat_room)
        if not combat or not combat.is_active:
            return

        # Find target participant ID
        target_id = None
        if target_name:
            for participant_id, participant in combat.participants.items():
                if hasattr(participant.entity, 'name') and self.game_engine.world_manager._matches_target(target_name.lower(), participant.entity.name.lower()):
                    target_id = participant_id
                    break
                elif hasattr(participant.entity, '_mob_data'):
                    mob_name = participant.entity._mob_data.get('name', '')
                    if self.game_engine.world_manager._matches_target(target_name.lower(), mob_name.lower()):
                        target_id = participant_id
                        break

        if not target_id:
            await self.game_engine.connection_manager.send_message(player_id, f"You don't see '{target_name}' in combat.")
            return

        # Execute attack using async combat system
        result = combat.execute_attack(str(player_id), target_id)

        # Send result to player
        message = result.get('message', 'Attack completed.')
        await self.game_engine.connection_manager.send_message(player_id, message)

        # Add fatigue message if present
        fatigue_msg = result.get('fatigue_message', '')
        if fatigue_msg:
            await self.game_engine.connection_manager.send_message(player_id, fatigue_msg)

        # Show remaining attacks
        attacks_left = result.get('attacks_remaining', 0)
        if result.get('success') and attacks_left > 0:
            await self.game_engine.connection_manager.send_message(player_id, f"You have {attacks_left} attacks remaining.")

        # Broadcast to room (exclude the attacking player)
        if result.get('hit'):
            await self.broadcast_to_room(combat_room, message, exclude_player=player_id)

        # Check if target died
        if result.get('target_dead'):
            await self.handle_mob_death(combat_room, target_id)

        # Check if combat should end
        if combat.is_combat_over():
            await self.end_async_combat(combat_room)

    async def handle_mob_death(self, room_id: str, mob_participant_id: str):
        """Handle when a mob dies in combat."""
        # Remove dead mob from room
        if room_id in self.game_engine.room_mobs:
            # Find and remove the dead mob
            alive_mobs = []
            for mob in self.game_engine.room_mobs[room_id]:
                mob_id = f"mob_{mob.get('id', 'unknown')}"
                if mob_id != mob_participant_id:
                    alive_mobs.append(mob)
            self.game_engine.room_mobs[room_id] = alive_mobs

        # Award experience to players in combat
        for player_id, combat_room in self.player_combats.items():
            if combat_room == room_id:
                player_data = self.game_engine.player_manager.connected_players.get(player_id)
                if player_data and player_data.get('character'):
                    # Award 25 XP for killing the mob
                    player_data['character']['experience'] = player_data['character'].get('experience', 0) + 25
                    await self.game_engine.connection_manager.send_message(player_id, "You gain 25 experience points!")

    async def end_async_combat(self, room_id: str):
        """End async combat in a room."""
        combat = self.active_combats.get(room_id)
        if not combat:
            return

        # End the combat
        combat.end_combat()

        # Clean up combat tracking
        players_to_remove = []
        for player_id, combat_room in self.player_combats.items():
            if combat_room == room_id:
                players_to_remove.append(player_id)

        for player_id in players_to_remove:
            del self.player_combats[player_id]

        if room_id in self.active_combats:
            del self.active_combats[room_id]

        await self.broadcast_to_room(room_id, "Combat has ended.")

    async def process_mob_ai(self):
        """Process AI for all mobs in all rooms."""
        try:
            for room_id, mobs in self.game_engine.room_mobs.items():
                for mob in mobs.copy():  # Use copy to avoid modification during iteration
                    await self.process_single_mob_ai(mob, room_id)
        except Exception as e:
            self.logger.error(f"Error in mob AI processing: {e}")

    async def process_single_mob_ai(self, mob: dict, room_id: str):
        """Process AI for a single mob."""
        try:
            # Skip if mob is dead
            if mob.get('health', 0) <= 0:
                return

            # Skip if mob is fatigued
            mob_id = mob.get('id', f"{mob.get('name', 'unknown')}_{room_id}")
            if self.is_mob_fatigued(mob_id):
                return

            # Find players in the same room
            target_players = []
            for player_id, player_data in self.game_engine.player_manager.connected_players.items():
                if player_data.get('character', {}).get('room_id') == room_id:
                    target_players.append(player_id)

            # Attack a random player if any are present
            if target_players and mob.get('type') == 'hostile':
                target_player_id = random.choice(target_players)
                await self.execute_mob_attack(mob, mob_id, target_player_id, room_id)

        except Exception as e:
            self.logger.error(f"Error in single mob AI processing: {e}")

    async def execute_mob_attack(self, mob: dict, mob_id: str, target_player_id: int, room_id: str):
        """Execute a mob attack against a player."""
        try:
            # Use mob attack
            mob_level = mob.get('level', 1)
            if not self.use_mob_attack(mob_id, mob_level):
                return

            # Get target player data
            player_data = self.game_engine.player_manager.connected_players.get(target_player_id)
            if not player_data:
                return

            character = player_data['character']
            mob_name = mob.get('name', 'Unknown Mob')

            # Create temp entities for attack calculation
            class TempMob:
                def __init__(self, mob_data):
                    self.name = mob_data.get('name', 'Unknown')
                    self.level = mob_data.get('level', 1)
                    self.strength = mob_data.get('strength', 12)
                    self.dexterity = mob_data.get('dexterity', 10)
                    self.constitution = 12
                    self.intelligence = 8
                    self.wisdom = 10
                    self.charisma = 6

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

            temp_mob = TempMob(mob)
            temp_char = TempCharacter(character)

            # Import damage calculator
            from .damage_calculator import DamageCalculator

            # Get player's armor class
            player_armor = character.get('armor_class', 0)

            # Check attack outcome (miss/dodge/deflect/hit)
            outcome = DamageCalculator.check_attack_outcome(temp_mob, temp_char, player_armor)

            if outcome['result'] == 'miss':
                # Mob missed
                miss_msg = f"{mob_name} attacks you but misses!"
                await self.game_engine.connection_manager.send_message(target_player_id, miss_msg)

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{mob_name} attacks {character['name']} but misses!"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

            elif outcome['result'] == 'dodge':
                # Player dodged
                dodge_msg = f"You dodge {mob_name}'s attack!"
                await self.game_engine.connection_manager.send_message(target_player_id, dodge_msg)

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{character['name']} dodges {mob_name}'s attack!"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

            elif outcome['result'] == 'deflect':
                # Armor deflected
                deflect_msg = f"Your armor deflects {mob_name}'s attack!"
                await self.game_engine.connection_manager.send_message(target_player_id, deflect_msg)

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{character['name']}'s armor deflects {mob_name}'s attack!"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

            else:
                # Hit - calculate damage with mob's natural attack
                natural_attack = {
                    'damage': mob.get('damage'),
                    'damage_min': mob.get('damage_min', 1),
                    'damage_max': mob.get('damage_max', 4)
                }
                damage_info = DamageCalculator.calculate_melee_damage(temp_mob, natural_attack=natural_attack)
                damage = damage_info['damage']
                is_critical = damage_info['is_critical']

                # Apply damage
                current_health = character.get('health', character.get('constitution', 10) * 3)
                new_health = max(0, current_health - damage)
                character['health'] = new_health

                # Send attack message to target player
                attack_msg = f"{mob_name} attacks you for {damage} damage"
                if is_critical:
                    attack_msg += " (Critical Hit!)"
                attack_msg += f"! (Health: {new_health})"
                await self.game_engine.connection_manager.send_message(target_player_id, attack_msg)

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{mob_name} attacks {character['name']} for {damage} damage!"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

                # Check if player died
                if new_health <= 0:
                    death_msg = f"You have been killed by {mob_name}!"
                    await self.game_engine.connection_manager.send_message(target_player_id, death_msg)

                    # Respawn player (simple respawn logic)
                    character['health'] = character.get('constitution', 10) * 3
                    character['room_id'] = 'starting_room'  # Move to starting room

                    respawn_msg = "You have respawned in the starting room."
                    await self.game_engine.connection_manager.send_message(target_player_id, respawn_msg)

        except Exception as e:
            self.logger.error(f"Error in mob attack execution: {e}")

    async def execute_seamless_attack(self, player_id: int, target: dict, room_id: str):
        """Execute a seamless attack without combat mode."""
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data:
            return

        character = player_data['character']

        # Use an attack
        if not self.use_player_attack(player_id):
            await self.game_engine.connection_manager.send_message(player_id, "You cannot attack right now!")
            return

        # Create temporary entities for damage calculation
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
                self.health = mob_data.get('health', 100)
                self.max_health = mob_data.get('max_health', 100)
                self.strength = 12
                self.dexterity = 10
                self.constitution = 12
                self.intelligence = 8
                self.wisdom = 10
                self.charisma = 6

        temp_char = TempCharacter(character)
        temp_mob = TempMob(target)

        # Import damage calculator
        from .damage_calculator import DamageCalculator

        target_name = target.get('name', 'the target')
        attacks_remaining = self.get_player_attacks_remaining(player_id)
        is_fatigued = self.is_player_fatigued(player_id)

        # Mob armor class (could be from equipment or natural armor)
        mob_armor = target.get('armor_class', 0)

        # Check attack outcome (miss/dodge/deflect/hit)
        outcome = DamageCalculator.check_attack_outcome(temp_char, temp_mob, mob_armor)

        if outcome['result'] == 'miss':
            # Miss
            await self.game_engine.connection_manager.send_message(player_id, f"You miss {target_name}!")
            await self.broadcast_to_room(room_id, f"{character['name']} misses {target_name}!", exclude_player=player_id)
        elif outcome['result'] == 'dodge':
            # Dodged
            await self.game_engine.connection_manager.send_message(player_id, f"{target_name} dodges your attack!")
            await self.broadcast_to_room(room_id, f"{target_name} dodges {character['name']}'s attack!", exclude_player=player_id)
        elif outcome['result'] == 'deflect':
            # Deflected by armor
            await self.game_engine.connection_manager.send_message(player_id, f"Your attack is deflected by {target_name}'s armor!")
            await self.broadcast_to_room(room_id, f"{character['name']}'s attack is deflected by {target_name}'s armor!", exclude_player=player_id)
        else:
            # Hit - calculate damage with equipped weapon
            equipped_weapon = character.get('equipped', {}).get('weapon')
            damage_info = DamageCalculator.calculate_melee_damage(temp_char, equipped_weapon)
            damage = damage_info['damage']
            is_critical = damage_info['is_critical']

            # Apply damage to target
            target['health'] = max(0, target['health'] - damage)
            target_alive = target['health'] > 0

            # Build attack message
            hit_msg = f"You attack {target_name} for {damage} damage"
            if is_critical:
                hit_msg += " (Critical Hit!)"
            hit_msg += "!"

            await self.game_engine.connection_manager.send_message(player_id, hit_msg)
            await self.broadcast_to_room(room_id, f"{character['name']} attacks {target_name} for {damage} damage!", exclude_player=player_id)

            # Check if target died
            if not target_alive:
                await self.game_engine.connection_manager.send_message(player_id, f"{target_name} has been defeated!")
                await self.broadcast_to_room(room_id, f"{target_name} has been defeated!", exclude_player=player_id)

                # Award experience, gold, and loot
                await self.handle_mob_loot_drop(player_id, target, room_id)

                # Remove dead mob from room
                if room_id in self.game_engine.room_mobs:
                    self.game_engine.room_mobs[room_id] = [mob for mob in self.game_engine.room_mobs[room_id] if mob != target]

        # Show remaining attacks or fatigue status
        if is_fatigued:
            fatigue_time = self.get_player_fatigue_remaining(player_id)
            await self.game_engine.connection_manager.send_message(player_id, f"You are now fatigued for {fatigue_time:.1f} seconds.")
        elif attacks_remaining > 0:
            await self.game_engine.connection_manager.send_message(player_id, f"You have {attacks_remaining} attacks remaining.")

    async def broadcast_to_room(self, room_id: str, message: str, exclude_player: int = None):
        """Broadcast a message to all players in a room."""
        for player_id, player_data in self.game_engine.player_manager.connected_players.items():
            if player_id == exclude_player:
                continue

            character = player_data.get('character')
            if character and character.get('room_id') == room_id:
                await self.game_engine.connection_manager.send_message(player_id, message)

    async def handle_mob_loot_drop(self, player_id: int, mob: dict, room_id: str):
        """Handle experience, gold, and loot drops when a mob is defeated.

        Args:
            player_id: The player who defeated the mob
            mob: The mob dict with loot data
            room_id: The room where the mob was defeated
        """
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']

        # Award experience
        exp_reward = mob.get('experience_reward', 25)
        character['experience'] = character.get('experience', 0) + exp_reward
        await self.game_engine.connection_manager.send_message(player_id, f"You gain {exp_reward} experience points!")

        # Award gold
        gold_reward = mob.get('gold_reward', [0, 5])
        if isinstance(gold_reward, list) and len(gold_reward) == 2:
            gold_amount = random.randint(gold_reward[0], gold_reward[1])
        else:
            gold_amount = gold_reward if isinstance(gold_reward, int) else 0

        if gold_amount > 0:
            character['gold'] = character.get('gold', 0) + gold_amount
            await self.game_engine.connection_manager.send_message(player_id, f"You loot {gold_amount} gold!")

            # Update encumbrance for gold weight change
            self.game_engine.player_manager.update_encumbrance(character)

        # Process loot table
        loot_table = mob.get('loot_table', [])
        if loot_table:
            dropped_items = []
            for loot_entry in loot_table:
                item_id = loot_entry.get('item_id')
                drop_chance = loot_entry.get('chance', 0.0)

                # Roll for drop
                if random.random() < drop_chance:
                    # Get item data from world loader
                    item_data = self.game_engine.world_manager.items.get(item_id)
                    if item_data:
                        # Create a copy of the item to drop in the room
                        dropped_item = item_data.copy()
                        self.game_engine.item_manager.add_item_to_room(room_id, dropped_item)
                        dropped_items.append(dropped_item['name'])

            if dropped_items:
                if len(dropped_items) == 1:
                    await self.game_engine.connection_manager.send_message(
                        player_id, f"{mob.get('name', 'The mob')} dropped {dropped_items[0]}!")
                else:
                    items_str = ", ".join(dropped_items[:-1]) + f" and {dropped_items[-1]}"
                    await self.game_engine.connection_manager.send_message(
                        player_id, f"{mob.get('name', 'The mob')} dropped {items_str}!")