#!/usr/bin/env python3
"""Test script for async combat system."""

import time
from src.server.game.combat.combat_system import AsyncCombat


def test_async_combat():
    """Test the async combat system with attack limits and fatigue."""
    print("Testing Async Combat System")
    print("=" * 40)

    # Create combat instance
    combat = AsyncCombat()

    # Create mock entities
    class MockPlayer:
        def __init__(self, name, level=1):
            self.name = name
            self.level = level
            self.health = 100
            self.max_health = 100
            self.strength = 15
            self.dexterity = 12
            self.constitution = 14
            self.intelligence = 10
            self.wisdom = 10
            self.charisma = 12

        def take_damage(self, amount):
            self.health = max(0, self.health - amount)

        def is_alive(self):
            return self.health > 0

    class MockMob:
        def __init__(self, name, level=1):
            self.name = name
            self.level = level
            self.health = 50
            self.max_health = 50
            self.strength = 12
            self.dexterity = 10
            self.constitution = 12
            self.intelligence = 8
            self.wisdom = 10
            self.charisma = 6

        def take_damage(self, amount):
            self.health = max(0, self.health - amount)

        def is_alive(self):
            return self.health > 0

    # Create participants
    player = MockPlayer("TestPlayer", level=1)
    mob = MockMob("TestMob", level=1)

    # Add participants to combat
    combat.add_participant(player, "player1")
    combat.add_participant(mob, "mob1")
    combat.start_combat()

    print(f"Combat started with {player.name} (Level {player.level}) vs {mob.name}")
    print(f"Player max attacks: {combat.participants['player1'].max_attacks}")
    print(f"Player fatigue duration: {combat.participants['player1'].fatigue_duration} seconds")
    print()

    # Test multiple attacks
    attack_count = 0
    while combat.is_active and not combat.is_combat_over():
        attack_count += 1
        print(f"--- Attack {attack_count} ---")

        # Check if player can attack
        can_attack = combat.can_participant_attack("player1")
        print(f"Player can attack: {can_attack}")

        if can_attack:
            # Execute attack
            result = combat.execute_attack("player1", "mob1")
            print(f"Attack result: {result['success']}")

            if result['success']:
                if result['hit']:
                    print(f"Hit! Damage: {result['damage']}")
                    if result['is_critical']:
                        print("CRITICAL HIT!")
                    print(f"Mob health: {mob.health}/{mob.max_health}")
                else:
                    print("Miss!")

                print(f"Attacks remaining: {result['attacks_remaining']}")
                if result['fatigue_message']:
                    print(f"Fatigue: {result['fatigue_message']}")
            else:
                print(f"Attack failed: {result['message']}")
        else:
            # Check fatigue
            participant = combat.participants.get("player1")
            if participant and participant.is_fatigued:
                fatigue_remaining = participant.get_fatigue_remaining()
                print(f"Player is fatigued for {fatigue_remaining:.1f} more seconds")

                # Wait a bit and try again
                time.sleep(1)
                continue

        print()

        # Check if mob is dead
        if not mob.is_alive():
            print("Mob defeated!")
            break

        # Limit test to prevent infinite loop
        if attack_count >= 10:
            print("Test limit reached")
            break

    # Test fatigue recovery
    if combat.participants.get("player1") and combat.participants["player1"].is_fatigued:
        print("Testing fatigue recovery...")
        participant = combat.participants["player1"]

        while participant.is_fatigued:
            remaining = participant.get_fatigue_remaining()
            print(f"Fatigue remaining: {remaining:.1f}s")
            time.sleep(1)

            # Check if fatigue expired
            participant.can_attack()  # This updates fatigue status

        print("Fatigue recovered!")
        print(f"Attacks available: {participant.attacks_remaining}")

    # Display final combat status
    print("\nFinal Combat Status:")
    status = combat.get_combat_status()
    for pid, pstatus in status['participants'].items():
        print(f"{pid}: {pstatus['name']} - HP: {pstatus['health']}/{pstatus['max_health']}")
        print(f"  Attacks: {pstatus['attacks_remaining']}, Fatigued: {pstatus['is_fatigued']}")

    print("Test completed!")


if __name__ == "__main__":
    test_async_combat()