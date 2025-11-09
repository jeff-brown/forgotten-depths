#!/usr/bin/env python3
"""Test script for fatigue functionality only."""

import time


class SimpleFatigueSystem:
    """Simple fatigue system for testing."""

    def __init__(self):
        self.player_fatigue = {}

    def _is_player_fatigued(self, player_id: int) -> bool:
        """Check if a player is currently fatigued from combat."""
        if player_id not in self.player_fatigue:
            return False

        fatigue_info = self.player_fatigue[player_id]
        current_time = time.time()

        # If fatigue_end_time is 0, player is not fatigued (just tracking attacks)
        if fatigue_info['fatigue_end_time'] == 0:
            return False

        # Check if fatigue has expired
        if current_time >= fatigue_info['fatigue_end_time']:
            # Fatigue expired, clean up
            del self.player_fatigue[player_id]
            return False

        return True

    def _get_player_fatigue_remaining(self, player_id: int) -> float:
        """Get remaining fatigue time for a player in seconds."""
        if player_id not in self.player_fatigue:
            return 0.0

        fatigue_info = self.player_fatigue[player_id]
        current_time = time.time()
        remaining = fatigue_info['fatigue_end_time'] - current_time
        return max(0.0, remaining)

    def _set_player_fatigue(self, player_id: int, duration: float = 15.0):
        """Set a player as fatigued for the specified duration."""
        self.player_fatigue[player_id] = {
            'fatigue_end_time': time.time() + duration,
            'attacks_remaining': 0
        }

    def _get_player_attacks_remaining(self, player_id: int, level: int = 1) -> int:
        """Get number of attacks remaining for a player."""
        if player_id not in self.player_fatigue:
            # Player not in combat or not fatigued, calculate max attacks
            return 2 + (level - 1) // 5  # 2 at level 1, +1 every 5 levels

        return self.player_fatigue[player_id].get('attacks_remaining', 0)

    def _use_player_attack(self, player_id: int, level: int = 1) -> bool:
        """Use one of the player's attacks. Returns True if attack was used successfully."""
        if self._is_player_fatigued(player_id):
            return False

        # Get current attacks remaining
        attacks_remaining = self._get_player_attacks_remaining(player_id, level)
        if attacks_remaining <= 0:
            return False

        # Use one attack
        attacks_remaining -= 1

        # Always ensure player is tracked in fatigue system from first attack
        if attacks_remaining <= 0:
            # Player is now fatigued
            self._set_player_fatigue(player_id)
        else:
            # Update attacks remaining (ensure player is tracked from first attack)
            self.player_fatigue[player_id] = {
                'fatigue_end_time': 0,
                'attacks_remaining': attacks_remaining
            }

        return True


def test_fatigue_system():
    """Test the fatigue system functionality."""
    print("Testing Fatigue System")
    print("=" * 30)

    system = SimpleFatigueSystem()
    player_id = 1
    level = 1

    # Test 1: Initial state
    print("=== Initial State ===")
    attacks = system._get_player_attacks_remaining(player_id, level)
    fatigued = system._is_player_fatigued(player_id)
    print(f"Attacks remaining: {attacks}")
    print(f"Is fatigued: {fatigued}")
    print()

    # Test 2: Use attacks
    print("=== Using Attacks ===")
    for i in range(3):
        print(f"Attack {i+1}:")
        attacks_before = system._get_player_attacks_remaining(player_id, level)
        can_attack = not system._is_player_fatigued(player_id) and attacks_before > 0
        print(f"  Attacks before: {attacks_before}")
        print(f"  Can attack: {can_attack}")

        if can_attack:
            success = system._use_player_attack(player_id, level)
            attacks_after = system._get_player_attacks_remaining(player_id, level)
            fatigued_after = system._is_player_fatigued(player_id)
            print(f"  Attack success: {success}")
            print(f"  Attacks after: {attacks_after}")
            print(f"  Fatigued after: {fatigued_after}")

            if fatigued_after:
                fatigue_time = system._get_player_fatigue_remaining(player_id)
                print(f"  Fatigue time: {fatigue_time:.1f}s")
        else:
            if system._is_player_fatigued(player_id):
                fatigue_time = system._get_player_fatigue_remaining(player_id)
                print(f"  Cannot attack - fatigued for {fatigue_time:.1f}s")
            else:
                print(f"  Cannot attack - no attacks remaining")
        print()

    # Test 3: Movement restriction simulation
    print("=== Movement Restriction Test ===")
    fatigued = system._is_player_fatigued(player_id)
    if fatigued:
        fatigue_time = system._get_player_fatigue_remaining(player_id)
        print(f"Player is fatigued for {fatigue_time:.1f}s - CANNOT MOVE")
    else:
        print("Player is not fatigued - CAN MOVE")
    print()

    # Test 4: Fatigue recovery simulation
    print("=== Fatigue Recovery Test ===")
    print("Simulating time passage (expiring fatigue)...")

    # Manually expire fatigue
    if player_id in system.player_fatigue:
        system.player_fatigue[player_id]['fatigue_end_time'] = time.time() - 1

    fatigued_after = system._is_player_fatigued(player_id)
    attacks_after = system._get_player_attacks_remaining(player_id, level)
    print(f"Fatigued after recovery: {fatigued_after}")
    print(f"Attacks after recovery: {attacks_after}")

    if not fatigued_after:
        print("Player can now move and attack again!")

    print("\n✅ Fatigue System Test Complete!")


if __name__ == "__main__":
    test_fatigue_system()