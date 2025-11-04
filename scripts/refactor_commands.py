"""Script to refactor command_handler.py into smaller modules."""

import re
import os


def extract_method(lines, start_line, method_name):
    """Extract a method and its complete body."""
    # Find the method indentation
    method_line = lines[start_line - 1]
    method_indent = len(method_line) - len(method_line.lstrip())

    # Extract all lines belonging to this method
    method_lines = [method_line]
    i = start_line

    while i < len(lines):
        line = lines[i]
        # Empty lines or docstrings continue the method
        if not line.strip():
            method_lines.append(line)
            i += 1
            continue

        # Check if still part of method (indented more than method def)
        line_indent = len(line) - len(line.lstrip())
        if line_indent > method_indent or (line.strip() and line.strip()[0] in ['"', "'"]):
            method_lines.append(line)
            i += 1
        else:
            break

    return method_lines, i


def find_imports(lines):
    """Extract import statements from the file."""
    imports = []
    in_imports = True

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            if in_imports:
                imports.append(line)
            continue

        if stripped.startswith('import ') or stripped.startswith('from '):
            imports.append(line)
        elif stripped.startswith('class '):
            in_imports = False
            break
        elif in_imports and not stripped:
            imports.append(line)

    return imports


def create_handler_module(module_name, methods_info, source_lines, imports):
    """Create a handler module file."""
    class_name = ''.join(word.capitalize() for word in module_name.split('_')) + 'CommandHandler'

    output = []
    output.append(f'"""Command handlers for {module_name.replace("_", " ")} operations."""')
    output.append('')

    # Add necessary imports
    output.append('import asyncio')
    output.append('import random')
    output.append('import json')
    output.append('import time')
    output.append('from typing import Optional, Dict, Any, Tuple')
    output.append('from ..base_handler import BaseCommandHandler')
    output.append('from ...utils.colors import (')
    output.append('    service_message, item_found, error_message,')
    output.append('    info_message, success_message, announcement,')
    output.append('    Colors, wrap_color')
    output.append(')')
    output.append('')
    output.append('')
    output.append(f'class {class_name}(BaseCommandHandler):')
    output.append(f'    """Handles {module_name.replace("_", " ")} related commands."""')
    output.append('')

    # Add each method
    for method_info in methods_info:
        method_lines, _ = extract_method(source_lines, method_info['line'], method_info['name'])
        output.extend(method_lines)
        output.append('')

    return '\n'.join(output)


# Define method categorization
CATEGORIES = {
    'auth': {
        'methods': ['login_process', 'character_selection', 'character_creation_input'],
        'filename': 'auth_handler.py'
    },
    'character': {
        'methods': ['health_command', 'experience_command', 'stats_command', 'reroll_command', 'train_command', 'ability_command'],
        'filename': 'character_handler.py'
    },
    'inventory': {
        'methods': ['inventory_command', 'get_item', 'drop_item', 'equip_item', 'unequip_item', 'put_command'],
        'filename': 'inventory_handler.py'
    },
    'item_usage': {
        'methods': ['eat_command', 'drink_command', 'light_command', 'extinguish_command', 'fill_command', 'read_command'],
        'filename': 'item_handler.py'
    },
    'combat': {
        'methods': ['attack_command', 'shoot_command', 'flee_command', 'retrieve_ammo', 'heal_command'],
        'filename': 'combat_handler.py'
    },
    'vendor': {
        'methods': ['trade_command', 'ring_command', 'list_vendor_items', 'buy_item', 'sell_item', 'buy_passage', 'rent_room'],
        'filename': 'vendor_handler.py'
    },
    'world': {
        'methods': ['search_traps_command', 'disarm_trap_command', 'look_command', 'look_at_target', 'special_action'],
        'filename': 'world_handler.py'
    },
    'magic': {
        'methods': ['spellbook_command', 'cast_command'],
        'filename': 'magic_handler.py'
    },
    'quest': {
        'methods': ['quest_log', 'abandon_quest', 'talk_to_npc', 'accept_quest'],
        'filename': 'quest_handler.py'
    },
    'admin': {
        'methods': ['admin_give_gold', 'admin_give_item', 'admin_give_xp', 'admin_mob_status',
                   'admin_teleport', 'admin_respawn_npc', 'admin_complete_quest'],
        'filename': 'admin_handler.py'
    },
    'map': {
        'methods': ['map_command', 'show_all_areas_map', 'show_area_map', 'generate_ascii_map', 'generate_simple_list_map'],
        'filename': 'map_handler.py'
    }
}


if __name__ == '__main__':
    # Read source file
    with open('src/server/commands/command_handler.py', 'r') as f:
        source_content = f.read()
        source_lines = source_content.split('\n')

    # Find all methods
    all_methods = []
    for i, line in enumerate(source_lines, 1):
        match = re.match(r'^(\s*)(async )?def (_handle_\w+|_show_\w+|_generate_\w+)', line)
        if match:
            indent = match.group(1)
            is_async = match.group(2) is not None
            method_name = match.group(3)
            all_methods.append({
                'name': method_name,
                'line': i,
                'is_async': is_async,
                'indent': len(indent)
            })

    # Extract imports
    imports = find_imports(source_lines)

    # Create output directory
    os.makedirs('src/server/commands/handlers', exist_ok=True)

    # Process each category
    for category, config in CATEGORIES.items():
        print(f"\nProcessing {category}...")

        # Find methods for this category
        category_methods = []
        for method_info in all_methods:
            method_base = method_info['name'].replace('_handle_', '').replace('_show_', 'show_').replace('_generate_', 'generate_')
            if any(keyword in method_base for keyword in config['methods']):
                category_methods.append(method_info)
                print(f"  - {method_info['name']}")

        if category_methods:
            # Create module
            module_content = create_handler_module(category, category_methods, source_lines, imports)

            # Write to file
            output_path = f"src/server/commands/handlers/{config['filename']}"
            with open(output_path, 'w') as f:
                f.write(module_content)

            print(f"  Created {output_path} with {len(category_methods)} methods")

    print("\nRefactoring complete!")
    print(f"Processed {len(all_methods)} total methods")
