# Spell System Enhancements - Option A Implementation

This document describes the completed enhancements to the Forgotten Depths spell casting system (Option A: Complete Missing Features).

## Summary of Changes

All five missing features from Option A have been successfully implemented:

1. ✅ **AOE Spells** - Area-of-effect spells now hit all mobs in room
2. ✅ **Spell Level Scaling** - Damage and healing scale with caster level
3. ✅ **Player Mana Regeneration** - Already implemented (verified)
4. ✅ **Spell Failure Chances** - Players can fail spell casts based on level/intelligence
5. ✅ **Active Buff Effects** - Enhancement spells modify character stats dynamically

---

## 1. Area-of-Effect (AOE) Spells

**Location:** `src/server/commands/command_handler.py:3591-3664`

### Implementation Details
- AOE spells (where `requires_target: false` and `range: "area"`) now damage all mobs in the current room
- Damage is rolled once and applied to all targets
- Each mob that survives becomes aggro'd on the caster
- Defeated mobs drop loot and award experience normally
- Clear visual feedback shows damage to each mob

### Example AOE Spells
- **Komidaku** (Sorcerer, Level 10) - Ice storm, 16d4 cold damage
- **Todudaku** (Sorcerer, Level 12) - Firestorm, 32-96 fire damage
- **Dumoti** (Sorcerer, Level 18) - Maelstrom, 8d2-4 cold damage

### Testing
```
# In a room with multiple mobs:
cast komidaku

Expected output:
> You cast Komidaku! A wave of cold energy fills the room!
>   Goblin takes 42 cold damage!
>   Orc takes 42 cold damage!
>   Troll takes 42 cold damage!
```

---

## 2. Spell Level Scaling

**Location:** `src/server/commands/command_handler.py:3743-3768`

### Implementation Details
- New method: `_calculate_scaled_spell_value()`
- Spells with `"scales_with_level": "Yes"` gain bonus damage/healing
- **Scaling Formula:** Base Value × (1.0 + (Caster Level - Spell Level) × 0.10)
- Example: Level 10 caster with Level 2 spell = +80% effectiveness (8 level difference × 10%)

### Applied To
- Single-target damage spells (`_cast_damage_spell`)
- AOE damage spells (area spells)
- Healing spells (`_cast_heal_spell`)

### Example Scaling Spells
- **Komizadaku** (Sorcerer, Level 10) - Scales with level
- **Todukar** (Sorcerer, Level 12) - Scales with level
- **Kusamotu** (Cleric, Level 10) - Healing scales with level

### Testing
```
# Level 15 character casting Level 2 spell (Komiza, base: 10d2-8)
# Expected scaling: +130% (13 level difference)
# Base roll: 12 → Scaled: 27 damage

cast komiza orc
> You cast Komiza! It strikes Orc for 27 cold damage!
```

---

## 3. Player Mana Regeneration

**Location:** `src/server/core/async_game_engine.py:395-397`

### Implementation Details
- **Already Implemented** - Verified existing system
- Mana regenerates every game tick (1 second by default)
- **Regeneration Rate:** Intelligence / 40 per tick
- Example: 16 INT = 0.4 mana/tick = 24 mana/minute
- Regeneration continues even at full health
- No regeneration penalty from hunger/thirst (unlike health)

### Testing
```
# Check mana regeneration:
1. Use spell to consume mana
2. Wait 10-15 seconds
3. Check character sheet - mana should increase
```

---

## 4. Spell Failure Chances for Players

**Location:** `src/server/commands/command_handler.py:3434-3456, 3806-3836`

### Implementation Details
- New method: `_calculate_player_spell_failure_chance()`
- Spell can fail after mana/fatigue costs are applied
- **Failure Formula:**
  - Base: 5% failure rate
  - +10% per level if spell level > caster level
  - -1% per intelligence modifier point
  - Clamped: 0% - 50% maximum

### Example Failure Chances
| Caster Level | INT | Spell Level | Failure Chance |
|-------------|-----|-------------|----------------|
| 5 | 14 | 2 | 3% (5% base - 2% INT bonus) |
| 5 | 14 | 8 | 33% (5% base + 30% level penalty - 2% INT) |
| 10 | 18 | 10 | 1% (5% base - 4% INT bonus) |
| 1 | 10 | 10 | 50% (capped at 50%) |

### Testing
```
# Low-level character casting high-level spell:
cast todudaku
> You attempt to cast Todudaku, but the spell fizzles and fails!

# Note: Mana is still consumed, teaching the importance of appropriate spell selection
```

---

## 5. Active Buff Effects on Character Stats

**Location:**
- `src/server/commands/command_handler.py:3730-3813` (application)
- `src/server/core/async_game_engine.py:519-575` (expiration)

### Implementation Details

