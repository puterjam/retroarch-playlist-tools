"""
ROM Scanner Module
Scans directories for ROM files
"""

from pathlib import Path
from typing import List, Dict, Optional, Callable, TYPE_CHECKING
import json

from .utils import calculate_crc32, normalize_rom_name, is_hack_version, extract_region_info, format_file_size
from .models import ROMInfo

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from .matcher import ROMMatcher
    from .playlist import PlaylistGenerator


class ROMScanner:
    """Scans directories for ROM files"""

    def __init__(self, config):
        """Initialize scanner

        Args:
            config: Config instance
        """
        self.config = config
        self.roms: List[ROMInfo] = []
        self.matcher: Optional[ROMMatcher] = None
        self.playlist_generator: Optional[PlaylistGenerator] = None
        self.unmatched_roms_file = Path(self.config.get("unknown_games_db", "unknown_games.json"))

    def scan(self, path: Optional[str] = None, recursive: bool = True,
             calculate_crc: bool = True, progress_callback: Optional[Callable] = None) -> List[ROMInfo]:
        """Scan directory for ROM files

        Args:
            path: Directory to scan (uses config roms_path if None)
            recursive: Scan subdirectories
            calculate_crc: Calculate CRC32 checksums
            progress_callback: Optional callback function(current, total, rom_info)

        Returns:
            List of ROMInfo objects
        """
        if path is None:
            path = self.config.get("roms_path")

        scan_path = Path(path)
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return []

        print(f"Scanning directory: {scan_path}")

        # Get all supported extensions
        supported_extensions = set(self.config.get_all_extensions())

        # Find all ROM files
        rom_files = []
        if recursive:
            for ext in supported_extensions:
                rom_files.extend(scan_path.rglob(f"*{ext}"))
        else:
            for ext in supported_extensions:
                rom_files.extend(scan_path.glob(f"*{ext}"))

        # Filter out macOS temporary files (._filename) and hidden files
        rom_files_filtered = []
        skipped_count = 0
        for rom_file in rom_files:
            filename = rom_file.name
            # Skip files starting with ._ (AppleDouble format)
            # Skip files starting with . (hidden files)
            if filename.startswith('._') or (filename.startswith('.') and not filename.startswith('..')):
                skipped_count += 1
                continue
            rom_files_filtered.append(rom_file)

        if skipped_count > 0:
            print(f"Skipped {skipped_count} temporary/hidden file(s)")

        rom_files = rom_files_filtered
        print(f"Found {len(rom_files)} ROM files")

        # Process each ROM
        self.roms = []
        for idx, rom_path in enumerate(rom_files, 1):
            if progress_callback:
                progress_callback(idx, len(rom_files), None)

            rom_info = self._process_rom(rom_path, calculate_crc)
            if rom_info:
                self.roms.append(rom_info)

                if progress_callback:
                    progress_callback(idx, len(rom_files), rom_info)

        return self.roms

    def _process_rom(self, rom_path: Path, calculate_crc: bool) -> Optional[ROMInfo]:
        """Process a single ROM file

        Args:
            rom_path: Path to ROM file
            calculate_crc: Calculate CRC32 checksum

        Returns:
            ROMInfo object or None if error
        """
        try:
            # Get file info
            file_size = rom_path.stat().st_size
            extension = rom_path.suffix.lower()

            # Find matching system
            core_config = self.config.get_core_by_extension(extension)
            if not core_config:
                print(f"Warning: No core found for extension {extension}")
                return None

            system_name = core_config["system_name"]

            # Calculate CRC32 if requested
            crc32 = None
            if calculate_crc:
                crc32 = calculate_crc32(rom_path)

            # Normalize name and detect hacks
            normalized_name = normalize_rom_name(rom_path.name)
            is_hack, base_game_name = is_hack_version(rom_path.name)

            # Extract region
            region = extract_region_info(rom_path.name)

            rom_info = ROMInfo(
                path=str(rom_path),
                filename=rom_path.name,
                system=system_name,
                extension=extension,
                size=file_size,
                size_formatted=format_file_size(file_size),
                crc32=crc32,
                normalized_name=normalized_name,
                is_hack=is_hack,
                base_game_name=base_game_name,
                region=region
            )

            return rom_info

        except Exception as e:
            print(f"Error processing {rom_path}: {e}")
            return None

    def get_roms_by_system(self) -> Dict[str, List[ROMInfo]]:
        """Group ROMs by system

        Returns:
            Dictionary mapping system name to list of ROMs
        """
        systems = {}
        for rom in self.roms:
            if rom.system not in systems:
                systems[rom.system] = []
            systems[rom.system].append(rom)
        return systems

    def get_unmatched_roms(self) -> List[ROMInfo]:
        """Get list of ROMs that haven't been matched to database

        Returns:
            List of unmatched ROMs
        """
        return [rom for rom in self.roms if not rom.matched]

    def get_hack_versions(self) -> List[ROMInfo]:
        """Get list of hack/mod ROMs

        Returns:
            List of hack ROMs
        """
        return [rom for rom in self.roms if rom.is_hack]

    def export_scan_results(self, output_path: str) -> bool:
        """Export scan results to JSON

        Args:
            output_path: Path to output file

        Returns:
            True if successful
        """
        try:
            output = {
                "total_roms": len(self.roms),
                "systems": {},
                "roms": [rom.to_dict() for rom in self.roms]
            }

            # Add system statistics
            systems = self.get_roms_by_system()
            for system_name, roms in systems.items():
                output["systems"][system_name] = {
                    "count": len(roms),
                    "total_size": sum(rom.size for rom in roms),
                    "matched": sum(1 for rom in roms if rom.matched),
                    "hacks": sum(1 for rom in roms if rom.is_hack)
                }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print(f"Scan results exported to: {output_path}")
            return True

        except Exception as e:
            print(f"Error exporting scan results: {e}")
            return False

    def scan_and_match(self, path: Optional[str] = None, recursive: bool = True,
                      calculate_crc: bool = True, auto_match: bool = True,
                      generate_playlists: bool = False,
                      progress_callback: Optional[Callable] = None) -> bool:
        """Unified scan, match, and playlist generation

        Args:
            path: Directory to scan (uses config roms_path if None)
            recursive: Scan subdirectories
            calculate_crc: Calculate CRC32 checksums
            auto_match: Automatically match ROMs to database
            generate_playlists: Generate playlists after matching
            progress_callback: Optional callback function(current, total, rom_info)

        Returns:
            True if successful
        """
        # Step 1: Scan ROMs
        print("\n" + "=" * 60)
        print("STEP 1: Scanning ROMs")
        print("=" * 60)

        self.scan(path, recursive, calculate_crc, progress_callback)

        if not self.roms:
            print("No ROMs found!")
            return False

        # Step 2: Match to database (if requested)
        if auto_match:
            print("\n" + "=" * 60)
            print("STEP 2: Matching to Database")
            print("=" * 60)

            # Import here to avoid circular dependency
            from .matcher import ROMMatcher
            self.matcher = ROMMatcher(self.config)
            auto_rename = self.config.get("scan_options.auto_rename", False)
            matched, total = self.matcher.match_all_roms(self.roms, auto_rename=auto_rename)

            # Check for missing databases
            if self.matcher.has_missing_databases():
                missing = self.matcher.get_missing_databases()
                print("\n⚠️  WARNING: Missing databases for systems:")
                for system in missing:
                    print(f"  - {system}")
                print("\nRun 'download-db' command to download missing databases:")
                print("  python main.py download-db")

            # Save unmatched ROMs
            unmatched = self.get_unmatched_roms()
            if unmatched:
                self.save_unmatched_roms(unmatched)

        # Step 3: Generate playlists (if requested)
        if generate_playlists:
            print("\n" + "=" * 60)
            print("STEP 3: Generating Playlists")
            print("=" * 60)

            # Import here to avoid circular dependency
            from .playlist import PlaylistGenerator
            self.playlist_generator = PlaylistGenerator(self.config)
            playlists = self.playlist_generator.generate_playlists(
                self.roms,
                group_by_system=True
            )

            print(f"\n✓ Generated {len(playlists)} playlist(s)")

        # Print final summary
        self.print_summary()

        return True

    def save_unmatched_roms(self, unmatched_roms: List[ROMInfo]) -> bool:
        """Save unmatched ROMs to temporary JSON file

        Args:
            unmatched_roms: List of unmatched ROM information

        Returns:
            True if successful
        """
        if not unmatched_roms:
            return True

        try:
            # Load existing unmatched games if file exists
            existing_data = {}
            if self.unmatched_roms_file.exists():
                with open(self.unmatched_roms_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)

            # Add new unmatched ROMs
            for rom in unmatched_roms:
                # Use CRC32 as key if available, otherwise use path
                key = rom.crc32 if rom.crc32 else rom.path

                if key not in existing_data:
                    existing_data[key] = {
                        'filename': rom.filename,
                        'path': rom.path,
                        'system': rom.system,
                        'crc32': rom.crc32,
                        'normalized_name': rom.normalized_name,
                        'is_hack': rom.is_hack,
                        'base_game_name': rom.base_game_name,
                        'region': rom.region,
                        'size': rom.size,
                        'size_formatted': rom.size_formatted,
                        # Fields for manual completion
                        'manual_name': '',
                        'manual_year': None,
                        'manual_developer': '',
                        'manual_publisher': '',
                        'notes': ''
                    }

            # Save to file
            with open(self.unmatched_roms_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            print(f"\n📝 Saved {len(unmatched_roms)} unmatched ROMs to: {self.unmatched_roms_file}")
            print("   You can manually edit this file to add game information")
            return True

        except Exception as e:
            print(f"Error saving unmatched ROMs: {e}")
            return False

    def print_summary(self):
        """Print scan summary"""
        print("\n" + "=" * 60)
        print("SCAN SUMMARY")
        print("=" * 60)

        print(f"Total ROMs found: {len(self.roms)}")

        systems = self.get_roms_by_system()
        print(f"Systems: {len(systems)}")

        for system_name, roms in sorted(systems.items()):
            total_size = sum(rom.size for rom in roms)
            matched = sum(1 for rom in roms if rom.matched)
            hacks = sum(1 for rom in roms if rom.is_hack)

            print(f"\n  {system_name}:")
            print(f"    ROMs: {len(roms)}")
            print(f"    Size: {format_file_size(total_size)}")
            print(f"    Matched: {matched}/{len(roms)}")
            if hacks > 0:
                print(f"    Hacks: {hacks}")

        unmatched = self.get_unmatched_roms()
        if unmatched:
            print(f"\n⚠️  Unmatched ROMs: {len(unmatched)}")
            print(f"   Use 'python main.py match' to manually match games")

        print("=" * 60)
