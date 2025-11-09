# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Forgotten Depths is a Python-based Multi-User Dungeon (MUD) game with both terminal and web client support. It uses an async-based architecture with SQLite for persistence and supports real-time multiplayer gameplay.

## Common Commands

### Setup and Initialization
```bash
# Install dependencies
pip install -r requirements/base.txt

# Initialize database with test data
python scripts/reset_database.py --test-data

# Validate world data (rooms, connections, etc.)
python scripts/create_world.py --validate
```

### Running the Server
```bash
# Start the async server (default: localhost:4000, web: localhost:8080)
python main.py

# Or use the script directly
python scripts/start_async_server.py
```

### Client Connections
```bash
# Terminal client
python src/client/terminal_client.py

# Web client: http://localhost:8080
```

### Admin Tools
```bash
# List all players
python scripts/admin_tools.py list-players

# List all characters
python scripts/admin_tools.py list-characters

# Database backup
python scripts/admin_tools.py backup

# Database statistics
python scripts/admin_tools.py stats

# Delete player
python scripts/admin_tools.py delete-player <username>
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src

# Run single test file
python -m pytest tests/unit/test_player.py
```

## Architecture

### Core Systems (Async-based)

The game uses **AsyncGameEngine** (`src/server/core/async_game_engine.py`) as the central coordinator that manages:

1. **AsyncConnectionManager** - Handles network connections (telnet on port 4000, web on port 8080)
2. **CommandHandler** - Processes player commands and routes them to appropriate handlers
3. **WorldManager** - Manages rooms, areas, exits, and world graph navigation
4. **CombatSystem** - Handles combat encounters, fatigue, and damage calculations
5. **VendorSystem** - Manages NPC vendors and commerce
6. **ItemManager** - Manages item instances and properties
7. **PlayerManager** - Handles player connections, authentication, and character data
8. **EventSystem** - Pub/sub event coordination across systems

### Data Flow

**Player Input** → AsyncConnectionManager → CommandHandler → Specific command handlers (movement, combat, inventory, etc.) → Game state updates → AsyncConnectionManager sends responses

### Database Schema

SQLite database (`data/mud.db`) with three main tables:
- `players` - User accounts (name, password_hash, character_data JSON blob)
- `characters` - Character stats (level, experience, health, mana, room_id, stats JSON)
- `character_items` - Player inventory (character_id, item_id, quantity, equipped)

The game uses a hybrid approach: structured columns for core data, JSON blobs for flexible character data.

### World Data Structure

World data is stored in JSON files:
- `data/world/rooms/*.json` - Individual room definitions with exits, NPCs, items, and lair properties
- `data/world/areas/*.json` - Area metadata grouping rooms
- `data/npcs/*.json` - NPC definitions (vendors, quest givers, etc.) - loaded once at initialization and cached
- `data/mobs/*.json` - Monster/mob definitions organized by type
- `data/world/connections.json` - Room connections (legacy, mostly superseded by room exit data)

Room connections form a directed graph managed by WorldGraph (`src/server/game/world/graph.py`). The graph supports:
- Standard directional exits (north, south, east, west, up, down)
- Special exits (doors, hidden passages, etc.)
- Graph validation and pathfinding

### Combat System

Combat uses a **fatigue-based** system:
- Players have attack cooldowns tracked in `CombatSystem.player_fatigue`
- Mobs have attack cooldowns in `CombatSystem.mob_fatigue`
- Combat encounters are async tasks tracked in `CombatSystem.active_combats`
- Damage calculation considers weapon stats, armor, and character attributes

Lair rooms spawn specific monsters with respawn timers managed by the game engine's tick loop.

### Command Structure (Modular Architecture)

