"""Character command handler for character info and progression commands."""

import random
import json
from pathlib import Path
from ..base_handler import BaseCommandHandler
from ...utils.colors import wrap_color, Colors
from ...game.player.stats_utils import get_stamina_hp_bonus


class CharacterCommandHandler(BaseCommandHandler):
    """Handles character information and progression commands."""

    async def handle_health_command(self, player_id: int, character: dict):
        """Display health, mana, and status.

        Usage: health, hp
        """
        char = character

        # Determine status based on hunger/thirst
        hunger = char.get('hunger', 100)
        thirst = char.get('thirst', 100)
        low_threshold = self.config_manager.get_setting('player', 'hunger_thirst', 'low_warning_threshold', default=20)
        status_conditions = []

        if hunger <= 0:
            status_conditions.append("Starving")
        elif hunger <= low_threshold:
            status_conditions.append("Hungry")

        if thirst <= 0:
            status_conditions.append("Dehydrated")
        elif thirst <= low_threshold:
            status_conditions.append("Thirsty")

        # Check for active effects (debuffs/DOT effects)
        active_effects = char.get('active_effects', [])
        for effect in active_effects:
            effect_type = effect.get('type', effect.get('effect', ''))
            if effect_type == 'poison':
                status_conditions.append("Poisoned")
            elif effect_type == 'burning':
                status_conditions.append("Burning")
            elif effect_type == 'bleeding':
                status_conditions.append("Bleeding")
            elif effect_type == 'acid':
                status_conditions.append("Acid Burned")
            elif effect_type == 'paralyze':
                status_conditions.append("Paralyzed")
            elif effect_type == 'charm':
                status_conditions.append("Charmed")
            elif effect_type == 'stat_drain':
                status_conditions.append("Drained")

        # Use existing status or build from conditions
        if status_conditions:
            status = ", ".join(status_conditions)
        else:
            status = char.get('status', 'Healthy')

        # Check if class uses magic
        player_class = char.get('class', 'fighter')
        class_uses_magic = self._class_uses_magic(player_class)

        # Build mana line only if class uses magic
        if class_uses_magic:
            current_mana = int(char.get('current_mana', char.get('current_mana', 10)))
            max_mana = int(char.get('max_mana', 10))
            mana_value = wrap_color(f"{current_mana} / {max_mana}", Colors.BOLD_WHITE)
            mana_line = f"{wrap_color('Mana:', Colors.BOLD_CYAN)}          {mana_value}\n"
        else:
            mana_line = ""

        current_hp = int(char.get('current_hit_points', 20))
        max_hp = int(char.get('max_hit_points', 20))
        hp_value = wrap_color(f"{current_hp} / {max_hp}", Colors.BOLD_WHITE)

        health_text = f"""
{wrap_color('Hit Points:', Colors.BOLD_CYAN)}    {hp_value}
{mana_line}{wrap_color('Status:', Colors.BOLD_CYAN)}        {wrap_color(status, Colors.BOLD_WHITE)}
{Colors.BOLD_WHITE}"""
        await self.send_message(player_id, health_text)

    async def handle_experience_command(self, player_id: int, character: dict):
        """Display experience, level, and rune.

        Usage: experience, xp, exp
        """
        char = character

        # Calculate XP progress
        current_level = char.get('level', 1)
        current_xp = char.get('experience', 0)
        xp_for_next = self.calculate_xp_for_level(current_level + 1)
        xp_remaining = xp_for_next - current_xp

        experience_text = f"""
{wrap_color('Level:', Colors.BOLD_CYAN)}         {wrap_color(str(char['level']), Colors.BOLD_YELLOW)}
{wrap_color('Experience:', Colors.BOLD_CYAN)}    {wrap_color(f"{char['experience']}/{xp_for_next}", Colors.BOLD_WHITE)} ({xp_remaining} to next level)
{wrap_color('Rune:', Colors.BOLD_CYAN)}          {wrap_color(char['rune'].title(), Colors.BOLD_WHITE)}
{Colors.BOLD_WHITE}"""
        await self.send_message(player_id, experience_text)

    async def handle_stats_command(self, player_id: int, character: dict):
        """Display character statistics.

        Usage: stats, score, sheet
        """
        char = character

        # Determine status based on hunger/thirst
        hunger = char.get('hunger', 100)
        thirst = char.get('thirst', 100)
        low_threshold = self.config_manager.get_setting('player', 'hunger_thirst', 'low_warning_threshold', default=20)
        status_conditions = []

        if hunger <= 0:
            status_conditions.append("Starving")
        elif hunger <= low_threshold:
            status_conditions.append("Hungry")

        if thirst <= 0:
            status_conditions.append("Dehydrated")
        elif thirst <= low_threshold:
            status_conditions.append("Thirsty")

        # Check for active effects (debuffs/DOT effects)
        active_effects = char.get('active_effects', [])
        for effect in active_effects:
            effect_type = effect.get('type', effect.get('effect', ''))
            if effect_type == 'poison':
                status_conditions.append("Poisoned")
            elif effect_type == 'burning':
                status_conditions.append("Burning")
            elif effect_type == 'bleeding':
                status_conditions.append("Bleeding")
            elif effect_type == 'acid':
                status_conditions.append("Acid Burned")
            elif effect_type == 'paralyze':
                status_conditions.append("Paralyzed")
            elif effect_type == 'charm':
                status_conditions.append("Charmed")
            elif effect_type == 'stat_drain':
                status_conditions.append("Drained")

        # Use existing status or build from conditions
        if status_conditions:
            status = ", ".join(status_conditions)
        else:
            status = char.get('status', 'Healthy')

        # Calculate XP progress
        current_level = char.get('level', 1)
        current_xp = char.get('experience', 0)
        xp_for_next = self.calculate_xp_for_level(current_level + 1)
        xp_remaining = xp_for_next - current_xp

        # Check if class uses magic
        player_class = char.get('class', 'fighter')
        class_uses_magic = self._class_uses_magic(player_class)

        # Build mana line only if class uses magic
        if class_uses_magic:
            current_mana = int(char.get('current_mana', char.get('current_mana', 10)))
            max_mana = int(char.get('max_mana', 10))
            mana_value = wrap_color(f"{current_mana} / {max_mana}", Colors.BOLD_WHITE)
            mana_line = f"{wrap_color('Mana:', Colors.BOLD_CYAN)}          {mana_value}\n"
        else:
            mana_line = ""

        # Pre-calculate HP values
        current_hp = int(char.get('current_hit_points', 20))
        max_hp = int(char.get('max_hit_points', 20))
        hp_value = wrap_color(f"{current_hp} / {max_hp}", Colors.BOLD_WHITE)

        # Colorize stats display
        stats_text = f"""
{wrap_color('Name:', Colors.BOLD_CYAN)}          {wrap_color(char['name'], Colors.BOLD_WHITE)}
{wrap_color('Species:', Colors.BOLD_CYAN)}       {wrap_color(char['species'], Colors.BOLD_WHITE)}
{wrap_color('Class:', Colors.BOLD_CYAN)}         {wrap_color(char['class'], Colors.BOLD_WHITE)}
{wrap_color('Level:', Colors.BOLD_CYAN)}         {wrap_color(str(char['level']), Colors.BOLD_YELLOW)}
{wrap_color('Experience:', Colors.BOLD_CYAN)}    {wrap_color(f"{char['experience']}/{xp_for_next}", Colors.BOLD_WHITE)} ({xp_remaining} to next level)
{wrap_color('Rune:', Colors.BOLD_CYAN)}          {wrap_color(char['rune'].title(), Colors.BOLD_WHITE)}

{wrap_color('Intellect:', Colors.BOLD_CYAN)}     {wrap_color(str(char['intellect']), Colors.BOLD_WHITE)}
{wrap_color('Wisdom:', Colors.BOLD_CYAN)}        {wrap_color(str(char['wisdom']), Colors.BOLD_WHITE)}
{wrap_color('Strength:', Colors.BOLD_CYAN)}      {wrap_color(str(char['strength']), Colors.BOLD_WHITE)}
{wrap_color('Constitution:', Colors.BOLD_CYAN)}  {wrap_color(str(char['constitution']), Colors.BOLD_WHITE)}
{wrap_color('Dexterity:', Colors.BOLD_CYAN)}     {wrap_color(str(char['dexterity']), Colors.BOLD_WHITE)}
{wrap_color('Charisma:', Colors.BOLD_CYAN)}      {wrap_color(str(char['charisma']), Colors.BOLD_WHITE)}

{wrap_color('Hit Points:', Colors.BOLD_CYAN)}    {hp_value}
{mana_line}{wrap_color('Status:', Colors.BOLD_CYAN)}        {wrap_color(status, Colors.BOLD_WHITE)}
{wrap_color('Armor Class:', Colors.BOLD_CYAN)}   {wrap_color(str(self.get_effective_armor_class(char)), Colors.BOLD_WHITE)}

{wrap_color('Weapon:', Colors.BOLD_CYAN)}        {wrap_color(char['equipped']['weapon']['name'] if char['equipped']['weapon'] else 'Fists', Colors.BOLD_WHITE)}
{wrap_color('Armor:', Colors.BOLD_CYAN)}         {wrap_color(char['equipped']['armor']['name'] if char['equipped']['armor'] else 'None', Colors.BOLD_WHITE)}
{wrap_color('Encumbrance:', Colors.BOLD_CYAN)}   {wrap_color(f"{char['encumbrance']} / {char['max_encumbrance']}", Colors.BOLD_WHITE)}
{wrap_color('Gold:', Colors.BOLD_CYAN)}          {wrap_color(str(char['gold']), Colors.BOLD_YELLOW)}
{Colors.BOLD_WHITE}"""
        await self.send_message(player_id, stats_text)

    async def handle_reroll_command(self, player_id: int, character: dict):
        """Handle the reroll command to reroll stats for level 1 characters.

        Usage: reroll
        """
        # Check if character is level 1
        if character.get('level', 1) != 1:
            await self.send_message(
                player_id,
                "You can only reroll stats at level 1!"
            )
            return

        # Check if character has gained any experience
        if character.get('experience', 0) > 0:
            await self.send_message(
                player_id,
                "You can only reroll stats if you haven't gained any experience yet!"
            )
            return

        # Get race and class data
        races = self._load_races()
        classes = self._load_classes()

        # Find race key from name
        race_key = None
        for key, data in races.items():
            if data['name'] == character.get('species'):
                race_key = key
                break

        # Find class key from name
        class_key = None
        for key, data in classes.items():
            if data['name'] == character.get('class'):
                class_key = key
                break

        if not race_key or not class_key:
            await self.send_message(
                player_id,
                "Error: Could not find your race or class data."
            )
            return

        race_data = races[race_key]
        class_data = classes[class_key]

        # Roll new random stats using configured ranges
        stat_ranges = self.config_manager.get_setting('player', 'starting_stats', default={})

        def roll_stat(stat_name):
            """Roll a stat within the configured min/max range."""
            stat_config = stat_ranges.get(stat_name, {})
            if isinstance(stat_config, dict) and 'min' in stat_config and 'max' in stat_config:
                return random.randint(stat_config['min'], stat_config['max'])
            # Fallback to 3d6 if no config
            return sum(random.randint(1, 6) for _ in range(3))

        old_stats = {
            'strength': character.get('strength', 10),
            'dexterity': character.get('dexterity', 10),
            'constitution': character.get('constitution', 10),
            'vitality': character.get('vitality', 10),
            'intellect': character.get('intellect', 10),
            'wisdom': character.get('wisdom', 10),
            'charisma': character.get('charisma', 10)
        }

        base_stats = {
            'strength': roll_stat('strength'),
            'dexterity': roll_stat('dexterity'),
            'constitution': roll_stat('constitution'),
            'vitality': roll_stat('vitality'),
            'intellect': roll_stat('intelligence'),
            'wisdom': roll_stat('wisdom'),
            'charisma': roll_stat('charisma')
        }

        # Apply race modifiers
        for stat, value in race_data.get('stat_modifiers', {}).items():
            base_stats[stat] = base_stats.get(stat, 10) + value

        # Apply class modifiers
        for stat, value in class_data.get('stat_modifiers', {}).items():
            base_stats[stat] = base_stats.get(stat, 10) + value

        # Update character stats
        character.update(base_stats)

        # This is the REROLL command - should reset HP from scratch
        # Formula: baseVitality + raceModifier + classModifier + staminaBonus
        old_max_hp = character.get('max_hit_points', 0)

        # New base vitality roll (8-20)
        base_vitality = random.randint(8, 20)

        # Race vitality modifier
        race_vitality_mod = race_data.get('stat_modifiers', {}).get('vitality', 0)

        # Class vitality modifier
        class_vitality_mod = class_data.get('stat_modifiers', {}).get('vitality', 0)

        # Stamina (constitution) HP bonus lookup table
        constitution = character['constitution']
        stamina_hp_bonus = get_stamina_hp_bonus(constitution)

        # Final calculation (minimum 8 HP) - resets to new value
        max_hp = max(8, base_vitality + race_vitality_mod + class_vitality_mod + stamina_hp_bonus)

        # Recalculate max mana
        intellect = character['intellect']
        mana_modifier = class_data.get('mana_modifier', 1.0)
        base_mana = intellect * 3
        random_mana = random.randint(1, 5)
        max_mana = int((base_mana + random_mana) * mana_modifier)

        # Update HP and mana
        old_max_mana = character.get('max_mana', 0)

        character['max_hit_points'] = max_hp
        character['current_hit_points'] = max_hp
        character['max_mana'] = max_mana
        character['current_mana'] = max_mana

        # Update max encumbrance based on new strength
        self.player_manager.update_encumbrance(character)

        # Show before and after stats
        reroll_msg = f"""
=== Stats Rerolled! ===

Old Stats:
STR: {old_stats['strength']}  DEX: {old_stats['dexterity']}  CON: {old_stats['constitution']}  VIT: {old_stats.get('vitality', 0)}
INT: {old_stats['intellect']}  WIS: {old_stats['wisdom']}  CHA: {old_stats['charisma']}
HP: {old_max_hp}  Mana: {old_max_mana}

New Stats:
STR: {character['strength']}  DEX: {character['dexterity']}  CON: {character['constitution']}  VIT: {character.get('vitality', 0)}
INT: {character['intellect']}  WIS: {character['wisdom']}  CHA: {character['charisma']}
HP: {max_hp}  Mana: {max_mana}
"""
        await self.send_message(player_id, reroll_msg)

    async def handle_train_command(self, player_id: int, character: dict):
        """Handle the train command to level up.

        Usage: train
        """
        room_id = character.get('room_id')

        # Check if there's a trainer in the room
        room = self.world_manager.get_room(room_id)
        if not room:
            await self.send_message(
                player_id,
                "You are not in a valid room."
            )
            return

        has_trainer = False
        npcs = room.npcs if hasattr(room, 'npcs') else []

        for npc in npcs:
            # Get NPC data from world manager using npc_id
            npc_data = self.world_manager.get_npc_data(npc.npc_id)
            if npc_data:
                services = npc_data.get('services', [])
                if 'trainer' in services or 'level_up' in services:
                    has_trainer = True
                    break

        if not has_trainer:
            await self.send_message(
                player_id,
                "There is no trainer here. You must find a trainer to level up."
            )
            return

        # Get current stats
        current_level = character.get('level', 1)
        current_xp = character.get('experience', 0)
        max_level = self.config_manager.get_setting('player', 'leveling', 'max_level', default=50)

        # Check if at max level
        if current_level >= max_level:
            await self.send_message(
                player_id,
                f"You have reached the maximum level of {max_level}!"
            )
            return

        # Calculate XP needed for next level
        xp_needed = self.calculate_xp_for_level(current_level + 1)
        xp_remaining = xp_needed - current_xp

        # Check if player has enough XP
        if current_xp < xp_needed:
            await self.send_message(
                player_id,
                f"You need {xp_remaining} more experience to reach level {current_level + 1}. (Current: {current_xp}/{xp_needed})"
            )
            return

        # Level up!
        old_level = current_level
        new_level = current_level + 1
        character['level'] = new_level

        # Get leveling bonuses from config
        mana_per_level = self.config_manager.get_setting('player', 'leveling', 'mana_per_level', default=5)
        stat_points = self.config_manager.get_setting('player', 'leveling', 'stat_points_per_level', default=2)

        # Load race and class data for modifiers
        races = self._load_races()
        classes = self._load_classes()
        player_race = character.get('species', 'human').lower()
        player_class = character.get('class', 'fighter').lower()
        race_data = races.get(player_race, races.get('human', {}))
        class_data = classes.get(player_class, classes.get('fighter', {}))

        # Increase max HP using vitality formula (same as training)
        # Formula: oldMaxVitality + newRoll + raceModifier + classModifier + staminaBonus
        old_max_hp = character.get('max_hit_points', 100)

        # New base vitality roll (8-20)
        new_vitality_roll = random.randint(8, 20)

        # Race vitality modifier
        race_vitality_mod = race_data.get('stat_modifiers', {}).get('vitality', 0)

        # Class vitality modifier
        class_vitality_mod = class_data.get('stat_modifiers', {}).get('vitality', 0)

        # Stamina (constitution) HP bonus lookup table
        constitution = character.get('constitution', 10)
        stamina_hp_bonus = get_stamina_hp_bonus(constitution)

        # Final calculation: old max + new roll + modifiers + stamina bonus (minimum 8 HP gain)
        hp_gain = new_vitality_roll + race_vitality_mod + class_vitality_mod + stamina_hp_bonus
        new_max_hp = old_max_hp + max(8, hp_gain)
        character['max_hit_points'] = new_max_hp

        # Check if class uses magic
        player_class = character.get('class', 'fighter')
        class_uses_magic = self._class_uses_magic(player_class)

        # Increase max mana (only for magic-using classes)
        old_max_mana = character.get('max_mana', 0)
        new_max_mana = old_max_mana
        if class_uses_magic:
            new_max_mana = old_max_mana + mana_per_level
            character['max_mana'] = new_max_mana

        # Fully restore health on level up
        character['current_hit_points'] = new_max_hp

        # Fully restore mana on level up (only for magic-using classes)
        if class_uses_magic:
            character['current_mana'] = new_max_mana

        # Automatically distribute stat points
        stat_increases = self._distribute_stat_points(character, stat_points)

        # Send level up messages
        stat_gains_text = "\n".join([f"  {stat.capitalize()}: +{amount}" for stat, amount in stat_increases.items() if amount > 0])

        # Build mana line only if class uses magic
        mana_line = f"  Max Mana: {old_max_mana} -> {new_max_mana}\n" if class_uses_magic else ""

        level_up_msg = f"""
========================================
         LEVEL UP!
========================================
  Level: {old_level} -> {new_level}
  Max HP: {old_max_hp} -> {new_max_hp}
{mana_line}
  Stat Increases:
{stat_gains_text}
========================================

Congratulations, {character['name']}! You feel stronger and more capable!
"""

        await self.send_message(player_id, level_up_msg)

        # Notify room
        await self.player_manager.notify_room_except_player(
            room_id,
            player_id,
            f"{character['name']} has gained a level! They are now level {new_level}!"
        )

        # Save character
        if self.game_engine.player_storage:
            username = self.player_manager.get_player_data(player_id).get('username')
            if username:
                self.game_engine.player_storage.save_character_data(username, character)

    # Helper methods

    def get_effective_armor_class(self, character: dict) -> int:
        """Calculate effective armor class including buffs.

        Args:
            character: The character dict

        Returns:
            Total armor class including base AC and buff bonuses
        """
        base_ac = character.get('armor_class', 0)

        # Add bonuses from active buffs
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('effect') == 'ac_bonus':
                base_ac += effect.get('bonus_amount', 0)

        return base_ac

    def calculate_xp_for_level(self, level: int) -> int:
        """Calculate the total XP required to reach a specific level.

        Args:
            level: The target level

        Returns:
            Total XP required to reach that level
        """
        if level <= 1:
            return 0

        base_xp = self.config_manager.get_setting('player', 'leveling', 'base_xp_per_level', default=100)
        multiplier = self.config_manager.get_setting('player', 'leveling', 'xp_multiplier', default=1.5)

        # Calculate cumulative XP: sum of XP needed for each level
        total_xp = 0
        for lvl in range(2, level + 1):
            xp_for_level = int(base_xp * (multiplier ** (lvl - 2)))
            total_xp += xp_for_level

        return total_xp

    def _class_uses_magic(self, class_name: str) -> bool:
        """Check if a character class uses magic.

        Args:
            class_name: The name of the class (e.g., 'fighter', 'sorcerer')

        Returns:
            True if the class uses magic, False otherwise
        """
        try:
            classes_file = Path("data/player/classes.json")
            with open(classes_file, 'r') as f:
                classes_data = json.load(f)
                class_key = class_name.lower()
                if class_key in classes_data:
                    return classes_data[class_key].get('uses_magic', False)
        except Exception as e:
            self.logger.warning(f"Could not load class data: {e}")

        # Default: assume non-magic class
        return False

    def _distribute_stat_points(self, character: dict, points_to_distribute: int) -> dict:
        """Automatically distribute stat points across character stats up to their maximums.

        Args:
            character: The character dictionary
            points_to_distribute: Number of stat points to distribute

        Returns:
            Dictionary of stat name -> amount increased
        """
        # Load race data to get modifiers
        races_file = Path("data/player/races.json")
        race_modifiers = {}
        try:
            with open(races_file, 'r') as f:
                races_data = json.load(f)
                player_race = character.get('race', 'human')
                if player_race in races_data:
                    race_modifiers = races_data[player_race].get('stat_modifiers', {})
        except Exception as e:
            self.logger.warning(f"Could not load race modifiers: {e}")

        # Get base stat maximums from config
        starting_stats = self.config_manager.get_setting('player', 'starting_stats', default={})

        # Define stat list (map character field names to config names)
        stat_mapping = {
            'strength': 'strength',
            'dexterity': 'dexterity',
            'constitution': 'constitution',
            'vitality': 'vitality',
            'intellect': 'intelligence',  # character uses 'intellect', config uses 'intelligence'
            'wisdom': 'wisdom',
            'charisma': 'charisma'
        }

        # Calculate max for each stat (base max + race modifier)
        stat_maxes = {}
        for char_stat, config_stat in stat_mapping.items():
            base_max = starting_stats.get(config_stat, {}).get('max', 20)
            race_mod = race_modifiers.get(config_stat, 0)
            stat_maxes[char_stat] = base_max + race_mod

        # Track increases
        stat_increases = {stat: 0 for stat in stat_mapping.keys()}

        # Distribute points randomly
        for _ in range(points_to_distribute):
            # Get stats that haven't reached their maximum
            available_stats = [
                stat for stat in stat_mapping.keys()
                if character.get(stat, 10) < stat_maxes[stat]
            ]

            if not available_stats:
                # All stats are at max
                break

            # Randomly pick a stat and increase it
            chosen_stat = random.choice(available_stats)
            character[chosen_stat] = character.get(chosen_stat, 10) + 1
            stat_increases[chosen_stat] += 1

        return stat_increases

    def _load_races(self):
        """Load race definitions from JSON."""
        try:
            with open('data/player/races.json', 'r') as f:
                return json.load(f)
        except:
            # Fallback to default
            return {"human": {"name": "Human", "description": "Versatile humans", "base_stats": {"strength": 10, "dexterity": 10, "constitution": 10, "intellect": 10, "wisdom": 10, "charisma": 10}}}

    def _load_classes(self):
        """Load class definitions from JSON."""
        try:
            with open('data/player/classes.json', 'r') as f:
                return json.load(f)
        except:
            # Fallback to default
            return {"fighter": {"name": "Fighter", "description": "Martial warrior", "stat_modifiers": {}, "hp_modifier": 1.0, "mana_modifier": 1.0}}
