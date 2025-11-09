#!/usr/bin/env python3
"""Debug script for fatigue functionality."""

import time


class DebugFatigueSystem:
    """Debug fatigue system for testing."""

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
        print(f"    DEBUG: player_fatigue dict = {self.player_fatigue}")
        print(f"    DEBUG: Checking attacks for player {player_id}")

        if player_id not in self.player_fatigue:
            # Player not in combat or not fatigued, calculate max attacks
            print(f"    DEBUG: Player {player_id} not in fatigue dict, returning max attacks")
            return 2 + (level - 1) // 5  # 2 at level 1, +1 every 5 levels

        attacks = self.player_fatigue[player_id].get('attacks_remaining', 0)
        print(f"    DEBUG: Player {player_id} found in dict, attacks_remaining = {attacks}")
        return attacks

    def _use_player_attack(self, player_id: int, level: int = 1) -> bool:
        """Use one of the player's attacks. Returns True if attack was used successfully."""
        print(f"  DEBUG: Starting _use_player_attack for player {player_id}")

        if self._is_player_fatigued(player_id):
            print(f"  DEBUG: Player {player_id} is fatigued, cannot attack")
            return False

        # Get current attacks remaining
        attacks_remaining = self._get_player_attacks_remaining(player_id, level)
        print(f"  DEBUG: Current attacks remaining: {attacks_remaining}")

        if attacks_remaining <= 0:
            print(f"  DEBUG: No attacks remaining, attack failed")
            return False

        # Use one attack
        attacks_remaining -= 1
        print(f"  DEBUG: After using attack, attacks_remaining = {attacks_remaining}")

        # Always ensure player is tracked in fatigue system from first attack
        if attacks_remaining <= 0:
            # Player is now fatigued
            print(f"  DEBUG: Player {player_id} is now fatigued")
            self._set_player_fatigue(player_id)
        else:
            # Update attacks remaining (ensure player is tracked from first attack)
            print(f"  DEBUG: Setting player {player_id} attacks_remaining to {attacks_remaining}")
            self.player_fatigue[player_id] = {
                'fatigue_end_time': 0,
                'attacks_remaining': attacks_remaining
            }

        print(f"  DEBUG: Final player_fatigue dict = {self.player_fatigue}")
        return True


def test_debug_fatigue():
    """Test the fatigue system with debug output."""
    print("Testing Debug Fatigue System")
    print("=" * 40)

    system = DebugFatigueSystem()
    player_id = 1
    level = 1

    # Test 1: Initial state
    print("=== Initial State ===")
    attacks = system._get_player_attacks_remaining(player_id, level)
    fatigued = system._is_player_fatigued(player_id)
    print(f"Attacks remaining: {attacks}")
    print(f"Is fatigued: {fatigued}")
    print()

    # Test 2: Use attacks with debugging
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

    print("✅ Debug Fatigue System Test Complete!")


if __name__ == "__main__":
    test_debug_fatigue()