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

World data is stored in JSON files under `data/world/`:
- `rooms/*.json` - Individual room definitions with exits, NPCs, items, and lair properties
- `areas/*.json` - Area metadata grouping rooms
- `npcs/*.json` - NPC definitions (vendors, quest givers, etc.)
- `connections.json` - Room connections (legacy, mostly superseded by room exit data)

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

### Command Structure

Commands are organized by category under `src/server/commands/`:
- `movement/` - Navigation (go, north, south, etc.)
- `combat/` - Attack, flee, etc.
- `inventory/` - Get, drop, equip, unequip, inventory
- `vendor/` - Buy, sell, list
- `communication/` - Say, shout, whisper, etc.

Commands inherit from `BaseCommand` and are registered with `CommandManager`.

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
