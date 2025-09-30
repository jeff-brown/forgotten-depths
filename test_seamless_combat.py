#!/usr/bin/env python3
"""Test script for seamless combat system."""

import time
import asyncio
from src.server.core.async_game_engine import AsyncGameEngine


async def test_seamless_combat():
    """Test the seamless combat system with fatigue and movement restrictions."""
    print("Testing Seamless Combat System")
    print("=" * 40)

    # Create game engine
    engine = AsyncGameEngine()

    # Mock player ID and data
    player_id = 1
    engine.connected_players[player_id] = {
        'player_id': player_id,
        'authenticated': True,
        'username': 'TestPlayer',
        'character': {
            'name': 'TestPlayer',
            'level': 1,
            'room_id': 'test_room',
            'strength': 15,
            'dexterity': 12,
            'constitution': 14,
            'intellect': 10,
            'wisdom': 10,
            'charisma': 12,
            'experience': 0
        }
    }

    # Create mock target mob
    test_mob = {
        'id': 'test_mob',
        'name': 'Test Goblin',
        'level': 1,
        'health': 30,
        'max_health': 30,
        'type': 'hostile'
    }

    # Add mob to room
    engine.room_mobs['test_room'] = [test_mob]

    print(f"Player: {engine.connected_players[player_id]['character']['name']} (Level 1)")
    print(f"Target: {test_mob['name']} (Health: {test_mob['health']}/{test_mob['max_health']})")
    print()

    # Test 1: Check initial attack availability
    attacks_remaining = engine._get_player_attacks_remaining(player_id)
    is_fatigued = engine._is_player_fatigued(player_id)
    print(f"Initial attacks remaining: {attacks_remaining}")
    print(f"Initial fatigue status: {is_fatigued}")
    print()

    # Test 2: Simulate attacks
    for i in range(3):  # Try 3 attacks (should only get 2)
        print(f"--- Attack {i+1} ---")

        # Check if player can attack
        attacks_before = engine._get_player_attacks_remaining(player_id)
        can_attack = not engine._is_player_fatigued(player_id) and attacks_before > 0

        print(f"Attacks remaining before: {attacks_before}")
        print(f"Can attack: {can_attack}")

        if can_attack:
            # Simulate using an attack
            success = engine._use_player_attack(player_id)
            print(f"Attack used successfully: {success}")

            attacks_after = engine._get_player_attacks_remaining(player_id)
            is_fatigued_after = engine._is_player_fatigued(player_id)

            print(f"Attacks remaining after: {attacks_after}")
            print(f"Is fatigued after: {is_fatigued_after}")

            if is_fatigued_after:
                fatigue_time = engine._get_player_fatigue_remaining(player_id)
                print(f"Fatigue time remaining: {fatigue_time:.1f} seconds")
        else:
            if engine._is_player_fatigued(player_id):
                fatigue_time = engine._get_player_fatigue_remaining(player_id)
                print(f"Player is fatigued for {fatigue_time:.1f} more seconds")
            else:
                print("Player has no attacks remaining")

        print()

    # Test 3: Check movement restrictions while fatigued
    print("--- Movement Restriction Test ---")
    is_fatigued = engine._is_player_fatigued(player_id)
    print(f"Player is fatigued: {is_fatigued}")

    if is_fatigued:
        fatigue_time = engine._get_player_fatigue_remaining(player_id)
        print(f"Fatigue remaining: {fatigue_time:.1f} seconds")
        print("Player should not be able to move!")
    else:
        print("Player can move freely")

    print()

    # Test 4: Wait for fatigue to recover (simulate time passing)
    print("--- Fatigue Recovery Test ---")
    print("Simulating time passage...")

    # Manually expire fatigue by setting past time
    if player_id in engine.player_fatigue:
        engine.player_fatigue[player_id]['fatigue_end_time'] = time.time() - 1

    # Check recovery
    is_fatigued_after_time = engine._is_player_fatigued(player_id)
    attacks_after_recovery = engine._get_player_attacks_remaining(player_id)

    print(f"Is fatigued after recovery: {is_fatigued_after_time}")
    print(f"Attacks available after recovery: {attacks_after_recovery}")

    print("\nSeamless Combat Test Completed!")


if __name__ == "__main__":
    asyncio.run(test_seamless_combat())