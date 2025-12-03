"""
Chinese Name Mapper Module
Maps ROM names to Chinese game names from CSV files
"""

import csv
from pathlib import Path
from typing import Dict, Optional


class ChineseNameMapper:
    """Maps ROM names to Chinese game names"""

    def __init__(self, csv_dir: str = "deps/rom-name-cn"):
        """Initialize Chinese name mapper

        Args:
            csv_dir: Directory containing CSV files with Chinese names
        """
        self.csv_dir = Path(csv_dir)
        self.name_maps: Dict[str, Dict[str, str]] = {}
        self._load_csv_files()

    def _load_csv_files(self):
        """Load all CSV files from the directory"""
        if not self.csv_dir.exists():
            print(f"Warning: Chinese name CSV directory not found: {self.csv_dir}")
            return

        # Mapping of system names to CSV file names
        system_to_csv = {
            "Nintendo - Game Boy": "Nintendo - Game Boy.csv",
            "Nintendo - Game Boy Color": "Nintendo - Game Boy Color.csv",
            "Nintendo - Game Boy Advance": "Nintendo - Game Boy Advance.csv",
            "Nintendo - Nintendo Entertainment System": "Nintendo - Nintendo Entertainment System.csv",
            "Nintendo - Super Nintendo Entertainment System": "Nintendo - Super Nintendo Entertainment System.csv",
            "Nintendo - Nintendo 64": "Nintendo - Nintendo 64.csv",
            "Nintendo - GameCube": "Nintendo - GameCube.csv",
            "Nintendo - Wii": "Nintendo - Wii.csv",
            "Nintendo - Nintendo DS": "Nintendo - Nintendo DS.csv",
            "Nintendo - Nintendo 3DS": "Nintendo - Nintendo 3DS.csv",
            "Sega - Master System - Mark III": "Sega - Master System.csv",
            "Sega - Mega Drive - Genesis": "Sega - Mega Drive - Genesis.csv",
            "Sega - Game Gear": "Sega - Game Gear.csv",
            "Sega - Saturn": "Sega - Saturn.csv",
            "Sega - Dreamcast": "Sega - Dreamcast.csv",
            "Sony - PlayStation": "Sony - PlayStation.csv",
            "Sony - PlayStation Portable": "Sony - PlayStation Portable.csv",
            "SNK - Neo Geo": "Arcade - NEOGEO.csv",
            "FBNeo - Arcade Games": "Arcade - NEOGEO.csv",
        }

        for system_name, csv_filename in system_to_csv.items():
            csv_path = self.csv_dir / csv_filename
            if csv_path.exists():
                self.name_maps[system_name] = self._load_csv(csv_path)

    def _load_csv(self, csv_path: Path) -> Dict[str, str]:
        """Load a single CSV file

        Args:
            csv_path: Path to CSV file

        Returns:
            Dictionary mapping English name to Chinese name
        """
        name_map = {}

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # Check CSV format
                fieldnames = reader.fieldnames
                if not fieldnames:
                    return name_map

                # Handle different CSV formats
                if 'MAME Name' in fieldnames:
                    # Format: MAME Name, EN Name, CN Name (for arcade games)
                    for row in reader:
                        mame_name = row.get('MAME Name', '').strip()
                        en_name = row.get('EN Name', '').strip()
                        cn_name = row.get('CN Name', '').strip()

                        if en_name and cn_name:
                            name_map[en_name] = cn_name
                        if mame_name and cn_name:
                            # Also map MAME name for arcade games
                            name_map[mame_name] = cn_name

                elif 'Name EN' in fieldnames and 'Name CN' in fieldnames:
                    # Format: Name EN, Name CN
                    for row in reader:
                        en_name = row.get('Name EN', '').strip()
                        cn_name = row.get('Name CN', '').strip()

                        if en_name and cn_name:
                            name_map[en_name] = cn_name

        except Exception as e:
            print(f"Warning: Error loading CSV {csv_path}: {e}")

        return name_map

    def get_chinese_name(self, system: str, en_name: str) -> Optional[str]:
        """Get Chinese name for a game

        Args:
            system: System name (e.g., "Nintendo - Game Boy Advance")
            en_name: English game name

        Returns:
            Chinese name if found, None otherwise
        """
        if system not in self.name_maps:
            return None

        name_map = self.name_maps[system]

        # Try exact match first
        if en_name in name_map:
            return name_map[en_name]

        # Try case-insensitive match
        en_name_lower = en_name.lower()
        for key, value in name_map.items():
            if key.lower() == en_name_lower:
                return value

        return None

    def has_mapping_for_system(self, system: str) -> bool:
        """Check if Chinese name mapping exists for a system

        Args:
            system: System name

        Returns:
            True if mapping exists
        """
        return system in self.name_maps
