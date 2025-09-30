"""Logging utilities for the MUD server."""

import logging
import sys
from datetime import datetime
from typing import Optional

class MUDLogger:
    """Custom logger for the MUD server."""

    def __init__(self, name: str = "forgotten_depths", level: int = logging.INFO):
        """Initialize the logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Set up log handlers."""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        file_handler = logging.FileHandler('mud_server.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        self.logger.critical(message, *args, **kwargs)

    def player_action(self, player_name: str, action: str, details: str = ""):
        """Log player action."""
        message = f"PLAYER[{player_name}] {action}"
        if details:
            message += f" - {details}"
        self.info(message)

    def admin_action(self, admin_name: str, action: str, target: str = ""):
        """Log admin action."""
        message = f"ADMIN[{admin_name}] {action}"
        if target:
            message += f" on {target}"
        self.warning(message)

    def combat_action(self, attacker: str, target: str, action: str, result: str = ""):
        """Log combat action."""
        message = f"COMBAT: {attacker} {action} {target}"
        if result:
            message += f" - {result}"
        self.info(message)

def get_logger(name: str = "forgotten_depths") -> MUDLogger:
    """Get a logger instance."""
    return MUDLogger(name)