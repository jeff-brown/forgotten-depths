"""Damage calculation system for combat."""

import random
from typing import Dict, Any

class DamageCalculator:
    """Calculates damage for combat actions."""

    @staticmethod
    def calculate_melee_damage(attacker, weapon=None, natural_attack=None, crit_multiplier=2.0) -> Dict[str, Any]:
        """Calculate melee damage.

        Args:
            attacker: The attacking entity with strength attribute
            weapon: Optional weapon dict with properties.damage (e.g., "1d6+2")
            natural_attack: Optional dict with damage info for mobs (damage, damage_min, damage_max)
            crit_multiplier: Multiplier for critical hits (default 2.0)
        """
        base_damage = getattr(attacker, 'strength', 10) // 2

        if weapon:
            # Weapon is a dict from character equipment
            weapon_damage_str = weapon.get('properties', {}).get('damage', '1d4')
            weapon_damage = DamageCalculator._parse_dice_damage(weapon_damage_str)
            total_damage = base_damage + weapon_damage
        elif natural_attack:
            # Mob natural attack
            if 'damage' in natural_attack and isinstance(natural_attack['damage'], str) and 'd' in natural_attack['damage']:
                # Dice notation
                attack_damage = DamageCalculator._parse_dice_damage(natural_attack['damage'])
            elif 'damage_min' in natural_attack and 'damage_max' in natural_attack:
                # Min/max range
                attack_damage = random.randint(natural_attack['damage_min'], natural_attack['damage_max'])
            else:
                # Default
                attack_damage = random.randint(1, 4)

            total_damage = base_damage + attack_damage
        else:
            # Unarmed attack
            total_damage = base_damage + random.randint(1, 3)

        is_critical = random.random() < 0.05
        if is_critical:
            total_damage = int(total_damage * crit_multiplier)

        return {
            'damage': max(1, total_damage),
            'is_critical': is_critical,
            'damage_type': 'physical'
        }

    @staticmethod
    def calculate_ranged_damage(attacker, weapon=None, crit_multiplier=2.0) -> Dict[str, Any]:
        """Calculate ranged damage (DEX-based).

        Args:
            attacker: The attacking entity with dexterity attribute
            weapon: Optional ranged weapon dict with properties.damage
            crit_multiplier: Multiplier for critical hits (default 2.0)
        """
        # Ranged attacks use DEX instead of STR
        base_damage = getattr(attacker, 'dexterity', 10) // 2

        if weapon:
            # Ranged weapon damage
            weapon_damage_str = weapon.get('properties', {}).get('damage', '1d4')
            weapon_damage = DamageCalculator._parse_dice_damage(weapon_damage_str)
            total_damage = base_damage + weapon_damage
        else:
            # No weapon (shouldn't happen for ranged, but fallback)
            total_damage = base_damage + random.randint(1, 3)

        # Same crit chance as melee
        is_critical = random.random() < 0.05
        if is_critical:
            total_damage = int(total_damage * crit_multiplier)

        return {
            'damage': max(1, total_damage),
            'is_critical': is_critical,
            'damage_type': 'physical'
        }

    @staticmethod
    def _parse_dice_damage(damage_str: str) -> int:
        """Parse dice notation (e.g., '1d6+2') and return rolled damage.

        Args:
            damage_str: Dice notation string like "1d6", "2d4+3", "1d8+1"

        Returns:
            Integer damage value from rolled dice
        """
        try:
            # Handle formats like "1d6+2" or "2d4" or just "5"
            damage_str = damage_str.strip().lower()

            # If it's just a number, return it
            if 'd' not in damage_str:
                return int(damage_str)

            # Split on '+' or '-' for modifier
            modifier = 0
            if '+' in damage_str:
                parts = damage_str.split('+')
                damage_str = parts[0]
                modifier = int(parts[1])
            elif '-' in damage_str and damage_str.rfind('-') > 0:  # Check it's not just negative
                parts = damage_str.rsplit('-', 1)
                damage_str = parts[0]
                modifier = -int(parts[1])

            # Parse dice notation (e.g., "2d6")
            dice_parts = damage_str.split('d')
            num_dice = int(dice_parts[0]) if dice_parts[0] else 1
            die_size = int(dice_parts[1])

            # Roll the dice
            total = sum(random.randint(1, die_size) for _ in range(num_dice))
            return total + modifier

        except (ValueError, IndexError):
            # If parsing fails, return a default value
            return random.randint(1, 6)

    @staticmethod
    def calculate_spell_damage(caster, spell_level: int = 1) -> Dict[str, Any]:
        """Calculate spell damage."""
        base_damage = getattr(caster, 'intelligence', 10) // 2
        spell_damage = spell_level * 3 + random.randint(1, 6)
        total_damage = base_damage + spell_damage

        is_critical = random.random() < 0.03
        if is_critical:
            total_damage *= 1.5

        return {
            'damage': max(1, int(total_damage)),
            'is_critical': is_critical,
            'damage_type': 'magical'
        }

    @staticmethod
    def apply_armor(damage: int, armor_value: int) -> int:
        """Apply armor reduction to damage."""
        reduction = armor_value * 0.1
        final_damage = damage * (1 - min(0.8, reduction))
        return max(1, int(final_damage))

    @staticmethod
    def calculate_hit_chance(attacker, target) -> float:
        """Calculate the chance to hit a target."""
        base_chance = 0.75
        attacker_skill = getattr(attacker, 'dexterity', 10)
        target_defense = getattr(target, 'dexterity', 10)

        skill_modifier = (attacker_skill - target_defense) * 0.02
        return max(0.05, min(0.95, base_chance + skill_modifier))

    @staticmethod
    def calculate_dodge_chance(target) -> float:
        """Calculate the chance for target to dodge an attack."""
        base_dodge = 0.05  # 5% base dodge chance
        dexterity = getattr(target, 'dexterity', 10)

        # +1% dodge per dexterity point above 10
        dex_bonus = max(0, (dexterity - 10) * 0.01)

        return min(0.25, base_dodge + dex_bonus)  # Max 25% dodge

    @staticmethod
    def calculate_armor_deflect_chance(target, armor_class: int = 0) -> float:
        """Calculate the chance for armor to completely deflect an attack."""
        # Each point of armor class gives 3% deflect chance
        deflect_chance = armor_class * 0.03

        return min(0.30, deflect_chance)  # Max 30% deflect

    @staticmethod
    def check_attack_outcome(attacker, target, armor_class: int = 0) -> Dict[str, Any]:
        """Check if an attack hits, is dodged, or is deflected.

        Returns:
            Dict with keys: 'result' ('hit', 'miss', 'dodge', 'deflect'), 'hit_chance', 'dodge_chance', 'deflect_chance'
        """
        hit_chance = DamageCalculator.calculate_hit_chance(attacker, target)
        dodge_chance = DamageCalculator.calculate_dodge_chance(target)
        deflect_chance = DamageCalculator.calculate_armor_deflect_chance(target, armor_class)

        # Roll to hit
        hit_roll = random.random()
        if hit_roll > hit_chance:
            return {
                'result': 'miss',
                'hit_chance': hit_chance,
                'dodge_chance': dodge_chance,
                'deflect_chance': deflect_chance
            }

        # Check for dodge
        dodge_roll = random.random()
        if dodge_roll < dodge_chance:
            return {
                'result': 'dodge',
                'hit_chance': hit_chance,
                'dodge_chance': dodge_chance,
                'deflect_chance': deflect_chance
            }

        # Check for armor deflect
        deflect_roll = random.random()
        if deflect_roll < deflect_chance:
            return {
                'result': 'deflect',
                'hit_chance': hit_chance,
                'dodge_chance': dodge_chance,
                'deflect_chance': deflect_chance
            }

        # Attack hits
        return {
            'result': 'hit',
            'hit_chance': hit_chance,
            'dodge_chance': dodge_chance,
            'deflect_chance': deflect_chance
        }