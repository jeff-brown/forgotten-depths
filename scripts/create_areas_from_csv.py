#!/usr/bin/env python3
"""
Create area files from manually enriched CSV zone assignments.

Reads the updated rooms_summary.csv and reorganizes rooms into
proper area/zone files based on manual zone name and terrain assignments.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path


def load_updated_zone_assignments():
    """Load zone assignments from the manually updated CSV."""
    zones = {}  # zone_name -> {terrain, room_ids}

    with open('config/temp/rooms_summary.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            zone_name = row['zone_name']
            terrain = row['terrain']
            room_id = int(row['room_id'])

            if zone_name not in zones:
                zones[zone_name] = {
                    'name': zone_name,
                    'terrain': terrain,
                    'room_ids': []
                }

            zones[zone_name]['room_ids'].append(room_id)

    # Sort room IDs for each zone
    for zone in zones.values():
        zone['room_ids'].sort()

    return zones


def load_consolidated_rooms():
    """Load the consolidated room data."""
    with open('config/temp/all_rooms_consolidated.json', 'r') as f:
        data = json.load(f)
        return {room['room_id']: room for room in data['rooms']}


def create_area_files(zones, all_rooms, output_dir):
    """Create area JSON files for each zone."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Filter out transition zones (too small/scattered)
    main_zones = {
        name: zone for name, zone in zones.items()
        if not name.startswith('Transition') and len(zone['room_ids']) >= 5
    }

    print(f"Creating {len(main_zones)} area files...")
    print()

    # Sort zones by size (largest first)
    sorted_zones = sorted(main_zones.items(), key=lambda x: len(x[1]['room_ids']), reverse=True)

    for i, (zone_name, zone_data) in enumerate(sorted_zones, 1):
        # Create safe filename
        safe_name = zone_name.lower()
        safe_name = safe_name.replace(' ', '_')
        safe_name = safe_name.replace('(', '').replace(')', '')
        safe_name = safe_name.replace('-', '_')

        filename = f"{i:02d}_{safe_name}.json"
        filepath = output_path / filename

        # Get all rooms for this zone
        zone_rooms = []
        for room_id in zone_data['room_ids']:
            if room_id in all_rooms:
                room = all_rooms[room_id].copy()
                # Remove internal metadata fields
                for key in list(room.keys()):
                    if key.startswith('_'):
                        del room[key]
                zone_rooms.append(room)

        # Calculate statistics
        room_ids = zone_data['room_ids']
        exits_count = sum(len(r.get('exits', [])) for r in zone_rooms)
        npcs_count = sum(r.get('npcs', {}).get('count', 0) for r in zone_rooms)
        lairs_count = sum(len(r.get('lairs', [])) for r in zone_rooms)
        triggers_count = sum(len(r.get('triggers', [])) for r in zone_rooms)

        # Count rooms by terrain (should all be same, but check)
        terrain_breakdown = defaultdict(int)
        for room in zone_rooms:
            terrain_breakdown[room['terrain']['name']] += 1

        # Create area file structure
        area_data = {
            'area_id': i,
            'area_name': zone_name,
            'area_type': 'World1Zone',
            'terrain': zone_data['terrain'],
            '_metadata': {
                'version': '2.0',
                'source': 'Manual zone assignment from rooms_summary.csv',
                'description': f'{zone_name} - reorganized from World1 export',
                'total_rooms': len(zone_rooms),
                'room_id_range': {
                    'min': min(room_ids),
                    'max': max(room_ids)
                }
            },
            '_statistics': {
                'total_rooms': len(zone_rooms),
                'room_id_range': {
                    'min': min(room_ids),
                    'max': max(room_ids)
                },
                'total_exits': exits_count,
                'total_npcs': npcs_count,
                'total_lairs': lairs_count,
                'total_triggers': triggers_count,
                'terrain_breakdown': dict(terrain_breakdown)
            },
            'rooms': zone_rooms
        }

        # Write to file
        with open(filepath, 'w') as f:
            json.dump(area_data, f, indent=2)

        print(f"Created: {filename}")
        print(f"  Zone: {zone_name}")
        print(f"  Rooms: {len(zone_rooms)} (IDs {min(room_ids)}-{max(room_ids)})")
        print(f"  Terrain: {zone_data['terrain']}")
        print(f"  Stats: {exits_count} exits, {lairs_count} lairs, {triggers_count} triggers")
        print()

    return len(main_zones)


