"""World loader that supports consolidated data formats."""

import json
import gzip
import pickle
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import time

try:
    from .world_loader import WorldLoader
except ImportError:
    # For standalone execution
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    from world_loader import WorldLoader


class ConsolidatedWorldLoader(WorldLoader):
    """Enhanced world loader that supports consolidated data formats."""

    def __init__(self, data_directory: str = "data"):
        """Initialize the consolidated world loader."""
        super().__init__(data_directory)
        self.load_format = "auto"  # auto, individual, consolidated, compressed, area, binary

    def set_load_format(self, format_type: str):
        """Set the preferred loading format."""
        valid_formats = ["auto", "individual", "consolidated", "compressed", "area", "binary"]
        if format_type not in valid_formats:
            raise ValueError(f"Invalid format: {format_type}. Must be one of: {valid_formats}")
        self.load_format = format_type

    def detect_available_formats(self) -> Dict[str, bool]:
        """Detect which formats are available in the data directory."""
        data_path = Path(self.data_dir)

        formats = {
            'individual': False,
            'consolidated': False,
            'compressed': False,
            'area': False,
            'binary': False
        }

        # Check for individual files
        rooms_dir = data_path / 'world' / 'rooms'
        if rooms_dir.exists() and any(rooms_dir.glob('*.json')):
            formats['individual'] = True

        # Check for consolidated JSON
        consolidated_file = data_path / 'world_consolidated.json'
        if consolidated_file.exists():
            formats['consolidated'] = True

        # Check for compressed JSON
        compressed_file = data_path / 'world_consolidated_compressed.gz'
        if compressed_file.exists():
            formats['compressed'] = True

        # Check for area-based files
        area_dir = data_path / 'by_area'
        if area_dir.exists() and any(area_dir.glob('area_*.json')):
            formats['area'] = True

        # Check for binary format
        binary_file = data_path / 'world_data.pkl'
        if binary_file.exists():
            formats['binary'] = True

        return formats

    def choose_optimal_format(self) -> str:
        """Choose the optimal format based on what's available."""
        available = self.detect_available_formats()

        # Priority order: binary > compressed > area > consolidated > individual
        if available['binary']:
            return 'binary'
        elif available['compressed']:
            return 'compressed'
        elif available['area']:
            return 'area'
        elif available['consolidated']:
            return 'consolidated'
        elif available['individual']:
            return 'individual'
        else:
            raise FileNotFoundError("No world data found in any supported format")

    def load_from_binary(self) -> Dict[str, Any]:
        """Load world data from binary format (fastest)."""
        binary_file = Path(self.data_dir) / 'world_data.pkl'

        start_time = time.time()
        with open(binary_file, 'rb') as f:
            world_data = pickle.load(f)
        load_time = time.time() - start_time

        print(f"Loaded world from binary format in {load_time:.3f}s")
        return world_data

    def load_from_compressed(self) -> Dict[str, Any]:
        """Load world data from compressed JSON format."""
        compressed_file = Path(self.data_dir) / 'world_consolidated_compressed.gz'

        start_time = time.time()
        with gzip.open(compressed_file, 'rt', encoding='utf-8') as f:
            world_data = json.load(f)
        load_time = time.time() - start_time

        print(f"Loaded world from compressed format in {load_time:.3f}s")
        return world_data

    def load_from_consolidated(self) -> Dict[str, Any]:
        """Load world data from single JSON format."""
        consolidated_file = Path(self.data_dir) / 'world_consolidated.json'

        start_time = time.time()
        with open(consolidated_file, 'r', encoding='utf-8') as f:
            world_data = json.load(f)
        load_time = time.time() - start_time

        print(f"Loaded world from consolidated format in {load_time:.3f}s")
        return world_data

    def load_from_area_files(self) -> Dict[str, Any]:
        """Load world data from area-based files."""
        area_dir = Path(self.data_dir) / 'by_area'
        connections_file = area_dir / 'connections.json'

        start_time = time.time()

        world_data = {
            'rooms': {},
            'areas': {},
            'connections': {}
        }

        # Load all area files
        for area_file in area_dir.glob('area_*.json'):
            with open(area_file, 'r', encoding='utf-8') as f:
                area_data = json.load(f)

                # Extract area info
                area_info = area_data['area']
                world_data['areas'][area_info['id']] = area_info

                # Extract rooms
                world_data['rooms'].update(area_data['rooms'])

        # Load connections
        if connections_file.exists():
            with open(connections_file, 'r') as f:
                world_data['connections'] = json.load(f)

        load_time = time.time() - start_time
        print(f"Loaded world from area files in {load_time:.3f}s")
        return world_data

    def load_from_individual_files(self) -> Dict[str, Any]:
        """Load world data from individual files (original format)."""
        start_time = time.time()

        world_data = {
            'rooms': {},
            'areas': {},
            'connections': {}
        }

        # Use parent class methods
        world_data['areas'] = super().load_areas()
        world_data['connections'] = super().load_connections()

        # Load rooms
        rooms_data = super().load_rooms()
        # Convert to the format expected by consolidated loader
        for room_id, room_data in rooms_data.items():
            world_data['rooms'][room_id] = room_data

        load_time = time.time() - start_time
        print(f"Loaded world from individual files in {load_time:.3f}s")
        return world_data

    def load_world_data(self) -> Dict[str, Any]:
        """Load world data using the optimal format."""
        if self.load_format == "auto":
            format_to_use = self.choose_optimal_format()
        else:
            format_to_use = self.load_format
            available = self.detect_available_formats()
            if not available.get(format_to_use, False):
                raise FileNotFoundError(f"Requested format '{format_to_use}' not available")

        print(f"Loading world data using format: {format_to_use}")

        if format_to_use == "binary":
            return self.load_from_binary()
        elif format_to_use == "compressed":
            return self.load_from_compressed()
        elif format_to_use == "consolidated":
            return self.load_from_consolidated()
        elif format_to_use == "area":
            return self.load_from_area_files()
        elif format_to_use == "individual":
            return self.load_from_individual_files()
        else:
            raise ValueError(f"Unknown format: {format_to_use}")

    # Override parent methods to use consolidated loading
    def load_rooms(self) -> Dict[str, Any]:
        """Load rooms using consolidated format."""
        world_data = self.load_world_data()
        return world_data['rooms']

    def load_areas(self) -> Dict[str, Any]:
        """Load areas using consolidated format."""
        world_data = self.load_world_data()
        return world_data['areas']

    def load_connections(self) -> Dict[str, Any]:
        """Load connections using consolidated format."""
        world_data = self.load_world_data()
        return world_data['connections']

    def get_load_performance_stats(self) -> Dict[str, float]:
        """Benchmark different loading formats."""
        available = self.detect_available_formats()
        stats = {}

        for format_name, is_available in available.items():
            if not is_available:
                continue

            print(f"Benchmarking {format_name} format...")

            # Set format and measure load time
            original_format = self.load_format
            self.load_format = format_name

            try:
                start_time = time.time()
                world_data = self.load_world_data()
                end_time = time.time()

                stats[format_name] = {
                    'load_time': end_time - start_time,
                    'rooms_count': len(world_data['rooms']),
                    'areas_count': len(world_data['areas'])
                }

            except Exception as e:
                print(f"Error benchmarking {format_name}: {e}")
                stats[format_name] = {'error': str(e)}

            finally:
                self.load_format = original_format

        return stats


def benchmark_formats(data_directory: str) -> None:
    """Benchmark all available world data formats."""
    print("=== World Data Format Benchmark ===")
    print()

    loader = ConsolidatedWorldLoader(data_directory)
    available = loader.detect_available_formats()

    print("Available formats:")
    for format_name, is_available in available.items():
        status = "✓" if is_available else "✗"
        print(f"  {status} {format_name}")
    print()

    # Run benchmarks
    stats = loader.get_load_performance_stats()

    print("Performance Results:")
    print("-" * 50)
    sorted_stats = sorted(stats.items(), key=lambda x: x[1].get('load_time', float('inf')))

    for format_name, stat in sorted_stats:
        if 'error' in stat:
            print(f"{format_name:12}: ERROR - {stat['error']}")
        else:
            load_time = stat['load_time']
            rooms = stat['rooms_count']
            areas = stat['areas_count']
            print(f"{format_name:12}: {load_time:.3f}s ({rooms} rooms, {areas} areas)")

    print()
    fastest = sorted_stats[0]
    print(f"Fastest format: {fastest[0]} ({fastest[1]['load_time']:.3f}s)")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = "./data/consolidated_ether"

    benchmark_formats(data_dir)