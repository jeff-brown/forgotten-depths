# Spell System Testing Guide

Quick reference for testing the new spell system enhancements.

## Quick Test Commands

### 1. Test AOE Spells
```bash
# Find a room with multiple mobs
look
# Cast an area spell
cast komidaku
# Should damage all mobs in the room with one damage roll
```

### 2. Test Spell Scaling
```bash
# Create/use a high-level character (10+)
# Buy/learn a low-level spell with "scales_with_level": "Yes"
# Examples: komizadaku, todukar, kusamotu

cast todukar orc
# Damage should be significantly higher than base dice roll
```

### 3. Test Mana Regeneration
```bash
# Cast a spell to use mana
cast komiza orc

# Check current mana
stats

# Wait 30 seconds
# Check mana again - should have regenerated
stats
```

### 4. Test Spell Failure
```bash
# Use a low-level character (1-3)
# Try to cast a high-level spell (10+)

cast todudaku
# High chance of: "You attempt to cast Todudaku, but the spell fizzles and fails!"
# Note: Mana is still consumed
```

### 5. Test Enhancement Buffs
```bash
# Learn an enhancement spell (igatok, rotok, etc.)
# Check current stats
stats

# Cast enhancement
cast igatok
# Should see: "Your agility increases by X! (old -> new)"

# Check stats again
stats
# Dexterity should be higher

# Wait for buff to expire (or wait 5-10 minutes for typical duration)
# Should see: "The Igatok effect has worn off."

# Check stats one more time
stats
# Dexterity should be back to original value
```

## Spell Examples by Feature

### AOE Damage Spells (Sorcerer)
- **komidaku** - Level 10, 16d4 cold, area
- **todudaku** - Level 12, 32-96 fire, area
- **komasidaku** - Level 14, 7d2-6 cold, area
- **dumoti** - Level 18, 8d2-4 cold, area

### Scaling Damage Spells
- **komizadaku** (Sorcerer L10) - Scales
- **todukar** (Sorcerer L12) - Scales
- **komasidaku** (Sorcerer L14) - Scales
- **dumoti** (Sorcerer L18) - Scales

### Scaling Healing Spells (Cleric)
- **kusamotu** (Cleric L10) - 30-150 healing, scales
- **kusamotumaru** (Cleric L18) - 30-120 area healing, scales

### Enhancement Spells (Multi-class)
- **igatok** (L6) - Enhance Agility (+5d4 DEX)
- **rotok** (L6) - Enhance Constitution (+5d4 CON)
- **darok** (L6) - Enhance Vitality (+5d4 VIT)
- **shield** (L2) - AC Bonus (+3 AC, 600 rounds)

## Character Setup for Testing

### Option 1: Create New Mage Character
```
1. Start server: python main.py
2. Connect: python src/client/terminal_client.py
3. Create character: Choose Sorcerer or Cleric
4. You'll start at level 1 with no spells
```

### Option 2: Buy Spell Scrolls
```
# Find a magic shop (check vendor locations)
list
buy scroll_of_komiza
buy scroll_of_igatok

# Learn the spells
read scroll_of_komiza
read scroll_of_igatok

# View your spellbook
spellbook
```

### Option 3: Admin Character (if database tools available)
```sql
-- Increase character level
UPDATE characters SET level = 15 WHERE player_id = 1;

-- Give lots of gold for buying scrolls
UPDATE characters SET gold = 10000 WHERE player_id = 1;
```

## Expected Behavior Checklist

### ✓ AOE Spells
- [x] Single damage roll applied to all mobs
- [x] Each mob shows individual damage message
- [x] Defeated mobs drop loot
- [x] Survivors become aggressive
- [x] Room notification sent

### ✓ Spell Scaling
- [x] Higher level = more damage/healing
- [x] Formula: base × (1 + (caster_level - spell_level) × 0.10)
- [x] Only applies to spells with "scales_with_level": "Yes"
- [x] Works for damage, healing, and AOE spells

### ✓ Mana Regeneration
- [x] Regenerates at INT/40 per tick
- [x] Continues even at full health
- [x] No hunger/thirst penalty
- [x] Visible in stats command

### ✓ Spell Failure
- [x] 5% base failure rate
- [x] +10% per level above caster
- [x] -1% per INT modifier point
- [x] Capped at 0-50%
- [x] Mana consumed even on failure
- [x] Clear failure message

### ✓ Enhancement Buffs
- [x] Stats increase immediately
- [x] Shows old → new value
- [x] Effect tracked in active_effects
- [x] Stats restore when buff expires
- [x] Expiration notification sent

## Debugging Commands

```bash
# Check character data (if you have database access)
python scripts/admin_tools.py list-characters

# Check spell data is loaded
python -c "from src.server.config.config_manager import ConfigManager; cm = ConfigManager(); print(len(cm.game_data['spells']), 'spells loaded')"

# Validate JSON files
python -c "import json; json.load(open('data/spells/sorcerer_spells.json'))"
```

## Common Issues

### "Unknown spell: X"
- Spell not in character's spellbook
- Use `spellbook` to see known spells
- Use `read scroll_of_X` to learn new spells

### "You don't have enough mana"
- Wait for mana to regenerate
- Mana regen rate: INT / 40 per second
- Example: 16 INT = 0.4 mana/sec = 24 mana/min

### Spell fizzles frequently
- Check caster level vs spell level
- Increase Intelligence to reduce failure rate
- Use spells appropriate for your level

### AOE spell says "no enemies"
- Room has no mobs
- Move to a different room
- Try spawning mobs if in test environment

### Enhancement doesn't show effect
- Check spell type is "enhancement"
- Verify `effect_amount` field exists
- Ensure effect name matches supported effects

## Performance Testing

Test with multiple simultaneous actions:
```bash
# Terminal 1: Player 1 casts AOE spell
cast komidaku

# Terminal 2: Player 2 casts single-target spell
cast komiza orc

# Terminal 3: Player 3 uses enhancement
cast igatok
```

All should work smoothly without conflicts.

---

## Next Steps After Testing

Once Option A features are verified:
1. Document any bugs found
2. Adjust balance as needed
3. Plan Option B enhancements (visual effects, spell resistance)
4. Plan Option C polish (balance tuning, new spells)

---

*Happy spell slinging!* 🧙‍♂️✨
