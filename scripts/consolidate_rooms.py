#!/usr/bin/env python3
"""
Consolidate all room data from 27 area files into a single JSON file.

This creates a master room list sorted by room_id to facilitate
manual data enrichment and zone assignment.
"""

import json
from pathlib import Path


def load_all_rooms():
    """Load all rooms from area files and consolidate."""
    all_rooms = []
    area_files = sorted(Path('config/temp/world1_export').glob('area_*.json'))

    print(f"Loading {len(area_files)} area files...")

    for area_file in area_files:
        with open(area_file, 'r') as f:
            data = json.load(f)
            area_id = data['_metadata']['area_id']

            for room in data['rooms']:
                # Add source area metadata
                room['_source_area'] = area_id
                room['_source_file'] = area_file.name
                all_rooms.append(room)

    print(f"Loaded {len(all_rooms)} total rooms")
    return all_rooms


def load_zone_assignments():
    """Load zone assignments from analysis."""
    with open('config/temp/zone_analysis_v2.json', 'r') as f:
        analysis = json.load(f)

    # Build room_id -> zone mapping
    room_to_zone = {}
    for zone in analysis['zones']:
        zone_info = {
            'zone_id': zone['zone_id'],
            'zone_name': zone['zone_name'],
            'size': zone['size'],
            'terrain': zone['terrain']
        }
        for room_id in zone['room_ids']:
            room_to_zone[room_id] = zone_info

    return room_to_zone


def analyze_room_accessibility(room_id, teleporter_data, connection_data):
    """Determine how a room can be accessed."""
    access_methods = []

    # Check if room is in a zone with normal connections
    for zone_data in connection_data['zones']:
        zone_id = zone_data['zone_id']
        if zone_data['total_connections'] > 0:
            # This zone has normal connections
            access_methods.append('walk')
            break

    # Check if room is in a teleporter-only zone
    if room_id in teleporter_data.get('teleporter_only_zones', []):
        access_methods.append('teleporter_only')

    # Check if room has teleporters
    # (This would require more detailed analysis, simplified for now)

    return access_methods if access_methods else ['unknown']


