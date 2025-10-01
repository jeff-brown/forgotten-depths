"""Async game engine that coordinates all game systems."""

import asyncio
import random
import time
import json
from typing import Optional, Dict, Any

from ..networking.async_connection_manager import AsyncConnectionManager
from ..commands.base_command import CommandManager
from ..game.world.world_manager import WorldManager
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
        self.command_manager = CommandManager()
        self.world_manager = WorldManager(self)
        self.config_manager = ConfigManager()
        self.command_handler = CommandHandler(self)
        self.vendor_system = VendorSystem(self)
        self.combat_system = CombatSystem(self)
        self.item_manager = ItemManager(self)
        self.player_manager = PlayerManager(self)

        # Database and persistence
        self.database: Optional[Database] = None
        self.player_storage: Optional[PlayerStorage] = None


        # Room mob management - tracks spawned mobs in each room
        self.room_mobs: Dict[str, list] = {}

        # Lair management - tracks respawn timers for lair rooms
        self.lair_timers: Dict[str, float] = {}  # room_id -> time when mob should respawn

        # Wandering mob management
        self.last_wandering_spawn_check = time.time()

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
            self.logger.error(f"Game engine error: {e}")
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

        # Stop connection manager
        await self.connection_manager.stop_server()

        # Disconnect database
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
            await self._move_wandering_mobs()

            # Regenerate health and mana
            await self._regenerate_players()
            await self._regenerate_mobs()

            # Update spell cooldowns
            await self._update_spell_cooldowns()

            # Update active buffs/effects
            await self._update_active_effects()

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
            current_health = character.get('health', 0)
            max_health = character.get('max_hit_points', 100)
            current_mana = character.get('mana', 0)
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

            # Apply hunger/thirst damage if starving/dehydrated
            damage_taken = 0
            if hunger <= 0:
                # Starvation damage per tick (configurable)
                damage_taken += starvation_damage
                # Remind player every 60 seconds
                last_starving_warning = warnings.get('starving', 0)
                if current_time - last_starving_warning >= 60:
                    await self.connection_manager.send_message(player_id, "You are starving! Find food soon!")
                    warnings['starving'] = current_time
            else:
                # Reset timestamp when hunger is restored above 0
                warnings['starving'] = 0

            if thirst <= 0:
                # Dehydration damage per tick (configurable, more dangerous than starvation)
                damage_taken += dehydration_damage
                # Remind player every 60 seconds
                last_dehydrated_warning = warnings.get('dehydrated', 0)
                if current_time - last_dehydrated_warning >= 60:
                    await self.connection_manager.send_message(player_id, "You are severely dehydrated! Find water immediately!")
                    warnings['dehydrated'] = current_time
            else:
                # Reset timestamp when thirst is restored above 0
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
                character['health'] = max(1, current_health - damage_taken)

            # Calculate regen amounts
            # Health regen: CON / 50 per tick (e.g., 15 CON = 0.3 HP/tick = 18 HP/min)
            health_regen = constitution / 50.0
            # Mana regen: INT / 40 per tick (e.g., 16 INT = 0.4 mana/tick = 24 mana/min)
            mana_regen = intellect / 40.0

            # Apply regeneration (only if not starving/dehydrated)
            if current_health < max_health and hunger > 0 and thirst > 0:
                new_health = min(current_health + health_regen, max_health)
                character['health'] = new_health

            if current_mana < max_mana:
                new_mana = min(current_mana + mana_regen, max_mana)
                character['mana'] = new_mana

    async def _regenerate_mobs(self):
        """Regenerate health for all mobs."""
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

                # Apply regeneration
                if current_health < max_health and current_health > 0:
                    new_health = min(current_health + health_regen, max_health)
                    mob['health'] = new_health

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
                    # Notify player when buff expires
                    spell_name = effect.get('spell_id', 'Unknown')
                    await self.connection_manager.send_message(
                        player_id,
                        f"The {spell_name} effect has worn off."
                    )

            # Remove expired effects (in reverse order to preserve indices)
            for i in reversed(expired_effects):
                active_effects.pop(i)

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
            # Check if player is in the arena room
            if room_id != 'arena':
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
        try:
            with open('data/npcs/monsters.json', 'r') as f:
                monsters_data = json.load(f)
            monsters = {m['id']: m for m in monsters_data}
        except Exception as e:
            self.logger.error(f"Failed to load monsters data: {e}")
            return

        # Find all lair rooms and spawn their mobs
        for room_id, room in self.world_manager.rooms.items():
            if hasattr(room, 'is_lair') and room.is_lair:
                lair_monster_id = getattr(room, 'lair_monster', None)
                if lair_monster_id and lair_monster_id in monsters:
                    self._spawn_lair_mob(room_id, lair_monster_id, monsters[lair_monster_id])
                    self.logger.info(f"[LAIR] Spawned {lair_monster_id} in {room_id}")

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

    def _spawn_lair_mob(self, room_id: str, monster_id: str, monster: dict):
        """Spawn a mob in a lair room."""
        if room_id not in self.room_mobs:
            self.room_mobs[room_id] = []

        # Generate random stats
        level = monster.get('level', 1)
        monster_type = monster.get('type', 'monster')
        stats = self._generate_mob_stats(level, monster_type)

        # Create mob instance with full stat block
        mob_name = monster.get('name', 'Unknown Creature')
        spawned_mob = {
            'id': monster_id,
            'name': mob_name,
            'type': 'hostile',
            'description': monster.get('description', f'A fierce {mob_name}'),
            'level': level,
            'health': monster.get('health', 100),
            'max_health': monster.get('health', 100),
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

            'experience_reward': monster.get('experience_reward', 25),
            'gold_reward': monster.get('gold_reward', [0, 5]),
            'loot_table': monster.get('loot_table', []),
            'experience': 0,  # Track XP gained from mob vs mob combat
            'gold': 0,  # Track gold looted from other mobs
            'is_lair_mob': True
        }

        self.room_mobs[room_id].append(spawned_mob)

    async def _check_lair_respawns(self):
        """Check if any lair mobs need to respawn."""
        current_time = time.time()

        # Load monster data (cache this if performance becomes an issue)
        try:
            with open('data/npcs/monsters.json', 'r') as f:
                monsters_data = json.load(f)
            monsters = {m['id']: m for m in monsters_data}
        except Exception as e:
            self.logger.error(f"Failed to load monsters data for respawn: {e}")
            return

        # Check each lair room
        for room_id, room in self.world_manager.rooms.items():
            if not (hasattr(room, 'is_lair') and room.is_lair):
                continue

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
                    self._spawn_lair_mob(room_id, lair_monster_id, monsters[lair_monster_id])
                    del self.lair_timers[room_id]
                    self.logger.info(f"[LAIR] {lair_monster_id} respawned in {room_id}")
            else:
                # Mob is alive, clear any existing timer
                if room_id in self.lair_timers:
                    del self.lair_timers[room_id]

    async def _check_wandering_mob_spawns(self):
        """Check if we should spawn a wandering mob."""
        # Check if enabled
        enabled = self.config_manager.get_setting('dungeon', 'wandering_mobs', 'enabled', default=False)
        self.logger.info(f"[WANDERING DEBUG] Enabled setting value: {enabled}, type: {type(enabled)}")
        self.logger.info(f"[WANDERING DEBUG] Full dungeon config: {self.config_manager.get_setting('dungeon')}")
        if not enabled:
            self.logger.debug(f"[WANDERING] System not enabled: {enabled}")
            return

        current_time = time.time()
        spawn_interval = self.config_manager.get_setting('dungeon', 'wandering_mobs', 'spawn_interval', default=30)

        # Check if it's time to try spawning
        time_since_last = current_time - self.last_wandering_spawn_check
        self.logger.info(f"[WANDERING DEBUG] Time since last: {time_since_last:.1f}s, spawn_interval: {spawn_interval}s")
        if time_since_last < spawn_interval:
            return

        self.last_wandering_spawn_check = current_time
        self.logger.info(f"[WANDERING] Checking for spawn (interval: {spawn_interval}s)")

        # Count current wandering mobs
        wandering_count = 0
        for room_mobs in self.room_mobs.values():
            for mob in room_mobs:
                if mob.get('is_wandering'):
                    wandering_count += 1

        # Check if we're at max capacity
        max_wandering = self.config_manager.get_setting('dungeon', 'wandering_mobs', 'max_wandering_mobs', default=5)
        self.logger.debug(f"[WANDERING] Current count: {wandering_count}/{max_wandering}")
        if wandering_count >= max_wandering:
            self.logger.debug(f"[WANDERING] At max capacity, skipping spawn")
            return

        # Roll for spawn chance
        spawn_chance = self.config_manager.get_setting('dungeon', 'wandering_mobs', 'spawn_chance', default=0.3)
        roll = random.random()
        self.logger.debug(f"[WANDERING] Spawn roll: {roll:.2f} (need <= {spawn_chance})")
        if roll > spawn_chance:
            self.logger.debug(f"[WANDERING] Failed spawn roll")
            return

        # Select a random mob from the pool
        mob_pool = self.config_manager.get_setting('dungeon', 'wandering_mobs', 'mob_pool', default=[])
        if not mob_pool:
            self.logger.debug(f"[WANDERING] No mob pool configured")
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
            self.logger.debug(f"[WANDERING] Failed to select mob from pool")
            return

        self.logger.debug(f"[WANDERING] Selected mob: {selected_mob_id}")

        # Load monster data
        try:
            with open('data/npcs/monsters.json', 'r') as f:
                monsters_data = json.load(f)
            monsters = {m['id']: m for m in monsters_data}
        except Exception as e:
            self.logger.error(f"Failed to load monsters data for wandering spawn: {e}")
            return

        if selected_mob_id not in monsters:
            self.logger.debug(f"[WANDERING] Mob {selected_mob_id} not found in monsters.json")
            return

        # Get all dungeon rooms
        area_id = self.config_manager.get_setting('dungeon', 'wandering_mobs', 'area_id', default='arena_dungeon')
        dungeon_rooms = []
        for room_id, room in self.world_manager.rooms.items():
            if hasattr(room, 'area_id') and room.area_id == area_id:
                dungeon_rooms.append(room_id)

        self.logger.debug(f"[WANDERING] Found {len(dungeon_rooms)} dungeon rooms for area {area_id}")
        if not dungeon_rooms:
            self.logger.debug(f"[WANDERING] No dungeon rooms found")
            return

        # Select random room to spawn in
        spawn_room = random.choice(dungeon_rooms)

        # Spawn the wandering mob
        self._spawn_wandering_mob(spawn_room, selected_mob_id, monsters[selected_mob_id])
        self.logger.info(f"[WANDERING] Spawned {selected_mob_id} in {spawn_room}")

    def _spawn_wandering_mob(self, room_id: str, monster_id: str, monster: dict):
        """Spawn a wandering mob in a room."""
        if room_id not in self.room_mobs:
            self.room_mobs[room_id] = []

        # Generate random stats
        level = monster.get('level', 1)
        monster_type = monster.get('type', 'monster')
        stats = self._generate_mob_stats(level, monster_type)

        # Create mob instance
        mob_name = monster.get('name', 'Unknown Creature')
        spawned_mob = {
            'id': monster_id,
            'name': mob_name,
            'type': 'hostile',
            'description': monster.get('description', f'A fierce {mob_name}'),
            'level': level,
            'health': monster.get('health', 100),
            'max_health': monster.get('health', 100),
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

            'experience_reward': monster.get('experience_reward', 25),
            'gold_reward': monster.get('gold_reward', [0, 5]),
            'loot_table': monster.get('loot_table', []),
            'experience': 0,
            'gold': 0,
            'is_wandering': True  # Mark as wandering mob
        }

        self.room_mobs[room_id].append(spawned_mob)

    async def _move_wandering_mobs(self):
        """Move wandering mobs randomly between rooms."""
        movement_chance = self.config_manager.get_setting('dungeon', 'wandering_mobs', 'movement_chance', default=0.2)

        # Iterate through all rooms
        for room_id in list(self.room_mobs.keys()):
            if room_id not in self.room_mobs:
                continue

            for mob in self.room_mobs[room_id][:]:  # Copy to avoid modification during iteration
                # Skip non-wandering mobs
                if not mob.get('is_wandering'):
                    continue

                # Roll for movement
                if random.random() > movement_chance:
                    continue

                # Get current room
                room = self.world_manager.get_room(room_id)
                if not room or not hasattr(room, 'exits'):
                    continue

                # Get available exits
                exits = list(room.exits.keys())
                if not exits:
                    continue

                # Choose random exit
                direction = random.choice(exits)

                # Get destination room ID from exit object
                exit_obj = room.exits.get(direction)
                if not exit_obj:
                    continue

                destination_id = exit_obj.destination if hasattr(exit_obj, 'destination') else str(exit_obj)
                if not destination_id or destination_id not in self.world_manager.rooms:
                    continue

                # Move mob to new room
                self.room_mobs[room_id].remove(mob)
                if destination_id not in self.room_mobs:
                    self.room_mobs[destination_id] = []
                self.room_mobs[destination_id].append(mob)

                # Notify players in both rooms
                mob_name = mob.get('name', 'Unknown creature')

                # Notify players in source room
                await self._notify_room_players_sync(room_id, f"{mob_name} wanders {direction}.")

                # Notify players in destination room
                opposite_direction = self._get_opposite_direction(direction)
                arrival_msg = f"{mob_name} wanders in from the {opposite_direction}."
                await self._notify_room_players_sync(destination_id, arrival_msg)

                self.logger.debug(f"[WANDERING] {mob_name} moved from {room_id} {direction} to {destination_id}")

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
            if player_data.get('character', {}).get('room_id') == room_id:
                await self.connection_manager.send_message(player_id, message)








