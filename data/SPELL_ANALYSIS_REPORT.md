# Comprehensive Spell Analysis Report
## Forgotten Depths MUD - All Spell Systems

**Generated:** 2025-11-01
**Total Spells Analyzed:** 91 spells across 6 spell files

---

## Executive Summary

This report provides a comprehensive analysis of all spells in the Forgotten Depths MUD game, examining spell distribution, mana costs, balance issues, and providing recommendations for standardization.

### Key Findings:
- **91 total spells** across 6 categories (Mob, Druid, Cleric, Sorcerer, Warlock, Multi-class)
- **Significant mana cost inconsistencies** detected, particularly in multi-class spells
- **Multi-class spells are 54% more expensive** on average than class-specific spells
- **Several outliers identified** that require balancing
- **Duplicate spells exist** between mob and multi-class spell files

---

## Table of Contents
1. [Spell Distribution](#spell-distribution)
2. [Mana Cost Analysis](#mana-cost-analysis)
3. [Outliers and Balance Issues](#outliers-and-balance-issues)
4. [Multi-Class vs Class-Specific Comparison](#multi-class-vs-class-specific-comparison)
5. [Recommendations](#recommendations)
6. [Appendix: Detailed Spell Tables](#appendix-detailed-spell-tables)

---

## Spell Distribution

### Spells by Class/Category

| Class/Category | Number of Spells | Percentage |
|----------------|------------------|------------|
| Warlock        | 25               | 27.5%      |
| Multi-Class    | 22               | 24.2%      |
| Cleric         | 13               | 14.3%      |
| Mob            | 11               | 12.1%      |
| Druid          | 10               | 11.0%      |
| Sorcerer       | 10               | 11.0%      |

**Observation:** Warlock has the most spells (25), while Druid and Sorcerer are tied with the fewest (10 each). Multi-class has a substantial collection with 22 spells.

### Spells by Level

| Level | Count | Min Mana | Max Mana | Avg Mana | Median Mana |
|-------|-------|----------|----------|----------|-------------|
| 1     | 5     | 5        | 12       | 9.0      | 10.0        |
| 2     | 10    | 4        | 20       | 9.0      | 5.5         |
| 3     | 2     | 20       | 25       | 22.5     | 22.5        |
| 4     | 11    | 6        | 20       | 10.6     | 8.0         |
| 5     | 1     | 30       | 30       | 30.0     | 30.0        |
| 6     | 10    | 12       | 40       | 25.4     | 29.0        |
| 8     | 13    | 15       | 35       | 22.1     | 22.0        |
| 10    | 15    | 25       | 100      | 43.5     | 35.0        |
| 12    | 7     | 30       | 50       | 44.4     | 45.0        |
| 14    | 9     | 55       | 80       | 64.2     | 60.0        |
| 16    | 5     | 65       | 150      | 90.0     | 75.0        |
| 18    | 3     | 70       | 75       | 72.3     | 72.0        |

**Observations:**
- Level 10 has the most spells (15) and highest variance (min: 25, max: 100)
- Mana costs generally increase with level, but inconsistently
- Levels 7, 9, 11, 13, 15, and 17 have **no spells**
- Level 16 shows extreme variance (65-150 mana)

### Spells by School

| School          | Count | Percentage |
|----------------|-------|------------|
| Evocation      | 67    | 73.6%      |
| Necromancy     | 8     | 8.8%       |
| Restoration    | 7     | 7.7%       |
| Illusion       | 3     | 3.3%       |
| Transmutation  | 2     | 2.2%       |
| Conjuration    | 2     | 2.2%       |
| Enchantment    | 1     | 1.1%       |
| Abjuration     | 1     | 1.1%       |

**Observation:** Evocation dominates with 73.6% of all spells. Other schools are severely underrepresented.

### Spells by Type

| Type         | Count | Percentage |
|--------------|-------|------------|
| Damage       | 50    | 54.9%      |
| Heal         | 17    | 18.7%      |
| Drain        | 8     | 8.8%       |
| Enhancement  | 7     | 7.7%       |
| Buff         | 4     | 4.4%       |
| Debuff       | 3     | 3.3%       |
| Summon       | 2     | 2.2%       |

---

## Mana Cost Analysis

### Statistical Formula Analysis

Based on regression analysis of all spells:

**Linear Formula (Best Fit):**
```
Mana Cost = 4.66 × Spell_Level - 4.01
```

**Coefficient of Determination:** This formula provides a reasonable baseline but doesn't account for:
- Area of Effect spells (typically +15-30 mana)
- Spell complexity (buff/drain/enhancement effects)
- Class restrictions

### Actual vs Predicted Mana Costs by Level

| Level | Actual Avg | Linear Formula | Quadratic (0.5×L²+2×L) | Exponential (5×1.5^L) |
|-------|------------|----------------|------------------------|----------------------|
| 1     | 9.0        | 0.6            | 2.5                    | 7.5                  |
| 2     | 9.0        | 5.3            | 6.0                    | 11.2                 |
| 3     | 22.5       | 10.0           | 10.5                   | 16.9                 |
| 4     | 10.6       | 14.6           | 16.0                   | 25.3                 |
| 6     | 25.4       | 24.0           | 30.0                   | 57.0                 |
| 8     | 22.1       | 33.3           | 48.0                   | 128.1                |
| 10    | 43.5       | 42.6           | 70.0                   | 288.3                |
| 12    | 44.4       | 51.9           | 96.0                   | 648.7                |
| 14    | 64.2       | 61.3           | 126.0                  | 1459.6               |
| 16    | 90.0       | 70.6           | 160.0                  | 3284.2               |
| 18    | 72.3       | 79.9           | 198.0                  | 7389.5               |

**Key Insight:** The linear formula provides the best fit for existing data. Exponential formulas result in absurdly high costs at higher levels.

---

## Outliers and Balance Issues

### Significantly Over/Under-Costed Spells

The following spells deviate significantly from their level peers (z-score > 1.5):

#### OVERCOSTED SPELLS

| Spell Name     | Level | Actual Mana | Expected Avg | Deviation | Class       | Notes                    |
|----------------|-------|-------------|--------------|-----------|-------------|--------------------------|
| Novadimaru     | 16    | 150         | 90.0         | +60.0     | Multi-class | Area invisibility        |
| Novadi         | 10    | 100         | 43.5         | +56.5     | Multi-class | Single invisibility      |
| Jinasutok      | 14    | 80          | 64.2         | +15.8     | Multi-class | Multi-stat enhancement   |
| Poratok        | 14    | 80          | 64.2         | +15.8     | Multi-class | Multi-stat enhancement   |
| Novadidan      | 8     | 35          | 22.1         | +12.9     | Multi-class | Charm effect             |
| Heal           | 2     | 20          | 9.0          | +11.0     | Mob         | Basic healing            |
| Kotari         | 4     | 20          | 10.6         | +9.4      | Multi-class | Cure hunger              |
| Watari         | 4     | 20          | 10.6         | +9.4      | Multi-class | Cure thirst              |

**Pattern:** Most overcosted spells are in the multi-class category, particularly utility spells (invisibility, buff, cure effects).

#### UNDERCOSTED SPELLS

| Spell Name     | Level | Actual Mana | Expected Avg | Deviation | Class      | Notes                    |
|----------------|-------|-------------|--------------|-----------|------------|--------------------------|
| Todukar        | 12    | 30          | 44.4         | -14.4     | Sorcerer   | Single-target fire, scales |
| Poison Spray   | 1     | 5           | 9.0          | -4.0      | Mob        | Single-target poison     |

**Observation:** Very few undercosted spells exist, suggesting the system leans toward higher costs overall.

---

## Multi-Class vs Class-Specific Comparison

### Statistical Comparison

| Metric                  | Multi-Class | Class-Specific | Difference |
|-------------------------|-------------|----------------|------------|
| Total Spells            | 22          | 69             | -         |
| Average Mana Cost       | 46.2        | 29.9           | +54.5%    |
| Average Spell Level     | 7.5         | 8.3            | -0.8      |
| Most Common Type        | Heal        | Damage         | -         |

**Key Finding:** Multi-class spells cost 54.5% more mana on average despite being 0.8 levels lower on average. This suggests a significant premium for multi-class accessibility.

### Type Distribution Comparison

| Type        | Multi-Class Count | Multi-Class Avg Mana | Class-Specific Count | Class-Specific Avg Mana |
|-------------|-------------------|----------------------|----------------------|-------------------------|
| Damage      | 2                 | 7.5                  | 48                   | 27.7                    |
| Heal        | 8                 | 41.9                 | 9                    | 29.9                    |
| Buff        | 4                 | 67.0                 | 0                    | -                       |
| Enhancement | 7                 | 51.9                 | 0                    | -                       |
| Debuff      | 1                 | 35.0                 | 2                    | 42.5                    |
| Drain       | 0                 | -                    | 8                    | 32.5                    |
| Summon      | 0                 | -                    | 2                    | 57.5                    |

**Observations:**
- **Multi-class focuses on utility:** All buff and enhancement spells are multi-class only
- **Drain and Summon are class-specific:** These effects are not available to multi-class
- **Multi-class healing is more expensive:** 41.9 vs 29.9 average mana (40% premium)

### Duplicate Spells

Two spells appear in multiple files with different stats:

#### Magic Missile
- **Mob version:** Level 1, 10 mana
- **Multi-class version:** Level 2, 5 mana
- **Issue:** Same spell, different levels and costs (multi-class version is cheaper!)

#### Lightning Bolt
- **Mob version:** Level 3, 25 mana, damage: 5d8
- **Multi-class version:** Level 4, 10 mana, damage: 4d6
- **Issue:** Multi-class version is higher level but costs 60% less mana

**Recommendation:** Consolidate duplicate spells and standardize stats.

---

## Recommendations

### 1. Mana Cost Formula Standardization

Implement a tiered formula system:

#### Base Formula (Single-Target Damage)
```
Base Mana = 5 × Spell_Level
```

#### Modifiers
- **Area of Effect:** +15 mana (or +3 × Spell_Level for scaling)
- **Additional Effects (drain, buff, enhancement):** +10 mana
- **Healing Spells:** +5 mana
- **Scales with Level:** +5 mana
- **Multi-stat Enhancement/Drain:** +10 mana
- **Utility Effects (invisibility, charm):** +15 mana

#### Example Applications:
- **Level 4 Lightning Bolt (single-target):** 5 × 4 = 20 mana
- **Level 10 Area Fire Storm:** (5 × 10) + 15 = 65 mana
- **Level 6 Enhancement (3 stats):** (5 × 6) + 10 + 10 = 50 mana
- **Level 10 Invisibility:** (5 × 10) + 15 = 65 mana

### 2. Address Specific Outliers

| Spell        | Current Mana | Recommended Mana | Rationale                                    |
|--------------|--------------|------------------|----------------------------------------------|
| Novadi       | 100          | 65               | Level 10 invisibility: (5×10)+15            |
| Novadimaru   | 150          | 95               | Level 16 area invisibility: (5×16)+15       |
| Heal (mob)   | 20           | 15               | Level 2 healing: (5×2)+5                    |
| Kotari       | 20           | 25               | Level 4 utility cure: (5×4)+5               |
| Watari       | 20           | 25               | Level 4 utility cure: (5×4)+5               |
| Todukar      | 30           | 45               | Level 12 scaling damage: (5×12)-15+5        |

### 3. Fill Level Gaps

Currently missing levels: 7, 9, 11, 13, 15, 17

**Recommendation:** Create at least 1-2 spells per missing level for each class to provide smoother progression.

### 4. Balance School Distribution

Current state: Evocation = 73.6%, all others combined = 26.4%

**Recommendation:** Diversify spell schools:
- Convert some evocation damage spells to appropriate schools (e.g., ice damage → conjuration)
- Add more abjuration defensive spells
- Expand illusion and enchantment schools for crowd control
- Create more necromancy spells for warlocks

### 5. Consolidate Duplicate Spells

**Magic Missile and Lightning Bolt** appear in both mob and multi-class files.

**Recommendation:**
- Keep multi-class versions only
- Update mob spell lists to reference multi-class spell definitions
- Standardize stats: Magic Missile (Level 1, 5 mana), Lightning Bolt (Level 3, 20 mana)

### 6. Multi-Class Spell Premium

Current: +54.5% mana cost average for multi-class spells

**Recommendation:** Establish clear pricing policy:
- **Option A (Current):** Maintain premium for accessibility (suggest 20-30% instead of 54%)
- **Option B (Balanced):** Eliminate premium, rely on class restrictions for balance
- **Option C (Hybrid):** Premium only on powerful utility spells (invisibility, multi-stat buffs)

### 7. Create Spell Tiers

Organize spells into clear progression tiers:

| Tier     | Levels | Base Mana Range | Purpose                          |
|----------|--------|-----------------|----------------------------------|
| Cantrips | 1-2    | 5-10            | Basic attacks, minor utility     |
| Novice   | 3-6    | 15-30           | Core combat spells               |
| Adept    | 7-10   | 35-55           | Power spells, area effects       |
| Expert   | 11-14  | 60-85           | Devastating effects, strong CC   |
| Master   | 15-18  | 90-120          | Ultimate abilities               |

---

## Appendix: Detailed Spell Tables

### Level 1 Spells (5 total)

| Spell Name    | Class | Mana | Type   | School       | Damage   | AoE    |
|---------------|-------|------|--------|--------------|----------|--------|
| Poison Spray  | Mob   | 5    | Damage | Conjuration  | 1d12     | Single |
| Acid Splash   | Mob   | 8    | Damage | Conjuration  | 2d6      | Single |
| Magic Missile | Mob   | 10   | Damage | Evocation    | 2d4+2    | Single |
| Sacred Flame  | Mob   | 10   | Damage | Evocation    | 2d8      | Single |
| Cure Wounds   | Mob   | 12   | Damage | Restoration  | -2d8     | Single |

### Level 2 Spells (10 total)

| Spell Name      | Class       | Mana | Type   | School        | Effect          | AoE    |
|-----------------|-------------|------|--------|---------------|-----------------|--------|
| Motu            | Cleric      | 4    | Heal   | Restoration   | 5d8 healing     | Single |
| Pakaza          | Druid       | 5    | Damage | Evocation     | 4d2 piercing    | Single |
| Komiza          | Sorcerer    | 5    | Damage | Evocation     | 10d2-8 cold     | Single |
| Teka            | Warlock     | 5    | Damage | Transmutation | 7d3-5 force     | Single |
| Magic Missile   | Multi-class | 5    | Damage | Evocation     | 2d4+2 force     | Single |
| Shield          | Multi-class | 6    | Buff   | Abjuration    | +3 AC, 600s     | Self   |
| Eldritch Blast  | Mob         | 10   | Damage | Evocation     | 3d10 force      | Single |
| Frost Ray       | Mob         | 15   | Damage | Evocation     | 3d6 cold        | Single |
| Fadi            | Multi-class | 15   | Heal   | Restoration   | 8d2-6 regen     | Single |
| Heal            | Mob         | 20   | Damage | Restoration   | -3d8 healing    | Single |

### Level 10 Spells (15 total)

| Spell Name    | Class       | Mana | Type        | School      | Effect              | AoE    |
|---------------|-------------|------|-------------|-------------|---------------------|--------|
| Kusamotu      | Cleric      | 25   | Heal        | Restoration | 15d10 healing       | Single |
| Pakazuma      | Druid       | 28   | Damage      | Evocation   | 20d3-10 piercing    | Single |
| Giteka        | Warlock     | 28   | Damage      | Evocation   | 16d8 force          | Single |
| Takumaru      | Warlock     | 30   | Debuff      | Necromancy  | Paralyze 5s         | Single |
| Torazuma      | Druid       | 32   | Damage      | Evocation   | 16d4 force          | Single |
| Gitami        | Cleric      | 32   | Damage      | Evocation   | 16d4 force          | Single |
| Kamotumaru    | Cleric      | 35   | Heal        | Evocation   | 8d4 area heal       | Area   |
| Komidaku      | Sorcerer    | 35   | Damage      | Evocation   | 16d4 cold           | Area   |
| Dobumaru      | Warlock     | 35   | Damage      | Evocation   | Poison area         | Area   |
| Komizadaku    | Sorcerer    | 40   | Damage      | Evocation   | 5d2-4 cold, scales  | Area   |
| Kamazadaku    | Warlock     | 42   | Drain       | Evocation   | Area mana drain     | Area   |
| Kotarimaru    | Multi-class | 60   | Heal        | Evocation   | Area cure hunger    | Area   |
| Watarimaru    | Multi-class | 60   | Heal        | Evocation   | Area cure thirst    | Area   |
| Yarimaru      | Multi-class | 70   | Enhancement | Evocation   | +2 AC area          | Area   |
| Novadi        | Multi-class | 100  | Buff        | Illusion    | Invisibility 300s   | Single |

### All Spells by Class

#### Cleric (13 spells)
Levels: 2, 4, 8, 10, 12, 14, 18
Focus: Healing (8 heal spells), radiant damage (3 spells), area support

#### Druid (10 spells)
Levels: 2, 4, 6, 8, 10, 12, 14, 16, 18
Focus: Nature damage (piercing, force, lightning), area effects at high levels

#### Sorcerer (10 spells)
Levels: 2, 4, 6, 8, 10, 12, 14, 18
Focus: Elemental damage (ice/fire), area devastation spells

#### Warlock (25 spells)
Levels: 2, 4, 6, 8, 10, 12, 14, 16
Focus: Dark energy, drain effects, debuffs, summons, most diverse spell list

#### Multi-class (22 spells)
Levels: 2, 4, 6, 8, 10, 14, 16
Focus: Utility, buffs, enhancements, healing, no damage focus

#### Mob (11 spells)
Levels: 1, 2, 3, 5
Focus: Basic combat spells for NPCs, low-level only

---

## Conclusion

The spell system shows significant variety but suffers from:
1. **Inconsistent mana cost scaling** (especially for multi-class spells)
2. **Level gaps** (no spells at levels 7, 9, 11, 13, 15, 17)
3. **School imbalance** (73% evocation)
4. **Duplicate spells** with conflicting stats
5. **Unclear multi-class pricing policy**

**Priority Actions:**
1. Implement standardized mana cost formula
2. Rebalance the 8 identified outlier spells
3. Consolidate duplicate spells
4. Fill level gaps for smoother progression
5. Clarify multi-class spell premium policy (recommend 20-30% instead of 54%)

**Impact:** These changes will create a more balanced, predictable progression system that rewards player advancement appropriately while maintaining class distinction and spell diversity.

---

**Report compiled by:** Comprehensive spell analysis script
**Spell files analyzed:**
- `/data/spells/mob_spells.json`
- `/data/spells/druid_spells.json`
- `/data/spells/cleric_spells.json`
- `/data/spells/sorcerer_spells.json`
- `/data/spells/warlock_spells.json`
- `/data/spells/multi_class_spells.json`
