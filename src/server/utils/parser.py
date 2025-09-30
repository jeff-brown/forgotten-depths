"""Text parsing utilities for command interpretation."""

import re
from typing import List, Tuple, Dict, Any

class CommandParser:
    """Parses player input into commands and arguments."""

    def __init__(self):
        """Initialize the command parser."""
        self.aliases = {
            "'": "say",
            "\"": "say",
            ":": "emote",
            "me": "emote",
            "l": "look",
            "n": "north",
            "s": "south",
            "e": "east",
            "w": "west",
            "ne": "northeast",
            "nw": "northwest",
            "se": "southeast",
            "sw": "southwest",
            "u": "up",
            "d": "down",
            "i": "inventory",
            "inv": "inventory"
        }

    def parse_input(self, input_text: str) -> Tuple[str, List[str]]:
        """Parse input text into command and arguments."""
        input_text = input_text.strip()

        if not input_text:
            return "", []

        if input_text[0] in ["'", "\""]:
            return "say", [input_text[1:]]

        if input_text[0] == ":":
            return "emote", [input_text[1:]]

        parts = input_text.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        command = self.aliases.get(command, command)

        return command, args

    def parse_direction(self, direction: str) -> str:
        """Parse and normalize direction input."""
        direction = direction.lower().strip()

        direction_aliases = {
            "n": "north",
            "s": "south",
            "e": "east",
            "w": "west",
            "ne": "northeast",
            "nw": "northwest",
            "se": "southeast",
            "sw": "southwest",
            "u": "up",
            "d": "down"
        }

        return direction_aliases.get(direction, direction)

    def parse_target(self, target_text: str, available_targets: List[str]) -> str:
        """Parse target text and find best match from available targets."""
        if not target_text or not available_targets:
            return None

        target_text = target_text.lower()

        for target in available_targets:
            if target.lower() == target_text:
                return target

        for target in available_targets:
            if target.lower().startswith(target_text):
                return target

        for target in available_targets:
            if target_text in target.lower():
                return target

        return None

    def extract_quoted_text(self, text: str) -> List[str]:
        """Extract quoted strings from text."""
        pattern = r'\"([^\"]*)\"|\'([^\']*)\''
        matches = re.findall(pattern, text)
        return [match[0] or match[1] for match in matches]

    def split_arguments(self, args_text: str) -> List[str]:
        """Split arguments while preserving quoted strings."""
        if not args_text:
            return []

        quoted_strings = self.extract_quoted_text(args_text)
        temp_text = args_text

        for i, quoted in enumerate(quoted_strings):
            placeholder = f"__QUOTED_{i}__"
            temp_text = temp_text.replace(f'"{quoted}"', placeholder)
            temp_text = temp_text.replace(f"'{quoted}'", placeholder)

        args = temp_text.split()

        for i, arg in enumerate(args):
            if arg.startswith("__QUOTED_"):
                quote_index = int(arg.split("_")[2])
                args[i] = quoted_strings[quote_index]

        return args

class TextFormatter:
    """Formats text for display to players."""

    @staticmethod
    def wrap_text(text: str, width: int = 80) -> str:
        """Wrap text to specified width."""
        if len(text) <= width:
            return text

        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    @staticmethod
    def colorize(text: str, color_code: str) -> str:
        """Add color codes to text (basic implementation)."""
        color_codes = {
            'red': '\033[31m',
            'green': '\033[32m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'magenta': '\033[35m',
            'cyan': '\033[36m',
            'white': '\033[37m',
            'reset': '\033[0m'
        }

        if color_code in color_codes:
            return f"{color_codes[color_code]}{text}{color_codes['reset']}"
        return text

    @staticmethod
    def capitalize_first(text: str) -> str:
        """Capitalize the first letter of text."""
        if not text:
            return text
        return text[0].upper() + text[1:]