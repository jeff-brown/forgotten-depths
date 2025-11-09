"""
Character Stats Utility Functions

Provides shared utility functions for character stat calculations.
"""


def get_stamina_hp_bonus(stamina: int) -> int:
    """Get HP bonus based on stamina (constitution) value.

    Args:
        stamina: The character's stamina/constitution stat

    Returns:
        HP bonus value
    """
    # More generous scaling: constitution directly contributes to HP
    # This ensures even low-con characters get decent HP gains
    if stamina >= 50:
        return 25
    elif stamina >= 45:
        return 22
    elif stamina >= 40:
        return 20
    elif stamina >= 35:
        return 18
    elif stamina >= 30:
        return 15
    elif stamina >= 25:
        return 13
    elif stamina >= 20:
        return 11
    elif stamina >= 18:
        return 10
    elif stamina >= 16:
        return 9
    elif stamina >= 14:
        return 8
    elif stamina >= 12:
        return 7
    elif stamina >= 10:
        return 6
    elif stamina >= 8:
        return 5
    else:
        return 4
