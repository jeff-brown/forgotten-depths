"""Player management system for handling player connections, authentication, and data persistence."""

import asyncio
import time
from typing import Optional, Dict, Any

from ...persistence.player_storage import PlayerStorage
from ...utils.logger import get_logger


class PlayerManager:
    """Manages player connections, authentication, and data persistence."""

    def __init__(self, game_engine):
        """Initialize the player manager with a reference to the game engine."""
        self.game_engine = game_engine
        self.logger = get_logger()

        # Player management
        self.connected_players: Dict[int, Any] = {}
        self.logged_in_usernames: Dict[str, int] = {}  # username -> player_id mapping

    @property
    def player_storage(self) -> Optional[PlayerStorage]:
        """Get the player storage instance from the game engine."""
        return self.game_engine.player_storage

    @property
    def connection_manager(self):
        """Get the connection manager from the game engine."""
        return self.game_engine.connection_manager

    def handle_player_connect(self, player_id: int):
        """Handle a new player connection."""
        self.logger.info(f"Player {player_id} connected")

        # Initialize player session
        self.connected_players[player_id] = {
            'player_id': player_id,
            'connection_time': time.time(),
            'authenticated': False,
            'character': None,
            'login_state': 'username_prompt'
        }

        # Send initial prompts (async)
        asyncio.create_task(self._send_welcome_messages(player_id))

    async def _send_welcome_messages(self, player_id: int):
        """Send welcome messages to a new player."""
        await self.connection_manager.send_message(player_id, "Welcome to Forgotten Depths!")
        await self.connection_manager.send_message(player_id, "Username: ", add_newline=False)

    async def handle_player_disconnect(self, player_id: int):
        """Handle a player disconnection."""
        self.logger.info(f"Player {player_id} disconnected")

        if player_id in self.connected_players:
            player_data = self.connected_players[player_id]

            # Notify others in the room that this player has left
            if (player_data.get('character') and
                player_data.get('authenticated') and
                player_data.get('username')):
                username = player_data['username']
                room_id = player_data['character'].get('room_id')
                if room_id:
                    await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} has left the game.")

                # Remove from logged in users
                if username in self.logged_in_usernames:
                    del self.logged_in_usernames[username]
                    self.logger.info(f"User '{username}' logged out")

                # Clean up summoned creatures if this player is a party leader
                character = player_data.get('character')
                if character:
                    await self._despawn_player_summons(player_id, character, room_id)

                    # Disband party if this player is the leader
                    await self._disband_party_on_leader_disconnect(player_id, character)

                    # Clear following relationships
                    await self._clear_following_on_disconnect(player_id, character, username)

            # Save character if authenticated
            if player_data.get('character') and player_data.get('authenticated'):
                self.save_player_character(player_id, player_data['character'])

            # Clean up
            del self.connected_players[player_id]

    def is_user_already_logged_in(self, username: str) -> bool:
        """Check if a user is already logged in."""
        return username in self.logged_in_usernames

    def authenticate_player(self, username: str, password: str) -> bool:
        """Authenticate a player or create new account.

        Returns True if authentication successful or new account created.
        Returns False if wrong password for existing account.
        """
        if not self.player_storage:
            # No database - allow anyone
            return True

        # Try to authenticate against existing account
        self.logger.debug(f"Attempting to authenticate user '{username}'")
        player_id = self.player_storage.authenticate_player(username, password)

        if player_id is not None:
            # Authentication successful
            self.logger.info(f"User '{username}' authenticated successfully (player_id={player_id})")
            return True

        self.logger.debug(f"Authentication failed for '{username}', checking if user exists")

        # Authentication failed - check if this is a new user or wrong password
        # Try to load character data to see if user exists
        existing_char = self.player_storage.load_character_data(username)

        if existing_char is not None:
            # User exists but wrong password
            self.logger.warning(f"Failed login attempt for user '{username}' - wrong password")
            return False

        self.logger.debug(f"User '{username}' doesn't exist, creating new account")

        # User doesn't exist - create new account
        try:
            new_player_id = self.player_storage.create_player(username, password)
            self.logger.info(f"Created new player account: {username} (id={new_player_id})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create player {username}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def save_player_character(self, player_id: int, character: Dict[str, Any]):
        """Save a player's character to the database.

        Args:
            player_id: The player's connection ID
            character: The character data dict to save
        """
        if not self.player_storage:
            return

        try:
            # Get the player's username
            player_data = self.connected_players.get(player_id)
            if not player_data:
                return

            username = player_data.get('username')
            if not username:
                self.logger.warning(f"Cannot save character for player {player_id}: no username")
                return

            # Save the character data
            import json
            char_json = json.dumps(character)
            char_size_kb = len(char_json) / 1024
            num_inventory = len(character.get('inventory', []))
            num_effects = len(character.get('active_effects', []))
            num_cooldowns = len(character.get('spell_cooldowns', {}))
            print(f"[DEBUG] Saving character for '{username}': level {character.get('level')}, gold {character.get('gold')}, room {character.get('room_id')}, size={char_size_kb:.1f}KB, inv={num_inventory}, effects={num_effects}, cooldowns={num_cooldowns}")
            success = self.player_storage.save_character_data(username, character)
            if success:
                self.logger.info(f"Successfully saved character data for {username}")
                print(f"[DEBUG] Save confirmed for '{username}'")
            else:
                self.logger.error(f"Failed to save character data for {username}")
                print(f"[DEBUG] Save FAILED for '{username}'")

        except Exception as e:
            self.logger.error(f"Failed to save character for player {player_id}: {e}")

    def save_all_players(self):
        """Save all connected players."""
        for player_id, player_data in self.connected_players.items():
            if player_data.get('character') and player_data.get('authenticated'):
                self.save_player_character(player_id, player_data['character'])

    def on_player_connected(self, data):
        """Event handler for player connection."""
        self.logger.debug(f"Player connected event: {data}")

    def on_player_disconnected(self, data):
        """Event handler for player disconnection."""
        self.logger.debug(f"Player disconnected event: {data}")

    def on_player_command(self, data):
        """Event handler for player command."""
        self.logger.debug(f"Player command event: {data}")

    def get_connected_player_count(self) -> int:
        """Get the number of connected players."""
        return len(self.connected_players)

    def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a connected player."""
        return self.connected_players.get(player_id)

    def get_player_data(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player data for a specific player ID."""
        return self.connected_players.get(player_id)

    def is_player_authenticated(self, player_id: int) -> bool:
        """Check if a player is authenticated."""
        player_data = self.connected_players.get(player_id)
        return player_data.get('authenticated', False) if player_data else False

    def get_player_character(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get a player's character data."""
        player_data = self.connected_players.get(player_id)
        return player_data.get('character') if player_data else None

    def set_player_character(self, player_id: int, character: Dict[str, Any]):
        """Set a player's character data."""
        if player_id in self.connected_players:
            self.connected_players[player_id]['character'] = character

    def set_player_authenticated(self, player_id: int, authenticated: bool = True):
        """Set a player's authentication status."""
        if player_id in self.connected_players:
            self.connected_players[player_id]['authenticated'] = authenticated

    def get_player_username(self, player_id: int) -> Optional[str]:
        """Get a player's username."""
        player_data = self.connected_players.get(player_id)
        return player_data.get('username') if player_data else None

    def set_player_username(self, player_id: int, username: str):
        """Set a player's username."""
        if player_id in self.connected_players:
            self.connected_players[player_id]['username'] = username

    def get_player_login_state(self, player_id: int) -> Optional[str]:
        """Get a player's login state."""
        player_data = self.connected_players.get(player_id)
        return player_data.get('login_state') if player_data else None

    def set_player_login_state(self, player_id: int, login_state: str):
        """Set a player's login state."""
        if player_id in self.connected_players:
            self.connected_players[player_id]['login_state'] = login_state

    def get_players_in_room(self, room_id: str, exclude_player_id: Optional[int] = None) -> list:
        """Get all players in a specific room."""
        players_in_room = []
        for player_id, player_data in self.connected_players.items():
            if (player_data.get('character') and
                player_data['character'].get('room_id') == room_id and
                (exclude_player_id is None or player_id != exclude_player_id)):
                players_in_room.append({
                    'player_id': player_id,
                    'username': player_data.get('username', f'player_{player_id}'),
                    'character': player_data['character']
                })
        return players_in_room

    def is_player_connected(self, player_id: int) -> bool:
        """Check if a player is currently connected."""
        return player_id in self.connected_players

    def get_all_connected_players(self) -> Dict[int, Any]:
        """Get all connected players data."""
        return self.connected_players.copy()

    async def move_player(self, player_id: int, direction: str):
        """Move a player in a direction."""
        import time
        move_start = time.time()
        timings = {}

        t0 = time.time()
        player_data = self.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return
        timings['get_player'] = time.time() - t0

        # Check if player is fatigued from combat
        t0 = time.time()
        if self.game_engine.combat_system.is_player_fatigued(player_id):
            fatigue_time = self.game_engine.combat_system.get_player_fatigue_remaining(player_id)
            await self.connection_manager.send_message(player_id,
                f"You are too exhausted from combat to move! Wait {fatigue_time:.1f} more seconds.")
            return
        timings['fatigue_check'] = time.time() - t0

        character = player_data['character']

        # Check if player is paralyzed
        t0 = time.time()
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze':
                await self.connection_manager.send_message(player_id,
                    "You are paralyzed and cannot move!")
                return
        timings['paralyze_check'] = time.time() - t0

        t0 = time.time()
        current_room = character['room_id']
        exits = self.game_engine.world_manager.get_exits_from_room(current_room)
        timings['get_exits'] = time.time() - t0

        # Map short directions to full names
        direction_map = {
            'n': 'north', 's': 'south', 'e': 'east', 'w': 'west',
            'ne': 'northeast', 'nw': 'northwest',
            'se': 'southeast', 'sw': 'southwest',
            'u': 'up', 'd': 'down'
        }

        full_direction = direction_map.get(direction, direction)

        if full_direction in exits:
            new_room = exits[full_direction]
            username = player_data.get('username', 'Someone')

            # Check barriers using the barrier system
            t0 = time.time()
            old_room = self.game_engine.world_manager.get_room(current_room)
            unlock_message = None

            if old_room:
                # Use barrier system to check if movement is allowed
                if hasattr(self.game_engine, 'barrier_system'):
                    can_pass, unlock_msg = await self.game_engine.barrier_system.check_barrier(
                        player_id, character, old_room, full_direction, username
                    )

                    if not can_pass:
                        # Barrier blocked movement
                        return

                    if unlock_msg:
                        unlock_message = unlock_msg
            timings['barrier_check'] = time.time() - t0

            # Send vendor farewell from the room being left
            t0 = time.time()
            if hasattr(self.game_engine, 'vendor_system'):
                await self.game_engine.vendor_system.send_vendor_farewell(player_id, current_room)
            timings['vendor_farewell'] = time.time() - t0

            # Notify others in the current room that this player is leaving
            t0 = time.time()
            await self.game_engine._notify_room_except_player(current_room, player_id, f"{username} has just gone {full_direction}.")
            timings['notify_leave'] = time.time() - t0

            # Move the player
            character['room_id'] = new_room

            # Check for trap triggers when entering the new room
            # Pass the direction we're entering from (opposite of travel direction)
            from ...utils.colors import damage_to_player, announcement, success_message

            # Map travel direction to entry direction (reverse)
            opposite_directions = {
                'north': 'south', 'south': 'north',
                'east': 'west', 'west': 'east',
                'northeast': 'southwest', 'southwest': 'northeast',
                'northwest': 'southeast', 'southeast': 'northwest',
                'up': 'down', 'down': 'up'
            }
            entry_direction = opposite_directions.get(full_direction, full_direction)

            t0 = time.time()
            trap_result = self.game_engine.trap_system.check_trap_trigger(player_id, new_room, entry_direction)
            timings['trap_check'] = time.time() - t0
            if trap_result:
                # Check if player avoided the trap
                if trap_result.get('avoided'):
                    # Player successfully avoided the trap
                    await self.connection_manager.send_message(player_id, success_message(trap_result['message']))
                    # Notify others in the room
                    await self.game_engine._notify_room_except_player(
                        new_room, player_id,
                        f"{username} nimbly avoids a hidden trap!"
                    )
                else:
                    # Trap triggered upon entering!
                    damage_msg = await self.game_engine.trap_system.apply_trap_damage(player_id, trap_result)

                    # Only send message if damage_msg is not empty (pit traps handle their own messages)
                    if damage_msg:
                        await self.connection_manager.send_message(player_id, damage_to_player(damage_msg))

                        # Notify others in the room
                        trap_def = trap_result['trap_def']
                        trap_msg = trap_def['trigger_message'].format(target=username)
                        await self.game_engine._notify_room_except_player(new_room, player_id, announcement(trap_msg))

                    # If pit trap teleported player, stop movement processing (don't show normal entry messages)
                    if trap_result.get('trap_config', {}).get('type') == 'pit':
                        return

            # Track visited rooms for map functionality
            if 'visited_rooms' not in character:
                character['visited_rooms'] = []
            # Keep as list for JSON serialization
            if new_room not in character['visited_rooms']:
                character['visited_rooms'].append(new_room)

            # Check if any wandering mobs should follow the player
            t0 = time.time()
            await self._check_mob_following(player_id, current_room, new_room, full_direction)
            timings['mob_following'] = time.time() - t0

            # Send unlock message if applicable
            t0 = time.time()
            message = ""
            if unlock_message:
                message += unlock_message
            message += f"You go {full_direction}."
            await self.connection_manager.send_message(player_id, message)
            timings['send_move_msg'] = time.time() - t0

            # Notify others in the new room that this player has arrived
            t0 = time.time()
            opposite_direction = self._get_opposite_direction(full_direction)
            if opposite_direction:
                await self.game_engine._notify_room_except_player(new_room, player_id, f"{username} has just arrived from {opposite_direction}.")
            else:
                await self.game_engine._notify_room_except_player(new_room, player_id, f"{username} has just arrived.")
            timings['notify_arrive'] = time.time() - t0

            t0 = time.time()
            await self.game_engine.world_manager.send_room_description(player_id, detailed=False)
            timings['room_desc'] = time.time() - t0

            # Move followers if any players are following this player
            t0 = time.time()
            await self._move_followers(player_id, current_room, new_room, full_direction, username)
            timings['move_followers'] = time.time() - t0

            # Move summoned creatures if this player is a party leader with summons
            t0 = time.time()
            await self._move_summons(player_id, current_room, new_room, full_direction, username)
            timings['move_summons'] = time.time() - t0

            # Send vendor greeting from the room being entered
            t0 = time.time()
            if hasattr(self.game_engine, 'vendor_system'):
                await self.game_engine.vendor_system.send_vendor_greeting(player_id, new_room)
            timings['vendor_greeting'] = time.time() - t0

            # Log movement timing
            move_duration = time.time() - move_start
            if move_duration > 0.1:  # Log if movement takes >100ms
                slow_parts = [(k, v) for k, v in timings.items() if v > 0.05]
                slow_parts.sort(key=lambda x: x[1], reverse=True)
                breakdown = ", ".join([f"{k}={v*1000:.0f}ms" for k, v in slow_parts[:5]])
                self.logger.warning(f"[MOVE_PERF] Slow movement for player {player_id}: {move_duration*1000:.0f}ms (top: {breakdown})")
        else:
            available = ", ".join(exits.keys()) if exits else "none"
            await self.connection_manager.send_message(player_id, f"You can't go {direction}. Available exits: {available}")

    def _get_opposite_direction(self, direction: str) -> str:
        """Get the opposite direction for arrival messages."""
        opposite_map = {
            'north': 'south', 'south': 'north',
            'east': 'west', 'west': 'east',
            'northeast': 'southwest', 'southwest': 'northeast',
            'northwest': 'southeast', 'southeast': 'northwest',
            'up': 'below', 'down': 'above',
            'window': 'window'  # Special case for bidirectional exits
        }
        return opposite_map.get(direction, None)

    async def _check_mob_following(self, player_id: int, old_room_id: str, new_room_id: str, direction: str):
        """Check if any wandering mobs should follow the player.

        Args:
            player_id: The player who just moved
            old_room_id: The room the player left
            new_room_id: The room the player entered
            direction: The direction the player moved
        """
        import random
        from ...utils.logger import get_logger
        logger = get_logger()

        # Get follow chance from config
        follow_chance = self.game_engine.config_manager.get_setting('combat', 'mob_follow', 'follow_chance', default=0.4)

        logger.info(f"[FOLLOW] Checking mob following from {old_room_id} to {new_room_id}, follow_chance={follow_chance}")

        # Check if there are any mobs in the old room
        if old_room_id not in self.game_engine.room_mobs:
            logger.debug(f"[FOLLOW] No mobs in room {old_room_id}")
            return

        logger.info(f"[FOLLOW] Found {len(self.game_engine.room_mobs[old_room_id])} mobs in old room")

        mobs_to_follow = []

        for mob in self.game_engine.room_mobs[old_room_id][:]:  # Copy to avoid modification during iteration
            # Only wandering mobs can follow
            if not mob.get('is_wandering'):
                logger.debug(f"[FOLLOW] {mob.get('name')} is not a wandering mob, is_wandering={mob.get('is_wandering')}")
                continue

            # Skip if mob is dead
            if mob.get('health', 0) <= 0:
                logger.debug(f"[FOLLOW] {mob.get('name')} is dead")
                continue

            # Roll for follow chance
            roll = random.random()
            if roll >= follow_chance:
                logger.debug(f"[FOLLOW] {mob.get('name')} failed follow roll: {roll:.2f} >= {follow_chance}")
                continue

            logger.info(f"[FOLLOW] {mob.get('name')} passed follow roll: {roll:.2f} < {follow_chance}")

            # Get the exit from old room
            old_room = self.game_engine.world_manager.get_room(old_room_id)
            if not old_room:
                continue

            # Check if mob can follow through this exit
            exit_obj = old_room.exits.get(direction)
            if not exit_obj:
                logger.debug(f"[FOLLOW] No exit {direction} found in room")
                continue

            # Check if exit is locked
            if old_room.is_exit_locked(direction):
                logger.debug(f"[FOLLOW] {mob.get('name')} cannot follow - exit {direction} is locked")
                continue

            # Check if destination is a safe room
            dest_room = self.game_engine.world_manager.get_room(new_room_id)
            if dest_room and hasattr(dest_room, 'is_safe') and dest_room.is_safe:
                logger.debug(f"[FOLLOW] {mob.get('name')} cannot follow - destination is a safe room")
                continue

            # This mob will follow
            logger.info(f"[FOLLOW] {mob.get('name')} will follow")
            mobs_to_follow.append(mob)

        # Move the mobs that are following
        for mob in mobs_to_follow:
            mob_name = mob.get('name', 'Unknown creature')

            # Remove from old room
            if old_room_id in self.game_engine.room_mobs:
                self.game_engine.room_mobs[old_room_id] = [m for m in self.game_engine.room_mobs[old_room_id] if m != mob]

            # Add to new room
            if new_room_id not in self.game_engine.room_mobs:
                self.game_engine.room_mobs[new_room_id] = []
            self.game_engine.room_mobs[new_room_id].append(mob)

            # Notify players in old room
            for pid, player_data in self.connected_players.items():
                if player_data.get('character', {}).get('room_id') == old_room_id:
                    await self.connection_manager.send_message(
                        pid,
                        f"{mob_name} follows {direction}."
                    )

            # Notify players in new room (including the player who moved)
            for pid, player_data in self.connected_players.items():
                if player_data.get('character', {}).get('room_id') == new_room_id:
                    await self.connection_manager.send_message(
                        pid,
                        f"{mob_name} follows you into the room!"
                    )

            logger.info(f"[FOLLOW] {mob_name} followed player from {old_room_id} to {new_room_id} via {direction}")

    async def _move_followers(self, leader_id: int, old_room_id: str, new_room_id: str, direction: str, leader_name: str):
        """Move any players who are following this player.

        Args:
            leader_id: The player who just moved
            old_room_id: The room the leader left
            new_room_id: The room the leader entered
            direction: The direction the leader moved
            leader_name: The name of the leader (for messages)
        """
        from ...utils.logger import get_logger
        logger = get_logger()

        # Find all players following this leader
        for follower_id, follower_data in self.connected_players.items():
            if follower_id == leader_id:
                continue

            follower_char = follower_data.get('character')
            if not follower_char:
                continue

            # Check if this player is following the leader
            if follower_char.get('following') != leader_id:
                continue

            # Check if follower is in the same room as the old room (where leader was)
            if follower_char.get('room_id') != old_room_id:
                # Follower lost the leader
                follower_name = follower_data.get('username', 'Someone')
                await self.connection_manager.send_message(
                    follower_id,
                    f"You lose sight of {leader_name} and stop following."
                )
                follower_char['following'] = None
                # Remove from leader's followers list
                leader_data = self.connected_players.get(leader_id)
                if leader_data and leader_data.get('character'):
                    leader_char = leader_data['character']
                    if 'followers' in leader_char and follower_id in leader_char['followers']:
                        leader_char['followers'].remove(follower_id)
                continue

            # Check if follower is in combat - cannot follow while fighting
            if follower_id in self.game_engine.combat_system.player_combats:
                follower_name = follower_data.get('username', 'Someone')
                await self.connection_manager.send_message(
                    follower_id,
                    f"You are in combat and cannot follow {leader_name}!"
                )
                continue

            # Check if follower is fatigued
            if self.game_engine.combat_system.is_player_fatigued(follower_id):
                follower_name = follower_data.get('username', 'Someone')
                fatigue_time = self.game_engine.combat_system.get_player_fatigue_remaining(follower_id)
                await self.connection_manager.send_message(
                    follower_id,
                    f"You are too exhausted to follow {leader_name}! Wait {fatigue_time:.1f} more seconds."
                )
                continue

            # Check if follower is paralyzed
            active_effects = follower_char.get('active_effects', [])
            is_paralyzed = any(
                effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze'
                for effect in active_effects
            )
            if is_paralyzed:
                await self.connection_manager.send_message(
                    follower_id,
                    f"You are paralyzed and cannot follow {leader_name}!"
                )
                continue

            # Move the follower
            follower_name = follower_data.get('username', 'Someone')
            logger.info(f"[PARTY_FOLLOW] {follower_name} (ID {follower_id}) following {leader_name} {direction}")

            # Notify others in old room that follower is leaving
            await self.notify_room_except_player(
                old_room_id,
                follower_id,
                f"{follower_name} follows {leader_name} {direction}."
            )

            # Move follower to new room
            follower_char['room_id'] = new_room_id

            # Track visited rooms
            if 'visited_rooms' not in follower_char:
                follower_char['visited_rooms'] = []
            # Keep as list for JSON serialization
            if new_room_id not in follower_char['visited_rooms']:
                follower_char['visited_rooms'].append(new_room_id)

            # Notify follower
            await self.connection_manager.send_message(
                follower_id,
                f"You follow {leader_name} {direction}."
            )

            # Notify others in new room
            opposite_direction = self._get_opposite_direction(direction)
            if opposite_direction:
                await self.notify_room_except_player(
                    new_room_id,
                    follower_id,
                    f"{follower_name} has just arrived from {opposite_direction}, following {leader_name}."
                )
            else:
                await self.notify_room_except_player(
                    new_room_id,
                    follower_id,
                    f"{follower_name} has just arrived, following {leader_name}."
                )

            # Send room description to follower
            await self.game_engine.world_manager.send_room_description(follower_id, detailed=False)

            logger.info(f"[PARTY_FOLLOW] {follower_name} successfully followed to {new_room_id}")

    async def _move_summons(self, leader_id: int, old_room_id: str, new_room_id: str, direction: str, leader_name: str):
        """Move any summoned creatures belonging to this player's party.

        Args:
            leader_id: The player who just moved
            old_room_id: The room the player left
            new_room_id: The room the player entered
            direction: The direction the player moved
            leader_name: The name of the player (for messages)
        """
        from ...utils.logger import get_logger
        logger = get_logger()

        # Get the player's character
        player_data = self.connected_players.get(leader_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        party_leader_id = character.get('party_leader', leader_id)

        # Get the party leader's character to access summons
        if party_leader_id == leader_id:
            leader_char = character
        else:
            leader_player_data = self.connected_players.get(party_leader_id)
            if not leader_player_data or not leader_player_data.get('character'):
                return
            leader_char = leader_player_data['character']

        # Get list of summoned party members from the party leader
        summoned_members = leader_char.get('summoned_party_members', [])
        if not summoned_members:
            return

        # Find summons in the old room that belong to this party
        if old_room_id not in self.game_engine.room_mobs:
            return

        mobs_in_old_room = self.game_engine.room_mobs[old_room_id]
        mobs_to_move = []

        for mob in mobs_in_old_room:
            if not mob:
                continue

            # Check if this is a summoned creature belonging to our party
            summon_id = mob.get('summon_instance_id')
            if summon_id and summon_id in summoned_members:
                # Check if summon's party leader matches (extra safety check)
                if mob.get('party_leader') == party_leader_id:
                    mobs_to_move.append(mob)

        # Move each summon
        for mob in mobs_to_move:
            mob_name = mob.get('name', 'creature')

            # Notify old room
            await self.game_engine._notify_room_players_sync(
                old_room_id,
                f"{mob_name} follows {leader_name} {direction}."
            )

            # Remove from old room
            self.game_engine.room_mobs[old_room_id].remove(mob)

            # Add to new room
            if new_room_id not in self.game_engine.room_mobs:
                self.game_engine.room_mobs[new_room_id] = []
            self.game_engine.room_mobs[new_room_id].append(mob)

            # Notify new room
            opposite_direction = self._get_opposite_direction(direction)
            if opposite_direction:
                await self.game_engine._notify_room_players_sync(
                    new_room_id,
                    f"{mob_name} has just arrived from {opposite_direction}, following {leader_name}."
                )
            else:
                await self.game_engine._notify_room_players_sync(
                    new_room_id,
                    f"{mob_name} has just arrived, following {leader_name}."
                )

            logger.info(f"[SUMMON_FOLLOW] {mob_name} (summon of {leader_name}) followed from {old_room_id} to {new_room_id} via {direction}")

    async def _despawn_player_summons(self, player_id: int, character: dict, room_id: str):
        """Despawn all summoned creatures belonging to a player when they logout or die.

        Args:
            player_id: The player ID
            character: The player's character data
            room_id: The room where the player is/was
        """
        from ...utils.logger import get_logger
        logger = get_logger()

        # Check if this player is a party leader with summons
        party_leader_id = character.get('party_leader', player_id)
        if party_leader_id != player_id:
            # Not a party leader, no summons to clean up
            return

        summoned_members = character.get('summoned_party_members', [])
        if not summoned_members:
            return

        # Find and remove all summons across all rooms
        rooms_with_summons = []
        for room_check_id, mobs in list(self.game_engine.room_mobs.items()):
            for mob in mobs[:]:  # Create copy to avoid modification during iteration
                if not mob:
                    continue

                summon_id = mob.get('summon_instance_id')
                if summon_id and summon_id in summoned_members:
                    # This is one of the player's summons
                    mob_name = mob.get('name', 'creature')

                    # Notify room that summon is despawning
                    await self.game_engine._notify_room_players_sync(
                        room_check_id,
                        f"{mob_name} fades away as its summoner departs."
                    )

                    # Remove summon from room
                    self.game_engine.room_mobs[room_check_id].remove(mob)

                    logger.info(f"[SUMMON_DESPAWN] Despawned {mob_name} (summon of player {player_id}) from room {room_check_id} due to player disconnect")

        # Clear summoned party members list
        character['summoned_party_members'] = []

    async def _disband_party_on_leader_disconnect(self, player_id: int, character: dict):
        """Disband the party when the party leader disconnects.

        Args:
            player_id: The disconnecting player's ID
            character: The disconnecting player's character data
        """
        from ...utils.logger import get_logger
        logger = get_logger()

        # Check if this player is a party leader
        party_leader_id = character.get('party_leader', player_id)
        if party_leader_id != player_id:
            # Not a leader, just remove from their leader's party
            leader_player_data = self.connected_players.get(party_leader_id)
            if leader_player_data and leader_player_data.get('character'):
                leader_char = leader_player_data['character']
                party_members = leader_char.get('party_members', [])
                if player_id in party_members:
                    party_members.remove(player_id)
                    logger.info(f"[PARTY] Removed disconnecting player {player_id} from party leader {party_leader_id}'s party")
            return

        # Player is a party leader - check if they have party members
        party_members = character.get('party_members', [player_id])

        # If only member is themselves, nothing to do
        if len(party_members) <= 1:
            return

        logger.info(f"[PARTY] Disbanding party for disconnecting leader {player_id} ({character.get('name')})")

        # Notify all party members that the party is being disbanded
        leader_name = character.get('name', 'The party leader')

        for member_id in party_members:
            if member_id == player_id:
                continue  # Skip the disconnecting leader

            # Get member's character - use actual reference from connected_players
            member_player_data = self.connected_players.get(member_id)
            if member_player_data and member_player_data.get('character'):
                member_char = member_player_data['character']

                # Reset member's party data
                member_char['party_leader'] = member_id
                if 'party_members' in member_char:
                    del member_char['party_members']

                # Clear following status if following anyone
                if member_char.get('following'):
                    following_id = member_char.get('following')
                    member_char['following'] = None

                    # Remove from target's followers list if still connected
                    if following_id in self.connected_players:
                        target_data = self.connected_players[following_id]
                        if target_data.get('character'):
                            target_char = target_data['character']
                            if 'followers' in target_char and member_id in target_char['followers']:
                                target_char['followers'].remove(member_id)

                # Notify member
                await self.connection_manager.send_message(
                    member_id,
                    f"{leader_name} has left the game. The party has been disbanded."
                )

                logger.info(f"[PARTY] Removed player {member_id} from disbanded party")

        # Clear leader's party data
        character['party_leader'] = player_id
        if 'party_members' in character:
            del character['party_members']

    async def _clear_following_on_disconnect(self, player_id: int, character: dict, username: str):
        """Clear following relationships when a player disconnects.

        Args:
            player_id: The disconnecting player's ID
            character: The disconnecting player's character data
            username: The disconnecting player's username
        """
        from ...utils.logger import get_logger
        logger = get_logger()

        # Case 1: This player is following someone - notify the leader
        if character.get('following'):
            leader_id = character['following']
            character['following'] = None

            # Remove from leader's followers list
            leader_data = self.connected_players.get(leader_id)
            if leader_data and leader_data.get('character'):
                leader_char = leader_data['character']
                if 'followers' in leader_char and player_id in leader_char['followers']:
                    leader_char['followers'].remove(player_id)
                    await self.connection_manager.send_message(
                        leader_id,
                        f"{username} has stopped following you (disconnected)."
                    )
                    logger.info(f"[FOLLOW] Player {player_id} stopped following {leader_id} due to disconnect")

        # Case 2: This player has followers - notify them all
        if character.get('followers'):
            followers = character.get('followers', []).copy()
            for follower_id in followers:
                follower_data = self.connected_players.get(follower_id)
                if follower_data and follower_data.get('character'):
                    follower_char = follower_data['character']
                    follower_char['following'] = None
                    follower_name = follower_data.get('username', 'Someone')
                    await self.connection_manager.send_message(
                        follower_id,
                        f"{username} has left the game. You stop following."
                    )
                    logger.info(f"[FOLLOW] Player {follower_id} stopped following {player_id} due to leader disconnect")

            # Clear followers list
            character['followers'] = []

    async def notify_room_except_player(self, room_id: str, exclude_player_id: int, message: str):
        """Send a message to all players in a room except the specified player."""
        for player_id, player_data in self.connected_players.items():
            if (player_id != exclude_player_id and
                player_data.get('character') and
                player_data['character'].get('room_id') == room_id):
                await self.connection_manager.send_message(player_id, message)

    def calculate_encumbrance(self, character: Dict[str, Any]) -> int:
        """Calculate total encumbrance from inventory, equipped items, and gold.

        Args:
            character: The character dict

        Returns:
            Total encumbrance weight
        """
        total_weight = 0

        # Add weight from inventory items
        for item in character.get('inventory', []):
            total_weight += item.get('weight', 0)

        # Add weight from equipped items
        equipped = character.get('equipped', {})
        for slot, item in equipped.items():
            if item:
                total_weight += item.get('weight', 0)

        # Add weight from gold (100 gold = 1 weight unit)
        gold_weight = character.get('gold', 0) / 100.0

        total_weight += gold_weight

        return round(total_weight, 2)

    def calculate_max_encumbrance(self, character: Dict[str, Any]) -> int:
        """Calculate max encumbrance based on character's strength.

        Args:
            character: The character dict

        Returns:
            Maximum encumbrance capacity
        """
        strength = character.get('strength', 10)
        # Base formula: Strength * 100
        # A character with 10 strength can carry 1000 weight
        # A character with 20 strength can carry 2000 weight
        return strength * 100

    def update_encumbrance(self, character: Dict[str, Any]):
        """Update the character's encumbrance value based on current inventory.

        Args:
            character: The character dict to update
        """
        character['encumbrance'] = self.calculate_encumbrance(character)
        character['max_encumbrance'] = self.calculate_max_encumbrance(character)