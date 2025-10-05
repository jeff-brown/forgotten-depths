"""Configuration manager for loading items and vendors from YAML files."""

import os
import yaml
import json
from typing import Dict, Any, Optional, List
from pathlib import Path


class ConfigManager:
    """Manages loading and caching of configuration data."""

    def __init__(self, config_dir: str = None):
        """Initialize the config manager.

        Args:
            config_dir: Path to configuration directory. If None, uses default.
        """
        if config_dir is None:
            # Default to config directory relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        self._items_cache = None
        self._vendors_cache = None
        self._vendors_by_location = None
        self.game_data = {}  # For storing races, classes, spells, etc.
        self.game_settings = {}  # For storing game settings from game_settings.yaml

        # Load game data on initialization
        self._load_game_data()
        self._load_game_settings()

    def load_items(self) -> Dict[str, Any]:
        """Load items configuration from JSON files (by type)."""
        if self._items_cache is None:
            items_dir = Path("data/items")
            all_items = {}

            # Load items from type-specific JSON files
            if items_dir.exists():
                for item_file in items_dir.glob("*.json"):
                    # Skip items.json if it exists (legacy file)
                    if item_file.name == "items.json":
                        continue

                    try:
                        with open(item_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            type_items = config.get('items', {})
                            all_items.update(type_items)
                    except Exception as e:
                        print(f"Warning: Could not load items from {item_file}: {e}")

            # Fallback to legacy items.json if no type files found
            if not all_items:
                items_file_json = Path("data/items/items.json")
                items_file_yaml = self.config_dir / "items.yaml"

                if items_file_json.exists():
                    with open(items_file_json, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    all_items = config.get('items', {})
                elif items_file_yaml.exists():
                    with open(items_file_yaml, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    all_items = config.get('items', {})
                else:
                    raise FileNotFoundError(f"Items config files not found in {items_dir}")

            self._items_cache = all_items

        return self._items_cache

    def load_vendors(self) -> Dict[str, Any]:
        """Load vendors configuration from YAML file."""
        if self._vendors_cache is None:
            vendors_file = self.config_dir / "vendors.yaml"

            if not vendors_file.exists():
                raise FileNotFoundError(f"Vendors config file not found: {vendors_file}")

            with open(vendors_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self._vendors_cache = config.get('vendors', {})

        return self._vendors_cache

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item configuration by ID."""
        items = self.load_items()
        return items.get(item_id)

    def get_vendor_for_location(self, location: str) -> Optional[Dict[str, Any]]:
        """Get vendor configuration for a specific location."""
        if self._vendors_by_location is None:
            self._build_vendor_location_cache()

        return self._vendors_by_location.get(location)

    def _build_vendor_location_cache(self):
        """Build cache mapping locations to vendors."""
        self._vendors_by_location = {}
        vendors = self.load_vendors()

        for vendor_id, vendor_config in vendors.items():
            locations = vendor_config.get('locations', [])
            for location in locations:
                if location in self._vendors_by_location:
                    print(f"Warning: Multiple vendors for location '{location}': "
                          f"{self._vendors_by_location[location]['id']} and {vendor_id}")

                # Add vendor ID to the config for easier reference
                vendor_data = vendor_config.copy()
                vendor_data['id'] = vendor_id
                self._vendors_by_location[location] = vendor_data

    def get_vendor_inventory_with_items(self, vendor_id: str) -> List[Dict[str, Any]]:
        """Get vendor inventory with full item details."""
        vendors = self.load_vendors()
        vendor = vendors.get(vendor_id)

        if not vendor:
            return []

        inventory = []
        for item_entry in vendor.get('inventory', []):
            item_id = item_entry['item_id']
            item_config = self.get_item(item_id)

            if item_config:
                # Combine item config with vendor-specific pricing
                inventory_item = {
                    'item_id': item_id,
                    'name': item_config['name'],
                    'price': item_entry['price'],
                    'stock': item_entry.get('stock', 1),
                    'weight': item_config['weight'],
                    'description': item_config.get('description', ''),
                    'type': item_config.get('type', 'misc'),
                    'properties': item_config.get('properties', {})
                }
                inventory.append(inventory_item)

        return inventory

    def create_item_instance(self, item_id: str, vendor_price: int = None) -> Optional[Dict[str, Any]]:
        """Create an item instance from configuration.

        Args:
            item_id: The item identifier
            vendor_price: Optional price override from vendor

        Returns:
            Dictionary representing the item instance, or None if item not found
        """
        item_config = self.get_item(item_id)
        if not item_config:
            return None

        # Create item instance with appropriate value
        price = vendor_price if vendor_price is not None else item_config['base_value']

        item_instance = {
            'id': item_id,  # Include item ID for reference
            'name': item_config['name'],
            'weight': item_config.get('weight', 0),  # Default to 0 if missing
            'value': price,  # Use vendor price or base value
            'type': item_config.get('type', 'misc'),
            'description': item_config.get('description', ''),
            'properties': item_config.get('properties', {})
        }

        # Include nutrition/hydration for food/drink items
        if 'nutrition' in item_config:
            item_instance['nutrition'] = item_config['nutrition']
        if 'hydration' in item_config:
            item_instance['hydration'] = item_config['hydration']

        return item_instance

    def get_vendor_buy_price(self, vendor_id: str, item_value: int) -> int:
        """Calculate buy price for an item at a vendor."""
        vendors = self.load_vendors()
        vendor = vendors.get(vendor_id)

        if not vendor:
            return int(item_value * 0.5)  # Default 50%

        buy_rate = vendor.get('buy_rate', 0.5)
        return int(item_value * buy_rate)

    def reload_config(self):
        """Clear cache and force reload of configuration files."""
        self._items_cache = None
        self._vendors_cache = None
        self._vendors_by_location = None
        self._load_game_data()

    def _load_game_data(self):
        """Load game data files (races, classes, spells)."""
        project_root = Path(__file__).parent.parent.parent.parent
        data_dir = project_root / "data"
        player_dir = data_dir / "player"

        # Load races (try new location first, then fall back to old)
        races_file = player_dir / "races.json"
        if not races_file.exists():
            races_file = data_dir / "races.json"
        if races_file.exists():
            with open(races_file, 'r', encoding='utf-8') as f:
                self.game_data['races'] = json.load(f)

        # Load classes (try new location first, then fall back to old)
        classes_file = player_dir / "classes.json"
        if not classes_file.exists():
            classes_file = data_dir / "classes.json"
        if classes_file.exists():
            with open(classes_file, 'r', encoding='utf-8') as f:
                self.game_data['classes'] = json.load(f)

        # Load spells from school-specific JSON files
        spells_dir = data_dir / "spells"
        all_spells = {}

        # Load spells from school-specific files
        if spells_dir.exists():
            for spell_file in spells_dir.glob("*.json"):
                # Skip backup and legacy files
                if spell_file.name in ['spells.json', 'spells.json.backup']:
                    continue

                try:
                    with open(spell_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        school_spells = config.get('spells', {})
                        all_spells.update(school_spells)
                except Exception as e:
                    print(f"Warning: Could not load spells from {spell_file}: {e}")

        # Fallback to legacy spells.json if no school files found
        if not all_spells:
            legacy_file = spells_dir / "spells.json"
            if not legacy_file.exists():
                legacy_file = data_dir / "spells.json"
            if legacy_file.exists():
                with open(legacy_file, 'r', encoding='utf-8') as f:
                    all_spells = json.load(f)

        self.game_data['spells'] = all_spells

    def _load_game_settings(self):
        """Load game settings from game_settings.yaml."""
        settings_file = self.config_dir / "game_settings.yaml"
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                self.game_settings = yaml.safe_load(f) or {}
        else:
            # Use defaults if file doesn't exist
            self.game_settings = {}

    def get_setting(self, *path, default=None):
        """Get a setting value using dot notation.

        Args:
            *path: Path components (e.g., 'player', 'hunger_thirst', 'hunger_decay_per_tick')
            default: Default value if setting not found

        Returns:
            The setting value or default
        """
        value = self.game_settings
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value