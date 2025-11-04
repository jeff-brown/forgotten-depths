#!/usr/bin/env python3
"""Test script to demonstrate RGB color dimming based on light levels."""

import sys
sys.path.insert(0, 'src')

from server.utils.colors import (
    RGBColors, wrap_color, light_level_to_factor, Colors
)


def test_dimming():
    """Demonstrate color dimming at different light levels."""

    print("\n=== RGB Color Dimming Test ===\n")

    # Test different light levels
    light_levels = [
        ("Pitch Black", 0.0),
        ("Very Dark", 0.1),
        ("Dark", 0.2),
        ("Dim", 0.4),
        ("Shadowy", 0.6),
        ("Warm", 0.7),
        ("Normal", 0.8),
        ("Bright", 1.0),
    ]

    # Test room description (yellow)
    print("Room Description (Yellow):")
    for name, level in light_levels:
        dim_factor = light_level_to_factor(level)
        text = f"  {name:12} (factor={dim_factor:.1f}): "
        desc = wrap_color("You are in a dark cavern.", RGBColors.BOLD_YELLOW, dim_factor)
        print(f"{text}{desc}{Colors.BOLD_WHITE}")

    print()

    # Test NPCs/Mobs (green)
    print("NPCs and Mobs (Green):")
    for name, level in light_levels:
        dim_factor = light_level_to_factor(level)
        text = f"  {name:12} (factor={dim_factor:.1f}): "
        npc = wrap_color("Brother Aldric is here.", RGBColors.BOLD_GREEN, dim_factor)
        print(f"{text}{npc}{Colors.BOLD_WHITE}")

    print()

    # Test items (cyan)
    print("Items on Floor (Cyan):")
    for name, level in light_levels:
        dim_factor = light_level_to_factor(level)
        text = f"  {name:12} (factor={dim_factor:.1f}): "
        item = wrap_color("There is a rusty sword lying on the floor.", RGBColors.BOLD_CYAN, dim_factor)
        print(f"{text}{item}{Colors.BOLD_WHITE}")

    print()

    # Test players (magenta)
    print("Other Players (Magenta):")
    for name, level in light_levels:
        dim_factor = light_level_to_factor(level)
        text = f"  {name:12} (factor={dim_factor:.1f}): "
        player = wrap_color("Gandalf is here.", RGBColors.BOLD_MAGENTA, dim_factor)
        print(f"{text}{player}{Colors.BOLD_WHITE}")

    print()

    # Test string light levels
    print("String Light Level Conversions:")
    string_levels = ["pitch_black", "dark", "dim", "shadowy", "warm", "normal", "bright", "brilliant"]
    for level_str in string_levels:
        factor = light_level_to_factor(level_str)
        text = f"  '{level_str:12}' -> {factor:.1f}: "
        sample = wrap_color("Sample text", RGBColors.BOLD_YELLOW, factor)
        print(f"{text}{sample}{Colors.BOLD_WHITE}")

    print("\n=== Test Complete ===\n")
    print("Note: If you see proper color gradients above, RGB dimming is working!")
    print("If colors look wrong or you see escape codes, your terminal may not support RGB.\n")


if __name__ == "__main__":
    test_dimming()
