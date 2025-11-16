# World1 Zone Connection Map

**Generated**: November 16, 2025
**Source**: Zone connection analysis

## Key Findings

### The Big Problem: 19 Isolated Zones! 🚨

**19 out of 48 major zones have NO connections** to other zones. This indicates:
- Data extraction issues (missing exits)
- Negative room IDs in exits (we filtered those out)
- Separate "instances" or phased content
- Incomplete world data

The largest isolated zone is the 734-room "Dungeon - UNKNOWN" zone!

### Zone Hierarchy

```
Hub Zones (1):
  └─ Forest - Main Area (75 rooms) - 8 connections

Major Connectors (6):
  ├─ Fire Realm - Main Area (164 rooms) - 6 connections
  ├─ Desert - Main Area (100 rooms) - 6 connections
  ├─ Dungeon - DESERT (97 rooms) - 6 connections
  ├─ Dungeon Level 2 (56 rooms) - 6 connections
  ├─ Town Area (51 rooms, Mountains) - 6 connections
  └─ Dungeon - FOREST (41 rooms) - 6 connections

Connectors (11 zones):
  - Moderate traffic zones linking 2-4 other zones

Pathways (11 zones):
  - Linear progression zones (entrance -> exit)

Isolated (19 zones):
  - No connections found (DATA ISSUE)
```

## Connected Zone Networks

### Network 1: Dungeon Levels (Classic Progression)

```
Dungeon Level 1 (52 rooms)
      ↕ (stairwell)
Dungeon Level 2 (56 rooms)
      ↕ (stairwell)
Dungeon Level 3 (73 rooms)
```

**Notes**:
- Classic vertical dungeon progression
- Rooms 1-182
- Terrain: DUNGEON1 → DUNGEON2 → DUNGEON3

### Network 2: Forest Hub

```
                    Forest - Main Area (75 rooms)
                    /     |      |      \
                   /      |      |       \
                  /       |      |        \
           Desert(100) Unknown Forest(5) Forest(5)
               |
               |
          Jungle(313) ← Desert
               |
          Dungeon3(127) → Fire1(143)
```

**Notes**:
- Forest is the main hub
- Desert connects to Jungle
- Multiple small forest zones branch off

### Network 3: Fire Realms

```
Fire1 (143 rooms) ←→ Dungeon3(127) ←→ Desert(100)
   ↓
Fire2 (95 rooms) ←→ Dungeon3(533)
   ↓
Fire2 (another instance, 28 rooms)
```

### Network 4: Town Networks

```
Town - Market District (119 rooms, SWAMP)
       ↕
Fire Realm - Main Area (164 rooms, FOREST)
       ↕
Town Area (51 rooms, MOUNTAINS)
       ↕
Dungeon - UNKNOWN
```

**Notes**:
- Towns connected by Fire Realm
- Mixed terrains (SWAMP, FOREST, MOUNTAINS)

```
Town Area (178 rooms, SWAMP - Sewers)
       ↕
Dungeon - DESERT (97 rooms)
       ↕
Temple
```

### Network 5: Temple System

```
Temple (114 rooms, DUNGEON3)
Temple (98 rooms, DUNGEON2)
   Both connected to Dungeon - DESERT
```

## Isolated Major Zones (Need Investigation)

These zones have NO connections detected:

| Zone | Size | Room Range | Terrain | Likely Issue |
|------|------|------------|---------|--------------|
| Dungeon - UNKNOWN | 734 | 3195-3928 | UNKNOWN | Missing exits or instance |
| Dungeon3 | 89 | 754-843 | DUNGEON3 | Separate instance? |
| Dungeon3 | 533 | 1464-2132 | DUNGEON3 | Actually has connections! |
| Dungeon3 | 46 | 1190-1237 | DUNGEON3 | Instance |
| Dungeon3 | 46 | 1238-1283 | DUNGEON3 | Instance |
| Dungeon3 | 31 | 3092-3122 | DUNGEON3 | Instance |
| Dungeon3 | 30 | 3123-3152 | DUNGEON3 | Instance |
| Town - Market District | 119 | 324-442 | SWAMP | Actually connected! |
| Multiple small zones | 8-19 rooms | Various | UNKNOWN | Likely instances |

**Note**: The analysis shows Zone 2 (533-room Dungeon3) and Zone 9 (Market District) DO have connections, so there may be a bug in the "isolated" detection.

## Room ID Patterns

Looking at room ranges reveals interesting patterns:

- **Rooms 1-233**: Early game (Dungeons 1-3, Town entrance)
- **Rooms 234-1463**: Fire Realm complex
- **Rooms 1464-2815**: Dungeon3 + Jungle mega-complex
- **Rooms 2816-3001**: Forest areas
- **Rooms 3002-3194**: Small scattered zones (possibly instances)
- **Rooms 3195-3928**: Huge UNKNOWN dungeon (isolated!)
- **Rooms 3930-4064**: Late-game town area (mountains, paths)

## Recommendations

### 1. Fix Data Extraction
- Review exit parsing for negative room IDs
- Check if exits reference rooms in different area files
- Investigate the 734-room UNKNOWN zone manually

### 2. Zone Renaming Based on Connections

| Current Name | Better Name (based on connections) |
|--------------|-----------------------------------|
| Fire Realm - Main Area | Town Connector (links 2 towns) |
| Forest - Main Area | Forest Hub (central hub) |
| Desert - Main Area | Wilderness Connector |
| Dungeon - DESERT | Desert Temple Approach |

### 3. Instance Detection
The isolated DUNGEON3 zones (30-89 rooms each) are likely:
- Separate dungeon instances
- Private raid zones
- Quest-specific areas
- Need metadata to identify their purpose

### 4. Next Steps
- Manual review of isolated zones
- Fix exit parsing to include negative/external room refs
- Map quest data to understand instance purposes
- Create world map visualization

## Data Files

- **Connection Data**: `config/temp/zone_connections.json`
- **Zone Analysis**: `config/temp/zone_analysis_v2.json`