def main():
    print("="*70)
    print("World1 Room Consolidation")
    print("="*70)
    print()

    # Load all rooms
    all_rooms = load_all_rooms()

    # Sort by room_id
    print("Sorting rooms by room_id...")
    all_rooms.sort(key=lambda r: r['room_id'])

    # Load zone assignments
    print("Loading zone assignments...")
    room_to_zone = load_zone_assignments()

    # Load connection data
    print("Loading connection analysis...")
    with open('config/temp/zone_connections.json', 'r') as f:
        connection_data = json.load(f)

    # Load teleporter data
    print("Loading teleporter analysis...")
    with open('config/temp/teleporter_analysis.json', 'r') as f:
        teleporter_data = json.load(f)

    # Enrich each room with zone and accessibility info
    print("Enriching room data...")
    for room in all_rooms:
        room_id = room['room_id']

        # Add zone assignment
        zone_info = room_to_zone.get(room_id)
        if zone_info:
            room['_zone'] = zone_info
        else:
            room['_zone'] = {
                'zone_id': None,
                'zone_name': 'Unassigned',
                'size': 0,
                'terrain': 'UNKNOWN'
            }

        # Add exit count
        room['_exit_count'] = len(room.get('exits', []))

        # Add NPC count
        room['_npc_count'] = room.get('npcs', {}).get('count', 0)

        # Add lair count
        room['_lair_count'] = len(room.get('lairs', []))

        # Add trigger count and types
        triggers = room.get('triggers', [])
        room['_trigger_count'] = len(triggers)
        room['_trigger_types'] = [t.get('trigger_type', {}).get('name', 'UNKNOWN') for t in triggers]

    # Create output structure
    output = {
        '_metadata': {
            'version': '1.0',
            'description': 'Consolidated room data from World1 export, sorted by room_id',
            'total_rooms': len(all_rooms),
            'source_files': 27,
            'generated_by': 'scripts/consolidate_rooms.py'
        },
        '_summary': {
            'total_rooms': len(all_rooms),
            'room_id_range': {
                'min': min(r['room_id'] for r in all_rooms),
                'max': max(r['room_id'] for r in all_rooms)
            },
            'zones_assigned': len([r for r in all_rooms if r['_zone']['zone_id'] is not None]),
            'zones_unassigned': len([r for r in all_rooms if r['_zone']['zone_id'] is None]),
            'rooms_with_npcs': len([r for r in all_rooms if r['_npc_count'] > 0]),
            'rooms_with_lairs': len([r for r in all_rooms if r['_lair_count'] > 0]),
            'rooms_with_triggers': len([r for r in all_rooms if r['_trigger_count'] > 0]),
            'total_exits': sum(r['_exit_count'] for r in all_rooms),
            'total_npcs': sum(r['_npc_count'] for r in all_rooms),
            'total_lairs': sum(r['_lair_count'] for r in all_rooms),
            'total_triggers': sum(r['_trigger_count'] for r in all_rooms)
        },
        'rooms': all_rooms
    }

    # Write to file
    output_file = 'config/temp/all_rooms_consolidated.json'
    print(f"\nWriting consolidated data to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    # Print summary
    print()
    print("="*70)
    print("CONSOLIDATION COMPLETE")
    print("="*70)
    print()
    print(f"Total rooms: {output['_summary']['total_rooms']}")
    print(f"Room ID range: {output['_summary']['room_id_range']['min']} - {output['_summary']['room_id_range']['max']}")
    print()
    print("Zone Assignment:")
    print(f"  Assigned to zones: {output['_summary']['zones_assigned']}")
    print(f"  Unassigned: {output['_summary']['zones_unassigned']}")
    print()
    print("Content Statistics:")
    print(f"  Rooms with NPCs: {output['_summary']['rooms_with_npcs']}")
    print(f"  Rooms with lairs: {output['_summary']['rooms_with_lairs']}")
    print(f"  Rooms with triggers: {output['_summary']['rooms_with_triggers']}")
    print()
    print(f"  Total exits: {output['_summary']['total_exits']}")
    print(f"  Total NPCs: {output['_summary']['total_npcs']}")
    print(f"  Total lairs: {output['_summary']['total_lairs']}")
    print(f"  Total triggers: {output['_summary']['total_triggers']}")
    print()
    print(f"File size: {len(json.dumps(output)) / (1024*1024):.2f} MB")
    print()
    print("Ready for manual enrichment!")

    # Also create a CSV summary for easier viewing in spreadsheet
    import csv
    csv_file = 'config/temp/rooms_summary.csv'
    print(f"Creating CSV summary: {csv_file}...")

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'room_id', 'short_description', 'zone_id', 'zone_name',
            'terrain', 'exits', 'npcs', 'lairs', 'triggers', 'flags',
            'source_area', 'keywords'
        ])

        for room in all_rooms:
            # Extract keywords from description for quick scan
            desc = room.get('long_description', '').lower()
            keywords = []
            for kw in ['town', 'shop', 'temple', 'forest', 'cave', 'fire', 'ice', 'desert', 'jungle']:
                if kw in desc:
                    keywords.append(kw)

            writer.writerow([
                room['room_id'],
                room.get('short_description', '')[:60],
                room['_zone']['zone_id'] or '',
                room['_zone']['zone_name'],
                room['_zone']['terrain'],
                room['_exit_count'],
                room['_npc_count'],
                room['_lair_count'],
                room['_trigger_count'],
                ','.join(room.get('room_flags', {}).get('decoded_flags', [])),
                room['_source_area'],
                ','.join(keywords)
            ])

    print(f"CSV summary created: {csv_file}")
    print()
    print("Next steps:")
    print("  1. Review all_rooms_consolidated.json for manual enrichment")
    print("  2. Open rooms_summary.csv in spreadsheet for quick overview")
    print("  3. Identify rooms that need zone reassignment")
    print("  4. Add custom metadata (quest flags, level requirements, etc.)")


if __name__ == "__main__":
    main()
