"""Trap system for handling room traps and their effects."""

import random
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from ...utils.logger import get_logger


class TrapType:
    """Defines trap types and their base properties."""

    _trap_data: Dict[str, Any] = {}
    _loaded: bool = False

    @classmethod
    def _load_traps(cls):
        """Load trap definitions from JSON file."""
        if cls._loaded:
            return

        trap_file = Path("data/traps/traps.json")
        if not trap_file.exists():
            logger = get_logger()
            logger.error(f"Trap data file not found: {trap_file}")
            cls._trap_data = {}
            cls._loaded = True
            return

        try:
            with open(trap_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cls._trap_data = data.get('traps', {})
                cls._loaded = True
                logger = get_logger()
                logger.info(f"Loaded {len(cls._trap_data)} trap types from {trap_file}")
        except Exception as e:
            logger = get_logger()
            logger.error(f"Error loading trap data: {e}")
            cls._trap_data = {}
            cls._loaded = True

    @classmethod
    def get_trap(cls, trap_type: str) -> Optional[Dict[str, Any]]:
        """Get trap definition by type."""
        cls._load_traps()
        return cls._trap_data.get(trap_type.lower())


class TrapSystem:
    """Manages trap triggers, detection, and disarming."""

    def __init__(self, game_engine):
        """Initialize the trap system."""
        self.game_engine = game_engine
        self.logger = get_logger()
        self.room_trap_states = {}  # room_id -> {trap_index: {triggered: bool, disarmed: bool, trigger_time: float}}
        self.player_trap_awareness = {}  # player_id -> {room_id: [detected_trap_indices]}

    def get_room_traps(self, room_id: str) -> List[Dict[str, Any]]:
        """Get traps for a room from world data."""
        room = self.game_engine.world_manager.rooms.get(room_id)
        if not room:
            return []

        room_data = self.game_engine.world_manager.rooms_data.get(room_id, {})
        return room_data.get('traps', [])

    def initialize_room_traps(self, room_id: str):
        """Initialize trap states for a room if not already initialized."""
        if room_id not in self.room_trap_states:
            traps = self.get_room_traps(room_id)
            self.room_trap_states[room_id] = {}
            for i in range(len(traps)):
                self.room_trap_states[room_id][i] = {
                    'triggered': False,
                    'disarmed': False,
                    'trigger_time': 0,
                }

    def reset_expired_traps(self, room_id: str):
        """Reset traps that have been triggered longer than their reset time."""
        if room_id not in self.room_trap_states:
            return

        traps = self.get_room_traps(room_id)
        current_time = time.time()

        for i, trap_config in enumerate(traps):
            trap_state = self.room_trap_states[room_id].get(i, {})

            # Skip disarmed traps (they stay disarmed)
            if trap_state.get('disarmed'):
                continue

            # Check if trap is triggered and should reset
            if trap_state.get('triggered'):
                trigger_time = trap_state.get('trigger_time', 0)
                reset_time = trap_config.get('reset_time', 300)  # Default 5 minutes

                if current_time - trigger_time >= reset_time:
                    # Reset the trap
                    self.room_trap_states[room_id][i]['triggered'] = False
                    self.room_trap_states[room_id][i]['trigger_time'] = 0
                    self.logger.info(f"[TRAP] Trap {i} in room {room_id} has reset")

    def check_trap_trigger(self, player_id: int, room_id: str) -> Optional[Dict[str, Any]]:
        """Check if player triggers a trap when entering a room."""
        self.initialize_room_traps(room_id)
        self.reset_expired_traps(room_id)

        traps = self.get_room_traps(room_id)
        if not traps:
            return None

        self.logger.info(f"[TRAP] Checking {len(traps)} trap(s) in room {room_id}")

        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return None

        character = player_data['character']

        # Check each trap
        for i, trap_config in enumerate(traps):
            trap_state = self.room_trap_states[room_id].get(i, {})

            # Skip if already triggered or disarmed
            if trap_state.get('triggered') or trap_state.get('disarmed'):
                continue

            # Get trap definition
            trap_type = trap_config.get('type')
            trap_def = TrapType.get_trap(trap_type)
            if not trap_def:
                self.logger.warning(f"[TRAP] Unknown trap type '{trap_type}' in room {room_id}")
                continue

            # Trigger chance (can be modified by player stats/skills)
            trigger_chance = trap_config.get('trigger_chance', 0.5)

            # Dexterity can help avoid traps
            dex = character.get('dexterity', 10)
            dex_modifier = (dex - 10) // 2
            trigger_chance = max(0.1, trigger_chance - (dex_modifier * 0.1))

            if random.random() < trigger_chance:
                # Check for passive trap avoidance ability (e.g., Rogue's Trap Sense)
                ability_effect = self.game_engine.ability_system.check_passive_ability(
                    character,
                    'on_trigger_trap',
                    {'trap_type': trap_type}
                )

                if ability_effect and ability_effect.get('type') == 'avoid_chance':
                    avoid_chance = ability_effect.get('value', 0.0)
                    if random.random() < avoid_chance:
                        # Ability saved from trap!
                        self.logger.info(f"[TRAP] {trap_def['name']} avoided by ability in room {room_id}!")
                        # Don't mark trap as triggered, player avoided it
                        continue

                # Trap triggered!
                self.logger.info(f"[TRAP] {trap_def['name']} triggered in room {room_id}!")
                self.room_trap_states[room_id][i]['triggered'] = True
                self.room_trap_states[room_id][i]['trigger_time'] = time.time()
                return {
                    'trap_index': i,
                    'trap_def': trap_def,
                    'trap_config': trap_config,
                }

        return None

    def apply_trap_damage(self, player_id: int, trap_result: Dict[str, Any]) -> str:
        """Apply trap damage and effects to a player."""
        trap_def = trap_result['trap_def']
        trap_config = trap_result['trap_config']

        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return ""

        character = player_data['character']
        username = player_data.get('username', 'Someone')

        # Calculate damage
        damage_dice = trap_def.get('damage', '1d6')
        damage = self._roll_dice(damage_dice)

        # Apply any damage multipliers from trap config
        damage_multiplier = trap_config.get('damage_multiplier', 1.0)
        damage = int(damage * damage_multiplier)

        # Apply damage
        current_hp = character.get('health', character.get('max_health', 20))
        new_hp = max(0, current_hp - damage)
        character['health'] = new_hp

        # Format trigger message
        trigger_msg = trap_def['trigger_message'].format(target=username)
        damage_msg = f"You take {damage} {trap_def['damage_type']} damage!"

        # Apply ongoing effects
        effect = trap_def.get('effect')
        if effect:
            if 'active_effects' not in character:
                character['active_effects'] = []

            if effect in ['poison', 'burning']:
                character['active_effects'].append({
                    'type': effect,
                    'duration': trap_def.get('effect_duration', 3),
                    'damage': trap_def.get('effect_damage', '1d4'),
                    'state_text': trap_def.get('effect_state_text', effect),
                    'removal_text': trap_def.get('effect_removal_text', f'no longer {effect}')
                })
                # Use proper grammar from trap definition, fallback to effect name
                effect_state = trap_def.get('effect_state_text', effect)
                damage_msg += f" You are now {effect_state}!"

        return f"{trigger_msg} {damage_msg}"

    def search_for_traps(self, player_id: int, room_id: str) -> str:
        """Player searches for traps in current room."""
        self.initialize_room_traps(room_id)

        traps = self.get_room_traps(room_id)
        if not traps:
            return "You search carefully but find no traps."

        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return ""

        character = player_data['character']

        # Wisdom modifier helps with detection
        wis = character.get('wisdom', 10)
        wis_modifier = (wis - 10) // 2

        # Initialize player awareness for this room
        if player_id not in self.player_trap_awareness:
            self.player_trap_awareness[player_id] = {}
        if room_id not in self.player_trap_awareness[player_id]:
            self.player_trap_awareness[player_id][room_id] = []

        detected = []
        already_known = []

        for i, trap_config in enumerate(traps):
            # Skip if already disarmed
            trap_state = self.room_trap_states[room_id].get(i, {})
            if trap_state.get('disarmed'):
                continue

            # Check if already detected
            if i in self.player_trap_awareness[player_id][room_id]:
                already_known.append(i)
                continue

            trap_type = trap_config.get('type')
            trap_def = TrapType.get_trap(trap_type)
            if not trap_def:
                continue

            # Detection roll
            detection_dc = trap_def.get('detection_dc', 12)
            roll = random.randint(1, 20) + wis_modifier

            if roll >= detection_dc:
                detected.append(i)
                self.player_trap_awareness[player_id][room_id].append(i)

        # Build response message
        if detected:
            messages = []
            for i in detected:
                trap_config = traps[i]
                trap_def = TrapType.get_trap(trap_config['type'])
                messages.append(trap_def['search_message'])
            return "\n".join(messages)
        elif already_known:
            return "You've already found all the traps you can detect here."
        else:
            return "You search carefully but don't find any traps. (They might still be there!)"

    def disarm_trap(self, player_id: int, room_id: str, trap_index: int = 0) -> str:
        """Attempt to disarm a trap."""
        self.initialize_room_traps(room_id)

        traps = self.get_room_traps(room_id)
        if not traps or trap_index >= len(traps):
            return "There's no trap there to disarm."

        # Check if player has detected this trap
        if player_id not in self.player_trap_awareness:
            return "You need to search for traps first!"
        if room_id not in self.player_trap_awareness[player_id]:
            return "You need to search for traps first!"
        if trap_index not in self.player_trap_awareness[player_id][room_id]:
            return "You haven't detected that trap yet. Try searching first."

        trap_state = self.room_trap_states[room_id].get(trap_index, {})
        if trap_state.get('disarmed'):
            return "That trap has already been disarmed."

        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return ""

        character = player_data['character']

        # Dexterity modifier helps with disarming
        dex = character.get('dexterity', 10)
        dex_modifier = (dex - 10) // 2

        trap_config = traps[trap_index]
        trap_def = TrapType.get_trap(trap_config['type'])

        # Disarm roll
        disarm_dc = trap_def.get('disarm_dc', 15)
        roll = random.randint(1, 20) + dex_modifier

        if roll >= disarm_dc:
            # Success!
            self.room_trap_states[room_id][trap_index]['disarmed'] = True
            return f"You successfully disarm the {trap_def['name']}!"
        elif roll < 5:
            # Critical failure - trigger the trap
            self.room_trap_states[room_id][trap_index]['triggered'] = True
            trap_result = {
                'trap_index': trap_index,
                'trap_def': trap_def,
                'trap_config': trap_config,
            }
            damage_msg = self.apply_trap_damage(player_id, trap_result)
            return f"You fumble while disarming the trap! {damage_msg}"
        else:
            # Failure but safe
            return f"You fail to disarm the {trap_def['name']}, but it doesn't trigger."

    def _roll_dice(self, dice_str: str) -> int:
        """Roll dice from string notation like '2d6+3'."""
        try:
            # Parse dice notation
            if 'd' not in dice_str:
                return int(dice_str)

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
            return total + modifier
        except:
            return 0

    async def update_trap_effects(self):
        """Update ongoing trap effects (poison, burning) - called each game tick."""
        from ...utils.colors import error_message, announcement

        for player_id, player_data in self.game_engine.player_manager.get_all_connected_players().items():
            character = player_data.get('character')
            if not character:
                continue

            effects = character.get('active_effects', [])
            if not effects:
                continue

            effects_to_remove = []

            for i, effect in enumerate(effects):
                effect_type = effect.get('type')
                duration = effect.get('duration', 0)

                if duration <= 0:
                    effects_to_remove.append(i)
                    continue

                # Only process DOT (damage over time) effects here
                # Skip other effect types (paralyze, stat_drain, enhancement, buff, etc.)
                dot_effect_types = ['poison', 'burning', 'bleeding', 'acid']
                if effect_type not in dot_effect_types:
                    continue

                # Apply effect damage
                damage_dice = effect.get('damage', '1d4')
                damage = self._roll_dice(damage_dice)

                current_hp = character.get('health', character.get('max_health', 20))
                new_hp = max(0, current_hp - damage)
                character['health'] = new_hp

                # Send message
                effect_name = effect_type.capitalize() if effect_type else "Unknown"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"{effect_name} deals {damage} damage to you!")
                )

                # Decrease duration
                effect['duration'] = duration - 1

                if effect['duration'] == 0:
                    # Use proper grammar from stored effect data, fallback to generic message
                    effect_removal = effect.get('removal_text')
                    if effect_removal:
                        effect_end_text = f"You are {effect_removal}."
                    else:
                        effect_end_text = f"The {effect_type} effect wears off."

                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        announcement(effect_end_text)
                    )

            # Remove expired effects (in reverse order to maintain indices)
            for i in sorted(effects_to_remove, reverse=True):
                effects.pop(i)

            character['active_effects'] = effects
