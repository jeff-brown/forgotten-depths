"""
Magic Command Handler

Handles commands for spell management and casting:
- spellbook - View known spells
- unlearn - Forget a spell
- cast - Cast spells (damage, heal, buff, debuff, drain, etc.)
"""

import time
import random
from ..base_handler import BaseCommandHandler
from ...utils.colors import error_message, success_message, colorize, Colors


class MagicCommandHandler(BaseCommandHandler):
    """Handler for magic and spellcasting commands."""

    async def handle_spellbook_command(self, player_id: int, character: dict):
        """Display the player's spellbook with all known spells."""
        spellbook = character.get('spellbook', [])

        if not spellbook:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "Your spellbook is empty. You haven't learned any spells yet."
            )
            return

        # Load spell data
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})

        # Build spellbook display
        lines = ["=== Your Spellbook ===\n"]

        for spell_id in spellbook:
            spell = spell_data.get(spell_id)
            if not spell:
                self.game_engine.logger.warning(f"Spell '{spell_id}' not found in spell_data for spellbook display")
                lines.append(f"{spell_id} (spell data not found)")
                lines.append("")
                continue

            # Get cooldown info
            cooldowns = character.get('spell_cooldowns', {})
            cooldown_remaining = cooldowns.get(spell_id, 0)

            # Format spell entry - with safe defaults
            name = spell.get('name', spell_id)
            level = spell.get('level', '?')
            mana = spell.get('mana_cost', '?')
            spell_type = spell.get('type', 'unknown')

            # Type-specific info
            type_info = ""
            if spell_type == 'damage':
                damage = spell.get('damage', '?')
                damage_type = spell.get('damage_type', 'physical')
                type_info = f"Damage: {damage} ({damage_type})"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'heal':
                effect = spell.get('effect', 'heal_hit_points')
                if effect == 'heal_hit_points':
                    heal = spell.get('heal_amount', '?')
                    type_info = f"Healing: {heal} HP"
                elif effect == 'cure_poison':
                    type_info = "Cures poison"
                elif effect == 'cure_hunger':
                    type_info = "Cures hunger"
                elif effect == 'cure_thirst':
                    type_info = "Quenches thirst"
                elif effect == 'cure_paralysis':
                    type_info = "Cures paralysis"
                elif effect == 'cure_drain':
                    type_info = "Restores drained stats"
                elif effect == 'regeneration':
                    type_info = "Regeneration over time"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'buff':
                effect = spell.get('effect', 'unknown')
                duration = spell.get('duration', 0)
                bonus = spell.get('bonus_amount', 0)
                if effect == 'ac_bonus':
                    type_info = f"Armor Class +{bonus} ({duration} seconds)"
                elif effect == 'invisible':
                    type_info = f"Invisibility ({duration} seconds)"
                else:
                    type_info = f"Effect: {effect} ({duration} seconds)"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'enhancement':
                effect = spell.get('effect', 'unknown')
                effect_amount = spell.get('effect_amount', '?')
                effect_map = {
                    'enhance_agility': 'Dexterity',
                    'enhance_dexterity': 'Dexterity',
                    'enhance_strength': 'Strength',
                    'enhance_constitution': 'Constitution',
                    'enhance_physique': 'Constitution',
                    'enhance_vitality': 'Vitality',
                    'enhance_stamina': 'Vitality',
                    'enhance_mental': 'INT/WIS/CHA',
                    'enhance_body': 'STR/DEX/CON'
                }
                stat_name = effect_map.get(effect, effect)
                type_info = f"Enhances {stat_name} by {effect_amount}"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'drain':
                damage = spell.get('damage', '?')
                damage_type = spell.get('damage_type', 'force')
                effect = spell.get('effect', None)
                type_info = f"Damage: {damage} ({damage_type})"
                if effect:
                    effect_amount = spell.get('effect_amount', '?')
                    duration = spell.get('effect_duration', '?')
                    effect_map = {
                        'drain_mana': 'Mana',
                        'drain_health': 'Health',
                        'drain_agility': 'Dexterity',
                        'drain_physique': 'Constitution',
                        'drain_stamina': 'Vitality',
                        'drain_mental': 'INT/WIS/CHA',
                        'drain_body': 'STR/DEX/CON'
                    }
                    drain_name = effect_map.get(effect, effect)
                    type_info += f" + Drains {drain_name} by {effect_amount} ({duration} rounds)"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'debuff':
                effect = spell.get('effect', 'unknown')
                duration = spell.get('effect_duration', '?')
                damage = spell.get('damage', None)
                if effect == 'paralyze':
                    type_info = f"Paralyzes target ({duration} rounds)"
                elif effect == 'charm':
                    type_info = f"Charms target, preventing attacks ({duration} rounds)"
                else:
                    type_info = f"Effect: {effect} ({duration} rounds)"
                if damage:
                    damage_type = spell.get('damage_type', 'force')
                    type_info += f" + Damage: {damage} ({damage_type})"
                # Add area of effect if applicable
                aoe = spell.get('area_of_effect', 'Single')
                if aoe == 'Area':
                    type_info += " [AOE]"
            elif spell_type == 'summon':
                type_info = "Summons a creature"

            cooldown_text = ""
            if cooldown_remaining > 0:
                cooldown_text = f" [COOLDOWN: {cooldown_remaining} rounds]"

            lines.append(f"{name} (Level {level}) - {mana} mana{cooldown_text}")
            lines.append(f"  {spell['description']}")
            if type_info:
                lines.append(f"  {type_info}")
            lines.append("")

        await self.game_engine.connection_manager.send_message(
            player_id,
            "\n".join(lines)
        )

    async def handle_unlearn_spell_command(self, player_id: int, character: dict, spell_input: str):
        """Handle unlearning/forgetting a spell."""
        from ...utils.colors import error_message, success_message

        spellbook = character.get('spellbook', [])

        if not spellbook:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Your spellbook is empty. You don't know any spells to unlearn.")
            )
            return

        # Load spell data
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})

        # Find the spell by matching spell_input against spell IDs or spell names
        spell_id = None
        spell_name = None
        spell_input_lower = spell_input.lower()

        # First, try exact match on spell ID
        if spell_input_lower in spellbook:
            spell_id = spell_input_lower
            spell = spell_data.get(spell_id, {})
            spell_name = spell.get('name', spell_id)
        else:
            # Try partial match on spell name or ID
            matches = []
            for sid in spellbook:
                spell = spell_data.get(sid, {})
                sname = spell.get('name', sid)

                # Check if input matches spell ID or name (case insensitive, partial match)
                if spell_input_lower in sid.lower() or spell_input_lower in sname.lower():
                    matches.append((sid, sname))

            if len(matches) == 0:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You don't know a spell called '{spell_input}'. Use 'spellbook' to see your spells.")
                )
                return
            elif len(matches) == 1:
                spell_id, spell_name = matches[0]
            else:
                # Multiple matches - show options
                lines = [error_message(f"Multiple spells match '{spell_input}':")]
                for sid, sname in matches:
                    lines.append(f"  - {sname} ({sid})")
                lines.append("Please be more specific.")
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "\n".join(lines)
                )
                return

        # Remove the spell from spellbook
        character['spellbook'].remove(spell_id)

        # Also remove any active cooldown for this spell
        if 'spell_cooldowns' in character and spell_id in character['spell_cooldowns']:
            del character['spell_cooldowns'][spell_id]

        # Send success message
        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You have forgotten the spell: {spell_name}")
        )

        # Notify room
        room_id = character.get('room_id')
        await self.game_engine.player_manager.notify_room_except_player(
            room_id,
            player_id,
            f"{character.get('name', 'Someone')} concentrates deeply, erasing knowledge of a spell from their mind."
        )

    async def handle_cast_command(self, player_id: int, character: dict, params: str):
        """Handle casting a spell."""
        # Parse spell name and optional target from params
        # Format: "cast <spell_name> [target_name]"
        # Spell names can have spaces (e.g., "cure light wounds", "ice shard")

        # Load spell data
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})
        spellbook = character.get('spellbook', [])

        # Find the spell by matching against known spell names
        # Try longest matches first to handle multi-word spell names
        spell_id = None
        spell = None
        target_name = None

        params_lower = params.strip().lower()

        # Build list of possible spells from spellbook
        known_spells = [(sid, spell_data[sid]) for sid in spellbook if sid in spell_data]

        # Sort by spell name length (longest first) to match multi-word names correctly
        known_spells.sort(key=lambda x: len(x[1]['name']), reverse=True)

        # Try to match spell name at the beginning of params
        for sid, s in known_spells:
            spell_name_lower = s['name'].lower()
            spell_id_lower = sid.lower()

            # Try matching by spell name
            if params_lower.startswith(spell_name_lower):
                spell_id = sid
                spell = s
                # Everything after the spell name is the target
                remainder = params[len(spell_name_lower):].strip()
                target_name = remainder if remainder else None
                break
            # Try matching by spell ID (e.g., "ice_shard" or "iceshard")
            elif params_lower.startswith(spell_id_lower):
                spell_id = sid
                spell = s
                remainder = params[len(spell_id_lower):].strip()
                target_name = remainder if remainder else None
                break
            # Try matching spell ID without underscores
            elif params_lower.startswith(spell_id_lower.replace('_', '')):
                spell_id = sid
                spell = s
                spell_id_no_underscore = spell_id_lower.replace('_', '')
                remainder = params[len(spell_id_no_underscore):].strip()
                target_name = remainder if remainder else None
                break

        if not spell:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Unknown spell: {params.strip()}"
            )
            return

        # Check if player knows this spell
        if spell_id not in spellbook:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't know the spell '{spell['name']}'."
            )
            return

        # Check class restriction and spell level restrictions
        player_class = character.get('class', '').lower()
        spell_class_restriction = spell.get('class_restriction', '').lower()

        if spell_class_restriction and spell_class_restriction != player_class:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Only {spell_class_restriction}s can cast {spell['name']}."
            )
            return

        # Check spell level restrictions based on class
        spell_level = spell.get('level', 1)

        # Get max spell level from class data
        classes_data = self.game_engine.config_manager.game_data.get('classes', {})
        class_info = classes_data.get(player_class, {})
        max_spell_level = class_info.get('max_spell_level', 99)  # Default to 99 (no restriction)

        if max_spell_level > 0 and spell_level > max_spell_level:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"As a {character.get('class', 'adventurer')}, you can only cast spells up to level {max_spell_level}. {spell['name']} is level {spell_level}."
            )
            return

        # Check if player is paralyzed
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('type') == 'paralyze' or effect.get('effect') == 'paralyze':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "You are paralyzed and cannot cast spells!"
                )
                return

        # Check cooldown
        cooldowns = character.get('spell_cooldowns', {})
        if spell_id in cooldowns and cooldowns[spell_id] > 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"{spell['name']} is still on cooldown ({cooldowns[spell_id]} rounds remaining)."
            )
            return

        # Check if player is magically fatigued (all spell types cause fatigue)
        if self._is_spell_fatigued(player_id):
            fatigue_time = self._get_spell_fatigue_remaining(player_id)
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You are too magically exhausted to cast spells! Wait {fatigue_time:.1f} more seconds."
            )
            return

        # Validate target BEFORE consuming resources (mana and fatigue)
        # This prevents wasting resources on invalid targets
        if spell.get('requires_target', False):
            if not target_name:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You need a target to cast {spell['name']}. Use: cast {spell['name']} <target>"
                )
                return

            # Check if target exists
            room_id = character.get('room_id')
            target = await self.game_engine.combat_system.find_combat_target(room_id, target_name)

            if not target:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You don't see '{target_name}' here."
                )
                return

        # Check for duplicate buff/enhancement (before mana consumption)
        if spell['type'] in ['buff', 'enhancement']:
            # For self-cast buffs (no target specified and not AOE)
            area_of_effect = spell.get('area_of_effect', 'Single')
            if not target_name and area_of_effect != 'Area':
                spell_name = spell.get('name', 'Unknown')
                effect = spell.get('effect', 'unknown')

                # Initialize active_effects if it doesn't exist
                if 'active_effects' not in character:
                    character['active_effects'] = []

                active_effects = character['active_effects']

                for existing_effect in active_effects:
                    existing_spell_id = existing_effect.get('spell_id')
                    existing_effect_name = existing_effect.get('effect')

                    if existing_spell_id == spell_name or existing_effect_name == effect:
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            f"You are already under the effect of {spell_name}!"
                        )
                        return

        # Check summon spell restrictions (before mana consumption)
        if spell['type'] == 'summon':
            # Summon spells should not have a target
            if target_name:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("That spell does not need to be cast at a specific person or creature.")
                )
                return

            # Check room restrictions - no summoning in SAFE rooms
            room_id = character.get('room_id')
            room = self.game_engine.world_manager.get_room(room_id)
            if room:
                is_safe = getattr(room, 'is_safe', False)
                if is_safe:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message("Sorry, summoning spells are not permitted here.")
                    )
                    return

        # Check mana
        mana_cost = spell['mana_cost']
        current_mana = character.get('current_mana', 0)

        if current_mana < mana_cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't have enough mana to cast {spell['name']}. (Need {mana_cost}, have {current_mana})"
            )
            return

        # Deduct mana
        character['current_mana'] = current_mana - mana_cost

        # Apply spell fatigue for ALL spell types (prevents spam casting)
        # Cooldown acts as a multiplier: 0 = 10s, 1 = 10s, 2 = 20s, 3 = 30s, etc.
        cooldown = spell.get('cooldown', 0)
        multiplier = max(1, cooldown)  # Minimum 1x for cooldown 0 or 1
        self._apply_spell_fatigue(player_id, multiplier)

        # Set cooldown (no longer used for fatigue, kept for potential future use)
        if spell.get('cooldown', 0) > 0:
            if 'spell_cooldowns' not in character:
                character['spell_cooldowns'] = {}
            character['spell_cooldowns'][spell_id] = spell['cooldown']

        # Check for spell failure
        caster_level = character.get('level', 1)
        caster_intelligence = character.get('intellect', 10)
        spell_min_level = spell.get('level', 1)

        failure_chance = self._calculate_player_spell_failure_chance(
            caster_level, caster_intelligence, spell_min_level
        )

        if random.random() < failure_chance:
            # Spell failed!
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You attempt to cast {spell['name']}, but the spell fizzles and fails!"
            )
            room_id = character.get('room_id')
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')}'s spell fizzles and fails!"
            )
            # Note: Mana was already consumed and fatigue already applied
            return

        # Apply spell effect based on type
        room_id = character.get('room_id')

        if spell['type'] == 'damage':
            await self._cast_damage_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] == 'heal':
            await self._cast_heal_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] == 'drain':
            await self._cast_drain_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] == 'debuff':
            await self._cast_debuff_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] in ['buff', 'enhancement']:
            await self._cast_buff_spell(player_id, character, spell, room_id, target_name)
        elif spell['type'] == 'summon':
            await self._cast_summon_spell(player_id, character, spell, room_id, target_name)

    async def _cast_damage_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a damage spell."""
        # Check if spell requires target
        if spell.get('requires_target', False):
            if not target_name:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You need a target to cast {spell['name']}. Use: cast {spell['name']} <target>"
                )
                return

            # Find target using combat system's method
            target = await self.game_engine.combat_system.find_combat_target(room_id, target_name)

            if not target:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You don't see '{target_name}' here."
                )
                return

            # Create temporary entities for hit calculation
            class TempCharacter:
                def __init__(self, char_data):
                    self.name = char_data['name']
                    self.level = char_data.get('level', 1)
                    self.strength = char_data.get('strength', 10)
                    self.dexterity = char_data.get('dexterity', 10)
                    self.constitution = char_data.get('constitution', 10)
                    self.intelligence = char_data.get('intellect', 10)
                    self.wisdom = char_data.get('wisdom', 10)
                    self.charisma = char_data.get('charisma', 10)

            class TempMob:
                def __init__(self, mob_data):
                    self.name = mob_data.get('name', 'Unknown')
                    self.level = mob_data.get('level', 1)
                    self.strength = 12
                    self.dexterity = 10
                    self.constitution = 12
                    self.intelligence = 8
                    self.wisdom = 10
                    self.charisma = 6

            temp_char = TempCharacter(character)
            temp_mob = TempMob(target)

            # Import damage calculator
            from ...game.combat.damage_calculator import DamageCalculator

            # Check spell hit (spells use INT for accuracy instead of DEX)
            mob_armor = target.get('armor_class', 0)
            base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)

            # For spells, swap INT/WIS for DEX in hit calculation
            saved_dex = temp_char.dexterity
            temp_char.dexterity = temp_char.intelligence  # Use INT for spell accuracy

            outcome = DamageCalculator.check_attack_outcome(temp_char, temp_mob, mob_armor, base_hit_chance)

            # Restore original DEX
            temp_char.dexterity = saved_dex

            if outcome['result'] == 'miss':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but it misses {target['name']}!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')}'s {spell['name']} misses {target['name']}!"
                )
                return
            elif outcome['result'] == 'dodge':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but {target['name']} dodges it!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{target['name']} dodges {character.get('name', 'Someone')}'s {spell['name']}!"
                )
                return
            elif outcome['result'] == 'deflect':
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but {target['name']}'s defenses deflect it!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{target['name']}'s defenses deflect {character.get('name', 'Someone')}'s {spell['name']}!"
                )
                return

            # Spell hit! Roll damage
            damage_roll = spell.get('damage', '1d6')
            base_damage = self._roll_dice(damage_roll)

            # Apply level scaling if spell supports it
            caster_level = character.get('level', 1)
            damage = self._calculate_scaled_spell_value(base_damage, spell, caster_level)

            # Apply damage
            target['health'] -= damage

            # Apply poison DOT if damage type is poison
            damage_type = spell.get('damage_type', 'magical')
            poison_message = ""
            if damage_type == 'poison':
                poison_duration = spell.get('poison_duration', 5)
                poison_damage = spell.get('poison_damage', '1d2')

                # Initialize poison_effects if needed
                if 'poison_effects' not in target:
                    target['poison_effects'] = []

                # Add poison effect
                target['poison_effects'].append({
                    'duration': poison_duration,
                    'damage': poison_damage,
                    'caster_id': player_id,
                    'spell_name': spell['name']
                })
                poison_message = f" {target['name']} is poisoned!"

            # Send messages using cast_message and hit_message if available
            from ...utils.colors import spell_cast

            # Get cast and hit messages from spell data, with fallbacks
            cast_msg = spell.get('cast_message', "{caster} casts {spell} at {target}!")
            hit_msg = spell.get('hit_message', "It strikes for {damage} {damage_type} damage!")

            # Format cast message for caster
            caster_name = character.get('name', 'You')
            formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', target['name']).replace('{spell}', spell['name'])

            # Format hit message
            formatted_hit = hit_msg.replace('{damage}', str(int(damage))).replace('{damage_type}', damage_type).replace('{target}', target['name'])

            # Combine with poison message if applicable
            spell_msg = f"{formatted_cast} {formatted_hit}{poison_message}"

            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(spell_msg, damage_type=damage_type, spell_type=spell.get('type'))
            )

            # Notify room using cast_message
            room_cast_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', target['name']).replace('{spell}', spell['name'])
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_cast_msg
            )

            # Check if mob died
            if target['health'] <= 0:
                # Send death message
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"{target['name']} has been defeated!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{target['name']} has been defeated!"
                )

                # Handle loot, gold, and experience
                await self.game_engine.combat_system.handle_mob_loot_drop(player_id, target, room_id)

                # Remove mob from room
                mob_participant_id = self.game_engine.combat_system.get_mob_identifier(target)
                await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)
            else:
                # Mob survived - set/update aggro on the caster
                if 'aggro_target' not in target:
                    target['aggro_target'] = player_id
                    target['aggro_room'] = room_id
                    self.game_engine.logger.debug(f"[AGGRO] {target['name']} is now aggro'd on player {player_id} (spell attack)")
                # Update aggro timestamp if this is the current aggro target
                if target.get('aggro_target') == player_id:
                    import time
                    target['aggro_last_attack'] = time.time()

        else:
            # Area spell (no specific target needed) - hits all mobs in the room
            mobs_in_room = self.game_engine.room_mobs.get(room_id, [])

            if not mobs_in_room:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but there are no enemies to affect!"
                )
                return

            # Roll damage once for the spell
            damage_roll = spell.get('damage', '1d6')
            base_damage = self._roll_dice(damage_roll)

            # Apply level scaling if spell supports it
            caster_level = character.get('level', 1)
            damage = self._calculate_scaled_spell_value(base_damage, spell, caster_level)

            # Send cast message to caster using cast_message and hit_message
            from ...utils.colors import spell_cast
            damage_type = spell.get('damage_type', 'magical')

            # Get cast and hit messages from spell data, with fallbacks
            cast_msg = spell.get('cast_message', "{caster} casts {spell}!")
            hit_msg = spell.get('hit_message', "A wave of {damage_type} energy fills the room!")

            # Format cast message for caster
            formatted_cast = cast_msg.replace('{caster}', 'You').replace('{spell}', spell['name'])

            # Format hit message - replace damage and damage_type
            formatted_hit = hit_msg.replace('{damage}', str(int(damage))).replace('{damage_type}', damage_type)

            spell_msg = f"{formatted_cast} {formatted_hit}"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(spell_msg, damage_type=damage_type, spell_type=spell.get('type'))
            )

            # Notify room using cast_message and hit_message
            room_cast_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{spell}', spell['name'])
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{room_cast_msg} {formatted_hit}"
            )

            # Track defeated mobs to remove after loop
            defeated_mobs = []

            # Apply damage to all mobs
            for mob in mobs_in_room[:]:  # Create copy to avoid modification during iteration
                # Apply damage
                mob['health'] -= damage

                # Apply poison DOT if damage type is poison
                poison_message = ""
                if damage_type == 'poison':
                    poison_duration = spell.get('poison_duration', 5)
                    poison_damage = spell.get('poison_damage', '1d2')

                    # Initialize poison_effects if needed
                    if 'poison_effects' not in mob:
                        mob['poison_effects'] = []

                    # Add poison effect
                    mob['poison_effects'].append({
                        'duration': poison_duration,
                        'damage': poison_damage,
                        'caster_id': player_id,
                        'spell_name': spell['name']
                    })
                    poison_message = " (poisoned!)"

                # Send damage message
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"  {mob['name']} takes {int(damage)} {spell.get('damage_type', 'magical')} damage!{poison_message}"
                )

                # Check if mob died
                if mob['health'] <= 0:
                    defeated_mobs.append(mob)
                else:
                    # Mob survived - set aggro on the caster
                    if 'aggro_target' not in mob:
                        mob['aggro_target'] = player_id
                        mob['aggro_room'] = room_id
                        self.game_engine.logger.debug(f"[AGGRO] {mob['name']} is now aggro'd on player {player_id} (AOE spell)")
                    # Update aggro timestamp
                    if mob.get('aggro_target') == player_id:
                        import time
                        mob['aggro_last_attack'] = time.time()

            # Handle defeated mobs
            for mob in defeated_mobs:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"  {mob['name']} has been defeated!"
                )
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"  {mob['name']} has been defeated!"
                )

                # Handle loot, gold, and experience
                await self.game_engine.combat_system.handle_mob_loot_drop(player_id, mob, room_id)

                # Remove mob from room
                mob_participant_id = self.game_engine.combat_system.get_mob_identifier(mob)
                await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)

    async def _cast_heal_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a healing spell or status cure spell."""
        from ...utils.colors import spell_cast

        # Check if this is a status cure spell instead of HP healing
        effect = spell.get('effect', 'heal_hit_points')

        if effect == 'cure_poison':
            # This is a cure poison spell, not a healing spell
            await self._cast_cure_poison_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect == 'cure_hunger':
            # Cure hunger spell
            await self._cast_cure_hunger_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect == 'cure_thirst':
            # Cure thirst spell
            await self._cast_cure_thirst_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect == 'cure_paralysis':
            # Cure paralysis spell
            await self._cast_cure_paralysis_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect == 'cure_drain':
            # Cure drain spell
            await self._cast_cure_drain_spell(player_id, character, spell, room_id, target_name)
            return
        elif effect in ['cure_sleep', 'cure_blind']:
            # Other status cure effects - implement later if needed
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"The {effect} effect is not yet implemented."
            )
            return

        # This is a regular HP healing spell
        # Roll healing amount
        heal_roll = spell.get('heal_amount', '1d8')
        base_heal = self._roll_dice(heal_roll)

        # Apply level scaling if spell supports it
        caster_level = character.get('level', 1)
        heal_amount = self._calculate_scaled_spell_value(base_heal, spell, caster_level)

        # Check if this is an AOE heal
        area_of_effect = spell.get('area_of_effect', 'Single')

        if area_of_effect == 'Area':
            # AOE heal - heal all players in the room
            healed_players = []

            # Get all connected players
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room
                if other_character.get('room_id') != room_id:
                    continue

                # Get current and max health
                current_health = other_character.get('current_hit_points', 0)
                max_health = other_character.get('max_hit_points', 100)

                # Skip if already at full health
                if current_health >= max_health:
                    continue

                # Apply healing
                actual_heal = min(heal_amount, max_health - current_health)
                other_character['current_hit_points'] = min(current_health + heal_amount, max_health)

                # Send message to healed player using cast_message and hit_message
                cast_msg = spell.get('cast_message', "{caster} casts {spell} on {target}!")
                hit_msg = spell.get('hit_message', "Healing energy restores {damage} hit points!")

                if other_player_id == player_id:
                    formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', 'yourself').replace('{spell}', spell['name'])
                else:
                    formatted_cast = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', 'you').replace('{spell}', spell['name'])

                formatted_hit = hit_msg.replace('{damage}', str(int(actual_heal)))
                heal_msg = f"{formatted_cast} {formatted_hit}\nHealth: {int(other_character['current_hit_points'])} / {int(max_health)}"

                await self.game_engine.connection_manager.send_message(
                    other_player_id,
                    spell_cast(heal_msg, spell_type='heal')
                )

                healed_players.append(other_character.get('name', 'Someone'))

            # Notify room about the AOE heal using cast_message
            cast_msg = spell.get('cast_message', "{caster} casts {spell}!")
            room_cast_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{spell}', spell['name'])

            if healed_players:
                room_msg = room_cast_msg
            else:
                room_msg = f"{room_cast_msg} But no one needs healing!"

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

        else:
            # Single-target heal
            # Determine target
            if spell.get('requires_target', False) and target_name:
                # Find target player by name
                target_player_id = None
                target_character = None

                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    other_character = other_conn_data.get('character')
                    if not other_character:
                        continue

                    # Check if player is in same room and name matches
                    if other_character.get('room_id') == room_id:
                        if other_character.get('name', '').lower() == target_name.lower():
                            target_player_id = other_player_id
                            target_character = other_character
                            break

                if not target_character:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You don't see '{target_name}' here."
                    )
                    return
            else:
                # Default to self-healing
                target_player_id = player_id
                target_character = character

            # Get current and max health
            current_health = target_character.get('current_hit_points', 0)
            max_health = target_character.get('max_hit_points', 100)

            # Check if target is already at full health
            if current_health >= max_health:
                if target_player_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']}, but you are already at full health!"
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are already at full health!"
                    )
                return

            # Apply healing
            actual_heal = min(heal_amount, max_health - current_health)
            target_character['current_hit_points'] = min(current_health + heal_amount, max_health)

            # Send messages using cast_message and hit_message
            cast_msg = spell.get('cast_message', "{caster} casts {spell} on {target}!")
            hit_msg = spell.get('hit_message', "Healing energy restores {damage} hit points!")

            if target_player_id == player_id:
                # Self-heal
                formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', 'yourself').replace('{spell}', spell['name'])
                formatted_hit = hit_msg.replace('{damage}', str(int(actual_heal)))
                heal_msg = f"{formatted_cast} {formatted_hit}\nHealth: {int(target_character['current_hit_points'])} / {int(max_health)}"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(heal_msg, spell_type='heal')
                )

                room_cast_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', 'themselves').replace('{spell}', spell['name'])
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    room_cast_msg
                )
            else:
                # Healing another player
                cast_msg = spell.get('cast_message', "{caster} casts {spell} on {target}!")
                hit_msg = spell.get('hit_message', "Healing energy restores {damage} hit points!")

                # Message to caster
                formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', target_character.get('name', 'someone')).replace('{spell}', spell['name'])
                formatted_hit = hit_msg.replace('{damage}', str(int(actual_heal)))
                caster_msg = f"{formatted_cast} {formatted_hit}"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(caster_msg, spell_type='heal')
                )

                # Message to target
                target_cast = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', 'you').replace('{spell}', spell['name'])
                target_msg = f"{target_cast} {formatted_hit}\nHealth: {int(target_character['current_hit_points'])} / {int(max_health)}"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    spell_cast(target_msg, spell_type='heal')
                )

                # Notify other players in room (exclude caster and target)
                room_cast_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', target_character.get('name', 'someone')).replace('{spell}', spell['name'])
                notify_msg = f"{room_cast_msg} {formatted_hit}"
                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    if other_player_id == player_id or other_player_id == target_player_id:
                        continue
                    other_character = other_conn_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            notify_msg
                        )

    async def _cast_cure_poison_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure poison spell - removes poison DOT effects from target(s)."""
        from ...utils.colors import spell_cast

        # Check if this is an AOE cure
        area_of_effect = spell.get('area_of_effect', 'Single')

        if area_of_effect == 'Area':
            # AOE cure poison - cure all players in the room
            cured_players = []

            # Get all connected players in the room
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room
                if other_character.get('room_id') != room_id:
                    continue

                # Check if player has poison effects
                if 'poison_effects' in other_character and other_character['poison_effects']:
                    # Clear all poison effects
                    poison_count = len(other_character['poison_effects'])
                    other_character['poison_effects'] = []
                    cured_players.append(other_character.get('name', 'Someone'))

                    # Notify the cured player
                    if other_player_id == player_id:
                        cure_msg = f"You cast {spell['name']}! You are cured of {poison_count} poison effect(s)!"
                    else:
                        cure_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! You are cured of {poison_count} poison effect(s)!"

                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        spell_cast(cure_msg, spell_type='heal')
                    )

            # Notify room
            if cured_players:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, and a purifying mist washes over the room!"
            else:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, but no one is poisoned!"

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

        else:
            # Single-target cure poison
            # Determine target
            if spell.get('requires_target', False) and target_name:
                # Find target player by name
                target_player_id = None
                target_character = None

                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    other_character = other_conn_data.get('character')
                    if not other_character:
                        continue

                    # Check if player is in same room and name matches
                    if other_character.get('room_id') == room_id:
                        if other_character.get('name', '').lower() == target_name.lower():
                            target_player_id = other_player_id
                            target_character = other_character
                            break

                if not target_character:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You don't see '{target_name}' here."
                    )
                    return
            else:
                # Default to self-curing
                target_player_id = player_id
                target_character = character

            # Check if target has poison effects
            if 'poison_effects' not in target_character or not target_character['poison_effects']:
                if target_player_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']}, but you are not poisoned!"
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are not poisoned!"
                    )
                return

            # Clear poison effects
            poison_count = len(target_character['poison_effects'])
            target_character['poison_effects'] = []

            # Send messages
            if target_player_id == player_id:
                # Self-cure
                cure_msg = f"You cast {spell['name']}! You are cured of {poison_count} poison effect(s)!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(cure_msg, spell_type='heal')
                )

                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')} casts {spell['name']} and a green aura surrounds them!"
                )
            else:
                # Curing another player
                caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! They are cured of {poison_count} poison effect(s)!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(caster_msg, spell_type='heal')
                )

                target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! You are cured of {poison_count} poison effect(s)!"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    spell_cast(target_msg, spell_type='heal')
                )

                # Notify other players in room (exclude caster and target)
                notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, who is cured of poison!"
                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    if other_player_id == player_id or other_player_id == target_player_id:
                        continue
                    other_character = other_conn_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            notify_msg
                        )

    async def _cast_cure_hunger_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure hunger spell - restores hunger to full for target(s)."""
        from ...utils.colors import spell_cast

        # Check if this is an AOE cure
        area_of_effect = spell.get('area_of_effect', 'Single')

        if area_of_effect == 'Area':
            # AOE cure hunger - cure all players in the room
            cured_players = []

            # Get all connected players in the room
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room
                if other_character.get('room_id') != room_id:
                    continue

                # Restore hunger to full
                current_hunger = other_character.get('hunger', 100)
                if current_hunger < 100:
                    other_character['hunger'] = 100
                    cured_players.append(other_character.get('name', 'Someone'))

                    # Notify the cured player
                    if other_player_id == player_id:
                        cure_msg = f"You cast {spell['name']}! Your hunger is completely satisfied!"
                    else:
                        cure_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your hunger is completely satisfied!"

                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        spell_cast(cure_msg, spell_type='heal')
                    )

            # Notify room
            if cured_players:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, and a brownish mist fills the room!"
            else:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, but no one is hungry!"

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

        else:
            # Single-target cure hunger
            # Determine target
            if spell.get('requires_target', False) and target_name:
                # Find target player by name
                target_player_id = None
                target_character = None

                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    other_character = other_conn_data.get('character')
                    if not other_character:
                        continue

                    # Check if player is in same room and name matches
                    if other_character.get('room_id') == room_id:
                        if other_character.get('name', '').lower() == target_name.lower():
                            target_player_id = other_player_id
                            target_character = other_character
                            break

                if not target_character:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You don't see '{target_name}' here."
                    )
                    return
            else:
                # Default to self-curing
                target_player_id = player_id
                target_character = character

            # Check if target is hungry
            current_hunger = target_character.get('hunger', 100)
            if current_hunger >= 100:
                if target_player_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']}, but you are not hungry!"
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are not hungry!"
                    )
                return

            # Restore hunger to full
            target_character['hunger'] = 100

            # Send messages
            if target_player_id == player_id:
                # Self-cure
                cure_msg = f"You cast {spell['name']}! Your hunger is completely satisfied!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(cure_msg, spell_type='heal')
                )

                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')} casts {spell['name']} and a brownish aura surrounds them!"
                )
            else:
                # Curing another player
                caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! Their hunger is completely satisfied!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(caster_msg, spell_type='heal')
                )

                target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your hunger is completely satisfied!"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    spell_cast(target_msg, spell_type='heal')
                )

                # Notify other players in room (exclude caster and target)
                notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, satisfying their hunger!"
                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    if other_player_id == player_id or other_player_id == target_player_id:
                        continue
                    other_character = other_conn_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            notify_msg
                        )

    async def _cast_cure_thirst_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure thirst spell - restores thirst to full for target(s)."""
        from ...utils.colors import spell_cast

        # Check if this is an AOE cure
        area_of_effect = spell.get('area_of_effect', 'Single')

        if area_of_effect == 'Area':
            # AOE cure thirst - cure all players in the room
            cured_players = []

            # Get all connected players in the room
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room
                if other_character.get('room_id') != room_id:
                    continue

                # Restore thirst to full
                current_thirst = other_character.get('thirst', 100)
                if current_thirst < 100:
                    other_character['thirst'] = 100
                    cured_players.append(other_character.get('name', 'Someone'))

                    # Notify the cured player
                    if other_player_id == player_id:
                        cure_msg = f"You cast {spell['name']}! Your thirst is completely quenched!"
                    else:
                        cure_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your thirst is completely quenched!"

                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        spell_cast(cure_msg, spell_type='heal')
                    )

            # Notify room
            if cured_players:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, and a cool blue mist fills the room!"
            else:
                room_msg = f"{character.get('name', 'Someone')} casts {spell['name']}, but no one is thirsty!"

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

        else:
            # Single-target cure thirst
            # Determine target
            if spell.get('requires_target', False) and target_name:
                # Find target player by name
                target_player_id = None
                target_character = None

                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    other_character = other_conn_data.get('character')
                    if not other_character:
                        continue

                    # Check if player is in same room and name matches
                    if other_character.get('room_id') == room_id:
                        if other_character.get('name', '').lower() == target_name.lower():
                            target_player_id = other_player_id
                            target_character = other_character
                            break

                if not target_character:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You don't see '{target_name}' here."
                    )
                    return
            else:
                # Default to self-curing
                target_player_id = player_id
                target_character = character

            # Check if target is thirsty
            current_thirst = target_character.get('thirst', 100)
            if current_thirst >= 100:
                if target_player_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']}, but you are not thirsty!"
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are not thirsty!"
                    )
                return

            # Restore thirst to full
            target_character['thirst'] = 100

            # Send messages
            if target_player_id == player_id:
                # Self-cure
                cure_msg = f"You cast {spell['name']}! Your thirst is completely quenched!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(cure_msg, spell_type='heal')
                )

                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{character.get('name', 'Someone')} casts {spell['name']} and a cool blue aura surrounds them!"
                )
            else:
                # Curing another player
                caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! Their thirst is completely quenched!"
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(caster_msg, spell_type='heal')
                )

                target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your thirst is completely quenched!"
                await self.game_engine.connection_manager.send_message(
                    target_player_id,
                    spell_cast(target_msg, spell_type='heal')
                )

                # Notify other players in room (exclude caster and target)
                notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, quenching their thirst!"
                for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                    if other_player_id == player_id or other_player_id == target_player_id:
                        continue
                    other_character = other_conn_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            notify_msg
                        )

    async def _cast_cure_paralysis_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure paralysis spell - removes paralysis effects from target."""
        from ...utils.colors import spell_cast, error_message

        # Determine target
        if spell.get('requires_target', False) and target_name:
            # Find target player by name
            target_player_id = None
            target_character = None

            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room and name matches
                if other_character.get('room_id') == room_id:
                    if other_character.get('name', '').lower() == target_name.lower():
                        target_player_id = other_player_id
                        target_character = other_character
                        break

            if not target_character:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You don't see '{target_name}' here.")
                )
                return
        else:
            # Default to self-curing
            target_player_id = player_id
            target_character = character

        # Check if target has paralysis effects
        if 'active_effects' not in target_character:
            target_character['active_effects'] = []

        # Remove paralysis effects (check both 'paralyze' and 'paralyzed')
        original_count = len(target_character['active_effects'])
        target_character['active_effects'] = [
            effect for effect in target_character['active_effects']
            if effect.get('type') not in ['paralyze', 'paralyzed'] and effect.get('effect') not in ['paralyze', 'paralyzed']
        ]
        effects_removed = original_count - len(target_character['active_effects'])

        if effects_removed == 0:
            # Target is not paralyzed
            if target_player_id == player_id:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but you are not paralyzed!"
                )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they are not paralyzed!"
                )
            return

        # Send messages
        if target_player_id == player_id:
            # Self-cure
            cure_msg = f"You cast {spell['name']}! You can move freely again!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(cure_msg, spell_type='heal')
            )

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} casts {spell['name']} and their paralysis fades!"
            )
        else:
            # Curing another player
            caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! They can move freely again!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(caster_msg, spell_type='heal')
            )

            target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! You can move freely again!"
            await self.game_engine.connection_manager.send_message(
                target_player_id,
                spell_cast(target_msg, spell_type='heal')
            )

            # Notify other players in room (exclude caster and target)
            notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, freeing them from paralysis!"
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                if other_player_id == player_id or other_player_id == target_player_id:
                    continue
                other_character = other_conn_data.get('character')
                if other_character and other_character.get('room_id') == room_id:
                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        notify_msg
                    )

    async def _cast_cure_drain_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a cure drain spell - removes stat drain effects from target."""
        from ...utils.colors import spell_cast, error_message

        # Determine target
        if spell.get('requires_target', False) and target_name:
            # Find target player by name
            target_player_id = None
            target_character = None

            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_conn_data.get('character')
                if not other_character:
                    continue

                # Check if player is in same room and name matches
                if other_character.get('room_id') == room_id:
                    if other_character.get('name', '').lower() == target_name.lower():
                        target_player_id = other_player_id
                        target_character = other_character
                        break

            if not target_character:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You don't see '{target_name}' here.")
                )
                return
        else:
            # Default to self-curing
            target_player_id = player_id
            target_character = character

        # Check if target has drain effects
        if 'active_effects' not in target_character:
            target_character['active_effects'] = []

        # Remove drain effects and restore stats
        original_count = len(target_character['active_effects'])
        drained_effects = [
            effect for effect in target_character['active_effects']
            if effect.get('type') == 'stat_drain' or 'drain' in effect.get('effect', '')
        ]

        # Restore drained stats
        for drain_effect in drained_effects:
            effect_type = drain_effect.get('effect', '')
            drain_amount = drain_effect.get('effect_amount', 0)

            # Restore the stats that were drained
            if 'drain' in effect_type:
                # Map drain effects to stats and restore them
                if effect_type == 'drain_agility':
                    target_character['dexterity'] = target_character.get('dexterity', 10) + drain_amount
                elif effect_type == 'drain_physique':
                    target_character['constitution'] = target_character.get('constitution', 10) + drain_amount
                elif effect_type == 'drain_stamina':
                    target_character['vitality'] = target_character.get('vitality', 10) + drain_amount
                elif effect_type == 'drain_mental':
                    # Restore all mental stats
                    target_character['intelligence'] = target_character.get('intelligence', 10) + drain_amount
                    target_character['intellect'] = target_character.get('intellect', 10) + drain_amount
                    target_character['wisdom'] = target_character.get('wisdom', 10) + drain_amount
                    target_character['charisma'] = target_character.get('charisma', 10) + drain_amount
                elif effect_type == 'drain_body':
                    # Restore all physical stats
                    target_character['strength'] = target_character.get('strength', 10) + drain_amount
                    target_character['dexterity'] = target_character.get('dexterity', 10) + drain_amount
                    target_character['constitution'] = target_character.get('constitution', 10) + drain_amount

        # Remove all drain effects
        target_character['active_effects'] = [
            effect for effect in target_character['active_effects']
            if effect.get('type') != 'stat_drain' and 'drain' not in effect.get('effect', '')
        ]
        effects_removed = len(drained_effects)

        if effects_removed == 0:
            # Target has no drain effects
            if target_player_id == player_id:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']}, but you have no drained stats!"
                )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You cast {spell['name']} on {target_character.get('name', 'someone')}, but they have no drained stats!"
                )
            return

        # Send messages
        if target_player_id == player_id:
            # Self-cure
            cure_msg = f"You cast {spell['name']}! Your drained stats are restored!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(cure_msg, spell_type='heal')
            )

            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} casts {spell['name']} and their strength returns!"
            )
        else:
            # Curing another player
            caster_msg = f"You cast {spell['name']} on {target_character.get('name', 'someone')}! Their drained stats are restored!"
            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(caster_msg, spell_type='heal')
            )

            target_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on you! Your drained stats are restored!"
            await self.game_engine.connection_manager.send_message(
                target_player_id,
                spell_cast(target_msg, spell_type='heal')
            )

            # Notify other players in room (exclude caster and target)
            notify_msg = f"{character.get('name', 'Someone')} casts {spell['name']} on {target_character.get('name', 'someone')}, restoring their vitality!"
            for other_player_id, other_conn_data in self.game_engine.player_manager.connected_players.items():
                if other_player_id == player_id or other_player_id == target_player_id:
                    continue
                other_character = other_conn_data.get('character')
                if other_character and other_character.get('room_id') == room_id:
                    await self.game_engine.connection_manager.send_message(
                        other_player_id,
                        notify_msg
                    )

    async def _cast_drain_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a drain spell that does damage and drains resources or stats."""
        from ...utils.colors import spell_cast, error_message

        # Drain spells require a target
        if not target_name:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You need a target to cast {spell['name']}. Use: cast {spell['name']} <target>")
            )
            return

        # Find target using combat system's method
        target = await self.game_engine.combat_system.find_combat_target(room_id, target_name)

        if not target:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't see '{target_name}' here.")
            )
            return

        # Roll damage
        damage_roll = spell.get('damage', '1d6')
        base_damage = self._roll_dice(damage_roll)

        # Apply level scaling if spell supports it
        caster_level = character.get('level', 1)
        damage = self._calculate_scaled_spell_value(base_damage, spell, caster_level)

        # Get damage type
        damage_type = spell.get('damage_type', 'force')
        effect = spell.get('effect', 'unknown')

        # Create temporary entities for hit calculation (same as damage spell)
        class TempCharacter:
            def __init__(self, char_data):
                self.name = char_data['name']
                self.level = char_data.get('level', 1)
                self.strength = char_data.get('strength', 10)
                self.dexterity = char_data.get('dexterity', 10)
                self.constitution = char_data.get('constitution', 10)
                self.intelligence = char_data.get('intellect', 10)
                self.wisdom = char_data.get('wisdom', 10)
                self.charisma = char_data.get('charisma', 10)

        class TempMob:
            def __init__(self, mob_data):
                self.name = mob_data.get('name', 'Unknown')
                self.level = mob_data.get('level', 1)
                self.strength = 12
                self.dexterity = 10
                self.constitution = 12
                self.intelligence = 8
                self.wisdom = 10
                self.charisma = 6

        temp_char = TempCharacter(character)
        temp_mob = TempMob(target)

        # Import damage calculator
        from ...game.combat.damage_calculator import DamageCalculator

        # Check spell hit (spells use INT for accuracy)
        mob_armor = target.get('armor_class', 0)
        base_hit_chance = self.game_engine.config_manager.get_setting('combat', 'base_hit_chance', default=0.50)

        # For spells, swap INT/WIS for DEX in hit calculation
        saved_dex = temp_char.dexterity
        temp_char.dexterity = temp_char.intelligence

        outcome = DamageCalculator.check_attack_outcome(temp_char, temp_mob, mob_armor, base_hit_chance)

        # Restore original DEX
        temp_char.dexterity = saved_dex

        if outcome['result'] == 'miss':
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cast {spell['name']}, but it misses {target['name']}!"
            )
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')}'s {spell['name']} misses {target['name']}!"
            )
            return
        elif outcome['result'] == 'dodge':
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You cast {spell['name']}, but {target['name']} dodges it!"
            )
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{target['name']} dodges {character.get('name', 'Someone')}'s {spell['name']}!"
            )
            return

        # Apply damage to target
        current_health = target.get('current_hit_points', target.get('max_hit_points', 20))
        new_health = max(0, current_health - damage)
        target['current_hit_points'] = new_health

        # Handle drain effects based on effect type
        drain_message = ""

        if effect == 'drain_mana':
            # Roll drain amount
            effect_amount_roll = spell.get('effect_amount', '-1d2')
            drain_amount = abs(self._roll_dice(effect_amount_roll))

            # Drain mana from target and give to caster
            target_current_mana = target.get('current_mana', 0)
            actual_drain = min(drain_amount, target_current_mana)

            if actual_drain > 0:
                target['current_mana'] = max(0, target_current_mana - actual_drain)
                caster_current_mana = character.get('current_mana', 0)
                caster_max_mana = character.get('max_mana', 50)
                character['current_mana'] = min(caster_current_mana + actual_drain, caster_max_mana)
                drain_message = f" You drain {int(actual_drain)} mana!"

        elif effect == 'drain_health':
            # Life steal - heal the caster for the damage dealt
            # All drain_health spells should heal the caster
            caster_current_hp = character.get('current_hit_points', 0)
            caster_max_hp = character.get('max_hit_points', 100)
            heal_amount = min(damage, caster_max_hp - caster_current_hp)
            if heal_amount > 0:
                character['current_hit_points'] = min(caster_current_hp + heal_amount, caster_max_hp)
                drain_message = f" You absorb {int(heal_amount)} HP!"

        elif effect in ['drain_agility', 'drain_physique', 'drain_stamina', 'drain_mental', 'drain_body']:
            # Stat drain effects - apply debuff that reduces stats over time
            effect_amount_roll = spell.get('effect_amount', '-1d5')
            drain_amount = abs(self._roll_dice(effect_amount_roll))

            # Initialize active_effects if needed
            if 'active_effects' not in target:
                target['active_effects'] = []

            # Add drain debuff (lasts for duration, reducing stats)
            drain_duration = spell.get('effect_duration', 10)  # Default 10 ticks
            target['active_effects'].append({
                'type': 'stat_drain',
                'effect': effect,
                'duration': drain_duration,
                'effect_amount': drain_amount,
                'caster_id': player_id
            })

            # Apply immediate stat reduction
            self._apply_drain_effect(target, effect, drain_amount)
            drain_message = f" {target['name']}'s stats are drained by {drain_amount}!"

        # Get cast and hit messages from spell data, with fallbacks
        cast_msg = spell.get('cast_message', "{caster} casts {spell} at {target}!")
        hit_msg = spell.get('hit_message', "It strikes for {damage} {damage_type} damage!")

        # Format hit message for caster (they see the result)
        formatted_hit = hit_msg.replace('{damage}', str(int(damage))).replace('{damage_type}', damage_type).replace('{target}', target['name']).replace('{caster}', 'you')

        # Send hit message to caster with drain message if applicable
        spell_msg = f"{formatted_hit}{drain_message}"

        # Send message to caster
        await self.game_engine.connection_manager.send_message(
            player_id,
            spell_cast(spell_msg, damage_type=damage_type, spell_type='drain')
        )

        # Notify room using cast_message only (they see the action)
        room_cast_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', target['name']).replace('{spell}', spell['name'])
        await self.game_engine.player_manager.notify_room_except_player(
            room_id,
            player_id,
            room_cast_msg
        )

        # Check if mob died
        if new_health <= 0:
            # Send death message
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"{target['name']} has been defeated!"
            )
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{target['name']} has been defeated!"
            )

            # Handle loot, gold, and experience (must be called before handle_mob_death)
            await self.game_engine.combat_system.handle_mob_loot_drop(player_id, target, room_id)

            # Remove mob from room
            mob_participant_id = self.game_engine.combat_system.get_mob_identifier(target)
            await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)
        else:
            # Mob survived - set/update aggro on the caster
            if 'aggro_target' not in target:
                target['aggro_target'] = player_id
                target['aggro_room'] = room_id
                self.game_engine.logger.debug(f"[AGGRO] {target['name']} is now aggro'd on player {player_id} (drain spell)")
            # Update aggro timestamp if this is the current aggro target
            if target.get('aggro_target') == player_id:
                import time
                target['aggro_last_attack'] = time.time()

    async def _cast_debuff_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a debuff spell (paralyze, slow, etc.) on target(s)."""
        from ...utils.colors import spell_cast

        effect = spell.get('effect', 'unknown')
        effect_duration = spell.get('effect_duration', 5)
        area_of_effect = spell.get('area_of_effect', 'Single')

        # Check if spell requires target
        if spell.get('requires_target', False) and not target_name:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You must specify a target for this spell."
            )
            return

        # Roll damage if the spell has a damage component
        damage = 0
        damage_type = spell.get('damage_type', 'force')
        if 'damage' in spell:
            damage_roll = spell.get('damage', '0')
            damage = self._roll_dice(damage_roll)

        targets_affected = []

        if area_of_effect == 'Area':
            # AOE debuff - affect all mobs in the room
            mobs = self.game_engine.room_mobs.get(room_id, [])

            for mob in mobs:
                # Apply damage if any
                if damage > 0:
                    current_health = mob.get('current_hit_points', mob.get('health', mob.get('max_hit_points', 20)))
                    new_health = max(0, current_health - damage)

                    if 'current_hit_points' in mob:
                        mob['current_hit_points'] = new_health
                    if 'health' in mob:
                        mob['health'] = new_health

                # Apply debuff effect
                if 'active_effects' not in mob:
                    mob['active_effects'] = []

                mob['active_effects'].append({
                    'type': effect,
                    'duration': effect_duration,
                    'effect': effect,
                    'effect_amount': spell.get('effect_amount', 0),
                    'caster_id': player_id
                })

                targets_affected.append(mob['name'])

                # Check if mob died from damage
                if damage > 0 and new_health <= 0:
                    mob_participant_id = self.game_engine.combat_system.get_mob_identifier(mob)
                    await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)

            if targets_affected:
                # Get cast and hit messages from spell data, with fallbacks
                cast_msg = spell.get('cast_message', "{caster} casts {spell}!")
                hit_msg = spell.get('hit_message', "{effect} affects all enemies!")

                # Format cast message for caster
                formatted_cast = cast_msg.replace('{caster}', 'You').replace('{spell}', spell['name'])

                # Format hit message
                effect_name = effect.replace('_', ' ').title()
                formatted_hit = hit_msg.replace('{effect}', effect_name)
                if damage > 0:
                    formatted_hit = formatted_hit.replace('{damage}', str(int(damage))).replace('{damage_type}', damage_type)

                spell_msg = f"{formatted_cast} {formatted_hit}"

                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(spell_msg, spell_type='debuff')
                )

                # Notify room using cast_message
                room_cast_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{spell}', spell['name'])
                await self.game_engine.player_manager.notify_room_except_player(
                    room_id,
                    player_id,
                    f"{room_cast_msg} {formatted_hit}"
                )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "There are no targets in range."
                )

        else:
            # Single target debuff
            if not target_name:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "You must specify a target."
                )
                return

            # Find the target mob
            target = None
            mobs = self.game_engine.room_mobs.get(room_id, [])

            for mob in mobs:
                if target_name.lower() in mob.get('name', '').lower():
                    target = mob
                    break

            if not target:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You don't see {target_name} here."
                )
                return

            # Apply damage if any
            if damage > 0:
                current_health = target.get('current_hit_points', target.get('health', target.get('max_hit_points', 20)))
                max_health = target.get('max_hit_points', target.get('max_health', 20))
                new_health = max(0, current_health - damage)

                if 'current_hit_points' in target:
                    target['current_hit_points'] = new_health
                if 'health' in target:
                    target['health'] = new_health

            # Apply debuff effect
            if 'active_effects' not in target:
                target['active_effects'] = []

            target['active_effects'].append({
                'type': effect,
                'duration': effect_duration,
                'effect': effect,
                'effect_amount': spell.get('effect_amount', 0),
                'caster_id': player_id
            })

            # Get cast and hit messages from spell data, with fallbacks
            cast_msg = spell.get('cast_message', "{caster} casts {spell} at {target}!")
            hit_msg = spell.get('hit_message', "{target} is afflicted with {effect}!")

            # Format cast message for caster
            formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', target['name']).replace('{spell}', spell['name'])

            # Format hit message
            effect_name = effect.replace('_', ' ').title()
            formatted_hit = hit_msg.replace('{target}', target['name']).replace('{effect}', effect_name)
            if damage > 0:
                formatted_hit = formatted_hit.replace('{damage}', str(int(damage))).replace('{damage_type}', damage_type)

            spell_msg = f"{formatted_cast} {formatted_hit}"

            await self.game_engine.connection_manager.send_message(
                player_id,
                spell_cast(spell_msg, spell_type='debuff')
            )

            # Notify room using cast_message
            room_cast_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', target['name']).replace('{spell}', spell['name'])
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{room_cast_msg} {formatted_hit}"
            )

            # Check if mob died from damage
            if damage > 0 and new_health <= 0:
                mob_participant_id = self.game_engine.combat_system.get_mob_identifier(target)
                await self.game_engine.combat_system.handle_mob_death(room_id, mob_participant_id)

    async def _cast_buff_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a buff/enhancement spell on self or target player(s)."""
        from ...utils.colors import spell_cast, error_message

        effect = spell.get('effect', 'unknown')
        duration = spell.get('duration', 0)
        spell_type = spell.get('type', 'buff')
        area_of_effect = spell.get('area_of_effect', 'Single')
        spell_name = spell.get('name', 'Unknown')

        # Calculate effect amount for enhancement spells
        effect_amount = 0
        if spell_type == 'enhancement':
            effect_amount_roll = spell.get('effect_amount', '0')
            if effect_amount_roll and effect_amount_roll != '0':
                # Strip leading + or - sign if present
                effect_amount_roll_str = str(effect_amount_roll).lstrip('+')
                effect_amount = self._roll_dice(effect_amount_roll_str)
            else:
                effect_amount = spell.get('bonus_amount', 0)
        else:
            effect_amount = spell.get('bonus_amount', 0)

        # Determine targets
        targets = []

        if area_of_effect == 'Area':
            # AOE buff - affect all players in the room (including caster)
            for other_player_id, other_player_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_player_data.get('character')
                if other_character and other_character.get('room_id') == room_id:
                    targets.append((other_player_id, other_character, other_player_data.get('username', 'Someone')))
        elif target_name:
            # Single target buff on another player
            target_found = False
            for other_player_id, other_player_data in self.game_engine.player_manager.connected_players.items():
                other_character = other_player_data.get('character')
                if other_character and other_character.get('room_id') == room_id:
                    other_username = other_player_data.get('username', '')
                    if target_name.lower() in other_username.lower():
                        targets.append((other_player_id, other_character, other_username))
                        target_found = True
                        break

            if not target_found:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"You don't see '{target_name}' here."
                )
                return
        else:
            # Self-buff
            targets.append((player_id, character, character.get('name', 'You')))

        # Apply buff to all targets
        for target_id, target_char, target_name_str in targets:
            # Initialize active_effects if needed
            if 'active_effects' not in target_char:
                target_char['active_effects'] = []

            # Check if target already has this buff/enhancement active
            already_has_buff = False
            for existing_effect in target_char['active_effects']:
                if existing_effect.get('spell_id') == spell_name or existing_effect.get('effect') == effect:
                    already_has_buff = True
                    break

            if already_has_buff:
                # Notify caster that target already has this buff
                if target_id == player_id:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message(f"You are already under the effect of {spell_name}!")
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message(f"{target_name_str} is already under the effect of {spell_name}!")
                    )
                continue  # Skip this target

            # Add the buff
            buff = {
                'spell_id': spell_name,
                'effect': effect,
                'duration': duration,
                'bonus_amount': spell.get('bonus_amount', 0),
                'effect_amount': effect_amount
            }
            target_char['active_effects'].append(buff)

            # Apply immediate effect for enhancements
            if spell_type == 'enhancement' and effect_amount > 0:
                effect_msg = self._apply_enhancement_effect(target_char, effect, effect_amount)

                # Get cast and hit messages from spell data, with fallbacks
                cast_msg = spell.get('cast_message', "{caster} casts {spell} on {target}!")
                hit_msg = spell.get('hit_message', "{target} is enhanced!")

                # Message to caster
                if target_id == player_id:
                    formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', 'yourself').replace('{spell}', spell['name'])
                    formatted_hit = hit_msg.replace('{target}', 'You')
                else:
                    formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', target_name_str).replace('{spell}', spell['name'])
                    formatted_hit = hit_msg.replace('{target}', target_name_str)

                spell_msg = f"{formatted_cast} {formatted_hit}"

                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(spell_msg, spell_type='enhancement')
                )

                # Message to target (if different from caster)
                if target_id != player_id:
                    target_cast = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', 'you').replace('{spell}', spell['name'])
                    target_hit = hit_msg.replace('{target}', 'You')
                    await self.game_engine.connection_manager.send_message(
                        target_id,
                        spell_cast(f"{target_cast} {target_hit}", spell_type='enhancement')
                    )
            else:
                # Regular buff message
                # Get cast and hit messages from spell data, with fallbacks
                cast_msg = spell.get('cast_message', "{caster} casts {spell} on {target}!")
                hit_msg = spell.get('hit_message', "{target} gains magical protection!")

                # Message to caster
                if target_id == player_id:
                    formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', 'yourself').replace('{spell}', spell['name'])
                    formatted_hit = hit_msg.replace('{target}', 'You').replace('{caster}', 'You')
                else:
                    formatted_cast = cast_msg.replace('{caster}', 'You').replace('{target}', target_name_str).replace('{spell}', spell['name'])
                    formatted_hit = hit_msg.replace('{target}', target_name_str).replace('{caster}', 'You')

                spell_msg = f"{formatted_cast} {formatted_hit}"

                await self.game_engine.connection_manager.send_message(
                    player_id,
                    spell_cast(spell_msg, spell_type=spell_type)
                )

                # Message to target (if different from caster)
                if target_id != player_id:
                    target_cast = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', 'you').replace('{spell}', spell['name'])
                    target_hit = hit_msg.replace('{target}', 'You').replace('{caster}', character.get('name', 'Someone'))
                    await self.game_engine.connection_manager.send_message(
                        target_id,
                        spell_cast(f"{target_cast} {target_hit}", spell_type=spell_type)
                    )

        # Notify room using cast_message
        cast_msg = spell.get('cast_message', "{caster} casts {spell} on {target}!")

        if area_of_effect == 'Area':
            room_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{spell}', spell['name']).replace(' on {target}', '')
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )
        elif len(targets) > 0 and targets[0][0] != player_id:
            # Notify other players except caster and target
            room_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{target}', targets[0][2]).replace('{spell}', spell['name'])
            for other_player_id, other_player_data in self.game_engine.player_manager.connected_players.items():
                if other_player_id != player_id and other_player_id != targets[0][0]:
                    other_character = other_player_data.get('character')
                    if other_character and other_character.get('room_id') == room_id:
                        await self.game_engine.connection_manager.send_message(
                            other_player_id,
                            room_msg
                        )
        else:
            room_msg = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{spell}', spell['name']).replace(' on {target}', '')
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                room_msg
            )

    def _apply_drain_effect(self, target: dict, effect: str, amount: int):
        """Apply a drain effect to reduce a target's stats.

        Args:
            target: The target (mob or character) dictionary
            effect: The drain effect type
            amount: The amount to drain (reduce)
        """
        drain_map = {
            'drain_agility': 'dexterity',
            'drain_physique': 'constitution',
            'drain_stamina': 'vitality'
        }

        if effect in drain_map:
            stat_key = drain_map[effect]
            current_value = target.get(stat_key, 10)
            target[stat_key] = max(1, current_value - amount)
        elif effect == 'drain_mental':
            # Drain all mental stats (INT, WIS, CHA)
            target['intelligence'] = max(1, target.get('intelligence', target.get('intellect', 10)) - amount)
            target['intellect'] = max(1, target.get('intellect', 10) - amount)
            target['wisdom'] = max(1, target.get('wisdom', 10) - amount)
            target['charisma'] = max(1, target.get('charisma', 10) - amount)
        elif effect == 'drain_body':
            # Drain all physical stats (STR, DEX, CON)
            target['strength'] = max(1, target.get('strength', 10) - amount)
            target['dexterity'] = max(1, target.get('dexterity', 10) - amount)
            target['constitution'] = max(1, target.get('constitution', 10) - amount)

    def _apply_enhancement_effect(self, character: dict, effect: str, amount: int) -> str:
        """Apply an enhancement effect to a character's stats.

        Args:
            character: The character dictionary
            effect: The enhancement effect type
            amount: The amount to enhance by

        Returns:
            A message describing the effect
        """
        effect_map = {
            'enhance_agility': ('dexterity', 'agility'),
            'enhance_dexterity': ('dexterity', 'dexterity'),
            'enhance_strength': ('strength', 'strength'),
            'enhance_constitution': ('constitution', 'constitution'),
            'enhance_vitality': ('vitality', 'vitality'),
            'enhance_intelligence': ('intellect', 'intelligence'),
            'enhance_wisdom': ('wisdom', 'wisdom'),
            'enhance_charisma': ('charisma', 'charisma'),
            # Aliases for compatibility
            'enhance_physique': ('constitution', 'constitution'),
            'enhance_stamina': ('vitality', 'vitality')
        }

        if effect in effect_map:
            stat_key, stat_name = effect_map[effect]
            old_value = character.get(stat_key, 10)
            character[stat_key] = old_value + amount
            return f"Your {stat_name} increases by {amount}! ({old_value} -> {character[stat_key]})"
        elif effect == 'enhance_mental':
            # Enhance all mental stats (INT, WIS, CHA)
            int_old = character.get('intellect', 10)
            wis_old = character.get('wisdom', 10)
            cha_old = character.get('charisma', 10)
            character['intellect'] = int_old + amount
            character['wisdom'] = wis_old + amount
            character['charisma'] = cha_old + amount
            return f"Your mental faculties sharpen! INT +{amount}, WIS +{amount}, CHA +{amount}"
        elif effect == 'enhance_body':
            # Enhance all physical stats (STR, DEX, CON)
            str_old = character.get('strength', 10)
            dex_old = character.get('dexterity', 10)
            con_old = character.get('constitution', 10)
            character['strength'] = str_old + amount
            character['dexterity'] = dex_old + amount
            character['constitution'] = con_old + amount
            return f"Your body surges with power! STR +{amount}, DEX +{amount}, CON +{amount}"
        elif effect == 'ac_bonus':
            return f"A magical barrier surrounds you, increasing your armor class by {amount}!"
        elif effect == 'invisible':
            return "You fade from view, becoming invisible!"

        return f"You feel the power of the spell course through you!"

    def _roll_dice(self, dice_string: str) -> int:
        """Roll dice from a string like '2d6+3', '1d8', or '-1d5' (negative)."""
        import re

        # Handle negative dice notation (e.g., '-1d5') by stripping the leading minus
        # and making the result negative after rolling
        is_negative = dice_string.strip().startswith('-')
        if is_negative:
            dice_string = dice_string.strip()[1:]  # Remove the leading minus

        # Parse the dice string
        match = re.match(r'(\d+)d(\d+)([+-]\d+)?', dice_string.lower())
        if not match:
            return 0

        num_dice = int(match.group(1))
        die_size = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0

        # Roll the dice
        total = sum(random.randint(1, die_size) for _ in range(num_dice))
        result = total + modifier

        # Apply negative if original string was negative
        return -result if is_negative else result

    def _calculate_scaled_spell_value(self, base_value: int, spell: dict, caster_level: int) -> int:
        """Calculate scaled spell damage or healing based on caster level.

        Args:
            base_value: The base rolled damage or healing value
            spell: The spell data dictionary
            caster_level: The caster's character level

        Returns:
            The scaled value
        """
        scales_with_level = spell.get('scales_with_level', 'No')

        if scales_with_level not in ['Yes', 'yes', True]:
            return base_value

        # Multiplicative scaling: base damage × caster level
        # Example: Level 18 caster with 8 base damage = 8 × 18 = 144 damage
        scaled_value = base_value * caster_level

        return scaled_value

    def _calculate_player_spell_failure_chance(self, caster_level: int, caster_intelligence: int, spell_min_level: int) -> float:
        """Calculate the chance that a player's spell cast will fail.

        Args:
            caster_level: Level of the caster
            caster_intelligence: Intelligence stat of the caster
            spell_min_level: Minimum level required for the spell

        Returns:
            Float between 0.0 and 0.50 representing failure chance (0.10 = 10% chance to fail)
        """
        # Base failure rate: 5%
        base_failure = 0.05

        # Level difference penalty: +10% per level if spell is above caster's level
        level_penalty = 0.0
        if spell_min_level > caster_level:
            level_penalty = (spell_min_level - caster_level) * 0.10

        # Intelligence bonus: reduce failure based on intelligence modifier
        # D&D style: (stat - 10) / 2 = modifier
        intelligence_modifier = (caster_intelligence - 10) / 2
        intelligence_bonus = intelligence_modifier * 0.01  # 1% per modifier point

        # Calculate final failure chance
        failure_chance = base_failure + level_penalty - intelligence_bonus

        # Clamp between 0% and 50% (players are generally more skilled than mobs)
        failure_chance = max(0.0, min(0.50, failure_chance))

        return failure_chance

    def _is_spell_fatigued(self, player_id: int) -> bool:
        """Check if a player is currently spell fatigued."""
        if player_id not in self.game_engine.spell_fatigue:
            return False

        fatigue_info = self.game_engine.spell_fatigue[player_id]
        current_time = time.time()

        if 'fatigue_end_time' not in fatigue_info:
            del self.game_engine.spell_fatigue[player_id]
            return False

        if fatigue_info['fatigue_end_time'] == 0:
            return False

        if current_time >= fatigue_info['fatigue_end_time']:
            del self.game_engine.spell_fatigue[player_id]
            return False

        return True

    def _get_spell_fatigue_remaining(self, player_id: int) -> float:
        """Get remaining spell fatigue time in seconds."""
        if player_id not in self.game_engine.spell_fatigue:
            return 0.0

        fatigue_info = self.game_engine.spell_fatigue[player_id]
        if 'fatigue_end_time' not in fatigue_info:
            return 0.0

        current_time = time.time()
        remaining = fatigue_info['fatigue_end_time'] - current_time
        return max(0.0, remaining)

    def _apply_spell_fatigue(self, player_id: int, multiplier: float = 1.0):
        """Apply spell fatigue to a player.

        Args:
            player_id: The player ID
            multiplier: Fatigue duration multiplier (base 10 seconds * multiplier)
        """
        base_duration = 10.0  # Base fatigue duration in seconds
        duration = base_duration * multiplier

        self.game_engine.spell_fatigue[player_id] = {
            'fatigue_end_time': time.time() + duration
        }

    async def _cast_summon_spell(self, player_id: int, character: dict, spell: dict, room_id: str, target_name: str = None):
        """Cast a summoning spell to conjure a creature ally.

        Args:
            player_id: The caster's player ID
            character: The caster's character data
            spell: The spell definition
            room_id: The room where the spell is cast
            target_name: Should be None (summon spells don't target)
        """
        from ...utils.colors import spell_cast
        import copy

        # Get summon level range from spell
        # If spell scales with level, calculate range based on caster level
        if spell.get('scales_summon_with_level', False):
            caster_level = character.get('level', 1)
            # Calculate summon level range: 1 to (caster_level + 1) // 2
            # E.g., level 1 = 1-1, level 6 = 1-3, level 12 = 1-6, level 18 = 1-9
            # This ensures low-level necromancers can always summon, while high-level
            # necromancers have access to more powerful undead
            min_summon_level = 1
            max_summon_level = max(1, (caster_level + 1) // 2)
        else:
            min_summon_level = spell.get('min_summon_level', 1)
            max_summon_level = spell.get('max_summon_level', 1)

        allow_special_terrain = spell.get('allow_special_terrain', False)
        summon_type = spell.get('summon_type', None)  # e.g., "undead", "beast", etc.

        # Find all eligible mobs to summon
        eligible_mobs = []

        # Search through all monsters data (flat dict of mob_id -> mob_data)
        monsters_data = self.game_engine.monsters_data

        for mob_id, mob_template in monsters_data.items():
            mob_level = mob_template.get('level', 1)

            # Check level range
            if mob_level < min_summon_level or mob_level > max_summon_level:
                continue

            # Filter by mob type if specified (e.g., "undead" for necromancer)
            if summon_type:
                mob_type = mob_template.get('type', '')
                if mob_type != summon_type:
                    continue

            # Exclude SPECIAL terrain mobs (only summon natural creatures)
            # Unless the spell explicitly allows special terrain (like kusamuda)
            if not allow_special_terrain:
                terrain = mob_template.get('terrain', {})
                terrain_name = terrain.get('name', '') if isinstance(terrain, dict) else ''
                if terrain_name == 'Special':
                    continue

            eligible_mobs.append(mob_template)

        if not eligible_mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The summoning spell fails - no creatures answer your call!")
            )
            type_filter = f", type={summon_type}" if summon_type else ""
            self.game_engine.logger.error(f"No eligible mobs found for summon spell {spell.get('name')} (levels {min_summon_level}-{max_summon_level}{type_filter})")
            return

        # Randomly select a mob from eligible list
        mob_template = random.choice(eligible_mobs)

        # Clone the mob template to create a new instance
        summoned_mob = copy.deepcopy(mob_template)

        # Mark it as summoned and set owner
        summoned_mob['is_summoned'] = True
        summoned_mob['summoner_id'] = player_id
        summoned_mob['summoner_name'] = character.get('name', 'Unknown')

        # Summons are friendly, not hostile - they don't auto-attack players
        summoned_mob['type'] = 'friendly'
        summoned_mob['aggressive'] = False

        # Generate unique ID for this summon instance
        import time as time_module
        summon_id = f"{summoned_mob.get('id', 'summon')}_{player_id}_{int(time_module.time() * 1000)}"
        summoned_mob['summon_instance_id'] = summon_id

        # Reset health to max
        summoned_mob['health'] = summoned_mob.get('max_health', 10)

        # Add to room (check if room has space)
        if room_id not in self.game_engine.room_mobs:
            self.game_engine.room_mobs[room_id] = []

        # Check room capacity (optional - let natural limits apply)
        room_mobs = self.game_engine.room_mobs[room_id]
        max_room_mobs = self.game_engine.config_manager.get_setting('world', 'max_room_mobs', default=50)

        if len(room_mobs) >= max_room_mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You intone {spell.get('name')}!")
            )
            await self.game_engine.player_manager.notify_room_except_player(
                room_id,
                player_id,
                f"{character.get('name', 'Someone')} just intoned {spell.get('description', 'a summoning spell')}!"
            )
            await self.game_engine.connection_manager.send_message(
                player_id,
                "The spell succeeds, but the room is too crowded for your summon to appear!"
            )
            return

        # Add summoned mob to room
        self.game_engine.room_mobs[room_id].append(summoned_mob)

        # Add summon to caster's party automatically
        party_leader_id = character.get('party_leader', player_id)

        # Get the party leader's character
        if party_leader_id == player_id:
            leader_char = character
        else:
            leader_player_data = self.game_engine.player_manager.connected_players.get(party_leader_id)
            leader_char = leader_player_data.get('character') if leader_player_data else None

        if leader_char:
            # Initialize party_members if needed
            if 'party_members' not in leader_char:
                leader_char['party_members'] = [party_leader_id]

            # Add summon to party (using negative ID to distinguish from players)
            # Summons get a special party ID based on their instance ID
            summon_party_id = f"summon_{summon_id}"
            summoned_mob['party_leader'] = party_leader_id
            summoned_mob['party_id'] = summon_party_id

            # Track summon in party (stored separately from player party members)
            if 'summoned_party_members' not in leader_char:
                leader_char['summoned_party_members'] = []
            leader_char['summoned_party_members'].append(summon_id)

        # Send success messages using cast_message and hit_message
        mob_name = summoned_mob.get('name', 'a creature')
        mob_prefix = "An" if mob_name[0].lower() in 'aeiou' else "A"

        # Get cast and hit messages from spell data, with fallbacks
        cast_msg = spell.get('cast_message', "{caster} intones a summoning spell!")
        hit_msg = spell.get('hit_message', "{mob_prefix} {mob_name} appears in a puff of reddish smoke!")

        # Caster sees cast message
        formatted_cast = cast_msg.replace('{caster}', 'You').replace('{spell}', spell.get('name', 'a summoning spell'))
        await self.game_engine.connection_manager.send_message(
            player_id,
            spell_cast(formatted_cast, spell_type='summon')
        )

        # Room sees cast message (not including caster)
        room_cast = cast_msg.replace('{caster}', character.get('name', 'Someone')).replace('{spell}', spell.get('name', 'a summoning spell'))
        await self.game_engine.player_manager.notify_room_except_player(
            room_id,
            player_id,
            success_message(room_cast)
        )

        # Everyone sees hit message (the summon appearing)
        formatted_hit = hit_msg.replace('{mob_prefix}', mob_prefix).replace('{mob_name}', mob_name)
        await self.game_engine._notify_room_players_sync(
            room_id,
            colorize(formatted_hit, Colors.BOLD_RED)
        )

        self.game_engine.logger.info(f"[SUMMON] Player {player_id} ({character.get('name')}) summoned {mob_name} (level {summoned_mob.get('level')}) in room {room_id}")
