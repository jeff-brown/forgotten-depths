# Mage Quarter Expansion

New magical district added to the starter town of Millhaven, featuring specialized spell scroll vendors for each spellcasting class.

## Overview

The **Mage Quarter** is a dedicated magical learning district accessible from Arcane Square. It features four specialized magic shops, each run by a master of their respective magical tradition, surrounding a central plaza.

## Town Layout

### Navigation Path
```
Town Square
    ↓ (south via town_path)
Arcane Square
    ↓ (southeast)
Mystic Plaza (NEW - Central Hub)
    ├── North: Sorcerer's Sanctum (NEW)
    ├── South: Warlock's Den (NEW)
    ├── East: Druid's Grove (NEW)
    └── West: Divine Chapel (NEW)
```

### Quick Directions from Town Square
```
south, southeast  → Reaches Mystic Plaza
```

## New Locations

### 1. Mystic Plaza (mystic_plaza)
**Central Hub of the Mage Quarter**

A magnificent circular courtyard with polished marble floors inlaid with silver runes. Four ornate archways mark the cardinal directions, each leading to a specialized magic shop. A floating crystal sculpture at the center casts prismatic light across the plaza.

**NPCs:**
- Arcane Scholar Meridian - Helpful guide who can provide information about each shop

**Exits:**
- North → Sorcerer's Sanctum
- South → Warlock's Den
- East → Druid's Grove
- West → Divine Chapel
- Northwest → Arcane Square (return to town)

---

### 2. Sorcerer's Sanctum (sorcerers_sanctum)
**Elemental Evocation Specialist**

An elegant establishment radiating raw arcane power. Walls lined with crystalline shelves, flames dancing in blue and crimson braziers, and delicate ice crystals floating through the air.

**Vendor:** Master Pyrus Frostweaver (Level 20)
- **Specialty:** Sorcerer evocation spells (fire & ice)
- **Buy Rate:** 40% of item value
- **Sell Markup:** 1.5x base price

**Inventory:**
| Scroll | Level | Price | Stock |
|--------|-------|-------|-------|
| Komiza (Ice Shard) | 2 | 150g | 5 |
| Toduza (Flame Bolt) | 4 | 300g | 4 |
| Komizuma (Ice Shower) | 6 | 500g | 3 |
| Toduzuma (Flame Shower) | 8 | 900g | 3 |
| Komidaku (Ice Storm AOE) | 10 | 1500g | 2 |
| Komizadaku (Ice Storm AOE, Scales) | 10 | 2000g | 2 |
| Todudaku (Firestorm AOE) | 12 | 3500g | 1 |
| Todukar (Fireball, Scales) | 12 | 2500g | 2 |
| Komasidaku (Fire & Ice Storm AOE, Scales) | 14 | 4500g | 1 |
| Dumoti (Elemental Maelstrom AOE, Scales) | 18 | 7000g | 1 |

---

### 3. Divine Chapel of Sacred Scrolls (divine_chapel)
**Healing & Holy Magic Specialist**

A peaceful sanctuary filled with soft golden light from hanging censers. Pristine white shelves hold blessed spell scrolls, and the scent of incense fills the air.

**Vendor:** Sister Lumina (Level 18)
- **Specialty:** Cleric divine & restoration spells
- **Buy Rate:** 45% of item value
- **Sell Markup:** 1.4x base price

**Inventory:**
| Scroll | Level | Price | Stock |
|--------|-------|-------|-------|
| Motu (Minor Heal) | 2 | 100g | 6 |
| Kamotu (Heal) | 4 | 250g | 5 |
| Tami (Weak Force Beam) | 4 | 300g | 4 |
| Dobudanimaru (Cure Poison AOE) | 8 | 700g | 3 |
| Gimotu (Greater Heal) | 8 | 700g | 3 |
| Katami (Force Beam) | 8 | 900g | 3 |
| Motumaru (Heal AOE) | 8 | 800g | 2 |
| Gitami (Brilliant Force Beam) | 10 | 1800g | 2 |
| Kamotumaru (Greater Heal AOE) | 10 | 1800g | 2 |
| Kusamotu (Powerful Heal, Scales) | 10 | 1500g | 2 |
| Kusatami (Devastating Force Beam) | 12 | 2800g | 1 |
| Gimotumaru (Greater Heal AOE) | 14 | 3500g | 1 |
| Kusamotumaru (Powerful Heal AOE, Scales) | 18 | 5500g | 1 |

---

### 4. Druid's Grove (druids_grove)
**Nature Magic Specialist**

Feels like stepping into an ancient forest glade. Living vines climb the walls with glowing flowers, and a massive hollow oak tree serves as a display case. Moss carpets the floor.

**Vendor:** Elder Thornbark (Level 19)
- **Specialty:** Druid nature spells
- **Buy Rate:** 45% of item value
- **Sell Markup:** 1.4x base price

