"""Generic special ability system for mobs."""

import random
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from ...utils.logger import get_logger


class MobAbility(ABC):
    """Base class for all mob special abilities."""

    def __init__(self, ability_data: Dict[str, Any]):
        """Initialize the ability with data from mob definition.

        Args:
            ability_data: Dictionary containing ability configuration
        """
        self.name = ability_data.get('name', 'unknown_ability')
        self.cooldown = ability_data.get('cooldown', 10.0)  # Cooldown in seconds
        self.use_chance = ability_data.get('use_chance', 0.3)  # 30% chance to use when available
        self.min_level = ability_data.get('min_level', 1)  # Minimum mob level to use this ability
        self.data = ability_data
        self.logger = get_logger()

    @abstractmethod
    async def execute(self, attacker: dict, target: dict, combat_system, room_id: str) -> Dict[str, Any]:
        """Execute the ability.

        Args:
            attacker: The mob using the ability
            target: The target of the ability (player or mob)
            combat_system: Reference to combat system for messaging
            room_id: Current room ID

        Returns:
            Dictionary with results:
                - success: bool (whether ability was used)
                - message: str (message to show to target)
                - room_message: str (message to show to others in room)
                - damage: int (damage dealt if any)
                - effects: list (status effects applied if any)
        """
        pass

    def can_use(self, mob_level: int) -> bool:
        """Check if mob meets the level requirement for this ability.

        Args:
            mob_level: Level of the mob

        Returns:
            True if mob can use this ability
        """
        return mob_level >= self.min_level


class BreathWeaponAbility(MobAbility):
    """Breath weapon ability (fire, frost, acid, etc.)."""

    def __init__(self, ability_data: Dict[str, Any]):
        super().__init__(ability_data)
        self.damage_dice = ability_data.get('damage', '3d6')
        self.damage_type = ability_data.get('damage_type', 'fire')
        self.verb = ability_data.get('verb', 'breathes')
        self.effect = ability_data.get('effect', None)  # Optional status effect

    async def execute(self, attacker: dict, target: dict, combat_system, room_id: str) -> Dict[str, Any]:
        """Execute the breath weapon attack."""
        attacker_name = attacker.get('name', 'Unknown creature')
        target_name = target.get('name', 'the target')
        # Mobs have 'experience_reward' field, players don't
        is_player_target = 'experience_reward' not in target

        # Parse damage dice
        damage = self._roll_damage(self.damage_dice)

        # Build messages - verb already includes the full action like "breathes frost at"
        if is_player_target:
            # Target is a player
            message = f"{attacker_name} {self.verb} you for {damage} damage!"
            room_message = f"{attacker_name} {self.verb} {target_name}!"
        else:
            # Target is a mob
            message = None  # No direct message to players
            room_message = f"{attacker_name} {self.verb} {target_name} for {damage} damage!"

        # Apply damage to target
        target['health'] = max(0, target['health'] - damage)

        self.logger.info(f"[ABILITY] {attacker_name} used breath weapon ({self.damage_type}) on {target_name} for {damage} damage")

        result = {
            'success': True,
            'message': message,
            'room_message': room_message,
            'damage': damage,
            'effects': []
        }

        # Apply status effect if configured
        if self.effect:
            result['effects'].append(self.effect)

        return result

    def _roll_damage(self, dice_string: str) -> int:
        """Roll damage dice.

        Args:
            dice_string: Dice notation (e.g., "3d6", "2d8+4")

        Returns:
            Total damage rolled
        """
        try:
            # Handle format like "3d6" or "2d8+4"
            parts = dice_string.replace('-', '+-').split('+')
            total = 0

            for part in parts:
                part = part.strip()
                if not part:
                    continue

                if 'd' in part.lower():
                    # Dice roll
                    num_dice, die_size = part.lower().split('d')
                    num_dice = int(num_dice) if num_dice else 1
                    die_size = int(die_size)
                    for _ in range(num_dice):
                        total += random.randint(1, die_size)
                else:
                    # Flat modifier
                    total += int(part)

            return max(1, total)  # Minimum 1 damage
        except Exception as e:
            self.logger.error(f"Error parsing damage dice '{dice_string}': {e}")
            return 10  # Default damage

    def _get_damage_description(self) -> str:
        """Get descriptive text for the breath weapon based on damage type."""
        descriptions = {
            'fire': 'a blast of flame',
            'frost': 'a blast of frost',
            'cold': 'a blast of frost',
            'ice': 'a blast of frost',
            'acid': 'a spray of acid',
            'poison': 'a cloud of poison',
            'lightning': 'a bolt of lightning',
            'dark': 'a blast of dark energy',
            'necrotic': 'a wave of necrotic energy'
        }
        return descriptions.get(self.damage_type.lower(), f'a blast of {self.damage_type}')


class AbilityRegistry:
    """Registry for mob abilities."""

    _abilities: Dict[str, type] = {}

    @classmethod
    def register(cls, ability_type: str, ability_class: type):
        """Register an ability class.

        Args:
            ability_type: Type identifier for this ability
            ability_class: The ability class to register
        """
        cls._abilities[ability_type] = ability_class

    @classmethod
    def create_ability(cls, ability_data: Dict[str, Any]) -> Optional[MobAbility]:
        """Create an ability instance from data.

        Args:
            ability_data: Dictionary containing ability configuration including 'type'

        Returns:
            Ability instance or None if type not recognized
        """
        ability_type = ability_data.get('type')
        if not ability_type:
            return None

        ability_class = cls._abilities.get(ability_type)
        if not ability_class:
            return None

        return ability_class(ability_data)

    @classmethod
    def get_registered_types(cls) -> List[str]:
        """Get list of registered ability types."""
        return list(cls._abilities.keys())


# Register built-in ability types
AbilityRegistry.register('breath_weapon', BreathWeaponAbility)
