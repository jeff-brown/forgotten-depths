"""Class-specific ability system for players."""

import json
import time
import os
from typing import Dict, Any, Optional, List
from ...utils.logger import get_logger


class ClassAbilitySystem:
    """Manages class-specific abilities for players."""

    def __init__(self, game_engine):
        """Initialize the class ability system.

        Args:
            game_engine: Reference to the main game engine
        """
        self.game_engine = game_engine
        self.logger = get_logger()

        # Loaded abilities: { class_name: [ability_dicts] }
        self.class_abilities: Dict[str, List[Dict[str, Any]]] = {}

        # Player ability cooldowns: { player_id: { ability_id: cooldown_end_time } }
        self.ability_cooldowns: Dict[int, Dict[str, float]] = {}

        # Active ability effects: { player_id: { ability_id: effect_data } }
        self.active_effects: Dict[int, Dict[str, Any]] = {}

    def load_class_abilities(self, class_name: str) -> bool:
        """Load abilities for a specific class from JSON file.

        Args:
            class_name: Name of the class (e.g., 'rogue', 'fighter')

        Returns:
            True if loaded successfully, False otherwise
        """
        if class_name in self.class_abilities:
            return True  # Already loaded

        # Construct file path
        ability_file = os.path.join(
            'data', 'classes', 'abilities', f'{class_name.lower()}_abilities.json'
        )

        if not os.path.exists(ability_file):
            self.logger.warning(f"[ABILITIES] No ability file found for class: {class_name}")
            self.class_abilities[class_name] = []
            return False

        try:
            with open(ability_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            abilities = data.get('abilities', [])
            self.class_abilities[class_name] = abilities

            self.logger.info(f"[ABILITIES] Loaded {len(abilities)} abilities for class: {class_name}")
            return True

        except Exception as e:
            self.logger.error(f"[ABILITIES] Error loading abilities for {class_name}: {e}")
            self.class_abilities[class_name] = []
            return False

    def get_available_abilities(self, character: dict) -> List[Dict[str, Any]]:
        """Get all abilities available to a character based on class and level.

        Args:
            character: Character data dictionary

        Returns:
            List of ability dictionaries the character can use
        """
        class_name = character.get('class', '').lower()
        char_level = character.get('level', 1)

        # Ensure abilities are loaded
        self.load_class_abilities(class_name)

        abilities = self.class_abilities.get(class_name, [])

        # Filter by minimum level requirement
        available = []
        for ability in abilities:
            min_level = ability.get('min_level', 1)
            if char_level >= min_level:
                available.append(ability)

        return available

    def get_passive_abilities(self, character: dict) -> List[Dict[str, Any]]:
        """Get passive abilities for a character.

        Args:
            character: Character data dictionary

        Returns:
            List of passive ability dictionaries
        """
        available = self.get_available_abilities(character)
        return [a for a in available if a.get('type') == 'passive']

    def get_active_abilities(self, character: dict) -> List[Dict[str, Any]]:
        """Get active (command-based) abilities for a character.

        Args:
            character: Character data dictionary

        Returns:
            List of active ability dictionaries
        """
        available = self.get_available_abilities(character)
        return [a for a in available if a.get('type') == 'active']

    def check_passive_ability(self, character: dict, trigger: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if a passive ability should activate.

        Args:
            character: Character data dictionary
            trigger: Trigger event (e.g., 'on_critical_hit', 'combat_check')
            context: Additional context data for the trigger

        Returns:
            Ability effect data if triggered, None otherwise
        """
        passive_abilities = self.get_passive_abilities(character)

        for ability in passive_abilities:
            if ability.get('trigger') == trigger:
                # Check requirements
                if self._check_requirements(character, ability, context):
                    self.logger.debug(f"[ABILITIES] Passive ability triggered: {ability['name']}")
                    return ability.get('effect', {})

        return None

    def _check_requirements(self, character: dict, ability: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if all requirements for an ability are met.

        Args:
            character: Character data dictionary
            ability: Ability dictionary
            context: Context data

        Returns:
            True if all requirements met
        """
        requirements = ability.get('requirement') or ability.get('requirements')
        if not requirements:
            return True

        # Check stat requirements
        if 'stat' in requirements:
            stat_name = requirements['stat']
            min_value = requirements.get('min_value', 0)
            char_stat = character.get('stats', {}).get(stat_name, 10)
            if char_stat < min_value:
                return False

        # Check item requirements
        if 'items' in requirements:
            required_items = requirements['items']
            inventory = character.get('inventory', [])
            for item_id in required_items:
                if not any(item.get('id') == item_id for item in inventory):
                    return False

        return True

    def is_ability_on_cooldown(self, player_id: int, ability_id: str) -> bool:
        """Check if an ability is on cooldown.

        Args:
            player_id: Player ID
            ability_id: Ability identifier

        Returns:
            True if on cooldown
        """
        if player_id not in self.ability_cooldowns:
            return False

        cooldown_end = self.ability_cooldowns[player_id].get(ability_id, 0)
        return time.time() < cooldown_end

    def get_cooldown_remaining(self, player_id: int, ability_id: str) -> float:
        """Get remaining cooldown time for an ability.

        Args:
            player_id: Player ID
            ability_id: Ability identifier

        Returns:
            Seconds remaining on cooldown, 0 if not on cooldown
        """
        if not self.is_ability_on_cooldown(player_id, ability_id):
            return 0.0

        cooldown_end = self.ability_cooldowns[player_id][ability_id]
        return max(0.0, cooldown_end - time.time())

    def set_ability_cooldown(self, player_id: int, ability_id: str, cooldown_seconds: float):
        """Set an ability on cooldown.

        Args:
            player_id: Player ID
            ability_id: Ability identifier
            cooldown_seconds: Cooldown duration in seconds
        """
        if player_id not in self.ability_cooldowns:
            self.ability_cooldowns[player_id] = {}

        self.ability_cooldowns[player_id][ability_id] = time.time() + cooldown_seconds
        self.logger.debug(f"[ABILITIES] Set cooldown for player {player_id}, ability {ability_id}: {cooldown_seconds}s")

    def get_ability_by_command(self, character: dict, command: str) -> Optional[Dict[str, Any]]:
        """Find an active ability by its command or alias.

        Args:
            character: Character data dictionary
            command: Command string (e.g., 'picklock', 'backstab')

        Returns:
            Ability dictionary if found, None otherwise
        """
        active_abilities = self.get_active_abilities(character)

        for ability in active_abilities:
            # Check primary command
            if ability.get('command', '').lower() == command.lower():
                return ability

            # Check aliases
            aliases = ability.get('aliases', [])
            if command.lower() in [a.lower() for a in aliases]:
                return ability

        return None

    async def execute_active_ability(self, player_id: int, ability: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute an active ability.

        Args:
            player_id: Player ID
            ability: Ability dictionary
            **kwargs: Additional arguments for the ability

        Returns:
            Result dictionary with success, message, etc.
        """
        ability_id = ability['id']
        ability_name = ability['name']

        # Check cooldown
        if self.is_ability_on_cooldown(player_id, ability_id):
            cooldown_remaining = self.get_cooldown_remaining(player_id, ability_id)
            return {
                'success': False,
                'message': f"{ability_name} is on cooldown. {cooldown_remaining:.1f}s remaining."
            }

        # Set cooldown
        cooldown = ability.get('cooldown', 0)
        if cooldown > 0:
            self.set_ability_cooldown(player_id, ability_id, cooldown)

        # Ability-specific execution will be handled by individual ability handlers
        return {
            'success': True,
            'message': f"Executed {ability_name}",
            'ability': ability
        }
