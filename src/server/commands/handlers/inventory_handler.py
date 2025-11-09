"""Inventory command handler for inventory management commands."""

from ..base_handler import BaseCommandHandler
from ...utils.colors import wrap_color, Colors, error_message, success_message, item_found


class InventoryCommandHandler(BaseCommandHandler):
    """Handles inventory management commands."""

    async def handle_inventory_command(self, player_id: int, character: dict):
        """Display player inventory.

        Usage: inventory, inv, i
        """
        char = character
        inventory_text = f"{wrap_color('You are carrying:', Colors.BOLD_CYAN)}\n"
        if char['inventory']:
            for i, item in enumerate(char['inventory'], 1):
                item_name = item['name']

                # Add quantity if item has more than 1
                quantity = item.get('quantity', 1)
                if quantity > 1:
                    item_name += f" {wrap_color(f'({quantity})', Colors.BOLD_GREEN)}"

                # Add lit/unlit status for light sources
                if item.get('is_light_source', False):
                    if item.get('is_lit', False):
                        time_remaining = item.get('time_remaining', 0)
                        minutes = int(time_remaining // 60)
                        seconds = int(time_remaining % 60)
                        item_name += f" {wrap_color('(lit', Colors.BOLD_YELLOW)}{wrap_color(f' - {minutes}m {seconds}s', Colors.BOLD_GREEN)}{wrap_color(')', Colors.BOLD_YELLOW)}"
                    else:
                        item_name += f" {wrap_color('(unlit)', Colors.BOLD_WHITE)}"

                # Add container contents summary
                if item.get('type') == 'container':
                    contents = item.get('contents', [])
                    if contents:
                        # Show total quantity of items in container
                        for content_item in contents:
                            content_quantity = content_item.get('quantity', 1)
                            content_name = content_item.get('name', 'items')
                            item_name += f" {wrap_color(f'({content_quantity} {content_name})', Colors.BOLD_GREEN)}"
                    else:
                        item_name += f" {wrap_color('(empty)', Colors.BOLD_WHITE)}"

                inventory_text += f"  {wrap_color(str(i) + '.', Colors.BOLD_WHITE)} {wrap_color(item_name, Colors.BOLD_WHITE)}\n"
        else:
            inventory_text += f"  {wrap_color('Nothing.', Colors.BOLD_WHITE)}\n"

        # Show equipped items
        inventory_text += f"\n{wrap_color('--- Equipped ---', Colors.BOLD_YELLOW)}\n"
        weapon = char['equipped']['weapon']
        armor = char['equipped']['armor']
        inventory_text += f"{wrap_color('Weapon:', Colors.BOLD_CYAN)} {wrap_color(weapon['name'] if weapon else 'None', Colors.BOLD_WHITE)}\n"
        inventory_text += f"{wrap_color('Armor:', Colors.BOLD_CYAN)}  {wrap_color(armor['name'] if armor else 'None', Colors.BOLD_WHITE)}\n"

        inventory_text += f"\n{wrap_color('Gold:', Colors.BOLD_CYAN)} {wrap_color(str(char['gold']), Colors.BOLD_YELLOW)}{Colors.BOLD_WHITE}"
        await self.send_message(player_id, inventory_text)

    async def handle_get_item(self, player_id: int, item_name: str):
        """Handle picking up an item from the room.

        Usage: get <item>, take <item>
        """
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # First, try to pick up an item from the room floor
        if room_id:
            item, match_type = self.game_engine.item_manager.remove_item_from_room(room_id, item_name)
            if item:
                # Check encumbrance before picking up
                current_encumbrance = self.player_manager.calculate_encumbrance(character)
                item_weight = item.get('weight', 0)
                max_encumbrance = self.player_manager.calculate_max_encumbrance(character)

                if current_encumbrance + item_weight > max_encumbrance:
                    # Put the item back on the floor since we can't pick it up
                    self.game_engine.item_manager.add_item_to_room(room_id, item)
                    await self.send_message(
                        player_id,
                        error_message(f"You cannot pick up {item['name']} - you are carrying too much! ({current_encumbrance + item_weight:.1f}/{max_encumbrance})")
                    )
                    return

                # Found item on floor, pick it up
                character['inventory'].append(item)

                # Update encumbrance
                self.player_manager.update_encumbrance(character)

                await self.send_message(
                    player_id,
                    item_found(f"You pick up the {item['name']}.")
                )

                # Notify others in the room
                username = player_data.get('username', 'Someone')
                await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} picks up a {item['name']}.")
                return

        # Item not found on floor or in config
        await self.send_message(
            player_id,
            error_message(f"You don't see a {item_name} here.")
        )

    async def handle_drop_item(self, player_id: int, item_name: str):
        """Handle dropping an item from inventory.

        Usage: drop <item>
        """
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']

        # Find item in inventory using partial name matching
        inventory = character.get('inventory', [])
        item_to_drop, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.send_message(
                player_id,
                error_message(f"You don't have a {item_name}.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just drop the first one
            pass  # item_to_drop and item_index are already set to the first match

        # Remove item from inventory
        dropped_item = character['inventory'].pop(item_index)

        # Add item to room
        room_id = character.get('room_id')
        if room_id:
            self.game_engine.item_manager.add_item_to_room(room_id, dropped_item)

        # Update encumbrance
        self.player_manager.update_encumbrance(character)

        await self.send_message(
            player_id,
            success_message(f"Ok, you dropped your {dropped_item['name'].lower()}.")
        )

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} drops a {dropped_item['name']}.")

    async def handle_equip_item(self, player_id: int, item_name: str):
        """Handle equipping an item from inventory.

        Usage: equip <item>, wear <item>, wield <item>
        """
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        inventory = character.get('inventory', [])

        # Find item in inventory using partial name matching
        item_to_equip, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        if match_type == 'none':
            await self.send_message(
                player_id,
                error_message(f"You don't have a {item_name} to equip.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just equip the first one
            pass  # item_to_equip and item_index are already set to the first match

        # Determine which slot this item goes in
        item_type = item_to_equip.get('type', 'misc')
        if item_type == 'weapon':
            slot = 'weapon'
        elif item_type == 'armor':
            slot = 'armor'
        else:
            await self.send_message(
                player_id,
                error_message(f"You cannot equip the {item_to_equip['name']}.")
            )
            return

        # Check level requirement
        item_properties = item_to_equip.get('properties', {})
        required_level = item_properties.get('required_level', 0)
        character_level = character.get('level', 1)

        if character_level < required_level:
            await self.send_message(
                player_id,
                error_message(f"You must be level {required_level} to equip the {item_to_equip['name']}. (You are level {character_level})")
            )
            return

        # Check class requirement
        allowed_classes = item_properties.get('allowed_classes', None)
        if allowed_classes:
            character_class = character.get('class', 'fighter').lower()
            if character_class not in allowed_classes:
                class_list = ", ".join([c.capitalize() for c in allowed_classes])
                await self.send_message(
                    player_id,
                    f"Only {class_list} can equip the {item_to_equip['name']}."
                )
                return

        # Check if slot is already occupied
        equipped_items = character.get('equipped', {})
        if equipped_items.get(slot):
            currently_equipped = equipped_items[slot]
            await self.send_message(player_id,
                f"You are already wearing {currently_equipped['name']}. "
                f"You must unequip it first.")
            return

        # Remove from inventory and equip
        equipped_item = character['inventory'].pop(item_index)
        character['equipped'][slot] = equipped_item

        # Update armor class if armor
        if item_type == 'armor':
            armor_class = equipped_item.get('properties', {}).get('armor_class', 0)
            character['armor_class'] = armor_class

        # Update encumbrance (should be same, but recalculate for consistency)
        self.player_manager.update_encumbrance(character)

        await self.send_message(player_id, f"You equip the {equipped_item['name']}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} equips a {equipped_item['name']}.")

    async def handle_unequip_item(self, player_id: int, item_name: str):
        """Handle unequipping an item to inventory.

        Usage: unequip <item>, remove <item>
        """
        player_data = self.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        equipped = character.get('equipped', {})

        # Create a list of equipped items for partial matching
        equipped_items = []
        slot_mapping = {}
        for slot, equipped_item in equipped.items():
            if equipped_item:
                equipped_items.append(equipped_item)
                slot_mapping[equipped_item['name']] = slot

        # Find the equipped item using partial name matching
        item_to_unequip, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(equipped_items, item_name)

        if match_type == 'none':
            await self.send_message(
                player_id,
                error_message(f"You don't have a {item_name} equipped.")
            )
            return
        elif match_type == 'multiple':
            # Find the matching items for the error message
            matches = [item['name'] for item in equipped_items if item_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.send_message(
                player_id,
                error_message(f"'{item_name}' matches multiple equipped items: {match_list}. Please be more specific.")
            )
            return

        # Get the slot to clear
        slot_to_clear = slot_mapping[item_to_unequip['name']]

        # Unequip the item
        character['equipped'][slot_to_clear] = None
        character['inventory'].append(item_to_unequip)

        # Update armor class if armor
        if item_to_unequip.get('type') == 'armor':
            character['armor_class'] = 0  # Reset to base armor class

        # Update encumbrance
        self.player_manager.update_encumbrance(character)

        await self.send_message(player_id, f"You unequip your {item_to_unequip['name']}.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} unequips their {item_to_unequip['name']}.")

    async def handle_put_command(self, player_id: int, character: dict, params: str):
        """Handle putting an item into a container.

        Usage: put <item> in <container>
               put all <item> in <container>
               put <quantity> <item> in <container>
        """
        # Parse the command
        if ' in ' not in params.lower():
            await self.send_message(
                player_id,
                error_message("Usage: put <item> in <container>, put all <item> in <container>, or put <quantity> <item> in <container>")
            )
            return

        parts = params.split(' in ', 1)
        item_part = parts[0].strip()
        container_name = parts[1].strip()

        if not item_part or not container_name:
            await self.send_message(
                player_id,
                error_message("Usage: put <item> in <container>, put all <item> in <container>, or put <quantity> <item> in <container>")
            )
            return

        # Check for quantity or "all" prefix
        put_all = False
        specific_quantity = None
        item_name = item_part

        # Check for "all" prefix
        if item_part.lower().startswith('all '):
            put_all = True
            item_name = item_part[4:].strip()
        else:
            # Check for numeric quantity prefix (e.g., "3 arrow")
            parts_item = item_part.split(None, 1)
            if len(parts_item) >= 2 and parts_item[0].isdigit():
                specific_quantity = int(parts_item[0])
                item_name = parts_item[1]

        inventory = character.get('inventory', [])

        # Find the container first
        container, container_index, container_match_type = self.game_engine.item_manager.find_item_by_partial_name(
            inventory, container_name
        )

        if container_match_type == 'none':
            await self.send_message(
                player_id,
                error_message(f"You don't have a {container_name}.")
            )
            return
        elif container_match_type == 'multiple':
            matches = [item['name'] for item in inventory if container_name.lower() in item['name'].lower()]
            match_list = ", ".join(matches)
            await self.send_message(
                player_id,
                error_message(f"'{container_name}' matches multiple items: {match_list}. Please be more specific.")
            )
            return

        # Verify it's actually a container
        if container.get('type') != 'container':
            await self.send_message(
                player_id,
                error_message(f"The {container['name']} is not a container.")
            )
            return

        # Check container capacity
        container_props = container.get('properties', {})
        max_capacity = container_props.get('max_capacity', 20)
        contents = container.get('contents', [])
        current_capacity = sum(item.get('quantity', 1) for item in contents)

        if put_all or specific_quantity:
            # Find all matching items in inventory (by item ID for stackable items)
            items_to_put = []
            target_item_id = None

            for i, item in enumerate(inventory):
                if i == container_index:
                    continue  # Skip the container itself

                # Get item name and id safely
                item_name_str = item.get('name', '')
                item_id_str = item.get('id', '')

                # Check if item matches by name or id
                if item_name.lower() in item_name_str.lower() or item_id_str.lower() == item_name.lower():
                    if target_item_id is None:
                        target_item_id = item_id_str
                    # Only match items with the same ID (so all arrows stack together)
                    if item_id_str == target_item_id:
                        items_to_put.append((item, i))

            if not items_to_put:
                await self.send_message(
                    player_id,
                    error_message(f"You don't have any {item_name}.")
                )
                return

            # Calculate total quantity available
            total_available = sum(item.get('quantity', 1) for item, _ in items_to_put)

            # Determine how much to transfer
            if specific_quantity:
                # User specified exact amount
                if specific_quantity > total_available:
                    await self.send_message(
                        player_id,
                        error_message(f"You only have {total_available} {items_to_put[0][0]['name']}, not {specific_quantity}.")
                    )
                    return
                quantity_to_put = specific_quantity
            else:
                # User said "all"
                quantity_to_put = total_available

            # Check capacity and adjust if needed
            space_available = max_capacity - current_capacity
            if quantity_to_put > space_available:
                if put_all:
                    # Auto-adjust for "all" command
                    quantity_to_put = space_available
                    if quantity_to_put <= 0:
                        await self.send_message(
                            player_id,
                            error_message(f"The {container['name']} is full. (Capacity: {current_capacity}/{max_capacity})")
                        )
                        return
                else:
                    # User specified exact amount that won't fit
                    await self.send_message(
                        player_id,
                        error_message(f"The {container['name']} only has room for {space_available} more items. (Capacity: {current_capacity}/{max_capacity})")
                    )
                    return

            # Add to container (stack with existing if present)
            item_id = items_to_put[0][0].get('id')
            existing_item = None
            for content_item in contents:
                if content_item.get('id') == item_id:
                    existing_item = content_item
                    break

            if existing_item:
                # Stack with existing item
                existing_item['quantity'] = existing_item.get('quantity', 1) + quantity_to_put
            else:
                # Add new item to contents
                if 'contents' not in container:
                    container['contents'] = []
                new_item = items_to_put[0][0].copy()
                new_item['quantity'] = quantity_to_put
                container['contents'].append(new_item)

            # Remove from inventory
            remaining_to_remove = quantity_to_put
            for item, idx in reversed(items_to_put):
                if remaining_to_remove <= 0:
                    break

                item_qty = item.get('quantity', 1)

                if item_qty <= remaining_to_remove:
                    # Remove entire stack
                    if idx < container_index:
                        character['inventory'].pop(idx)
                        container_index -= 1
                    else:
                        character['inventory'].pop(idx)
                    remaining_to_remove -= item_qty
                else:
                    # Partial removal from stack
                    item['quantity'] = item_qty - remaining_to_remove
                    remaining_to_remove = 0

            item_display_name = items_to_put[0][0]['name']
            if put_all and quantity_to_put < total_available:
                await self.send_message(
                    player_id,
                    success_message(f"You put {quantity_to_put} {item_display_name} in your {container['name']} ({total_available - quantity_to_put} remaining, container full).")
                )
            else:
                await self.send_message(
                    player_id,
                    success_message(f"You put {quantity_to_put} {item_display_name} in your {container['name']}.")
                )

        else:
            # Single item logic
            # Find the item to put
            item_to_put, item_index, item_match_type = self.game_engine.item_manager.find_item_by_partial_name(
                inventory, item_name
            )

            if item_match_type == 'none':
                await self.send_message(
                    player_id,
                    error_message(f"You don't have a {item_name}.")
                )
                return
            elif item_match_type == 'multiple':
                matches = [item['name'] for item in inventory if item_name.lower() in item['name'].lower()]
                match_list = ", ".join(matches)
                await self.send_message(
                    player_id,
                    error_message(f"'{item_name}' matches multiple items: {match_list}. Please be more specific.")
                )
                return

            # Can't put a container in itself
            if item_index == container_index:
                await self.send_message(
                    player_id,
                    error_message(f"You can't put something inside itself.")
                )
                return

            item_quantity = item_to_put.get('quantity', 1)

            if current_capacity + item_quantity > max_capacity:
                await self.send_message(
                    player_id,
                    error_message(f"The {container['name']} is full. (Capacity: {current_capacity}/{max_capacity})")
                )
                return

            # Check if container already has this item type (for stacking)
            item_id = item_to_put.get('id')
            existing_item = None
            for content_item in contents:
                if content_item.get('id') == item_id:
                    existing_item = content_item
                    break

            if existing_item:
                # Stack with existing item
                existing_item['quantity'] = existing_item.get('quantity', 1) + item_quantity
            else:
                # Add new item to contents
                if 'contents' not in container:
                    container['contents'] = []
                container['contents'].append(item_to_put.copy())

            # Remove from inventory
            if container_index < item_index:
                character['inventory'].pop(item_index)
            else:
                character['inventory'].pop(item_index)

            await self.send_message(
                player_id,
                success_message(f"You put {item_quantity} {item_to_put['name']} in your {container['name']}.")
            )

        # Notify others in the room
        player_data = self.player_manager.get_player_data(player_id)
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(
                room_id, player_id,
                f"{username} puts something in their {container['name']}."
            )