#### Enhancement Spell Application
- Enhancement spells (`type: "enhancement"`) directly modify character stats
- Effect amount is rolled from `effect_amount` field (e.g., "+5d4")
- Stats are immediately increased when spell is cast
- Clear feedback shows old → new stat values

#### Effect Removal on Expiration
- When buff duration reaches 0, stat bonuses are automatically removed
- Character receives notification when buff expires
- Stats cannot drop below 1 (safety check)

#### Supported Enhancement Effects
- `enhance_agility` → Increases Dexterity
- `enhance_strength` → Increases Strength
- `enhance_constitution` → Increases Constitution
- `enhance_vitality` → Increases Vitality
- `enhance_intelligence` → Increases Intelligence
- `enhance_wisdom` → Increases Wisdom
- `enhance_charisma` → Increases Charisma
- `ac_bonus` → Increases Armor Class (visual feedback only for now)
- `invisible` → Invisibility effect (visual feedback only for now)

### Example Enhancement Spells
- **Igatok** (Level 6) - Enhance Agility (+5d4 DEX)
- **Rotok** (Level 6) - Enhance Constitution (+5d4 CON)
- **Darok** (Level 6) - Enhance Vitality (+5d4 VIT)
- **Shield** (Level 2) - AC bonus (+3 AC, 600 round duration)

### Testing
```
# Cast enhancement spell:
cast igatok
> You cast Igatok! Your agility increases by 12! (15 -> 27)

# Wait for duration to expire (or use 'effects' command to check):
> The Igatok effect has worn off.
# Dexterity returns to 15

# Check current buffs:
spellbook
# Shows active effects with durations
```

---

## Files Modified

### Primary Changes
1. **src/server/commands/command_handler.py**
   - AOE spell implementation (3591-3664)
   - Spell scaling system (3743-3768)
   - Spell failure checking (3434-3456, 3806-3836)
   - Enhancement buff application (3730-3813)

2. **src/server/core/async_game_engine.py**
   - Enhancement buff expiration (519-575)
   - Verified mana regeneration (395-397)

### No Changes Required
- Spell data files are already properly formatted
- ConfigManager loads all spell types correctly
- Character migration adds required fields

---

## Spell Data Format Requirements

For spells to use these new features, ensure the following fields are set:

### AOE Spells
```json
{
  "name": "Fireball",
  "type": "damage",
  "range": "area",
  "requires_target": false,
  "damage": "8d6",
  "damage_type": "fire"
}
```

### Scaling Spells
```json
{
  "name": "Magic Missile",
  "type": "damage",
  "damage": "3d4+3",
  "scales_with_level": "Yes"
}
```

### Enhancement Spells
```json
{
  "name": "Bull's Strength",
  "type": "enhancement",
  "effect": "enhance_strength",
  "effect_amount": "+2d6",
  "duration": 300
}
```

---

## Gameplay Impact

### Balance Considerations
1. **AOE Spells** - Now extremely powerful for clearing multiple weak mobs, but risky (aggros everything)
2. **Scaling** - High-level characters casting low-level spells remain effective
3. **Failure Chances** - Discourages casting spells far above character level
4. **Enhancements** - Temporary stat boosts create tactical depth

### Recommended Next Steps (Options B & C)
- **Option B: Enhance Existing Features**
  - Add color coding for spell damage types
  - Implement spell resistance/saving throws
  - Add concentration checks for maintaining buffs

- **Option C: Polish & Balance**
  - Review mana costs vs. damage output
  - Adjust spell fatigue durations
  - Balance AOE vs single-target spell effectiveness

---

## Testing Checklist

- [ ] AOE spell hits all mobs in room
- [ ] Scaled spells deal/heal more at higher levels
- [ ] Mana regenerates over time
- [ ] Spells can fail with appropriate messages
- [ ] Enhancement spells increase stats immediately
- [ ] Enhancement effects expire and remove stat bonuses
- [ ] Spell scrolls can still be read to learn spells
- [ ] Spell fatigue prevents spam casting
- [ ] Class restrictions still enforced
- [ ] Mana costs still deducted correctly

---

## Known Limitations

1. **AC Bonus** - Shield spell provides visual feedback but AC bonus not yet integrated into combat calculations
2. **Invisibility** - Visual effect only, not integrated with mob aggro system yet
3. **Debuff Spells** - Debuff type handled but no debuff spells currently use stat reduction
4. **Multi-target Enhancements** - Enhancement spells only target self currently

These limitations can be addressed in Option B (Enhance Existing Features).

---

## Performance Notes

- AOE spells iterate through room mobs once (O(n) complexity)
- Spell scaling adds negligible computation (simple multiplication)
- Buff/debuff tracking adds one effect object per active buff
- No performance concerns for typical gameplay (< 10 active buffs per player)

---

*Last Updated: 2025-10-25*
*Implementation: Complete*
*Status: Ready for Testing*
