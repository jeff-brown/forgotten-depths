# Forgotten Depths MUD

A Python-based Multi-User Dungeon (MUD) game with both terminal and web client support.

## Quick Start

1. Install Python 3.8+
2. Clone and setup:
   ```bash
   pip install -r requirements/base.txt
   ```
3. Initialize the game:
   ```bash
   python scripts/reset_database.py --test-data
   python scripts/create_world.py --validate
   ```
4. Start the server:
   ```bash
   python main.py
   ```
5. Connect via terminal client or web browser (http://localhost:8080)

## Documentation

See `docs/setup.md` for detailed setup instructions.

## License

MIT License
