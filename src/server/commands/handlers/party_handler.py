"""Party Command Handler

Handles commands for party management and cooperation:
- party - View party members and their stats
- join - Request to join another player's party
- leave - Leave current party
- add - Add member to party (leader only)
- remove - Remove member from party (leader only)
- appoint - Transfer leadership (leader only)
- disband - Dissolve the party (leader only)
- follow - Follow another player's movements
"""

from ..base_handler import BaseCommandHandler
from ...utils.colors import error_message, success_message, info_message


class PartyCommandHandler(BaseCommandHandler):
    """Handler for party and group commands."""

    async def handle_party_command(self, player_id: int, character: dict):
        """Display current party composition and member stats.

        Usage: party
        """
        party_leader_id = character.get('party_leader', player_id)

        # Check if player is in a party
        if party_leader_id == player_id and not character.get('party_members'):
            await self.send_message(
                player_id,
                error_message("Sorry, you are not a member of any party.")
            )
            return

        # Get party leader's data - use actual reference from connected_players
        if party_leader_id == player_id:
            leader_data = character
        else:
            leader_player_data = self.game_engine.player_manager.connected_players.get(party_leader_id)
            if not leader_player_data or not leader_player_data.get('character'):
                await self.send_message(
                    player_id,
                    error_message("Your party leader is not found. Party data may be corrupted.")
                )
                return
            leader_data = leader_player_data['character']

        # Get party members
        party_members = leader_data.get('party_members', [party_leader_id])
        if party_leader_id not in party_members:
            party_members.insert(0, party_leader_id)

        # Build party display
        lines = ["Your party currently consists of:"]
        player_room = character.get('room_id')

        # Display player members
        for member_id in party_members:
            # Get member data - use actual reference from connected_players
            if member_id == player_id:
                member_char = character
            else:
                member_player_data = self.game_engine.player_manager.connected_players.get(member_id)
                if not member_player_data or not member_player_data.get('character'):
                    continue
                member_char = member_player_data['character']

            # Only show stats if member is in same room
            member_room = member_char.get('room_id')
            if member_room == player_room:
                # Calculate vitality percentage
                current_hp = member_char.get('current_hit_points', 0)
                max_hp = member_char.get('max_hit_points', 1)
                vitality_percent = int((current_hp / max_hp) * 100) if max_hp > 0 else 0

                # Get status
                status = self._get_player_status(member_char, player_room)

                # Format member line
                leader_mark = "(L)" if member_id == party_leader_id else "   "
                name = member_char.get('name', 'Unknown')

                lines.append(
                    f"{name:30} {leader_mark} [HE:{vitality_percent}% ST:{status}]"
                )

        # Display summoned members (if any)
        summoned_members = leader_data.get('summoned_party_members', [])
        if summoned_members:
            # Find summons in the player's room
            room_mobs = self.game_engine.room_mobs.get(player_room, [])
            for mob in room_mobs:
                summon_id = mob.get('summon_instance_id')
                if summon_id and summon_id in summoned_members:
                    # Calculate vitality percentage
                    current_hp = mob.get('health', 0)
                    max_hp = mob.get('max_health', 1)
                    vitality_percent = int((current_hp / max_hp) * 100) if max_hp > 0 else 0

                    # Summons are always standing unless in combat
                    status = "standing"
                    if player_room in self.game_engine.combat_system.active_combats:
                        combat = self.game_engine.combat_system.active_combats[player_room]
                        if mob in combat.get('mobs', []):
                            status = "fighting"

                    # Format summon line
                    name = mob.get('name', 'Unknown summon')
                    lines.append(
                        f"{name:30} (S) [HE:{vitality_percent}% ST:{status}]"
                    )

        await self.send_message(player_id, "\n".join(lines))

    async def handle_join_command(self, player_id: int, character: dict, target_name: str):
        """Request to join another player's party.

        Usage: join <player_name>
        """
        if not target_name:
            await self.send_message(
                player_id,
                error_message("Join whom? Usage: join <player_name>")
            )
            return

        # Check if player is already in a party
        party_leader_id = character.get('party_leader', player_id)
        if party_leader_id != player_id:
            # Player is a member of another party
            await self.send_message(
                player_id,
                error_message("You must leave your current party before joining another.")
            )
            return

        # Check if player is a leader with members
        party_members = character.get('party_members', [player_id])
        if len(party_members) > 1:
            # Player is a leader with other members
            await self.send_message(
                player_id,
                error_message("You must disband your party before joining another.")
            )
            return

        # Find target player
        room_id = character.get('room_id')
        target_player = self._find_player_in_room(room_id, target_name)

        if not target_player:
            await self.send_message(
                player_id,
                error_message(f"You don't see '{target_name}' here.")
            )
            return

        target_id = target_player['player_id']
        target_char = target_player['character']

        # Cannot join yourself
        if target_id == player_id:
            await self.send_message(
                player_id,
                error_message("You cannot join your own party.")
            )
            return

        # Check if target is a party leader (or solo)
        target_leader_id = target_char.get('party_leader', target_id)
        if target_leader_id != target_id:
            # Target is a member of someone else's party
            await self.send_message(
                player_id,
                error_message(f"{target_char.get('name')} is not a party leader. You must join their leader instead.")
            )
            return

        # Check if already in target's party
        target_party_members = target_char.get('party_members', [target_id])
        if player_id in target_party_members:
            await self.send_message(
                player_id,
                error_message(f"You are already in {target_char.get('name')}'s party.")
            )
            return

        # Add join request to target
        if 'party_join_requests' not in target_char:
            target_char['party_join_requests'] = []

        if player_id not in target_char['party_join_requests']:
            target_char['party_join_requests'].append(player_id)

        # Notify both players
        await self.send_message(
            player_id,
            success_message(f"You request to join {target_char.get('name')}'s party.")
        )
        await self.send_message(
            target_id,
            info_message(f"{character.get('name')} requests to join your party. Type 'accept {character.get('name')}' to allow.")
        )

    async def handle_accept_command(self, player_id: int, character: dict, target_name: str):
        """Accept a player's request to join your party.

        Usage: accept <player_name>
        """
        if not target_name:
            await self.send_message(
                player_id,
                error_message("Accept whom? Usage: accept <player_name>")
            )
            return

        # Find target in join requests
        join_requests = character.get('party_join_requests', [])

        # Find the requesting player
        requester = None
        for req_id in join_requests:
            req_player = self.player_manager.get_player_data(req_id)
            if req_player and req_player.get('character'):
                req_char = req_player['character']
                if req_char.get('name', '').lower() == target_name.lower():
                    requester = req_player
                    requester['player_id'] = req_id
                    break

        if not requester:
            await self.send_message(
                player_id,
                error_message(f"{target_name} has not requested to join your party.")
            )
            return

        requester_id = requester['player_id']
        requester_char = requester['character']

        # Remove from join requests
        join_requests.remove(requester_id)

        # Add to party
        await self._add_to_party(player_id, character, requester_id, requester_char)

        # Notify
        await self.send_message(
            player_id,
            success_message(f"You have added {requester_char.get('name')} to your party.")
        )
        await self.send_message(
            requester_id,
            success_message(f"You have joined {character.get('name')}'s party.")
        )

    async def handle_leave_command(self, player_id: int, character: dict):
        """Leave current party.

        Usage: leave
        """
        party_leader_id = character.get('party_leader', player_id)

        # Check if player is the leader
        if party_leader_id == player_id and character.get('party_members'):
            await self.send_message(
                player_id,
                error_message("You must appoint a new leader or disband the party first.")
            )
            return

        # Check if actually in a party
        if party_leader_id == player_id:
            await self.send_message(
                player_id,
                error_message("You are not in a party.")
            )
            return

        # Remove from leader's party
        leader_data = self.player_manager.get_player_character(party_leader_id)
        if leader_data and 'party_members' in leader_data:
            if player_id in leader_data['party_members']:
                leader_data['party_members'].remove(player_id)

        # Make self the leader
        character['party_leader'] = player_id
        if 'party_members' in character:
            del character['party_members']

        # Stop following if following anyone
        if character.get('following'):
            await self._stop_following(player_id, character)

        # Notify
        await self.send_message(
            player_id,
            success_message("You have left the party.")
        )

        # Notify party
        await self._notify_party(
            party_leader_id,
            info_message(f"{character.get('name')} has left the party."),
            exclude_ids=[player_id]
        )

    async def handle_add_command(self, player_id: int, character: dict, target_name: str):
        """Add a member to your party (leader only).

        Usage: add <player_name>
        """
        # Check if player is leader
        if character.get('party_leader', player_id) != player_id:
            await self.send_message(
                player_id,
                error_message("Only the party leader can add members.")
            )
            return

        if not target_name:
            await self.send_message(
                player_id,
                error_message("Add whom? Usage: add <player_name>")
            )
            return

        # Find target player
        room_id = character.get('room_id')
        target_player = self._find_player_in_room(room_id, target_name)

        if not target_player:
            await self.send_message(
                player_id,
                error_message(f"You don't see '{target_name}' here.")
            )
            return

        target_id = target_player['player_id']
        target_char = target_player['character']

        # Cannot add yourself
        if target_id == player_id:
            await self.send_message(
                player_id,
                error_message("You are already the party leader.")
            )
            return

        # Check if already in party
        party_members = character.get('party_members', [player_id])
        if target_id in party_members:
            await self.send_message(
                player_id,
                error_message(f"{target_char.get('name')} is already in your party.")
            )
            return

        # Check if target is in another party
        target_leader_id = target_char.get('party_leader', target_id)
        if target_leader_id != target_id:
            # Target is a member of another party
            await self.send_message(
                player_id,
                error_message(f"{target_char.get('name')} is already in another party.")
            )
            return

        # Check if target is a leader with members
        target_party_members = target_char.get('party_members', [target_id])
        if len(target_party_members) > 1:
            # Target is a leader with other members
            await self.send_message(
                player_id,
                error_message(f"{target_char.get('name')} is leading their own party.")
            )
            return

        # Add to party
        await self._add_to_party(player_id, character, target_id, target_char)

        # Notify
        await self.send_message(
            player_id,
            success_message(f"You add {target_char.get('name')} to your party.")
        )
        await self.send_message(
            target_id,
            info_message(f"{character.get('name')} has added you to their party.")
        )
        await self._notify_party(
            player_id,
            info_message(f"{character.get('name')} has added {target_char.get('name')} to the party."),
            exclude_ids=[player_id, target_id]
        )

    async def handle_remove_command(self, player_id: int, character: dict, target_name: str):
        """Remove a member from your party (leader only).

        Usage: remove <player_name>
        """
        # Check if player is leader
        if character.get('party_leader', player_id) != player_id:
            await self.send_message(
                player_id,
                error_message("Only the party leader can remove members.")
            )
            return

        if not target_name:
            await self.send_message(
                player_id,
                error_message("Remove whom? Usage: remove <player_name>")
            )
            return

        # Find target in party
        party_members = character.get('party_members', [player_id])
        target_id = None
        target_char = None

        for member_id in party_members:
            if member_id == player_id:
                continue
            # Get the actual character reference from connected_players
            member_player_data = self.game_engine.player_manager.connected_players.get(member_id)
            if member_player_data and member_player_data.get('character'):
                member_data = member_player_data['character']
                if member_data.get('name', '').lower() == target_name.lower():
                    target_id = member_id
                    target_char = member_data
                    break

        if not target_id:
            await self.send_message(
                player_id,
                error_message(f"{target_name} is not in your party.")
            )
            return

        # Remove from party
        party_members.remove(target_id)

        # Make target their own leader
        target_char['party_leader'] = target_id
        if 'party_members' in target_char:
            del target_char['party_members']

        # Stop following if following
        if target_char.get('following'):
            await self._stop_following(target_id, target_char)

        # Notify
        await self.send_message(
            player_id,
            success_message(f"You remove {target_char.get('name')} from your party.")
        )
        await self.send_message(
            target_id,
            info_message(f"{character.get('name')} has removed you from the party.")
        )
        await self._notify_party(
            player_id,
            info_message(f"{character.get('name')} has removed {target_char.get('name')} from the party."),
            exclude_ids=[player_id, target_id]
        )

    async def handle_appoint_command(self, player_id: int, character: dict, target_name: str):
        """Transfer party leadership to another member.

        Usage: appoint <player_name>
        """
        # Check if player is leader
        if character.get('party_leader', player_id) != player_id:
            await self.send_message(
                player_id,
                error_message("Only the party leader can appoint a new leader.")
            )
            return

        if not target_name:
            await self.send_message(
                player_id,
                error_message("Appoint whom? Usage: appoint <player_name>")
            )
            return

        # Find target in party
        party_members = character.get('party_members', [player_id])
        target_id = None
        target_char = None

        for member_id in party_members:
            # Get the actual character reference from connected_players
            member_player_data = self.game_engine.player_manager.connected_players.get(member_id)
            if member_player_data and member_player_data.get('character'):
                member_data = member_player_data['character']
                if member_data.get('name', '').lower() == target_name.lower():
                    target_id = member_id
                    target_char = member_data
                    break

        if not target_id or target_id == player_id:
            await self.send_message(
                player_id,
                error_message(f"{target_name} is not in your party or is you.")
            )
            return

        # Check if in same room
        if target_char.get('room_id') != character.get('room_id'):
            await self.send_message(
                player_id,
                error_message(f"{target_char.get('name')} must be in the same room.")
            )
            return

        # Transfer leadership
        target_char['party_leader'] = target_id
        target_char['party_members'] = party_members.copy()

        # Update old leader
        character['party_leader'] = target_id
        if 'party_members' in character:
            del character['party_members']

        # Update all other members
        for member_id in party_members:
            if member_id not in [player_id, target_id]:
                # Get the actual character reference from connected_players
                member_player_data = self.game_engine.player_manager.connected_players.get(member_id)
                if member_player_data and member_player_data.get('character'):
                    member_data = member_player_data['character']
                    member_data['party_leader'] = target_id

        # Notify
        await self.send_message(
            player_id,
            success_message(f"You appoint {target_char.get('name')} as the new party leader.")
        )
        await self.send_message(
            target_id,
            success_message(f"{character.get('name')} has appointed you as the new party leader.")
        )
        await self._notify_party(
            target_id,
            info_message(f"{character.get('name')} has appointed {target_char.get('name')} as the new party leader."),
            exclude_ids=[player_id, target_id]
        )

    async def handle_disband_command(self, player_id: int, character: dict):
        """Dissolve the party (leader only).

        Usage: disband
        """
        # Check if player is leader
        if character.get('party_leader', player_id) != player_id:
            await self.send_message(
                player_id,
                error_message("Only the party leader can disband the party.")
            )
            return

        party_members = character.get('party_members', [player_id])

        if len(party_members) <= 1:
            await self.send_message(
                player_id,
                error_message("You are not in a party with other members.")
            )
            return

        # Notify all members
        await self._notify_party(
            player_id,
            info_message(f"{character.get('name')} has disbanded the party.")
        )

        # Disband party
        for member_id in party_members:
            # Get the actual character reference from connected_players
            member_player_data = self.game_engine.player_manager.connected_players.get(member_id)
            if member_player_data and member_player_data.get('character'):
                member_data = member_player_data['character']
                member_data['party_leader'] = member_id
                if 'party_members' in member_data:
                    del member_data['party_members']
                # Stop following
                if member_data.get('following'):
                    await self._stop_following(member_id, member_data)

        # Clear leader's party data
        character['party_leader'] = player_id
        if 'party_members' in character:
            del character['party_members']

    async def handle_follow_command(self, player_id: int, character: dict, target_name: str = None):
        """Follow another player or stop following.

        Usage: follow <player_name> or follow (to stop)
        """
        # Stop following if no target
        if not target_name:
            if not character.get('following'):
                await self.send_message(
                    player_id,
                    info_message("You are not following anyone.")
                )
                return

            await self._stop_following(player_id, character)
            return

        # Find target player
        room_id = character.get('room_id')
        target_player = self._find_player_in_room(room_id, target_name)

        if not target_player:
            await self.send_message(
                player_id,
                error_message(f"You don't see '{target_name}' here.")
            )
            return

        target_id = target_player['player_id']
        target_char = target_player['character']

        # Cannot follow yourself
        if target_id == player_id:
            await self.send_message(
                player_id,
                error_message("You cannot follow yourself.")
            )
            return

        # Start following
        character['following'] = target_id

        # Add to target's followers list
        if 'followers' not in target_char:
            target_char['followers'] = []
        if player_id not in target_char['followers']:
            target_char['followers'].append(player_id)

        # Notify
        await self.send_message(
            player_id,
            success_message(f"You start following {target_char.get('name')}.")
        )
        await self.send_message(
            target_id,
            info_message(f"{character.get('name')} starts following you.")
        )

    # Helper Methods

    def _get_player_status(self, character: dict, room_id: str) -> str:
        """Get player's current status for party display."""
        # Check if in combat
        if room_id in self.game_engine.combat_system.active_combats:
            combat = self.game_engine.combat_system.active_combats[room_id]
            if character.get('name') in [p.get('name') for p in combat['players']]:
                return "fighting"

        # Check for status effects
        active_effects = character.get('active_effects', [])
        for effect in active_effects:
            if effect.get('effect') == 'paralyzed':
                return "incapacitated"

        # Default to standing
        return "standing"

    def _find_player_in_room(self, room_id: str, player_name: str):
        """Find a player in the given room by name."""
        # Get all players in room
        for pid, pdata in self.game_engine.player_manager.connected_players.items():
            if not pdata.get('character'):
                continue
            char = pdata['character']
            if char.get('room_id') == room_id:
                if char.get('name', '').lower() == player_name.lower():
                    return {
                        'player_id': pid,
                        'character': char
                    }
        return None

    async def _add_to_party(self, leader_id: int, leader_char: dict, member_id: int, member_char: dict):
        """Add a member to the party."""
        # Initialize party_members if needed
        if 'party_members' not in leader_char:
            leader_char['party_members'] = [leader_id]

        # Add member
        if member_id not in leader_char['party_members']:
            leader_char['party_members'].append(member_id)

        # Set member's leader
        member_char['party_leader'] = leader_id

        # Remove member from their old party if they had one
        if 'party_members' in member_char:
            del member_char['party_members']

    async def _stop_following(self, player_id: int, character: dict):
        """Stop following the current target."""
        following_id = character.get('following')
        if not following_id:
            return

        # Remove from target's followers - get actual character reference
        target_player_data = self.game_engine.player_manager.connected_players.get(following_id)
        if target_player_data and target_player_data.get('character'):
            target_data = target_player_data['character']
            if 'followers' in target_data and player_id in target_data['followers']:
                target_data['followers'].remove(player_id)

        # Clear following
        character['following'] = None

        # Notify
        target_name = target_data.get('name', 'someone') if target_data else 'someone'
        await self.send_message(
            player_id,
            info_message(f"You stop following {target_name}.")
        )

    async def _notify_party(self, leader_id: int, message: str, exclude_ids: list = None):
        """Send a message to all party members."""
        if exclude_ids is None:
            exclude_ids = []

        # Get the actual character reference from connected_players
        leader_player_data = self.game_engine.player_manager.connected_players.get(leader_id)
        if not leader_player_data or not leader_player_data.get('character'):
            return

        leader_data = leader_player_data['character']
        party_members = leader_data.get('party_members', [leader_id])

        for member_id in party_members:
            if member_id not in exclude_ids:
                await self.send_message(member_id, message)
