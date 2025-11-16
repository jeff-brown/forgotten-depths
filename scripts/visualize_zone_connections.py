#!/usr/bin/env python3
"""
Visualize how World1 zones connect to each other.

This helps understand the world structure and identify:
- Hub zones (many connections)
- Linear progressions (zone A -> zone B -> zone C)
- Isolated zones
- Proper zone names based on their role in the world
"""

import json
from collections import defaultdict


def load_zone_analysis():
    """Load the zone analysis data."""
    with open('config/temp/zone_analysis_v2.json', 'r') as f:
        return json.load(f)


def load_all_rooms():
    """Load all rooms from area files."""
    from pathlib import Path

    all_rooms = {}
    area_files = sorted(Path('config/temp/world1_export').glob('area_*.json'))

    for area_file in area_files:
        with open(area_file, 'r') as f:
            data = json.load(f)
            for room in data['rooms']:
                all_rooms[room['room_id']] = room

    return all_rooms


def build_zone_map(zones):
    """Build mapping of room_id -> zone_id."""
    room_to_zone = {}

    for zone in zones:
        zone_id = zone['zone_id']
        for room_id in zone['room_ids']:
            room_to_zone[room_id] = zone_id

    return room_to_zone


def find_zone_connections(zones, all_rooms, room_to_zone):
    """Find which zones connect to which other zones."""
    zone_connections = defaultdict(lambda: defaultdict(int))  # zone_id -> {neighbor_zone_id: count}

    for zone in zones:
        zone_id = zone['zone_id']

        # Check all rooms in this zone
        for room_id in zone['room_ids']:
            room = all_rooms.get(room_id)
            if not room:
                continue

            # Check all exits
            for exit_info in room.get('exits', []):
                target_room = exit_info.get('to_room')

                # Valid positive room ID?
                if target_room and target_room > 0 and target_room in room_to_zone:
                    target_zone = room_to_zone[target_room]

                    # Connection to a different zone?
                    if target_zone != zone_id:
                        zone_connections[zone_id][target_zone] += 1

    return zone_connections


def analyze_zone_role(zone, connections_from, connections_to):
    """Determine the role of a zone in the world."""
    num_from = len(connections_from)
    num_to = len(connections_to)
    total = num_from + num_to

    if total == 0:
        return "Isolated"
    elif total >= 8:
        return "Hub"
    elif total >= 5:
        return "Major Connector"
    elif total >= 3:
        return "Connector"
    elif num_from == 1 and num_to == 1:
        return "Pathway"
    elif num_from == 1 or num_to == 1:
        return "Branch"
    else:
        return "Minor Area"


def main():
    print("="*70)
    print("World1 Zone Connection Analysis")
    print("="*70)
    print()

    # Load data
    print("Loading zone analysis...")
    analysis = load_zone_analysis()
    zones = analysis['zones']

    print("Loading room data...")
    all_rooms = load_all_rooms()

    # Build mappings
    print("Building zone mappings...")
    room_to_zone = build_zone_map(zones)

    # Find connections
    print("Analyzing zone connections...")
    zone_connections = find_zone_connections(zones, all_rooms, room_to_zone)

    # Build reverse connections (who connects TO this zone)
    reverse_connections = defaultdict(lambda: defaultdict(int))
    for from_zone, targets in zone_connections.items():
        for to_zone, count in targets.items():
            reverse_connections[to_zone][from_zone] += count

    print()
    print("="*70)
    print("ZONE CONNECTION MAP")
    print("="*70)
    print()

    # Focus on major zones (5+ rooms)
    major_zones = [z for z in zones if z['size'] >= 5]

    # Analyze each zone
    zone_info = []
    for zone in major_zones:
        zone_id = zone['zone_id']
        connections_from = zone_connections[zone_id]
        connections_to = reverse_connections[zone_id]

        role = analyze_zone_role(zone, connections_from, connections_to)

        zone_info.append({
            'zone': zone,
            'role': role,
            'connections_from': connections_from,
            'connections_to': connections_to,
            'total_connections': len(connections_from) + len(connections_to)
        })

    # Sort by total connections (hubs first)
    zone_info.sort(key=lambda x: x['total_connections'], reverse=True)

    # Print each zone with its connections
    for info in zone_info:
        zone = info['zone']
        print(f"Zone {zone['zone_id']}: {zone['zone_name']} ({zone['size']} rooms)")
        print(f"  Role: {info['role']}")
        print(f"  Room Range: {zone['room_id_range'][0]}-{zone['room_id_range'][1]}")
        print(f"  Terrain: {zone['terrain']}")

        # Show connections FROM this zone
        if info['connections_from']:
            print(f"  Exits to ({len(info['connections_from'])} zones):")
            for target_zone_id, count in sorted(info['connections_from'].items(), key=lambda x: x[1], reverse=True)[:5]:
                target_zone = next(z for z in zones if z['zone_id'] == target_zone_id)
                print(f"    -> Zone {target_zone_id}: {target_zone['zone_name']} ({count} exits)")

        # Show connections TO this zone
        if info['connections_to']:
            print(f"  Entrances from ({len(info['connections_to'])} zones):")
            for from_zone_id, count in sorted(info['connections_to'].items(), key=lambda x: x[1], reverse=True)[:5]:
                from_zone = next(z for z in zones if z['zone_id'] == from_zone_id)
                print(f"    <- Zone {from_zone_id}: {from_zone['zone_name']} ({count} entrances)")

        print()

    # Summary statistics
    print("="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    print()

    roles = defaultdict(int)
    for info in zone_info:
        roles[info['role']] += 1

    print("Zone Roles:")
    for role, count in sorted(roles.items(), key=lambda x: x[1], reverse=True):
        print(f"  {role}: {count} zones")

    print()
    print("Top 5 Hub Zones (most connected):")
    for i, info in enumerate(zone_info[:5], 1):
        zone = info['zone']
        total = info['total_connections']
        print(f"  {i}. Zone {zone['zone_id']}: {zone['zone_name']} ({total} connections)")

    print()
    print("Isolated Zones (no connections):")
    isolated = [info for info in zone_info if info['total_connections'] == 0]
    if isolated:
        for info in isolated[:10]:
            zone = info['zone']
            print(f"  - Zone {zone['zone_id']}: {zone['zone_name']} ({zone['size']} rooms)")
    else:
        print("  None!")

    # Export detailed connection data
    output_file = "config/temp/zone_connections.json"
    connection_data = {
        'zones': [],
        'summary': {
            'total_zones': len(major_zones),
            'hub_zones': len([i for i in zone_info if i['role'] == 'Hub']),
            'isolated_zones': len(isolated)
        }
    }

    for info in zone_info:
        zone = info['zone']
        connection_data['zones'].append({
            'zone_id': zone['zone_id'],
            'zone_name': zone['zone_name'],
            'size': zone['size'],
            'role': info['role'],
            'room_range': zone['room_id_range'],
            'terrain': zone['terrain'],
            'connections_from': {str(k): v for k, v in info['connections_from'].items()},
            'connections_to': {str(k): v for k, v in info['connections_to'].items()},
            'total_connections': info['total_connections']
        })

    with open(output_file, 'w') as f:
        json.dump(connection_data, f, indent=2)

    print()
    print(f"Detailed connection data saved to: {output_file}")


if __name__ == "__main__":
    main()
