# Mob Spellcasting System

## Overview

The mob spellcasting system allows hostile mobs to cast spells during combat. Spellcasting mobs have mana pools that regenerate over time and spell cooldowns to prevent spam. Each spell has different damage, mana costs, and thematic effects.

## How It Works

### Spellcasting Mobs

Mobs with `"spellcaster": true` in their definition can cast spells. When such a mob attacks:

1. **70% chance**: Attempt to cast a spell (if mana, fatigue, and cooldowns allow)
2. **30% chance**: Use a physical attack

**Important:** After casting a spell, the mob becomes **spell fatigued** (duration: (spell_level - caster_level) × 15, minimum 15s) and will use physical attacks until fatigue expires. This prevents spell-spam and ensures alternating between spells and melee attacks.

**Example:** Level 4 Ogre Mage casting Fireball (level 5): (5-4) × 15 = **30 seconds** of spell fatigue, using only physical attacks during that time.

### Mana System

- **Mana Pool**: Each spellcasting mob has a mana pool calculated as: `50 + (level * 10) + (spell_skill / 2)`
  - Example: Level 4 mob with 60 spell_skill = 50 + 40 + 30 = 120 mana
- **Mana Regeneration**: 5 mana per second (automatic, handled in game tick)
- **Mana Costs**: Each spell has a different mana cost (5-30 mana)

### Spell Cooldowns and Fatigue

**Two Mechanisms Prevent Spell Spam:**

1. **Spell Fatigue** (affects ALL spells)
   - After casting ANY spell, caster becomes "spell fatigued"
   - Cannot cast ANY spell while fatigued
   - **Can still use physical attacks** during fatigue
   - **Duration**: (spell_level - caster_level) × 15 seconds, minimum 15 seconds
     - **Spell at level:** 15 seconds (minimum)
     - **Spell 1 level above:** 30 seconds
     - **Spell 2 levels above:** 45 seconds
     - **Spell 3 levels above:** 60 seconds
   - Example: Level 4 caster, Fireball (level 5): (5-4) × 15 = **30 seconds**
   - Example: Level 4 caster, Magic Missile (level 1): (1-4) × 15 = -45 → **15 seconds** (minimum)
   - Similar to player spell fatigue system
   - Called "magical exhaustion" in-game

2. **Individual Spell Cooldowns**: 5-15 seconds (varies by spell)
   - Each spell has its own cooldown timer
   - Prevents casting the same spell repeatedly
   - Works in addition to spell fatigue
   - Starts counting when spell is cast

### Spell Failure

Spells can fail when cast, based on several factors:

- **Base Failure Rate**: 10% chance for any spell
- **Level Penalty**: +15% failure per level if spell is above caster's level
  - Example: Level 2 mob casting level 4 spell = +30% failure
- **Intelligence Bonus**: Higher intelligence reduces failure
  - Formula: (Intelligence - 10) / 2 * 2% reduction
  - Example: Intelligence 16 = +3 modifier = -6% failure
- **Spell Skill Bonus**: Higher spell_skill reduces failure (mobs only)
  - spell_skill 50 = no bonus/penalty
  - spell_skill 100 = -5% failure
  - spell_skill 0 = +5% failure
- **Failure Range**: Minimum 5%, Maximum 95%

**When a spell fails:**
- Mana is still consumed
- Cooldown is still applied
- No damage/healing occurs
- A failure message is displayed: "{caster} attempts to cast {spell}, but the spell fizzles and fails!"

**Example Calculations:**

*Ogre Mage (Level 4, Intelligence 12, spell_skill 60) casting Fireball (min_level 5):*
- Base: 10%
- Level penalty: +15% (spell is 1 level higher)
- Intelligence bonus: -2% (modifier +1)
- Spell skill bonus: -1% (60 - 50 = +10/10 = 1%)
- **Final: 22% failure chance**

*Ogress Mage (Level 4, Intelligence 14, spell_skill 65) casting Frost Ray (min_level 2):*
- Base: 10%
- Level penalty: 0% (spell is below caster level)
- Intelligence bonus: -4% (modifier +2)
- Spell skill bonus: -1.5% (65 - 50 = +15/10 = 1.5%)
- **Final: 4.5% → clamped to 5% (minimum)**

### Spell Selection AI

Mobs choose spells intelligently:

1. **Healing Priority**: If mob's health drops below `heal_threshold` (varies by spell list), try to cast healing spell
2. **Offensive Spells**: Otherwise, randomly choose from available offensive spells
3. **Availability**: Only spells that:
   - Have sufficient mana
   - Are not on cooldown

**Note:** Mobs CAN attempt to cast spells above their level (unlike earlier versions). Higher-level spells have increased failure rates based on the level difference (see Spell Failure section).

## Spell Lists

Mobs are assigned a `spell_list` type that determines which spells they can cast and their behavior:

### Available Spell Lists

