"""Command handler for processing player commands."""

import asyncio
import random
import json
import time
from typing import Optional, Dict, Any, Tuple
from ..utils.colors import (
    service_message, item_found, error_message,
    info_message, success_message, announcement,
    Colors, wrap_color
)


class CommandHandler:
    """Handles parsing and execution of player commands."""

    def __init__(self, game_engine):
        """Initialize the command handler with reference to the game engine.

        Args:
            game_engine: The AsyncGameEngine instance this handler belongs to
        """
        self.game_engine = game_engine
        self.logger = game_engine.logger

        # Initialize handler modules
        from .handlers.map_handler import MapCommandHandler
        from .handlers.admin_handler import AdminCommandHandler
        from .handlers.quest_handler import QuestCommandHandler
        from .handlers.character_handler import CharacterCommandHandler
        from .handlers.inventory_handler import InventoryCommandHandler
        from .handlers.item_usage_handler import ItemUsageCommandHandler
        from .handlers.vendor_handler import VendorCommandHandler
        from .handlers.combat_handler import CombatCommandHandler
        from .handlers.world_handler import WorldCommandHandler
        from .handlers.auth_handler import AuthCommandHandler
        from .handlers.magic_handler import MagicCommandHandler
        from .handlers.ability_handler import AbilityCommandHandler
        from .handlers.party_handler import PartyCommandHandler
        self.map_handler = MapCommandHandler(game_engine)
        self.admin_handler = AdminCommandHandler(game_engine)
        self.quest_handler = QuestCommandHandler(game_engine)
        self.character_handler = CharacterCommandHandler(game_engine)
        self.inventory_handler = InventoryCommandHandler(game_engine)
        self.item_usage_handler = ItemUsageCommandHandler(game_engine)
        self.vendor_handler = VendorCommandHandler(game_engine)
        self.combat_handler = CombatCommandHandler(game_engine)
        self.world_handler = WorldCommandHandler(game_engine)
        self.auth_handler = AuthCommandHandler(game_engine)
        self.magic_handler = MagicCommandHandler(game_engine)
        self.ability_handler = AbilityCommandHandler(game_engine)
        self.party_handler = PartyCommandHandler(game_engine)

        # Give ability_handler access to combat_handler for attack routing
        self.ability_handler.combat_handler = self.combat_handler

    async def handle_player_command(self, player_id: int, command: str, params: str):
        """Handle a command from a player.

        Entry point for all player commands - routes to login, character creation, or game commands.
        """
        if not self.game_engine.player_manager.is_player_connected(player_id):
            return

        # Handle command asynchronously
        asyncio.create_task(self._process_player_command(player_id, command, params))

    async def _process_player_command(self, player_id: int, command: str, params: str):
        """Process a player command asynchronously.

        Routes commands based on player state (login, character creation, or in-game).
        """
        player_data = self.game_engine.player_manager.get_player_data(player_id)

        # Handle character creation (even if authenticated)
        if player_data.get('creating_character'):
            await self.auth_handler.handle_character_creation_input(player_id, command)
            return

        # Handle login process
        if not player_data.get('authenticated'):
            await self.auth_handler.handle_login_process(player_id, command, params)
            return

        # Handle game commands
        await self._handle_game_command(player_id, command, params)

    async def _handle_game_command(self, player_id: int, command: str, params: str):
        """Handle a game command from an authenticated player."""
        player_data = self.game_engine.player_manager.get_player_data(player_id)
        if not player_data or not player_data.get('character'):
            return

        # Handle commands directly like the simple server
        original_command = f"{command} {params}".strip()
        full_command = f"{command} {params}".strip().lower()
        character = player_data['character']

        # Empty command refreshes the basic UI
        if not command:
            # Just show the basic room description
            await self.game_engine._send_room_description(player_id, detailed=False)
            return

        if command in ['quit', 'q']:
            await self.game_engine.connection_manager.send_message(player_id, "Goodbye!")
            await self.game_engine.connection_manager.disconnect_player(player_id)
            return

        elif command in ['look', 'l']:
            if params:
                # Check if params is a direction first
                await self.world_handler.handle_look_command(player_id, params)
            else:
                # Look around the room
                await self.game_engine._send_room_description(player_id, detailed=True)

        elif command == 'gaze' and params:
            # Handle special room actions like "gaze mirror"
            await self.world_handler.handle_special_action(player_id, command, params)

        elif command in ['map', 'worldmap']:
            # Show map of areas and rooms
            await self.map_handler.handle_map_command(player_id, character, params)

        elif command in ['help', '?']:
            help_text = """
Available Commands:
==================
look (l)           - Look around or examine target
gaze <target>      - Gaze at a target for detailed examination
help (?)           - Show this help
exits (ex)         - Show exits
map [area]         - Show world map or detailed area map

Character Info:
==============
stats (st)         - Show character stats
health (he)        - Show hit points, mana, and status
experience (xp)    - Show level, experience, and rune
inventory (inv,i)  - Show inventory
spellbook (sb)     - Show learned spells
unlearn <spell>    - Remove a spell from your spellbook (forget)
reroll             - Reroll stats (level 1, 0 XP only)
train              - Level up at a trainer

Items & Equipment:
=================
get <item>         - Pick up an item
drop <item>        - Drop an item
eat <item>         - Eat food
drink <item>       - Drink beverage (dr, quaff)
read <item>        - Read a scroll to learn a spell (study)
equip <item>       - Equip weapon or armor (eq)
unequip <item>     - Unequip weapon or armor
put <item>         - Put item in container (store, stow)
ring <item>        - Manage rings (ri)
light <item>       - Light a torch, lantern, or candle (ignite)
extinguish <item>  - Extinguish a light source (douse, snuff)
fill <item>        - Fill a lantern with lamp oil (refill)

Traps & Locks:
=============
search             - Search for traps in current room (detect)
disarm             - Disarm a detected trap (disable)

Vendors & Services:
==================
list               - Show vendor wares (wares)
buy <item>         - Buy from vendor (b)
sell <item>        - Sell to vendor
rent/rest          - Rent a room at inn (restores HP/MP, cost scales with level)
heal               - Receive healing from healer (if available)

Combat Commands:
===============
attack <target>    - Attack a target (att, a, kill)
cast <spell>       - Cast a spell (c)
shoot <target>     - Shoot with ranged weapon (fire, sh)
retrieve           - Retrieve spent ammunition (recover, gather)
flee               - Try to flee from combat (run)

Quests & NPCs:
=============
quest              - Show quest log (quests, questlog)
talk <npc>         - Talk to an NPC (speak)
accept <quest>     - Accept a quest from NPC
abandon <quest>    - Abandon a quest

Movement:
=========
north (n)          - Go north
south (s)          - Go south
east (e)           - Go east
west (w)           - Go west
northeast (ne)     - Go northeast
northwest (nw)     - Go northwest
southeast (se)     - Go southeast
southwest (sw)     - Go southwest
up (u)             - Go up
down (d)           - Go down
buy passage        - Buy passage across the great lake (requires rune, 100 gold)

Party System:
============
party              - Show party members and their status
join <player>      - Request to join a player's party
accept <player>    - Accept a player's join request
leave              - Leave your current party
add <player>       - Add a player to your party (leader only)
remove <player>    - Remove a player from party (leader only)
appoint <player>   - Transfer party leadership to another member
disband            - Disband the party (leader only)
follow <player>    - Follow a player's movements
follow             - Stop following

Class Abilities:
===============
Rogue:
  picklock         - Pick a locked door
  backstab         - Next attack deals massive damage
  shadow_step      - Become harder to hit for a duration
  poison_blade     - Poison your weapon for multiple attacks

Fighter:
  power_attack     - Next attack deals more damage but less accurate
  cleave           - Attack multiple enemies at once
  dual_wield       - Fight with two weapons
  shield_bash      - Bash with shield to stun enemy
  battle_cry       - Boost damage for a duration

Ranger:
  track            - Track creatures in nearby rooms
  tame <creature>  - Tame a creature as a companion
  pathfind <dest>  - Find path to destination
  forage           - Search for food and supplies
  camouflage       - Hide from enemies
  multishot        - Fire arrows at multiple targets
  call_of_the_wild - Summon a wild companion

System:
======
quit (q)           - Quit the game

Admin Commands (Debug):
======================
givegold <amt>     - Give yourself gold
giveitem <id>      - Give yourself an item
givexp <amt>       - Give yourself experience
setstat <stat> <n> - Set a stat (str/dex/con/vit/int/wis/cha)
setlevel <level>   - Set your level (auto-adjusts HP/mana)
sethealth <hp>     - Set health (or 'sethealth full')
setmana <mana>     - Set mana (or 'setmana full')
godmode            - Toggle god mode (99 stats, level 50, 9999 HP/mana)
condition <type>   - Apply condition: poison, hungry, thirsty, starving, dehydrated, paralyzed
mobstatus          - Show all mobs and their flags
teleport <room>    - Teleport to a room (or 'teleport <player> <room>')
respawnnpc <id>    - Respawn an NPC
completequest <id> - Mark a quest as complete
"""
            await self.game_engine.connection_manager.send_message(player_id, help_text)

        elif command in ['exits', 'ex']:
            exits = self.game_engine.world_manager.get_exits_from_room(character['room_id'])
            if exits:
                await self.game_engine.connection_manager.send_message(player_id, f"Available exits: {', '.join(exits.keys())}")
            else:
                await self.game_engine.connection_manager.send_message(player_id, "No exits available.")

        elif command in ['stats', 'score', 'st']:
            await self.character_handler.handle_stats_command(player_id, character)

        elif command in ['health', 'he']:
            await self.character_handler.handle_health_command(player_id, character)

        elif command in ['experience', 'xp']:
            await self.character_handler.handle_experience_command(player_id, character)

        elif command == 'reroll':
            await self.character_handler.handle_reroll_command(player_id, character)

        elif command == 'train':
            await self.character_handler.handle_train_command(player_id, character)

        elif command in ['inventory', 'inv', 'i']:
            await self.inventory_handler.handle_inventory_command(player_id, character)

        elif command in ['spellbook', 'spells', 'sb']:
            await self.magic_handler.handle_spellbook_command(player_id, character)

        elif command in ['unlearn', 'forget'] and params:
            await self.magic_handler.handle_unlearn_spell_command(player_id, character, params)

        elif command in ['unlearn', 'forget']:
            await self.game_engine.connection_manager.send_message(player_id, "Unlearn what spell? Use 'spellbook' to see your spells.")

        elif command in ['cast', 'c'] and params:
            await self.magic_handler.handle_cast_command(player_id, character, params)

        elif command in ['cast', 'c']:
            await self.game_engine.connection_manager.send_message(player_id, "Cast what spell? Use 'spellbook' to see your spells.")

        elif command == 'get' and params:
            # Pick up an item from the room
            await self.inventory_handler.handle_get_item(player_id, params)

        elif command == 'get':
            # Get command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to get?")

        elif command == 'drop' and params:
            # Drop an item from inventory
            await self.inventory_handler.handle_drop_item(player_id, params)

        elif command == 'drop':
            # Drop command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to drop?")

        elif command in ['eat', 'consume'] and params:
            # Eat food to restore hunger
            await self.item_usage_handler.handle_eat_command(player_id, params)

        elif command in ['eat', 'consume']:
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to eat?")

        elif command in ['drink', 'dr', 'quaff'] and params:
            # Drink to restore thirst
            await self.item_usage_handler.handle_drink_command(player_id, params)

        elif command in ['drink', 'dr', 'quaff']:
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to drink?")

        elif command in ['read', 'study'] and params:
            # Read a scroll to learn a spell
            await self.item_usage_handler.handle_read_command(player_id, params)

        elif command in ['read', 'study']:
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to read?")

        elif command in ['equip', 'eq'] and params:
            # Equip an item from inventory
            await self.inventory_handler.handle_equip_item(player_id, params)

        elif command in ['equip', 'eq']:
            # Equip command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to equip?")

        elif command == 'unequip' and params:
            # Unequip an item to inventory
            await self.inventory_handler.handle_unequip_item(player_id, params)

        elif command == 'unequip':
            # Unequip command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to unequip?")

        elif command in ['light', 'ignite'] and params:
            # Light a light source (torch, lantern, etc.)
            await self.item_usage_handler.handle_light_command(player_id, params)

        elif command in ['light', 'ignite']:
            # Light command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to light?")

        elif command in ['extinguish', 'douse', 'snuff'] and params:
            # Extinguish a lit light source
            await self.item_usage_handler.handle_extinguish_command(player_id, params)

        elif command in ['extinguish', 'douse', 'snuff']:
            # Extinguish command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to extinguish?")

        elif command in ['fill', 'refill'] and params:
            # Fill/refill a lantern with oil
            await self.item_usage_handler.handle_fill_command(player_id, params)

        elif command in ['fill', 'refill']:
            # Fill command without parameters
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to fill?")

        elif command in ['search', 'detect']:
            # Search for traps in current room
            await self.world_handler.handle_search_traps_command(player_id, character)

        elif command in ['disarm', 'disable']:
            # Disarm a detected trap
            await self.world_handler.handle_disarm_trap_command(player_id, character)

        elif command in ['buy', 'b'] and params and params.lower() in ['passage']:
            # Handle buying passage across the great lake
            await self.world_handler.handle_buy_passage(player_id, character)

        elif command in ['buy', 'b', 'sell'] and params:
            # Handle buying/selling with vendors
            await self.vendor_handler.handle_trade_command(player_id, command, params)

        elif command in ['list', 'wares']:
            # Show vendor inventory if in vendor room
            # Support "list" or "list <vendor_name>"
            await self.vendor_handler.handle_list_vendor_items(player_id, params if params else None)

        elif command in ['rent', 'rest', 'sleep']:
            # Rent a room at the inn to restore HP/MP
            await self.world_handler.handle_rent_room(player_id, character)

        elif command in ['heal', 'healing'] and params:
            # Handle healing at a temple/healer
            await self.vendor_handler.handle_heal_command(player_id, params)

        elif command in ['heal', 'healing']:
            # Show healing options
            await self.vendor_handler.handle_heal_command(player_id, "list")

        elif command in ['ring', 'ri'] and params:
            # Handle ring command for special items like the gong
            await self.world_handler.handle_ring_command(player_id, params)

        elif command in ['ring', 'ri'] and not params:
            await self.game_engine.connection_manager.send_message(player_id, "What would you like to ring?")

        elif command in ['put', 'store', 'stow'] and params:
            # Put item in container
            await self.inventory_handler.handle_put_command(player_id, character, params)

        elif command in ['put', 'store', 'stow']:
            await self.game_engine.connection_manager.send_message(player_id, "Usage: put <item> in <container>")

        # Combat commands
        elif command in ['attack', 'att', 'a', 'kill']:
            if not params:
                await self.game_engine.connection_manager.send_message(player_id, "Attack what?")
            else:
                await self.combat_handler.handle_attack_command(player_id, params)

        elif command in ['shoot', 'fire', 'sh']:
            if not params:
                await self.game_engine.connection_manager.send_message(player_id, "Shoot what?")
            else:
                await self.combat_handler.handle_shoot_command(player_id, params)

        elif command in ['retrieve', 'recover', 'gather']:
            # Retrieve spent ammunition (arrows, bolts, etc.)
            await self.combat_handler.handle_retrieve_ammo(player_id)

        elif command in ['flee', 'run']:
            await self.combat_handler.handle_flee_command(player_id)

        elif command in ['north', 'n', 'south', 's', 'east', 'e', 'west', 'w',
                        'northeast', 'ne', 'northwest', 'nw', 'southeast', 'se',
                        'southwest', 'sw', 'up', 'u', 'down', 'd']:
            await self.game_engine._move_player(player_id, command)

        # Quest commands
        elif command in ['quest', 'quests', 'questlog']:
            await self.quest_handler.handle_quest_log(player_id, character)

        elif command in ['talk', 'speak'] and params:
            await self.quest_handler.handle_talk_to_npc(player_id, character, params)

        elif command in ['talk', 'speak']:
            await self.game_engine.connection_manager.send_message(player_id, "Who would you like to talk to?")

        elif command == 'accept' and params:
            # Check if this is a party join request first
            if 'party_join_requests' in character and character['party_join_requests']:
                # Try to accept as party request
                await self.party_handler.handle_accept_command(player_id, character, params)
            else:
                # Fall back to quest acceptance
                await self.quest_handler.handle_accept_quest(player_id, character, params)

        elif command == 'accept':
            await self.game_engine.connection_manager.send_message(player_id, "What quest or party join request would you like to accept?")

        elif command in ['abandon', 'drop'] and params:
            await self.quest_handler.handle_abandon_quest(player_id, character, params)

        elif command in ['abandon', 'drop']:
            await self.game_engine.connection_manager.send_message(player_id, "What quest would you like to abandon? Usage: abandon <quest_id>")

        # Party commands
        elif command == 'party':
            await self.party_handler.handle_party_command(player_id, character)

        elif command == 'join' and params:
            await self.party_handler.handle_join_command(player_id, character, params)

        elif command == 'join':
            await self.game_engine.connection_manager.send_message(player_id, "Who do you want to join? Usage: join <player_name>")

        elif command == 'leave':
            await self.party_handler.handle_leave_command(player_id, character)

        elif command == 'add' and params:
            await self.party_handler.handle_add_command(player_id, character, params)

        elif command == 'add':
            await self.game_engine.connection_manager.send_message(player_id, "Who do you want to add to your party? Usage: add <player_name>")

        elif command == 'remove' and params:
            await self.party_handler.handle_remove_command(player_id, character, params)

        elif command == 'remove':
            await self.game_engine.connection_manager.send_message(player_id, "Who do you want to remove from your party? Usage: remove <player_name>")

        elif command == 'appoint' and params:
            await self.party_handler.handle_appoint_command(player_id, character, params)

        elif command == 'appoint':
            await self.game_engine.connection_manager.send_message(player_id, "Who do you want to appoint as party leader? Usage: appoint <player_name>")

        elif command == 'disband':
            await self.party_handler.handle_disband_command(player_id, character)

        elif command == 'follow' and params:
            await self.party_handler.handle_follow_command(player_id, character, params)

        elif command == 'follow':
            await self.party_handler.handle_follow_command(player_id, character, None)

        # Admin commands
        elif command == 'givegold' and params:
            await self.admin_handler.handle_admin_give_gold(player_id, character, params)

        elif command == 'givegold':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: givegold <amount>")

        elif command == 'giveitem' and params:
            await self.admin_handler.handle_admin_give_item(player_id, character, params)

        elif command == 'giveitem':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: giveitem <item_id>")

        elif command == 'givexp' and params:
            await self.admin_handler.handle_admin_give_xp(player_id, character, params)

        elif command == 'givexp':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: givexp <amount>")

        elif command == 'respawnnpc' and params:
            await self.admin_handler.handle_admin_respawn_npc(player_id, character, params)

        elif command == 'respawnnpc':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: respawnnpc <npc_id>")

        elif command == 'mobstatus':
            await self.admin_handler.handle_admin_mob_status(player_id)

        elif command == 'teleport' and params:
            await self.admin_handler.handle_admin_teleport(player_id, character, params)

        elif command == 'teleport':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: teleport <room_id> OR teleport <player_name> <room_id>")

        elif command == 'setstat' and params:
            await self.admin_handler.handle_admin_set_stat(player_id, character, params)

        elif command == 'setstat':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: setstat <stat_name> <value>\nStats: strength, dexterity, constitution, vitality, intellect, wisdom, charisma")

        elif command == 'setlevel' and params:
            await self.admin_handler.handle_admin_set_level(player_id, character, params)

        elif command == 'setlevel':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: setlevel <level>")

        elif command == 'setmana' and params:
            await self.admin_handler.handle_admin_set_mana(player_id, character, params)

        elif command == 'setmana':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: setmana <current> [max] OR setmana full")

        elif command == 'sethealth' and params:
            await self.admin_handler.handle_admin_set_health(player_id, character, params)

        elif command == 'sethealth':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: sethealth <current> [max] OR sethealth full")

        elif command in ['godmode', 'god']:
            await self.admin_handler.handle_admin_god_mode(player_id, character)

        elif command == 'condition' and params:
            await self.admin_handler.handle_admin_condition_command(player_id, character, params)

        elif command == 'condition':
            await self.game_engine.connection_manager.send_message(player_id, "Usage: condition <type>\nTypes: poison, hungry, thirsty, starving, dehydrated, paralyzed")

        else:
            # Check if this is a class ability command
            ability = self.game_engine.ability_system.get_ability_by_command(character, command)
            if ability:
                # Execute the ability
                await self.ability_handler.handle_ability_command(player_id, character, ability, params)
            else:
                # Treat unknown commands as speech/chat messages
                username = player_data.get('username', 'Someone')
                room_id = character.get('room_id')

                # Broadcast message to others in the room
                await self.game_engine._notify_room_except_player(room_id, player_id, f"From {username}: {original_command}\n")

                # Confirm to sender
                await self.game_engine.connection_manager.send_message(player_id, "-- Message sent --")















