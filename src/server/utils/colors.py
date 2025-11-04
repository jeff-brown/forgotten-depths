"""ANSI color utility for terminal output.

Based on the color strategy from classic MUD systems:
- Red: Damage to player, danger, status ailments
- Magenta: Combat actions, successful attacks, errors
- Blue/Cyan: Magic, spells, services, transactions
- Yellow: Announcements, special events
- Green: Monster spawns, status effects
- White: Default text

Supports RGB true color with dynamic dimming based on room light levels.
"""


class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors (legacy ANSI)
    RESET = '\033[0m'

    # Normal colors
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'

    # Bold colors
    BOLD_RED = '\033[1;31m'
    BOLD_GREEN = '\033[1;32m'
    BOLD_YELLOW = '\033[1;33m'
    BOLD_BLUE = '\033[1;34m'
    BOLD_MAGENTA = '\033[1;35m'
    BOLD_CYAN = '\033[1;36m'
    BOLD_WHITE = '\033[1;37m'

    # Blinking (for critical messages)
    BLINK_RED = '\033[1;5;31m'


# RGB color mappings for dimming support
class RGBColors:
    """RGB values for true color support with dimming."""

    # Normal intensity RGB values
    RED = (205, 0, 0)
    GREEN = (0, 205, 0)
    YELLOW = (205, 205, 0)
    BLUE = (0, 0, 238)
    MAGENTA = (205, 0, 205)
    CYAN = (0, 205, 205)
    WHITE = (229, 229, 229)

    # Bold (bright) intensity RGB values
    BOLD_RED = (255, 0, 0)
    BOLD_GREEN = (0, 255, 0)
    BOLD_YELLOW = (255, 255, 0)
    BOLD_BLUE = (92, 92, 255)
    BOLD_MAGENTA = (255, 0, 255)
    BOLD_CYAN = (0, 255, 255)
    BOLD_WHITE = (255, 255, 255)


def rgb_color(r: int, g: int, b: int) -> str:
    """Create RGB color ANSI code (24-bit true color).

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        ANSI escape code for RGB color
    """
    return f"\033[38;2;{r};{g};{b}m"


def dim_rgb(rgb: tuple, factor: float) -> tuple:
    """Dim RGB color by factor.

    Args:
        rgb: Tuple of (r, g, b) values (0-255)
        factor: Dimming factor (0.0 = black, 1.0 = full brightness)

    Returns:
        Dimmed (r, g, b) tuple
    """
    factor = max(0.0, min(1.0, factor))  # Clamp to 0.0-1.0
    r, g, b = rgb
    return (int(r * factor), int(g * factor), int(b * factor))


def light_level_to_factor(light_level) -> float:
    """Convert room light_level to dimming factor.

    Args:
        light_level: Either a float (0.0-1.0) or string ("dark", "dim", "normal", "bright")

    Returns:
        Dimming factor (0.0-1.0)
    """
    if isinstance(light_level, (int, float)):
        return max(0.0, min(1.0, float(light_level)))

    # String mappings
    string_map = {
        "pitch_black": 0.0,
        "dark": 0.2,
        "dim": 0.4,
        "shadowy": 0.6,
        "warm": 0.7,
        "normal": 0.8,
        "bright": 1.0,
        "brilliant": 1.0
    }

    if isinstance(light_level, str):
        return string_map.get(light_level.lower(), 1.0)

    # Default to full brightness if unknown
    return 1.0


def colorize(text: str, color_code: str) -> str:
    """Apply ANSI color code to text and reset at the end.

    Args:
        text: The text to colorize
        color_code: The ANSI color code (e.g., Colors.BOLD_RED)

    Returns:
        Colored text with reset code at the end
    """
    return f"{color_code}{text}{Colors.BOLD_WHITE}"


# Semantic color functions based on message type

def damage_to_player(text: str) -> str:
    """Color for damage taken by player (bold red)."""
    return colorize(text, Colors.BOLD_RED)


def damage_to_enemy(text: str) -> str:
    """Color for damage dealt to enemies (bold magenta)."""
    return colorize(text, Colors.BOLD_MAGENTA)


def combat_action(text: str) -> str:
    """Color for combat actions like dodges, misses (bold magenta)."""
    return colorize(text, Colors.BOLD_MAGENTA)