def create_area_index(zones, output_dir):
    """Create an index file listing all areas."""
    output_path = Path(output_dir)

    main_zones = {
        name: zone for name, zone in zones.items()
        if not name.startswith('Transition') and len(zone['room_ids']) >= 5
    }

    sorted_zones = sorted(main_zones.items(), key=lambda x: len(x[1]['room_ids']), reverse=True)

    areas = []
    for i, (zone_name, zone_data) in enumerate(sorted_zones, 1):
        safe_name = zone_name.lower()
        safe_name = safe_name.replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
        filename = f"{i:02d}_{safe_name}.json"

        areas.append({
            'area_id': i,
            'area_name': zone_name,
            'filename': filename,
            'terrain': zone_data['terrain'],
            'room_count': len(zone_data['room_ids']),
            'room_id_range': {
                'min': min(zone_data['room_ids']),
                'max': max(zone_data['room_ids'])
            }
        })

    index_data = {
        '_metadata': {
            'version': '2.0',
            'description': 'World1 areas reorganized by manual zone assignments',
            'total_areas': len(areas),
            'total_rooms': sum(a['room_count'] for a in areas)
        },
        'areas': areas
    }

    index_file = output_path / 'areas_index.json'
    with open(index_file, 'w') as f:
        json.dump(index_data, f, indent=2)

    print(f"Created area index: {index_file}")
    print(f"  Total areas: {len(areas)}")
    print(f"  Total rooms: {sum(a['room_count'] for a in areas)}")

    return index_file


def main():
    print("="*70)
    print("Create Area Files from Manual Zone Assignments")
    print("="*70)
    print()

    # Load data
    print("Loading manually updated zone assignments from CSV...")
    zones = load_updated_zone_assignments()
    print(f"Found {len(zones)} zones")

    print("\nLoading consolidated room data...")
    all_rooms = load_consolidated_rooms()
    print(f"Loaded {len(all_rooms)} rooms")

    print()
    print("="*70)
    print("Zone Summary")
    print("="*70)
    print()

    # Show zone summary
    sorted_zones = sorted(zones.items(), key=lambda x: len(x[1]['room_ids']), reverse=True)
    for zone_name, zone_data in sorted_zones[:15]:
        room_ids = zone_data['room_ids']
        count = len(room_ids)
        terrain = zone_data['terrain']
        room_range = f"{min(room_ids)}-{max(room_ids)}"
        print(f"  {zone_name:40} {count:4} rooms  ({room_range:12})  {terrain}")

    if len(sorted_zones) > 15:
        print(f"  ... and {len(sorted_zones) - 15} more zones")

    print()
    print("="*70)

    # Create output directory
    output_dir = 'config/temp/world1_areas'

    print(f"\nCreating area files in: {output_dir}/")
    print()

    # Create area files
    num_areas = create_area_files(zones, all_rooms, output_dir)

    print("="*70)

    # Create index
    print()
    create_area_index(zones, output_dir)

    print()
    print("="*70)
    print("COMPLETE")
    print("="*70)
    print()
    print(f"Created {num_areas} area files")
    print(f"Output directory: {output_dir}/")
    print()
    print("Next steps:")
    print("  1. Review area files in config/temp/world1_areas/")
    print("  2. Adjust zone assignments if needed")
    print("  3. Plan migration to game's data/world/ structure")


if __name__ == "__main__":
    main()
