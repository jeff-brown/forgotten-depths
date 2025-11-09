# Testing RGB Color Dimming

## What Was Implemented

RGB true-color dimming based on room light levels:
- Room descriptions (yellow) dim from 0% to 100% based on `light_level`
- NPCs and mobs (green) dim based on light
- Items on floor (cyan) dim based on light
- Other players (magenta) dim based on light

## How to Test

### 1. Check Your Terminal Supports RGB

Run this test:
```bash
bash test_terminal_rgb.sh
```

If you see colored text gradients, your terminal supports RGB. If not, you'll see white text or escape codes.

**Terminals that support RGB:**
- macOS Terminal.app (10.14+)
- iTerm2
- Most modern Linux terminals

**Terminals that may NOT support RGB:**
- Very old terminal versions
- Some SSH clients
- Basic telnet clients

### 2. Start the Game Server

```bash
python main.py
```

### 3. Connect with Telnet

```bash
telnet localhost 4000
```

### 4. Test Different Light Levels

Visit these rooms to see dimming in action:

**Bright Room (light_level: 1.0 or "bright"):**
```
go town_square
look
```
Should see: Full bright yellow room description, bright green NPCs, bright cyan items

**Dark Room (light_level: 0.3):**
```
go dungeon_cavern
look
```
Should see: Dimmed yellow (darker), dimmed green, dimmed cyan

**Very Dark Room (light_level: 0.1):**
```
go dungeon_crypt
look
```
Should see: Very dim yellow (almost dark), very dim green, very dim cyan

## Troubleshooting

### "All text is white"

This means one of these issues:

1. **Your terminal doesn't support RGB colors**
   - Solution: Use iTerm2 or update Terminal.app
   - Check: Run `echo $COLORTERM` (should show "truecolor" or "24bit")

2. **Telnet client strips ANSI codes**
   - Solution: Use the built-in Python telnet client:
     ```bash
     python src/client/terminal_client.py
     ```

3. **Light level defaulting to 1.0**
   - Check if rooms have `light_level` in their JSON files
   - Run: `grep light_level data/world/rooms/*.json`

### "I see escape codes like [38;2;127;127;0m"

Your terminal doesn't support RGB colors. Try:
- Upgrading to iTerm2
- Using a different terminal emulator
- Setting `COLORTERM=truecolor` environment variable

## Expected Behavior

In a **bright room** (town_square):
```
[Bright Yellow] You are in the town square.
[Bright Green] Brother Aldric is here.
[Bright Cyan] There is a rusty sword lying on the floor.
```

In a **dark room** (dungeon_cavern, light_level: 0.3):
```
[Dark Yellow] You are in the underground cavern.
[Dark Green] A Huge Rat is here.
[Dark Cyan] There is a torch lying on the floor.
```

The colors should be **noticeably dimmer** in dark rooms.

## Light Level Values

Rooms can use numeric (0.0-1.0) or string values:
- `0.0` or `"pitch_black"` - Cannot see (black text)
- `0.1` - Barely visible
- `0.2` or `"dark"` - Very dark
- `0.3` - Dark cavern
- `0.4` or `"dim"` - Dimly lit
- `0.6` or `"shadowy"` - Shadows
- `0.7` or `"warm"` - Warm lighting (candles, firelight)
- `0.8` or `"normal"` - Normal indoor lighting
- `1.0` or `"bright"` - Full daylight/bright

## How It Works

1. When player enters room, system reads `light_level` from room JSON
2. Converts to dimming factor (0.0-1.0)
3. Multiplies RGB color values by factor
4. Sends RGB ANSI codes to terminal: `\033[38;2;R;G;Bm`
5. Terminal renders dimmed colors

