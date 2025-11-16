#!/usr/bin/env python3
"""
Analyze World1 export files and cluster rooms into thematic zones.

This script:
1. Reads all 27 area JSON files from config/temp/world1_export/
2. Analyzes room descriptions, terrain types, and connections
3. Clusters rooms into logical thematic zones
4. Outputs zone definitions for migration into the game
"""

import json
import os
from collections import defaultdict
from pathlib import Path
import re


def load_all_areas(export_dir):
    """Load all area JSON files."""
    areas = []
    area_files = sorted(Path(export_dir).glob("area_*.json"))

    print(f"Found {len(area_files)} area files")

    for area_file in area_files:
        with open(area_file, 'r') as f:
            data = json.load(f)
            areas.append({
                'file': area_file.name,
                'area_id': data['_metadata']['area_id'],
                'rooms': data['rooms'],
                'stats': data['_statistics']
            })

    return areas


def extract_all_rooms(areas):
    """Extract all rooms from all areas into a single dictionary."""
    all_rooms = {}

    for area in areas:
        for room in area['rooms']:
            room_id = room['room_id']
            all_rooms[room_id] = {
                **room,
                'source_area': area['area_id'],
                'source_file': area['file']
            }

    print(f"Total rooms extracted: {len(all_rooms)}")
    return all_rooms


def build_room_graph(all_rooms):
    """Build a graph of room connections."""
    graph = defaultdict(set)

    for room_id, room in all_rooms.items():
        for exit_info in room.get('exits', []):
            target_room = exit_info.get('target_room')
            if target_room is not None and target_room in all_rooms:
                graph[room_id].add(target_room)
                # Bidirectional
                graph[target_room].add(room_id)

    return graph


def analyze_room_keywords(room):
    """Extract keywords from room descriptions to help identify zones."""
    keywords = set()

    desc = room.get('long_description', '').lower()
    short = room.get('short_description', '').lower()

    # Common zone indicators
    patterns = [
        r'\b(town|city|village|settlement)\b',
        r'\b(dungeon|cave|cavern|crypt|tomb)\b',
        r'\b(forest|woods|grove|tree)\b',
        r'\b(mountain|peak|cliff|ridge)\b',
        r'\b(desert|sand|dune)\b',
        r'\b(swamp|marsh|bog|wetland)\b',
        r'\b(ice|snow|frozen|glacier)\b',
        r'\b(fire|lava|volcano|inferno)\b',
        r'\b(temple|shrine|altar|chapel|church)\b',
        r'\b(castle|fort|fortress|keep)\b',
        r'\b(shop|store|market|vendor)\b',
        r'\b(tavern|inn|pub)\b',
        r'\b(arena|coliseum)\b',
        r'\b(garden|park)\b',
        r'\b(jungle|tropical)\b',
        r'\b(water|ocean|sea|lake|river)\b',
        r'\b(ruins|ancient|old)\b',
        r'\b(dark|shadow|gloom)\b',
    ]

    for pattern in patterns:
        if re.search(pattern, desc) or re.search(pattern, short):
            match = re.search(pattern, desc + ' ' + short)
            if match:
                keywords.add(match.group(1))

    return keywords


def cluster_by_terrain_and_connectivity(all_rooms, graph):
    """Cluster rooms by terrain type and spatial connectivity."""
    clusters = []
    visited = set()

    def bfs_cluster(start_room_id, terrain_filter=None):
        """BFS to find connected rooms with same terrain."""
        cluster = set()
        queue = [start_room_id]
        visited.add(start_room_id)
        cluster.add(start_room_id)

        start_terrain = all_rooms[start_room_id]['terrain']['name']

        while queue:
            current = queue.pop(0)

            for neighbor in graph[current]:
                if neighbor not in visited:
                    neighbor_terrain = all_rooms[neighbor]['terrain']['name']

                    # Only cluster if same terrain
                    if neighbor_terrain == start_terrain:
                        visited.add(neighbor)
                        cluster.add(neighbor)
                        queue.append(neighbor)

        return cluster

    # Find all connected components with same terrain
    for room_id in sorted(all_rooms.keys()):
        if room_id not in visited:
            cluster = bfs_cluster(room_id)
            if cluster:
                clusters.append(cluster)

    return clusters


