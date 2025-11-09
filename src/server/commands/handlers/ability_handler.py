"""Ability command handler for class-specific abilities."""

import random
from ..base_handler import BaseCommandHandler
from ...utils.colors import error_message, success_message, info_message


class AbilityCommandHandler(BaseCommandHandler):
    """Handles class-specific ability commands."""

    async def handle_ability_command(self, player_id: int, character: dict, ability: dict, params: str):
        """Handle execution of a class ability command.

        Args:
            player_id: The player ID
            character: Character data dictionary
            ability: The ability dictionary
            params: Additional parameters for the ability
        """
        ability_id = ability['id']
        ability_name = ability['name']

        # Execute the ability through the ability system
        result = await self.game_engine.ability_system.execute_active_ability(
            player_id,
            ability,
            target_name=params if params else None
        )

        if not result['success']:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(result['message'])
            )
            return

        # Handle specific ability types
        ability_id = ability['id']

        # Rogue abilities
        if ability_id == 'picklock':
            await self._execute_picklock_ability(player_id, character, ability, params)
        elif ability_id == 'backstab':
            await self._execute_backstab_ability(player_id, character, ability, params)
        elif ability_id == 'shadow_step':
            await self._execute_shadow_step_ability(player_id, character, ability)
        elif ability_id == 'poison_blade':
            await self._execute_poison_blade_ability(player_id, character, ability)
        # Fighter abilities
        elif ability_id == 'power_attack':
            await self._execute_power_attack_ability(player_id, character, ability, params)
        elif ability_id == 'cleave':
            await self._execute_cleave_ability(player_id, character, ability)
        elif ability_id == 'dual_wield':
            await self._execute_dual_wield_ability(player_id, character, ability)
        elif ability_id == 'shield_bash':
            await self._execute_shield_bash_ability(player_id, character, ability, params)
        elif ability_id == 'battle_cry':
            await self._execute_battle_cry_ability(player_id, character, ability)
        # Ranger abilities
        elif ability_id == 'track':
            await self._execute_track_ability(player_id, character, ability)
        elif ability_id == 'tame':
            await self._execute_tame_ability(player_id, character, ability, params)
        elif ability_id == 'pathfind':
            await self._execute_pathfind_ability(player_id, character, ability, params)
        elif ability_id == 'forage':
            await self._execute_forage_ability(player_id, character, ability)
        elif ability_id == 'camouflage':
            await self._execute_camouflage_ability(player_id, character, ability)
        elif ability_id == 'multishot':
            await self._execute_multishot_ability(player_id, character, ability)
        elif ability_id == 'call_of_the_wild':
            await self._execute_call_wild_ability(player_id, character, ability)
        else:
            # Generic ability execution
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You use {ability_name}!")
            )

    async def _execute_picklock_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the picklock ability."""
        # TODO: Implement picklock logic
        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message("You attempt to pick the lock... (Not yet implemented)")
        )

    async def _execute_backstab_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the backstab ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Backstab what? Usage: backstab <target>")
            )
            return

        # Check if in combat
        room_id = character.get('room_id')
        if room_id in self.game_engine.combat_system.active_combats:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You can't backstab while in active combat!")
            )
            return

        # Apply backstab buff for next attack
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        character['active_abilities']['backstab'] = {
            'damage_multiplier': ability['effect']['value'],
            'attacks_remaining': 1
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You prepare a devastating backstab attack!")
        )

        # Now attack the target - use combat_handler
        await self.combat_handler.handle_attack_command(player_id, params)

    async def _execute_shadow_step_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the shadow step (stealth) ability."""
        # Apply stealth effect
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        import time
        duration = ability['effect']['duration']
        character['active_abilities']['shadow_step'] = {
            'end_time': time.time() + duration,
            'dodge_bonus': ability['effect']['dodge_bonus']
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You melt into the shadows! (+{int(ability['effect']['dodge_bonus']*100)}% dodge for {duration}s)")
        )

    async def _execute_poison_blade_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the poison blade ability."""
        # Check for poison vial
        inventory = character.get('inventory', [])
        poison_vial = None
        for item in inventory:
            if item.get('id') == 'poison_vial':
                poison_vial = item
                break

        if not poison_vial:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have a poison vial!")
            )
            return

        # Remove poison vial
        inventory.remove(poison_vial)

        # Apply poison effect for next 3 attacks
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        character['active_abilities']['poison_blade'] = {
            'charges': ability['effect']['charges'],
            'damage': ability['effect']['damage'],
            'duration': ability['effect']['duration'],
            'tick_rate': ability['effect']['tick_rate']
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You coat your weapon with deadly poison! (Next {ability['effect']['charges']} attacks)")
        )

    # Fighter Ability Handlers

    async def _execute_power_attack_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the power attack ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Power attack what? Usage: powerattack <target>")
            )
            return

        # Apply power attack buff for next attack
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        character['active_abilities']['power_attack'] = {
            'damage_multiplier': ability['effect']['value'],
            'hit_penalty': ability['effect']['hit_penalty'],
            'attacks_remaining': 1
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You wind up for a devastating power attack!")
        )

        # Now attack the target - use combat_handler
        await self.combat_handler.handle_attack_command(player_id, params)

    async def _execute_cleave_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the cleave ability (AoE attack)."""
        room_id = character.get('room_id')
        if not room_id:
            return

        # Get all mobs in the room
        mobs = self.game_engine.room_mobs.get(room_id, [])
        if not mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("There are no enemies to cleave!")
            )
            return

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You swing your weapon in a wide arc, attacking all enemies!")
        )

        # Attack each mob with reduced damage
        damage_mult = ability['effect']['damage_multiplier']
        for mob in mobs[:]:  # Copy list since we might remove mobs
            # Apply cleave buff temporarily
            if 'active_abilities' not in character:
                character['active_abilities'] = {}

            character['active_abilities']['cleave'] = {
                'damage_multiplier': damage_mult,
                'attacks_remaining': 1
            }

            # Attack this mob - use combat_handler
            mob_name = mob.get('name', 'creature')
            await self.combat_handler.handle_attack_command(player_id, mob_name)

    async def _execute_dual_wield_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the dual wield toggle ability."""
        # Check if already dual wielding
        current_mode = character.get('dual_wield_mode', False)

        if current_mode:
            # Turn off dual wield
            character['dual_wield_mode'] = False
            await self.game_engine.connection_manager.send_message(
                player_id,
                info_message("You return to single weapon fighting.")
            )
        else:
            # Check if has two weapons equipped
            equipped = character.get('equipped', {})
            main_weapon = equipped.get('weapon')
            off_weapon = equipped.get('off_hand_weapon')

            if not main_weapon:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message("You need a weapon equipped to dual wield!")
                )
                return

            # For now, just enable the mode (off-hand weapon can be added later)
            character['dual_wield_mode'] = True
            character['dual_wield_config'] = {
                'main_hand_mult': ability['effect']['main_hand_mult'],
                'off_hand_mult': ability['effect']['off_hand_mult']
            }
            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You ready yourself to fight with both hands! (Main: {int(ability['effect']['main_hand_mult']*100)}%, Off: {int(ability['effect']['off_hand_mult']*100)}%)")
            )

    async def _execute_shield_bash_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the shield bash ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Shield bash what? Usage: shieldbash <target>")
            )
            return

        # Check for shield
        equipped = character.get('equipped', {})
        shield = equipped.get('shield')
        if not shield:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You don't have a shield equipped!")
            )
            return

        # Apply shield bash effect
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        character['active_abilities']['shield_bash'] = {
            'damage': ability['effect']['damage'],
            'stun_duration': ability['effect']['stun_duration'],
            'attacks_remaining': 1
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You slam your shield into the enemy!")
        )

        # Now attack the target - use combat_handler
        await self.combat_handler.handle_attack_command(player_id, params)

    async def _execute_battle_cry_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the battle cry (buff) ability."""
        # Apply battle cry effect
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        import time
        duration = ability['effect']['duration']
        character['active_abilities']['battle_cry'] = {
            'end_time': time.time() + duration,
            'damage_bonus': ability['effect']['damage_bonus'],
            'armor_bonus': ability['effect']['armor_bonus']
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You unleash a mighty battle cry! (+{int(ability['effect']['damage_bonus']*100)}% damage, +{ability['effect']['armor_bonus']} armor for {duration}s)")
        )

        # Notify room
        room_id = character.get('room_id')
        char_name = character.get('name', 'Someone')
        await self.game_engine._notify_room_except_player(
            room_id,
            player_id,
            f"{char_name} unleashes a mighty battle cry!"
        )

    # Ranger Ability Handlers

    async def _execute_track_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the track ability."""
        room_id = character.get('room_id')
        if not room_id:
            return

        # Get current room
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            return

        # Find nearby mobs in adjacent rooms
        tracked_mobs = []
        for exit_name, exit_data in room.exits.items():
            target_room_id = exit_data.get('target')
            if target_room_id:
                target_mobs = self.game_engine.room_mobs.get(target_room_id, [])
                if target_mobs:
                    tracked_mobs.append((exit_name, target_mobs))

        if not tracked_mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                info_message("You don't detect any creatures nearby.")
            )
            return

        # Display tracked creatures
        lines = [success_message("You detect the following creatures:")]
        for direction, mobs in tracked_mobs:
            mob_names = [mob.get('name', 'creature') for mob in mobs]
            lines.append(f"  {direction.upper()}: {', '.join(mob_names)}")

        await self.game_engine.connection_manager.send_message(
            player_id,
            "\n".join(lines)
        )

    async def _execute_tame_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the tame ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Tame what? Usage: tame <creature>")
            )
            return

        # TODO: Implement full pet/taming system
        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You attempt to tame the {params}...")
        )
        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message("(Full taming/pet system not yet implemented)")
        )

    async def _execute_pathfind_ability(self, player_id: int, character: dict, ability: dict, params: str):
        """Execute the pathfind ability."""
        if not params:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("Pathfind to where? Usage: pathfind <location>")
            )
            return

        room_id = character.get('room_id')
        if not room_id:
            return

        # Try to find the target location
        target_room = None
        target_location = params.lower()

        # Search for room by name or partial name
        for room in self.game_engine.world_manager.rooms.values():
            room_name = room.name.lower()
            if target_location in room_name or room_name in target_location:
                target_room = room
                break

        if not target_room:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't find a path to '{params}'.")
            )
            return

        # Use world graph to find path
        try:
            path = self.game_engine.world_manager.world_graph.find_path(room_id, target_room.room_id)
            if path:
                # Convert room IDs to directions
                directions = []
                current_id = room_id
                for next_id in path[1:]:  # Skip first room (current position)
                    current_room = self.game_engine.world_manager.get_room(current_id)
                    # Find which exit leads to next_id
                    for exit_name, exit_data in current_room.exits.items():
                        if exit_data.get('target') == next_id:
                            directions.append(exit_name)
                            break
                    current_id = next_id

                if directions:
                    path_str = " -> ".join(directions)
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        success_message(f"Path to {target_room.name}: {path_str}")
                    )
                else:
                    await self.game_engine.connection_manager.send_message(
                        player_id,
                        error_message(f"You can't find a clear path to '{params}'.")
                    )
            else:
                await self.game_engine.connection_manager.send_message(
                    player_id,
                    error_message(f"You can't find a path to '{params}'.")
                )
        except Exception as e:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message(f"You can't find a path to '{params}'.")
            )

    async def _execute_forage_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the forage ability."""
        room_id = character.get('room_id')
        if not room_id:
            return

        # Get current room
        room = self.game_engine.world_manager.get_room(room_id)
        if not room:
            return

        # Check if room has forageable items
        import random
        success_chance = ability['effect'].get('success_chance', 0.5)

        if random.random() < success_chance:
            # Successfully foraged
            forage_items = ['berries', 'herbs', 'mushrooms', 'roots']
            item = random.choice(forage_items)

            await self.game_engine.connection_manager.send_message(
                player_id,
                success_message(f"You forage and find some {item}!")
            )
            # TODO: Add item to inventory
        else:
            await self.game_engine.connection_manager.send_message(
                player_id,
                info_message("You search the area but find nothing useful.")
            )

    async def _execute_camouflage_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the camouflage (stealth) ability."""
        # Apply camouflage effect
        if 'active_abilities' not in character:
            character['active_abilities'] = {}

        import time
        duration = ability['effect']['duration']
        character['active_abilities']['camouflage'] = {
            'end_time': time.time() + duration,
            'stealth_bonus': ability['effect'].get('stealth_bonus', 0.5)
        }

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You blend into your surroundings! (Stealth for {duration}s)")
        )

    async def _execute_multishot_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the multishot ability."""
        room_id = character.get('room_id')
        if not room_id:
            return

        # Check for ranged weapon
        equipped = character.get('equipped', {})
        weapon = equipped.get('weapon')
        if not weapon or weapon.get('weapon_type') not in ['bow', 'crossbow']:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("You need a bow or crossbow equipped to use multishot!")
            )
            return

        # Get all mobs in the room
        mobs = self.game_engine.room_mobs.get(room_id, [])
        if not mobs:
            await self.game_engine.connection_manager.send_message(
                player_id,
                error_message("There are no enemies to shoot!")
            )
            return

        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message(f"You fire multiple arrows at your enemies!")
        )

        # Attack up to 3 mobs with reduced damage
        damage_mult = ability['effect']['damage_multiplier']
        max_targets = ability['effect'].get('max_targets', 3)

        for mob in mobs[:max_targets]:
            # Apply multishot buff temporarily
            if 'active_abilities' not in character:
                character['active_abilities'] = {}

            character['active_abilities']['multishot'] = {
                'damage_multiplier': damage_mult,
                'attacks_remaining': 1
            }

            # Attack this mob - use combat_handler
            mob_name = mob.get('name', 'creature')
            await self.combat_handler.handle_attack_command(player_id, mob_name)

    async def _execute_call_wild_ability(self, player_id: int, character: dict, ability: dict):
        """Execute the call of the wild (summon pet) ability."""
        # TODO: Implement full pet/companion system
        await self.game_engine.connection_manager.send_message(
            player_id,
            success_message("You call out to the wild! A spirit wolf appears at your side...")
        )
        await self.game_engine.connection_manager.send_message(
            player_id,
            info_message("(Full pet/companion system not yet implemented)")
        )
