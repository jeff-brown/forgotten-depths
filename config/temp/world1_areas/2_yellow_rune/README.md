# Yellow Rune Areas

**Import Order**: 3
**Recommended Level Range**: 15-25
**Total Areas**: 2
**Total Rooms**: 342

## Description

Second progression tier. Flagstone dungeon complex.

## Areas in This Tier

- **Flagstone Area** (299 rooms) - `04_flagstone_area.json`
- **Flagworks Area** (43 rooms) - `23_flagworks_area.json`


## Migration Notes

### Import Order
Import this tier after white rune areas

### Access Control
Players must have the **Yellow Rune** in their inventory to access these areas.

Exit blocking should show:
```
> north
A shimmering barrier blocks your path. You sense it requires a Yellow Rune to pass.
```


### Testing Checklist
- [ ] All rooms load correctly
- [ ] Exits connect properly within tier
- [ ] Exits to other tiers show correct rune requirements
- [ ] NPCs spawn correctly in lairs
- [ ] Triggers function (teleporters, traps, etc.)

---

*Generated from World1 export data*
