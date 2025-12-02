"""
ROM Matcher Module
Matches ROMs to game databases
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from .scanner import ROMInfo


class ROMMatcher:
    """Matches ROMs to game database entries"""

    def __init__(self, config):
        """Initialize matcher

        Args:
            config: Config instance
        """
        self.config = config
        self.databases = {}
        self.unknown_games = []

    def load_database(self, system: str, db_path: Optional[str] = None) -> bool:
        """Load game database for a system

        Args:
            system: System name
            db_path: Path to database file (uses config if None)

        Returns:
            True if successful
        """
        if db_path is None:
            # Try to find database in config path
            db_dir = Path(self.config.get("database_path"))
            core_config = self.config.get(f"cores.{system}")

            if not core_config:
                print(f"Error: System not found in config: {system}")
                return False

            db_name = core_config.get("db_name")
            if not db_name:
                print(f"Error: No database name configured for {system}")
                return False

            db_path = db_dir / db_name

        db_path = Path(db_path)
        if not db_path.exists():
            print(f"Warning: Database not found: {db_path}")
            return False

        try:
            # RetroArch databases are in RDB format (custom binary format)
            # For now, we'll support JSON format for compatibility
            # You may need to convert RDB to JSON using libretro tools

            if db_path.suffix == '.json':
                with open(db_path, 'r', encoding='utf-8') as f:
                    self.databases[system] = json.load(f)
            elif db_path.suffix == '.rdb':
                # Try to parse RDB format
                self.databases[system] = self._parse_rdb(db_path)
            else:
                print(f"Error: Unsupported database format: {db_path.suffix}")
                return False

            print(f"Loaded database for {system}: {len(self.databases[system])} entries")
            return True

        except Exception as e:
            print(f"Error loading database {db_path}: {e}")
            return False

    def _parse_rdb(self, db_path: Path) -> List[Dict]:
        """Parse RetroArch RDB format

        Note: This is a simplified parser. Full RDB parsing is complex.
        Consider using libretro's dat2rdb/rdb2dat tools for conversion.

        Args:
            db_path: Path to RDB file

        Returns:
            List of game entries
        """
        print(f"Warning: RDB parsing not fully implemented. Consider converting to JSON format.")
        print(f"Use: rdb2dat {db_path} > {db_path.with_suffix('.json')}")
        return []

    def match_rom(self, rom_info: ROMInfo) -> Optional[Dict]:
        """Match a ROM to database entry

        Args:
            rom_info: ROM information

        Returns:
            Matched game entry or None
        """
        system = rom_info.system

        if system not in self.databases:
            # Try to load database
            if not self.load_database(system):
                return None

        db = self.databases[system]

        # Try CRC32 match first (most reliable)
        if rom_info.crc32:
            match = self._match_by_crc32(rom_info.crc32, db)
            if match:
                return match

        # Try filename match
        match = self._match_by_name(rom_info.normalized_name, db)
        if match:
            return match

        # Try fuzzy matching as last resort
        match = self._fuzzy_match(rom_info.normalized_name, db)
        if match:
            return match

        return None

    def _match_by_crc32(self, crc32: str, database: List[Dict]) -> Optional[Dict]:
        """Match by CRC32 checksum

        Args:
            crc32: CRC32 checksum
            database: Game database

        Returns:
            Matched entry or None
        """
        crc32_lower = crc32.lower()
        for entry in database:
            if entry.get('crc', '').lower() == crc32_lower:
                return entry
        return None

    def _match_by_name(self, normalized_name: str, database: List[Dict]) -> Optional[Dict]:
        """Match by normalized name

        Args:
            normalized_name: Normalized ROM name
            database: Game database

        Returns:
            Matched entry or None
        """
        normalized_lower = normalized_name.lower()
        for entry in database:
            entry_name = entry.get('name', '').lower()
            if entry_name == normalized_lower:
                return entry
        return None

    def _fuzzy_match(self, normalized_name: str, database: List[Dict],
                     threshold: float = 0.8) -> Optional[Dict]:
        """Fuzzy match by name similarity

        Args:
            normalized_name: Normalized ROM name
            database: Game database
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            Best matched entry or None
        """
        best_match = None
        best_score = threshold

        normalized_lower = normalized_name.lower()

        for entry in database:
            entry_name = entry.get('name', '').lower()
            score = SequenceMatcher(None, normalized_lower, entry_name).ratio()

            if score > best_score:
                best_score = score
                best_match = entry

        return best_match

    def match_all_roms(self, roms: List[ROMInfo]) -> Tuple[int, int]:
        """Match all ROMs to database

        Args:
            roms: List of ROM information

        Returns:
            Tuple of (matched_count, total_count)
        """
        matched = 0
        total = len(roms)

        print(f"Matching {total} ROMs to database...")

        for rom in roms:
            match = self.match_rom(rom)

            if match:
                # Update ROM info with matched data
                rom.matched = True
                rom.game_name = match.get('name')
                rom.release_year = match.get('releaseyear')
                rom.developer = match.get('developer')
                rom.publisher = match.get('publisher')
                matched += 1
            else:
                # Add to unknown games list
                self.unknown_games.append(rom)

        print(f"Matched {matched}/{total} ROMs ({matched/total*100:.1f}%)")
        return matched, total

    def find_similar_games(self, rom_info: ROMInfo, limit: int = 5) -> List[Tuple[Dict, float]]:
        """Find similar games for unmatched ROM

        Args:
            rom_info: ROM information
            limit: Maximum number of results

        Returns:
            List of (game_entry, similarity_score) tuples
        """
        system = rom_info.system

        if system not in self.databases:
            if not self.load_database(system):
                return []

        db = self.databases[system]
        normalized_lower = rom_info.normalized_name.lower()

        # Calculate similarity scores for all games
        similarities = []
        for entry in db:
            entry_name = entry.get('name', '').lower()
            score = SequenceMatcher(None, normalized_lower, entry_name).ratio()
            similarities.append((entry, score))

        # Sort by score and return top matches
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    def save_unknown_games(self) -> bool:
        """Save unknown games to file for manual review

        Returns:
            True if successful
        """
        if not self.unknown_games:
            print("No unknown games to save")
            return True

        unknown_db_path = Path(self.config.get("unknown_games_db"))

        try:
            # Load existing unknown games if file exists
            existing_unknown = {}
            if unknown_db_path.exists():
                with open(unknown_db_path, 'r', encoding='utf-8') as f:
                    existing_unknown = json.load(f)

            # Add new unknown games
            for rom in self.unknown_games:
                # Use CRC32 as key if available, otherwise use filename
                key = rom.crc32 if rom.crc32 else rom.filename

                if key not in existing_unknown:
                    existing_unknown[key] = {
                        'filename': rom.filename,
                        'path': rom.path,
                        'system': rom.system,
                        'crc32': rom.crc32,
                        'normalized_name': rom.normalized_name,
                        'is_hack': rom.is_hack,
                        'base_game_name': rom.base_game_name,
                        'region': rom.region,
                        'manual_name': '',  # User can fill this in
                        'manual_year': None,
                        'notes': ''
                    }

            # Save to file
            with open(unknown_db_path, 'w', encoding='utf-8') as f:
                json.dump(existing_unknown, f, indent=2, ensure_ascii=False)

            print(f"Saved {len(self.unknown_games)} unknown games to {unknown_db_path}")
            print("You can manually edit this file to add game information")
            return True

        except Exception as e:
            print(f"Error saving unknown games: {e}")
            return False

    def load_manual_matches(self) -> Dict:
        """Load manually matched games

        Returns:
            Dictionary of manual matches
        """
        unknown_db_path = Path(self.config.get("unknown_games_db"))

        if not unknown_db_path.exists():
            return {}

        try:
            with open(unknown_db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading manual matches: {e}")
            return {}
