"""
ROM Matcher Module
Matches ROMs to game databases
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from .models import ROMInfo
from .rdb_query import LibretroDBQuery


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
        self.rdb_query = LibretroDBQuery()
        self.missing_databases = set()  # Track missing databases

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

        # Check if database exists
        if not db_path.exists():
            print(f"Warning: Database not found: {db_path}")
            self.missing_databases.add(system)
            return False

        try:
            # Use libretrodb_tool for RDB files, fallback to JSON
            if db_path.suffix == '.rdb':
                # Check if RDB is accessible via libretrodb_tool
                if self.rdb_query.check_db_exists(db_path):
                    # Store the database path for later queries
                    self.databases[system] = {
                        'type': 'rdb',
                        'path': db_path
                    }
                    print(f"Loaded RDB database for {system}: {db_path.name}")
                    return True
                else:
                    print(f"Error: Cannot access RDB database: {db_path}")
                    return False
            elif db_path.suffix == '.json':
                with open(db_path, 'r', encoding='utf-8') as f:
                    self.databases[system] = {
                        'type': 'json',
                        'data': json.load(f)
                    }
                print(f"Loaded JSON database for {system}: {len(self.databases[system]['data'])} entries")
                return True
            else:
                print(f"Error: Unsupported database format: {db_path.suffix}")
                return False

        except Exception as e:
            print(f"Error loading database {db_path}: {e}")
            return False

    def _parse_rdb(self, db_path: Path) -> List[Dict]:
        """Parse RetroArch RDB format using libretrodb_tool

        Args:
            db_path: Path to RDB file

        Returns:
            List of game entries
        """
        # This method is deprecated, use load_database instead
        print(f"Warning: Direct RDB parsing is deprecated. Use load_database() instead.")
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

    def _match_by_crc32(self, crc32: str, database: Dict) -> Optional[Dict]:
        """Match by CRC32 checksum

        Args:
            crc32: CRC32 checksum
            database: Game database metadata

        Returns:
            Matched entry or None
        """
        if database['type'] == 'rdb':
            # Use libretrodb_tool for RDB databases
            try:
                return self.rdb_query.find_by_crc32(database['path'], crc32)
            except Exception as e:
                print(f"Error querying RDB: {e}")
                return None
        else:
            # Fallback to JSON search
            crc32_lower = crc32.lower()
            for entry in database['data']:
                if entry.get('crc', '').lower() == crc32_lower:
                    return entry
            return None

    def _match_by_name(self, normalized_name: str, database: Dict) -> Optional[Dict]:
        """Match by normalized name

        Args:
            normalized_name: Normalized ROM name
            database: Game database metadata

        Returns:
            Matched entry or None
        """
        if database['type'] == 'rdb':
            # Try glob pattern matching with libretrodb_tool
            try:
                # Try exact match first
                results = self.rdb_query.find_by_name_glob(database['path'], normalized_name)
                if results:
                    return results[0]
                return None
            except Exception as e:
                print(f"Error querying RDB: {e}")
                return None
        else:
            # Fallback to JSON search
            normalized_lower = normalized_name.lower()
            for entry in database['data']:
                entry_name = entry.get('name', '').lower()
                if entry_name == normalized_lower:
                    return entry
            return None

    def _fuzzy_match(self, normalized_name: str, database: Dict,
                     threshold: float = 0.8) -> Optional[Dict]:
        """Fuzzy match by name similarity

        Args:
            normalized_name: Normalized ROM name
            database: Game database metadata
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            Best matched entry or None
        """
        best_match = None
        best_score = threshold

        normalized_lower = normalized_name.lower()

        # Get all entries for fuzzy matching
        entries = []
        if database['type'] == 'rdb':
            try:
                # Try wildcard search to get candidates
                entries = self.rdb_query.find_by_name_glob(database['path'], '*')
            except Exception as e:
                print(f"Error querying RDB for fuzzy match: {e}")
                return None
        else:
            entries = database['data']

        for entry in entries:
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

        # First, apply manual matches
        manual_matched = self.apply_manual_matches(roms)
        matched += manual_matched

        # Then try automatic matching for remaining ROMs
        for rom in roms:
            if rom.matched:
                continue  # Already matched by manual matches

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

        database = self.databases[system]
        normalized_lower = rom_info.normalized_name.lower()

        # Get all entries
        entries = []
        if database['type'] == 'rdb':
            try:
                entries = self.rdb_query.find_by_name_glob(database['path'], '*')
            except Exception:
                return []
        else:
            entries = database['data']

        # Calculate similarity scores for all games
        similarities = []
        for entry in entries:
            entry_name = entry.get('name', '').lower()
            score = SequenceMatcher(None, normalized_lower, entry_name).ratio()
            similarities.append((entry, score))

        # Sort by score and return top matches
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    def get_missing_databases(self) -> List[str]:
        """Get list of missing database systems

        Returns:
            List of system names with missing databases
        """
        return list(self.missing_databases)

    def has_missing_databases(self) -> bool:
        """Check if any databases are missing

        Returns:
            True if databases are missing
        """
        return len(self.missing_databases) > 0

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
        """Load manually matched games from manual_matches.json

        Returns:
            Dictionary of manual matches
        """
        manual_matches_path = Path(self.config.get("manual_matches_db", "manual_matches.json"))

        if not manual_matches_path.exists():
            return {}

        try:
            with open(manual_matches_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading manual matches: {e}")
            return {}

    def save_manual_match(self, rom_crc32: str, matched_entry: Dict, rom_info: Dict) -> bool:
        """Save a manual match to manual_matches.json

        Args:
            rom_crc32: CRC32 of the ROM
            matched_entry: The matched database entry
            rom_info: Original ROM information

        Returns:
            True if successful
        """
        manual_matches_path = Path(self.config.get("manual_matches_db", "manual_matches.json"))

        try:
            # Load existing matches
            existing_matches = {}
            if manual_matches_path.exists():
                with open(manual_matches_path, 'r', encoding='utf-8') as f:
                    existing_matches = json.load(f)

            # Add new match (will overwrite if key exists)
            match_data = {
                'filename': rom_info.get('filename'),
                'path': rom_info.get('path'),
                'system': rom_info.get('system'),
                'crc32': rom_crc32,
                'matched_name': matched_entry.get('name'),
                'matched_region': matched_entry.get('region'),
                'matched_crc': matched_entry.get('crc'),
                'release_year': matched_entry.get('releaseyear'),
                'developer': matched_entry.get('developer'),
                'publisher': matched_entry.get('publisher'),
                'serial': matched_entry.get('serial'),
                'rom_name': matched_entry.get('rom_name'),
            }

            # Add LaunchBox specific fields if present
            if 'launchbox_url' in matched_entry:
                match_data['launchbox_url'] = matched_entry.get('launchbox_url')
            if 'launchbox_id' in matched_entry:
                match_data['launchbox_id'] = matched_entry.get('launchbox_id')
            if 'source' in matched_entry:
                match_data['source'] = matched_entry.get('source')

            existing_matches[rom_crc32] = match_data

            # Save to file
            with open(manual_matches_path, 'w', encoding='utf-8') as f:
                json.dump(existing_matches, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error saving manual match: {e}")
            return False

    def interactive_match_rom(self, rom_info: ROMInfo, limit: int = 10) -> Optional[Dict]:
        """Interactive fuzzy matching for a ROM

        Args:
            rom_info: ROM information
            limit: Maximum number of candidates to show

        Returns:
            Selected game entry or None
        """
        system = rom_info.system

        if system not in self.databases:
            if not self.load_database(system):
                print(f"Cannot load database for {system}")
                return None

        print(f"\n{'='*60}")
        print(f"ROM: {rom_info.filename}")
        print(f"System: {system}")
        print(f"CRC32: {rom_info.crc32}")
        print(f"Normalized Name: {rom_info.normalized_name}")
        print(f"{'='*60}\n")

        # Get similar games
        similar_games = self.find_similar_games(rom_info, limit=limit)

        if not similar_games:
            print("No similar games found in database")
            return None

        print("Similar games found:\n")
        for i, (entry, score) in enumerate(similar_games, 1):
            name = entry.get('name', 'Unknown')
            region = entry.get('region', 'N/A')
            year = entry.get('releaseyear', 'N/A')
            crc = entry.get('crc', 'N/A')
            print(f"  {i}. {name}")
            print(f"     Region: {region} | Year: {year} | CRC: {crc} | Match: {score:.1%}")

        print(f"\n  0. None of these / Skip")
        print(f"  s. Search with custom query")

        while True:
            choice = input("\nSelect a match (number): ").strip().lower()

            if choice == '0':
                return None
            elif choice == 's':
                # Custom search
                query = input("Enter search query: ").strip()
                if not query:
                    continue

                print("\nSearching...")
                database = self.databases[system]

                # Get all entries matching the query
                entries = []
                if database['type'] == 'rdb':
                    try:
                        # Use wildcard search
                        entries = self.rdb_query.find_by_name_glob(database['path'], f'*{query}*')
                    except Exception as e:
                        print(f"Error searching: {e}")
                        continue
                else:
                    # JSON search
                    query_lower = query.lower()
                    for entry in database['data']:
                        entry_name = entry.get('name', '').lower()
                        if query_lower in entry_name:
                            entries.append(entry)

                if not entries:
                    print("No results found")
                    continue

                # Show results
                print(f"\nFound {len(entries)} results:\n")
                display_limit = min(15, len(entries))
                for i, entry in enumerate(entries[:display_limit], 1):
                    name = entry.get('name', 'Unknown')
                    region = entry.get('region', 'N/A')
                    year = entry.get('releaseyear', 'N/A')
                    crc = entry.get('crc', 'N/A')
                    print(f"  {i}. {name}")
                    print(f"     Region: {region} | Year: {year} | CRC: {crc}")

                if len(entries) > display_limit:
                    print(f"\n  ... and {len(entries) - display_limit} more results")

                print(f"\n  0. Back to fuzzy matches")

                sub_choice = input("\nSelect a match (number): ").strip()
                try:
                    idx = int(sub_choice)
                    if idx == 0:
                        continue
                    elif 1 <= idx <= len(entries):
                        return entries[idx - 1]
                    else:
                        print("Invalid choice")
                except ValueError:
                    print("Please enter a number")

            else:
                try:
                    idx = int(choice)
                    if 1 <= idx <= len(similar_games):
                        return similar_games[idx - 1][0]
                    else:
                        print("Invalid choice")
                except ValueError:
                    print("Please enter a number")

    def apply_manual_matches(self, roms: List[ROMInfo]) -> int:
        """Apply manual matches to ROMs

        Args:
            roms: List of ROM information

        Returns:
            Number of ROMs matched from manual_matches.json
        """
        manual_matches = self.load_manual_matches()

        if not manual_matches:
            return 0

        matched_count = 0

        for rom in roms:
            if rom.matched:
                continue  # Already matched

            # Check if there's a manual match for this ROM
            if rom.crc32 and rom.crc32 in manual_matches:
                match = manual_matches[rom.crc32]

                # Update ROM info with manual match data
                rom.matched = True
                rom.game_name = match.get('matched_name')
                rom.release_year = match.get('release_year')
                rom.developer = match.get('developer')
                rom.publisher = match.get('publisher')

                matched_count += 1

        if matched_count > 0:
            print(f"Applied {matched_count} manual matches")

        return matched_count
