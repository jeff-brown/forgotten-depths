"""Async game engine that coordinates all game systems."""

import asyncio
import random
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any

from ..networking.async_connection_manager import AsyncConnectionManager
from ..game.world.world_manager import WorldManager
from ..game.world.barrier_system import BarrierSystem
from .event_system import EventSystem
from ..commands.command_handler import CommandHandler
from ..game.vendors.vendor_system import VendorSystem
from ..game.combat.combat_system import CombatSystem
from ..game.items.item_manager import ItemManager
from ..game.player.player_manager import PlayerManager
from ..persistence.database import Database
from ..persistence.player_storage import PlayerStorage
from ..config.config_manager import ConfigManager
from ..utils.logger import get_logger
from ..game.npcs.mob import Mob
from ..game.quests.quest_manager import QuestManager
from ..game.traps.trap_system import TrapSystem
from ..game.abilities.class_ability_system import ClassAbilitySystem
from shared.constants.game_constants import GAME_TICK_RATE


class AsyncGameEngine:
    """Async game engine that manages all game systems and coordinates updates."""

    def __init__(self):
        """Initialize the game engine."""
        self.logger = get_logger()
        self.running = False
        self.tick_rate = GAME_TICK_RATE

        # Core systems
        self.event_system = EventSystem()
        self.connection_manager = AsyncConnectionManager()
        self.world_manager = WorldManager(self)
        self.config_manager = ConfigManager()
        self.barrier_system = BarrierSystem(self.world_manager, self.connection_manager)
        self.barrier_system.game_engine = self  # Set game_engine reference for room notifications
        self.command_handler = CommandHandler(self)
        self.vendor_system = VendorSystem(self)
        self.combat_system = CombatSystem(self)
        self.item_manager = ItemManager(self)
        self.player_manager = PlayerManager(self)
        self.quest_manager = QuestManager(self)
        self.trap_system = TrapSystem(self)
        self.ability_system = ClassAbilitySystem(self)

        # Database and persistence
        self.database: Optional[Database] = None
        self.player_storage: Optional[PlayerStorage] = None


        # Cached game data (loaded once at initialization)
        self.monsters_data: Dict[str, Any] = {}  # Cached monster definitions

        # Room mob management - tracks spawned mobs in each room
        self.room_mobs: Dict[str, list] = {}

        # Lair management - tracks respawn timers for lair rooms
        self.lair_timers: Dict[str, float] = {}  # room_id -> time when mob should respawn

        # Wandering mob management
        self.last_wandering_spawn_check = time.time()

        # Arena gong cooldowns - tracks last gong use per room
        self.gong_cooldowns: Dict[str, float] = {}  # room_id -> timestamp of last gong use

        # Combat management - tracks active combat encounters
        self.active_combats: Dict[str, AsyncCombat] = {}  # room_id -> AsyncCombat
        self.player_combats: Dict[int, str] = {}     # player_id -> room_id with active combat
        self.player_fatigue: Dict[int, Dict[str, Any]] = {}  # player_id -> physical fatigue info
        self.mob_fatigue: Dict[str, Dict[str, Any]] = {}     # mob_id -> fatigue info
        self.spell_fatigue: Dict[int, Dict[str, Any]] = {}   # player_id -> spell fatigue info

        # Note: Vendor management now handled by VendorSystem

        # Background tasks
        self.game_loop_task: Optional[asyncio.Task] = None
        self.last_auto_save = time.time()
        self.auto_save_interval = 60.0  # Auto-save every 60 seconds

        # Setup system connections
        self._setup_connections()

    def _setup_connections(self):
        """Setup connections between systems."""
        # Connect connection manager to game events
        self.connection_manager.on_player_connect = self.player_manager.handle_player_connect
        self.connection_manager.on_player_disconnect = self.player_manager.handle_player_disconnect
        self.connection_manager.on_player_command = self.command_handler.handle_player_command

        # Subscribe to events
        self.event_system.subscribe('player_connected', self.player_manager.on_player_connected)
        self.event_system.subscribe('player_disconnected', self.player_manager.on_player_disconnected)
        self.event_system.subscribe('player_command', self.player_manager.on_player_command)

    def _load_all_monsters(self) -> Dict[str, Any]:
        """Load all monsters from type-specific JSON files.

        Returns:
            Dictionary mapping monster IDs to monster data
        """
        from pathlib import Path

        monsters = {}
        mobs_dir = Path("data/mobs")

        # Load monsters from type-specific files
        if mobs_dir.exists():
            for monster_file in mobs_dir.glob("*.json"):
                try:
                    with open(monster_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        type_monsters = config.get('monsters', [])
                        for monster in type_monsters:
                            monsters[monster['id']] = monster
                except Exception as e:
                    self.logger.error(f"Failed to load monsters from {monster_file}: {e}")

        # Fallback to legacy monsters.json if no type files found
        if not monsters:
            legacy_file = Path("data/npcs/monsters.json")
            if legacy_file.exists():
                try:
                    with open(legacy_file, 'r', encoding='utf-8') as f:
                        monsters_data = json.load(f)
                        monsters = {m['id']: m for m in monsters_data}
                except Exception as e:
                    self.logger.error(f"Failed to load monsters from {legacy_file}: {e}")

        return monsters

    def initialize_database(self, database: Database):
        """Initialize database connection."""
        self.database = database
        self.player_storage = PlayerStorage(database)
        self.logger.info("Database initialized")

    async def start(self, host: str = "localhost", port: int = 4000):
        """Start the async game engine."""
        if self.running:
            self.logger.warning("Game engine is already running")
            return

        self.running = True
        self.logger.info("Starting async game engine")

        try:
            # Initialize world
            self.world_manager.load_world()

            # Load monsters data once (cached for later use)
            self.logger.info("Loading world data...")
            self.monsters_data = self._load_all_monsters()
            self.logger.info(f"Loaded {len(self.monsters_data)} monster definitions")

            # Initialize lair spawns
            self._initialize_lairs()

            # Load vendor and item data
            self.vendor_system.load_vendors_and_items()

            # Start connection manager
            self.connection_manager.initialize(host, port, self.event_system)

            # Start background tasks
            self.game_loop_task = asyncio.create_task(self._game_loop())

            # Start the server (this will run until stopped)
            await self.connection_manager.start_server(host, port)

        except asyncio.CancelledError:
            self.logger.info("Game engine cancelled")
        except Exception as e:
            self.logger.error(f"Game engine error: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self):
        """Stop the game engine."""
        if not self.running:
            return

        self.logger.info("Stopping async game engine")
        self.running = False

        # Save all player data FIRST (before canceling anything)
        try:
            if self.database and self.database.connection:
                self.logger.info("Saving all players before shutdown...")
                self.player_manager.save_all_players()
                self.logger.info("All players saved")
        except Exception as e:
            self.logger.error(f"Error saving players during shutdown: {e}")

        # Cancel game loop
        if self.game_loop_task:
            self.game_loop_task.cancel()
            try:
                await self.game_loop_task
            except asyncio.CancelledError:
                pass

        # Stop connection manager (this will trigger player disconnects which save characters)
        await self.connection_manager.stop_server()

        # Give a moment for any pending disconnect saves to complete
        await asyncio.sleep(0.1)

        # Disconnect database LAST (after all saves are complete)
        if self.database:
            try:
                self.database.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting database: {e}")

    async def _game_loop(self):
        """Main async game loop."""
        last_tick = time.time()

        try:
            while self.running:
                current_time = time.time()

                # Check if it's time for a tick
                if current_time - last_tick >= self.tick_rate:
                    await self.tick()
                    last_tick = current_time

                # Sleep to prevent busy waiting
                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            self.logger.info("Game loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in game loop: {e}")

    async def tick(self):
        """Process one async game tick."""
        try:
            # Update world
            await self.world_manager.update_world()

            # Update NPCs, combat, etc.
            await self._update_npcs()
            await self._update_combat()

            # Check lair respawns
            await self._check_lair_respawns()

            # Check wandering mob spawns
            await self._check_wandering_mob_spawns()

            # Move wandering mobs
            try:
                await self._move_wandering_mobs()
            except Exception as e:
                self.logger.error(f"Error moving wandering mobs: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

            # Regenerate health and mana
            await self._regenerate_players()
            await self._regenerate_mobs()

            # Update spell cooldowns
            await self._update_spell_cooldowns()

            # Update light sources (burning)
            await self._update_light_sources()

            # Update trap effects (poison, burning)
            await self.trap_system.update_trap_effects()

            # Update active buffs/effects
            await self._update_active_effects()

            # Update poison DOT effects
            await self._update_poison_effects()

            # Replenish vendor stock (every 5 minutes)
            await self.vendor_system.replenish_vendor_stock()

            # Auto-save check
            current_time = time.time()
            if current_time - self.last_auto_save >= self.auto_save_interval:
                await self._auto_save_players()
                self.last_auto_save = current_time

        except Exception as e:
            self.logger.error(f"Error in game tick: {e}")

    async def _update_npcs(self):
        """Update all NPCs asynchronously."""
        await self.combat_system.process_mob_ai()

    async def _update_combat(self):
        """Update combat encounters asynchronously."""
        # This would handle ongoing combat
        # For now, just a placeholder
        pass

    async def _regenerate_players(self):
        """Regenerate health and mana for all players."""
        for player_id, player_data in self.player_manager.connected_players.items():
            character = player_data.get('character')
            if not character:
                continue

            # Get stats
            constitution = character.get('constitution', 10)
            intellect = character.get('intellect', 10)

            # Get current and max values
            current_health = character.get('current_hit_points', 0)
            max_health = character.get('max_hit_points', 100)
            current_mana = character.get('current_mana', 0)
            max_mana = character.get('max_mana', 50)

            # Hunger and thirst decay (configurable from game_settings.yaml)
            hunger_decay = self.config_manager.get_setting('player', 'hunger_thirst', 'hunger_decay_per_tick', default=0.05)
            thirst_decay = self.config_manager.get_setting('player', 'hunger_thirst', 'thirst_decay_per_tick', default=0.075)

            hunger = character.get('hunger', 100)
            thirst = character.get('thirst', 100)

            hunger = max(0, hunger - hunger_decay)
            thirst = max(0, thirst - thirst_decay)

            character['hunger'] = hunger
            character['thirst'] = thirst

            # Track warning states with timestamps
            if 'warning_timestamps' not in character:
                character['warning_timestamps'] = {}

            warnings = character['warning_timestamps']
            current_time = time.time()

            # Get damage and warning settings from config
            starvation_damage = self.config_manager.get_setting('player', 'hunger_thirst', 'starvation_damage_per_tick', default=0.5)
            dehydration_damage = self.config_manager.get_setting('player', 'hunger_thirst', 'dehydration_damage_per_tick', default=1.0)
            low_threshold = self.config_manager.get_setting('player', 'hunger_thirst', 'low_warning_threshold', default=20)

            # Apply hunger/thirst damage with tiered severity
            damage_taken = 0

            # Hunger damage - tiered based on severity
            if hunger <= 0:
                # Starving (0): Full damage
                damage_taken += starvation_damage
                # Remind player every 60 seconds
                last_starving_warning = warnings.get('starving', 0)
                if current_time - last_starving_warning >= 60:
                    await self.connection_manager.send_message(player_id, "You are starving! Find food soon!")
                    warnings['starving'] = current_time
            elif hunger <= 5:
                # Very hungry (1-5): 75% damage
                damage_taken += starvation_damage * 0.75
                warnings['starving'] = 0
            elif hunger <= 10:
                # Hungry (6-10): 50% damage
                damage_taken += starvation_damage * 0.5
                warnings['starving'] = 0
            elif hunger <= 15:
                # Getting hungry (11-15): 25% damage
                damage_taken += starvation_damage * 0.25
                warnings['starving'] = 0
            else:
                # Reset timestamp when hunger is healthy
                warnings['starving'] = 0

            # Thirst damage - tiered based on severity (more dangerous than hunger)
            if thirst <= 0:
                # Dehydrated (0): Full damage
                damage_taken += dehydration_damage
                # Remind player every 60 seconds
                last_dehydrated_warning = warnings.get('dehydrated', 0)
                if current_time - last_dehydrated_warning >= 60:
                    await self.connection_manager.send_message(player_id, "You are severely dehydrated! Find water immediately!")
                    warnings['dehydrated'] = current_time
            elif thirst <= 5:
                # Very thirsty (1-5): 75% damage
                damage_taken += dehydration_damage * 0.75
                warnings['dehydrated'] = 0
            elif thirst <= 10:
                # Thirsty (6-10): 50% damage
                damage_taken += dehydration_damage * 0.5
                warnings['dehydrated'] = 0
            elif thirst <= 15:
                # Getting thirsty (11-15): 25% damage
                damage_taken += dehydration_damage * 0.25
                warnings['dehydrated'] = 0
            else:
                # Reset timestamp when thirst is healthy
                warnings['dehydrated'] = 0

            # Warnings at low levels (much less frequent - 0.5% = ~1 warning per 200 ticks = ~3 mins)
            if thirst <= low_threshold and thirst > 0:
                if random.random() < 0.005:
                    await self.connection_manager.send_message(player_id, "You are very thirsty.")

            if hunger <= low_threshold and hunger > 0:
                if random.random() < 0.005:
                    await self.connection_manager.send_message(player_id, "You are very hungry.")

            # Apply damage (but can't die from hunger/thirst - minimum 1 HP)
            if damage_taken > 0:
                character['current_hit_points'] = max(1, current_health - damage_taken)

            # Calculate regen amounts
            # Health regen: CON / 50 per tick (e.g., 15 CON = 0.3 HP/tick = 18 HP/min)
            health_regen = constitution / 50.0
            # Mana regen: INT / 40 per tick (e.g., 16 INT = 0.4 mana/tick = 24 mana/min)
            mana_regen = intellect / 40.0

            # Apply regeneration (only if not starving/dehydrated)
            if current_health < max_health and hunger > 0 and thirst > 0:
                new_health = min(current_health + health_regen, max_health)
                character['current_hit_points'] = new_health

            if current_mana < max_mana:
                new_mana = min(current_mana + mana_regen, max_mana)
                character['current_mana'] = new_mana

    async def _regenerate_mobs(self):
        """Regenerate health and mana for all mobs."""
        for room_id, mobs in self.room_mobs.items():
            for mob in mobs:
                if not isinstance(mob, dict):
                    continue

                # Get mob stats
                constitution = mob.get('constitution', 10)

                # Get current and max health
                current_health = mob.get('health', 0)
                max_health = mob.get('max_health', 100)

                # Calculate regen: CON / 50 per tick (same as players)
                health_regen = constitution / 50.0

                # Apply health regeneration
                if current_health < max_health and current_health > 0:
                    new_health = min(current_health + health_regen, max_health)
                    mob['health'] = new_health

                # Regenerate mana for spellcasters
                if mob.get('spellcaster', False):
                    mob_id = mob.get('id', f"{mob.get('name', 'unknown')}_{room_id}")
                    # Initialize mana if needed
                    if mob_id not in self.combat_system.spellcasting.mob_mana:
                        mob_level = mob.get('level', 1)
                        spell_skill = mob.get('spell_skill', 50)
                        self.combat_system.spellcasting.initialize_mob_mana(mob_id, mob_level, spell_skill)
                    # Regenerate mana
                    self.combat_system.spellcasting.regenerate_mana(mob_id)

    async def _update_spell_cooldowns(self):
        """Update spell cooldowns for all players."""
        for player_id, player_data in self.player_manager.connected_players.items():
            character = player_data.get('character')
            if not character:
                continue

            cooldowns = character.get('spell_cooldowns', {})
            if not cooldowns:
                continue

            # Reduce all cooldowns by 1
            for spell_id in list(cooldowns.keys()):
                cooldowns[spell_id] -= 1
                # Remove cooldowns that have expired
                if cooldowns[spell_id] <= 0:
                    del cooldowns[spell_id]

    async def _update_light_sources(self):
        """Update lit light sources - decrease burn time and remove when depleted."""
        from ..utils.colors import announcement, error_message

        for player_id, player_data in self.player_manager.connected_players.items():
            character = player_data.get('character')
            if not character:
                continue

            inventory = character.get('inventory', [])
            items_to_remove = []

            for i, item in enumerate(inventory):
                # Check if item is a lit light source
                if not item.get('is_light_source', False):
                    continue
                if not item.get('is_lit', False):
                    continue

                # Decrease burn time (tick_rate seconds per tick)
                time_remaining = item.get('time_remaining', 0)
                time_remaining -= self.tick_rate

                # Check for warnings
                if time_remaining <= 60 and item.get('_warned_60', False) is False:
                    # 1 minute warning
                    await self.connection_manager.send_message(
                        player_id,
                        announcement(f"Your {item['name']} flickers - it will burn out soon!")
                    )
                    item['_warned_60'] = True

                if time_remaining <= 10 and item.get('_warned_10', False) is False:
                    # 10 second warning
                    await self.connection_manager.send_message(
                        player_id,
                        error_message(f"Your {item['name']} is almost out!")
                    )
                    item['_warned_10'] = True

                # Update time remaining
                item['time_remaining'] = time_remaining

                # Check if depleted
                if time_remaining <= 0:
                    # Light source burned out
                    item['is_lit'] = False
                    await self.connection_manager.send_message(
                        player_id,
                        error_message(f"Your {item['name']} has burned out and is no longer providing light.")
                    )

                    # For non-reusable light sources (torches, candles), remove from inventory
                    if not item.get('properties', {}).get('can_relight', False):
                        items_to_remove.append(i)

                        # Notify room
                        username = player_data.get('username', 'Someone')
                        room_id = character.get('room_id')
                        if room_id:
                            await self.player_manager.notify_room_except_player(
                                room_id, player_id,
                                f"{username}'s {item['name']} burns out completely, leaving only ash."
                            )

            # Remove depleted items (in reverse order to preserve indices)
            for i in sorted(items_to_remove, reverse=True):
                inventory.pop(i)

    async def _update_active_effects(self):
        """Update active buff/debuff effects for all players."""
        for player_id, player_data in self.player_manager.connected_players.items():
            character = player_data.get('character')
            if not character:
                continue

            active_effects = character.get('active_effects', [])
            if not active_effects:
                continue

            # Reduce duration by 1 for all active effects
            expired_effects = []
            for i, effect in enumerate(active_effects):
                effect['duration'] -= 1
                if effect['duration'] <= 0:
                    expired_effects.append(i)
                    # Notify player when buff/debuff expires
                    # Check both 'spell_id' (for buffs/spells) and 'type' (for trap effects)
                    effect_name = effect.get('spell_id') or effect.get('type', 'Unknown')

                    # Handle stat restoration based on effect type
                    effect_amount = effect.get('effect_amount', 0)
                    effect_type = effect.get('type', '')
                    effect_name_check = effect.get('effect', '')

                    # Check if this is an enhancement effect (by checking if effect name starts with 'enhance_')
                    if effect_name_check and effect_name_check.startswith('enhance_') and effect_amount > 0:
                        # Enhancement effects - remove bonuses
                        self._remove_enhancement_effect(character, effect_name_check, effect_amount)
                    elif effect_type == 'stat_drain' and effect_amount > 0:
                        # Drain effects - restore drained stats
                        self._restore_drain_effect(character, effect_name_check, effect_amount)

                    await self.connection_manager.send_message(
                        player_id,
                        f"The {effect_name} effect has worn off."
                    )

            # Remove expired effects (in reverse order to preserve indices)
            for i in reversed(expired_effects):
                active_effects.pop(i)

    async def _update_poison_effects(self):
        """Update poison DOT effects for all players and mobs."""
        import random

        # Process poison effects on players
        for player_id, player_data in self.player_manager.connected_players.items():
            character = player_data.get('character')
            if not character:
                continue

            poison_effects = character.get('poison_effects', [])
            if not poison_effects:
                continue

            # Process each poison effect
            expired_effects = []
            for i, poison in enumerate(poison_effects):
                # Roll poison damage
                poison_damage_roll = poison.get('damage', '1d2')
                # Parse dice notation
                if 'd' in poison_damage_roll:
                    parts = poison_damage_roll.split('d')
                    num_dice = int(parts[0])
                    dice_value = int(parts[1].split('+')[0].split('-')[0])
                    modifier = 0
                    if '+' in parts[1]:
                        modifier = int(parts[1].split('+')[1])
                    elif '-' in parts[1]:
                        modifier = -int(parts[1].split('-')[1])

                    damage = sum(random.randint(1, dice_value) for _ in range(num_dice)) + modifier
                else:
                    damage = int(poison_damage_roll)

                # Apply poison damage to player
                current_health = character.get('current_hit_points', 0)
                max_health = character.get('max_hit_points', 100)
                new_health = max(0, current_health - damage)
                character['current_hit_points'] = new_health

                # Notify the poisoned player
                await self.connection_manager.send_message(
                    player_id,
                    f"You take {int(damage)} poison damage! Health: {int(new_health)}/{int(max_health)}"
                )

                # Reduce duration
                poison['duration'] -= 1
                if poison['duration'] <= 0:
                    expired_effects.append(i)
                    await self.connection_manager.send_message(
                        player_id,
                        "The poison has run its course."
                    )

                # Check if player died from poison
                if new_health <= 0:
                    await self.connection_manager.send_message(
                        player_id,
                        "You have succumbed to poison!"
                    )
                    # Handle player death
                    await self.combat_system.handle_player_death(player_id, character)
                    break  # Exit poison loop since player is dead

            # Remove expired poison effects (in reverse order)
            for i in reversed(expired_effects):
                poison_effects.pop(i)

        # Process poison effects on mobs
        for room_id, mobs in self.room_mobs.items():
            for mob in mobs[:]:  # Copy list to avoid modification issues
                poison_effects = mob.get('poison_effects', [])
                if not poison_effects:
                    continue

                # Process each poison effect
                expired_effects = []
                for i, poison in enumerate(poison_effects):
                    # Roll poison damage
                    poison_damage_roll = poison.get('damage', '1d2')
                    # Parse dice notation
                    if 'd' in poison_damage_roll:
                        parts = poison_damage_roll.split('d')
                        num_dice = int(parts[0])
                        dice_value = int(parts[1].split('+')[0].split('-')[0])
                        modifier = 0
                        if '+' in parts[1]:
                            modifier = int(parts[1].split('+')[1])
                        elif '-' in parts[1]:
                            modifier = -int(parts[1].split('-')[1])

                        damage = sum(random.randint(1, dice_value) for _ in range(num_dice)) + modifier
                    else:
                        damage = int(poison_damage_roll)

                    # Apply poison damage
                    current_health = mob.get('current_hit_points', mob.get('health', mob.get('max_hit_points', 20)))
                    new_health = max(0, current_health - damage)

                    # Update both health fields for compatibility
                    if 'current_hit_points' in mob:
                        mob['current_hit_points'] = new_health
                    if 'health' in mob:
                        mob['health'] = new_health

                    # Notify caster if they're online
                    caster_id = poison.get('caster_id')
                    if caster_id and caster_id in self.player_manager.connected_players:
                        caster_data = self.player_manager.connected_players[caster_id]
                        caster_char = caster_data.get('character')
                        # Only notify if caster is in the same room
                        if caster_char and caster_char.get('room_id') == room_id:
                            await self.connection_manager.send_message(
                                caster_id,
                                f"{mob['name']} takes {int(damage)} poison damage!"
                            )

                    # Reduce duration
                    poison['duration'] -= 1
                    if poison['duration'] <= 0:
                        expired_effects.append(i)

                    # Check if mob died from poison
                    if new_health <= 0:
                        # Handle mob death
                        mob_participant_id = self.combat_system.get_mob_identifier(mob)

                        # Notify all players in the room
                        for player_id, player_data in self.player_manager.connected_players.items():
                            player_char = player_data.get('character')
                            if player_char and player_char.get('room_id') == room_id:
                                await self.connection_manager.send_message(
                                    player_id,
                                    f"{mob['name']} succumbs to poison!"
                                )

                        # Always award loot (gold goes to caster if online, items drop in room)
                        if caster_id:
                            await self.combat_system.handle_mob_loot_drop(caster_id, mob, room_id)
                        else:
                            # No caster (shouldn't happen, but handle it)
                            # Just drop items with no player_id
                            await self.combat_system.handle_mob_loot_drop(0, mob, room_id)

                        await self.combat_system.handle_mob_death(room_id, mob_participant_id)
                        break  # Exit poison loop since mob is dead

                # Remove expired poison effects (in reverse order)
                for i in reversed(expired_effects):
                    poison_effects.pop(i)

    def _remove_enhancement_effect(self, character: dict, effect: str, amount: int):
        """Remove an enhancement effect from a character's stats.

        Args:
            character: The character dictionary
            effect: The enhancement effect type
            amount: The amount to remove
        """
        effect_map = {
            'enhance_agility': 'dexterity',
            'enhance_dexterity': 'dexterity',
            'enhance_strength': 'strength',
            'enhance_constitution': 'constitution',
            'enhance_vitality': 'vitality',
            'enhance_intelligence': 'intellect',
            'enhance_wisdom': 'wisdom',
            'enhance_charisma': 'charisma',
            # Aliases for compatibility
            'enhance_physique': 'constitution',
            'enhance_stamina': 'vitality'
        }

        if effect in effect_map:
            stat_key = effect_map[effect]
            current_value = character.get(stat_key, 10)
            character[stat_key] = max(1, current_value - amount)  # Don't go below 1
        elif effect == 'enhance_mental':
            # Remove mental stat enhancements (INT, WIS, CHA)
            character['intellect'] = max(1, character.get('intellect', 10) - amount)
            character['wisdom'] = max(1, character.get('wisdom', 10) - amount)
            character['charisma'] = max(1, character.get('charisma', 10) - amount)
        elif effect == 'enhance_body':
            # Remove physical stat enhancements (STR, DEX, CON)
            character['strength'] = max(1, character.get('strength', 10) - amount)
            character['dexterity'] = max(1, character.get('dexterity', 10) - amount)
            character['constitution'] = max(1, character.get('constitution', 10) - amount)

    def _restore_drain_effect(self, character: dict, effect: str, amount: int):
        """Restore stats that were drained by a drain spell.

        Args:
            character: The character dictionary
            effect: The drain effect type
            amount: The amount to restore
        """
        drain_map = {
            'drain_agility': 'dexterity',
            'drain_physique': 'constitution',
            'drain_stamina': 'vitality'
        }

        if effect in drain_map:
            stat_key = drain_map[effect]
            current_value = character.get(stat_key, 10)
            character[stat_key] = current_value + amount
        elif effect == 'drain_mental':
            # Restore all mental stats (INT, WIS, CHA)
            character['intellect'] = character.get('intellect', 10) + amount
            character['wisdom'] = character.get('wisdom', 10) + amount
            character['charisma'] = character.get('charisma', 10) + amount
        elif effect == 'drain_body':
            # Restore all physical stats (STR, DEX, CON)
            character['strength'] = character.get('strength', 10) + amount
            character['dexterity'] = character.get('dexterity', 10) + amount
            character['constitution'] = character.get('constitution', 10) + amount

    async def _auto_save_players(self):
        """Auto-save all connected players with characters."""
        try:
            saved_count = 0
            for player_id, player_data in self.player_manager.connected_players.items():
                if player_data.get('character') and player_data.get('authenticated'):
                    self.player_manager.save_player_character(player_id, player_data['character'])
                    saved_count += 1

            if saved_count > 0:
                self.logger.info(f"Auto-saved {saved_count} player(s)")
        except Exception as e:
            self.logger.error(f"Error during auto-save: {e}")



    async def _move_player(self, player_id: int, direction: str):
        """Move a player in a direction - delegates to player_manager."""
        await self.player_manager.move_player(player_id, direction)


    async def _send_room_description(self, player_id: int, detailed: bool = False):
        """Send the description of the player's current room - delegates to world_manager."""
        await self.world_manager.send_room_description(player_id, detailed)

    def _check_npc_hostility(self, npc_id: str) -> bool:
        """Check if an NPC is hostile using preloaded world manager data."""
        return self.world_manager.is_npc_hostile(npc_id)

    async def _notify_room_except_player(self, room_id: str, exclude_player_id: int, message: str):
        """Send a message to all players in a room except the specified player - delegates to player_manager."""
        await self.player_manager.notify_room_except_player(room_id, exclude_player_id, message)



    def get_connected_player_count(self) -> int:
        """Get the number of connected players."""
        return self.player_manager.get_connected_player_count()

    def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a connected player."""
        return self.player_manager.get_player_info(player_id)


    async def _handle_drop_item(self, player_id: int, item_name: str):
        """Handle dropping an item from inventory - delegates to item_manager."""
        await self.item_manager.handle_drop_item(player_id, item_name)

    async def _handle_equip_item(self, player_id: int, item_name: str):
        """Handle equipping an item from inventory - delegates to item_manager."""
        await self.item_manager.handle_equip_item(player_id, item_name)

    async def _handle_unequip_item(self, player_id: int, item_name: str):
        """Handle unequipping an item to inventory - delegates to item_manager."""
        await self.item_manager.handle_unequip_item(player_id, item_name)

    async def _handle_trade_command(self, player_id: int, action: str, item_name: str):
        """Handle buy/sell commands with vendors."""
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Use vendor system to handle trade
        await self.vendor_system.handle_trade_command(player_id, action, item_name)

    async def _handle_ring_command(self, player_id: int, target: str):
        """Handle ring command for special items like gongs."""
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Check if the target matches "gong" or similar variations
        target_lower = target.lower()
        if target_lower in ['gong', 'g', 'bronze gong', 'bronze']:
            # Check if player is in an arena room (configured in game settings)
            arena_config = self.config_manager.get_arena_by_room(room_id)
            if not arena_config:
                await self.connection_manager.send_message(player_id, "There is no gong here to ring.")
                return

            # Ring the gong and spawn a mob - delegates to world_manager
            await self.world_manager.handle_ring_gong(player_id, room_id)
        else:
            await self.connection_manager.send_message(player_id, f"You cannot ring {target}.")

    async def _handle_list_vendor_items(self, player_id: int):
        """Show vendor inventory."""
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Use vendor system to handle listing
        await self.vendor_system.handle_list_vendor_items(player_id)



    async def _handle_look_at_target(self, player_id: int, target_name: str):
        """Handle looking at specific targets like NPCs and mobs - delegates to world_manager."""
        await self.world_manager.handle_look_at_target(player_id, target_name)

    def _initialize_lairs(self):
        """Initialize all lair rooms with their starting mobs."""
        # Load monster data
        # Use cached monsters data
        if not self.monsters_data:
            self.logger.error("Monsters data not loaded")
            return

        # Find all lair rooms and spawn their mobs
        for room_id, room in self.world_manager.rooms.items():
            # Support old format: is_lair + lair_monster
            if hasattr(room, 'is_lair') and room.is_lair:
                lair_monster_id = getattr(room, 'lair_monster', None)
                if lair_monster_id and lair_monster_id in self.monsters_data:
                    self._spawn_lair_mob(room_id, lair_monster_id, self.monsters_data[lair_monster_id])
                    self.logger.info(f"[LAIR] Spawned {lair_monster_id} in {room_id}")

            # Support new format: lairs array
            elif hasattr(room, 'lairs') and room.lairs:
                for lair in room.lairs:
                    mob_id = lair.get('mob_id')
                    max_mobs = lair.get('max_mobs', 1)

                    if mob_id and mob_id in self.monsters_data:
                        # Spawn up to max_mobs
                        for i in range(max_mobs):
                            self._spawn_lair_mob(room_id, mob_id, self.monsters_data[mob_id])
                        self.logger.info(f"[LAIR] Spawned {max_mobs}x {mob_id} in {room_id}")

    def spawn_mob(self, room_id: str, monster_id: str, monster: dict, **kwargs) -> dict:
        """Centralized mob spawning logic.

        Args:
            room_id: Room to spawn the mob in
            monster_id: Monster ID (from monster data)
            monster: Monster data dictionary
            **kwargs: Additional flags to add to the mob (e.g., is_lair_mob=True, is_wandering=True, spawn_area='forest')

        Returns:
            The spawned mob dictionary
        """
        # Ensure room has mob list
        if room_id not in self.room_mobs:
            self.room_mobs[room_id] = []

        # Generate random stats
        level = monster.get('level', 1)
        monster_type = monster.get('type', 'monster')
        stats = self._generate_mob_stats(level, monster_type)

        # Randomize HP (±20% variance)
        base_hp = monster.get('health', 100)
        hp_variance = int(base_hp * 0.2)
        randomized_hp = random.randint(
            max(1, base_hp - hp_variance),
            base_hp + hp_variance
        )

        # Randomize XP reward (±20% variance)
        base_xp = monster.get('experience_reward', 25)
        xp_variance = int(base_xp * 0.2)
        randomized_xp = random.randint(
            max(1, base_xp - xp_variance),
            base_xp + xp_variance
        )

        # Create mob instance with full stat block
        mob_name = monster.get('name', 'Unknown Creature')
        spawned_mob = {
            'id': monster_id,
            'name': mob_name,
            'type': 'hostile',
            'description': monster.get('description', f'A fierce {mob_name}'),
            'level': level,
            'health': randomized_hp,
            'max_health': randomized_hp,
            'damage': monster.get('damage', '1d4'),
            'damage_min': monster.get('damage_min', 1),
            'damage_max': monster.get('damage_max', 4),
            'armor_class': monster.get('armor', 0),

            # Full stat block
            'strength': stats['strength'],
            'dexterity': stats['dexterity'],
            'constitution': stats['constitution'],
            'intelligence': stats['intelligence'],
            'wisdom': stats['wisdom'],
            'charisma': stats['charisma'],

            'experience_reward': randomized_xp,
            'gold_reward': monster.get('gold_reward', [0, 5]),
            'loot_table': monster.get('loot_table', []),
            'experience': 0,  # Track XP gained from mob vs mob combat
            'gold': 0,  # Track gold looted from other mobs

            # Spellcasting fields
            'spellcaster': monster.get('spellcaster', False),
            'spell_skill': monster.get('spell_skill', 50),
            'spell_list': monster.get('spell_list', 'generic_caster'),

            # Special abilities
            'abilities': monster.get('abilities', []),
        }

        # Add any additional flags passed via kwargs
        spawned_mob.update(kwargs)

        # Add to room
        self.room_mobs[room_id].append(spawned_mob)

        # Load special abilities for this mob
        mob_instance_id = self.combat_system.get_mob_identifier(spawned_mob)
        self.combat_system.load_mob_abilities(spawned_mob, mob_instance_id)

        # Equip humanoid mobs with weapons and armor
        if monster_type == 'humanoid':
            self._equip_humanoid_mob(spawned_mob, monster)

            # Update description if it has a weapon placeholder
            if '{0}' in spawned_mob['description']:
                weapon = spawned_mob.get('equipped', {}).get('weapon')

                # Build weapon description with article (a/an)
                if weapon:
                    weapon_name = weapon['name'].lower()
                    # Use 'an' for words starting with vowels
                    article = 'an' if weapon_name[0] in 'aeiou' else 'a'
                    weapon_desc = f"{article} {weapon_name}"
                else:
                    weapon_desc = "their fists"

                # Check if description has multiple placeholders
                if '{1}' in spawned_mob['description']:
                    # Second placeholder is for shield/secondary weapon
                    # For now, use "and a shield" as default for armed mobs
                    shield_desc = "and a shield" if weapon else ""
                    spawned_mob['description'] = spawned_mob['description'].format(weapon_desc, shield_desc)
                else:
                    # Single placeholder, just weapon
                    spawned_mob['description'] = spawned_mob['description'].format(weapon_desc)

        # Build log message
        log_extras = ", ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else "no flags"
        self.logger.info(f"[MOB_SPAWN] Spawned {mob_name} (level {level}) in {room_id} ({log_extras})")

        return spawned_mob

    def _generate_mob_stats(self, level: int, monster_type: str = 'monster') -> dict:
        """Generate random stats for a mob based on level and type.

        Args:
            level: The mob's level
            monster_type: Type of monster (affects stat distribution)

        Returns:
            Dictionary with all 6 stats
        """
        # Base stats start at 8 + level
        base = 8 + level

        # Add random variance (-2 to +2)
        variance = lambda: random.randint(-2, 2)

        stats = {
            'strength': base + variance(),
            'dexterity': base + variance(),
            'constitution': base + variance(),
            'intelligence': base + variance(),
            'wisdom': base + variance(),
            'charisma': base + variance()
        }

        # Type-based adjustments
        if monster_type == 'undead':
            stats['constitution'] += 2
            stats['charisma'] -= 3
            stats['intelligence'] -= 1
        elif monster_type == 'animal':
            stats['strength'] += 1
            stats['dexterity'] += 2
            stats['intelligence'] -= 4
            stats['wisdom'] += 1
        elif monster_type == 'humanoid':
            # Balanced, no adjustments
            pass

        # Ensure minimum of 3 for all stats
        for stat in stats:
            stats[stat] = max(3, stats[stat])

        return stats

    def _load_item_definitions(self):
        """Load weapon and armor definitions from JSON files."""
        if hasattr(self, '_weapons_cache') and hasattr(self, '_armor_cache'):
            return self._weapons_cache, self._armor_cache

        weapons = {}
        armor = {}

        # Load weapons
        weapon_file = Path('data/items/weapon.json')
        if weapon_file.exists():
            try:
                with open(weapon_file, 'r', encoding='utf-8') as f:
                    weapon_data = json.load(f)
                    weapons = weapon_data.get('items', {})
            except Exception as e:
                self.logger.error(f"Error loading weapon data: {e}")

        # Load armor
        armor_file = Path('data/items/armor.json')
        if armor_file.exists():
            try:
                with open(armor_file, 'r', encoding='utf-8') as f:
                    armor_data = json.load(f)
                    armor = armor_data.get('items', {})
            except Exception as e:
                self.logger.error(f"Error loading armor data: {e}")

        # Cache for future use
        self._weapons_cache = weapons
        self._armor_cache = armor

        return weapons, armor

    def _equip_humanoid_mob(self, spawned_mob: dict, monster_data: dict):
        """Equip a humanoid mob with appropriate weapons and armor."""
        mob_level = spawned_mob.get('level', 1)
        mob_name = spawned_mob.get('name', '')

        # Get mob's class from data (with fallback to fighter)
        mob_class = monster_data.get('class', 'fighter')

        # Load item definitions
        weapons, armor = self._load_item_definitions()

        # Filter weapons by level and class
        eligible_weapons = []
        for weapon_id, weapon_data in weapons.items():
            props = weapon_data.get('properties', {})
            required_level = props.get('required_level', 0)
            allowed_classes = props.get('allowed_classes', None)

            # Skip if level too high or too low (allow some variance)
            if required_level > mob_level or required_level < max(0, mob_level - 5):
                continue

            # Skip if class restricted and mob's class not allowed
            if allowed_classes and mob_class not in allowed_classes:
                continue

            # Skip natural weapons, ammunition, and ranged weapons
            weapon_type = props.get('weapon_type', '')
            is_ranged = props.get('ranged', False)
            if weapon_type in ['natural', 'ammunition', 'thrown'] or is_ranged:
                continue

            eligible_weapons.append((weapon_id, weapon_data))

        # Filter armor by level and class
        eligible_armor = []
        for armor_id, armor_data in armor.items():
            props = armor_data.get('properties', {})
            required_level = props.get('required_level', 0)
            allowed_classes = props.get('allowed_classes', None)

            # Skip if level too high or too low (allow some variance)
            if required_level > mob_level or required_level < max(0, mob_level - 5):
                continue

            # Skip if class restricted and mob's class not allowed
            if allowed_classes and mob_class not in allowed_classes:
                continue

            eligible_armor.append((armor_id, armor_data))

        # Initialize equipped dict
        spawned_mob['equipped'] = {}

        # Always equip a weapon if available (100% chance)
        if eligible_weapons:
            weapon_id, weapon_data = random.choice(eligible_weapons)
            spawned_mob['equipped']['weapon'] = {
                'id': weapon_id,
                'name': weapon_data['name'],
                'type': 'weapon',
                'weight': weapon_data.get('weight', 1),
                'base_value': weapon_data.get('base_value', 0),
                'description': weapon_data.get('description', ''),
                'properties': weapon_data.get('properties', {})
            }
            # Update mob's damage from weapon
            damage = weapon_data['properties'].get('damage', '1d4')
            spawned_mob['damage'] = damage
            self.logger.info(f"[MOB_EQUIP] {mob_name} equipped with {weapon_data['name']} ({damage} damage)")

        # Always equip armor if available (100% chance)
        if eligible_armor:
            armor_id, armor_data = random.choice(eligible_armor)
            spawned_mob['equipped']['armor'] = {
                'id': armor_id,
                'name': armor_data['name'],
                'type': 'armor',
                'weight': armor_data.get('weight', 1),
                'base_value': armor_data.get('base_value', 0),
                'description': armor_data.get('description', ''),
                'properties': armor_data.get('properties', {})
            }
            # Update mob's armor class from armor
            armor_class = armor_data['properties'].get('armor_class', 0)
            spawned_mob['armor_class'] = armor_class
            self.logger.info(f"[MOB_EQUIP] {mob_name} equipped with {armor_data['name']} (AC {armor_class})")

        # Store mob's class for reference
        spawned_mob['class'] = mob_class

    def _spawn_lair_mob(self, room_id: str, monster_id: str, monster: dict):
        """Spawn a mob in a lair room."""
        self.spawn_mob(room_id, monster_id, monster, is_lair_mob=True)

    async def _check_lair_respawns(self):
        """Check if any lair mobs need to respawn."""
        current_time = time.time()

        # Load monster data (cache this if performance becomes an issue)
        monsters = self._load_all_monsters()
        if not monsters:
            self.logger.error("Failed to load monsters data for respawn")
            return

        # Check each lair room
        for room_id, room in self.world_manager.rooms.items():
            # Support old format: is_lair + lair_monster
            if hasattr(room, 'is_lair') and room.is_lair:
                lair_monster_id = getattr(room, 'lair_monster', None)
                if not lair_monster_id or lair_monster_id not in monsters:
                    continue

                # Check if mob is alive in the room
                room_has_mob = False
                if room_id in self.room_mobs:
                    for mob in self.room_mobs[room_id]:
                        if mob.get('id') == lair_monster_id and mob.get('is_lair_mob'):
                            room_has_mob = True
                            break

                # If mob is dead and respawn timer has passed, respawn it
                if not room_has_mob:
                    # Check if we have a timer set for this room
                    if room_id not in self.lair_timers:
                        # No timer set, set one now
                        respawn_time = getattr(room, 'respawn_time', 300)
                        self.lair_timers[room_id] = current_time + respawn_time
                        self.logger.info(f"[LAIR] {lair_monster_id} died in {room_id}, respawn in {respawn_time}s")
                    elif current_time >= self.lair_timers[room_id]:
                        # Timer expired, respawn the mob
                        self._spawn_lair_mob(room_id, lair_monster_id, self.monsters_data[lair_monster_id])
                        del self.lair_timers[room_id]
                        self.logger.info(f"[LAIR] {lair_monster_id} respawned in {room_id}")
                else:
                    # Mob is alive, clear any existing timer
                    if room_id in self.lair_timers:
                        del self.lair_timers[room_id]

            # Support new format: lairs array
            elif hasattr(room, 'lairs') and room.lairs:
                for lair in room.lairs:
                    mob_id = lair.get('mob_id')
                    max_mobs = lair.get('max_mobs', 1)
                    respawn_time = lair.get('respawn_time', 300)

                    if not mob_id or mob_id not in monsters:
                        continue

                    # Count how many of this mob type are alive in the room
                    alive_count = 0
                    if room_id in self.room_mobs:
                        for mob in self.room_mobs[room_id]:
                            if mob.get('id') == mob_id and mob.get('is_lair_mob'):
                                alive_count += 1

                    # Calculate how many we need to spawn
                    needed = max_mobs - alive_count

                    if needed > 0:
                        # Use a unique key for this specific lair spawn
                        timer_key = f"{room_id}:{mob_id}"

                        if timer_key not in self.lair_timers:
                            # No timer set, set one now
                            self.lair_timers[timer_key] = current_time + respawn_time
                            self.logger.info(f"[LAIR] {mob_id} died in {room_id}, respawn in {respawn_time}s")
                        elif current_time >= self.lair_timers[timer_key]:
                            # Timer expired, respawn the mob(s)
                            for i in range(needed):
                                self._spawn_lair_mob(room_id, mob_id, self.monsters_data[mob_id])
                            del self.lair_timers[timer_key]
                            self.logger.info(f"[LAIR] {needed}x {mob_id} respawned in {room_id}")
                    else:
                        # All mobs alive, clear any existing timer
                        timer_key = f"{room_id}:{mob_id}"
                        if timer_key in self.lair_timers:
                            del self.lair_timers[timer_key]

    async def _check_wandering_mob_spawns(self):
        """Check if we should spawn wandering mobs in all configured areas."""
        current_time = time.time()

        # Get all wandering mob configurations
        wandering_configs = self.config_manager.get_setting('wandering_mobs', default={})
        if not wandering_configs:
            return

        # Check if it's time to try spawning
        time_since_last = current_time - self.last_wandering_spawn_check
        if time_since_last < 30:  # Global check interval
            return

        self.last_wandering_spawn_check = current_time

        # Process each area
        for area_id, config in wandering_configs.items():
            if not config.get('enabled', False):
                continue

            await self._check_area_spawn(area_id, config, current_time)

    async def _check_area_spawn(self, area_id: str, config: dict, current_time: float):
        """Check and spawn wandering mobs for a specific area."""
        spawn_interval = config.get('spawn_interval', 30)

        # Count current wandering mobs in this area
        wandering_count = 0
        for room_id, room_mobs in self.room_mobs.items():
            room = self.world_manager.get_room(room_id)
            if room and hasattr(room, 'area_id') and room.area_id == area_id:
                for mob in room_mobs:
                    if mob.get('is_wandering'):
                        wandering_count += 1

        # Check if we're at max capacity for this area
        max_wandering = config.get('max_wandering_mobs', 5)
        if wandering_count >= max_wandering:
            return

        # Roll for spawn chance
        spawn_chance = config.get('spawn_chance', 0.3)
        roll = random.random()
        if roll > spawn_chance:
            return

        # Select a random mob from the pool
        mob_pool = config.get('mob_pool', [])
        if not mob_pool:
            return

        # Weighted random selection
        total_weight = sum(entry.get('weight', 1) for entry in mob_pool)
        roll = random.random() * total_weight
        current = 0
        selected_mob_id = None

        for entry in mob_pool:
            current += entry.get('weight', 1)
            if roll <= current:
                selected_mob_id = entry.get('id')
                break

        if not selected_mob_id:
            return

        # Load monster data
        monsters = self._load_all_monsters()
        if not monsters:
            self.logger.error("Failed to load monsters data for wandering spawn")
            return

        if selected_mob_id not in monsters:
            return

        # Get all rooms for this area
        area_rooms = []
        for room_id, room in self.world_manager.rooms.items():
            if hasattr(room, 'area_id') and room.area_id == area_id:
                area_rooms.append(room_id)

        if not area_rooms:
            return

        # Select random room to spawn in
        spawn_room = random.choice(area_rooms)

        # Spawn the wandering mob
        self._spawn_wandering_mob(spawn_room, selected_mob_id, self.monsters_data[selected_mob_id], area_id)

    def _spawn_wandering_mob(self, room_id: str, monster_id: str, monster: dict, area_id: str = None):
        """Spawn a wandering mob in a room."""
        self.spawn_mob(room_id, monster_id, monster, is_wandering=True, spawn_area=area_id)

    async def _move_wandering_mobs(self):
        """Move wandering mobs randomly between rooms."""
        # Get wandering mob configs for movement chances
        wandering_configs = self.config_manager.get_setting('wandering_mobs', default={})

        # Count total mobs and wandering mobs
        total_mobs = 0
        total_wandering = 0
        total_lair = 0
        total_gong = 0
        total_other = 0

        for room_id, room_mobs in self.room_mobs.items():
            for mob in room_mobs:
                if mob is None:
                    continue
                total_mobs += 1
                if mob.get('is_wandering'):
                    total_wandering += 1
                elif mob.get('is_lair_mob'):
                    total_lair += 1
                elif mob.get('spawned_by_gong'):
                    total_gong += 1
                else:
                    total_other += 1


        # Iterate through all rooms
        for room_id in list(self.room_mobs.keys()):
            if room_id not in self.room_mobs:
                continue

            for mob in self.room_mobs[room_id][:]:  # Copy to avoid modification during iteration
                # Skip non-wandering mobs
                if not mob.get('is_wandering'):
                    continue

                mob_name = mob.get('name', 'Unknown creature')

                # Check if there are any players in the room - if so, don't move (stay to fight)
                players_in_room = []
                for player_id, player_data in self.player_manager.connected_players.items():
                    character = player_data.get('character')
                    if character and character.get('room_id') == room_id:
                        players_in_room.append(player_id)

                if players_in_room:
                    continue

                # Check if mob is paralyzed
                active_effects = mob.get('active_effects', [])
                is_paralyzed = False
                for effect in active_effects:
                    if effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze':
                        is_paralyzed = True
                        break

                if is_paralyzed:
                    continue

                # Get movement chance for this mob's spawn area
                spawn_area = mob.get('spawn_area', 'arena_dungeon')
                area_config = wandering_configs.get(spawn_area, {})
                movement_chance = area_config.get('movement_chance', 0.2)

                # Roll for movement
                roll = random.random()
                if roll > movement_chance:
                    continue

                # Get current room
                room = self.world_manager.get_room(room_id)
                if not room:
                    continue

                # Get available exits
                exits = list(room.exits.keys()) if hasattr(room, 'exits') else []
                if not exits:
                    continue

                # Choose random exit
                direction = random.choice(exits)

                # Get destination room ID from exit object
                exit_obj = room.exits.get(direction)
                if not exit_obj:
                    continue

                destination_id = exit_obj.destination_room_id if hasattr(exit_obj, 'destination_room_id') else str(exit_obj)
                if not destination_id or destination_id not in self.world_manager.rooms:
                    continue

                # Check barriers - wandering mobs must respect barriers like aggressive mobs
                if hasattr(self, 'barrier_system'):
                    # Create a minimal character dict for the mob (most mobs don't have keys)
                    mob_character = {
                        'inventory': mob.get('inventory', [])
                    }

                    # Check if barrier blocks movement
                    can_pass, unlock_msg = await self.barrier_system.check_barrier(
                        player_id=-1,  # Negative ID indicates this is a mob
                        character=mob_character,
                        room=room,
                        direction=direction,
                        player_name=mob_name
                    )

                    if not can_pass:
                        # Barrier blocked movement - skip this exit and try a different one next time
                        continue

                    # If barrier was unlocked, update mob's inventory
                    if unlock_msg:
                        mob['inventory'] = mob_character['inventory']

                # Check if destination is in the same area (prevent leaving dungeon)
                destination_room = self.world_manager.get_room(destination_id)
                current_area = getattr(room, 'area_id', None)
                destination_area = getattr(destination_room, 'area_id', None)

                if current_area and destination_area and current_area != destination_area:
                    continue

                # Move mob to new room
                self.room_mobs[room_id].remove(mob)
                if destination_id not in self.room_mobs:
                    self.room_mobs[destination_id] = []
                self.room_mobs[destination_id].append(mob)

                # Notify players in both rooms
                # Notify players in source room
                await self._notify_room_players_sync(room_id, f"{mob_name} wanders {direction}.")

                # Notify players in destination room
                opposite_direction = self._get_opposite_direction(direction)
                arrival_msg = f"{mob_name} wanders in from the {opposite_direction}."
                await self._notify_room_players_sync(destination_id, arrival_msg)

    def _get_opposite_direction(self, direction: str) -> str:
        """Get the opposite direction."""
        opposites = {
            'north': 'south',
            'south': 'north',
            'east': 'west',
            'west': 'east',
            'up': 'down',
            'down': 'up',
            'northeast': 'southwest',
            'northwest': 'southeast',
            'southeast': 'northwest',
            'southwest': 'northeast'
        }
        return opposites.get(direction, direction)

    async def _notify_room_players_sync(self, room_id: str, message: str):
        """Send a message to all players in a room (sync version for use in tick)."""
        for player_id, player_data in self.player_manager.connected_players.items():
            if not player_data:
                continue
            character = player_data.get('character')
            if character and character.get('room_id') == room_id:
                await self.connection_manager.send_message(player_id, message)








