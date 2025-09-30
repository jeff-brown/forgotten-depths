# Forgotten Depths MUD - Setup Guide

## Requirements

- Python 3.8 or higher
- SQLite (included with Python)
- Optional: Flask and Flask-SocketIO for web client

## Installation

1. Clone or download the project files
2. Navigate to the project directory
3. Install dependencies:

```bash
# Basic dependencies
pip install -r requirements/base.txt

# For web client support
pip install -r requirements/dev.txt

# For testing
pip install -r requirements/test.txt
```

## Quick Start

1. **Initialize the database:**
```bash
python scripts/reset_database.py --test-data
```

2. **Validate world data:**
```bash
python scripts/create_world.py --validate
```

3. **Start the server:**
```bash
python scripts/start_server.py
```

4. **Connect with terminal client:**
```bash
python src/client/terminal_client.py
```

5. **Or use web client:**
   - Open browser to http://localhost:8080

## Configuration

### Server Configuration
Edit `config/server.yaml` to configure:
- Network settings (host, port)
- Game settings (tick rate, save interval)
- Logging settings

### Database Configuration
Edit `config/database.yaml` to configure:
- Database path
- Backup settings
- Performance settings

### Game Settings
Edit `config/game_settings.yaml` to configure:
- Player starting stats
- Combat settings
- Economy settings
- Death penalties

## Administration

### List Players
```bash
python scripts/admin_tools.py list-players
```

### List Characters
```bash
python scripts/admin_tools.py list-characters
```

### Backup Database
```bash
python scripts/admin_tools.py backup
```

### Delete Player
```bash
python scripts/admin_tools.py delete-player <username>
```

### Database Statistics
```bash
python scripts/admin_tools.py stats
```

## Development

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/unit/test_player.py

# Run with coverage
python -m pytest tests/ --cov=src
```

### Code Structure

```
src/
├── server/          # Server-side code
│   ├── core/        # Game engine and core systems
│   ├── game/        # Game logic (players, world, combat)
│   ├── networking/  # Network communication
│   ├── commands/    # Player commands
│   ├── persistence/ # Data storage
│   └── utils/       # Utility functions
├── client/          # Client implementations
│   ├── terminal_client.py
│   └── web_client/
└── shared/          # Shared code and types
```

### Adding New Commands

1. Create command class in `src/server/commands/`
2. Inherit from `BaseCommand`
3. Implement `execute()` method
4. Register command in command manager

### Adding New Items

1. Add item data to appropriate JSON file in `data/items/`
2. Create item class if needed in `src/server/game/items/`
3. Update world loader if using custom item types

### Adding New Areas/Rooms

1. Create room files in `data/world/rooms/`
2. Create area file in `data/world/areas/`
3. Update `data/world/connections.json`
4. Validate with `python scripts/create_world.py --validate`

## Troubleshooting

### Database Issues
- Delete `data/mud.db` and run `reset_database.py` again
- Check file permissions
- Ensure data directory exists

### Connection Issues
- Check if port 4000 is available
- Verify firewall settings
- Check server logs in `logs/server.log`

### Web Client Issues
- Ensure Flask and Flask-SocketIO are installed
- Check if port 8080 is available
- Verify static files are present

### Performance Issues
- Increase database cache size in `config/database.yaml`
- Adjust game tick rate in `config/server.yaml`
- Monitor server logs for errors

## Logging

Logs are written to:
- Console output
- `logs/server.log`

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

Configure logging in `config/server.yaml`.

## Security

- Change default passwords
- Use strong passwords (minimum 6 characters)
- Regular database backups
- Monitor for suspicious activity
- Keep Python and dependencies updated