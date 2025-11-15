"""Barrier system for managing locked doors, obstacles, and progression gates."""

from typing import Dict, Optional, Tuple
from ...utils.logger import get_logger


class BarrierSystem:
    """Manages barrier checking and unlocking."""

    def __init__(self, world_manager, connection_manager):
        """Initialize the barrier system."""
        self.world_manager = world_manager
        self.connection_manager = connection_manager
        self.logger = get_logger()
        self.game_engine = None  # Set by game engine after initialization

    async def check_barrier(self, player_id: int, character: Dict, room, direction: str,
                           player_name: str = "Someone") -> Tuple[bool, Optional[str]]:
        """
        Check if a barrier blocks movement in the given direction.

        Args:
            player_id: ID of the player attempting movement
            character: Player's character data
            room: Current room object
            direction: Direction of movement
            player_name: Player's display name for room notifications

        Returns:
            Tuple[bool, Optional[str]]: (can_pass, unlock_message)
            - can_pass: True if player can move through, False if blocked
            - unlock_message: Message to show if barrier was unlocked (None if already unlocked or blocked)
        """
        if direction not in room.barriers:
            return (True, None)  # No barrier

        barrier_info = room.barriers[direction]
        barrier_id = barrier_info.get('barrier_id')
        is_locked = barrier_info.get('locked', True)

        self.logger.info(f"[BARRIER] Exit {direction} has barrier '{barrier_id}', locked={is_locked}")

        # Get barrier definition
        barrier_def = self.world_manager.barriers.get(barrier_id)
        if not barrier_def:
            self.logger.error(f"[BARRIER] Barrier definition '{barrier_id}' not found!")
            # Only send message to players, not mobs (player_id >= 0)
            if player_id >= 0:
                await self.connection_manager.send_message(player_id, "Something is blocking your way.")
            # Notify room of failed attempt
            await self._notify_room_of_attempt(room, player_id, player_name, barrier_def, False)
            return (False, None)

        self.logger.info(f"[BARRIER] Found barrier definition for '{barrier_id}': {barrier_def.get('name')}")

        # Check requirements first (level, items, etc.) - these ALWAYS block, regardless of locked status
        requirements = barrier_def.get('requirements', {})
        if requirements:
            req_check = await self._check_requirements(player_id, character, requirements, barrier_def)
            if not req_check[0]:  # Requirements not met
                return req_check

        # If barrier is already unlocked and requirements passed, allow passage
        if not is_locked:
            return (True, None)

        # Barrier is locked - try to unlock it
        unlock_result = await self._try_unlock_barrier(player_id, character, barrier_info, barrier_def,
                                                       room, player_name, direction)

        return unlock_result

    async def _try_unlock_barrier(self, player_id: int, character: Dict, barrier_info: Dict,
                                  barrier_def: Dict, room, player_name: str, direction: str) -> Tuple[bool, Optional[str]]:
        """
        Attempt to unlock a barrier using available methods.

        Returns:
            Tuple[bool, Optional[str]]: (unlocked, unlock_message)
        """
        unlock_methods = barrier_def.get('unlock_methods', {})

        # Try key method first (most common)
        if 'key' in unlock_methods:
            result = await self._try_key_unlock(player_id, character, barrier_info, barrier_def,
                                               unlock_methods['key'], room, player_name, direction)
            if result[0]:  # Successfully unlocked
                return result

        # Try rune method (for magical barriers)
        if 'rune' in unlock_methods:
            result = await self._try_key_unlock(player_id, character, barrier_info, barrier_def,
                                               unlock_methods['rune'], room, player_name, direction)
            if result[0]:  # Successfully unlocked
                return result

        # Try rope method (for pits and climbing)
        if 'rope' in unlock_methods:
            result = await self._try_key_unlock(player_id, character, barrier_info, barrier_def,
                                               unlock_methods['rope'], room, player_name, direction)
            if result[0]:  # Successfully unlocked
                return result

        # Try climb method (skill-based climbing)
        if 'climb' in unlock_methods:
            result = await self._try_climb_unlock(player_id, character, barrier_info, barrier_def,
                                                 unlock_methods['climb'], room, player_name, direction)
            if result[0]:  # Successfully unlocked
                return result

        # TODO: Add other unlock methods here:
        # - pick (lockpicking for rogues)
        # - bash (strength-based door breaking)
        # - spell (knock, passwall, etc.)

        # No unlock method succeeded - show locked message and notify room
        locked_msg = barrier_def.get('locked_message', 'The way is blocked.')
        # Only send message to players, not mobs (player_id >= 0)
        if player_id >= 0:
            await self.connection_manager.send_message(player_id, locked_msg)
        await self._notify_room_of_attempt(room, player_id, player_name, barrier_def, False, direction)
        self.logger.info(f"[BARRIER] No unlock method succeeded, blocking movement")
        return (False, None)

    async def _try_key_unlock(self, player_id: int, character: Dict, barrier_info: Dict,
                              barrier_def: Dict, key_method: Dict, room, player_name: str,
                              direction: str) -> Tuple[bool, Optional[str]]:
        """
        Try to unlock barrier with a key.

        Returns:
            Tuple[bool, Optional[str]]: (unlocked, unlock_message)
        """
        if not key_method.get('enabled'):
            return (False, None)

        required_item = key_method.get('required_item')
        consumes_item = key_method.get('consumes_item', False)

        self.logger.info(f"[BARRIER] Checking for key: '{required_item}'")

        # Check if player has the required item
        has_item = False
        inventory = character.get('inventory', [])
        for item in inventory:
            if isinstance(item, dict):
                # Check multiple possible field names and formats
                item_id = item.get('id') or item.get('item_id') or item.get('name', '')
                # Normalize for comparison (lowercase, replace spaces with underscores)
                item_id_normalized = item_id.lower().replace(' ', '_')
                required_normalized = required_item.lower().replace(' ', '_')

                self.logger.debug(f"[BARRIER] Checking item: '{item_id}' (normalized: '{item_id_normalized}') vs required: '{required_item}' (normalized: '{required_normalized}')")

                if item_id_normalized == required_normalized:
                    has_item = True
                    self.logger.info(f"[BARRIER] Found matching key: '{item_id}'")
                    break
            elif isinstance(item, str):
                # String item - normalize and compare
                item_normalized = item.lower().replace(' ', '_')
                required_normalized = required_item.lower().replace(' ', '_')
                if item_normalized == required_normalized:
                    has_item = True
                    self.logger.info(f"[BARRIER] Found matching key: '{item}'")
                    break

        if not has_item:
            # Player doesn't have the key
            self.logger.info(f"[BARRIER] Player lacks required item '{required_item}'")
            return (False, None)

        # Player has the item - unlock the barrier
        self.logger.info(f"[BARRIER] Player has '{required_item}', unlocking barrier")

        # Optionally consume the item
        consumed_message = ""
        if consumes_item:
            required_normalized = required_item.lower().replace(' ', '_')
            for i, item in enumerate(inventory):
                if isinstance(item, dict):
                    # Check multiple possible field names and normalize for comparison
                    item_id = item.get('id') or item.get('item_id') or item.get('name', '')
                    item_id_normalized = item_id.lower().replace(' ', '_')

                    if item_id_normalized == required_normalized:
                        inventory.pop(i)
                        self.logger.info(f"[BARRIER] Consumed item '{item_id}'")
                        consumed_message = f"The {item_id.replace('_', ' ').lower()} crumbles to dust.\n"
                        break
                elif isinstance(item, str):
                    # String item - normalize and compare
                    item_normalized = item.lower().replace(' ', '_')
                    if item_normalized == required_normalized:
                        inventory.pop(i)
                        self.logger.info(f"[BARRIER] Consumed item '{item}'")
                        consumed_message = f"The {item.replace('_', ' ').lower()} crumbles to dust.\n"
                        break

            # Update encumbrance after consuming item
            # Note: This requires player_manager reference - we'll need to pass it or refactor
            # For now, skip encumbrance update

        # Unlock the barrier (but only for doors/gates, not obstacles like pits)
        barrier_type = barrier_def.get('type', 'locked_door')
        if barrier_type != 'obstacle':
            # Doors stay unlocked once opened
            barrier_info['locked'] = False
        # Obstacles (like pits) don't unlock - you just pass through this time

        unlock_msg = barrier_def.get('unlock_message', 'You unlock the way forward.')
        unlock_msg = unlock_msg.replace('{key}', required_item.replace('_', ' '))
        unlock_msg = unlock_msg.replace('{item}', required_item.replace('_', ' '))

        # Combine unlock message with consumption message
        full_message = unlock_msg + "\n" + consumed_message

        # Notify room of successful unlock
        await self._notify_room_of_unlock(room, player_id, player_name, barrier_def, direction)

        self.logger.info(f"[BARRIER] Barrier unlocked successfully with key")
        return (True, full_message)

    async def _try_climb_unlock(self, player_id: int, character: Dict, barrier_info: Dict,
                                barrier_def: Dict, climb_method: Dict, room, player_name: str,
                                direction: str) -> Tuple[bool, Optional[str]]:
        """
        Try to unlock barrier with climbing skill.

        Returns:
            Tuple[bool, Optional[str]]: (unlocked, unlock_message)
        """
        import random

        if not climb_method.get('enabled'):
            return (False, None)

        difficulty = climb_method.get('difficulty', 10)

        # Base chance to climb - everyone gets a tiny chance
        base_chance = 0.05  # 5% base chance for anyone

        # Get character's dexterity bonus
        dex = character.get('dexterity', 10)
        dex_modifier = (dex - 10) // 2
        dex_bonus = dex_modifier * 0.02  # +2% per dex modifier point

        # Get character's strength bonus (helps with climbing)
        strength = character.get('strength', 10)
        str_modifier = (strength - 10) // 2
        str_bonus = str_modifier * 0.02  # +2% per strength modifier point

        # Check for rogue climbing ability
        ability_bonus = 0.0
        char_class = character.get('class', '').lower()
        if char_class == 'rogue':
            # Rogues get significant climbing bonus
            level = character.get('level', 1)
            ability_bonus = 0.15 + (level * 0.01)  # 15% base + 1% per level
            self.logger.info(f"[BARRIER] Rogue climbing bonus: {ability_bonus}")

        # Calculate total success chance
        success_chance = base_chance + dex_bonus + str_bonus + ability_bonus
        success_chance = min(0.75, success_chance)  # Cap at 75%

        self.logger.info(f"[BARRIER] Climb attempt: difficulty={difficulty}, base={base_chance}, dex_bonus={dex_bonus}, str_bonus={str_bonus}, ability_bonus={ability_bonus}, total={success_chance}")

        roll = random.random()
        self.logger.info(f"[BARRIER] Climb roll: {roll} vs success_chance: {success_chance}")

        if roll < success_chance:
            # Successful climb!
            # Don't unlock the barrier - this is a one-time pass, not permanent unlock
            success_msg = climb_method.get('success_message', 'You manage to climb out.')

            # Notify room of successful climb
            await self._notify_room_of_unlock(room, player_id, player_name, barrier_def, direction)

            self.logger.info(f"[BARRIER] Successful climb!")
            return (True, success_msg)
        else:
            # Failed climb attempt
            fail_msg = "You attempt to climb but lose your grip and slide back down."
            if player_id >= 0:
                await self.connection_manager.send_message(player_id, fail_msg)

            # Notify room of failed attempt
            await self._notify_room_of_attempt(room, player_id, player_name, barrier_def, False, direction)

            self.logger.info(f"[BARRIER] Failed climb attempt")
            return (False, None)

    async def _check_requirements(self, player_id: int, character: Dict, requirements: Dict,
                                   barrier_def: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if character meets barrier requirements.

        Requirements can include:
        - min_level: Minimum level required
        - max_level: Maximum level allowed (for beginner areas)
        - required_item: Must have specific item
        - forbidden_item: Cannot have specific item
        - required_property: Must have specific character property (e.g., rune)
        - forbidden_property: Cannot have specific character property
        - required_class: Must be specific class

        Returns:
            Tuple[bool, Optional[str]]: (meets_requirements, failure_message)
        """
        # Check minimum level
        if 'min_level' in requirements:
            min_level = requirements['min_level']
            char_level = character.get('level', 1)
            if char_level < min_level:
                msg = barrier_def.get('requirement_fail_message',
                                     f"You must be at least level {min_level} to pass through here.")
                # Only send message to players, not mobs
                if player_id >= 0:
                    await self.connection_manager.send_message(player_id, msg)
                self.logger.info(f"[BARRIER] Level requirement not met: {char_level} < {min_level}")
                return (False, None)

        # Check maximum level (prevents high-level players from entering beginner areas)
        if 'max_level' in requirements:
            max_level = requirements['max_level']
            char_level = character.get('level', 1)
            if char_level > max_level:
                msg = barrier_def.get('requirement_fail_message',
                                     f"You have progressed beyond the need to go there.")
                # Only send message to players, not mobs
                if player_id >= 0:
                    await self.connection_manager.send_message(player_id, msg)
                self.logger.info(f"[BARRIER] Level too high: {char_level} > {max_level}")
                return (False, None)

        # Check for required item (must have in inventory)
        if 'required_item' in requirements:
            required_item = requirements['required_item']
            has_item = False
            inventory = character.get('inventory', [])
            for item in inventory:
                if isinstance(item, dict):
                    if item.get('id') == required_item or item.get('item_id') == required_item:
                        has_item = True
                        break
                elif item == required_item:
                    has_item = True
                    break

            if not has_item:
                msg = barrier_def.get('requirement_fail_message',
                                     f"You need a {required_item.replace('_', ' ')} to pass through here.")
                # Only send message to players, not mobs
                if player_id >= 0:
                    await self.connection_manager.send_message(player_id, msg)
                self.logger.info(f"[BARRIER] Required item missing: {required_item}")
                return (False, None)

        # Check for forbidden item (cannot have in inventory)
        if 'forbidden_item' in requirements:
            forbidden_item = requirements['forbidden_item']
            has_item = False
            inventory = character.get('inventory', [])
            for item in inventory:
                if isinstance(item, dict):
                    if item.get('id') == forbidden_item or item.get('item_id') == forbidden_item:
                        has_item = True
                        break
                elif item == forbidden_item:
                    has_item = True
                    break

            if has_item:
                msg = barrier_def.get('requirement_fail_message',
                                     f"You cannot pass through here while carrying a {forbidden_item.replace('_', ' ')}.")
                # Only send message to players, not mobs
                if player_id >= 0:
                    await self.connection_manager.send_message(player_id, msg)
                self.logger.info(f"[BARRIER] Forbidden item present: {forbidden_item}")
                return (False, None)

        # Check for required property (e.g., rune)
        if 'required_property' in requirements:
            required_prop = requirements['required_property']
            prop_name = required_prop.get('name')
            prop_value = required_prop.get('value')

            char_value = character.get(prop_name)
            if char_value != prop_value:
                msg = barrier_def.get('requirement_fail_message',
                                     f"You need {prop_name} {prop_value} to pass through here.")
                # Only send message to players, not mobs
                if player_id >= 0:
                    await self.connection_manager.send_message(player_id, msg)
                self.logger.info(f"[BARRIER] Required property missing: {prop_name}={prop_value}")
                return (False, None)

        # Check for forbidden property (e.g., cannot have white rune)
        if 'forbidden_property' in requirements:
            forbidden_prop = requirements['forbidden_property']
            prop_name = forbidden_prop.get('name')
            prop_value = forbidden_prop.get('value')

            char_value = character.get(prop_name)
            if char_value == prop_value:
                msg = barrier_def.get('requirement_fail_message',
                                     f"You cannot pass through here with {prop_name} {prop_value}.")
                # Only send message to players, not mobs
                if player_id >= 0:
                    await self.connection_manager.send_message(player_id, msg)
                self.logger.info(f"[BARRIER] Forbidden property present: {prop_name}={prop_value}")
                return (False, None)

        # Check for required class
        if 'required_class' in requirements:
            required_class = requirements['required_class']
            char_class = character.get('class', '').lower()
            if char_class != required_class.lower():
                msg = barrier_def.get('requirement_fail_message',
                                     f"Only {required_class}s may pass through here.")
                # Only send message to players, not mobs
                if player_id >= 0:
                    await self.connection_manager.send_message(player_id, msg)
                self.logger.info(f"[BARRIER] Class requirement not met: {char_class} != {required_class}")
                return (False, None)

        # All requirements met
        return (True, None)

    async def _notify_room_of_unlock(self, room, player_id: int, player_name: str,
                                     barrier_def: Dict, direction: str):
        """Notify other players in the room that a barrier was unlocked."""
        if not self.game_engine or not hasattr(self.game_engine, 'player_manager'):
            return

        barrier_name = barrier_def.get('name', 'the barrier')
        room_message = f"{player_name} unlocks {barrier_name} to the {direction}."

        if player_id < 0:
            # This is a mob - notify all players in the room
            await self.game_engine._notify_room_players_sync(room.room_id, room_message)
        else:
            # This is a player - send to all players in room except the one who unlocked it
            await self.game_engine.player_manager.notify_room_except_player(
                room.room_id, player_id, room_message
            )

    async def _notify_room_of_attempt(self, room, player_id: int, player_name: str,
                                      barrier_def: Optional[Dict], success: bool, direction: str = ""):
        """Notify other players in the room of a failed unlock attempt."""
        if not self.game_engine or not hasattr(self.game_engine, 'player_manager'):
            return

        if barrier_def:
            barrier_name = barrier_def.get('name', 'a barrier')
        else:
            barrier_name = "a barrier"

        if direction:
            room_message = f"{player_name} tries to pass through {barrier_name} to the {direction}, but fails."
        else:
            room_message = f"{player_name} tries to pass through {barrier_name}, but fails."

        if player_id < 0:
            # This is a mob - notify all players in the room
            await self.game_engine._notify_room_players_sync(room.room_id, room_message)
        else:
            # This is a player - send to all players in room except the one who attempted
            await self.game_engine.player_manager.notify_room_except_player(
                room.room_id, player_id, room_message
            )

    def get_barrier_info(self, room, direction: str) -> Optional[Dict]:
        """Get information about a barrier in a room."""
        if direction not in room.barriers:
            return None

        barrier_info = room.barriers[direction]
        barrier_id = barrier_info.get('barrier_id')
        barrier_def = self.world_manager.barriers.get(barrier_id)

        return {
            'barrier_id': barrier_id,
            'locked': barrier_info.get('locked', True),
            'definition': barrier_def
        }
