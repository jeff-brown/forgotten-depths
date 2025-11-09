"""Quest command handler for quest-related commands."""

from ..base_handler import BaseCommandHandler


class QuestCommandHandler(BaseCommandHandler):
    """Handles quest-related commands."""

    async def handle_quest_log(self, player_id: int, character: dict):
        """Display the player's quest log.

        Usage: quest, quests, questlog
        """
        quest_manager = self.game_engine.quest_manager
        quests = quest_manager.get_player_quests(character)

        if not quests:
            await self.send_message(player_id, "You have no active quests.")
            return

        lines = ["=== Quest Log ===\n"]

        for quest_id, quest_data in quests.items():
            quest = quest_manager.get_quest(quest_id)
            if not quest:
                continue

            status = "COMPLETED" if quest_data.get('completed', False) else "IN PROGRESS"
            rewarded = " [Rewarded]" if quest_data.get('rewarded', False) else ""

            lines.append(f"{quest['name']} ({quest_id}) - {status}{rewarded}")
            lines.append(f"  {quest.get('description', 'No description.')}")

            # Show objectives
            if 'objectives' in quest:
                lines.append("  Objectives:")
                for i, objective in enumerate(quest['objectives']):
                    obj_progress = quest_data.get('objectives', {}).get(i, {})
                    progress = obj_progress.get('progress', 0)
                    required = obj_progress.get('required', 1)
                    complete_marker = "✓" if progress >= required else " "

                    obj_desc = objective.get('description', 'Unknown objective')
                    lines.append(f"    [{complete_marker}] {obj_desc} ({progress}/{required})")

            # Show rewards if not yet rewarded
            if not quest_data.get('rewarded', False) and 'rewards' in quest:
                rewards = quest['rewards']
                reward_parts = []
                if 'experience' in rewards:
                    reward_parts.append(f"{rewards['experience']} XP")
                if 'gold' in rewards:
                    reward_parts.append(f"{rewards['gold']} gold")
                if 'rune' in rewards:
                    reward_parts.append(f"{rewards['rune']} rune")
                if reward_parts:
                    lines.append(f"  Rewards: {', '.join(reward_parts)}")

            lines.append("")

        await self.send_message(player_id, "\n".join(lines))

    async def handle_accept_quest(self, player_id: int, character: dict, params: str):
        """Accept a quest from an NPC.

        Usage: accept <quest_id>
        """
        quest_id = params.strip().lower()
        if not quest_id:
            await self.send_message(player_id, "Usage: accept <quest_id>")
            return

        quest_manager = self.game_engine.quest_manager
        quest = quest_manager.get_quest(quest_id)

        if not quest:
            await self.send_message(player_id, f"Quest '{quest_id}' not found.")
            return

        # Check if quest can be accepted
        can_accept, reason = quest_manager.can_accept_quest(character, quest_id)
        if not can_accept:
            await self.send_message(player_id, reason)
            return

        # Check if there's a quest giver NPC in the room
        room_id = character.get('room_id')
        room = self.world_manager.get_room(room_id)

        if not room:
            await self.send_message(player_id, "You can't accept quests right now.")
            return

        # Find NPC that offers this quest
        quest_giver = quest.get('quest_giver')
        npc_found = False

        if quest_giver:
            for npc in room.npcs:
                if npc.npc_id == quest_giver:
                    npc_found = True
                    break

            if not npc_found:
                await self.send_message(
                    player_id,
                    f"The quest giver for '{quest['name']}' is not here."
                )
                return

        # Accept the quest
        if quest_manager.accept_quest(character, quest_id):
            message = f"You have accepted the quest: {quest['name']}\n"
            message += f"{quest.get('description', '')}\n\n"
            message += "Objectives:\n"

            for objective in quest.get('objectives', []):
                message += f"  - {objective.get('description', 'Unknown objective')}\n"

            await self.send_message(player_id, message)

            # Notify room
            char_name = character.get('name', 'Someone')
            await self.game_engine._notify_room_except_player(
                room_id,
                player_id,
                f"{char_name} accepts a quest."
            )
        else:
            await self.send_message(player_id, "Failed to accept quest.")

    async def handle_abandon_quest(self, player_id: int, character: dict, params: str):
        """Abandon an active quest.

        Usage: abandon <quest_id>
        """
        quest_id = params.strip().lower()
        if not quest_id:
            await self.send_message(player_id, "Usage: abandon <quest_id>")
            return

        quest_manager = self.game_engine.quest_manager
        quest = quest_manager.get_quest(quest_id)

        if not quest:
            await self.send_message(player_id, f"Quest '{quest_id}' not found.")
            return

        if not quest_manager.has_quest(character, quest_id):
            await self.send_message(player_id, f"You don't have the quest '{quest['name']}'.")
            return

        # Check if quest is completed but not rewarded
        if quest_manager.is_quest_complete(character, quest_id):
            quest_data = character['quests'][quest_id]
            if not quest_data.get('rewarded', False):
                await self.send_message(
                    player_id,
                    f"You cannot abandon '{quest['name']}' - it's completed! Go claim your reward first."
                )
                return

        # Abandon the quest
        if quest_manager.abandon_quest(character, quest_id):
            await self.send_message(player_id, f"You have abandoned the quest: {quest['name']}")

            # Notify room
            room_id = character.get('room_id')
            char_name = character.get('name', 'Someone')
            await self.game_engine._notify_room_except_player(
                room_id,
                player_id,
                f"{char_name} abandons a quest."
            )
        else:
            await self.send_message(player_id, "Failed to abandon quest.")

    async def handle_talk_to_npc(self, player_id: int, character: dict, npc_name: str):
        """Talk to an NPC to interact with quests."""
        room_id = character.get('room_id')
        if not room_id:
            return

        # Get the player's current room
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            await self.game_engine.connection_manager.send_message(player_id, "You are nowhere.")
            return

        # Check if there are any NPCs in the room
        if not room.npcs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                "There is no one here to talk to."
            )
            return

        # Find NPC in the current room by partial name match
        npc_obj = None
        npc_name_lower = npc_name.lower()
        for npc in room.npcs:
            if npc_name_lower in npc.name.lower() or npc_name_lower in npc.npc_id.lower():
                npc_obj = npc
                break

        if not npc_obj:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"There is no '{npc_name}' here."
            )
            return

        # Get NPC data from world manager
        npc_data = self.game_engine.world_manager.get_npc_data(npc_obj.npc_id)

        if not npc_data:
            await self.game_engine.connection_manager.send_message(
                player_id,
                f"{npc_obj.name} has nothing to say."
            )
            return

        # Check if NPC has quests
        npc_quests = npc_data.get('quests', [])
        if not npc_quests:
            # For vendors and other NPCs, use default dialogue if available, otherwise greeting
            dialogue = npc_data.get('dialogue', {})

            # Check if this is a vendor (has a shop)
            if npc_data.get('shop') or (npc_data.get('services') and 'shop' in npc_data.get('services', [])):
                # Vendor: use default dialogue
                response = dialogue.get('default', dialogue.get('greeting', f"{npc_data['name']} has nothing to say."))
            else:
                # Regular NPC: use greeting
                response = dialogue.get('greeting', f"{npc_data['name']} has nothing to say.")

            await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{response}\"")
            return

        # Handle quest interaction
        for quest_id in npc_quests:
            quest = self.game_engine.quest_manager.get_quest(quest_id)
            if not quest:
                continue

            # Check if player has completed the quest
            if self.game_engine.quest_manager.is_quest_complete(character, quest_id):
                # Check if player has already been rewarded
                if character.get('quests', {}).get(quest_id, {}).get('rewarded'):
                    completed_already = npc_data.get('dialogue', {}).get('quest_completed_already', "I have nothing more for you.")
                    await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{completed_already}\"")
                else:
                    # Give reward
                    quest_complete_msg = npc_data.get('dialogue', {}).get('quest_complete', "You have completed the quest!")
                    await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{quest_complete_msg}\"")

                    self.game_engine.quest_manager.give_quest_reward(character, quest_id)

                    # Show rewards
                    rewards = quest.get('rewards', {})
                    reward_msgs = []
                    if 'experience' in rewards:
                        reward_msgs.append(f"You gain {rewards['experience']} experience!")
                    if 'gold' in rewards:
                        reward_msgs.append(f"You receive {rewards['gold']} gold!")
                    if 'rune' in rewards:
                        reward_msgs.append(f"You have been granted the {rewards['rune'].title()} Rune!")

                    if reward_msgs:
                        await self.game_engine.connection_manager.send_message(player_id, "\n".join(reward_msgs))
                return

            # Check if player has the quest
            if self.game_engine.quest_manager.has_quest(character, quest_id):
                in_progress = npc_data.get('dialogue', {}).get('quest_in_progress', "You are working on my quest.")
                await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{in_progress}\"")
                return

            # Offer the quest
            can_accept, reason = self.game_engine.quest_manager.can_accept_quest(character, quest_id)
            if not can_accept:
                await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{reason}\"")
                return

            quest_available = npc_data.get('dialogue', {}).get('quest_available', "I have a quest for you.")
            await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{quest_available}\"")
            await self.game_engine.connection_manager.send_message(player_id, f"\nType 'accept {quest_id}' to accept this quest.")
            return

        # No quest interaction needed - show default dialogue for quest givers as fallback
        dialogue = npc_data.get('dialogue', {})
        response = dialogue.get('greeting', f"{npc_data['name']} greets you.")
        await self.game_engine.connection_manager.send_message(player_id, f"{npc_obj.name} says: \"{response}\"")
