"""
World Command Handler

Handles commands for world interaction and observation:
- look - Look at room, directions, or targets
- Special actions - Room-specific actions (gaze mirror, etc.)
- ring - Ring special items like gongs to spawn arena encounters
- buy passage - Travel across the great lake between docks
- rent/rest/sleep - Rent rooms at inns to restore HP/mana
"""

from ..base_handler import BaseCommandHandler
from ...utils.colors import error_message, service_message, info_message, success_message


class WorldCommandHandler(BaseCommandHandler):
    """Handler for world interaction commands."""

    async def handle_look_command(self, player_id: int, params: str):
        """Handle look command - check if it's a direction or a target."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        current_room = character['room_id']

        # Map short directions to full names
        direction_map = {
            'n': 'north', 's': 'south', 'e': 'east', 'w': 'west',
            'ne': 'northeast', 'nw': 'northwest',
            'se': 'southeast', 'sw': 'southwest',
            'u': 'up', 'd': 'down'
        }

        # Normalize the direction
        target_lower = params.lower().strip()
        full_direction = direction_map.get(target_lower, target_lower)

        # Get available exits
        exits = self.game_engine.world_manager.get_exits_from_room(current_room, character)

        # Check if the params matches a direction
        if full_direction in exits:
            # It's a valid direction - show the adjacent room
            destination_room_id = exits[full_direction]

            # Send message about looking in that direction
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You look {full_direction}...\n"
            )

            # Show the room description for that direction
            await self.game_engine.world_manager.send_room_description_for_room(
                player_id,
                destination_room_id,
                character.get('id', player_id),
                detailed=True
            )
            return

        # Not a direction, treat as a target (NPC, mob, item, etc.)
        await self.handle_look_at_target(player_id, params)

    async def handle_look_at_target(self, player_id: int, target_name: str):
        """Handle looking at a specific target."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # First check if it's a player in the room
        target_lower = target_name.lower()
        for other_player_id, other_player_data in self.game_engine.player_manager.get_all_connected_players().items():
            if other_player_id == player_id:
                continue
            other_character = other_player_data.get('character')
            if other_character and other_character.get('room_id') == room_id:
                other_name = other_character.get('name', '').lower()
                if target_lower in other_name or other_name in target_lower:
                    # Check if the target player is invisible
                    active_effects = other_character.get('active_effects', [])
                    is_invisible = any(
                        effect.get('effect') in ['invisible', 'invisibility']
                        for effect in active_effects
                    )
                    if is_invisible:
                        # Can't see invisible players
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            error_message("You don't see that here.")
                        )
                        return
                    # Found a visible player - generate detailed description
                    description = self.generate_player_description(other_character)
                    await self.game_engine.connection_manager.send_message(player_id, description)
                    await self.game_engine.connection_manager.send_message(other_player_id, f"{character['name']} looks at you.")
                    return

        # Check for items on the floor
        room_items = self.game_engine.item_manager.get_room_items(room_id)
        for item in room_items:
            if target_lower in item['name'].lower():
                description = item.get('description', f"A {item['name'].lower()}.")
                await self.game_engine.connection_manager.send_message(player_id, f"You examine the {item['name']}: {description}")
                return

        # Check for mobs
        if room_id in self.game_engine.room_mobs:
            for mob in self.game_engine.room_mobs[room_id]:
                if target_lower in mob['name'].lower():
                    description = mob.get('description', f"A {mob['name'].lower()}.")
                    health_status = ""

                    # Get current and max health (mobs use 'health' and 'max_health')
                    current_health = mob.get('health', mob.get('current_hit_points', 100))
                    max_health = mob.get('max_health', mob.get('max_hit_points', 100))

                    # Show health status if mob is damaged
                    if current_health < max_health:
                        health_percent = (current_health / max_health) * 100
                        if health_percent > 75:
                            health_status = " It looks slightly wounded."
                        elif health_percent > 50:
                            health_status = " It looks moderately wounded."
                        elif health_percent > 25:
                            health_status = " It looks badly wounded."
                        else:
                            health_status = " It looks near death."

                    await self.game_engine.connection_manager.send_message(player_id, f"You look at the {mob['name']}: {description}{health_status}")
                    return

        # Check for NPCs
        room = self.game_engine.world_manager.get_room(room_id)
        if room and room.npcs:
            for npc in room.npcs:
                if target_lower in npc.name.lower() or target_lower in npc.npc_id.lower():
                    description = npc.description
                    await self.game_engine.connection_manager.send_message(player_id, f"You look at {npc.name}: {description}")
                    return

        # Check for vendors
        vendors = self.game_engine.vendor_system.get_vendors_in_room(room_id)
        for vendor in vendors:
            if target_lower in vendor['name'].lower():
                description = vendor.get('description', f"A merchant named {vendor['name']}.")
                await self.game_engine.connection_manager.send_message(player_id, f"You look at {vendor['name']}: {description}")
                return

        # Check player's inventory
        inventory = character.get('inventory', [])
        for item in inventory:
            if target_lower in item['name'].lower():
                description = item.get('description', f"A {item['name'].lower()}.")
                await self.game_engine.connection_manager.send_message(player_id, f"You examine your {item['name']}: {description}")
                return

        # Nothing found
        await self.game_engine.connection_manager.send_message(
            player_id,
            error_message(f"You don't see {target_name} here.")
        )

    async def handle_special_action(self, player_id: int, command: str, params: str):
        """Handle special room actions like 'gaze mirror'."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Get room data
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            return

        # Check if room has special_actions defined
        room_data = self.game_engine.world_manager.rooms_data.get(room_id, {})
        special_actions = room_data.get('special_actions', {})

        # Build the full action string
        action_key = f"{command} {params}".strip()

        if action_key in special_actions:
            action_data = special_actions[action_key]
            action_type = action_data.get('type')
            action_message = action_data.get('message', '')

            if action_type == 'self_inspect':
                # Show the action message first
                if action_message:
                    await self.game_engine.connection_manager.send_message(player_id, action_message)

                # Generate and send player's own description
                description = self.generate_player_description(character)
                await self.game_engine.connection_manager.send_message(player_id, description)
            else:
                # Generic action - just show the message
                if action_message:
                    await self.game_engine.connection_manager.send_message(player_id, action_message)
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't {command} {params} here.")
            )

    def generate_player_description(self, character: dict) -> str:
        """Generate a detailed description of a player based on their stats, class, race, and equipment."""
        name = character.get('name', 'Someone')

        # Get stats with effective bonuses
        from ...game.combat.combat_system import CombatSystem
        charisma = CombatSystem.get_effective_stat(character, 'charisma', 10)
        strength = CombatSystem.get_effective_stat(character, 'strength', 10)
        intelligence = CombatSystem.get_effective_stat(character, 'intelligence', 10)
        wisdom = CombatSystem.get_effective_stat(character, 'wisdom', 10)
        dexterity = CombatSystem.get_effective_stat(character, 'dexterity', 10)

        # Get species (race) and class
        race = character.get('species', character.get('race', 'human')).capitalize()
        char_class = character.get('class', 'fighter').capitalize()

        # Build description starting with name and charisma
        msg = f"{name} is a "

        # Charisma description
        if charisma >= 20:
            msg += "stunningly attractive"
        elif charisma >= 10:
            msg += "somewhat attractive"
        else:
            msg += "rather plain looking"

        # Strength + race + class
        if strength >= 20:
            msg += f" and powerfully built {race} {char_class}"
        elif strength >= 10:
            msg += f" and moderately built {race} {char_class}"
        else:
            msg += f" and slightly built {race} {char_class}"

        # Wisdom
        if wisdom >= 20:
            msg += ", with a worldly air about them"
        elif wisdom < 10:
            msg += ", with an inexperienced look about them"
        else:
            msg += ""

        msg += "."

        # Dexterity
        if dexterity >= 20:
            msg += " You notice that their movements are very quick and agile."
        elif dexterity < 10:
            msg += " You notice that their movements are rather slow and clumsy."

        # Intelligence
        if intelligence >= 20:
            msg += " They have a bright look in their eyes."
        elif intelligence < 10:
            msg += " They have a dull look in their eyes."

        # Equipment
        equipped = character.get('equipped', {})
        weapon = equipped.get('weapon')
        armor = equipped.get('armor')

        weapon_name = weapon.get('name', 'their fists') if weapon else 'their fists'
        armor_name = armor.get('name', 'plain clothes') if armor else 'plain clothes'

        msg += f" They are wearing {armor_name} and are armed with {weapon_name}."

        # Health status
        health = character.get('current_hit_points', character.get('max_health', 100))
        max_health = character.get('max_health', 100)
        health_percent = int((health / max_health) * 100)

        if health_percent < 25:
            msg += " They are sorely wounded."
        elif health_percent < 50:
            msg += " They seem to be moderately wounded."
        elif health_percent < 75:
            msg += " They appear to be wounded."
        elif health_percent < 100:
            msg += " They look as if they are lightly wounded."
        else:
            msg += " They seem to be in good physical condition."

        # Add rune description (only if player has a rune)
        rune = character.get('rune', '')
        if rune and rune not in [None, 'None', '']:
            rune_str = str(rune).strip()
            if rune_str:
                msg += f" You also notice a distinctive {rune_str.title()} rune inscribed on their forehead."

        return msg

    async def handle_ring_command(self, player_id: int, target: str):
        """Handle ring command for special items like gongs."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Check if the target matches "gong" or similar variations
        target_lower = target.lower()
        if target_lower in ['gong', 'g', 'bronze gong', 'bronze']:
            # Check if player is in an arena room (configured in game settings)
            arena_config = self.game_engine.config_manager.get_arena_by_room(room_id)
            if not arena_config:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("There is no gong here to ring.")
                )
                return

            # Ring the gong and spawn a mob (delegates to world_manager)
            await self.game_engine.world_manager.handle_ring_gong(player_id, room_id)
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You cannot ring {target}.")
            )

    async def handle_buy_passage(self, player_id: int, character: dict):
        """Handle buying passage across the great lake between docks.

        Requirements:
        1. Player must have a rune (not 'None')
        2. Player must have enough gold (configurable cost)
        3. Player must be at valid dock location (mhv_docks or lht_docks)

        Events during voyage:
        - Rats may eat food (configurable chance)
        - Player may be robbed (configurable chance, random gold amount)
        """
        room_id = character.get('room_id')

        # Define dock locations and their destinations
        dock_routes = {
            'mhv_docks': 'lht_docks',  # Main human village docks -> Lakeside human town docks
            'lht_docks': 'mhv_docks'   # Lakeside human town docks -> Main human village docks
        }

        # Check if player is at a valid dock
        if room_id not in dock_routes:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You can only buy passage from the docks."
            )
            return

        # Check if player has a rune
        rune = character.get('rune', 'None')
        if not rune or rune == 'None' or rune == '' or str(rune).lower() == 'none':
            await self.game_engine.connection_manager.send_message(
                player_id,
                "Sorry, by decree of the guild masters, no one shall venture across the great lake who does not bear a rune upon their brow."
            )
            return

        # Get configuration settings
        cost = self.game_engine.config_manager.get_setting('ship_passage', 'cost', default=100)
        rat_chance = self.game_engine.config_manager.get_setting('ship_passage', 'rat_event_chance', default=0.15)
        robbery_chance = self.game_engine.config_manager.get_setting('ship_passage', 'robbery_event_chance', default=0.10)
        robbery_min = self.game_engine.config_manager.get_setting('ship_passage', 'robbery_gold_min', default=10)
        robbery_max = self.game_engine.config_manager.get_setting('ship_passage', 'robbery_gold_max', default=50)

        # Check if player has enough gold
        player_gold = character.get('gold', 0)
        if player_gold < cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"Sorry, you cannot afford passage across the great lake! (Cost: {cost} gold, You have: {player_gold} gold)"
            )
            return

        # Deduct gold
        character['gold'] -= cost

        # Notify player and others in departure room
        player_name = character.get('name', 'Someone')
        await self.game_engine.connection_manager.send_message(
            player_id,
            "You buy passage across the great lake and board a ship..."
        )
        await self.game_engine._notify_room_except_player(
            room_id,
            player_id,
            f"{player_name} hands a small purse of coins to a ship's captain and boards a ship..."
        )

        # Random events during voyage
        import random

        # Rat event - eats food
        if random.random() < rat_chance:
            # Find a food item in inventory
            inventory = character.get('inventory', [])
            food_items = [item for item in inventory if item.get('type') == 'food']

            if food_items:
                # Remove a random food item
                food_to_remove = random.choice(food_items)
                inventory.remove(food_to_remove)
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"While aboard the ship your {food_to_remove.get('name', 'food')} was eaten by rats!"
                )

        # Robbery event - steal gold
        if random.random() < robbery_chance:
            # Calculate random amount to steal (but don't steal more than player has)
            max_steal = min(character.get('gold', 0), robbery_max)
            if max_steal >= robbery_min:
                stolen_amount = random.randint(robbery_min, max_steal)
                character['gold'] -= stolen_amount
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"While aboard the ship you seem to have been robbed! (Lost {stolen_amount} gold)"
                )

        # Teleport to destination
        destination_room_id = dock_routes[room_id]
        character['room_id'] = destination_room_id

        # Notify players at destination
        await self.game_engine._notify_room_except_player(
            destination_room_id,
            player_id,
            f"{player_name} has just arrived on a ship from across the great lake."
        )

        # Show room description to player
        await self.game_engine.world_manager.send_room_description(player_id, detailed=True)

    async def handle_rent_room(self, player_id: int, character: dict):
        """Handle renting a room at an inn to restore HP and mana."""
        room_id = character.get('room_id')

        # Get room object
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            await self.game_engine.connection_manager.send_message(player_id, "You are nowhere!")
            return

        # Get NPCs in the room
        npcs_in_room = room.npcs if hasattr(room, 'npcs') else []

        # Find an innkeeper NPC
        innkeeper_npc = None
        innkeeper_obj = None
        for npc_obj in npcs_in_room:
            # Get NPC data from world manager using the NPC object's ID
            npc_data = self.game_engine.world_manager.get_npc_data(npc_obj.npc_id)
            if npc_data:
                # Check if NPC has innkeeper in services or is type innkeeper
                if 'innkeeper' in npc_data.get('services', []) or 'rooms' in npc_data.get('services', []):
                    innkeeper_npc = npc_data
                    innkeeper_obj = npc_obj
                    break

        if not innkeeper_npc:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "There is no innkeeper here. You must find an inn to rent a room."
            )
            return

        # Calculate room cost based on player level (base 10 gold + 5 gold per level)
        player_level = character.get('level', 1)
        room_cost = 10 + (player_level * 5)

        # Check if player has enough gold
        player_gold = character.get('gold', 0)
        if player_gold < room_cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't have enough gold to rent a room. A room costs {room_cost} gold, but you only have {player_gold} gold."
            )
            return

        # Check if player needs rest
        current_health = character.get('current_hit_points', 0)
        max_health = character.get('max_hit_points', current_health)
        current_mana = character.get('current_mana', character.get('current_mana', 0))
        max_mana = character.get('max_mana', current_mana)

        if current_health >= max_health and current_mana >= max_mana:
            # Get already rested message from NPC dialogue
            dialogue = innkeeper_npc.get('dialogue', {})
            already_rested_msg = dialogue.get('rent_already_rested', "You look well-rested already! Perhaps come back when you're weary.")
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"{innkeeper_obj.name} says: \"{already_rested_msg}\""
            )
            return

        # Restore HP and mana to full
        health_restored = max_health - current_health
        mana_restored = max_mana - current_mana

        character['current_hit_points'] = max_health
        character['current_mana'] = max_mana
        character['current_mana'] = max_mana  # For backward compatibility

        # Deduct gold
        character['gold'] = player_gold - room_cost

        # Get dialogue from NPC data
        dialogue = innkeeper_npc.get('dialogue', {})
        rent_accept = dialogue.get('rent_accept', "Wonderful! Let me show you to your room.")
        rent_description = dialogue.get('rent_description', "You follow the innkeeper up a creaky wooden staircase to a cozy room with a soft bed and a washbasin. The sheets are clean and the pillows are plump. You rest deeply through the night...")

        # Send atmospheric message
        message = f"{innkeeper_obj.name} says: \"{rent_accept}\"\n\n"
        message += f"{rent_description}\n\n"

        if health_restored > 0:
            message += f"You wake feeling refreshed and healed! (+{int(health_restored)} HP)\n"
        if mana_restored > 0:
            message += f"Your magical energy has been fully restored! (+{int(mana_restored)} Mana)\n"

        message += f"\nYou paid {room_cost} gold for the room.\n"
        message += f"Health: {int(character['current_hit_points'])} / {int(max_health)}\n"
        message += f"Mana: {int(character['current_mana'])} / {int(max_mana)}\n"
        message += f"Gold: {int(character['gold'])}"

        await self.game_engine.connection_manager.send_message(player_id, service_message(message))

    async def handle_search_traps_command(self, player_id: int, character: dict):
        """Handle searching for traps in current room."""
        # Check if player is a rogue
        player_class = character.get('class', '').lower()
        if player_class != 'rogue':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Only rogues have the skills to search for traps.")
            )
            return

        room_id = character.get('room_id')
        if not room_id:
            return

        result = self.game_engine.trap_system.search_for_traps(player_id, room_id)

        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message(result)
        )

        # Notify others in the room
        username = self.game_engine.player_manager.get_player_data(player_id).get('username', 'Someone')
        await self.game_engine.player_manager.notify_room_except_player(
            room_id, player_id,
            f"{username} carefully searches the area for traps."
        )

    async def handle_disarm_trap_command(self, player_id: int, character: dict):
        """Handle disarming a detected trap."""
        # Check if player is a rogue
        player_class = character.get('class', '').lower()
        if player_class != 'rogue':
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Only rogues have the skills to disarm traps.")
            )
            return

        room_id = character.get('room_id')
        if not room_id:
            return

        # Disarm the first detected trap
        result = self.game_engine.trap_system.disarm_trap(player_id, room_id, 0)

        # Determine message type based on result
        if "successfully" in result:
            msg = success_message(result)
        elif "fumble" in result or "trigger" in result:
            msg = error_message(result)
        else:
            msg = info_message(result)

        await self.game_engine.connection_manager.send_message(player_id, msg)

        # Notify others in the room on success
        if "successfully" in result:
            username = self.game_engine.player_manager.get_player_data(player_id).get('username', 'Someone')
            await self.game_engine.player_manager.notify_room_except_player(
                room_id, player_id,
                f"{username} carefully disarms a trap."
            )
