# Admin Commands Reference

Quick reference guide for admin/debug commands in Forgotten Depths.

## Character Stats & Progression

### setstat <stat_name> <value>
Set a character stat to a specific value.

**Stats:** strength (str), dexterity (dex), constitution (con), vitality (vit), intellect/intelligence (int), wisdom (wis), charisma (cha)

**Value Range:** 1-99 (automatically clamped)

**Examples:**
```
setstat strength 25
setstat dex 30
setstat int 50
```

**Output:**
```
[ADMIN] Strength set: 10 → 25
```

---

### setlevel <level>
Set character level (automatically adjusts max HP and mana).

**Level Range:** 1-50 (automatically clamped)

**Auto-calculations:**
- Max HP: 100 + (level × 10)
- Max Mana: 50 + (level × 5)
- Both health and mana are restored to full

**Examples:**
```
setlevel 10
setlevel 25
setlevel 50
```

**Output:**
```
[ADMIN] Level set: 5 → 10
Max HP: 200, Max Mana: 100
Health and mana restored to full.
```

---

### sethealth <current> [max]
Set current health, optionally set max health.

**Shortcuts:**
- `sethealth full` - Restore to max HP

**Examples:**
```
sethealth 50        # Set current HP to 50
sethealth 100 200   # Set current to 100, max to 200
sethealth full      # Restore to full HP
```

**Output:**
```
[ADMIN] Health set: 50 / 200
[ADMIN] Health restored to full: 200
```

---

### setmana <current> [max]
Set current mana, optionally set max mana.

**Shortcuts:**
- `setmana full` - Restore to max mana

**Examples:**
```
setmana 30        # Set current mana to 30
setmana 50 100    # Set current to 50, max to 100
setmana full      # Restore to full mana
```

**Output:**
```
[ADMIN] Mana set: 50 / 100
[ADMIN] Mana restored to full: 100
```

---

### godmode (or god)
Toggle god mode - instant maximum power!

**Effects when enabled:**
- All stats → 99
- Level → 50
- Max HP → 9999
- Max Mana → 9999
- Current HP → 9999
- Current Mana → 9999
- +100,000 gold

**Examples:**
```
godmode    # Enable god mode
god        # Same as godmode
godmode    # Disable god mode (toggle)
```

**Output:**
```
[ADMIN] GOD MODE ENABLED!
All stats set to 99, Level 50, HP/Mana 9999, +100,000 gold

[ADMIN] God mode disabled. Use 'setstat' and 'setlevel' to adjust stats manually.
```

---

## Resources & Items

### givegold <amount>
Add gold to your character.

**Examples:**
```
givegold 1000
givegold 50000
```

**Output:**
```
[ADMIN] Added 1000 gold. You now have 1250 gold.
```

---

### giveitem <item_id>
Add any item to your inventory.

**Finding Item IDs:**
- Check `data/items/*.json` files
- Item IDs are the keys in the JSON (e.g., "iron_sword", "health_potion")

**Examples:**
```
giveitem iron_sword
giveitem scroll_komiza
giveitem health_potion
```

**Output:**
```
[ADMIN] Added iron_sword to your inventory.
```

---

### givexp <amount>
Add experience points (can trigger level ups).

**Examples:**
```
givexp 500
givexp 10000
```

**Output:**
```
[ADMIN] Added 500 XP. You now have 750 XP. (250 XP until level 6)
[ADMIN] You've gained a level! You are now level 6.
```

---

## World & NPCs

### teleport <room_id>
Teleport yourself to any room.

**Finding Room IDs:**
- Check `data/world/rooms/*.json` files
- Room ID is the "id" field in each file

**Examples:**
```
teleport town_square
teleport mystic_plaza
teleport dungeon1_1
```

**Multi-player variant:**
```
teleport <player_name> <room_id>
```

---

### respawnnpc <npc_id>
Respawn an NPC in its original room (useful if NPC was killed or removed).

**Examples:**
```
respawnnpc master_pyrus_frostweaver
respawnnpc elder_thornbark
```

---

### mobstatus
Display debug information about all active mobs (wandering, lair, gong-summoned).

**Example:**
```
mobstatus
```

**Output:**
```
[ADMIN] Mob Status Report:
Total mobs: 15
Wandering: 5
Lair: 8
Gong-spawned: 2
```

---

## Quests

### completequest <quest_id>
Mark a quest as completed (bypasses all requirements).

**Examples:**
```
completequest slay_the_dragon
completequest fetch_herbs
```

---

## Common Testing Workflows

### Quick Power Character
```bash
godmode
# Instant level 50 character with max stats
```

### Test Specific Build
```bash
setlevel 20
setstat strength 30
setstat dexterity 25
setstat intellect 40
givegold 10000
```

### Test Spell Casting
```bash
setlevel 15
setstat int 50
setmana full
giveitem scroll_komiza
read scroll_komiza
cast komiza <target>
```

### Test Shopping
```bash
givegold 50000
teleport mystic_plaza
north  # Sorcerer's Sanctum
list
buy scroll_todudaku
```

### Recovery Commands
```bash
sethealth full
setmana full
# Quick heal/mana restore
```

---

## Tips & Best Practices

1. **Start with godmode** for initial testing, then fine-tune with individual commands
2. **Use setlevel** instead of manually setting HP/mana - it auto-calculates correctly
3. **Check stats** after modifications with the `stats` command
4. **Save often** - admin commands modify your character in real-time
5. **Testing spell scrolls:** Use `giveitem scroll_<spell_name>` then `read` it
6. **Gold for shopping:** `givegold 100000` gives plenty for all scrolls

---

## Finding Item/Room/NPC IDs

### Spell Scrolls
Located in: `data/items/spell_scroll.json`
Format: `scroll_<spell_name>` (e.g., scroll_komiza, scroll_todudaku)

### Regular Items
Located in: `data/items/*.json` files organized by type
- `weapons.json`
- `armor.json`
- `consumables.json`
- `equipment.json`
- etc.

### Room IDs
Located in: `data/world/rooms/**/*.json`
Common starter areas:
- `town_square` - Main town hub
- `mystic_plaza` - Mage quarter
- `sorcerers_sanctum` - Sorcerer shop
- `divine_chapel` - Cleric shop
- `druids_grove` - Druid shop
- `warlocks_den` - Warlock shop
- `market_square` - Shopping district
- `dungeon1_1` - First dungeon

### NPC IDs
Located in: `data/npcs/*.json`
Shop vendors:
- `master_pyrus_frostweaver` - Sorcerer scrolls
- `sister_lumina` - Cleric scrolls
- `elder_thornbark` - Druid scrolls
- `malachar_the_bound` - Warlock scrolls

---

## Safety Notes

⚠️ **These are debug commands** - they modify your character directly without any gameplay restrictions.

- **No undo:** Changes are immediate and permanent (unless you reload from backup)
- **Balance:** Using admin commands can break game balance for normal play
- **Testing:** These commands are perfect for testing new features quickly
- **Database:** Changes are saved to `data/mud.db` on auto-save

---

*For production/normal gameplay, consider disabling these commands or restricting to specific admin accounts.*
