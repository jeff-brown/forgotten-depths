"""Admin command handler for debug and testing commands."""

import uuid
from ...utils.colors import error_message
from ..base_handler import BaseCommandHandler


class AdminCommandHandler(BaseCommandHandler):
    """Handles admin/debug commands."""

    async def _handle_admin_give_gold(self, player_id: int, character: dict, params: str):
        """Admin command to give gold to the current player."""
        try:
            amount = int(params.strip())
            if amount <= 0:
                await self.game_engine.connection_manager.send_message(player_id, "Amount must be positive.")
                return

            # Add gold to character
            current_gold = character.get('gold', 0)
            character['gold'] = current_gold + amount

            # Update encumbrance for gold weight change
            self.game_engine.player_manager.update_encumbrance(character)

            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Added {amount} gold. You now have {character['gold']} gold."
            )

        except ValueError:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Invalid amount. Usage: givegold <amount>")
            )

    async def _handle_admin_give_item(self, player_id: int, character: dict, params: str):
        """Admin command to give an item to the current player."""
        item_id = params.strip().lower()

        # Load items from all JSON files in data/items/
        items = self.game_engine.config_manager.load_items()
        if not items:
            await self.game_engine.connection_manager.send_message(player_id, "[ADMIN] No items found in data/items/")
            return

        # Find the item
        if item_id not in items:
            await self.game_engine.connection_manager.send_message(player_id, f"[ADMIN] Item '{item_id}' not found. Available items: {', '.join(list(items.keys())[:10])}...")
            return

        item_config = items[item_id]

        # Create item instance
        import uuid
        item_instance = {
            'id': str(uuid.uuid4()),
            'item_id': item_id,
            'name': item_config.get('name', item_id),
            'type': item_config.get('type', 'misc'),
            'weight': item_config.get('weight', 0),
        }

        # Add item-specific properties
        if 'damage' in item_config:
            item_instance['damage'] = item_config['damage']
        if 'armor_class' in item_config:
            item_instance['armor_class'] = item_config['armor_class']
        if 'properties' in item_config:
            item_instance['properties'] = item_config['properties']

        # Check encumbrance
        current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
        max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)
        item_weight = item_instance.get('weight', 0)

        if current_encumbrance + item_weight > max_encumbrance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Cannot add item: would exceed max encumbrance ({max_encumbrance})."
            )
            return

        # Add to inventory
        if 'inventory' not in character:
            character['inventory'] = []
        character['inventory'].append(item_instance)

        # Update encumbrance
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Added {item_instance['name']} to your inventory."
        )

    async def _handle_admin_give_xp(self, player_id: int, character: dict, params: str):
        """Admin command to give experience to the current player."""
        try:
            amount = int(params.strip())
            if amount <= 0:
                await self.game_engine.connection_manager.send_message(player_id, "Amount must be positive.")
                return

            # Add experience
            current_xp = character.get('experience', 0)
            character['experience'] = current_xp + amount

            # Check for level up
            current_level = character.get('level', 1)
            xp_for_next = self.calculate_xp_for_level(current_level + 1)

            if character['experience'] >= xp_for_next:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"[ADMIN] Added {amount} XP. You now have {character['experience']} XP.\nYou have enough XP to level up! Find a trainer and use 'train' command."
                )
            else:
                xp_remaining = xp_for_next - character['experience']
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"[ADMIN] Added {amount} XP. You now have {character['experience']} XP. ({xp_remaining} XP until level {current_level + 1})"
                )

        except ValueError:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Invalid amount. Usage: givexp <amount>")
            )

    async def _handle_admin_mob_status(self, player_id: int):
        """Admin command to show all mobs and their status."""
        total_mobs = 0
        wandering_count = 0
        lair_count = 0
        gong_count = 0
        other_count = 0

        status_msg = "[ADMIN] Mob Status Report\n" + "=" * 50 + "\n\n"

        for room_id, mobs in self.game_engine.room_mobs.items():
            if not mobs:
                continue

            room_mob_count = len([m for m in mobs if m is not None])
            if room_mob_count == 0:
                continue

            status_msg += f"Room: {room_id} ({room_mob_count} mobs)\n"

            for mob in mobs:
                if mob is None:
                    continue

                total_mobs += 1
                mob_name = mob.get('name', 'Unknown')
                mob_hp = mob.get('current_hit_points', 0)
                mob_max_hp = mob.get('max_health', 0)
                mob_level = mob.get('level', 1)

                flags = []
                if mob.get('is_wandering'):
                    flags.append('WANDERING')
                    wandering_count += 1
                elif mob.get('is_lair_mob'):
                    flags.append('LAIR')
                    lair_count += 1
                elif mob.get('spawned_by_gong'):
                    flags.append('GONG')
                    gong_count += 1
                else:
                    flags.append('OTHER')
                    other_count += 1

                flag_str = ', '.join(flags) if flags else 'NONE'
                status_msg += f"  - {mob_name} (Lv{mob_level}) HP:{mob_hp}/{mob_max_hp} [{flag_str}]\n"

            status_msg += "\n"

        status_msg += "=" * 50 + "\n"
        status_msg += f"Total Mobs: {total_mobs}\n"
        status_msg += f"  Wandering: {wandering_count}\n"
        status_msg += f"  Lair: {lair_count}\n"
        status_msg += f"  Gong-spawned: {gong_count}\n"
        status_msg += f"  Other: {other_count}\n"

        movement_chance = self.game_engine.config_manager.get_setting('dungeon', 'wandering_mobs', 'movement_chance', default=0.2)
        enabled = self.game_engine.config_manager.get_setting('dungeon', 'wandering_mobs', 'enabled', default=False)
        status_msg += f"\nWandering System: {'ENABLED' if enabled else 'DISABLED'}\n"
        status_msg += f"Movement Chance: {movement_chance * 100}% per tick\n"

        await self.game_engine.connection_manager.send_message(player_id, status_msg)

    async def handle_admin_give_gold(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin give gold command."""
        await self._handle_admin_give_gold(player_id, character, params)

    async def handle_admin_give_xp(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin give XP command."""
        await self._handle_admin_give_xp(player_id, character, params)

    async def handle_admin_give_item(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin give item command."""
        await self._handle_admin_give_item(player_id, character, params)

    async def handle_admin_mob_status(self, player_id: int):
        """Public wrapper for admin mob status command."""
        await self._handle_admin_mob_status(player_id)

    async def handle_admin_respawn_npc(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin respawn NPC command."""
        await self._handle_admin_respawn_npc(player_id, character, params)

    async def handle_admin_set_stat(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin set stat command."""
        await self._handle_admin_set_stat(player_id, character, params)

    async def handle_admin_set_level(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin set level command."""
        await self._handle_admin_set_level(player_id, character, params)

    async def handle_admin_set_mana(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin set mana command."""
        await self._handle_admin_set_mana(player_id, character, params)

    async def handle_admin_set_health(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin set health command."""
        await self._handle_admin_set_health(player_id, character, params)

    async def handle_admin_god_mode(self, player_id: int, character: dict):
        """Public wrapper for admin god mode command."""
        await self._handle_admin_god_mode(player_id, character)

    async def handle_admin_condition_command(self, player_id: int, character: dict, params: str):
        """Public wrapper for admin condition command."""
        await self._handle_admin_condition_command(player_id, character, params)

    async def handle_admin_teleport(self, player_id: int, character: dict, params: str):
        """Admin command to teleport self or another player to a room.

        Usage:
            teleport <room_id>              - Teleport yourself
            teleport <player_name> <room_id> - Teleport another player
        """
        parts = params.strip().split(maxsplit=1)

        if len(parts) == 1:
            # Teleport self to room
            target_room_id = parts[0]
            target_player_id = player_id
            target_character = character
            teleporter_name = character.get('name', 'Admin')
        elif len(parts) == 2:
            # Teleport another player to room
            target_player_name = parts[0]
            target_room_id = parts[1]

            # Find target player
            target_player_id = None
            target_character = None

            for pid, pdata in self.game_engine.player_manager.connected_players.items():
                char = pdata.get('character')
                if char and char.get('name', '').lower() == target_player_name.lower():
                    target_player_id = pid
                    target_character = char
                    break

            if not target_player_id:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"[ADMIN] Player '{target_player_name}' not found or not online."
                )
                return

            teleporter_name = character.get('name', 'Admin')
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "Usage: teleport <room_id> OR teleport <player_name> <room_id>"
            )
            return

        # Verify target room exists
        target_room = self.game_engine.world_manager.get_room(target_room_id)
        if not target_room:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Room '{target_room_id}' does not exist."
            )
            return

        # Get old room
        old_room_id = target_character.get('room_id')
        target_name = target_character.get('name', 'Someone')

        # Notify players in old room
        if old_room_id:
            await self.game_engine._notify_room_except_player(
                old_room_id,
                target_player_id,
                f"{target_name} vanishes in a flash of light!"
            )

        # Update character's room
        target_character['room_id'] = target_room_id

        # Notify players in new room
        await self.game_engine._notify_room_except_player(
            target_room_id,
            target_player_id,
            f"{target_name} appears in a flash of light!"
        )

        # Show room description to teleported player
        await self.game_engine.world_manager.send_room_description(target_player_id, detailed=True)

        # Confirm to admin
        if target_player_id == player_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Teleported to {target_room_id} ({target_room.title})"
            )
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Teleported {target_name} to {target_room_id} ({target_room.title})"
            )
            await self.game_engine.connection_manager.send_message(
                target_player_id,
                f"[ADMIN] You have been teleported to {target_room.title} by {teleporter_name}!"
            )

    async def _handle_admin_respawn_npc(self, player_id: int, character: dict, params: str):
        """Admin command to respawn an NPC in its original room.

        Usage: respawnnpc <npc_id>
        """
        npc_id = params.strip()

        if not npc_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: respawnnpc <npc_id>"
            )
            return

        # Check if NPC exists in the world data
        npc_data = self.game_engine.world_manager.get_npc_data(npc_id)
        if not npc_data:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] NPC '{npc_id}' not found in NPC data."
            )
            return

        # Find which room this NPC should be in
        target_room_id = None
        for room_id, room_data in self.game_engine.world_manager.rooms_data.items():
            if 'npcs' in room_data and npc_id in room_data['npcs']:
                target_room_id = room_id
                break

        if not target_room_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Could not find original room for NPC '{npc_id}'."
            )
            return

        # Get the target room
        target_room = self.game_engine.world_manager.get_room(target_room_id)
        if not target_room:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Target room '{target_room_id}' does not exist."
            )
            return

        # Check if NPC already exists in the room
        npc_already_exists = False
        for npc in target_room.npcs:
            if npc.npc_id == npc_id:
                npc_already_exists = True
                break

        if npc_already_exists:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] NPC '{npc_data.get('name', npc_id)}' already exists in room {target_room_id}."
            )
            return

        # Create and add the NPC
        from ...game.npcs.npc import NPC

        description = npc_data.get('long_description') or npc_data.get('description', 'A mysterious figure.')

        npc = NPC(
            npc_id=npc_data.get('id', npc_id),
            name=npc_data.get('name', 'Unknown NPC'),
            description=description
        )

        npc.room_id = target_room_id
        if 'type' in npc_data:
            npc.npc_type = npc_data['type']
        if 'dialogue' in npc_data:
            npc.dialogue = npc_data['dialogue']

        target_room.npcs.append(npc)

        # Notify admin
        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Respawned NPC '{npc_data.get('name', npc_id)}' in room {target_room_id} ({target_room.title})."
        )

        # Notify players in the room
        await self.game_engine._notify_room_except_player(
            target_room_id,
            player_id,
            f"{npc_data.get('name', 'Someone')} appears in a shimmer of magical energy!"
        )

    async def _handle_admin_set_stat(self, player_id: int, character: dict, params: str):
        """Admin command to set a character stat.

        Usage: setstat <stat_name> <value>
        Stats: strength, dexterity, constitution, vitality, intellect, wisdom, charisma
        """
        parts = params.strip().split()
        if len(parts) != 2:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: setstat <stat_name> <value>\nStats: strength, dexterity, constitution, vitality, intellect, wisdom, charisma"
            )
            return

        stat_name = parts[0].lower()
        try:
            value = int(parts[1])
        except ValueError:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Error: Value must be a number"
            )
            return

        # Map stat names to character keys
        stat_map = {
            'str': 'strength',
            'strength': 'strength',
            'dex': 'dexterity',
            'dexterity': 'dexterity',
            'con': 'constitution',
            'constitution': 'constitution',
            'vit': 'vitality',
            'vitality': 'vitality',
            'int': 'intellect',
            'intellect': 'intellect',
            'intelligence': 'intellect',
            'wis': 'wisdom',
            'wisdom': 'wisdom',
            'cha': 'charisma',
            'charisma': 'charisma'
        }

        stat_key = stat_map.get(stat_name)
        if not stat_key:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Error: Unknown stat '{stat_name}'\nValid stats: strength, dexterity, constitution, vitality, intellect, wisdom, charisma"
            )
            return

        # Clamp value between 1 and 99
        value = max(1, min(99, value))

        old_value = character.get(stat_key, 10)
        character[stat_key] = value

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] {stat_key.capitalize()} set: {old_value} -> {value}"
        )

    async def _handle_admin_set_level(self, player_id: int, character: dict, params: str):
        """Admin command to set character level.

        Usage: setlevel <level>
        """
        try:
            level = int(params.strip())
        except ValueError:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Error: Level must be a number"
            )
            return

        # Clamp level between 1 and 50
        level = max(1, min(50, level))

        old_level = character.get('level', 1)
        character['level'] = level

        # Update max HP and mana based on new level
        # Base HP: 100 + (level * 10)
        # Base Mana: 50 + (level * 5)
        max_hp = 100 + (level * 10)
        max_mana = 50 + (level * 5)

        character['max_hit_points'] = max_hp
        character['max_mana'] = max_mana
        character['current_hit_points'] = max_hp
        character['current_mana'] = max_mana

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Level set: {old_level} -> {level}\nMax HP: {max_hp}, Max Mana: {max_mana}\nHealth and mana restored to full."
        )

    async def _handle_admin_set_mana(self, player_id: int, character: dict, params: str):
        """Admin command to set character mana.

        Usage: setmana <current> [max] OR setmana full
        """
        parts = params.strip().split()

        if parts[0].lower() == 'full':
            max_mana = character.get('max_mana', 50)
            character['current_mana'] = max_mana
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Mana restored to full: {max_mana}"
            )
            return

        try:
            current = int(parts[0])
        except (ValueError, IndexError):
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: setmana <current> [max] OR setmana full"
            )
            return

        # If max value provided, set it
        if len(parts) > 1:
            try:
                max_mana = int(parts[1])
                character['max_mana'] = max(1, max_mana)
            except ValueError:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "[ADMIN] Error: Max mana must be a number"
                )
                return

        character['current_mana'] = max(0, current)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Mana set: {character['current_mana']} / {character.get('max_mana', 50)}"
        )

    async def _handle_admin_set_health(self, player_id: int, character: dict, params: str):
        """Admin command to set character health.

        Usage: sethealth <current> [max] OR sethealth full
        """
        parts = params.strip().split()

        if parts[0].lower() == 'full':
            max_hp = character.get('max_hit_points', 100)
            character['current_hit_points'] = max_hp
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"[ADMIN] Health restored to full: {max_hp}"
            )
            return

        try:
            current = int(parts[0])
        except (ValueError, IndexError):
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] Usage: sethealth <current> [max] OR sethealth full"
            )
            return

        # If max value provided, set it
        if len(parts) > 1:
            try:
                max_hp = int(parts[1])
                character['max_hit_points'] = max(1, max_hp)
            except ValueError:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    "[ADMIN] Error: Max health must be a number"
                )
                return

        character['current_hit_points'] = max(1, current)

        await self.game_engine.connection_manager.send_message(
            player_id,
            f"[ADMIN] Health set: {character['current_hit_points']} / {character.get('max_hit_points', 100)}"
        )

    async def _handle_admin_god_mode(self, player_id: int, character: dict):
        """Admin command to toggle god mode (invincibility + max stats).

        Usage: godmode OR god
        """
        # Toggle god mode flag
        current_god_mode = character.get('god_mode', False)
        character['god_mode'] = not current_god_mode

        if character['god_mode']:
            # Enable god mode - set all stats to 99
            character['strength'] = 99
            character['dexterity'] = 99
            character['constitution'] = 99
            character['vitality'] = 99
            character['intellect'] = 99
            character['wisdom'] = 99
            character['charisma'] = 99

            # Set level to 50
            character['level'] = 50
            character['max_hit_points'] = 9999
            character['max_mana'] = 9999
            character['current_hit_points'] = 9999
            character['current_mana'] = 9999

            # Give lots of gold
            character['gold'] = character.get('gold', 0) + 100000

            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] GOD MODE ENABLED!\nAll stats set to 99, Level 50, HP/Mana 9999, +100,000 gold"
            )
        else:
            # Disable god mode
            await self.game_engine.connection_manager.send_message(
                player_id,
                "[ADMIN] God mode disabled. Use 'setstat' and 'setlevel' to adjust stats manually."
            )

    async def _handle_admin_condition_command(self, player_id: int, character: dict, params: str):
        """Admin command to apply various conditions to the player for testing.

        Usage: condition <type>
        Types: poison, hungry, thirsty, paralyzed
        """
        condition = params.strip().lower()

        if condition == 'poison':
            # Add poison effect
            if 'poison_effects' not in character:
                character['poison_effects'] = []

            character['poison_effects'].append({
                'duration': 10,
                'damage': '2d3',
                'caster_id': player_id,
                'spell_name': 'Admin Poison'
            })
            message = "[ADMIN] You have been poisoned! (10 ticks, 2d3 damage per tick)"

        elif condition == 'hungry':
            character['hunger'] = 10
            message = "[ADMIN] You are now very hungry! (Hunger set to 10)"

        elif condition == 'thirsty':
            character['thirst'] = 10
            message = "[ADMIN] You are now very thirsty! (Thirst set to 10)"

        elif condition == 'paralyzed':
            # Add paralysis effect to active_effects
            if 'active_effects' not in character:
                character['active_effects'] = []

            character['active_effects'].append({
                'type': 'paralyzed',
                'duration': 5,
                'effect': 'movement_disabled',
                'effect_amount': 0
            })
            message = "[ADMIN] You have been paralyzed! (5 ticks, movement disabled)"

        elif condition == 'starving':
            character['hunger'] = 0
            message = "[ADMIN] You are now starving! (Hunger set to 0, will take damage)"

        elif condition == 'dehydrated':
            character['thirst'] = 0
            message = "[ADMIN] You are now dehydrated! (Thirst set to 0, will take damage)"

        else:
            message = f"[ADMIN] Unknown condition: {condition}\nValid types: poison, hungry, thirsty, paralyzed, starving, dehydrated"

        await self.game_engine.connection_manager.send_message(player_id, message)

