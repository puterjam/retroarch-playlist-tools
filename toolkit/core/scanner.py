"""
ROM Scanner Module
Scans directories for ROM files
"""

from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
import json

from .utils import calculate_crc32, normalize_rom_name, is_hack_version, extract_region_info, format_file_size


@dataclass
class ROMInfo:
    """ROM file information"""
    path: str
    filename: str
    system: str
    extension: str
    size: int
    size_formatted: str
    crc32: Optional[str] = None
    normalized_name: str = ""
    is_hack: bool = False
    base_game_name: Optional[str] = None
    region: Optional[str] = None
    matched: bool = False
    game_name: Optional[str] = None
    release_year: Optional[int] = None
    developer: Optional[str] = None
    publisher: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class ROMScanner:
    """Scans directories for ROM files"""

    def __init__(self, config):
        """Initialize scanner

        Args:
            config: Config instance
        """
        self.config = config
        self.roms: List[ROMInfo] = []

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
            print(f"\nUnmatched ROMs: {len(unmatched)}")

        print("=" * 60)
