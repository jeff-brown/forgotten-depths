"""Spell system for managing mob spellcasting."""

import json
import random
from pathlib import Path
from typing import Dict, Any, Optional, List
from ...utils.logger import get_logger


class SpellType:
    """Defines spell types and their properties."""

    _spell_data: Dict[str, Any] = {}
    _mob_spell_lists: Dict[str, Any] = {}
    _loaded: bool = False

    @classmethod
    def _load_spells(cls):
        """Load spell definitions from JSON file."""
        if cls._loaded:
            return

        spell_file = Path("data/spells/mob_spells.json")
        if not spell_file.exists():
            logger = get_logger()
            logger.error(f"Spell data file not found: {spell_file}")
            cls._spell_data = {}
            cls._mob_spell_lists = {}
            cls._loaded = True
            return

        try:
            with open(spell_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cls._spell_data = data.get('spells', {})
                cls._mob_spell_lists = data.get('mob_spell_lists', {})
                cls._loaded = True
                logger = get_logger()
                logger.info(f"Loaded {len(cls._spell_data)} spells from {spell_file}")
        except Exception as e:
            logger = get_logger()
            logger.error(f"Error loading spell data: {e}")
            cls._spell_data = {}
            cls._mob_spell_lists = {}
            cls._loaded = True

    @classmethod
    def get_spell(cls, spell_id: str) -> Optional[Dict[str, Any]]:
        """Get spell definition by ID."""
        cls._load_spells()
        return cls._spell_data.get(spell_id.lower())

    @classmethod
    def get_mob_spell_list(cls, spell_list_type: str) -> Optional[Dict[str, Any]]:
        """Get mob spell list configuration by type."""
        cls._load_spells()
        return cls._mob_spell_lists.get(spell_list_type.lower())


class MobSpellcasting:
    """Manages spellcasting state and logic for mobs."""

    def __init__(self, combat_system):
        """Initialize the mob spellcasting system."""
        self.combat_system = combat_system
        self.logger = get_logger()

        # Mob mana tracking: mob_id -> {current_mana, max_mana, last_regen_time}
        self.mob_mana: Dict[str, Dict[str, Any]] = {}

        # Spell cooldowns: mob_id -> {spell_id: cooldown_end_time}
        self.mob_spell_cooldowns: Dict[str, Dict[str, float]] = {}

        # Spell fatigue: mob_id -> {fatigue_end_time}
        # After casting a spell, mob cannot cast ANY spell until fatigue expires
        # Duration based on spell cooldown (similar to player spell fatigue)
        self.mob_spell_fatigue: Dict[str, Dict[str, float]] = {}

    def initialize_mob_mana(self, mob_id: str, mob_level: int, spell_skill: int = 50):
        """Initialize mana pool for a spellcasting mob."""
        if mob_id in self.mob_mana:
            return  # Already initialized

        # Calculate max mana based on level and spell skill
        # Base: 50 mana, +10 per level, +spell_skill/2
        max_mana = 50 + (mob_level * 10) + (spell_skill // 2)

        import time
        self.mob_mana[mob_id] = {
            'current_mana': max_mana,
            'max_mana': max_mana,
            'last_regen_time': time.time()
        }

        self.mob_spell_cooldowns[mob_id] = {}
        self.logger.info(f"[SPELL] Initialized {mob_id} with {max_mana} mana")

    def can_cast_spell(self, mob_id: str, spell_id: str) -> bool:
        """Check if mob can cast a spell (has mana, not spell fatigued, and not on cooldown)."""
        if mob_id not in self.mob_mana:
            return False

        spell = SpellType.get_spell(spell_id)
        if not spell:
            return False

        import time
        current_time = time.time()

        # Check spell fatigue first (affects all spells)
        if mob_id in self.mob_spell_fatigue:
            fatigue_info = self.mob_spell_fatigue[mob_id]
            if 'fatigue_end_time' in fatigue_info:
                if current_time < fatigue_info['fatigue_end_time']:
                    return False
                # Fatigue expired, clean up
                del self.mob_spell_fatigue[mob_id]

        mana_info = self.mob_mana[mob_id]
        mana_cost = spell.get('mana_cost', 0)

        # Check mana
        if mana_info['current_mana'] < mana_cost:
            return False

        # Check individual spell cooldown
        cooldowns = self.mob_spell_cooldowns.get(mob_id, {})
        if spell_id in cooldowns:
            if current_time < cooldowns[spell_id]:
                return False

        return True

    def use_spell(self, mob_id: str, spell_id: str, mob_level: int = 1) -> bool:
        """Use a spell, consuming mana and setting cooldown. Returns True if successful.

        Args:
            mob_id: Unique identifier for the mob
            spell_id: ID of the spell being cast
            mob_level: Level of the mob casting the spell
        """
        if not self.can_cast_spell(mob_id, spell_id):
            return False

        spell = SpellType.get_spell(spell_id)
        if not spell:
            return False

        # Consume mana
        mana_cost = spell.get('mana_cost', 0)
        self.mob_mana[mob_id]['current_mana'] -= mana_cost

        # Set cooldowns and fatigue
        import time
        current_time = time.time()

        # Set individual spell cooldown
        cooldown_duration = spell.get('cooldown', 10.0)
        if mob_id not in self.mob_spell_cooldowns:
            self.mob_spell_cooldowns[mob_id] = {}
        self.mob_spell_cooldowns[mob_id][spell_id] = current_time + cooldown_duration

        # Apply spell fatigue (prevents casting any spell for a duration)
        # Formula: (spell_min_level - caster_level) * 15, minimum 15 seconds
        spell_min_level = spell.get('min_level', 1)
        level_difference = spell_min_level - mob_level
        fatigue_duration = max(15.0, level_difference * 15.0)

        self.mob_spell_fatigue[mob_id] = {
            'fatigue_end_time': current_time + fatigue_duration
        }

        self.logger.info(f"[SPELL] {mob_id} cast {spell_id}, {self.mob_mana[mob_id]['current_mana']}/{self.mob_mana[mob_id]['max_mana']} mana, fatigued for {fatigue_duration:.1f}s (level diff: {level_difference})")
        return True

    def get_available_spells(self, mob_id: str, spell_list_type: str, mob_level: int) -> List[str]:
        """Get list of spells this mob can currently cast."""
        spell_list_config = SpellType.get_mob_spell_list(spell_list_type)
        if not spell_list_config:
            # Fallback to generic caster
            spell_list_config = SpellType.get_mob_spell_list('generic_caster')

        if not spell_list_config:
            return []

        available_spells = []
        spell_ids = spell_list_config.get('spells', [])

        for spell_id in spell_ids:
            spell = SpellType.get_spell(spell_id)
            if not spell:
                continue

            # Don't filter by level - let mobs attempt higher-level spells
            # They'll just have higher failure rates (handled in spell failure logic)

            # Check if can cast (mana and cooldown)
            if self.can_cast_spell(mob_id, spell_id):
                available_spells.append(spell_id)

        return available_spells

    def regenerate_mana(self, mob_id: str, amount: int = None):
        """Regenerate mana for a mob. If amount is None, regenerates based on time elapsed."""
        if mob_id not in self.mob_mana:
            return

        import time
        mana_info = self.mob_mana[mob_id]

        if amount is None:
            # Time-based regeneration: 5 mana per second
            current_time = time.time()
            time_elapsed = current_time - mana_info['last_regen_time']
            amount = int(time_elapsed * 5)
            mana_info['last_regen_time'] = current_time

        if amount > 0:
            old_mana = mana_info['current_mana']
            mana_info['current_mana'] = min(
                mana_info['current_mana'] + amount,
                mana_info['max_mana']
            )
            if mana_info['current_mana'] > old_mana:
                self.logger.debug(f"[SPELL] {mob_id} regenerated {mana_info['current_mana'] - old_mana} mana")

    def choose_spell(self, mob_id: str, spell_list_type: str, mob_level: int, mob_health_percent: float) -> Optional[str]:
        """Choose which spell to cast based on mob AI."""
        spell_list_config = SpellType.get_mob_spell_list(spell_list_type)
        if not spell_list_config:
            spell_list_config = SpellType.get_mob_spell_list('generic_caster')

        if not spell_list_config:
            return None

        # Check if mob should heal
        heal_threshold = spell_list_config.get('heal_threshold', 0.3)
        if mob_health_percent < heal_threshold:
            # Try to cast healing spell
            available_spells = self.get_available_spells(mob_id, spell_list_type, mob_level)
            healing_spells = [s for s in available_spells if SpellType.get_spell(s).get('damage_type') == 'healing']
            if healing_spells:
                return random.choice(healing_spells)

        # Get available offensive spells
        available_spells = self.get_available_spells(mob_id, spell_list_type, mob_level)
        offensive_spells = [s for s in available_spells if SpellType.get_spell(s).get('damage_type') != 'healing']

        if not offensive_spells:
            return None

        # Choose randomly from available offensive spells
        return random.choice(offensive_spells)

    def calculate_spell_failure_chance(self, caster_level: int, caster_intelligence: int,
                                       spell_min_level: int, spell_skill: int = 50) -> float:
        """Calculate the chance that a spell cast will fail.

        Args:
            caster_level: Level of the caster
            caster_intelligence: Intelligence stat of the caster
            spell_min_level: Minimum level required for the spell
            spell_skill: Spell skill stat (0-100, default 50) - mobs only

        Returns:
            Float between 0.05 and 0.95 representing failure chance (0.10 = 10% chance to fail)
        """
        # Base failure rate: 10%
        base_failure = 0.10

        # Level difference penalty: +15% per level if spell is above caster's level
        level_penalty = 0.0
        if spell_min_level > caster_level:
            level_penalty = (spell_min_level - caster_level) * 0.15

        # Intelligence bonus: reduce failure based on intelligence modifier
        # D&D style: (stat - 10) / 2 = modifier
        intelligence_modifier = (caster_intelligence - 10) / 2
        intelligence_bonus = intelligence_modifier * 0.02  # 2% per modifier point

        # Spell skill bonus (mobs): reduce failure based on spell_skill
        # spell_skill of 50 = no bonus/penalty
        # spell_skill of 100 = -5% failure
        # spell_skill of 0 = +5% failure
        spell_skill_bonus = (spell_skill - 50) / 10 * 0.01

        # Calculate final failure chance
        failure_chance = base_failure + level_penalty - intelligence_bonus - spell_skill_bonus

        # Clamp between 5% and 95%
        failure_chance = max(0.05, min(0.95, failure_chance))

        return failure_chance

    def cleanup_mob(self, mob_id: str):
        """Clean up spell tracking for a dead/removed mob."""
        if mob_id in self.mob_mana:
            del self.mob_mana[mob_id]
        if mob_id in self.mob_spell_cooldowns:
            del self.mob_spell_cooldowns[mob_id]
        if mob_id in self.mob_spell_fatigue:
            del self.mob_spell_fatigue[mob_id]