def analyze_cluster(cluster, all_rooms):
    """Analyze a cluster to determine its theme and characteristics."""
    if not cluster:
        return None

    # Get all rooms in cluster
    rooms = [all_rooms[rid] for rid in cluster]

    # Common terrain
    terrain = rooms[0]['terrain']['name']

    # Collect all keywords
    all_keywords = set()
    for room in rooms:
        all_keywords.update(analyze_room_keywords(room))

    # Room ID range
    room_ids = sorted(cluster)
    min_id = min(room_ids)
    max_id = max(room_ids)

    # Flags
    all_flags = set()
    for room in rooms:
        all_flags.update(room.get('room_flags', {}).get('decoded_flags', []))

    # Sample descriptions
    sample_descs = [r['short_description'] for r in rooms[:3]]

    return {
        'size': len(cluster),
        'room_ids': room_ids,
        'room_id_range': (min_id, max_id),
        'terrain': terrain,
        'keywords': sorted(all_keywords),
        'flags': sorted(all_flags),
        'sample_descriptions': sample_descs,
        'source_areas': sorted(set(r['source_area'] for r in rooms))
    }


def suggest_zone_name(analysis):
    """Suggest a zone name based on analysis."""
    terrain = analysis['terrain']
    keywords = analysis['keywords']
    flags = analysis['flags']

    # Prioritize specific keywords over terrain
    if 'town' in keywords or 'city' in keywords:
        return f"Town Area ({terrain})"
    elif 'temple' in keywords or 'shrine' in keywords:
        return f"Temple District ({terrain})"
    elif 'arena' in keywords:
        return "Arena"
    elif 'tavern' in keywords or 'inn' in keywords:
        return "Tavern District"
    elif 'shop' in keywords or 'market' in keywords:
        return "Market District"
    elif 'castle' in keywords or 'fortress' in keywords:
        return f"Castle ({terrain})"
    elif 'fire' in keywords or 'lava' in keywords:
        return "Fire Realm"
    elif 'ice' in keywords or 'frozen' in keywords:
        return "Ice Realm"
    elif 'dungeon' in keywords or 'cave' in keywords:
        if terrain == 'DUNGEON1':
            return "Dungeon Level 1"
        elif terrain == 'DUNGEON2':
            return "Dungeon Level 2"
        elif terrain == 'DUNGEON3':
            return "Dungeon Level 3"
        else:
            return f"Dungeon ({terrain})"
    elif 'forest' in keywords:
        return "Forest"
    elif 'swamp' in keywords or 'marsh' in keywords:
        return "Swamp"
    elif 'desert' in keywords:
        return "Desert"
    elif 'mountain' in keywords:
        return "Mountains"
    elif 'jungle' in keywords:
        return "Jungle"
    else:
        # Fallback to terrain
        return terrain.title().replace('_', ' ')


def main():
    export_dir = "config/temp/world1_export"

    print("="*60)
    print("World1 Zone Analysis")
    print("="*60)

    # Load all areas
    areas = load_all_areas(export_dir)

    # Extract all rooms
    all_rooms = extract_all_rooms(areas)

    # Build connectivity graph
    print("Building room connection graph...")
    graph = build_room_graph(all_rooms)

    # Cluster rooms
    print("Clustering rooms by terrain and connectivity...")
    clusters = cluster_by_terrain_and_connectivity(all_rooms, graph)

    print(f"Found {len(clusters)} distinct clusters")
    print()

    # Analyze each cluster
    zones = []
    for i, cluster in enumerate(clusters, 1):
        analysis = analyze_cluster(cluster, all_rooms)
        zone_name = suggest_zone_name(analysis)

        zones.append({
            'zone_id': i,
            'zone_name': zone_name,
            **analysis
        })

    # Sort zones by size (largest first)
    zones.sort(key=lambda z: z['size'], reverse=True)

    # Print summary
    print("="*60)
    print("ZONE SUMMARY")
    print("="*60)

    for zone in zones:
        print(f"\nZone {zone['zone_id']}: {zone['zone_name']}")
        print(f"  Size: {zone['size']} rooms")
        print(f"  Room ID range: {zone['room_id_range'][0]} - {zone['room_id_range'][1]}")
        print(f"  Terrain: {zone['terrain']}")
        print(f"  Keywords: {', '.join(zone['keywords']) if zone['keywords'] else 'none'}")
        print(f"  Flags: {', '.join(zone['flags']) if zone['flags'] else 'none'}")
        print(f"  Sample rooms:")
        for desc in zone['sample_descriptions']:
            print(f"    - {desc}")

    # Export to JSON
    output_file = "config/temp/zone_analysis.json"
    with open(output_file, 'w') as f:
        json.dump({
            'total_rooms': len(all_rooms),
            'total_zones': len(zones),
            'zones': zones
        }, f, indent=2)

    print()
    print("="*60)
    print(f"Analysis complete! Results saved to: {output_file}")
    print("="*60)


if __name__ == "__main__":
    main()
