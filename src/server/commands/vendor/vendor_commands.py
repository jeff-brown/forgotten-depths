"""Vendor interaction commands."""

from typing import List
from ..base_command import BaseCommand


class BuyCommand(BaseCommand):
    """Command to buy items from vendors."""

    def __init__(self):
        super().__init__("buy", ["purchase"])
        self.description = "Buy an item from a vendor"
        self.usage = "buy <item> [quantity] [from <vendor>]"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the buy command."""
        if not args:
            return "Buy what? Use 'list' to see available items."

        if not player.character:
            return "You need a character to buy items."

        if not player.character.room_id:
            return "You need to be somewhere to buy items."

        # Get game engine from player
        if not hasattr(player, '_game_engine'):
            return "Shopping system not available."

        game_engine = player._game_engine

        # Parse arguments
        quantity = 1
        vendor_name = None
        item_name = None

        # Simple parsing: buy <item> [<quantity>] [from <vendor>]
        i = 0
        while i < len(args):
            if args[i].lower() == "from" and i + 1 < len(args):
                vendor_name = " ".join(args[i + 1:])
                break
            elif args[i].isdigit() and item_name is not None:
                quantity = int(args[i])
            else:
                if item_name is None:
                    item_name = args[i]
                else:
                    item_name += " " + args[i]
            i += 1

        if not item_name:
            return "What would you like to buy?"

        try:
            quantity = max(1, quantity)
        except ValueError:
            quantity = 1

        return game_engine.handle_vendor_purchase(player, item_name, quantity, vendor_name)


class ListCommand(BaseCommand):
    """Command to list vendor inventory."""

    def __init__(self):
        super().__init__("list", ["shop", "wares", "goods"])
        self.description = "List items available from vendors"
        self.usage = "list [vendor]"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the list command."""
        if not player.character:
            return "You need a character to browse shops."

        if not player.character.room_id:
            return "You need to be somewhere to browse shops."

        # Get game engine from player
        if not hasattr(player, '_game_engine'):
            return "Shopping system not available."

        game_engine = player._game_engine
        vendor_name = " ".join(args) if args else None

        return game_engine.handle_vendor_list(player, vendor_name)


class SellCommand(BaseCommand):
    """Command to sell items to vendors."""

    def __init__(self):
        super().__init__("sell", ["pawn"])
        self.description = "Sell an item to a vendor"
        self.usage = "sell <item> [quantity] [to <vendor>]"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the sell command."""
        if not args:
            return "Sell what?"

        if not player.character:
            return "You need a character to sell items."

        if not player.character.room_id:
            return "You need to be somewhere to sell items."

        # Get game engine from player
        if not hasattr(player, '_game_engine'):
            return "Trading system not available."

        game_engine = player._game_engine

        # Parse arguments similar to buy command
        quantity = 1
        vendor_name = None
        item_name = None

        i = 0
        while i < len(args):
            if args[i].lower() == "to" and i + 1 < len(args):
                vendor_name = " ".join(args[i + 1:])
                break
            elif args[i].isdigit() and item_name is not None:
                quantity = int(args[i])
            else:
                if item_name is None:
                    item_name = args[i]
                else:
                    item_name += " " + args[i]
            i += 1

        if not item_name:
            return "What would you like to sell?"

        try:
            quantity = max(1, quantity)
        except ValueError:
            quantity = 1

        return game_engine.handle_vendor_sale(player, item_name, quantity, vendor_name)


class ValueCommand(BaseCommand):
    """Command to check the value of items."""

    def __init__(self):
        super().__init__("value", ["appraise", "worth"])
        self.description = "Check the value of an item"
        self.usage = "value <item>"

    def execute(self, player: 'Player', args: List[str]) -> str:
        """Execute the value command."""
        if not args:
            return "Check the value of what?"

        if not player.character:
            return "You need a character to appraise items."

        # Get game engine from player
        if not hasattr(player, '_game_engine'):
            return "Appraisal system not available."

        game_engine = player._game_engine
        item_name = " ".join(args)

        return game_engine.handle_item_appraisal(player, item_name)


def get_vendor_commands():
    """Get all vendor-related commands."""
    return [
        BuyCommand(),
        ListCommand(),
        SellCommand(),
        ValueCommand()
    ]