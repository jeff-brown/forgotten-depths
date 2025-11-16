"""Combat system that manages all combat-related functionality."""

import time
import random
import asyncio
from typing import Optional, Dict, Any
from ...utils.colors import (
    damage_to_player, damage_to_enemy, combat_action,
    error_message, announcement, death_message
)
from ..magic.spell_system import MobSpellcasting, SpellType


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

        # Damage tracking for XP calculation - maps mob ID to damage dealt by each player
        # Format: { mob_id: { player_id: damage_dealt, ... }, ... }
        self.mob_damage_tracking: Dict[str, Dict[int, int]] = {}

        # Spent ammunition tracking - arrows and bolts that can be retrieved
        # Format: { room_id: { ammo_type: quantity, ... }, ... }
        self.spent_ammo: Dict[str, Dict[str, int]] = {}

        # Spellcasting system for mobs
        self.spellcasting = MobSpellcasting(self)

        # Ability system for mobs
        # Tracks ability cooldowns: mob_id -> { ability_name: cooldown_end_time }
        self.mob_ability_cooldowns: Dict[str, Dict[str, float]] = {}

        # Loaded abilities for each mob: mob_id -> { ability_name: MobAbility instance }
        self.mob_abilities: Dict[str, Dict[str, Any]] = {}

    def get_critical_multiplier(self, character: dict) -> float:
        """Get the critical hit multiplier for a character, accounting for passive abilities.

        Args:
            character: Character data dictionary

        Returns:
            Critical multiplier (default 2.0, or enhanced by abilities)
        """
        base_multiplier = 2.0

        # Check for critical hit passive ability (e.g., Rogue's Skillful Attacks)
        ability_effect = self.game_engine.ability_system.check_passive_ability(
            character,
            'on_critical_hit',
            {}
        )

        if ability_effect and ability_effect.get('type') == 'damage_multiplier':
            # Ability provides a bonus multiplier (e.g., 1.5 means +50% to crit damage)
            bonus = ability_effect.get('value', 1.0)
            # Apply: 2x base becomes 3x (2 * 1.5)
            return base_multiplier * bonus

        return base_multiplier

    def load_mob_abilities(self, mob: dict, mob_id: str):
        """Load special abilities for a mob from its definition.

        Args:
            mob: The mob dictionary
            mob_id: Unique identifier for this mob instance
        """
        from ..abilities import AbilityRegistry

        # Get abilities from mob data
        abilities_data = mob.get('abilities', [])
        if not abilities_data:
            return

        # Initialize storage for this mob
        if mob_id not in self.mob_abilities:
            self.mob_abilities[mob_id] = {}

        # Create ability instances
        for ability_data in abilities_data:
            # Skip old-style string abilities (not yet converted to new format)
            if isinstance(ability_data, str):
                continue

            # Only process dictionary-style abilities
            if not isinstance(ability_data, dict):
                continue

            ability = AbilityRegistry.create_ability(ability_data)
            if ability:
                # Check if mob level is high enough
                mob_level = mob.get('level', 1)
                if ability.can_use(mob_level):
                    self.mob_abilities[mob_id][ability.name] = ability
                    self.logger.info(f"[ABILITY] Loaded ability '{ability.name}' for {mob.get('name')} (id: {mob_id})")
                else:
                    self.logger.debug(f"[ABILITY] Skipping ability '{ability.name}' for {mob.get('name')} - level {mob_level} < required {ability.min_level}")
            else:
                ability_type = ability_data.get('type', 'unknown')
                self.logger.warning(f"[ABILITY] Unknown ability type '{ability_type}' for {mob.get('name')}")

    def check_and_use_ability(self, mob: dict, mob_id: str, target: dict, room_id: str) -> Optional[Dict[str, Any]]:
        """Check if mob should use a special ability and execute it if so.

        Args:
            mob: The mob attempting to use an ability
            mob_id: Unique identifier for this mob
            target: The target (player or mob)
            room_id: Current room ID

        Returns:
            Ability result dict if ability was used, None otherwise
        """
        # Check if this mob has any abilities loaded
        if mob_id not in self.mob_abilities or not self.mob_abilities[mob_id]:
            return None

        current_time = time.time()

        # Check each ability to see if it can be used
        for ability_name, ability in self.mob_abilities[mob_id].items():
            # Check cooldown
            if mob_id in self.mob_ability_cooldowns:
                cooldown_end = self.mob_ability_cooldowns[mob_id].get(ability_name, 0)
                if current_time < cooldown_end:
                    continue  # Still on cooldown

            # Roll for use chance
            if random.random() > ability.use_chance:
                continue  # Didn't roll to use ability

            # Ability can be used! Set cooldown
            if mob_id not in self.mob_ability_cooldowns:
                self.mob_ability_cooldowns[mob_id] = {}
            self.mob_ability_cooldowns[mob_id][ability_name] = current_time + ability.cooldown

            # Execute the ability asynchronously
            return ability_name  # Return the name to execute

        return None

    async def execute_ability(self, ability_name: str, mob: dict, mob_id: str, target: dict, room_id: str):
        """Execute a mob's special ability.

        Args:
            ability_name: Name of the ability to execute
            mob: The mob using the ability
            mob_id: Unique identifier for this mob
            target: The target (player or mob)
            room_id: Current room ID
        """
        if mob_id not in self.mob_abilities or ability_name not in self.mob_abilities[mob_id]:
            return

        ability = self.mob_abilities[mob_id][ability_name]

        try:
            # Execute the ability
            result = await ability.execute(mob, target, self, room_id)

            if not result or not result.get('success'):
                return

            # Handle messages
            message = result.get('message')
            room_message = result.get('room_message')

            # Determine if target is a player and get their ID
            # Mobs have 'experience_reward' field, players don't
            target_is_player = 'experience_reward' not in target
            target_player_id = None

            self.logger.info(f"[ABILITY] message='{message}', room_message='{room_message}'")
            self.logger.info(f"[ABILITY] target_is_player={target_is_player}, target keys: {list(target.keys())}")

            if target_is_player:
                # For player targets, we need to find their player_id
                target_name = target.get('name')
                self.logger.info(f"[ABILITY] Looking for player with name '{target_name}'")
                for pid, pdata in self.game_engine.player_manager.connected_players.items():
                    char = pdata.get('character')
                    if char and char.get('name') == target_name:
                        target_player_id = pid
                        self.logger.info(f"[ABILITY] Found player_id {pid} for name '{target_name}'")
                        break

                if target_player_id is None:
                    self.logger.warning(f"[ABILITY] Could not find player_id for target '{target_name}'")

            # Send message to target if they're a player
            if message and target_is_player and target_player_id is not None:
                self.logger.info(f"[ABILITY] Sending message to player {target_player_id}: {message}")
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    damage_to_player(message)
                )

            # Send room message to others (excluding target player if applicable)
            if room_message:
                for player_id, player_data in self.game_engine.player_manager.connected_players.items():
                    if player_data.get('character', {}).get('room_id') == room_id:
                        # Skip the target player to avoid duplicate messages
                        if target_is_player and player_id == target_player_id:
                            continue
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            combat_action(room_message)
                        )

            # Log ability use
            mob_name = mob.get('name', 'Unknown creature')
            target_name = target.get('name', 'Unknown target')
            damage = result.get('damage', 0)
            self.logger.info(f"[ABILITY] {mob_name} used {ability_name} on {target_name} for {damage} damage")

        except Exception as e:
            self.logger.error(f"[ABILITY] Error executing ability {ability_name}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def calculate_damage_xp(self, damage: int, player_level: int, mob_level: int) -> int:
        """Calculate XP earned from damage dealt based on level difference.

        Args:
            damage: Amount of damage dealt
            player_level: Level of the player
            mob_level: Level of the mob

        Returns:
            XP earned from the damage
        """
        level_diff = mob_level - player_level

        if level_diff >= 0:
            # Mob is same level or higher: (level_diff + 1)x multiplier
            multiplier = level_diff + 1
        else:
            # Mob is lower level: 1/(2^|level_diff|) multiplier
            multiplier = 1.0 / (2 ** abs(level_diff))

        xp = int(damage * multiplier)
        return max(1, xp)  # Minimum 1 XP

    def get_mob_identifier(self, mob: dict) -> str:
        """Get a unique identifier for a mob for tracking purposes.

        Args:
            mob: The mob dictionary

        Returns:
            Unique string identifier for the mob
        """
        # Use id() to get a unique identifier for this specific mob instance
        return str(id(mob))

    @staticmethod
    def get_effective_stat(char_data: dict, stat_name: str, base_value: int = 10) -> int:
        """Get the effective stat value including bonuses from active effects.

        Args:
            char_data: Character data dictionary
            stat_name: Name of the stat (e.g., 'strength', 'dexterity')
            base_value: Base value to use if stat not found in char_data

        Returns:
            Effective stat value with bonuses applied
        """
        base_stat = char_data.get(stat_name, base_value)

        # Check for active effects that boost this stat
        active_effects = char_data.get('active_effects', [])
        bonus = 0

        for effect in active_effects:
            effect_type = effect.get('effect', '')
            if effect_type == f'{stat_name}_bonus':
                bonus += effect.get('bonus_amount', 0)

        return base_stat + bonus

    def _get_required_ammunition(self, weapon_type: str) -> str:
        """Get the required ammunition type for a ranged weapon."""
        ammo_map = {
            'bow': 'arrow',
            'crossbow': 'arrow',  # Could use 'bolt' if we add it
            'sling': 'stone',
            'blowgun': 'dart'
        }
        return ammo_map.get(weapon_type, None)

    def _get_ammo_display_name(self, ammo_id: str) -> str:
        """Get display name for ammunition."""
        display_names = {
            'arrow': 'arrows',
            'stone': 'stones',
            'dart': 'darts',
            'bolt': 'bolts'
        }
        return display_names.get(ammo_id, ammo_id)

    def _get_ammo_container(self, ammo_type: str) -> str:
        """Get the preferred container for ammunition type."""
        container_map = {
            'arrow': 'quiver',
            'stone': 'pouch',
            'dart': 'case'
        }
        return container_map.get(ammo_type, None)

    async def _consume_ammunition(self, player_id: int, character: dict, ammo_id: str, weapon_name: str) -> bool:
        """Find and consume one ammunition from containers or inventory.

        Returns True if ammo was consumed, False if not available.
        """
        inventory = character.get('inventory', [])

        # First, check for ammo in appropriate containers (quiver, pouch, case)
        preferred_container = self._get_ammo_container(ammo_id)

        for container_item in inventory:
            # Check if this is a container
            if container_item.get('type') != 'container':
                continue

            # Check if it's the right container type (optional - could store in any container)
            container_id = container_item.get('id')
            if preferred_container and container_id != preferred_container:
                continue

            # Check container contents
            contents = container_item.get('contents', [])
            for i, ammo in enumerate(contents):
                if ammo.get('id') == ammo_id:
                    # Found ammunition in container!
                    quantity = ammo.get('quantity', 1)

                    if quantity > 1:
                        ammo['quantity'] = quantity - 1
                    else:
                        # Remove from container
                        contents.pop(i)

                    self.logger.info(f"[AMMO] Player {player_id} consumed 1 {ammo_id} from {container_id} ({quantity-1} remaining)")
                    return True

        # If not in containers, check loose in inventory (discouraged but allowed)
        for i, item in enumerate(inventory):
            if item.get('id') == ammo_id:
                quantity = item.get('quantity', 1)

                if quantity > 1:
                    item['quantity'] = quantity - 1
                else:
                    inventory.pop(i)

                self.logger.info(f"[AMMO] Player {player_id} consumed 1 loose {ammo_id} ({quantity-1} remaining)")

                # Warning about loose ammo
                from ...utils.colors import info_message
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    info_message(f"You should store your {self._get_ammo_display_name(ammo_id)} in a {preferred_container or 'container'}!")
                )
                return True

        # No ammunition found
        ammo_name = self._get_ammo_display_name(ammo_id)
        container_name = preferred_container or 'container'

        await self.game_engine.connection_manager.send_message(
            player_id,
            error_message(f"You need {ammo_name} in a {container_name} to shoot with your {weapon_name}!")
        )
        return False

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
        self.logger.info(f"[ATTACK] Player {player_id} has {attacks_remaining} attacks remaining")

        if attacks_remaining <= 0:
            return False

        # Use one attack
        attacks_remaining -= 1
        self.logger.info(f"[ATTACK] After using attack, player {player_id} has {attacks_remaining} attacks remaining")

        # Always ensure player is tracked in fatigue system
        if attacks_remaining <= 0:
            # Player is now fatigued
            self.logger.info(f"[ATTACK] Player {player_id} is now fatigued (15 second cooldown)")
            self.set_player_fatigue(player_id)
        else:
            # Update attacks remaining (ensure player is tracked from first attack)
            self.logger.info(f"[ATTACK] Saving player {player_id} with {attacks_remaining} attacks remaining")
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
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You are too exhausted to attack! Wait {fatigue_time:.1f} more seconds.")
            )
            return

        # Check if player is paralyzed or charmed
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("You are paralyzed and cannot attack!")
                )
                return
            if effect.get('type') == 'charm' or effect.get('effect') == 'charm':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("You are charmed and cannot attack!")
                )
                return

        # Check if player has attacks remaining
        attacks_remaining = self.get_player_attacks_remaining(player_id)
        if attacks_remaining <= 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You have no attacks remaining!")
            )
            return

        # Find target
        target = await self.find_combat_target(room_id, target_name)
        if not target:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't see '{target_name}' here.")
            )
            return

        # Check if target is hostile
        if hasattr(target, 'friendly') and target.friendly:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You cannot attack {getattr(target, 'name', target_name)}!")
            )
            return

        # Execute the attack directly (no combat mode)
        await self.execute_seamless_attack(player_id, target, room_id)

    async def handle_shoot_command(self, player_id: int, target_name: str):
        """Handle player shoot/fire command for ranged weapons (Phase 1: same room only)."""
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data:
            return

        character = player_data['character']
        room_id = character['room_id']

        # Check if player has a ranged weapon equipped
        equipped = character.get('equipped', {})
        weapon = equipped.get('weapon')

        if not weapon:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have a weapon equipped!")
            )
            return

        weapon_props = weapon.get('properties', {})
        is_ranged = weapon_props.get('ranged', False)

        if not is_ranged:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {weapon['name']} is not a ranged weapon! Use 'attack' for melee combat.")
            )
            return

        # Check for required ammunition
        weapon_type = weapon_props.get('weapon_type', '')
        required_ammo = self._get_required_ammunition(weapon_type)

        if required_ammo:
            # Find and consume ammunition (checks containers)
            ammo_consumed = await self._consume_ammunition(player_id, character, required_ammo, weapon['name'])
            if not ammo_consumed:
                return  # Error message already sent

        # Check if player is fatigued
        if self.is_player_fatigued(player_id):
            fatigue_time = self.get_player_fatigue_remaining(player_id)
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You are too exhausted to shoot! Wait {fatigue_time:.1f} more seconds.")
            )
            return

        # Check if player is paralyzed or charmed
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("You are paralyzed and cannot shoot!")
                )
                return
            if effect.get('type') == 'charm' or effect.get('effect') == 'charm':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("You are charmed and cannot shoot!")
                )
                return

        # Check if player has attacks remaining
        attacks_remaining = self.get_player_attacks_remaining(player_id)
        if attacks_remaining <= 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You have no attacks remaining!")
            )
            return

        # Find target in current room
        target = await self.find_combat_target(room_id, target_name)
        if not target:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't see '{target_name}' here.")
            )
            return

        # Check if target is hostile
        if hasattr(target, 'friendly') and target.friendly:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You cannot shoot {getattr(target, 'name', target_name)}!")
            )
            return

        # Execute ranged attack
        await self.execute_ranged_attack(player_id, target, room_id)

    async def handle_shoot_command_cross_room(self, player_id: int, target_name: str, direction: str):
        """Handle cross-room shooting - shoot targets in adjacent rooms.

        Args:
            player_id: ID of the player shooting
            target_name: Name of the target to shoot
            direction: Direction to shoot (north, south, east, west, etc.)
        """
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data:
            return

        character = player_data['character']
        room_id = character['room_id']

        # Check if player has a ranged weapon equipped
        equipped = character.get('equipped', {})
        weapon = equipped.get('weapon')

        if not weapon:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have a weapon equipped!")
            )
            return

        weapon_props = weapon.get('properties', {})
        is_ranged = weapon_props.get('ranged', False)

        if not is_ranged:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {weapon['name']} is not a ranged weapon! Use 'attack' for melee combat.")
            )
            return

        # Check for required ammunition
        weapon_type = weapon_props.get('weapon_type', '')
        required_ammo = self._get_required_ammunition(weapon_type)

        if required_ammo:
            # Find and consume ammunition
            ammo_consumed = await self._consume_ammunition(player_id, character, required_ammo, weapon['name'])
            if not ammo_consumed:
                return  # Error message already sent

        # Check if player is fatigued
        if self.is_player_fatigued(player_id):
            fatigue_time = self.get_player_fatigue_remaining(player_id)
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You are too exhausted to shoot! Wait {fatigue_time:.1f} more seconds.")
            )
            return

        # Check if player is paralyzed or charmed
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("You are paralyzed and cannot shoot!")
                )
                return
            if effect.get('type') == 'charm' or effect.get('effect') == 'charm':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("You are charmed and cannot shoot!")
                )
                return

        # Check if player has attacks remaining
        attacks_remaining = self.get_player_attacks_remaining(player_id)
        if attacks_remaining <= 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You have no attacks remaining!")
            )
            return

        # Get current room
        current_room = self.game_engine.world_manager.get_room(room_id)
        if not current_room:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Something went wrong - can't find your current location.")
            )
            return

        # Find exit in the specified direction
        # room.exits is a dict: {direction: Exit object}
        exit_obj = current_room.exits.get(direction.lower())

        if not exit_obj:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"There is no exit to the {direction}.")
            )
            return

        # Check line of sight - locked exits block shots
        if exit_obj.is_locked:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The path to the {direction} is blocked - you can't shoot through it!")
            )
            return

        # Get target room
        target_room_id = exit_obj.destination_room_id
        target_room = self.game_engine.world_manager.get_room(target_room_id)
        if not target_room:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You can't see what's in that direction.")
            )
            return

        # Find target in adjacent room
        target = await self.find_combat_target(target_room_id, target_name)
        if not target:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't see '{target_name}' in that direction.")
            )
            return

        # Check if target is hostile
        if hasattr(target, 'friendly') and target.friendly:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You cannot shoot {getattr(target, 'name', target_name)}!")
            )
            return

        # Execute cross-room ranged attack (with distance penalty)
        await self.execute_ranged_attack_cross_room(
            player_id, target, room_id, target_room_id, direction
        )

    async def handle_flee_command(self, player_id: int):
        """Handle player flee command - no longer needed in seamless combat."""
        await self.game_engine.connection_manager.send_message(player_id, "There is no combat mode to flee from. You can simply walk away if you're not fatigued.")

    async def handle_retrieve_ammo(self, player_id: int):
        """Handle retrieving spent ammunition from the current room.

        Players have a chance to recover arrows/bolts that were shot in this room.
        Recovery chance: 60% base, with some arrows potentially damaged/lost.
        """
        from ...utils.colors import info_message, service_message, error_message

        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data:
            return

        character = player_data['character']
        room_id = character['room_id']

        # Check if there's any spent ammo in this room
        if room_id not in self.spent_ammo or not self.spent_ammo[room_id]:
            await self.game_engine.connection_manager.send_message(
                player_id,
                info_message("You don't find any ammunition to retrieve here.")
            )
            return

        # Retrieve ammunition with 60% recovery rate per arrow
        recovered = {}
        total_attempted = 0
        total_recovered = 0

        for ammo_type, quantity in list(self.spent_ammo[room_id].items()):
            total_attempted += quantity
            recovered_count = 0

            for _ in range(quantity):
                if random.random() <= 0.6:  # 60% recovery chance
                    recovered_count += 1

            if recovered_count > 0:
                recovered[ammo_type] = recovered_count
                total_recovered += recovered_count

        # Clear spent ammo in this room
        self.spent_ammo[room_id] = {}

        if total_recovered == 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You search for ammunition but all {total_attempted} are too damaged to use.")
            )
            return

        # Add recovered ammo to inventory
        for ammo_type, count in recovered.items():
            ammo_display_name = self._get_ammo_display_name(ammo_type)

            # Try to find a container for the ammo (quiver, pouch, etc.)
            container_type = self._get_ammo_container(ammo_type)
            stored_in_container = False

            # Check if player has appropriate container
            for item in character['inventory']:
                if item.get('id') == container_type and item.get('type') == 'container':
                    # Add to container
                    if 'contents' not in item:
                        item['contents'] = []

                    # Check if ammo already exists in container
                    found_existing = False
                    for content in item['contents']:
                        if content.get('id') == ammo_type:
                            content['quantity'] = content.get('quantity', 1) + count
                            found_existing = True
                            break

                    if not found_existing:
                        # Create new ammo stack in container
                        ammo_item = self.game_engine.config_manager.get_item(ammo_type)
                        if ammo_item:
                            item['contents'].append({
                                'id': ammo_type,
                                'name': ammo_item.get('name', ammo_type),
                                'type': ammo_item.get('type', 'weapon'),
                                'weight': ammo_item.get('weight', 0.1),
                                'quantity': count,
                                'properties': ammo_item.get('properties', {})
                            })

                    stored_in_container = True
                    break

            # If no container found, add to loose inventory
            if not stored_in_container:
                # Check if ammo exists in loose inventory
                found_loose = False
                for item in character['inventory']:
                    if item.get('id') == ammo_type:
                        item['quantity'] = item.get('quantity', 1) + count
                        found_loose = True
                        break

                if not found_loose:
                    # Create new loose ammo
                    ammo_item = self.game_engine.config_manager.get_item(ammo_type)
                    if ammo_item:
                        character['inventory'].append({
                            'id': ammo_type,
                            'name': ammo_item.get('name', ammo_type),
                            'type': ammo_item.get('type', 'weapon'),
                            'weight': ammo_item.get('weight', 0.1),
                            'value': ammo_item.get('base_value', 1),
                            'quantity': count,
                            'properties': ammo_item.get('properties', {})
                        })

        # Update encumbrance
        self.game_engine.player_manager.update_encumbrance(character)

        # Send success message
        lost_count = total_attempted - total_recovered
        msg = f"You retrieve {total_recovered} {self._get_ammo_display_name(list(recovered.keys())[0])}"
        if lost_count > 0:
            msg += f" ({lost_count} were too damaged to recover)"
        msg += "."

        await self.game_engine.connection_manager.send_message(
            player_id,
            service_message(msg)
        )

    def get_spent_ammo_description(self, room_id: str, dim_factor: float = 1.0) -> str:
        """Get a description of spent ammunition in the room.

        Args:
            room_id: Room ID to check
            dim_factor: Light level dimming factor (0.0-1.0)

        Returns:
            Formatted string describing spent ammunition, or empty string if none
        """
        if room_id not in self.spent_ammo or not self.spent_ammo[room_id]:
            return ""

        ammo_descriptions = []
        for ammo_type, quantity in self.spent_ammo[room_id].items():
            ammo_name = self._get_ammo_display_name(ammo_type)
            if quantity == 1:
                ammo_descriptions.append(f"1 {ammo_name.rstrip('s')}")
            else:
                ammo_descriptions.append(f"{quantity} {ammo_name}")

        if ammo_descriptions:
            from ...utils.colors import wrap_color, RGBColors, Colors
            ammo_text = ", ".join(ammo_descriptions)
            return wrap_color(f"There are {ammo_text} scattered on the ground.", RGBColors.CYAN, dim_factor) + Colors.BOLD_WHITE

        return ""

    async def find_combat_target(self, room_id: str, target_name: str):
        """Find a valid combat target in the room."""
        # Check spawned mobs first
        room_mobs = self.game_engine.room_mobs.get(room_id, [])
        for mob in room_mobs:
            mob_name = mob.get('name', '')
            if self.game_engine.world_manager._matches_target(target_name.lower(), mob_name.lower()):
                return mob

        # Check NPCs (but exclude quest-givers and non-hostile NPCs)
        room = self.game_engine.world_manager.get_room(room_id)
        if room and hasattr(room, 'npcs'):
            for npc in room.npcs:
                if self.game_engine.world_manager._matches_target(target_name.lower(), npc.name.lower()):
                    # Get NPC data to check type
                    npc_data = self.game_engine.world_manager.get_npc_data(npc.npc_id)
                    if npc_data:
                        npc_type = npc_data.get('type', '')
                        # Block attacking quest-givers and non-hostile NPCs
                        if npc_type in ['quest_giver', 'vendor', 'trainer']:
                            return None
                        # Only allow attacking if explicitly hostile
                        if npc_data.get('hostile', False):
                            return npc_data
                    return None

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
        # Track which mob died for quest tracking
        dead_mob = None
        dead_mob_id = None

        # Remove dead mob from room
        if room_id in self.game_engine.room_mobs:
            # Find and remove the dead mob
            alive_mobs = []
            for mob in self.game_engine.room_mobs[room_id]:
                # Use get_mob_identifier to get the unique instance ID
                mob_id = self.get_mob_identifier(mob)
                if mob_id != mob_participant_id:
                    alive_mobs.append(mob)
                else:
                    # This is the dead mob
                    dead_mob = mob
                    dead_mob_id = mob.get('id')
                    # Clean up spell state for dead mob
                    self.spellcasting.cleanup_mob(mob_participant_id)
            self.game_engine.room_mobs[room_id] = alive_mobs

        # Track quest progress for players in combat
        for player_id, combat_room in self.player_combats.items():
            if combat_room == room_id:
                player_data = self.game_engine.player_manager.connected_players.get(player_id)
                if player_data and player_data.get('character'):
                    character = player_data['character']

                    # Note: XP is now awarded per damage dealt in execute_seamless_attack

                    # Track quest progress for killing this mob
                    if dead_mob and dead_mob_id:
                        # Check all active quests for kill objectives
                        player_quests = character.get('quests', {})
                        self.logger.info(f"[QUEST] Player killed {dead_mob_id} in {room_id}, checking {len(player_quests)} quests")
                        for quest_id in player_quests:
                            # Skip completed quests
                            quest_status = player_quests[quest_id]
                            if quest_status.get('completed'):
                                self.logger.info(f"[QUEST] Skipping {quest_id} - already completed")
                                continue

                            self.logger.info(f"[QUEST] Checking {quest_id} for kill_monster objective: {dead_mob_id}")
                            quest_completed = self.game_engine.quest_manager.check_objective_completion(
                                character,
                                quest_id,
                                'kill_monster',
                                dead_mob_id,
                                room_id
                            )

                            if quest_completed:
                                quest = self.game_engine.quest_manager.get_quest(quest_id)
                                if quest:
                                    completion_msg = quest.get('completed_message', 'Quest objective completed!')
                                    await self.game_engine.connection_manager.send_message(player_id, f"\n{completion_msg}\n")

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
            for room_id, mobs in list(self.game_engine.room_mobs.items()):
                # Skip if mobs is None or not a list
                if mobs is None or not isinstance(mobs, list):
                    self.logger.warning(f"[MOB_AI] Invalid mobs list in room {room_id}: {type(mobs)}")
                    continue

                # Filter out None values and make a copy to avoid modification during iteration
                valid_mobs = [mob for mob in mobs if mob is not None and isinstance(mob, dict)]

                for mob in valid_mobs:
                    await self.process_single_mob_ai(mob, room_id)
        except Exception as e:
            self.logger.error(f"Error in mob AI processing: {e}")
            import traceback
            self.logger.error(f"[MOB_AI] Traceback: {traceback.format_exc()}")

    async def process_single_mob_ai(self, mob: dict, room_id: str):
        """Process AI for a single mob."""
        try:
            # Skip if mob is None (could happen if removed during iteration)
            if mob is None:
                self.logger.warning(f"[MOB_AI] Skipping None mob in room {room_id}")
                return

            # Skip if mob is dead
            if mob.get('health', 0) <= 0:
                return

            # Skip if mob is fatigued
            mob_id = self.get_mob_identifier(mob)
            if self.is_mob_fatigued(mob_id):
                return

            # Skip if mob is paralyzed
            active_effects = mob.get('active_effects', [])
            for effect in active_effects:
                if effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze':
                    return

            # Skip if not hostile (unless it's a summoned creature - they attack hostile mobs)
            if mob.get('type') != 'hostile' and not mob.get('is_summoned'):
                return

            # Check if mob has aggro target from attacks
            if mob.get('aggro_target') and mob.get('aggro_room'):
                target_player_id = mob.get('aggro_target')
                target_room_id = mob.get('aggro_room')

                # Check aggro timeout (30 seconds without being attacked)
                aggro_timeout = 30.0  # seconds
                last_attack_time = mob.get('aggro_last_attack', 0)
                current_time = time.time()

                if last_attack_time > 0 and (current_time - last_attack_time) > aggro_timeout:
                    # Aggro has degraded - clear it
                    mob_name = mob.get('name', 'Unknown')
                    self.logger.info(f"[AGGRO] {mob_name} aggro on player {target_player_id} degraded after {aggro_timeout}s timeout")
                    mob.pop('aggro_target', None)
                    mob.pop('aggro_room', None)
                    mob.pop('aggro_last_attack', None)
                else:
                    # Aggro still valid - check if target player still exists and is online
                    target_player_data = self.game_engine.player_manager.connected_players.get(target_player_id)
                    if target_player_data and target_player_data.get('character'):
                        target_character = target_player_data['character']
                        actual_room = target_character.get('room_id')

                        # If target is in a different room, try to move toward them
                        if actual_room != room_id:
                            moved = await self.mob_move_toward_target(mob, room_id, actual_room)
                            if moved:
                                return  # Mob moved, done for this tick
                        else:
                            # Target is now in same room, clear aggro and attack normally
                            mob.pop('aggro_target', None)
                            mob.pop('aggro_room', None)
                            mob.pop('aggro_last_attack', None)
                    else:
                        # Target no longer exists, clear aggro
                        mob.pop('aggro_target', None)
                        mob.pop('aggro_room', None)
                        mob.pop('aggro_last_attack', None)

            # Check if mob should flee (only wandering mobs flee when low health)
            if mob.get('is_wandering'):
                current_health = mob.get('health', 0)
                max_health = mob.get('max_health', 100)
                health_percent = current_health / max_health if max_health > 0 else 0

                # Get flee settings from config
                flee_threshold = self.game_engine.config_manager.get_setting('combat', 'mob_flee', 'health_threshold', default=0.3)
                flee_chance = self.game_engine.config_manager.get_setting('combat', 'mob_flee', 'flee_chance', default=0.5)

                # Attempt to flee if health is below threshold and dice roll succeeds
                if health_percent < flee_threshold and random.random() < flee_chance:
                    fled = await self.attempt_mob_flee(mob, room_id)
                    if fled:
                        return  # Mob fled, don't attack

            # Find players in the same room (prioritize players, exclude invisible and party members)
            target_players = []

            # Get summoner's party leader (if this mob is a summon)
            mob_party_leader = mob.get('party_leader') if mob.get('is_summoned') else None

            for player_id, player_data in self.game_engine.player_manager.connected_players.items():
                character = player_data.get('character')
                if character and character.get('room_id') == room_id:
                    # Skip party members if this is a summoned creature
                    if mob_party_leader is not None:
                        player_party_leader = character.get('party_leader', player_id)
                        # Don't attack players in the same party
                        if player_party_leader == mob_party_leader:
                            continue

                    # Check if player is invisible
                    active_effects = character.get('active_effects', [])
                    is_invisible = any(
                        effect.get('effect') in ['invisible', 'invisibility']
                        for effect in active_effects
                    )
                    # Only target visible players
                    if not is_invisible:
                        target_players.append(player_id)

            # Determine target (player or mob)
            target = None
            target_is_player = False
            target_player_id = None

            # Build list of potential mob targets first
            other_mobs = []
            if room_id in self.game_engine.room_mobs:
                    # Check if attacking mob is a lair mob (summons are treated as wandering)
                    attacking_mob_is_lair = not mob.get('is_wandering', False) and not mob.get('is_summoned', False)

                    for other_mob in self.game_engine.room_mobs[room_id]:
                        # Skip None mobs
                        if other_mob is None:
                            continue

                        # Summoned mobs only attack hostile mobs
                        if mob.get('is_summoned'):
                            # Don't attack self, only attack living hostile mobs
                            if (other_mob != mob and
                                other_mob.get('health', 0) > 0 and
                                other_mob.get('type') == 'hostile'):
                                other_mobs.append(other_mob)
                        else:
                            # Regular hostile mob behavior
                            # Don't attack self, attack living hostile mobs and summoned mobs
                            is_valid_target = (other_mob != mob and
                                             other_mob.get('health', 0) > 0 and
                                             (other_mob.get('type') == 'hostile' or other_mob.get('is_summoned')))

                            if is_valid_target:
                                # If this mob is a lair mob, don't attack other lair mobs
                                # (but wandering mobs and summons are fair game)
                                if attacking_mob_is_lair:
                                    target_is_lair = not other_mob.get('is_wandering', False) and not other_mob.get('is_summoned', False)
                                    if target_is_lair:
                                        # Don't attack fellow lair mob
                                        continue
                                other_mobs.append(other_mob)

            # Now choose target: summoned mobs only attack other mobs, regular mobs can attack players or mobs
            if mob.get('is_summoned'):
                # Summoned mobs only attack hostile mobs, never players
                if other_mobs:
                    target = random.choice(other_mobs)
                    target_is_player = False
            else:
                # Regular hostile mobs: choose between players and other mobs
                # Combine both pools and choose randomly
                all_targets = []

                # Add players to target pool
                if target_players:
                    for player_id in target_players:
                        all_targets.append(('player', player_id))

                # Add mobs to target pool
                if other_mobs:
                    for other_mob in other_mobs:
                        all_targets.append(('mob', other_mob))

                # Choose a random target from combined pool
                if all_targets:
                    target_type, target_obj = random.choice(all_targets)

                    if target_type == 'player':
                        target_player_id = target_obj
                        player_data = self.game_engine.player_manager.connected_players.get(target_player_id)
                        if player_data:
                            target = player_data.get('character')
                            target_is_player = True
                    else:
                        target = target_obj
                        target_is_player = False

            # If we have a target, check for special ability use first
            if target:
                # Check if mob should use a special ability
                ability_name = self.check_and_use_ability(mob, mob_id, target, room_id)

                if ability_name:
                    # Mob will use special ability instead of normal attack
                    await self.execute_ability(ability_name, mob, mob_id, target, room_id)
                    # Set mob fatigue after using ability
                    self.set_mob_fatigue(mob_id)
                else:
                    # No ability used, proceed with normal attack
                    if target_is_player:
                        await self.execute_mob_attack(mob, mob_id, target_player_id, room_id)
                    else:
                        await self.execute_mob_vs_mob_attack(mob, mob_id, target, room_id)

        except Exception as e:
            self.logger.error(f"Error in single mob AI processing for mob in room {room_id}: {e}")
            self.logger.error(f"[MOB_AI] Mob object type: {type(mob)}, Mob value: {mob}")
            import traceback
            self.logger.error(f"[MOB_AI] Traceback: {traceback.format_exc()}")

    async def mob_move_toward_target(self, mob: dict, current_room_id: str, target_room_id: str) -> bool:
        """Move mob one step toward a target room.

        Args:
            mob: The mob to move
            current_room_id: Current room ID
            target_room_id: Target room ID to move toward

        Returns:
            True if mob successfully moved, False otherwise
        """
        try:
            mob_name = mob.get('name', 'Unknown creature')

            # Get current room
            room = self.game_engine.world_manager.get_room(current_room_id)
            if not room:
                return False

            # Get available exits
            all_exits = list(room.exits.keys()) if hasattr(room, 'exits') else []
            if not all_exits:
                self.logger.debug(f"[MOB_MOVE] {mob_name} has no exits to move through")
                return False

            # Use pathfinding to find best direction
            path = self.game_engine.world_manager.world_graph.find_path(current_room_id, target_room_id)

            if not path or len(path) < 2:
                # No path or already at destination
                return False

            # Next room in path
            next_room_id = path[1]

            # Find which direction leads to next room
            chosen_direction = None
            for direction in all_exits:
                exit_obj = room.exits.get(direction)
                if not exit_obj:
                    continue

                # Check if exit is locked
                if hasattr(exit_obj, 'is_locked') and exit_obj.is_locked:
                    continue

                # Get destination
                destination_id = exit_obj.destination_room_id if hasattr(exit_obj, 'destination_room_id') else str(exit_obj)
                if destination_id == next_room_id:
                    chosen_direction = direction
                    break

            if not chosen_direction:
                self.logger.debug(f"[MOB_MOVE] {mob_name} cannot find direction to {next_room_id}")
                return False

            # Check barriers - mobs must respect barriers like players do
            if hasattr(self.game_engine, 'barrier_system'):
                # Create a minimal character dict for the mob (most mobs don't have keys)
                mob_character = {
                    'inventory': mob.get('inventory', [])
                }

                # Check if barrier blocks movement
                can_pass, unlock_msg = await self.game_engine.barrier_system.check_barrier(
                    player_id=-1,  # Negative ID indicates this is a mob
                    character=mob_character,
                    room=room,
                    direction=chosen_direction,
                    player_name=mob_name
                )

                if not can_pass:
                    self.logger.debug(f"[MOB_MOVE] {mob_name} blocked by barrier in direction {chosen_direction}, clearing aggro")
                    # Clear aggro since we can't reach the target
                    mob.pop('aggro_target', None)
                    mob.pop('aggro_room', None)
                    return False

                # If barrier was unlocked, update mob's inventory
                if unlock_msg:
                    mob['inventory'] = mob_character['inventory']

            # Check if destination is a safe room - mobs cannot enter safe rooms
            dest_room = self.game_engine.world_manager.get_room(next_room_id)
            if dest_room and hasattr(dest_room, 'is_safe') and dest_room.is_safe:
                self.logger.debug(f"[MOB_MOVE] {mob_name} cannot enter safe room {next_room_id}, clearing aggro")
                # Clear aggro since we can't reach the target
                mob.pop('aggro_target', None)
                mob.pop('aggro_room', None)
                return False

            # Move the mob
            destination_id = next_room_id

            # Remove from current room
            if current_room_id in self.game_engine.room_mobs:
                if mob in self.game_engine.room_mobs[current_room_id]:
                    self.game_engine.room_mobs[current_room_id].remove(mob)

            # Add to destination room
            if destination_id not in self.game_engine.room_mobs:
                self.game_engine.room_mobs[destination_id] = []
            self.game_engine.room_mobs[destination_id].append(mob)

            # Update mob's position tracking if needed
            mob['current_room'] = destination_id

            # Notify players in both rooms
            await self.game_engine._notify_room(
                current_room_id,
                f"{mob_name} moves {chosen_direction}."
            )
            await self.game_engine._notify_room(
                destination_id,
                f"{mob_name} arrives from {self._get_opposite_direction(chosen_direction)}."
            )

            self.logger.info(f"[MOB_MOVE] {mob_name} moved {chosen_direction} toward target (from {current_room_id} to {destination_id})")
            return True

        except Exception as e:
            self.logger.error(f"[MOB_MOVE] Error moving mob: {e}")
            import traceback
            self.logger.error(f"[MOB_MOVE] Traceback: {traceback.format_exc()}")
            return False

    def _get_opposite_direction(self, direction: str) -> str:
        """Get the opposite direction for movement messages."""
        opposites = {
            'north': 'the south', 'n': 'the south',
            'south': 'the north', 's': 'the north',
            'east': 'the west', 'e': 'the west',
            'west': 'the east', 'w': 'the east',
            'northeast': 'the southwest', 'ne': 'the southwest',
            'northwest': 'the southeast', 'nw': 'the southeast',
            'southeast': 'the northwest', 'se': 'the northwest',
            'southwest': 'the northeast', 'sw': 'the northeast',
            'up': 'below', 'u': 'below',
            'down': 'above', 'd': 'above'
        }
        return opposites.get(direction.lower(), 'nearby')

    async def attempt_mob_flee(self, mob: dict, room_id: str) -> bool:
        """Attempt to make a mob flee to a random adjacent room.

        Args:
            mob: The mob attempting to flee
            room_id: Current room ID

        Returns:
            True if mob successfully fled, False otherwise
        """
        try:
            mob_name = mob.get('name', 'Unknown creature')

            # Get current room
            room = self.game_engine.world_manager.get_room(room_id)
            if not room:
                return False

            # Get available exits
            all_exits = list(room.exits.keys()) if hasattr(room, 'exits') else []
            if not all_exits:
                self.logger.debug(f"[FLEE] {mob_name} has no exits to flee through")
                return False

            # Filter out locked exits, barriers, and exits leading to safe rooms
            valid_exits = []
            for direction in all_exits:
                exit_obj = room.exits.get(direction)
                if not exit_obj:
                    continue

                # Check if exit is locked (old system - being phased out)
                if hasattr(exit_obj, 'is_locked') and exit_obj.is_locked:
                    self.logger.debug(f"[FLEE] {mob_name} cannot flee {direction} - exit is locked")
                    continue

                # Get destination room
                destination_id = exit_obj.destination_room_id if hasattr(exit_obj, 'destination_room_id') else str(exit_obj)
                if not destination_id or destination_id not in self.game_engine.world_manager.rooms:
                    continue

                # Check barriers - mobs must respect barriers when fleeing
                if hasattr(self.game_engine, 'barrier_system'):
                    mob_character = {
                        'inventory': mob.get('inventory', [])
                    }

                    can_pass, unlock_msg = await self.game_engine.barrier_system.check_barrier(
                        player_id=-1,  # Negative ID indicates this is a mob
                        character=mob_character,
                        room=room,
                        direction=direction,
                        player_name=mob_name
                    )

                    if not can_pass:
                        self.logger.debug(f"[FLEE] {mob_name} cannot flee {direction} - blocked by barrier")
                        continue

                    # Update mob inventory if barrier was unlocked
                    if unlock_msg:
                        mob['inventory'] = mob_character['inventory']

                # Check if destination is a safe room
                dest_room = self.game_engine.world_manager.get_room(destination_id)
                if dest_room and hasattr(dest_room, 'is_safe') and dest_room.is_safe:
                    self.logger.debug(f"[FLEE] {mob_name} cannot flee {direction} - destination is a safe room")
                    continue

                # This is a valid exit
                valid_exits.append((direction, destination_id))

            if not valid_exits:
                self.logger.debug(f"[FLEE] {mob_name} has no valid exits (all locked or lead to safe rooms)")
                return False

            # Choose random valid exit
            direction, destination_id = random.choice(valid_exits)

            # Remove mob from current room
            if room_id in self.game_engine.room_mobs:
                self.game_engine.room_mobs[room_id] = [m for m in self.game_engine.room_mobs[room_id] if m != mob]

            # Add mob to destination room
            if destination_id not in self.game_engine.room_mobs:
                self.game_engine.room_mobs[destination_id] = []
            self.game_engine.room_mobs[destination_id].append(mob)

            # Notify players in the room
            flee_msg = f"{mob_name} flees {direction}!"
            await self._notify_room_players(room_id, flee_msg)

            # Notify players in destination room
            arrive_msg = f"{mob_name} arrives, fleeing from combat!"
            await self._notify_room_players(destination_id, arrive_msg)

            self.logger.debug(f"[FLEE] {mob_name} fled from {room_id} to {destination_id} via {direction}")
            return True

        except Exception as e:
            self.logger.error(f"Error in mob flee attempt: {e}")
            import traceback
            self.logger.error(f"[FLEE] Traceback: {traceback.format_exc()}")
            return False

    async def execute_ranged_attack(self, player_id: int, target: dict, room_id: str):
        """Execute a ranged attack with a bow/crossbow (DEX-based)."""
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data:
            return

        character = player_data['character']

        # Use an attack
        if not self.use_player_attack(player_id):
            await self.game_engine.connection_manager.send_message(player_id, "You cannot shoot right now!")
            return

        # Create temporary entities for damage calculation
        class TempCharacter:
            def __init__(self, char_data):
                self.name = char_data['name']
                self.level = char_data.get('level', 1)
                # Get effective stats - DEX is primary for ranged
                self.strength = CombatSystem.get_effective_stat(char_data, 'strength', 10)
                self.dexterity = CombatSystem.get_effective_stat(char_data, 'dexterity', 10)
                self.constitution = CombatSystem.get_effective_stat(char_data, 'constitution', 10)
                self.intelligence = CombatSystem.get_effective_stat(char_data, 'intellect', 10)
                self.wisdom = CombatSystem.get_effective_stat(char_data, 'wisdom', 10)
                self.charisma = CombatSystem.get_effective_stat(char_data, 'charisma', 10)

        class TempMob:
            def __init__(self, mob_data):
                self.name = mob_data.get('name', 'Unknown')
                self.level = mob_data.get('level', 1)
                self.health = mob_data.get('health', 100)
                self.max_health = mob_data.get('max_health', 100)
                self.strength = mob_data.get('strength', 12)
                self.dexterity = mob_data.get('dexterity', 10)
                self.constitution = mob_data.get('constitution', 12)
                self.intelligence = mob_data.get('intelligence', 8)
                self.wisdom = mob_data.get('wisdom', 10)
                self.charisma = mob_data.get('charisma', 6)

        temp_char = TempCharacter(character)
        temp_mob = TempMob(target)

        # Import damage calculator
        from .damage_calculator import DamageCalculator

        target_name = target.get('name', 'the target')
        mob_armor = target.get('armor_class', 0)

        # Track spent ammunition (arrows can be retrieved later)
        equipped_weapon = character.get('equipped', {}).get('weapon')
        if equipped_weapon:
            weapon_type = equipped_weapon.get('properties', {}).get('weapon_type', '')
            required_ammo = self._get_required_ammunition(weapon_type)
            if required_ammo:
                # Add spent ammo to room
                if room_id not in self.spent_ammo:
                    self.spent_ammo[room_id] = {}
                self.spent_ammo[room_id][required_ammo] = self.spent_ammo[room_id].get(required_ammo, 0) + 1

        # Check attack outcome
        base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)
        outcome = DamageCalculator.check_attack_outcome(temp_char, temp_mob, mob_armor, base_hit_chance)

        if outcome['result'] == 'miss':
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"Your shot misses {target_name}!")
            )
            await self.broadcast_to_room(room_id, combat_action(f"{character['name']}'s shot misses {target_name}!"), exclude_player=player_id)
        elif outcome['result'] == 'dodge':
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"{target_name} dodges your shot!")
            )
            await self.broadcast_to_room(room_id, combat_action(f"{target_name} dodges {character['name']}'s shot!"), exclude_player=player_id)
        elif outcome['result'] == 'deflect':
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"Your shot is deflected by {target_name}'s armor!")
            )
            await self.broadcast_to_room(room_id, combat_action(f"{character['name']}'s shot is deflected by {target_name}'s armor!"), exclude_player=player_id)
        else:
            # Hit - calculate ranged damage
            equipped_weapon = character.get('equipped', {}).get('weapon')

            # Get critical multiplier (may be enhanced by class abilities)
            crit_multiplier = self.get_critical_multiplier(character)

            damage_info = DamageCalculator.calculate_ranged_damage(temp_char, equipped_weapon, crit_multiplier=crit_multiplier)
            damage = damage_info['damage']
            is_critical = damage_info['is_critical']

            # Check for Ranger's hunter's mark passive (+3 ranged damage)
            hunters_mark = self.game_engine.ability_system.check_passive_ability(
                character,
                'on_ranged_attack',
                {}
            )
            if hunters_mark and hunters_mark.get('type') == 'damage_bonus':
                damage += hunters_mark.get('value', 0)

            # Check for active multishot ability
            active_abilities = character.get('active_abilities', {})
            if 'multishot' in active_abilities:
                multishot_data = active_abilities['multishot']
                multishot_mult = multishot_data.get('damage_multiplier', 1.0)
                damage = int(damage * multishot_mult)

                # Consume one charge
                multishot_data['attacks_remaining'] = multishot_data.get('attacks_remaining', 1) - 1
                if multishot_data['attacks_remaining'] <= 0:
                    active_abilities.pop('multishot')

            # Apply damage
            target['health'] = max(0, target['health'] - damage)
            target_alive = target['health'] > 0

            # Track damage for XP
            mob_id = self.get_mob_identifier(target)
            if mob_id not in self.mob_damage_tracking:
                self.mob_damage_tracking[mob_id] = {}

            previous_damage = self.mob_damage_tracking[mob_id].get(player_id, 0)
            self.mob_damage_tracking[mob_id][player_id] = previous_damage + damage

            # Award XP
            player_level = character.get('level', 1)
            mob_level = target.get('level', 1)
            mob_max_hp = target.get('max_health', 100)

            total_damage_dealt = self.mob_damage_tracking[mob_id][player_id]
            countable_damage = damage
            if total_damage_dealt > mob_max_hp:
                countable_damage = damage - (total_damage_dealt - mob_max_hp)
                countable_damage = max(0, countable_damage)

            xp_earned = self.calculate_damage_xp(countable_damage, player_level, mob_level)
            if xp_earned > 0:
                character['experience'] = character.get('experience', 0) + xp_earned

            # Messages
            weapon_name = equipped_weapon.get('name', 'ranged weapon') if equipped_weapon else 'ranged weapon'
            hit_msg = f"You shoot {target_name} with your {weapon_name} for {damage} damage"
            if is_critical:
                hit_msg += " (Critical Hit!)"
            if xp_earned > 0:
                hit_msg += f" (+{xp_earned} XP)"
            hit_msg += "!"

            await self.game_engine.connection_manager.send_message(player_id, damage_to_enemy(hit_msg))
            await self.broadcast_to_room(
                room_id,
                combat_action(f"{character['name']} shoots {target_name} with their {weapon_name} for {damage} damage!"),
                exclude_player=player_id
            )

            # Check if target died
            if not target_alive:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    announcement(f"{target_name} has been defeated!")
                )
                await self.broadcast_to_room(
                    room_id,
                    announcement(f"{target_name} has been defeated!"),
                    exclude_player=player_id
                )

                # Award loot
                await self.handle_mob_loot_drop(player_id, target, room_id)

                # Cleanup
                if mob_id in self.mob_damage_tracking:
                    del self.mob_damage_tracking[mob_id]
                self.game_engine.room_mobs[room_id].remove(target)
            else:
                # Mob survived - set/update aggro on the attacker (for same-room ranged attacks)
                if 'aggro_target' not in target:
                    target['aggro_target'] = player_id
                    target['aggro_room'] = room_id
                    self.logger.debug(f"[AGGRO] {target_name} is now aggro'd on player {player_id} in room {room_id}")
                # Update aggro timestamp if this is the current aggro target
                if target.get('aggro_target') == player_id:
                    target['aggro_last_attack'] = time.time()

        # Note: Fatigue is already handled by use_player_attack() - do not call set_player_fatigue here!

    async def execute_ranged_attack_cross_room(self, player_id: int, target: dict, shooter_room_id: str, target_room_id: str, direction: str):
        """Execute a cross-room ranged attack with distance penalty.

        Args:
            player_id: ID of the attacking player
            target: Target mob dictionary
            shooter_room_id: Room ID where the shooter is located
            target_room_id: Room ID where the target is located
            direction: Direction of the shot (for messaging)
        """
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data:
            return

        character = player_data['character']

        # Use an attack
        if not self.use_player_attack(player_id):
            await self.game_engine.connection_manager.send_message(player_id, "You cannot shoot right now!")
            return

        # Create temporary entities for damage calculation
        class TempCharacter:
            def __init__(self, char_data):
                self.name = char_data['name']
                self.level = char_data.get('level', 1)
                # Get effective stats - DEX is primary for ranged
                self.strength = CombatSystem.get_effective_stat(char_data, 'strength', 10)
                self.dexterity = CombatSystem.get_effective_stat(char_data, 'dexterity', 10)
                self.constitution = CombatSystem.get_effective_stat(char_data, 'constitution', 10)
                self.intelligence = CombatSystem.get_effective_stat(char_data, 'intellect', 10)
                self.wisdom = CombatSystem.get_effective_stat(char_data, 'wisdom', 10)
                self.charisma = CombatSystem.get_effective_stat(char_data, 'charisma', 10)

        class TempMob:
            def __init__(self, mob_data):
                self.name = mob_data.get('name', 'Unknown')
                self.level = mob_data.get('level', 1)
                self.health = mob_data.get('health', 100)
                self.max_health = mob_data.get('max_health', 100)
                self.strength = mob_data.get('strength', 12)
                self.dexterity = mob_data.get('dexterity', 10)
                self.constitution = mob_data.get('constitution', 12)
                self.intelligence = mob_data.get('intelligence', 8)
                self.wisdom = mob_data.get('wisdom', 10)
                self.charisma = mob_data.get('charisma', 6)

        temp_char = TempCharacter(character)
        temp_mob = TempMob(target)

        # Import damage calculator
        from .damage_calculator import DamageCalculator

        target_name = target.get('name', 'the target')
        mob_armor = target.get('armor_class', 0)

        # Track spent ammunition in TARGET room (where arrow lands)
        equipped_weapon = character.get('equipped', {}).get('weapon')
        if equipped_weapon:
            weapon_type = equipped_weapon.get('properties', {}).get('weapon_type', '')
            required_ammo = self._get_required_ammunition(weapon_type)
            if required_ammo:
                # Add spent ammo to target room
                if target_room_id not in self.spent_ammo:
                    self.spent_ammo[target_room_id] = {}
                self.spent_ammo[target_room_id][required_ammo] = self.spent_ammo[target_room_id].get(required_ammo, 0) + 1

        # Apply cross-room penalty: -20% to hit chance, -10% damage
        base_dex = temp_char.dexterity
        temp_char.dexterity = int(temp_char.dexterity * 0.8)  # Reduce effective DEX for hit calculation

        # Check attack outcome with penalty
        base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)
        outcome = DamageCalculator.check_attack_outcome(temp_char, temp_mob, mob_armor, base_hit_chance)

        # Restore original DEX for damage calculation
        temp_char.dexterity = base_dex

        # Get opposite direction for messaging
        opposite_dir = {
            'north': 'south', 'n': 'south',
            'south': 'north', 's': 'north',
            'east': 'west', 'e': 'west',
            'west': 'east', 'w': 'east',
            'northeast': 'southwest', 'ne': 'southwest',
            'northwest': 'southeast', 'nw': 'southeast',
            'southeast': 'northwest', 'se': 'northwest',
            'southwest': 'northeast', 'sw': 'northeast',
            'up': 'down', 'u': 'down',
            'down': 'up', 'd': 'up'
        }.get(direction.lower(), 'somewhere')

        if outcome['result'] == 'miss':
            # Shooter room message
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"You draw your bow and fire an arrow {direction} at {target_name}, but it misses!")
            )
            await self.broadcast_to_room(
                shooter_room_id,
                combat_action(f"{character['name']} fires an arrow {direction}!"),
                exclude_player=player_id
            )
            # Target room message
            await self.broadcast_to_room(
                target_room_id,
                combat_action(f"An arrow flies in from the {opposite_dir} and clatters harmlessly against the wall.")
            )
        elif outcome['result'] == 'dodge':
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"You fire an arrow {direction} at {target_name}, but it dodges!")
            )
            await self.broadcast_to_room(
                shooter_room_id,
                combat_action(f"{character['name']} fires an arrow {direction}!"),
                exclude_player=player_id
            )
            await self.broadcast_to_room(
                target_room_id,
                combat_action(f"An arrow flies in from the {opposite_dir} at {target_name}, who dodges out of the way!")
            )
        elif outcome['result'] == 'deflect':
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"You fire an arrow {direction} at {target_name}, but it's deflected by armor!")
            )
            await self.broadcast_to_room(
                shooter_room_id,
                combat_action(f"{character['name']} fires an arrow {direction}!"),
                exclude_player=player_id
            )
            await self.broadcast_to_room(
                target_room_id,
                combat_action(f"An arrow flies in from the {opposite_dir} and bounces off {target_name}'s armor!")
            )
        else:
            # Hit - calculate ranged damage with distance penalty

            # Get critical multiplier (may be enhanced by class abilities)
            crit_multiplier = self.get_critical_multiplier(character)

            damage_info = DamageCalculator.calculate_ranged_damage(temp_char, equipped_weapon, crit_multiplier=crit_multiplier)
            base_damage = damage_info['damage']
            # Apply 10% damage reduction for cross-room shots
            damage = int(base_damage * 0.9)
            is_critical = damage_info['is_critical']

            # Apply damage
            target['health'] = max(0, target['health'] - damage)
            target_alive = target['health'] > 0

            # Track damage for XP
            mob_id = self.get_mob_identifier(target)
            if mob_id not in self.mob_damage_tracking:
                self.mob_damage_tracking[mob_id] = {}

            previous_damage = self.mob_damage_tracking[mob_id].get(player_id, 0)
            self.mob_damage_tracking[mob_id][player_id] = previous_damage + damage

            # Award XP
            player_level = character.get('level', 1)
            mob_level = target.get('level', 1)
            mob_max_hp = target.get('max_health', 100)

            total_damage_dealt = self.mob_damage_tracking[mob_id][player_id]
            countable_damage = damage
            if total_damage_dealt > mob_max_hp:
                countable_damage = damage - (total_damage_dealt - mob_max_hp)
                countable_damage = max(0, countable_damage)

            xp_earned = self.calculate_damage_xp(countable_damage, player_level, mob_level)
            if xp_earned > 0:
                character['experience'] = character.get('experience', 0) + xp_earned

            # Messages
            weapon_name = equipped_weapon.get('name', 'ranged weapon') if equipped_weapon else 'ranged weapon'
            hit_msg = f"You draw your bow and fire an arrow {direction} at {target_name} for {damage} damage"
            if is_critical:
                hit_msg += " (Critical Hit!)"
            if xp_earned > 0:
                hit_msg += f" (+{xp_earned} XP)"
            hit_msg += "!"

            await self.game_engine.connection_manager.send_message(player_id, damage_to_enemy(hit_msg))
            await self.broadcast_to_room(
                shooter_room_id,
                combat_action(f"{character['name']} fires an arrow {direction}!"),
                exclude_player=player_id
            )
            await self.broadcast_to_room(
                target_room_id,
                combat_action(f"An arrow flies in from the {opposite_dir} and strikes {target_name} for {damage} damage!")
            )

            # Check if target died
            if not target_alive:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    announcement(f"{target_name} has been defeated!")
                )
                await self.broadcast_to_room(
                    target_room_id,
                    announcement(f"{target_name} has been defeated!")
                )

                # Award loot (drops in target room)
                await self.handle_mob_loot_drop(player_id, target, target_room_id)

                # Cleanup
                if mob_id in self.mob_damage_tracking:
                    del self.mob_damage_tracking[mob_id]
                if target_room_id in self.game_engine.room_mobs and target in self.game_engine.room_mobs[target_room_id]:
                    self.game_engine.room_mobs[target_room_id].remove(target)
            else:
                # Mob survived - make it aggro on the shooter
                # Store aggro information for mob AI to use
                if 'aggro_target' not in target:
                    target['aggro_target'] = player_id
                    target['aggro_room'] = shooter_room_id
                    self.logger.info(f"[RANGED_AGGRO] {target_name} is now aggro'd on player {player_id} in room {shooter_room_id}")
                # Update aggro timestamp if this is the current aggro target
                if target.get('aggro_target') == player_id:
                    target['aggro_last_attack'] = time.time()

        # Note: Fatigue is already handled by use_player_attack()

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

            # Check if mob is a spellcaster
            is_spellcaster = mob.get('spellcaster', False)
            if is_spellcaster:
                # Initialize mana if not already done
                if mob_id not in self.spellcasting.mob_mana:
                    spell_skill = mob.get('spell_skill', 50)
                    self.spellcasting.initialize_mob_mana(mob_id, mob_level, spell_skill)

                # Decide whether to cast spell or use physical attack
                # 70% chance to cast spell if able, 30% physical attack
                spell_list_type = mob.get('spell_list', 'generic_caster')
                mob_health_percent = mob.get('health', 1) / mob.get('max_health', 1)

                if random.random() < 0.7:
                    # Try to cast a spell
                    chosen_spell = self.spellcasting.choose_spell(mob_id, spell_list_type, mob_level, mob_health_percent)
                    if chosen_spell:
                        # Cast the spell
                        await self.execute_mob_spell(mob, mob_id, chosen_spell, target_player_id, room_id)
                        return  # Spell was cast, done with attack
                # If no spell chosen or 30% physical attack, fall through to physical attack

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
                    # Get effective stats with active_effects bonuses
                    self.strength = CombatSystem.get_effective_stat(char_data, 'strength', 10)
                    self.dexterity = CombatSystem.get_effective_stat(char_data, 'dexterity', 10)
                    self.constitution = CombatSystem.get_effective_stat(char_data, 'constitution', 10)
                    self.intelligence = CombatSystem.get_effective_stat(char_data, 'intellect', 10)
                    self.wisdom = CombatSystem.get_effective_stat(char_data, 'wisdom', 10)
                    self.charisma = CombatSystem.get_effective_stat(char_data, 'charisma', 10)

            temp_mob = TempMob(mob)
            temp_char = TempCharacter(character)

            # Import damage calculator
            from .damage_calculator import DamageCalculator

            # Get player's effective armor class (including buffs)
            player_armor = self.game_engine.command_handler.character_handler.get_effective_armor_class(character)

            # Check attack outcome (miss/dodge/deflect/hit)
            base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)
            outcome = DamageCalculator.check_attack_outcome(temp_mob, temp_char, player_armor, base_hit_chance)

            # Determine weapon description for messages
            equipped_weapon = mob.get('equipped', {}).get('weapon')
            if equipped_weapon:
                weapon_name = equipped_weapon.get('name', 'weapon')
                attack_verb = f"attacks you with their {weapon_name}"
                attack_verb_other = f"attacks {character['name']} with their {weapon_name}"
            else:
                attack_verb = "attacks you"
                attack_verb_other = f"attacks {character['name']}"

            if outcome['result'] == 'miss':
                # Mob missed
                miss_msg = combat_action(f"{mob_name} {attack_verb} but misses!")
                await self.game_engine.connection_manager.send_message(target_player_id, miss_msg)

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{mob_name} {attack_verb_other} but misses!"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

            elif outcome['result'] == 'dodge':
                # Player dodged
                dodge_msg = combat_action(f"You dodge {mob_name}'s attack!")
                await self.game_engine.connection_manager.send_message(target_player_id, dodge_msg)

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{character['name']} dodges {mob_name}'s attack!"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

            elif outcome['result'] == 'deflect':
                # Armor deflected
                deflect_msg = combat_action(f"Your armor deflects {mob_name}'s attack!")
                await self.game_engine.connection_manager.send_message(target_player_id, deflect_msg)

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{character['name']}'s armor deflects {mob_name}'s attack!"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

            else:
                # Hit - calculate damage
                # Check if mob has equipped weapon (for humanoid mobs)
                if equipped_weapon:
                    # Use weapon damage
                    natural_attack = {
                        'damage': equipped_weapon.get('properties', {}).get('damage', '1d4'),
                        'damage_min': 1,
                        'damage_max': 4
                    }
                else:
                    # Use mob's natural attack
                    natural_attack = {
                        'damage': mob.get('damage', '1d4'),
                        'damage_min': mob.get('damage_min', 1),
                        'damage_max': mob.get('damage_max', 4)
                    }
                damage_info = DamageCalculator.calculate_melee_damage(temp_mob, natural_attack=natural_attack)
                damage = damage_info['damage']
                is_critical = damage_info['is_critical']

                # Apply damage
                current_health = character.get('current_hit_points', character.get('max_hit_points', 20))
                new_health = max(0, current_health - damage)
                character['current_hit_points'] = new_health

                # Send attack message to target player
                attack_msg = f"{mob_name} {attack_verb} for {int(damage)} damage"
                if is_critical:
                    attack_msg += " (Critical Hit!)"
                attack_msg += f"! (Health: {int(new_health)})"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    damage_to_player(attack_msg)
                )

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{mob_name} {attack_verb_other} for {int(damage)} damage!"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

                # Check if player died
                if new_health <= 0:
                    death_msg = death_message(f"You have been killed by {mob_name}!")
                    await self.game_engine.connection_manager.send_message(target_player_id, death_msg)

                    # Despawn player's summons on death
                    await self.game_engine.player_manager._despawn_player_summons(target_player_id, character, room_id)

                    # Respawn player (simple respawn logic)
                    max_hp = character.get('max_hit_points', 20)
                    character['current_hit_points'] = max_hp

                    # Get the actual starting room from world manager
                    starting_room_id = self.game_engine.world_manager.get_default_starting_room()
                    if starting_room_id:
                        character['room_id'] = starting_room_id
                    else:
                        # Fallback to inn_entrance if no starting room found
                        character['room_id'] = 'inn_entrance'

                    respawn_msg = "You have respawned in the starting room."
                    await self.game_engine.connection_manager.send_message(target_player_id, respawn_msg)

                    # Send room description after respawn
                    await self.game_engine.world_manager.send_room_description(target_player_id, detailed=False)

        except Exception as e:
            self.logger.error(f"Error in mob attack execution: {e}")

    async def execute_mob_spell(self, mob: dict, mob_id: str, spell_id: str, target_player_id: int, room_id: str):
        """Execute a mob spell cast against a player."""
        try:
            # Get spell definition
            spell = SpellType.get_spell(spell_id)
            if not spell:
                self.logger.error(f"[SPELL] Unknown spell {spell_id} for mob {mob_id}")
                return

            # Use the spell (consumes mana and sets cooldown)
            mob_level = mob.get('level', 1)
            if not self.spellcasting.use_spell(mob_id, spell_id, mob_level):
                self.logger.warning(f"[SPELL] Mob {mob_id} failed to cast {spell_id}")
                return

            # Get target player data
            player_data = self.game_engine.player_manager.connected_players.get(target_player_id)
            if not player_data:
                return

            character = player_data['character']
            mob_name = mob.get('name', 'Unknown Mob')
            spell_name = spell['name']
            damage_type = spell.get('damage_type', 'force')

            # Calculate spell failure chance
            mob_level = mob.get('level', 1)
            mob_intelligence = mob.get('intelligence', 10)
            mob_spell_skill = mob.get('spell_skill', 50)
            spell_min_level = spell.get('min_level', 1)

            failure_chance = self.spellcasting.calculate_spell_failure_chance(
                mob_level, mob_intelligence, spell_min_level, mob_spell_skill
            )

            # Roll for spell failure
            import random
            if random.random() < failure_chance:
                # Spell failed!
                failure_msg = f"{mob_name} attempts to cast {spell_name}, but the spell fizzles and fails!"
                self.logger.info(f"[SPELL] {mob_id} failed to cast {spell_id} ({failure_chance*100:.1f}% failure chance)")

                # Send failure message to target player
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    combat_action(failure_msg)
                )

                # Send failure message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            failure_msg
                        )
                return  # Exit without dealing damage/healing

            # Check if this is a healing spell (target_self)
            if spell.get('target_self', False):
                # Heal the mob
                damage_dice = spell.get('damage', '-2d8')
                damage = abs(self._roll_dice(damage_dice))  # Negative damage = healing

                current_health = mob.get('health', mob.get('max_health', 20))
                max_health = mob.get('max_health', 20)
                new_health = min(max_health, current_health + damage)
                mob['health'] = new_health

                # Format cast message
                cast_msg = spell['cast_message'].format(caster=mob_name, target=mob_name)
                hit_msg = spell['hit_message'].format(caster=mob_name, target=mob_name, damage=int(damage))

                # Send message to target player
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    combat_action(f"{cast_msg} {hit_msg}")
                )

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            f"{cast_msg} {hit_msg}"
                        )
            else:
                # Offensive spell - check if it hits first
                # Create temporary entities for hit calculation
                class TempMob:
                    def __init__(self, mob_data):
                        self.name = mob_data.get('name', 'Unknown')
                        self.level = mob_data.get('level', 1)
                        self.strength = 12
                        self.dexterity = 10
                        self.constitution = 12
                        self.intelligence = mob_data.get('intelligence', 10)
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

                # Get player's effective armor class (including buffs)
                player_armor = self.game_engine.command_handler.character_handler.get_effective_armor_class(character)
                base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)

                # For spells, swap INT for DEX in hit calculation
                saved_dex = temp_mob.dexterity
                temp_mob.dexterity = temp_mob.intelligence  # Use INT for spell accuracy

                # Check spell hit outcome
                outcome = DamageCalculator.check_attack_outcome(temp_mob, temp_char, player_armor, base_hit_chance)

                # Restore original DEX
                temp_mob.dexterity = saved_dex

                cast_msg = spell['cast_message'].format(caster=mob_name, target=character['name'])

                if outcome['result'] == 'miss':
                    # Spell missed
                    miss_msg = f"{cast_msg} The spell misses {character['name']}!"
                    await self.game_engine.connection_manager.send_message(
                        target_player_id,
                        combat_action(miss_msg)
                    )
                    for player_id, pd in self.game_engine.player_manager.connected_players.items():
                        if (player_id != target_player_id and
                            pd.get('character', {}).get('room_id') == room_id):
                            await self.game_engine.connection_manager.send_message(player_id, miss_msg)
                    return

                elif outcome['result'] == 'dodge':
                    # Spell dodged
                    dodge_msg = f"{cast_msg} {character['name']} dodges the spell!"
                    await self.game_engine.connection_manager.send_message(
                        target_player_id,
                        combat_action(dodge_msg)
                    )
                    for player_id, pd in self.game_engine.player_manager.connected_players.items():
                        if (player_id != target_player_id and
                            pd.get('character', {}).get('room_id') == room_id):
                            await self.game_engine.connection_manager.send_message(player_id, dodge_msg)
                    return

                elif outcome['result'] == 'deflect':
                    # Spell deflected
                    deflect_msg = f"{cast_msg} {character['name']}'s defenses deflect the spell!"
                    await self.game_engine.connection_manager.send_message(
                        target_player_id,
                        combat_action(deflect_msg)
                    )
                    for player_id, pd in self.game_engine.player_manager.connected_players.items():
                        if (player_id != target_player_id and
                            pd.get('character', {}).get('room_id') == room_id):
                            await self.game_engine.connection_manager.send_message(player_id, deflect_msg)
                    return

                # Spell hit! Roll damage
                damage_dice = spell.get('damage', '2d6')
                damage = self._roll_dice(damage_dice)

                # Apply damage
                current_health = character.get('current_hit_points', character.get('max_hit_points', 20))
                new_health = max(0, current_health - damage)
                character['current_hit_points'] = new_health

                # Format messages
                hit_msg = spell['hit_message'].format(damage=int(damage), target=character['name'])

                # Send message to target player
                attack_msg = f"{cast_msg} {hit_msg} (Health: {int(new_health)})"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    damage_to_player(attack_msg)
                )

                # Send message to other players in room
                for player_id, pd in self.game_engine.player_manager.connected_players.items():
                    if (player_id != target_player_id and
                        pd.get('character', {}).get('room_id') == room_id):
                        room_msg = f"{cast_msg} {hit_msg}"
                        await self.game_engine.connection_manager.send_message(player_id, room_msg)

                # Check if player died
                if new_health <= 0:
                    death_msg = death_message(f"You have been killed by {mob_name}'s {spell_name}!")
                    await self.game_engine.connection_manager.send_message(target_player_id, death_msg)

                    # Despawn player's summons on death
                    await self.game_engine.player_manager._despawn_player_summons(target_player_id, character, room_id)

                    # Respawn player
                    max_hp = character.get('max_hit_points', 20)
                    character['current_hit_points'] = max_hp

                    # Get the actual starting room from world manager
                    starting_room_id = self.game_engine.world_manager.get_default_starting_room()
                    if starting_room_id:
                        character['room_id'] = starting_room_id
                    else:
                        character['room_id'] = 'inn_entrance'

                    respawn_msg = "You have respawned in the starting room."
                    await self.game_engine.connection_manager.send_message(target_player_id, respawn_msg)

                    # Send room description after respawn
                    await self.game_engine.world_manager.send_room_description(target_player_id, detailed=False)

        except Exception as e:
            self.logger.error(f"Error in mob spell execution: {e}")
            import traceback
            self.logger.error(f"[SPELL] Traceback: {traceback.format_exc()}")

    def _roll_dice(self, dice_str: str) -> int:
        """Roll dice from string notation like '2d6+3'."""
        try:
            # Parse dice notation
            if 'd' not in dice_str:
                return int(dice_str)

            # Handle negative dice (for healing)
            is_negative = dice_str.startswith('-')
            if is_negative:
                dice_str = dice_str[1:]

            parts = dice_str.split('d')
            num_dice = int(parts[0]) if parts[0] else 1

            # Handle modifiers
            if '+' in parts[1]:
                die_size, modifier = parts[1].split('+')
                die_size = int(die_size)
                modifier = int(modifier)
            elif '-' in parts[1]:
                die_size, modifier = parts[1].split('-')
                die_size = int(die_size)
                modifier = -int(modifier)
            else:
                die_size = int(parts[1])
                modifier = 0

            total = sum(random.randint(1, die_size) for _ in range(num_dice))
            result = total + modifier

            return -result if is_negative else result
        except:
            return 0

    async def execute_mob_vs_mob_attack(self, attacker: dict, attacker_id: str, target: dict, room_id: str):
        """Execute a mob vs mob attack."""
        try:
            # Use mob attack
            attacker_level = attacker.get('level', 1)
            if not self.use_mob_attack(attacker_id, attacker_level):
                return

            attacker_name = attacker.get('name', 'Unknown Mob')
            target_name = target.get('name', 'Unknown Mob')

            # Create temp entities for attack calculation
            class TempMob:
                def __init__(self, mob_data):
                    self.name = mob_data.get('name', 'Unknown')
                    self.level = mob_data.get('level', 1)
                    self.strength = mob_data.get('strength', 12)
                    self.dexterity = mob_data.get('dexterity', 10)
                    self.constitution = mob_data.get('constitution', 12)
                    self.intelligence = mob_data.get('intelligence', 8)
                    self.wisdom = mob_data.get('wisdom', 10)
                    self.charisma = mob_data.get('charisma', 6)

            temp_attacker = TempMob(attacker)
            temp_target = TempMob(target)

            # Import damage calculator
            from .damage_calculator import DamageCalculator

            # Get target's armor class
            target_armor = target.get('armor_class', 0)

            # Check attack outcome
            base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)
            outcome = DamageCalculator.check_attack_outcome(temp_attacker, temp_target, target_armor, base_hit_chance)

            if outcome['result'] == 'miss':
                # Attacker missed
                await self._notify_room_players(room_id, f"{attacker_name} attacks {target_name} but misses!")

            elif outcome['result'] == 'dodge':
                # Target dodged
                await self._notify_room_players(room_id, f"{target_name} dodges {attacker_name}'s attack!")

            elif outcome['result'] == 'deflect':
                # Armor deflected
                await self._notify_room_players(room_id, f"{target_name}'s tough hide deflects {attacker_name}'s attack!")

            else:
                # Hit - calculate damage
                natural_attack = {
                    'damage': attacker.get('damage'),
                    'damage_min': attacker.get('damage_min', 1),
                    'damage_max': attacker.get('damage_max', 4)
                }
                damage_info = DamageCalculator.calculate_melee_damage(temp_attacker, natural_attack=natural_attack)
                damage = damage_info['damage']
                is_critical = damage_info['is_critical']

                # Apply damage
                current_health = target.get('health', 100)
                new_health = max(0, current_health - damage)
                target['health'] = new_health

                # Send attack message to room
                attack_msg = f"{attacker_name} attacks {target_name} for {int(damage)} damage"
                if is_critical:
                    attack_msg += " (Critical Hit!)"
                attack_msg += "!"
                await self._notify_room_players(room_id, attack_msg)

                # Check if target died
                if new_health <= 0:
                    # Award XP to attacking mob
                    xp_reward = target.get('experience_reward', 25)
                    if 'experience' not in attacker:
                        attacker['experience'] = 0
                    attacker['experience'] += xp_reward

                    # Award gold to attacking mob
                    gold_reward = target.get('gold_reward', [0, 5])
                    if isinstance(gold_reward, list) and len(gold_reward) == 2:
                        gold_amount = random.randint(gold_reward[0], gold_reward[1])
                    else:
                        gold_amount = gold_reward if isinstance(gold_reward, int) else 0

                    if gold_amount > 0:
                        if 'gold' not in attacker:
                            attacker['gold'] = 0
                        attacker['gold'] += gold_amount

                        # Notify players in room about the loot
                        await self._notify_room_players(room_id, f"{attacker_name} loots {gold_amount} gold from {target_name}'s corpse!")

                    # Notify room of death
                    death_msg = f"{target_name} has been slain by {attacker_name}!"
                    await self._notify_room_players(room_id, death_msg)

                    # Remove dead mob from room (don't use handle_mob_death as it awards XP to players)
                    if room_id in self.game_engine.room_mobs:
                        alive_mobs = []
                        for mob in self.game_engine.room_mobs[room_id]:
                            if mob != target:
                                alive_mobs.append(mob)
                        self.game_engine.room_mobs[room_id] = alive_mobs

                        # If this was a lair mob, start respawn timer
                        if target.get('is_lair_mob'):
                            import time
                            room = self.game_engine.world_manager.get_room(room_id)
                            if room and hasattr(room, 'respawn_time'):
                                respawn_time = room.respawn_time
                                self.game_engine.lair_timers[room_id] = time.time() + respawn_time
                                self.logger.info(f"[LAIR] {target.get('id')} killed by mob, respawn in {respawn_time}s")

        except Exception as e:
            self.logger.error(f"Error in mob vs mob attack execution: {e}")

    async def _notify_room_players(self, room_id: str, message: str):
        """Send a message to all players in a room."""
        for player_id, player_data in self.game_engine.player_manager.connected_players.items():
            if not player_data:
                continue
            character = player_data.get('character')
            if character and character.get('room_id') == room_id:
                await self.game_engine.connection_manager.send_message(player_id, message)

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
                # Get effective stats with active_effects bonuses
                self.strength = CombatSystem.get_effective_stat(char_data, 'strength', 10)
                self.dexterity = CombatSystem.get_effective_stat(char_data, 'dexterity', 10)
                self.constitution = CombatSystem.get_effective_stat(char_data, 'constitution', 10)
                self.intelligence = CombatSystem.get_effective_stat(char_data, 'intellect', 10)
                self.wisdom = CombatSystem.get_effective_stat(char_data, 'wisdom', 10)
                self.charisma = CombatSystem.get_effective_stat(char_data, 'charisma', 10)

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
        base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)
        outcome = DamageCalculator.check_attack_outcome(temp_char, temp_mob, mob_armor, base_hit_chance)

        if outcome['result'] == 'miss':
            # Miss
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"You miss {target_name}!")
            )
            await self.broadcast_to_room(room_id, combat_action(f"{character['name']} misses {target_name}!"), exclude_player=player_id)
        elif outcome['result'] == 'dodge':
            # Dodged
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"{target_name} dodges your attack!")
            )
            await self.broadcast_to_room(room_id, combat_action(f"{target_name} dodges {character['name']}'s attack!"), exclude_player=player_id)
        elif outcome['result'] == 'deflect':
            # Deflected by armor
            await self.game_engine.connection_manager.send_message(
                player_id,
                combat_action(f"Your attack is deflected by {target_name}'s armor!")
            )
            await self.broadcast_to_room(room_id, combat_action(f"{character['name']}'s attack is deflected by {target_name}'s armor!"), exclude_player=player_id)
        else:
            # Hit - calculate damage with equipped weapon
            equipped_weapon = character.get('equipped', {}).get('weapon')

            # Check if using ranged weapon in melee (applies penalty)
            is_ranged_weapon = False
            if equipped_weapon:
                is_ranged_weapon = equipped_weapon.get('properties', {}).get('ranged', False)

            # Get critical multiplier (may be enhanced by class abilities)
            crit_multiplier = self.get_critical_multiplier(character)

            damage_info = DamageCalculator.calculate_melee_damage(temp_char, equipped_weapon, crit_multiplier=crit_multiplier)
            damage = damage_info['damage']
            is_critical = damage_info['is_critical']

            # Check for active ability damage modifiers
            active_abilities = character.get('active_abilities', {})

            # Backstab (Rogue)
            if 'backstab' in active_abilities:
                backstab_data = active_abilities['backstab']
                backstab_mult = backstab_data.get('damage_multiplier', 1.0)
                damage = int(damage * backstab_mult)

                # Consume one charge
                backstab_data['attacks_remaining'] = backstab_data.get('attacks_remaining', 1) - 1
                if backstab_data['attacks_remaining'] <= 0:
                    active_abilities.pop('backstab')

            # Power Attack (Fighter)
            if 'power_attack' in active_abilities:
                power_data = active_abilities['power_attack']
                power_mult = power_data.get('damage_multiplier', 1.0)
                damage = int(damage * power_mult)

                # Consume one charge
                power_data['attacks_remaining'] = power_data.get('attacks_remaining', 1) - 1
                if power_data['attacks_remaining'] <= 0:
                    active_abilities.pop('power_attack')

            # Cleave (Fighter AoE)
            if 'cleave' in active_abilities:
                cleave_data = active_abilities['cleave']
                cleave_mult = cleave_data.get('damage_multiplier', 1.0)
                damage = int(damage * cleave_mult)

                # Consume one charge
                cleave_data['attacks_remaining'] = cleave_data.get('attacks_remaining', 1) - 1
                if cleave_data['attacks_remaining'] <= 0:
                    active_abilities.pop('cleave')

            # Battle Cry (Fighter buff)
            if 'battle_cry' in active_abilities:
                cry_data = active_abilities['battle_cry']
                end_time = cry_data.get('end_time', 0)
                if time.time() < end_time:
                    # Still active
                    damage_bonus = cry_data.get('damage_bonus', 0)
                    damage = int(damage * (1.0 + damage_bonus))
                else:
                    # Expired
                    active_abilities.pop('battle_cry')

            # Apply ranged weapon melee penalty (half damage)
            if is_ranged_weapon:
                damage = max(1, damage // 2)

            # Apply damage to target
            target['health'] = max(0, target['health'] - damage)
            target_alive = target['health'] > 0

            # Track damage dealt for XP calculation
            mob_id = self.get_mob_identifier(target)
            if mob_id not in self.mob_damage_tracking:
                self.mob_damage_tracking[mob_id] = {}

            previous_damage = self.mob_damage_tracking[mob_id].get(player_id, 0)
            self.mob_damage_tracking[mob_id][player_id] = previous_damage + damage

            # Award XP based on damage dealt with level scaling
            player_level = character.get('level', 1)
            mob_level = target.get('level', 1)
            mob_max_hp = target.get('max_health', 100)

            # Calculate XP earned, capping at mob's max HP
            # Don't award XP for overkill damage beyond the mob's max HP
            total_damage_dealt = self.mob_damage_tracking[mob_id][player_id]

            # Determine how much of this damage counts toward XP
            countable_damage = damage
            if total_damage_dealt > mob_max_hp:
                # Overkill - only count damage up to max HP
                countable_damage = damage - (total_damage_dealt - mob_max_hp)
                countable_damage = max(0, countable_damage)

            # Calculate XP for the countable damage
            xp_earned = self.calculate_damage_xp(countable_damage, player_level, mob_level)

            # Award XP
            if xp_earned > 0:
                character['experience'] = character.get('experience', 0) + xp_earned

            # Build attack message
            hit_msg = f"You attack {target_name} for {damage} damage"
            if is_critical:
                hit_msg += " (Critical Hit!)"
            if xp_earned > 0:
                hit_msg += f" (+{xp_earned} XP)"
            hit_msg += "!"

            await self.game_engine.connection_manager.send_message(player_id, damage_to_enemy(hit_msg))
            await self.broadcast_to_room(
                room_id,
                combat_action(f"{character['name']} attacks {target_name} for {damage} damage!"),
                exclude_player=player_id
            )

            # Check if target died
            if not target_alive:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    announcement(f"{target_name} has been defeated!")
                )
                await self.broadcast_to_room(
                    room_id,
                    announcement(f"{target_name} has been defeated!"),
                    exclude_player=player_id
                )

                # Award gold and loot (XP already awarded per damage)
                await self.handle_mob_loot_drop(player_id, target, room_id)

                # Clean up damage tracking for this mob
                if mob_id in self.mob_damage_tracking:
                    del self.mob_damage_tracking[mob_id]

                # Check quest progress for killing this mob (seamless combat)
                dead_mob_id = target.get('id')
                if dead_mob_id:
                    player_quests = character.get('quests', {})
                    self.logger.info(f"[QUEST] Player killed {dead_mob_id} in {room_id} (seamless), checking {len(player_quests)} quests")
                    for quest_id in player_quests:
                        # Skip completed quests
                        quest_status = player_quests[quest_id]
                        if quest_status.get('completed'):
                            self.logger.info(f"[QUEST] Skipping {quest_id} - already completed")
                            continue

                        self.logger.info(f"[QUEST] Checking {quest_id} for kill_monster objective: {dead_mob_id}")
                        quest_completed = self.game_engine.quest_manager.check_objective_completion(
                            character,
                            quest_id,
                            'kill_monster',
                            dead_mob_id,
                            room_id
                        )

                        if quest_completed:
                            quest = self.game_engine.quest_manager.get_quest(quest_id)
                            if quest:
                                completion_msg = quest.get('completed_message', 'Quest objective completed!')
                                await self.game_engine.connection_manager.send_message(player_id, f"\n{completion_msg}\n")

                # Handle mob death (removes from room)
                mob_participant_id = self.get_mob_identifier(target)
                await self.handle_mob_death(room_id, mob_participant_id)
            else:
                # Mob survived - set/update aggro on the attacker (for melee attacks in same room)
                if 'aggro_target' not in target:
                    target['aggro_target'] = player_id
                    target['aggro_room'] = room_id
                    self.logger.debug(f"[AGGRO] {target_name} is now aggro'd on player {player_id} in room {room_id}")
                # Update aggro timestamp if this is the current aggro target
                if target.get('aggro_target') == player_id:
                    target['aggro_last_attack'] = time.time()

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
        """Handle gold and loot drops when a mob is defeated.

        Note: XP is now awarded per damage dealt, not on kill.

        Args:
            player_id: The player who defeated the mob (0 if no player)
            mob: The mob dict with loot data
            room_id: The room where the mob was defeated
        """
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        player_online = player_data is not None and player_data.get('character') is not None

        # Only award XP and gold if player is online
        if player_online:
            character = player_data['character']

            # Award bonus XP if mob had accumulated experience from victories
            accumulated_exp = mob.get('experience', 0)
            if accumulated_exp > 0:
                character['experience'] = character.get('experience', 0) + accumulated_exp
                from ...utils.colors import service_message
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    service_message(f"You gain {accumulated_exp} bonus XP from the {mob.get('name', 'creature')}'s victories!")
                )

            # Award gold (base + accumulated from mob vs mob combat)
            gold_reward = mob.get('gold_reward', [0, 5])
            if isinstance(gold_reward, list) and len(gold_reward) == 2:
                base_gold = random.randint(gold_reward[0], gold_reward[1])
            else:
                base_gold = gold_reward if isinstance(gold_reward, int) else 0

            accumulated_gold = mob.get('gold', 0)
            total_gold = base_gold + accumulated_gold

            if total_gold > 0:
                # Get party members in the same room for gold sharing
                party_leader_id = character.get('party_leader', player_id)

                # Get leader's character to access party_members list
                if party_leader_id == player_id:
                    leader_char = character
                else:
                    leader_player_data = self.game_engine.player_manager.connected_players.get(party_leader_id)
                    leader_char = leader_player_data.get('character') if leader_player_data else None

                # Get all party members in the same room
                party_members_in_room = []
                if leader_char:
                    party_members = leader_char.get('party_members', [party_leader_id])
                    for member_id in party_members:
                        member_player_data = self.game_engine.player_manager.connected_players.get(member_id)
                        if member_player_data and member_player_data.get('character'):
                            member_char = member_player_data['character']
                            if member_char.get('room_id') == room_id:
                                party_members_in_room.append({
                                    'player_id': member_id,
                                    'character': member_char,
                                    'name': member_char.get('name', 'Unknown')
                                })

                # If no party members in room, just give to killer
                if not party_members_in_room:
                    party_members_in_room = [{'player_id': player_id, 'character': character, 'name': character.get('name', 'Unknown')}]

                # Split gold among party members (minimum 1 gold each)
                num_members = len(party_members_in_room)
                gold_per_member = max(1, total_gold // num_members)

                from ...utils.colors import item_found

                # Distribute gold to each party member
                for member_info in party_members_in_room:
                    member_id = member_info['player_id']
                    member_char = member_info['character']
                    member_name = member_info['name']

                    member_char['gold'] = member_char.get('gold', 0) + gold_per_member

                    # Update encumbrance for gold weight change
                    self.game_engine.player_manager.update_encumbrance(member_char)

                    # Send notification
                    if num_members > 1:
                        # Party split message
                        if accumulated_gold > 0:
                            await self.game_engine.connection_manager.send_message(
                                member_id,
                                item_found(f"Your party loots {total_gold} gold (+{accumulated_gold} from hoard). Your share: {gold_per_member} gold")
                            )
                        else:
                            await self.game_engine.connection_manager.send_message(
                                member_id,
                                item_found(f"Your party loots {total_gold} gold. Your share: {gold_per_member} gold")
                            )
                    else:
                        # Solo loot message
                        if accumulated_gold > 0:
                            await self.game_engine.connection_manager.send_message(
                                member_id,
                                item_found(f"You loot {base_gold} gold (+{accumulated_gold} from the {mob.get('name', 'creature')}'s hoard)! Total: {total_gold} gold")
                            )
                        else:
                            await self.game_engine.connection_manager.send_message(
                                member_id,
                                item_found(f"You loot {total_gold} gold!")
                            )

        # Process loot drops (lair loot, loot table, and equipped items)
        # These always drop in the room regardless of whether player is online
        dropped_items = []

        # Check if this is a lair mob and room has lair loot
        room_data = self.game_engine.world_manager.rooms_data.get(room_id)
        is_lair_mob = not mob.get('is_wandering', False)

        if is_lair_mob and room_data and 'lair_loot' in room_data:
            lair_loot = room_data.get('lair_loot', [])
            print(f"[LOOT DEBUG] Processing lair loot for lair mob '{mob.get('name')}': {lair_loot}")

            for item_id in lair_loot:
                # Get item data from world loader
                item_data = self.game_engine.world_manager.items.get(item_id)
                print(f"[LOOT DEBUG] Lair loot item data for '{item_id}': {item_data}")

                if item_data:
                    # Create a copy of the item to drop in the room
                    dropped_item = item_data.copy()

                    # Ensure 'value' is set from 'base_value' for selling
                    if 'base_value' in dropped_item and 'value' not in dropped_item:
                        dropped_item['value'] = dropped_item['base_value']

                    self.game_engine.item_manager.add_item_to_room(room_id, dropped_item)
                    dropped_items.append(dropped_item['name'])
                    print(f"[LOOT DEBUG] Dropped lair loot item '{dropped_item['name']}' in room '{room_id}'")
                else:
                    print(f"[LOOT DEBUG] WARNING: Lair loot item '{item_id}' not found in world_manager.items!")

        loot_table = mob.get('loot_table', [])
        print(f"[LOOT DEBUG] Mob '{mob.get('name')}' loot_table: {loot_table}")

        # Drop equipped items first (weapons and armor)
        equipped = mob.get('equipped', {})
        if equipped:
            # Drop equipped weapon
            if 'weapon' in equipped:
                weapon = equipped['weapon']
                # Ensure 'value' is set from 'base_value' for selling
                if 'base_value' in weapon and 'value' not in weapon:
                    weapon['value'] = weapon['base_value']
                self.game_engine.item_manager.add_item_to_room(room_id, weapon)
                dropped_items.append(weapon['name'])
                print(f"[LOOT DEBUG] Dropped equipped weapon '{weapon['name']}' in room '{room_id}'")

            # Drop equipped armor
            if 'armor' in equipped:
                armor = equipped['armor']
                # Ensure 'value' is set from 'base_value' for selling
                if 'base_value' in armor and 'value' not in armor:
                    armor['value'] = armor['base_value']
                self.game_engine.item_manager.add_item_to_room(room_id, armor)
                dropped_items.append(armor['name'])
                print(f"[LOOT DEBUG] Dropped equipped armor '{armor['name']}' in room '{room_id}'")

        # Process loot table
        if loot_table:
            for loot_entry in loot_table:
                item_id = loot_entry.get('item_id')
                drop_chance = loot_entry.get('chance', 0.0)

                print(f"[LOOT DEBUG] Processing loot entry: item_id={item_id}, chance={drop_chance}")

                # Roll for drop
                roll = random.random()
                print(f"[LOOT DEBUG] Roll: {roll:.3f} vs chance: {drop_chance:.3f}")

                if roll < drop_chance:
                    # Get item data from world loader
                    item_data = self.game_engine.world_manager.items.get(item_id)
                    print(f"[LOOT DEBUG] Item data for '{item_id}': {item_data}")

                    if item_data:
                        # Create a copy of the item to drop in the room
                        dropped_item = item_data.copy()

                        # Ensure 'value' is set from 'base_value' for selling
                        if 'base_value' in dropped_item and 'value' not in dropped_item:
                            dropped_item['value'] = dropped_item['base_value']

                        self.game_engine.item_manager.add_item_to_room(room_id, dropped_item)
                        dropped_items.append(dropped_item['name'])
                        print(f"[LOOT DEBUG] Dropped item '{dropped_item['name']}' in room '{room_id}'")
                    else:
                        print(f"[LOOT DEBUG] WARNING: Item '{item_id}' not found in world_manager.items!")
                else:
                    print(f"[LOOT DEBUG] Item '{item_id}' did not drop (roll failed)")
        else:
            print(f"[LOOT DEBUG] Mob has no loot_table defined")

        # Notify player about all drops
        if dropped_items:
            from ...utils.colors import item_found
            if len(dropped_items) == 1:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    item_found(f"{mob.get('name', 'The mob')} dropped {dropped_items[0]}!")
                )
            else:
                items_str = ", ".join(dropped_items[:-1]) + f" and {dropped_items[-1]}"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    item_found(f"{mob.get('name', 'The mob')} dropped {items_str}!")
                )
        else:
            print(f"[LOOT DEBUG] No items were dropped from this mob")