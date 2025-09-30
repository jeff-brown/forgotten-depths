"""Game constants and configuration values."""

# Server Configuration
DEFAULT_SERVER_HOST = "localhost"
DEFAULT_SERVER_PORT = 4000
DEFAULT_WEB_PORT = 8080
MAX_CONNECTIONS = 100
HEARTBEAT_INTERVAL = 30

# Game Mechanics
MAX_PLAYER_LEVEL = 100
STARTING_LEVEL = 1
STARTING_HEALTH = 100
STARTING_MANA = 50
STARTING_GOLD = 100

# Experience and Leveling
BASE_EXPERIENCE_NEEDED = 100
EXPERIENCE_MULTIPLIER = 1.5
EXPERIENCE_FROM_MOB_BASE = 25

# Combat
BASE_DAMAGE = 5
CRITICAL_HIT_CHANCE = 0.05
CRITICAL_DAMAGE_MULTIPLIER = 2.0
MISS_CHANCE = 0.1
FLEE_SUCCESS_CHANCE = 0.7

# Inventory
DEFAULT_INVENTORY_SIZE = 20
MAX_ITEM_STACK_SIZE = 99
STARTING_INVENTORY_SLOTS = 10

# Communication
MAX_MESSAGE_LENGTH = 500
MAX_CHANNEL_HISTORY = 100
TELL_TIMEOUT_SECONDS = 300

# World
MAX_ROOM_CAPACITY = 50
RESPAWN_TIME_SECONDS = 300
SAVE_INTERVAL_SECONDS = 60

# Database
DEFAULT_DB_PATH = "data/mud.db"
BACKUP_INTERVAL_HOURS = 6
MAX_SAVE_RETRIES = 3

# Text Formatting
TEXT_WRAP_WIDTH = 80
MAX_DESCRIPTION_LENGTH = 1000
MAX_NAME_LENGTH = 50

# Time and Scheduling
GAME_TICK_RATE = 1.0  # seconds
IDLE_TIMEOUT_MINUTES = 30
SAVE_ON_QUIT_TIMEOUT = 10

# Security
MAX_LOGIN_ATTEMPTS = 3
LOGIN_TIMEOUT_MINUTES = 15
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 50

# Directories
DATA_DIR = "data"
CONFIG_DIR = "config"
LOGS_DIR = "logs"
BACKUP_DIR = "backups"

# File Extensions
WORLD_FILE_EXT = ".json"
CONFIG_FILE_EXT = ".yaml"
LOG_FILE_EXT = ".log"

# Default Room - these are fallback constants only
# Actual starting room should be determined dynamically by world manager
DEFAULT_FALLBACK_ROOM_ID = "default_starting_room"
VOID_ROOM_ID = "void"

# Color Codes (for terminal clients)
COLOR_CODES = {
    "reset": "\033[0m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_black": "\033[90m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_white": "\033[97m"
}

# Status Messages
WELCOME_MESSAGE = "Welcome to Forgotten Depths!"
GOODBYE_MESSAGE = "Thanks for playing! See you next time."
CHARACTER_CREATED_MESSAGE = "Character created successfully!"
LOGIN_SUCCESS_MESSAGE = "Login successful. Welcome back!"
INVALID_COMMAND_MESSAGE = "I don't understand that command."

# Error Messages
CONNECTION_ERROR = "Connection error occurred."
DATABASE_ERROR = "Database error occurred."
SAVE_ERROR = "Failed to save data."
LOAD_ERROR = "Failed to load data."
PERMISSION_DENIED = "You don't have permission to do that."
ITEM_NOT_FOUND = "You don't see that here."
PLAYER_NOT_FOUND = "That player is not online."
ROOM_NOT_FOUND = "That room doesn't exist."