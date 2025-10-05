"""Vendor System - handles all vendor-related functionality."""

import json
import yaml
import os
import glob
from typing import Optional, Dict, Any, List
from ...utils.logger import get_logger


class VendorSystem:
    """Manages vendor data, inventory, and trading operations."""

    def __init__(self, game_engine):
        """Initialize the vendor system."""
        self.game_engine = game_engine
        self.logger = get_logger()

        # Vendor management - tracks vendor data and inventory
        self.vendors: Dict[str, Dict[str, Any]] = {}  # vendor_id -> vendor data
        self.vendor_locations: Dict[str, List[str]] = {}  # room_id -> vendor_ids
        self.items_data: Dict[str, Dict[str, Any]] = {}  # item_id -> item data

    def load_vendors_and_items(self):
        """Load vendor and item data from configuration files."""
        try:
            # Use cached items data from ConfigManager instead of reloading from disk
            self.items_data = self.game_engine.config_manager.load_items()
            self.logger.info(f"Loaded {len(self.items_data)} items from YAML")

            # Load vendor data from individual NPC files only
            npc_dir = os.path.join('data', 'world', 'npcs')
            if os.path.exists(npc_dir):
                npc_files = glob.glob(os.path.join(npc_dir, '*.json'))
                for npc_file in npc_files:
                    try:
                        with open(npc_file, 'r') as f:
                            npc_data = json.load(f)
                            # Check if this NPC has vendor services or shop data
                            if (npc_data.get('services') and 'shop' in npc_data.get('services', [])) or npc_data.get('shop'):
                                self._process_npc_vendor(npc_data)
                    except Exception as e:
                        self.logger.error(f"Error loading NPC file {npc_file}: {e}")

            self.logger.info(f"Loaded {len(self.vendors)} vendors from NPC files")

            # Load vendor location mappings from world room data
            self._load_vendor_locations_from_world()

        except Exception as e:
            self.logger.error(f"Error loading vendor data: {e}")

    def _process_yaml_vendors(self, vendors_config: dict):
        """Process vendors from YAML configuration."""
        for vendor_id, vendor_data in vendors_config.items():
            self.vendors[vendor_id] = vendor_data

            # Map vendor to locations
            locations = vendor_data.get('locations', [])
            for location in locations:
                if location not in self.vendor_locations:
                    self.vendor_locations[location] = []
                self.vendor_locations[location].append(vendor_id)

    def _process_json_vendors(self, vendors_list: list):
        """Process vendors from JSON configuration."""
        for vendor_data in vendors_list:
            vendor_id = vendor_data.get('id', vendor_data.get('name', '').lower().replace(' ', '_'))
            self.vendors[vendor_id] = vendor_data

    def _process_npc_vendor(self, npc_data: dict):
        """Process an NPC that has vendor services."""
        vendor_id = npc_data.get('id')
        if vendor_id:
            shop_data = npc_data.get('shop', {})
            buy_rate = shop_data.get('buy_rate', 0.5)
            sell_markup = shop_data.get('sell_markup', shop_data.get('sell_rate', 1.2))

            # Create vendor entry from NPC data
            self.vendors[vendor_id] = {
                'id': vendor_id,
                'name': npc_data.get('name', vendor_id),
                'description': npc_data.get('long_description', npc_data.get('short_description', '')),
                'keywords': npc_data.get('keywords', []),
                'dialogue': npc_data.get('dialogue', {}),
                'services': npc_data.get('services', []),
                'shop_type': shop_data.get('type', 'general'),
                'specialties': shop_data.get('specialties', []),
                'inventory': shop_data.get('inventory', []),
                'buy_rate': buy_rate,
                'sell_markup': sell_markup
            }

    def _load_vendor_locations_from_world(self):
        """Load vendor location mappings from world room data."""
        try:
            # Clear existing location mappings to rebuild from world data
            self.vendor_locations.clear()
            self.logger.info(f"[VENDOR DEBUG] Starting vendor location loading from world data")
            self.logger.info(f"[VENDOR DEBUG] Available vendors before mapping: {list(self.vendors.keys())}")

            # Load room data from world/rooms directory
            rooms_dir = os.path.join('data', 'world', 'rooms')
            self.logger.info(f"[VENDOR DEBUG] Looking for rooms in directory: {rooms_dir}")

            if os.path.exists(rooms_dir):
                room_files = glob.glob(os.path.join(rooms_dir, '*.json'))
                self.logger.info(f"[VENDOR DEBUG] Found {len(room_files)} room files: {[os.path.basename(f) for f in room_files]}")

                for room_file in room_files:
                    try:
                        with open(room_file, 'r') as f:
                            room_data = json.load(f)
                            room_id = room_data.get('id')
                            npcs = room_data.get('npcs', [])

                            self.logger.info(f"[VENDOR DEBUG] Processing room file {os.path.basename(room_file)}: room_id='{room_id}', npcs={npcs}")

                            if room_id and npcs:
                                # Check each NPC to see if it's a vendor
                                for npc_id in npcs:
                                    if npc_id in self.vendors:
                                        # Map this vendor to this room
                                        if room_id not in self.vendor_locations:
                                            self.vendor_locations[room_id] = []
                                        self.vendor_locations[room_id].append(npc_id)
                                        self.logger.info(f"[VENDOR DEBUG] Mapped vendor '{npc_id}' to room '{room_id}'")
                                    else:
                                        self.logger.info(f"[VENDOR DEBUG] NPC '{npc_id}' in room '{room_id}' is not a vendor")

                    except Exception as e:
                        self.logger.error(f"Error loading room file {room_file}: {e}")

                self.logger.info(f"Loaded vendor locations for {len(self.vendor_locations)} rooms from world data")
                self.logger.info(f"[VENDOR DEBUG] Final vendor_locations mapping: {dict(self.vendor_locations)}")

            else:
                self.logger.warning(f"World rooms directory not found at {rooms_dir}")

        except Exception as e:
            self.logger.error(f"Error loading vendor locations from world data: {e}")

    def get_vendors_in_room(self, room_id: str) -> list:
        """Get all vendors available in a specific room."""
        vendors = []

        # Check vendors mapped to this room from world data
        vendor_ids = self.vendor_locations.get(room_id, [])
        for vendor_id in vendor_ids:
            if vendor_id in self.vendors:
                vendors.append(self.vendors[vendor_id])

        return vendors

    def find_vendor_by_name(self, room_id: str, vendor_name: str) -> dict:
        """Find a vendor by name in the specified room."""
        vendors = self.get_vendors_in_room(room_id)

        vendor_name_lower = vendor_name.lower()
        for vendor in vendors:
            name = vendor.get('name', '').lower()
            if vendor_name_lower in name or name in vendor_name_lower:
                return vendor

        return None

    def get_vendor_in_room(self, room_id: str):
        """Get vendor data for the current room from loaded NPCs."""
        self.logger.info(f"[VENDOR DEBUG] get_vendor_in_room called with room_id: '{room_id}'")
        self.logger.info(f"[VENDOR DEBUG] Current vendor_locations mapping: {dict(self.vendor_locations)}")
        self.logger.info(f"[VENDOR DEBUG] Available vendors: {list(self.vendors.keys())}")

        # Use the room-based vendor location mapping
        vendors_in_room = self.get_vendors_in_room(room_id)
        self.logger.info(f"[VENDOR DEBUG] Vendors found in room '{room_id}': {[v.get('name', 'unnamed') for v in vendors_in_room]}")

        # Return the first vendor that has a shop (for backwards compatibility)
        for vendor in vendors_in_room:
            self.logger.info(f"[VENDOR DEBUG] Checking vendor {vendor.get('name', 'unnamed')}")
            self.logger.info(f"[VENDOR DEBUG] Vendor keys: {list(vendor.keys())}")
            self.logger.info(f"[VENDOR DEBUG] Has inventory: {bool(vendor.get('inventory'))}")
            if vendor.get('inventory'):
                self.logger.info(f"[VENDOR DEBUG] Inventory: {vendor.get('inventory')}")
                self.logger.info(f"[VENDOR DEBUG] Returning vendor with shop: {vendor.get('name', 'unnamed')}")
                return vendor

        self.logger.info(f"[VENDOR DEBUG] No vendors with shops found in room '{room_id}'")
        return None

    def get_item_price(self, vendor: dict, item_id: str, buying: bool = True) -> int:
        """Get the price of an item from a vendor."""
        # Check vendor's inventory first (from YAML config)
        if 'inventory' in vendor:
            for item in vendor['inventory']:
                if item.get('item_id') == item_id:
                    return item.get('price', 0)

        # Fallback to base item price with vendor markup
        item_data = self.items_data.get(item_id, {})
        base_value = item_data.get('base_value', 10)

        if buying:
            # Player is buying from vendor
            markup = vendor.get('sell_markup', 1.2)
            return int(base_value * markup)
        else:
            # Player is selling to vendor
            buy_rate = vendor.get('buy_rate', 0.5)
            return int(base_value * buy_rate)

    def vendor_has_item(self, vendor: dict, item_id: str, quantity: int = 1) -> bool:
        """Check if vendor has the specified item in sufficient quantity."""
        if 'inventory' in vendor:
            for item in vendor['inventory']:
                if item.get('item_id') == item_id:
                    stock = item.get('stock', 0)
                    return stock == -1 or stock >= quantity  # -1 means unlimited
        return False

    def reduce_vendor_stock(self, vendor: dict, item_id: str, quantity: int):
        """Reduce vendor stock after a purchase."""
        if 'inventory' in vendor:
            for item in vendor['inventory']:
                if item.get('item_id') == item_id:
                    stock = item.get('stock', 0)
                    if stock != -1:  # -1 means unlimited
                        item['stock'] = max(0, stock - quantity)
                    break

    def find_item_by_name(self, item_name: str) -> str:
        """Find an item ID by searching item names."""
        item_name_lower = item_name.lower()

        # First try exact match on item ID
        if item_name_lower in self.items_data:
            return item_name_lower

        # Then try partial match on display names
        for item_id, item_data in self.items_data.items():
            display_name = item_data.get('name', item_id).lower()
            if item_name_lower in display_name or display_name in item_name_lower:
                return item_id

        return None

    async def handle_trade_command(self, player_id: int, action: str, item_name: str):
        """Handle buy/sell commands with vendors."""
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        # Check if there's a vendor in the room
        vendor = self.get_vendor_in_room(room_id)
        if not vendor:
            await self.game_engine.connection_manager.send_message(player_id, "There is no vendor here to trade with.")
            return

        if action == 'buy':
            await self.handle_buy_item(player_id, vendor, item_name)
        elif action == 'sell':
            await self.handle_sell_item(player_id, vendor, item_name)

    async def handle_buy_item(self, player_id: int, vendor: dict, item_name: str):
        """Handle buying an item from a vendor."""
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        character = player_data['character']

        # Find item in vendor inventory
        for item_entry in vendor['inventory']:
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config and item_config['name'].lower() == item_name.lower():
                if character['gold'] >= item_entry['price']:
                    # Try to create item from config
                    created_item = self.game_engine.config_manager.create_item_instance(item_id, item_entry['price'])

                    if not created_item:
                        # Fallback to simple item creation
                        created_item = {
                            'name': item_config['name'],
                            'weight': item_config.get('weight', 0),
                            'value': item_entry['price']
                        }

                    # Check encumbrance before buying
                    current_encumbrance = self.game_engine.player_manager.calculate_encumbrance(character)
                    item_weight = created_item.get('weight', 0)
                    max_encumbrance = self.game_engine.player_manager.calculate_max_encumbrance(character)

                    if current_encumbrance + item_weight > max_encumbrance:
                        await self.game_engine.connection_manager.send_message(
                            player_id,
                            f"You cannot carry {created_item['name']} - you are carrying too much! ({current_encumbrance + item_weight:.1f}/{max_encumbrance})"
                        )
                        return

                    # Player can afford it and can carry it
                    character['gold'] -= item_entry['price']
                    character['inventory'].append(created_item)

                    # Update encumbrance properly
                    self.game_engine.player_manager.update_encumbrance(character)

                    await self.game_engine.connection_manager.send_message(player_id,
                        f"You buy a {item_config['name']} for {item_entry['price']} gold.")
                    return
                else:
                    await self.game_engine.connection_manager.send_message(player_id,
                        f"You don't have enough gold. {item_config['name']} costs {item_entry['price']} gold.")
                    return

        await self.game_engine.connection_manager.send_message(player_id, f"The vendor doesn't have a {item_name}.")

    async def handle_sell_item(self, player_id: int, vendor: dict, item_name: str):
        """Handle selling an item to a vendor."""
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        character = player_data['character']

        # Find item in player inventory
        for i, item in enumerate(character['inventory']):
            if item['name'].lower() == item_name.lower():
                # Calculate sell price using vendor's buy rate
                item_value = item.get('value', 5)
                buy_rate = vendor.get('buy_rate', 0.5)
                sell_price = int(item_value * buy_rate)

                # Remove item from inventory
                sold_item = character['inventory'].pop(i)
                character['gold'] += sell_price

                # Update encumbrance properly
                self.game_engine.player_manager.update_encumbrance(character)

                await self.game_engine.connection_manager.send_message(player_id,
                    f"You sell your {sold_item['name']} for {sell_price} gold.")
                return

        await self.game_engine.connection_manager.send_message(player_id, f"You don't have a {item_name} to sell.")

    async def handle_list_vendor_items(self, player_id: int):
        """Show vendor inventory."""
        player_data = self.game_engine.player_manager.connected_players.get(player_id)
        if not player_data or not player_data.get('character'):
            return

        character = player_data['character']
        room_id = character.get('room_id')

        vendor = self.get_vendor_in_room(room_id)
        if not vendor:
            await self.game_engine.connection_manager.send_message(player_id, "There is no vendor here.")
            return

        inventory_text = f"{vendor['name']} has the following items for sale:\n"
        for i, item_entry in enumerate(vendor['inventory'], 1):
            item_id = item_entry['item_id']
            item_config = self.game_engine.config_manager.get_item(item_id)
            if item_config:
                item_name = item_config['name']
                price = item_entry['price']
                inventory_text += f"  {i}. {item_name} - {price} gold\n"
            else:
                inventory_text += f"  {i}. {item_id} (unknown item) - {item_entry['price']} gold\n"

        await self.game_engine.connection_manager.send_message(player_id, inventory_text)

    def handle_vendor_purchase(self, player, item_name: str, quantity: int, vendor_name: str = None) -> str:
        """Handle a player purchasing an item from a vendor."""
        try:
            room_id = player.character.room_id
            vendors = self.get_vendors_in_room(room_id)

            if not vendors:
                return "There are no vendors here."

            # Find the specified vendor or use the first available
            if vendor_name:
                vendor = self.find_vendor_by_name(room_id, vendor_name)
                if not vendor:
                    return f"There is no vendor named '{vendor_name}' here."
            else:
                vendor = vendors[0]  # Use first vendor if none specified

            # Find matching item
            item_id = self.find_item_by_name(item_name)
            if not item_id:
                return f"'{item_name}' is not available."

            # Check if vendor has the item
            if not self.vendor_has_item(vendor, item_id, quantity):
                return f"{vendor.get('name', 'The vendor')} doesn't have {quantity} {item_name}(s) in stock."

            # Calculate total cost
            item_price = self.get_item_price(vendor, item_id, buying=True)
            total_cost = item_price * quantity

            # Check if player has enough gold
            if player.character.gold < total_cost:
                return f"You need {total_cost} gold, but you only have {player.character.gold} gold."

            # Process the purchase
            player.character.gold -= total_cost
            self.reduce_vendor_stock(vendor, item_id, quantity)

            # Add item to player inventory (simplified - would integrate with actual inventory system)
            # For now, just confirm the purchase

            vendor_name = vendor.get('name', 'The vendor')
            item_display_name = self.items_data.get(item_id, {}).get('name', item_name)

            if quantity == 1:
                return f"You buy {item_display_name} from {vendor_name} for {total_cost} gold. You have {player.character.gold} gold remaining."
            else:
                return f"You buy {quantity} {item_display_name}s from {vendor_name} for {total_cost} gold. You have {player.character.gold} gold remaining."

        except Exception as e:
            self.logger.error(f"Error in vendor purchase: {e}")
            return "Something went wrong with your purchase."

    def handle_vendor_list(self, player, vendor_name: str = None) -> str:
        """Handle listing vendor inventory."""
        try:
            room_id = player.character.room_id
            vendors = self.get_vendors_in_room(room_id)

            if not vendors:
                return "There are no vendors here."

            # Find the specified vendor or use all vendors
            if vendor_name:
                vendor = self.find_vendor_by_name(room_id, vendor_name)
                if not vendor:
                    return f"There is no vendor named '{vendor_name}' here."
                vendors = [vendor]

            result = []
            for vendor in vendors:
                vendor_display_name = vendor.get('name', 'Unknown Vendor')
                result.append(f"\n=== {vendor_display_name} ===")

                if 'inventory' in vendor and vendor['inventory']:
                    for item in vendor['inventory']:
                        item_id = item.get('item_id')
                        price = item.get('price', 0)
                        stock = item.get('stock', 0)

                        if item_id in self.items_data:
                            item_name = self.items_data[item_id].get('name', item_id)
                            item_desc = self.items_data[item_id].get('description', '')
                        else:
                            item_name = item_id
                            item_desc = ''

                        stock_text = "unlimited" if stock == -1 else f"{stock} in stock"
                        result.append(f"{item_name}: {price} gold ({stock_text})")
                        if item_desc:
                            result.append(f"  {item_desc}")
                else:
                    result.append("No items available.")

            result.append(f"\nYou have {player.character.gold} gold.")
            return "\n".join(result)

        except Exception as e:
            self.logger.error(f"Error listing vendor inventory: {e}")
            return "Unable to show vendor inventory."

    def handle_vendor_sale(self, player, item_name: str, quantity: int, vendor_name: str = None) -> str:
        """Handle a player selling an item to a vendor."""
        try:
            room_id = player.character.room_id
            vendors = self.get_vendors_in_room(room_id)

            if not vendors:
                return "There are no vendors here to sell to."

            # Find the specified vendor or use the first available
            if vendor_name:
                vendor = self.find_vendor_by_name(room_id, vendor_name)
                if not vendor:
                    return f"There is no vendor named '{vendor_name}' here."
            else:
                vendor = vendors[0]  # Use first vendor if none specified

            # Find matching item
            item_id = self.find_item_by_name(item_name)
            if not item_id:
                return f"You don't have '{item_name}' to sell."

            # Check if player has the item (simplified - would integrate with actual inventory system)
            # For now, assume they have it and calculate sale price

            sale_price = self.get_item_price(vendor, item_id, buying=False)
            total_value = sale_price * quantity

            # Process the sale
            player.character.gold += total_value

            vendor_name = vendor.get('name', 'The vendor')
            item_display_name = self.items_data.get(item_id, {}).get('name', item_name)

            if quantity == 1:
                return f"You sell {item_display_name} to {vendor_name} for {total_value} gold. You now have {player.character.gold} gold."
            else:
                return f"You sell {quantity} {item_display_name}s to {vendor_name} for {total_value} gold. You now have {player.character.gold} gold."

        except Exception as e:
            self.logger.error(f"Error in vendor sale: {e}")
            return "Something went wrong with your sale."

    def handle_item_appraisal(self, player, item_name: str) -> str:
        """Handle appraising an item's value."""
        try:
            item_id = self.find_item_by_name(item_name)
            if not item_id:
                return f"'{item_name}' is not a known item."

            item_data = self.items_data.get(item_id, {})
            item_display_name = item_data.get('name', item_name)
            base_value = item_data.get('base_value', 10)

            result = [f"{item_display_name}:"]
            result.append(f"  Base value: {base_value} gold")

            # Show vendor prices if there are vendors in the room
            room_id = player.character.room_id
            vendors = self.get_vendors_in_room(room_id)

            if vendors:
                result.append("  Vendor prices:")
                for vendor in vendors:
                    vendor_name = vendor.get('name', 'Unknown Vendor')
                    buy_price = self.get_item_price(vendor, item_id, buying=True)
                    sell_price = self.get_item_price(vendor, item_id, buying=False)
                    result.append(f"    {vendor_name}: buy for {buy_price}g, sells for {sell_price}g")

            return "\n".join(result)

        except Exception as e:
            self.logger.error(f"Error in item appraisal: {e}")
            return "Unable to appraise that item."