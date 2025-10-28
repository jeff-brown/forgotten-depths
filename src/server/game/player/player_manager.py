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
            print(f"[DEBUG] Saving character for '{username}': level {character.get('level')}, gold {character.get('gold')}, room {character.get('room_id')}")
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
        player_data = self.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        # Check if player is fatigued from combat
        if self.game_engine.combat_system.is_player_fatigued(player_id):
            fatigue_time = self.game_engine.combat_system.get_player_fatigue_remaining(player_id)
            await self.connection_manager.send_message(player_id,
                f"You are too exhausted from combat to move! Wait {fatigue_time:.1f} more seconds.")
            return

        character = player_data['character']
        current_room = character['room_id']
        exits = self.game_engine.world_manager.get_exits_from_room(current_room)

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

            # Check if exit is locked
            from ...utils.logger import get_logger
            logger = get_logger()

            logger.info(f"[DOOR] Player {username} attempting to move {full_direction} from {current_room} to {new_room}")

            old_room = self.game_engine.world_manager.get_room(current_room)
            unlock_message = None

            if old_room:
                logger.info(f"[DOOR] Room {current_room} locked_exits: {list(old_room.locked_exits.keys())}")

                if old_room.is_exit_locked(full_direction):
                    required_key = old_room.get_required_key(full_direction)
                    lock_desc = old_room.locked_exits[full_direction].get('description', 'The way is locked.')

                    logger.info(f"[DOOR] Exit {full_direction} IS LOCKED, required key: '{required_key}'")

                    # Check if player has the required key
                    has_key = False
                    inventory = character.get('inventory', [])
                    logger.info(f"[DOOR] Player inventory: {inventory}")

                    # Check for key by id, item_id, or by matching name
                    required_key_name = required_key.replace('_', ' ').title()
                    for item in inventory:
                        if isinstance(item, dict):
                            # Check id field
                            if item.get('id') == required_key:
                                has_key = True
                                break
                            # Check item_id field (for items created with old system)
                            if item.get('item_id') == required_key:
                                has_key = True
                                break
                            # Check name field
                            if item.get('name', '').lower() == required_key_name.lower():
                                has_key = True
                                break
                        elif item == required_key:
                            has_key = True
                            break

                    logger.info(f"[DOOR] Has required key '{required_key}': {has_key}")

                    if not has_key:
                        logger.info(f"[DOOR] Player does NOT have key, blocking movement")
                        await self.connection_manager.send_message(player_id, f"{lock_desc} You need a {required_key.replace('_', ' ')} to unlock it.")
                        return

                    # Player has the key - unlock the door, consume the key, and continue movement
                    logger.info(f"[DOOR] Player HAS key, unlocking exit '{full_direction}' and consuming key")

                    # Remove the key from inventory
                    inventory = character.get('inventory', [])
                    for i, item in enumerate(inventory):
                        should_remove = False
                        if isinstance(item, dict):
                            # Check id, item_id, or name
                            if item.get('id') == required_key:
                                should_remove = True
                            elif item.get('item_id') == required_key:
                                should_remove = True
                            elif item.get('name', '').lower() == required_key_name.lower():
                                should_remove = True
                        elif item == required_key:
                            should_remove = True

                        if should_remove:
                            removed_key = inventory.pop(i)
                            logger.info(f"[DOOR] Removed key '{required_key}' from inventory")
                            break

                    # Update encumbrance after removing key
                    self.game_engine.player_manager.update_encumbrance(character)

                    old_room.unlock_exit(full_direction)
                    unlock_message = f"You use your {required_key.replace('_', ' ')} to unlock the door. The key crumbles to dust.\n"
                else:
                    logger.info(f"[DOOR] Exit {full_direction} is NOT locked")

            # Send vendor farewell from the room being left
            if hasattr(self.game_engine, 'vendor_system'):
                await self.game_engine.vendor_system.send_vendor_farewell(player_id, current_room)

            # Check for trap triggers when exiting the room
            from ...utils.colors import error_message, announcement
            trap_result = self.game_engine.trap_system.check_trap_trigger(player_id, current_room)
            if trap_result:
                # Trap triggered while exiting!
                damage_msg = self.game_engine.trap_system.apply_trap_damage(player_id, trap_result)
                await self.connection_manager.send_message(player_id, error_message(damage_msg))

                # Notify others in the room
                trap_def = trap_result['trap_def']
                trap_msg = trap_def['trigger_message'].format(target=username)
                await self.game_engine._notify_room_except_player(current_room, player_id, announcement(trap_msg))

            # Notify others in the current room that this player is leaving
            await self.game_engine._notify_room_except_player(current_room, player_id, f"{username} has just gone {full_direction}.")

            # Move the player
            character['room_id'] = new_room

            # Track visited rooms for map functionality
            if 'visited_rooms' not in character:
                character['visited_rooms'] = set()
            if isinstance(character['visited_rooms'], list):
                character['visited_rooms'] = set(character['visited_rooms'])
            character['visited_rooms'].add(new_room)

            # Check if any wandering mobs should follow the player
            await self._check_mob_following(player_id, current_room, new_room, full_direction)

            # Send unlock message if applicable
            message = ""
            if unlock_message:
                message += unlock_message
            message += f"You go {full_direction}."
            await self.connection_manager.send_message(player_id, message)

            # Notify others in the new room that this player has arrived
            opposite_direction = self._get_opposite_direction(full_direction)
            if opposite_direction:
                await self.game_engine._notify_room_except_player(new_room, player_id, f"{username} has just arrived from {opposite_direction}.")
            else:
                await self.game_engine._notify_room_except_player(new_room, player_id, f"{username} has just arrived.")

            await self.game_engine.world_manager.send_room_description(player_id, detailed=False)

            # Send vendor greeting from the room being entered
            if hasattr(self.game_engine, 'vendor_system'):
                await self.game_engine.vendor_system.send_vendor_greeting(player_id, new_room)
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