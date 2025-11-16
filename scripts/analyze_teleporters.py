#!/usr/bin/env python3
"""
Analyze teleporter network in World1 to understand zone connections
that aren't visible through normal exits.
"""

import json
from pathlib import Path
from collections import defaultdict


def load_zone_analysis():
    """Load the zone analysis data."""
    with open('config/temp/zone_analysis_v2.json', 'r') as f:
        return json.load(f)


def build_room_to_zone_map(zones):
    """Build mapping of room_id -> zone."""
    room_to_zone = {}
    for zone in zones:
        for room_id in zone['room_ids']:
            room_to_zone[room_id] = zone
    return room_to_zone


def find_teleporters():
    """Find all teleporter triggers."""
    teleporters = []
    area_files = sorted(Path('config/temp/world1_export').glob('area_*.json'))

    for area_file in area_files:
        with open(area_file, 'r') as f:
            data = json.load(f)
            for room in data['rooms']:
                for trigger in room.get('triggers', []):
                    trigger_type = trigger.get('trigger_type', {})
                    if trigger_type.get('name') == 'TELEPORT':
                        decoded = trigger.get('decoded_values', {})
                        teleporters.append({
                            'from_room': room['room_id'],
                            'to_room': decoded.get('target_room'),
                            'from_desc': room['short_description'],
                            'is_enabled': decoded.get('is_enabled', True)
                        })

    return teleporters


def main():
    print("="*70)
    print("World1 Teleporter Network Analysis")
    print("="*70)
    print()

    # Load data
    print("Loading zone analysis...")
    analysis = load_zone_analysis()
    zones = analysis['zones']

    print("Building room-to-zone mapping...")
    room_to_zone = build_room_to_zone_map(zones)

    print("Finding teleporters...")
    teleporters = find_teleporters()

    print(f"Found {len(teleporters)} teleporters")
    print()

    # Analyze teleporter network
    print("="*70)
    print("TELEPORTER NETWORK")
    print("="*70)
    print()

    # Group by destination
    by_destination = defaultdict(list)
    for tp in teleporters:
        if tp['is_enabled']:
            by_destination[tp['to_room']].append(tp)

    print(f"Unique teleporter destinations: {len(by_destination)}")
    print()

    # Analyze zone-to-zone teleports
    zone_teleports = defaultdict(lambda: defaultdict(list))  # from_zone -> to_zone -> [teleporters]

    for tp in teleporters:
        if not tp['is_enabled']:
            continue

        from_room = tp['from_room']
        to_room = tp['to_room']

        from_zone = room_to_zone.get(from_room)
        to_zone = room_to_zone.get(to_room)

        if from_zone and to_zone:
            from_id = from_zone['zone_id']
            to_id = to_zone['zone_id']

            # Only track inter-zone teleports
            if from_id != to_id:
                zone_teleports[from_id][to_id].append(tp)

    print("INTER-ZONE TELEPORTER CONNECTIONS")
    print("-" * 70)
    print()

    # Sort zones by number of teleporter connections
    zones_with_teleports = []
    for from_zone_id, destinations in zone_teleports.items():
        from_zone = next(z for z in zones if z['zone_id'] == from_zone_id)
        total_teleports = sum(len(tps) for tps in destinations.values())

        zones_with_teleports.append({
            'zone': from_zone,
            'destinations': destinations,
            'total_teleports': total_teleports
        })

    zones_with_teleports.sort(key=lambda x: x['total_teleports'], reverse=True)

    for info in zones_with_teleports:
        zone = info['zone']
        print(f"Zone {zone['zone_id']}: {zone['zone_name']} ({zone['size']} rooms)")
        print(f"  {info['total_teleports']} teleporter(s) to {len(info['destinations'])} zone(s):")

        for to_zone_id, tps in sorted(info['destinations'].items(), key=lambda x: len(x[1]), reverse=True):
            to_zone = next(z for z in zones if z['zone_id'] == to_zone_id)
            print(f"    -> Zone {to_zone_id}: {to_zone['zone_name']} ({len(tps)} teleporter(s))")

            # Show sample teleporter
            if len(tps) <= 3:
                for tp in tps:
                    print(f"       Room {tp['from_room']} -> {tp['to_room']}")

        print()

    # Find zones that can ONLY be reached by teleporter
    print("="*70)
    print("TELEPORTER-ONLY ZONES")
    print("="*70)
    print()

    # Load connection data
    with open('config/temp/zone_connections.json', 'r') as f:
        connection_data = json.load(f)

    # Find zones with no normal connections but teleporter access
    teleporter_only = []
    zones_with_teleport_access = set()

    # Find which zones are teleport destinations
    for from_zone_id, destinations in zone_teleports.items():
        for to_zone_id in destinations.keys():
            zones_with_teleport_access.add(to_zone_id)

    for zone_data in connection_data['zones']:
        zone_id = zone_data['zone_id']
        total_connections = zone_data['total_connections']

        # If no normal connections but has teleporter access
        if total_connections == 0 and zone_id in zones_with_teleport_access:
            zone = next(z for z in zones if z['zone_id'] == zone_id)
            teleporter_only.append(zone)

    if teleporter_only:
        print(f"Found {len(teleporter_only)} zones accessible ONLY by teleporter:")
        print()
        for zone in teleporter_only:
            print(f"  Zone {zone['zone_id']}: {zone['zone_name']} ({zone['size']} rooms)")
            print(f"    Room range: {zone['room_id_range'][0]}-{zone['room_id_range'][1]}")

            # Show which zones teleport here
            sources = []
            for from_zone_id, destinations in zone_teleports.items():
                if zone['zone_id'] in destinations:
                    from_zone = next(z for z in zones if z['zone_id'] == from_zone_id)
                    sources.append(from_zone['zone_name'])

            print(f"    Accessible from: {', '.join(sources[:3])}")
            print()
    else:
        print("No teleporter-only zones found (all have normal exits too)")

    # Summary stats
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print()
    print(f"Total teleporters: {len([tp for tp in teleporters if tp['is_enabled']])}")
    print(f"Zones with outgoing teleporters: {len(zone_teleports)}")
    print(f"Zones with incoming teleporters: {len(zones_with_teleport_access)}")
    print(f"Teleporter-only zones: {len(teleporter_only)}")

    # Export data
    output = {
        'total_teleporters': len(teleporters),
        'enabled_teleporters': len([tp for tp in teleporters if tp['is_enabled']]),
        'zone_teleports': {},
        'teleporter_only_zones': [z['zone_id'] for z in teleporter_only]
    }

    for from_zone_id, destinations in zone_teleports.items():
        output['zone_teleports'][str(from_zone_id)] = {
            str(k): len(v) for k, v in destinations.items()
        }

    with open('config/temp/teleporter_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)

    print()
    print("Detailed analysis saved to: config/temp/teleporter_analysis.json")


if __name__ == "__main__":
    main()