**IMPORTANT:** The command system uses a modular handler architecture (refactored in issue #12). Commands are now organized into specialized handlers that inherit from `BaseCommandHandler`.

#### File Structure:
```
src/server/commands/
├── command_handler.py          # Main router (526 lines - thin routing layer)
├── base_handler.py             # Base class for all handlers
└── handlers/                   # Specialized command handlers
    ├── map_handler.py          # Map display and navigation
    ├── admin_handler.py        # Admin/debug commands
    ├── quest_handler.py        # Quest system and NPC interaction
    ├── character_handler.py    # Character info and stat management
    ├── inventory_handler.py    # Inventory management
    ├── item_usage_handler.py   # Item consumption (eat, drink, etc.)
    ├── vendor_handler.py       # Trading and shop services
    ├── combat_handler.py       # Combat commands
    ├── world_handler.py        # World interaction, traps, special movement
    ├── auth_handler.py         # Authentication and character creation
    ├── magic_handler.py        # Spell system
    └── ability_handler.py      # Class-specific abilities
```

#### Architecture Guidelines:

**When Adding New Commands:**

1. **Determine the handler category** - Which existing handler does this command belong to?
   - Quest-related? → `quest_handler.py`
   - Item usage? → `item_usage_handler.py` or `inventory_handler.py`
   - Spell/magic? → `magic_handler.py`
   - Class ability? → `ability_handler.py`
   - World interaction? → `world_handler.py`
   - etc.

2. **Add method to appropriate handler** - Follow naming convention:
   ```python
   async def handle_<command_name>(self, player_id: int, character: dict, params: str):
       """Handle the <command> command.

       Usage: <command> <parameters>
       """
       # Implementation
   ```

3. **Update main router** in `command_handler.py`:
   ```python
   elif command == 'yourcommand':
       await self.appropriate_handler.handle_yourcommand(player_id, character, params)
   ```

4. **Delegate to game systems** (see issue #17) - Handlers should be thin routing layers:
   ```python
   # ✅ GOOD - Handler delegates to game system
   async def handle_cast_spell(self, player_id, character, params):
       result = await self.game_engine.spell_system.cast_spell(character, params)
       await self.send_message(player_id, result.message)

   # ❌ BAD - Handler contains game logic
   async def handle_cast_spell(self, player_id, character, params):
       # 100 lines of spell calculation logic
       # This should be in src/server/game/magic/
   ```

**Separation of Concerns (Issue #17):**

Command handlers should:
- ✅ Parse commands and extract parameters
- ✅ Call appropriate game system methods
- ✅ Format and send responses
- ✅ Handle basic validation and error messages
- ❌ NOT contain complex game logic
- ❌ NOT contain utility functions
- ❌ NOT directly manipulate game state

Game logic should live in `src/server/game/*`:
- `src/server/game/player/` - Character progression, stats
- `src/server/game/magic/` - Spell systems
- `src/server/game/abilities/` - Class abilities
- `src/server/game/combat/` - Combat mechanics
- `src/server/game/items/` - Item management
- `src/server/game/world/` - World interactions
- `src/server/game/quests/` - Quest systems

**Handler Design Pattern:**
```python
from ..base_handler import BaseCommandHandler

class YourCommandHandler(BaseCommandHandler):
    """Handles category-specific commands."""

    async def handle_your_command(self, player_id: int, character: dict, params: str):
        """Handle your command.

        Usage: yourcommand <params>
        """
        # 1. Validate input
        if not params:
            await self.send_message(player_id, "Usage: yourcommand <params>")
            return

        # 2. Delegate to game system
        result = self.game_engine.your_system.do_something(character, params)

        # 3. Send response
        await self.send_message(player_id, result.message)

        # 4. Notify room if needed
        room_id = character.get('room_id')
        await self.broadcast_to_room(room_id, result.room_message, exclude_player=player_id)
```

**Key Points:**
- Each handler is <300 lines ideally (thin routing layer)
- Handlers inherit from `BaseCommandHandler` for common functionality
- Main `command_handler.py` only routes commands, doesn't implement them
- Game logic lives in `src/server/game/*` modules, not in handlers
- This architecture improves testability, maintainability, and reusability

### Game Systems Architecture

Game logic is organized into modular systems under `src/server/game/`:

#### Current Game Systems:
- **`player/`** - Character management, progression, stats
  - `player_manager.py` - Player data and character management
  - `stats_utils.py` - Stat calculations and bonuses
- **`combat/`** - Combat mechanics
  - `combat_system.py` - Combat encounters and damage
  - `damage_calculator.py` - Damage calculations
- **`items/`** - Item management
  - `item_manager.py` - Item instances and properties
- **`world/`** - World management
  - `world_manager.py` - Rooms, areas, NPCs
  - `graph.py` - World navigation graph
- **`quests/`** - Quest system
  - `quest_manager.py` - Quest tracking and completion
- **`vendors/`** - Commerce
  - `vendor_system.py` - Shop and trading

#### Planned/Future Game Systems (Issue #17):
- **`magic/`** - Spell systems (to be extracted from magic_handler)
  - `spell_executor.py` - Spell effect execution
  - `spell_targeting.py` - Target selection
  - `mana_system.py` - Mana costs and cooldowns
- **`abilities/`** - Class abilities (to be extracted from ability_handler)
  - `ability_executor.py` - Ability execution
  - `rogue_abilities.py` - Rogue-specific implementations
  - `fighter_abilities.py` - Fighter-specific implementations
  - `ranger_abilities.py` - Ranger-specific implementations
- **`world/`** - Enhanced world systems
  - `trap_system.py` - Trap detection and disarming
  - `passage_system.py` - Special movement (boats, teleports)

**When Adding New Game Logic:**
1. Identify which game system it belongs to (player, combat, magic, etc.)
2. Add the logic to the appropriate module in `src/server/game/`
3. Have command handlers call the game system methods
4. Keep handlers thin - they should only route, not implement

### Async Patterns

The codebase uses `asyncio` throughout:
- Game loop runs as background task (`AsyncGameEngine.game_loop_task`)
- Combat rounds are async tasks
- Connection I/O is non-blocking
- Player commands are processed via `asyncio.create_task()`

Be mindful of shared state access - most game data is modified within the main game loop or through async-safe methods.

### Configuration

YAML configs in `config/`:
- `server.yaml` - Network, game tick rate, combat settings, logging
- `database.yaml` - Database path and settings
- `game_settings.yaml` - Player stats, economy, death penalties
- `items.yaml` - Item type definitions

## Important Notes

- The database path is `data/mud.db` by default (configurable in `config/database.yaml`)
- The game uses a consolidated world loading system that reads from individual room JSON files
- Player character data is stored as JSON in the `character_data` column for flexibility
- Web client uses Flask and Socket.IO (optional, enable in `config/server.yaml`)
- Logging goes to console and `logs/server.log`
- The game auto-saves every 60 seconds by default

## File Paths

When working with paths, note:
- Scripts assume execution from project root
- `sys.path.insert(0, 'src')` is used to make imports work
- Data files use relative paths from project root (e.g., `data/mud.db`)

## Quick Reference: Where Does Code Go?

### Adding a New Command:
1. **Choose handler** based on command category (see `src/server/commands/handlers/`)
2. **Add method** to handler: `async def handle_commandname(self, player_id, character, params)`
3. **Update router** in `command_handler.py`: `await self.handler_name.handle_commandname(...)`
4. **Keep it thin** - delegate logic to game systems

### Adding Game Logic:
1. **Choose system** based on functionality (`src/server/game/player/`, `combat/`, `magic/`, etc.)
2. **Add method** to appropriate system manager
3. **Call from handler** - keep handler code minimal
4. **Make it testable** - game logic should work independently of command handlers

### Current Architecture (Issue #12 + #17):
```
Player Input
    ↓
command_handler.py (router - 526 lines)
    ↓
handlers/*.py (thin routing layer - <300 lines each)
    ↓
game/*/ (game logic - bulk of implementation)
    ↓
Database/Game State
```

### Example Flow:
```
Player types: "cast fireball goblin"
    ↓
CommandHandler.handle_command() routes to magic_handler
    ↓
MagicHandler.handle_cast_spell() validates and extracts params
    ↓
SpellSystem.cast_spell() executes game logic (damage, effects, mana)
    ↓
MagicHandler sends formatted response to player
```

**Remember:** Handlers route, game systems implement!
