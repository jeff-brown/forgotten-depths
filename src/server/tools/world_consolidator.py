"""Tool to consolidate world data from individual JSON files into optimized formats."""

import json
import os
import gzip
import pickle
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add src to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))


class WorldConsolidator:
    """Consolidates world data into various optimized formats."""

    def __init__(self, world_data_dir: str):
        """Initialize with world data directory."""
        self.world_data_dir = Path(world_data_dir)
        self.rooms_dir = self.world_data_dir / 'world' / 'rooms'
        self.areas_dir = self.world_data_dir / 'world' / 'areas'
        self.connections_file = self.world_data_dir / 'world' / 'connections.json'

    def consolidate_to_single_json(self, output_file: str, compress: bool = False):
        """Consolidate all world data into a single JSON file."""
        print(f"Consolidating world data to {output_file}...")

        consolidated = {
            'metadata': {
                'format': 'consolidated_world_v1',
                'compressed': compress,
                'total_rooms': 0,
                'total_areas': 0
            },
            'rooms': {},
            'areas': {},
            'connections': {}
        }

        # Load all rooms
        if self.rooms_dir.exists():
            print("Loading rooms...")
            room_count = 0
            for room_file in self.rooms_dir.glob('*.json'):
                with open(room_file, 'r', encoding='utf-8') as f:
                    room_data = json.load(f)
                    room_id = room_data['id']
                    consolidated['rooms'][room_id] = room_data
                    room_count += 1

                if room_count % 1000 == 0:
                    print(f"   Loaded {room_count} rooms...")

            consolidated['metadata']['total_rooms'] = room_count
            print(f"   ✓ Loaded {room_count} rooms")

        # Load all areas
        if self.areas_dir.exists():
            print("Loading areas...")
            area_count = 0
            for area_file in self.areas_dir.glob('*.json'):
                with open(area_file, 'r', encoding='utf-8') as f:
                    area_data = json.load(f)
                    area_id = area_data['id']
                    consolidated['areas'][area_id] = area_data
                    area_count += 1

            consolidated['metadata']['total_areas'] = area_count
            print(f"   ✓ Loaded {area_count} areas")

        # Load connections
        if self.connections_file.exists():
            print("Loading connections...")
            with open(self.connections_file, 'r') as f:
                consolidated['connections'] = json.load(f)
            print("   ✓ Loaded connections")

        # Write consolidated file
        output_path = Path(output_file)
        print(f"Writing consolidated data to {output_path}...")

        if compress:
            # Write compressed JSON
            with gzip.open(f"{output_path}.gz", 'wt', encoding='utf-8') as f:
                json.dump(consolidated, f, separators=(',', ':'))
            print(f"   ✓ Written compressed file: {output_path}.gz")
        else:
            # Write regular JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(consolidated, f, indent=2)
            print(f"   ✓ Written file: {output_path}")

        return consolidated

    def consolidate_by_area(self, output_dir: str):
        """Consolidate rooms by area into separate files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"Consolidating rooms by area to {output_dir}...")

        # First, load all areas to understand the structure
        areas = {}
        if self.areas_dir.exists():
            for area_file in self.areas_dir.glob('*.json'):
                with open(area_file, 'r', encoding='utf-8') as f:
                    area_data = json.load(f)
                    areas[area_data['id']] = area_data

        # Group rooms by area
        area_rooms = {area_id: [] for area_id in areas.keys()}
        orphaned_rooms = []

        if self.rooms_dir.exists():
            print("Grouping rooms by area...")
            room_count = 0
            for room_file in self.rooms_dir.glob('*.json'):
                with open(room_file, 'r', encoding='utf-8') as f:
                    room_data = json.load(f)
                    area_id = room_data.get('area_id', 'unknown')

                    if area_id in area_rooms:
                        area_rooms[area_id].append(room_data)
                    else:
                        orphaned_rooms.append(room_data)

                    room_count += 1

                if room_count % 1000 == 0:
                    print(f"   Processed {room_count} rooms...")

            print(f"   ✓ Processed {room_count} rooms")

        # Write area files
        for area_id, rooms in area_rooms.items():
            if not rooms:
                continue

            area_file_data = {
                'area': areas.get(area_id, {'id': area_id, 'name': area_id}),
                'rooms': {room['id']: room for room in rooms},
                'room_count': len(rooms)
            }

            area_file = output_path / f"area_{area_id}.json"
            with open(area_file, 'w', encoding='utf-8') as f:
                json.dump(area_file_data, f, indent=2)

            print(f"   ✓ {area_id}: {len(rooms)} rooms -> {area_file.name}")

        # Handle orphaned rooms
        if orphaned_rooms:
            orphaned_file_data = {
                'area': {'id': 'orphaned', 'name': 'Orphaned Rooms'},
                'rooms': {room['id']: room for room in orphaned_rooms},
                'room_count': len(orphaned_rooms)
            }

            orphaned_file = output_path / "area_orphaned.json"
            with open(orphaned_file, 'w', encoding='utf-8') as f:
                json.dump(orphaned_file_data, f, indent=2)

            print(f"   ✓ orphaned: {len(orphaned_rooms)} rooms -> {orphaned_file.name}")

        # Copy connections file
        if self.connections_file.exists():
            connections_dest = output_path / "connections.json"
            with open(self.connections_file, 'r') as src, open(connections_dest, 'w') as dst:
                dst.write(src.read())
            print(f"   ✓ Copied connections to {connections_dest.name}")

    def consolidate_to_binary(self, output_file: str):
        """Consolidate to binary format for fastest loading."""
        print(f"Consolidating to binary format: {output_file}...")

        world_data = {
            'rooms': {},
            'areas': {},
            'connections': {}
        }

        # Load all data
        if self.rooms_dir.exists():
            print("Loading rooms for binary conversion...")
            room_count = 0
            for room_file in self.rooms_dir.glob('*.json'):
                with open(room_file, 'r', encoding='utf-8') as f:
                    room_data = json.load(f)
                    world_data['rooms'][room_data['id']] = room_data
                    room_count += 1

                if room_count % 1000 == 0:
                    print(f"   Loaded {room_count} rooms...")

            print(f"   ✓ Loaded {room_count} rooms")

        if self.areas_dir.exists():
            for area_file in self.areas_dir.glob('*.json'):
                with open(area_file, 'r', encoding='utf-8') as f:
                    area_data = json.load(f)
                    world_data['areas'][area_data['id']] = area_data

        if self.connections_file.exists():
            with open(self.connections_file, 'r') as f:
                world_data['connections'] = json.load(f)

        # Write binary file
        with open(output_file, 'wb') as f:
            pickle.dump(world_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        print(f"   ✓ Written binary file: {output_file}")

        # Show size comparison
        original_size = sum(f.stat().st_size for f in self.rooms_dir.glob('*.json'))
        binary_size = Path(output_file).stat().st_size
        compression_ratio = (1 - binary_size / original_size) * 100

        print(f"   Original size: {original_size / (1024*1024):.1f} MB")
        print(f"   Binary size: {binary_size / (1024*1024):.1f} MB")
        print(f"   Compression: {compression_ratio:.1f}%")

    def create_optimized_formats(self, base_output_dir: str):
        """Create multiple optimized formats."""
        output_dir = Path(base_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print("=== Creating Optimized World Data Formats ===")
        print()

        # 1. Single JSON file
        print("1. Creating single JSON file...")
        single_json = output_dir / "world_consolidated.json"
        self.consolidate_to_single_json(str(single_json))
        print()

        # 2. Compressed single JSON
        print("2. Creating compressed JSON file...")
        compressed_json = output_dir / "world_consolidated_compressed"
        self.consolidate_to_single_json(str(compressed_json), compress=True)
        print()

        # 3. Area-based files
        print("3. Creating area-based files...")
        area_dir = output_dir / "by_area"
        self.consolidate_by_area(str(area_dir))
        print()

        # 4. Binary format
        print("4. Creating binary format...")
        binary_file = output_dir / "world_data.pkl"
        self.consolidate_to_binary(str(binary_file))
        print()

        # Show summary
        print("=== Consolidation Summary ===")
        original_files = len(list(self.rooms_dir.glob('*.json')))
        print(f"Original: {original_files} individual room files")
        print(f"Created formats:")
        print(f"  - Single JSON: world_consolidated.json")
        print(f"  - Compressed: world_consolidated_compressed.json.gz")
        print(f"  - By area: {len(list((output_dir / 'by_area').glob('area_*.json')))} area files")
        print(f"  - Binary: world_data.pkl (fastest loading)")

        return {
            'single_json': str(single_json),
            'compressed_json': str(compressed_json) + '.gz',
            'area_dir': str(area_dir),
            'binary_file': str(binary_file)
        }


def main():
    """Main function to run consolidation."""
    import argparse

    parser = argparse.ArgumentParser(description='Consolidate MUD world data files')
    parser.add_argument('input_dir', help='Input directory containing world data')
    parser.add_argument('output_dir', help='Output directory for consolidated data')
    parser.add_argument('--format', choices=['all', 'json', 'compressed', 'area', 'binary'],
                       default='all', help='Output format(s) to create')

    args = parser.parse_args()

    consolidator = WorldConsolidator(args.input_dir)

    if args.format == 'all':
        consolidator.create_optimized_formats(args.output_dir)
    elif args.format == 'json':
        output_file = Path(args.output_dir) / "world_consolidated.json"
        consolidator.consolidate_to_single_json(str(output_file))
    elif args.format == 'compressed':
        output_file = Path(args.output_dir) / "world_consolidated_compressed"
        consolidator.consolidate_to_single_json(str(output_file), compress=True)
    elif args.format == 'area':
        consolidator.consolidate_by_area(args.output_dir)
    elif args.format == 'binary':
        output_file = Path(args.output_dir) / "world_data.pkl"
        consolidator.consolidate_to_binary(str(output_file))


if __name__ == '__main__':
    main()