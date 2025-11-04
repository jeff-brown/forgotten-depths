# How to Play Forgotten Depths

## Quick Start

### 1. Start the Server

```bash
python main.py
```

The server will start on `localhost:4000`

### 2. Connect with the Python Client (Recommended)

```bash
python src/client/terminal_client.py
```

**Why use the Python client?**
- ✅ Full RGB color support with smooth dimming based on room light levels
- ✅ Proper ANSI escape sequence handling
- ✅ Works on all platforms
- ✅ Better performance and reliability

### Alternative: Connect with Standard Telnet

```bash
telnet localhost 4000
```

⚠️ **Note**: Standard telnet may not display RGB colors correctly. You'll see white text instead of colored gradients. Use the Python client for the best experience.

## Seeing the RGB Color Dimming

Once connected, try visiting rooms with different light levels:

### Bright Rooms (Full Color)
```
go town_square
look
```
You should see: Bright yellow descriptions, bright green NPCs, bright cyan items

### Moderately Lit Rooms
```
go inn_entrance
look
```
You should see: Slightly dimmed colors

### Dark Rooms (Dimmed Colors)
```
go dungeon_entrance
go south
go west
look
```
You should see: Noticeably dimmer yellow/green/cyan (about 30% brightness)

### Very Dark Rooms (Barely Visible)
```
go dungeon_entrance
go south
go east
go east
look
```
You should see: Very dim colors (about 10% brightness)

## What the Colors Mean

- **Yellow** - Room descriptions
- **Green** - NPCs and monsters
- **Cyan** - Items on the floor
- **Magenta** - Other players
- **Red** - Damage to you, danger
- **White** - Default text, messages

The brightness of these colors changes based on the room's `light_level` (0.0 = pitch black, 1.0 = full daylight).

## Basic Commands

- `help` - Show available commands
- `look` - Examine your surroundings
- `go <direction>` - Move (north, south, east, west, up, down)
- `get <item>` - Pick up an item
- `inventory` - Show your inventory
- `stats` - Show your character stats
- `quit` - Disconnect

## Troubleshooting

### "I don't see any colors"

1. Make sure you're using the Python client: `python src/client/terminal_client.py`
2. Check your terminal supports colors: `echo $COLORTERM` (should show "truecolor")
3. If using telnet, try the Python client instead

### "Colors work but no dimming"

This is expected with standard telnet. Use the Python client for RGB dimming.

### "Connection refused"

Make sure the server is running: `python main.py`

## Terminal Compatibility

**Best Support (RGB colors with dimming):**
- iTerm2 (macOS)
- Terminal.app (macOS 10.14+)
- GNOME Terminal (Linux)
- Konsole (Linux)
- Windows Terminal (Windows 10+)

**Basic Support (colors but no dimming):**
- Standard telnet clients
- PuTTY (may need configuration)
- Older terminal emulators
