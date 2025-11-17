# Violet Rune Areas (End-Game)

**Import Order**: 6
**Recommended Level Range**: 35-50+
**Total Areas**: 3
**Total Rooms**: 1167

## Description

Final progression tier. Includes Stone Passages mega-dungeon (832 rooms, 20% of world!), Deep Forest, and Elven settlement.

## Areas in This Tier

- **Stone Passages Areas** (832 rooms) - `01_stone_passages_areas.json`
- **Deep Forest Area** (199 rooms) - `06_deep_forest_area.json`
- **Elven Area** (136 rooms) - `10_elven_area.json`


## Migration Notes

### Import Order
Import this tier after blue rune areas

### Access Control
Players must have the **Violet Rune** in their inventory to access these areas.

Exit blocking should show:
```
> north
A shimmering barrier blocks your path. You sense it requires a Violet Rune to pass.
```


### Testing Checklist
- [ ] All rooms load correctly
- [ ] Exits connect properly within tier
- [ ] Exits to other tiers show correct rune requirements
- [ ] NPCs spawn correctly in lairs
- [ ] Triggers function (teleporters, traps, etc.)
- [ ] Stone Passages teleporter network functioning (173 triggers)
- [ ] Elven Area services accessible (shops, trainers, etc.)

---

*Generated from World1 export data*
