"""
Vendor Command Handler

Handles commands for trading with NPCs:
- trade (buy/sell) - Main trade dispatcher
- list - Display vendor inventory
- buy - Purchase items from vendors
- sell - Sell items to vendors
- heal - Healing services from healer NPCs
"""

from ..base_handler import BaseCommandHandler
from ...utils.colors import error_message, success_message, info_message, service_message


class VendorCommandHandler(BaseCommandHandler):
    """Handler for vendor/trading commands."""

    async def handle_trade_command(self, player_id: int, action: str, params: str):
        """Handle buy/sell commands with vendors.

        Supports:
        - buy <item> - buy from first vendor
        - buy <quantity> <item> - buy multiple items
        - buy <item> from <vendor> - buy from specific vendor
        - sell <item> - sell to first vendor
        - sell <item> to <vendor> - sell to specific vendor
        """
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Parse the command to extract item name and optional vendor name
        item_name = params
        vendor_name = None
        quantity = 1

        # Check for "from <vendor>" or "to <vendor>"
        if ' from ' in params.lower():
            parts = params.lower().split(' from ', 1)
            item_name = parts[0].strip()
            vendor_name = parts[1].strip()
        elif ' to ' in params.lower():
            parts = params.lower().split(' to ', 1)
            item_name = parts[0].strip()
            vendor_name = parts[1].strip()

        # Check for quantity at the beginning (e.g., "20 arrows" or "5 potions")
        if action == 'buy':
            parts = item_name.split(None, 1)
            if len(parts) == 2 and parts[0].isdigit():
                quantity = int(parts[0])
                item_name = parts[1]

        # Find the vendor
        if vendor_name:
            vendor = self.game_engine.vendor_system.find_vendor_by_name(room_id, vendor_name)
            if not vendor:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"There is no vendor named '{vendor_name}' here.")
                )
                return
        else:
            vendor = self.game_engine.vendor_system.get_vendor_in_room(room_id)
            if not vendor:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("There is no vendor here to trade with.")
                )
                return

        if action == 'buy':
            await self.handle_buy_item(player_id, vendor, item_name, quantity)
        elif action == 'sell':
            await self.handle_sell_item(player_id, vendor, item_name)

    async def handle_list_vendor_items(self, player_id: int, vendor_name: str = None):
        """Show vendor inventory.

        Args:
            player_id: The player requesting the list
            vendor_name: Optional name of specific vendor to list. If None, lists first vendor.
        """
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Find the vendor
        if vendor_name:
            vendor = self.game_engine.vendor_system.find_vendor_by_name(room_id, vendor_name)
            if not vendor:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"There is no vendor named '{vendor_name}' here.")
                )
                return
        else:
            vendor = self.game_engine.vendor_system.get_vendor_in_room(room_id)
            if not vendor:
                # Check if there are multiple vendors
                vendors = self.game_engine.vendor_system.get_vendors_in_room(room_id)
                if len(vendors) > 1:
                    vendor_names = [v['name'] for v in vendors]
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        info_message(f"There are multiple vendors here: {', '.join(vendor_names)}. Use 'list <vendor name>' to see a specific vendor's wares.")
                    )
                    return
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("There is no vendor here.")
                )
                return

        inventory_text = f"{vendor['name']} has the following items for sale:\n"
        for i, item_entry in enumerate(vendor['inventory'], 1):
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config:
                item_name = item_config['name']
                # Calculate price from base_value and vendor's sell_markup
                base_value = item_config.get('base_value', 0)
                sell_markup = vendor.get('sell_markup', 1.2)
                price = int(base_value * sell_markup)
                inventory_text += f"  {i}. {item_name} - {price} gold\n"
            else:
                # Try to get price from item_entry, fallback to 0
                price = item_entry.get('price', 0)
                inventory_text += f"  {i}. {item_id} (unknown item) - {price} gold\n"

        await self.game_engine.connection_manager.send_message(player_id, inventory_text)

    async def handle_buy_item(self, player_id: int, vendor: dict, item_name: str, quantity: int = 1):
        """Handle buying an item from a vendor.

        Args:
            player_id: The player making the purchase
            vendor: The vendor dict
            item_name: Name of the item to buy
            quantity: Number of items to buy (default 1)
        """
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        character = player_data['character']

        # Validate quantity
        if quantity < 1:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You must buy at least 1 item.")
            )
            return

        # Find the item in vendor inventory using multi-pass approach:
        # Pass 1: Try exact match on full name
        # Pass 2: Try matching on individual words (for "Scroll of X" items)
        # Pass 3: Try word boundary partial match (word starts with search term)
        # Pass 4: Fall back to substring match as last resort
        item_found_id = None
        item_price = None
        item_stock = None

        # First pass: Look for exact match
        for item_entry in vendor['inventory']:
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config and item_name.lower() == item_config['name'].lower():
                item_found_id = item_id
                # Calculate price from base_value and vendor's sell_markup
                base_value = item_config.get('base_value', 0)
                sell_markup = vendor.get('sell_markup', 1.2)
                item_price = int(base_value * sell_markup)
                item_stock = item_entry.get('stock', -1)
                break

        # Second pass: Try matching individual words (exact word match)
        if not item_found_id:
            for item_entry in vendor['inventory']:
                item_id = item_entry['item_id']
                item_config = self.game_engine.config_manager.get_item(item_id)
                if item_config:
                    item_words = item_config['name'].lower().split()
                    if item_name.lower() in item_words:
                        item_found_id = item_id
                        base_value = item_config.get('base_value', 0)
                        sell_markup = vendor.get('sell_markup', 1.2)
                        item_price = int(base_value * sell_markup)
                        item_stock = item_entry.get('stock', -1)
                        break

        # Third pass: Try word boundary match (word starts with search term)
        if not item_found_id:
            for item_entry in vendor['inventory']:
                item_id = item_entry['item_id']
                item_config = self.game_engine.config_manager.get_item(item_id)
                if item_config:
                    item_words = item_config['name'].lower().split()
                    if any(word.startswith(item_name.lower()) for word in item_words):
                        item_found_id = item_id
                        base_value = item_config.get('base_value', 0)
                        sell_markup = vendor.get('sell_markup', 1.2)
                        item_price = int(base_value * sell_markup)
                        item_stock = item_entry.get('stock', -1)
                        break

        # Fourth pass: Substring match as last resort
        if not item_found_id:
            for item_entry in vendor['inventory']:
                item_id = item_entry['item_id']
                item_config = self.game_engine.config_manager.get_item(item_id)
                if item_config and item_name.lower() in item_config['name'].lower():
                    item_found_id = item_id
                    # Calculate price from base_value and vendor's sell_markup
                    base_value = item_config.get('base_value', 0)
                    sell_markup = vendor.get('sell_markup', 1.2)
                    item_price = int(base_value * sell_markup)
                    item_stock = item_entry.get('stock', -1)
                    break

        if not item_found_id:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"{vendor['name']} doesn't have {item_name} for sale.")
            )
            return

        # Create proper item instance to get the real name
        item_instance = self.game_engine.config_manager.create_item_instance(item_found_id, item_price)
        if not item_instance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Error creating item.")
            )
            return

        # Check if vendor has enough stock (stock of -1 means unlimited)
        if item_stock != -1 and item_stock < quantity:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"{vendor['name']} only has {item_stock} {item_instance['name']} in stock.")
            )
            return

        # Calculate total cost
        total_price = item_price * quantity

        # Check if player has enough gold
        if character['gold'] < total_price:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have enough gold. {quantity} {item_instance['name']} costs {total_price} gold. (You have {character['gold']} gold)")
            )
            return

        # Check encumbrance before buying
        current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
        item_weight = item_instance.get('weight', 0) * quantity
        gold_weight_change = -total_price / 100.0  # Losing gold reduces weight
        max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)

        if current_encumbrance + item_weight + gold_weight_change > max_encumbrance:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You cannot carry {quantity} {item_instance['name']} - you are carrying too much!")
            )
            return

        # Complete the purchase
        character['gold'] -= total_price

        # Add items to inventory (stack if possible)
        if quantity == 1:
            character['inventory'].append(item_instance)
        else:
            # Create a single item with quantity field
            item_instance['quantity'] = quantity
            character['inventory'].append(item_instance)

        # Reduce vendor stock (if not unlimited)
        self.game_engine.vendor_system.reduce_vendor_stock(vendor, item_found_id, quantity)

        # Update encumbrance (accounts for gold weight change and new items)
        self.game_engine.player_manager.update_encumbrance(character)

        if quantity == 1:
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You buy {item_instance['name']} for {item_price} gold.")
            )
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You buy {quantity} {item_instance['name']} for {total_price} gold.")
            )

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} buys something from {vendor['name']}.")

    async def handle_sell_item(self, player_id: int, vendor: dict, item_name: str):
        """Handle selling an item to a vendor."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        character = player_data['character']

        # Find item in player inventory
        inventory = character.get('inventory', [])

        # Debug logging
        from server.utils.logger import get_logger
        logger = get_logger()
        logger.info(f"[SELL] Searching for '{item_name}' in inventory")
        logger.info(f"[SELL] Inventory has {len(inventory)} items")
        for i, item in enumerate(inventory):
            logger.info(f"[SELL]   {i}: {item}")

        item_to_sell, item_index, match_type = self.game_engine.item_manager.find_item_by_partial_name(inventory, item_name)

        logger.info(f"[SELL] Match result: match_type='{match_type}', item_to_sell={item_to_sell}, item_index={item_index}")

        if match_type == 'none' or item_to_sell is None:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You don't have a {item_name} to sell.")
            )
            return
        elif match_type == 'multiple':
            # If multiple matches, just sell the first one
            # This is the standard MUD behavior - "sell bread" sells one bread if you have multiple
            pass  # item_to_sell and item_index are already set to the first match

        # Calculate sell price (typically half of value)
        sell_price = max(1, item_to_sell.get('value', 10) // 2)

        # Complete the sale
        sold_item = character['inventory'].pop(item_index)
        character['gold'] += sell_price

        # Update encumbrance (accounts for gold weight change and removed item)
        self.game_engine.player_manager.update_encumbrance(character)

        await self.game_engine.connection_manager.send_message(player_id, f"You sell {sold_item['name']} for {sell_price} gold.")

        # Notify others in the room
        username = player_data.get('username', 'Someone')
        room_id = character.get('room_id')
        if room_id:
            await self.game_engine._notify_room_except_player(room_id, player_id, f"{username} sells something to {vendor['name']}.")

    async def handle_heal_command(self, player_id: int, params: str):
        """Handle healing command at a temple/healer."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        character = player_data.get('character', {})
        room_id = character.get('room_id')

        # Get room object
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            await self.game_engine.connection_manager.send_message(player_id, "You are nowhere!")
            return

        # Get NPCs in the room
        npcs_in_room = room.npcs if hasattr(room, 'npcs') else []
        print(f"[HEAL DEBUG] Room: {room_id}, NPCs: {npcs_in_room}")

        # Find a healer NPC
        healer_npc = None
        healer_obj = None
        for npc_obj in npcs_in_room:
            # Get NPC data from world manager using the NPC object's ID
            npc_data = self.game_engine.world_manager.get_npc_data(npc_obj.npc_id)
            print(f"[HEAL DEBUG] Checking NPC {npc_obj.npc_id}: {npc_data}")
            if npc_data:
                print(f"[HEAL DEBUG] NPC services: {npc_data.get('services', [])}")
                if 'healer' in npc_data.get('services', []):
                    healer_npc = npc_data
                    healer_obj = npc_obj
                    break

        if not healer_npc:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "There is no healer here. You must find a temple or healer to receive healing."
            )
            return

        # Show healing options if "list" or list available healing
        if params.lower() in ['list', 'options', 'help']:
            healing_options = healer_npc.get('healing', {})
            if not healing_options:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    f"{healer_obj.name} doesn't seem to offer healing services."
                )
                return

            message = f"\n{healer_obj.name} offers the following healing services:\n\n"
            for heal_type, heal_data in healing_options.items():
                heal_amount = heal_data.get('heal_amount', 0)
                if heal_amount == 'full':
                    heal_desc = "Full Health"
                else:
                    heal_desc = f"{heal_amount} HP"
                message += f"  {heal_data['name']:20} - {heal_desc:12} ({heal_data['cost']} gold)\n"
            message += f"\nUse 'heal <type>' to receive healing. Example: heal minor"

            await self.game_engine.connection_manager.send_message(player_id, message)
            return

        # Find matching heal type
        healing_options = healer_npc.get('healing', {})
        heal_type = None
        for key in healing_options.keys():
            if params.lower() in key.lower() or key.lower().startswith(params.lower()):
                heal_type = key
                break

        if not heal_type:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"I don't recognize that healing type. Use 'heal list' to see available options."
            )
            return

        heal_data = healing_options[heal_type]
        cost = heal_data['cost']
        heal_amount = heal_data['heal_amount']

        # Check if player has enough gold
        player_gold = character.get('gold', 0)
        if player_gold < cost:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"You don't have enough gold. {heal_data['name']} costs {cost} gold, but you only have {player_gold} gold."
            )
            return

        # Check if player needs healing
        current_health = character.get('current_hit_points', 0)
        max_health = character.get('max_hit_points', current_health)

        if current_health >= max_health:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "You are already at full health!"
            )
            return

        # Apply healing
        if heal_amount == 'full':
            actual_heal = max_health - current_health
            character['current_hit_points'] = max_health
        else:
            actual_heal = min(heal_amount, max_health - current_health)
            character['current_hit_points'] = min(current_health + heal_amount, max_health)

        # Deduct gold
        character['gold'] = player_gold - cost

        # Send message
        await self.game_engine.connection_manager.send_message(
            player_id,
            service_message(f"{healer_obj.name} channels healing energy into you. You are healed for {int(actual_heal)} HP!\nYou paid {cost} gold.\n\nHealth: {int(character['current_hit_points'])} / {int(max_health)}")
        )
