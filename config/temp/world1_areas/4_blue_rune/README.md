# Blue Rune Areas

**Import Order**: 5
**Recommended Level Range**: 30-40
**Total Areas**: 6
**Total Rooms**: 852

## Description

Fourth progression tier. Volcanic and underground network including caverns, valley, and sweltering passages.

## Areas in This Tier

- **Natural Caverns Area** (313 rooms) - `03_natural_caverns_area.json`
- **Sweltering Passages Area** (143 rooms) - `08_sweltering_passages_area.json`
- **Ledge Area** (136 rooms) - `09_ledge_area.json`
- **Granite Corridor Area** (127 rooms) - `11_granite_corridor_area.json`
- **Valley Area** (100 rooms) - `13_valley_area.json`
- **Tunnel Area** (33 rooms) - `24_tunnel_area.json`


## Migration Notes

### Import Order
Import this tier after green rune areas

### Access Control
Players must have the **Blue Rune** in their inventory to access these areas.

Exit blocking should show:
```
> north
A shimmering barrier blocks your path. You sense it requires a Blue Rune to pass.
```


### Testing Checklist
- [ ] All rooms load correctly
- [ ] Exits connect properly within tier
- [ ] Exits to other tiers show correct rune requirements
- [ ] NPCs spawn correctly in lairs
- [ ] Triggers function (teleporters, traps, etc.)

---

*Generated from World1 export data*