| Spell List | Spells | Heal Threshold | Aggression | Description |
|------------|--------|----------------|------------|-------------|
| **necromancer** | shadow_bolt, poison_spray, magic_missile | 30% | 80% | Dark magic and necrotic damage |
| **pyromancer** | fireball, acid_splash, magic_missile | 25% | 90% | Fire-focused aggressive caster |
| **frost_mage** | frost_ray, magic_missile, lightning_bolt | 30% | 70% | Cold and lightning spells |
| **storm_caller** | lightning_bolt, frost_ray, magic_missile | 35% | 75% | Weather-based magic |
| **dark_cultist** | shadow_bolt, eldritch_blast, poison_spray | 40% | 85% | Warlock-style dark magic |
| **priest** | sacred_flame, cure_wounds, magic_missile | 50% | 40% | Healing-focused, less aggressive |
| **warlock** | eldritch_blast, shadow_bolt, poison_spray | 30% | 80% | Eldritch and shadow magic |
| **generic_caster** | magic_missile, frost_ray, acid_splash | 30% | 60% | Basic all-purpose caster |

## Available Spells

### Damage Spells

| Spell | Damage | Mana Cost | Cooldown | Min Level | Damage Type | Description |
|-------|--------|-----------|----------|-----------|-------------|-------------|
| **Magic Missile** | 2d4+2 | 10 | 8s | 1 | Force | Unerring magical darts |
| **Fireball** | 6d6 | 30 | 15s | 5 | Fire | Massive ball of flame |
| **Lightning Bolt** | 5d8 | 25 | 12s | 3 | Lightning | Crackling electricity |
| **Frost Ray** | 3d6 | 15 | 10s | 2 | Cold | Freezing beam |
| **Acid Splash** | 2d6 | 8 | 6s | 1 | Acid | Corrosive acid |
| **Shadow Bolt** | 4d6 | 20 | 10s | 3 | Necrotic | Life-draining shadow |
| **Poison Spray** | 1d12 | 5 | 5s | 1 | Poison | Toxic fumes |
| **Eldritch Blast** | 3d10 | 10 | 8s | 2 | Force | Crackling eldritch energy |
| **Sacred Flame** | 2d8 | 10 | 8s | 1 | Radiant | Holy fire |

### Healing Spells

| Spell | Healing | Mana Cost | Cooldown | Min Level | Description |
|-------|---------|-----------|----------|-----------|-------------|
| **Heal** | 3d8 | 20 | 15s | 2 | Major healing |
| **Cure Wounds** | 2d8 | 12 | 12s | 1 | Moderate healing |

## Configuring Spellcasting Mobs

### Mob Definition

Add these properties to a mob in the mob JSON files:

```json
{
  "id": "dark_wizard",
  "name": "Dark Wizard",
  "type": "humanoid",
  "level": 3,
  "health": 30,
  "max_health": 30,
  "spellcaster": true,
  "spell_skill": 70,
  "spell_list": "necromancer",
  "loot_table": [
    {"item_id": "scroll_shadow_bolt", "chance": 0.3}
  ]
}
```

**Properties:**
- `spellcaster`: Set to `true` to enable spellcasting
- `spell_skill`: Affects mana pool (higher = more mana). Range: 0-100, typical: 50-80
- `spell_list`: Which spell list to use (see table above). Default: "generic_caster"

### Example Mobs

**Ogress Mage** (Level 4 Frost Mage):
- Spell List: frost_mage
- Spell Skill: 65
- Max Mana: ~82 (50 + 40 + 32)
- Can attempt: Frost Ray (5% fail, 15s fatigue), Magic Missile (5% fail, 15s fatigue), Lightning Bolt (5% fail, 15s fatigue)
- Heals when below 30% health
- All spells are at or below level, so failure rate is minimum (5%) and fatigue is minimum (15s)
- Can cast multiple spells per fight due to short fatigue duration

**Ogre Mage** (Level 4 Pyromancer):
- Spell List: pyromancer
- Spell Skill: 60
- Max Mana: ~80 (50 + 40 + 30)
- Can attempt: Fireball (22% fail, 30s fatigue), Acid Splash (7% fail, 15s fatigue), Magic Missile (7% fail, 15s fatigue)
- Heals when below 25% health
- Very aggressive (90% spell preference)
- Fireball often fails due to being above the mob's level
- Fireball has 30s fatigue (1 level above caster)

## Adding New Spells

Edit `data/spells/mob_spells.json`:

```json
{
  "spells": {
    "your_spell_id": {
      "name": "Spell Name",
      "damage": "XdY+Z",
      "damage_type": "force|fire|cold|lightning|etc",
      "mana_cost": 15,
      "cooldown": 10.0,
      "cast_message": "{caster} casts something at {target}!",
      "hit_message": "The spell hits for {damage} damage!",
      "min_level": 2,
      "spell_school": "evocation",
      "description": "What the spell does"
    }
  }
}
```

