# Command Handler Refactoring Plan

## Current State
The `command_handler.py` file has grown to **5,447 lines** with 53+ handler methods. This makes it difficult to maintain and navigate.

## Refactoring Strategy

### Phase 1: Infrastructure (COMPLETED)
- ✅ Created `base_handler.py` - Base class for all command handlers
- ✅ Created `handlers/` directory for modular command handlers
- ✅ Analyzed command categorization (11 main categories)

### Phase 2: Gradual Migration (IN PROGRESS)
Instead of a big-bang refactoring, we'll migrate categories incrementally:

1. **Start with self-contained modules** (easiest to extract):
   - Map handler (~340 lines) - No dependencies on other handlers
   - Admin commands (~200 lines) - Mostly independent
   - Quest handlers (~180 lines) - Well-defined scope

2. **Then move larger interconnected systems**:
   - Combat system
   - Inventory system
   - Magic/spellcasting

3. **Finally refactor core systems**:
   - Authentication
   - Character management
   - World interaction

### Phase 3: Command Router Simplification
Once handlers are extracted, simplify the main `_handle_game_command()` method to:
- Route commands to appropriate handler modules
- Handle only cross-cutting concerns (logging, permissions)
- Keep the massive if/elif chain but delegate implementation

## Target Architecture

```
src/server/commands/
├── __init__.py
├── command_handler.py          # Main router (target: <1000 lines)
├── base_handler.py              # Shared base class
└── handlers/
    ├── __init__.py
    ├── map_handler.py           # Map display and navigation
    ├── admin_handler.py         # Admin/debug commands
    ├── quest_handler.py         # Quest system
    ├── combat_handler.py        # Combat commands
    ├── inventory_handler.py     # Inventory management
    ├── magic_handler.py         # Spellcasting
    ├── character_handler.py     # Character info & development
    ├── vendor_handler.py        # Trading & services
    ├── world_handler.py         # World interaction
    ├── item_handler.py          # Item usage (eat, drink, etc.)
    └── auth_handler.py          # Authentication & character creation
```

## Benefits
- **Maintainability**: Easier to find and modify specific command logic
- **Testability**: Can test individual handler modules in isolation
- **Collaboration**: Multiple developers can work on different handlers
- **Performance**: Smaller files load faster in IDEs
- **Documentation**: Each handler can have focused documentation

## Migration Checklist
- [ ] Extract MapCommandHandler
- [ ] Extract AdminCommandHandler
- [ ] Extract QuestCommandHandler
- [ ] Extract CombatCommandHandler
- [ ] Extract InventoryCommandHandler
- [ ] Extract MagicCommandHandler
- [ ] Extract CharacterCommandHandler
- [ ] Extract VendorCommandHandler
- [ ] Extract WorldCommandHandler
- [ ] Extract ItemCommandHandler
- [ ] Extract AuthCommandHandler
- [ ] Update command_handler.py to use extracted handlers
- [ ] Add unit tests for each handler module
- [ ] Update documentation

## Notes
- Keep backward compatibility - no changes to external APIs
- Ensure all imports are properly handled
- Test thoroughly after each extraction
- Use composition pattern (handlers as attributes of CommandHandler)