def spell_cast(text: str, damage_type: str = None, spell_type: str = None) -> str:
    """Color for spell casting based on damage type or spell type.

    Args:
        text: The spell message text
        damage_type: The type of damage (fire, cold, lightning, etc.)
        spell_type: The type of spell (heal, buff, damage, etc.)

    Returns:
        Colored spell message
    """
    # Fire spells - bright orange/red
    if damage_type in ['fire', 'flame']:
        return colorize(text, rgb_color(255, 100, 0))  # Bright orange

    # Ice/Cold spells - bright cyan/blue
    elif damage_type in ['cold', 'ice', 'frost']:
        return colorize(text, rgb_color(0, 255, 255))  # Bright cyan

    # Lightning spells - electric yellow
    elif damage_type == 'lightning':
        return colorize(text, rgb_color(255, 255, 100))  # Bright yellow

    # Acid spells - toxic green
    elif damage_type == 'acid':
        return colorize(text, rgb_color(0, 255, 0))  # Bright green

    # Poison spells - sickly green
    elif damage_type == 'poison':
        return colorize(text, rgb_color(100, 200, 50))  # Sickly green

    # Force/Energy spells - violet
    elif damage_type == 'force':
        return colorize(text, rgb_color(200, 100, 255))  # Violet

    # Life steal - blood red
    elif damage_type == 'life_steal':
        return colorize(text, rgb_color(200, 0, 0))  # Dark red

    # Mana drain - deep blue
    elif damage_type == 'mana_drain':
        return colorize(text, rgb_color(0, 100, 200))  # Deep blue

    # Fear - pale gray
    elif damage_type == 'fear':
        return colorize(text, rgb_color(150, 150, 150))  # Pale gray

    # Piercing/Physical - gray/silver
    elif damage_type == 'piercing':
        return colorize(text, rgb_color(192, 192, 192))  # Silver

    # Healing spells - soft golden glow
    elif spell_type == 'heal':
        return colorize(text, rgb_color(255, 215, 0))  # Gold

    # Enhancement/buff spells - soft blue
    elif spell_type == 'enhancement':
        return colorize(text, rgb_color(100, 200, 255))  # Light blue

    # Drain spells - dark purple
    elif spell_type == 'drain':
        return colorize(text, rgb_color(139, 0, 139))  # Dark magenta

    # Debuff spells - dark violet/purple
    elif spell_type == 'debuff':
        return colorize(text, rgb_color(138, 43, 226))  # Blue-violet

    # Default magical effect - bold blue
    else:
        return colorize(text, Colors.BOLD_BLUE)


def service_message(text: str) -> str:
    """Color for services, transactions, rewards (bold cyan)."""
    return colorize(text, Colors.BOLD_CYAN)


def item_found(text: str) -> str:
    """Color for finding items or loot (bold cyan)."""
    return colorize(text, Colors.BOLD_CYAN)


def announcement(text: str) -> str:
    """Color for announcements and special events (bold yellow)."""
    return colorize(text, Colors.BOLD_YELLOW)


def error_message(text: str) -> str:
    """Color for errors and restrictions (normal magenta)."""
    return colorize(text, Colors.MAGENTA)


def status_ailment(text: str) -> str:
    """Color for hunger, thirst, poison, etc. (normal red or green)."""
    return colorize(text, Colors.RED)


def monster_spawn(text: str) -> str:
    """Color for monster spawning (bold green)."""
    return colorize(text, Colors.BOLD_GREEN)


def death_message(text: str) -> str:
    """Color for death/unconscious messages (blinking red)."""
    return colorize(text, Colors.BLINK_RED)


def success_message(text: str) -> str:
    """Color for success messages (bold green)."""
    return colorize(text, Colors.BOLD_GREEN)


def info_message(text: str) -> str:
    """Color for informational messages (white)."""
    return colorize(text, Colors.BOLD_WHITE)


# Helper for mixed color messages with dimming support
def wrap_color(text: str, color_code, dim_factor: float = 1.0) -> str:
    """Wrap text in color code without auto-reset (for inline coloring).

    Use this when you need to color part of a larger message.
    Make sure to include Colors.BOLD_WHITE at the end of your complete message.

    Args:
        text: Text to colorize
        color_code: Either ANSI color code string (e.g., Colors.BOLD_RED) or RGB tuple (e.g., RGBColors.BOLD_YELLOW)
        dim_factor: Dimming factor (0.0-1.0), only applies to RGB tuples

    Returns:
        Colored text without reset code
    """
    # If it's an RGB tuple, apply dimming and convert to RGB ANSI code
    if isinstance(color_code, tuple):
        if dim_factor < 1.0:
            color_code = dim_rgb(color_code, dim_factor)
        r, g, b = color_code
        return f"{rgb_color(r, g, b)}{text}"

    # Legacy ANSI code - use as-is
    return f"{color_code}{text}"


def get_dimmed_color(color_code, dim_factor: float = 1.0) -> str:
    """Get color code with dimming applied.

    Args:
        color_code: Either ANSI color code string or RGB tuple
        dim_factor: Dimming factor (0.0-1.0)

    Returns:
        ANSI color code (RGB if dimmed, original if legacy ANSI)
    """
    if isinstance(color_code, tuple):
        if dim_factor < 1.0:
            color_code = dim_rgb(color_code, dim_factor)
        r, g, b = color_code
        return rgb_color(r, g, b)

    # Legacy ANSI code - return as-is
    return color_code
