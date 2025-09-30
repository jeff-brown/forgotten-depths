"""Random number generation utilities."""

import random
from typing import List, Any, Tuple

class RandomUtils:
    """Utility functions for random number generation."""

    @staticmethod
    def roll_dice(num_dice: int, num_sides: int, modifier: int = 0) -> int:
        """Roll dice with format: XdY+Z (e.g., 2d6+3)."""
        total = sum(random.randint(1, num_sides) for _ in range(num_dice))
        return total + modifier

    @staticmethod
    def parse_dice_string(dice_string: str) -> int:
        """Parse and roll dice from string format (e.g., '2d6+3', '1d20')."""
        dice_string = dice_string.lower().replace(' ', '')

        if 'd' not in dice_string:
            try:
                return int(dice_string)
            except ValueError:
                return 0

        parts = dice_string.split('d')
        if len(parts) != 2:
            return 0

        try:
            num_dice = int(parts[0]) if parts[0] else 1

            if '+' in parts[1]:
                sides_part, modifier_part = parts[1].split('+')
                num_sides = int(sides_part)
                modifier = int(modifier_part)
            elif '-' in parts[1]:
                sides_part, modifier_part = parts[1].split('-')
                num_sides = int(sides_part)
                modifier = -int(modifier_part)
            else:
                num_sides = int(parts[1])
                modifier = 0

            return RandomUtils.roll_dice(num_dice, num_sides, modifier)

        except ValueError:
            return 0

    @staticmethod
    def weighted_choice(choices: List[Tuple[Any, float]]) -> Any:
        """Make a weighted random choice from a list of (item, weight) tuples."""
        if not choices:
            return None

        total_weight = sum(weight for _, weight in choices)
        if total_weight <= 0:
            return random.choice([item for item, _ in choices])

        r = random.uniform(0, total_weight)
        cumulative_weight = 0

        for item, weight in choices:
            cumulative_weight += weight
            if r <= cumulative_weight:
                return item

        return choices[-1][0]

    @staticmethod
    def percentage_chance(percentage: float) -> bool:
        """Return True if random chance succeeds."""
        return random.random() < (percentage / 100.0)

    @staticmethod
    def random_range(min_val: int, max_val: int) -> int:
        """Generate random integer in range [min_val, max_val]."""
        return random.randint(min_val, max_val)

    @staticmethod
    def shuffle_list(items: List[Any]) -> List[Any]:
        """Return a shuffled copy of the list."""
        shuffled = items.copy()
        random.shuffle(shuffled)
        return shuffled

    @staticmethod
    def random_elements(items: List[Any], count: int) -> List[Any]:
        """Select random elements from a list without replacement."""
        if count >= len(items):
            return RandomUtils.shuffle_list(items)

        return random.sample(items, count)

    @staticmethod
    def gaussian_int(mean: float, std_dev: float, min_val: int = None, max_val: int = None) -> int:
        """Generate a random integer from normal distribution."""
        value = random.gauss(mean, std_dev)
        result = round(value)

        if min_val is not None:
            result = max(result, min_val)
        if max_val is not None:
            result = min(result, max_val)

        return result