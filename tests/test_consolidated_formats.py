#!/usr/bin/env python3
"""Test script for consolidated world data formats."""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from server.persistence.consolidated_world_loader import ConsolidatedWorldLoader, benchmark_formats

def test_consolidated_formats():
    """Test the consolidated world data formats."""
    print("=== Testing Consolidated World Data Formats ===")
    print()

    # Test with consolidated ether data
    ether_data_dir = "./data/consolidated_ether"

    # Run benchmark
    benchmark_formats(ether_data_dir)

    print()
    print("=== Format Testing ===")

    # Test each format individually
    loader = ConsolidatedWorldLoader(ether_data_dir)

    # Test auto-detection
    print("Auto-detecting optimal format...")
    loader.set_load_format("auto")
    optimal_format = loader.choose_optimal_format()
    print(f"Optimal format: {optimal_format}")
    print()

    # Test loading with optimal format
    print("Loading with optimal format...")
    try:
        world_data = loader.load_world_data()
        print(f"Successfully loaded {len(world_data['rooms'])} rooms")
        print(f"Areas: {len(world_data['areas'])}")
        print(f"Connections: {len(world_data['connections']['rooms'])} room connection sets")
    except Exception as e:
        print(f"Error loading: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_consolidated_formats()