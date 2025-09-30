"""Network protocol definitions and message handling."""

from enum import Enum
from typing import Dict, Any

class MessageType(Enum):
    """Types of messages that can be sent between client and server."""
    COMMAND = "command"
    CHAT = "chat"
    SYSTEM = "system"
    LOGIN = "login"
    LOGOUT = "logout"

class Protocol:
    """Handles message parsing and formatting."""

    @staticmethod
    def parse_message(raw_message: str) -> Dict[str, Any]:
        """Parse a raw message into a structured format."""
        pass

    @staticmethod
    def format_message(message_type: MessageType, content: str, **kwargs) -> str:
        """Format a message for transmission."""
        pass

    @staticmethod
    def encode_message(message: str) -> bytes:
        """Encode a message for network transmission."""
        pass

    @staticmethod
    def decode_message(data: bytes) -> str:
        """Decode received data into a message."""
        pass