**Inventory:**
| Scroll | Level | Price | Stock |
|--------|-------|-------|-------|
| Ganazi | 2 | 200g | 5 |
| Kamaza | 4 | 300g | 4 |
| Giteka | 6 | 500g | 4 |
| Gimuda | 8 | 700g | 3 |
| Kamuda | 10 | 900g | 3 |
| Kamazadaku (AOE) | 14 | 1800g | 2 |
| Dakima | 10 | 1500g | 2 |
| Dakidaku (AOE) | 18 | 3500g | 1 |

---

### 5. Warlock's Den (warlocks_den)
**Eldritch Pact Magic Specialist**

A dimly lit establishment where shadows cling to corners. Spell scrolls float in mid-air, suspended by tendrils of dark energy and glowing with fel green light. Strange symbols writhe across the walls.

**Vendor:** Malachar the Bound (Level 17)
- **Specialty:** Warlock pact & eldritch spells
- **Buy Rate:** 35% of item value (lowest in town - dark magic is risky)
- **Sell Markup:** 1.6x base price (highest markup - forbidden knowledge is expensive)

**Inventory:**
| Scroll | Level | Price | Stock |
|--------|-------|-------|-------|
| Dobuza | 2 | 200g | 5 |
| Dobumaru | 6 | 600g | 3 |
| Jinasudani | 8 | 800g | 3 |
| Jinasutok | 10 | 1200g | 2 |
| Igadani | 12 | 1500g | 2 |
| Dobudakidaku (AOE) | 18 | 3000g | 1 |

---

## Files Created

### Room Definitions
- `data/world/rooms/mystic_plaza.json` - Central hub
- `data/world/rooms/sorcerers_sanctum.json` - Sorcerer shop
- `data/world/rooms/divine_chapel.json` - Cleric shop
- `data/world/rooms/druids_grove.json` - Druid shop
- `data/world/rooms/warlocks_den.json` - Warlock shop

### NPC/Vendor Definitions
- `data/npcs/master_pyrus_frostweaver.json` - Sorcerer vendor
- `data/npcs/sister_lumina.json` - Cleric vendor
- `data/npcs/elder_thornbark.json` - Druid vendor
- `data/npcs/malachar_the_bound.json` - Warlock vendor
- `data/npcs/arcane_scholar.json` - Plaza NPC helper

### Modified Files
- `data/world/rooms/arcane_square.json` - Added southeast exit to mystic_plaza

---

## Gameplay Notes

### For Players

**Getting Started:**
1. From Town Square, go **south** then **southeast** to reach Mystic Plaza
2. Talk to Arcane Scholar Meridian for guidance
3. Visit the appropriate shop for your class
4. Buy scrolls and **read** them to learn spells permanently

**Scroll Pricing:**
- Lower level scrolls (2-6): 100-700g
- Mid level scrolls (8-12): 700-3500g
- High level scrolls (14-18): 3500-7000g
- AOE and scaling spells cost more

**Stock Replenishment:**
- Vendors restock every 5 minutes (300 seconds)
- Limited quantity scrolls will replenish to initial stock levels
- High-level scrolls (stock: 1-2) are rare - grab them when you can!

### For Developers

**Vendor System Integration:**
- All vendors use the existing vendor system in `src/server/game/vendors/vendor_system.py`
- NPCs with `"services": ["shop"]` and a `shop` object are automatically loaded as vendors
- Room files with `vendor_id` property link to vendor NPCs
- Scroll items already exist in `data/items/spell_scroll.json`

**Testing:**
```bash
# Start server
python main.py

# Navigate to Mage Quarter
south
southeast

# List available shops
look

# Visit a shop (example: sorcerer)
north
list
buy scroll_komiza
read scroll_komiza
spellbook
```

---

## Design Philosophy

### Specialized vs. General Magic Shops

**The Old Arcane Emporium** (magic_shop in Arcane Square):
- Still exists for general magic items, potions, components
- May have a few common multi-class scrolls

**The New Mage Quarter:**
- **Specialization:** Each shop focuses on one magical tradition
- **Flavor:** Each vendor has unique personality and shop atmosphere
- **Economics:** Different buy/sell rates reflect vendor attitudes
- **Discovery:** Players must explore to find the best scrolls for their class

### Vendor Personalities

Each vendor reflects their magical tradition:
- **Pyrus** (Sorcerer): Confident, dramatic, proud of raw power
- **Lumina** (Cleric): Compassionate, serene, focused on service
- **Thornbark** (Druid): Ancient, wise, speaks of nature's balance
- **Malachar** (Warlock): Mysterious, ominous, hints at dark bargains

---

## Future Expansion Ideas

- **Bard's Stage:** Performance venue selling bard spells and instruments
- **Ranger's Lodge:** Wilderness outpost for ranger spells and tracking supplies
- **Mystic Library:** Research center where players can combine or modify spells
- **Spell Crafting:** Allow players to create custom spell variations
- **Quest Lines:** Each vendor could offer class-specific quests for rare spells
- **Reputation System:** Discounts for loyal customers of each tradition

---

*The Mage Quarter awaits! Choose your path wisely, young spellcaster.*
