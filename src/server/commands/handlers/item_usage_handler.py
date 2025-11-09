"""
Item Usage Command Handler

Handles commands for consuming and using items:
- eat - Consume food to restore hunger
- drink - Consume drinks/potions to restore thirst or gain effects
- light - Light torches, lanterns, candles
- extinguish - Extinguish lit light sources
- fill - Fill lanterns with lamp oil
- read - Read spell scrolls to learn spells
"""

from ..base_handler import BaseCommandHandler
from ...utils.colors import error_message, success_message, announcement, info_message


class ItemUsageCommandHandler(BaseCommandHandler):
    """Handler for item usage commands."""

    async def handle_eat_command(self, player_id: int, item_name: str):
        """Handle eating food to restore hunger."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find food item
        item_to_eat, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just eat the first one
            pass  # item_to_eat and item_index are already set to the first match

        # Check if item is food
        item_type = item_to_eat.get('type', '')
        if item_type != 'food':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't eat {item_to_eat['name']}!")
            )
            return

        # Get nutrition value (default 30 if not specified)
        nutrition = item_to_eat.get('nutrition', 30)

        # Restore hunger
        current_hunger = character.get('hunger', 100)
        new_hunger = min(100, current_hunger + nutrition)
        character['hunger'] = new_hunger

        # Decrement quantity or remove item from inventory
        current_quantity = item_to_eat.get('quantity', 1)
        if current_quantity > 1:
            # Decrement quantity
            item_to_eat['quantity'] = current_quantity - 1
        else:
            # Remove item entirely if it's the last one
            character['inventory'].pop(item_index)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"You eat {item_to_eat['name']}. Your hunger is restored. (Hunger: {new_hunger:.0f}/100)"
        )

    async def handle_drink_command(self, player_id: int, item_name: str):
        """Handle drinking to restore thirst or consume potions."""
        import re

        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find drink item
        item_to_drink, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just drink the first one
            pass  # item_to_drink and item_index are already set to the first match

        # Check if item is a drink or consumable
        item_type = item_to_drink.get('type', '')
        if item_type not in ['drink', 'potion', 'consumable']:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't drink {item_to_drink['name']}!")
            )
            return

        # Initialize messages list
        messages = []
        messages.append(f"You drink {item_to_drink['name']}.")

        # Get item properties
        properties = item_to_drink.get('properties', {})

        # Handle health restoration
        if 'restore_health' in properties:
            restore_health = properties['restore_health']

            # Parse health value (can be integer or dice notation like "4-16")
            if isinstance(restore_health, str):
                # Handle range notation like "4-16" or "32-128"
                if '-' in restore_health:
                    min_val, max_val = map(int, restore_health.split('-'))
                    import random
                    health_amount = random.randint(min_val, max_val)
                else:
                    health_amount = int(restore_health)
            else:
                health_amount = int(restore_health)

            current_health = character.get('current_hit_points', 0)
            max_health = character.get('max_hit_points', 100)
            new_health = min(max_health, current_health + health_amount)

            character['current_hit_points'] = new_health

            messages.append(f"You restore {health_amount} health! (HP: {new_health}/{max_health})")

        # Handle mana restoration
        if 'restore_mana' in properties:
            restore_mana = properties['restore_mana']
            mana_amount = int(restore_mana)

            current_mana = character.get('current_mana', character.get('current_mana', 0))
            max_mana = character.get('max_mana', 50)
            new_mana = min(max_mana, current_mana + mana_amount)

            character['current_mana'] = new_mana
            character['current_mana'] = new_mana

            messages.append(f"You restore {mana_amount} mana! (Mana: {new_mana}/{max_mana})")

        # Handle cure poison
        if properties.get('cure_poison'):
            # Initialize active_effects if needed
            if 'active_effects' not in character:
                character['active_effects'] = []

            # Remove poison effects
            original_count = len(character['active_effects'])
            character['active_effects'] = [
                effect for effect in character['active_effects']
                if effect.get('effect') != 'poison'
            ]

            if len(character['active_effects']) < original_count:
                messages.append("The poison leaves your body!")
            else:
                messages.append("You feel cleansed, though you weren't poisoned.")

        # Handle stat boost potions
        boost_duration = properties.get('boost_duration', 0)
        if boost_duration > 0:
            # Initialize active_effects if needed
            if 'active_effects' not in character:
                character['active_effects'] = []

            # Strength boost
            if 'strength_bonus' in properties:
                str_bonus = properties['strength_bonus']
                buff = {
                    'spell_id': item_to_drink.get('name', 'Strength Potion'),
                    'effect': 'strength_bonus',
                    'duration': boost_duration,
                    'bonus_amount': str_bonus
                }
                character['active_effects'].append(buff)
                messages.append(f"You feel stronger! (+{str_bonus} STR for {boost_duration} rounds)")

            # Dexterity boost
            if 'dexterity_bonus' in properties:
                dex_bonus = properties['dexterity_bonus']
                buff = {
                    'spell_id': item_to_drink.get('name', 'Dexterity Potion'),
                    'effect': 'dexterity_bonus',
                    'duration': boost_duration,
                    'bonus_amount': dex_bonus
                }
                character['active_effects'].append(buff)
                messages.append(f"You feel more agile! (+{dex_bonus} DEX for {boost_duration} rounds)")

        # Handle invisibility
        if 'invisibility_duration' in properties:
            invis_duration = properties['invisibility_duration']

            # Initialize active_effects if needed
            if 'active_effects' not in character:
                character['active_effects'] = []

            buff = {
                'spell_id': item_to_drink.get('name', 'Invisibility Potion'),
                'effect': 'invisibility',
                'duration': invis_duration,
                'bonus_amount': 1
            }
            character['active_effects'].append(buff)
            messages.append(f"You fade from view! (Invisible for {invis_duration} rounds)")

        # Handle hydration (for drinks)
        hydration = item_to_drink.get('hydration', 0)
        if hydration > 0:
            current_thirst = character.get('thirst', 100)
            new_thirst = min(100, current_thirst + hydration)
            character['thirst'] = new_thirst
            messages.append(f"Your thirst is quenched. (Thirst: {new_thirst:.0f}/100)")

        # Decrement quantity or remove item from inventory
        current_quantity = item_to_drink.get('quantity', 1)
        if current_quantity > 1:
            # Decrement quantity
            item_to_drink['quantity'] = current_quantity - 1
        else:
            # Remove item entirely if it's the last one
            character['inventory'].pop(item_index)

        # Send all messages
        await self.game_engine.connection_manager.send_message(
            player_id,
            "\n".join(messages)
        )

    async def handle_light_command(self, player_id: int, item_name: str):
        """Handle lighting a light source (torch, lantern, candle)."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find light source in inventory
        item_to_light, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
            )
            return

        # Check if item is a light source
        if not item_to_light.get('is_light_source', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't light {item_to_light['name']}.")
            )
            return

        # Check if already lit
        if item_to_light.get('is_lit', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_light['name']} is already lit!")
            )
            return

        # Check if it's depleted
        properties = item_to_light.get('properties', {})
        time_remaining = item_to_light.get('time_remaining', properties.get('max_duration', 0))

        if time_remaining <= 0:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_light['name']} has burned out and can't be lit.")
            )
            return

        # For lanterns, check if they need oil
        fuel_type = properties.get('fuel_type', 'none')
        if fuel_type == 'lamp_oil':
            fuel_charges = properties.get('fuel_charges', 0)
            if fuel_charges <= 0:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"The {item_to_light['name']} needs oil. Use 'fill lantern' with lamp oil in your inventory.")
                )
                return

        # Light the item
        item_to_light['is_lit'] = True
        if 'time_remaining' not in item_to_light:
            item_to_light['time_remaining'] = properties.get('max_duration', 600)

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You light the {item_to_light['name']}. It illuminates the area around you.")
        )

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(
                room_id, player_id,
                announcement(f"{username} lights a {item_to_light['name']}, casting light in the darkness.")
            )

    async def handle_extinguish_command(self, player_id: int, item_name: str):
        """Handle extinguishing a lit light source."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find light source in inventory
        item_to_extinguish, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
            )
            return

        # Check if item is a light source
        if not item_to_extinguish.get('is_light_source', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't extinguish {item_to_extinguish['name']}.")
            )
            return

        # Check if actually lit
        if not item_to_extinguish.get('is_lit', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_extinguish['name']} isn't lit.")
            )
            return

        # Extinguish the item
        item_to_extinguish['is_lit'] = False

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You extinguish the {item_to_extinguish['name']}. The light fades away.")
        )

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(
                room_id, player_id,
                f"{username} extinguishes their {item_to_extinguish['name']}, plunging the area into darkness."
            )

    async def handle_fill_command(self, player_id: int, item_name: str):
        """Handle filling a lantern with lamp oil."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find lantern to fill
        item_to_fill, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, use the first one
            pass  # item_to_fill and item_index are already set to the first match

        # Check if item is a light source that can be refilled
        if not item_to_fill.get('is_light_source', False):
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't fill {item_to_fill['name']}.")
            )
            return

        properties = item_to_fill.get('properties', {})
        fuel_type = properties.get('fuel_type', 'none')

        if fuel_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_fill['name']} doesn't need fuel.")
            )
            return

        if fuel_type != 'lamp_oil':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"The {item_to_fill['name']} requires {fuel_type}, which you don't have.")
            )
            return

        # Find lamp oil in inventory
        oil_item, oil_index, oil_match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, 'lamp_oil')

        if oil_match_type == 'none':
            # Try alternate names
            oil_item, oil_index, oil_match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, 'oil')

        if oil_match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have any lamp oil to fill it with.")
            )
            return

        # Check if the oil item is actually lamp oil
        if oil_item.get('id', '') != 'lamp_oil':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have any lamp oil to fill it with.")
            )
            return

        # Get fuel charges from the oil
        oil_properties = oil_item.get('properties', {})
        fuel_to_add = oil_properties.get('fuel_charges', 1800)

        # Add fuel to the lantern
        current_fuel = properties.get('fuel_charges', 0)
        max_duration = properties.get('max_duration', 1800)

        # Initialize properties dict if it doesn't exist
        if 'properties' not in item_to_fill:
            item_to_fill['properties'] = {}

        # Add fuel (cap at max_duration)
        new_fuel = min(current_fuel + fuel_to_add, max_duration)
        item_to_fill['properties']['fuel_charges'] = new_fuel

        # If the lantern was depleted, reset time_remaining
        if item_to_fill.get('time_remaining', 0) <= 0:
            item_to_fill['time_remaining'] = new_fuel
        else:
            # Add to existing time_remaining
            item_to_fill['time_remaining'] = min(item_to_fill.get('time_remaining', 0) + fuel_to_add, max_duration)

        # Reset warning flags
        item_to_fill['_warned_60'] = False
        item_to_fill['_warned_10'] = False

        # Decrement quantity or remove the oil flask from inventory
        current_quantity = oil_item.get('quantity', 1)
        if current_quantity > 1:
            # Decrement quantity
            oil_item['quantity'] = current_quantity - 1
        else:
            # Remove item entirely if it's the last one
            inventory.pop(oil_index)

        # Calculate time in minutes
        minutes = int(new_fuel // 60)

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You fill the {item_to_fill['name']} with lamp oil. It now has {minutes} minutes of fuel.")
        )

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine.player_manager.notify_room_except_player(
                room_id, player_id,
                f"{username} fills their {item_to_fill['name']} with lamp oil."
            )

    async def handle_read_command(self, player_id: int, item_name: str):
        """Handle reading a spell scroll to learn a spell."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find scroll item
        item_to_read, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just read the first one
            pass  # item_to_read and item_index are already set to the first match

        # Check if item is a spell scroll
        item_type = item_to_read.get('type', '')
        if item_type != 'spell_scroll':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't read {item_to_read['name']} to learn a spell!")
            )
            return

        # Get scroll properties
        properties = item_to_read.get('properties', {})
        spell_id = properties.get('spell_id')

        if not spell_id:
            await self.game_engine.connection_manager.send_message(player_id, f"This scroll doesn't contain a spell!")
            return

        # Check if player already knows the spell
        spellbook = character.get('spellbook', [])
        if spell_id in spellbook:
            await self.game_engine.connection_manager.send_message(player_id, f"You already know this spell!")
            return

        # Check requirements
        requirements = properties.get('requirements', {})
        min_level = requirements.get('min_level', 1)
        min_intelligence = requirements.get('min_intelligence', 0)

        player_level = character.get('level', 1)
        player_intelligence = character.get('intellect', 10)

        # Check level requirement
        if player_level < min_level:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You must be at least level {min_level} to learn this spell! (You are level {player_level})"
            )
            return

        # Check intelligence requirement
        if player_intelligence < min_intelligence:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You need at least {min_intelligence} Intelligence to learn this spell! (You have {player_intelligence})"
            )
            return

        # Get spell data to check class restrictions
        spell_data = self.game_engine.config_manager.game_data.get('spells', {})
        spell = spell_data.get(spell_id, {})

        if not spell:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Error: Spell data not found for {spell_id}!"
            )
            return

        # Check class restriction
        player_class = character.get('class', '').lower()
        spell_class_restriction = spell.get('class_restriction', '').lower()

        if spell_class_restriction and spell_class_restriction != player_class:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Only {spell_class_restriction}s can learn {spell.get('name', spell_id)}!"
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
                f"As a {character.get('class', 'adventurer')}, you can only learn spells up to level {max_spell_level}. {spell.get('name', spell_id)} is level {spell_level}."
            )
            return

        # Learn the spell!
        if 'spellbook' not in character:
            character['spellbook'] = []

        character['spellbook'].append(spell_id)

        # Remove scroll from inventory
        character['inventory'].pop(item_index)

        # Send success message (spell data already loaded above)
        spell_name = spell.get('name', spell_id)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"You carefully study the scroll and learn the spell: {spell_name}!"
        )