For healing spells, use negative damage and set `"target_self": true`:
```json
{
  "your_healing_spell": {
    "name": "Regeneration",
    "damage": "-4d6",
    "damage_type": "healing",
    "mana_cost": 15,
    "cooldown": 12.0,
    "cast_message": "{caster} channels healing energy!",
    "hit_message": "{caster} heals for {damage} hit points!",
    "min_level": 3,
    "spell_school": "restoration",
    "target_self": true
  }
}
```

## Adding New Spell Lists

Edit the `mob_spell_lists` section in `data/spells/mob_spells.json`:

```json
{
  "mob_spell_lists": {
    "your_spell_list": {
      "spells": ["spell_id_1", "spell_id_2", "spell_id_3"],
      "heal_threshold": 0.3,
      "aggression": 0.7
    }
  }
}
```

**Properties:**
- `spells`: Array of spell IDs this mob type can cast
- `heal_threshold`: Health percentage (0.0-1.0) at which mob tries to heal
- `aggression`: Not currently used, reserved for future AI improvements

## Technical Implementation

### Files

1. **data/spells/mob_spells.json** - Spell definitions and spell lists
2. **src/server/game/magic/spell_system.py** - Spell loading and mob spellcasting logic
3. **src/server/game/combat/combat_system.py** - Spell execution during combat
4. **src/server/core/async_game_engine.py** - Mana regeneration in game tick
5. **data/mobs/humanoid.json** - Example spellcasting mobs

### Key Classes

- **SpellType**: Loads and provides spell definitions
- **MobSpellcasting**: Manages mana pools, cooldowns, and spell selection
- **CombatSystem**: Integrates spellcasting into mob AI

### Combat Flow

1. Mob's turn comes up in combat AI
2. Check if mob is spellcaster
3. Initialize mana pool if needed
4. 70% chance: Try to cast spell
   - Check spell fatigue (are we magically exhausted?)
   - Choose spell based on health and availability
   - Check mana and individual spell cooldowns
   - Roll for spell failure
   - Execute spell if all checks pass
   - Apply spell fatigue ((spell_level - caster_level) × 15, min 15s)
5. 30% chance or if spell unavailable: Use physical attack
   - **Always** uses physical attack if spell fatigued
   - Spell fatigue does NOT prevent physical attacks

### Mana Regeneration

- Handled in `async_game_engine.py` tick loop
- Runs every game tick (default: 1 second)
- Regenerates 5 mana per second for all spellcasting mobs
- Auto-initializes mana for new spellcasters

### Cleanup

- When a mob dies, its mana and cooldown data is cleaned up
- Prevents memory leaks from removed mobs

## Balancing Guidelines

### Mana Costs
- Cantrips (level 1): 5-10 mana
- Low-level spells (level 2-3): 15-20 mana
- High-level spells (level 5+): 25-30 mana

### Cooldowns
- Spam spells: 5-8 seconds
- Standard spells: 10-12 seconds
- Powerful spells: 15+ seconds

### Damage
- Should be comparable to physical attacks for same level
- Higher mana cost = higher damage
- Consider: Magic Missile (always hits) vs Fireball (more damage but higher cost)

### Spell Skill
- Low-level casters: 40-50
- Mid-level casters: 55-70
- High-level casters: 75-90
- Epic casters: 95-100

## Gameplay Impact

### Player Strategy

- **Pressure casters**: Attack spellcasting mobs first to prevent high damage spells
- **Watch for heals**: When mob health gets low, expect healing spells
- **Mana pools are limited**: If you can survive the initial barrage, casters run out of mana
- **Mixed groups**: Combining casters with melee mobs creates challenging encounters
- **Spell fatigue windows**: After a mob casts a spell, it becomes spell fatigued and will only use physical attacks
  - Level 4 casting Fireball (level 5): 30 seconds of physical-only attacks
  - Level 4 casting Magic Missile (level 1): 15 seconds of physical-only attacks
  - Higher-level spells = longer fatigue
  - This is your chance to prepare, heal, or position
- **Multiple spells possible**: Lower-level spells have shorter fatigue (15s minimum), so mobs can cast multiple spells in longer fights

### Mob Diversity

- Physical attackers: Consistent damage, predictable
- Spellcasters: Burst damage, varied damage types, can heal
- Mixed encounters: More strategic and interesting combat

## Future Enhancements

1. **Buff Spells**: Shield, Haste, Strength buffs for self or allies
2. **Debuff Spells**: Slow, Weakness, Curse on players
3. **Area Spells**: Spells that hit multiple targets in a room
4. **Spell Resistance**: Player stats or items that reduce spell damage
5. **Counterspell**: Rogues or mages could interrupt enemy spells
6. **Mana Drain**: Spells or abilities that drain mob mana
7. **Spell Schools**: Resistances based on damage type (fire resistance, etc.)
8. **Intelligent Targeting**: Mobs choose weakest/lowest HP player
9. **Cooperative Casting**: Multiple casters coordinate for combos
10. **Environmental Effects**: Some spells interact with room features
