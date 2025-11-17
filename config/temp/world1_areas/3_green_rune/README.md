# Green Rune Areas

**Import Order**: 4
**Recommended Level Range**: 25-35
**Total Areas**: 1
**Total Rooms**: 500

## Description

Third progression tier. Labyrinth mega-dungeon (500 rooms). Note: Exit mechanism unclear - may require teleporter or quest completion.

## Areas in This Tier

- **Labyrinth Area** (500 rooms) - `02_labyrinth_area.json`


## Migration Notes

### Import Order
Import this tier after yellow rune areas

### Access Control
Players must have the **Green Rune** in their inventory to access these areas.

Exit blocking should show:
```
> north
A shimmering barrier blocks your path. You sense it requires a Green Rune to pass.
```


### Testing Checklist
- [ ] All rooms load correctly
- [ ] Exits connect properly within tier
- [ ] Exits to other tiers show correct rune requirements
- [ ] NPCs spawn correctly in lairs
- [ ] Triggers function (teleporters, traps, etc.)
- [ ] Labyrinth exit mechanism implemented (teleporter or quest)

---

*Generated from World1 export data*
