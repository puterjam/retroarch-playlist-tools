"""
Playlist Generator Module
Generates RetroArch playlist files
"""

import json
from pathlib import Path
from typing import List, Dict
from urllib.parse import quote

from .models import ROMInfo
from .chinese_name_mapper import ChineseNameMapper


class PlaylistGenerator:
    """Generates RetroArch playlist files"""

    def __init__(self, config):
        """Initialize playlist generator

        Args:
            config: Config instance
        """
        self.config = config
        self.manual_matches = self._load_manual_matches()
        self.chinese_mapper = ChineseNameMapper()

    def _load_manual_matches(self) -> Dict:
        """Load manual matches from manual_matches.json

        Returns:
            Dictionary of manual matches keyed by CRC32
        """
        manual_matches_path = Path(self.config.get("manual_matches_db", "manual_matches.json"))

        if not manual_matches_path.exists():
            return {}

        try:
            with open(manual_matches_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading manual matches: {e}")
            return {}

    def generate_playlists(self, roms: List[ROMInfo], group_by_system: bool = True) -> Dict[str, str]:
        """Generate playlists for ROMs

        Args:
            roms: List of ROM information
            group_by_system: Group ROMs by system (one playlist per system)

        Returns:
            Dictionary mapping playlist name to file path
        """
        playlists_path = Path(self.config.get("playlists_path"))
        playlists_path.mkdir(parents=True, exist_ok=True)

        generated = {}

        if group_by_system:
            # Group ROMs by system
            systems = {}
            for rom in roms:
                if rom.system not in systems:
                    systems[rom.system] = []
                systems[rom.system].append(rom)

            # Generate playlist for each system
            for system_name, system_roms in systems.items():
                playlist_path = playlists_path / f"{system_name}.lpl"
                if self.create_playlist(system_roms, playlist_path, system_name):
                    generated[system_name] = str(playlist_path)
        else:
            # Single playlist for all ROMs
            playlist_path = playlists_path / "All Games.lpl"
            if self.create_playlist(roms, playlist_path, "All Games"):
                generated["All Games"] = str(playlist_path)

        return generated

    def create_playlist(self, roms: List[ROMInfo], output_path: Path, playlist_name: str) -> bool:
        """Create a RetroArch playlist file

        Args:
            roms: List of ROMs to include
            output_path: Output playlist file path
            playlist_name: Name of the playlist

        Returns:
            True if successful
        """
        try:
            playlist_items = []

            for rom in roms:
                # Get core info for this ROM's system
                core_config = None
                for system, config in self.config.get("cores").items():
                    if system == rom.system:
                        core_config = config
                        break

                if not core_config:
                    print(f"Warning: No core configuration found for {rom.system}")
                    continue

                # Check if there's a manual match for this ROM
                manual_match = None
                if rom.crc32 and rom.crc32 in self.manual_matches:
                    manual_match = self.manual_matches[rom.crc32]

                # Determine display name (priority: manual_match > rom.game_name > normalized_name)
                if manual_match and manual_match.get('matched_name'):
                    display_name = manual_match['matched_name']
                elif rom.game_name:
                    display_name = rom.game_name
                else:
                    display_name = rom.normalized_name

                # Try to get Chinese name from CSV
                chinese_name = self.chinese_mapper.get_chinese_name(rom.system, display_name)
                if chinese_name:
                    # Use Chinese name as label
                    label = chinese_name
                else:
                    # Fall back to English name
                    label = display_name

                # Determine CRC32 (priority: manual matched_crc > rom.crc32)
                if manual_match and manual_match.get('matched_crc'):
                    crc32 = manual_match['matched_crc']
                elif rom.crc32:
                    crc32 = rom.crc32
                else:
                    crc32 = "DETECT"

                # Convert local path to runtime path for playlist
                runtime_path = self.config.get_runtime_rom_path(rom.path)

                # Build playlist entry
                entry = {
                    "path": runtime_path,
                    "label": label,
                    "core_path": "DETECT",  # Let RetroArch detect the core
                    "core_name": core_config["core_name"],
                    "crc32": crc32,
                    "db_name": core_config.get("db_name", "")
                }

                playlist_items.append(entry)

            # Create RetroArch playlist format
            playlist_data = {
                "version": "1.5",
                "default_core_path": "",
                "default_core_name": "",
                "label_display_mode": 0,
                "right_thumbnail_mode": 0,
                "left_thumbnail_mode": 0,
                "thumbnail_match_mode": 0,
                "sort_mode": 0,
                "items": playlist_items
            }

            # Save playlist
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=2, ensure_ascii=False)

            print(f"Generated playlist: {output_path} ({len(playlist_items)} items)")
            return True

        except Exception as e:
            print(f"Error creating playlist {output_path}: {e}")
            return False

    def update_playlist_entry(self, playlist_path: Path, rom_path: str, updates: Dict) -> bool:
        """Update a specific entry in a playlist

        Args:
            playlist_path: Path to playlist file
            rom_path: Path of ROM to update
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        try:
            if not playlist_path.exists():
                print(f"Error: Playlist not found: {playlist_path}")
                return False

            # Load playlist
            with open(playlist_path, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)

            # Find and update entry
            updated = False
            for item in playlist_data.get("items", []):
                if item.get("path") == rom_path:
                    item.update(updates)
                    updated = True
                    break

            if not updated:
                print(f"Warning: ROM not found in playlist: {rom_path}")
                return False

            # Save updated playlist
            with open(playlist_path, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error updating playlist: {e}")
            return False

    def remove_duplicates(self, playlist_path: Path) -> int:
        """Remove duplicate entries from playlist

        Args:
            playlist_path: Path to playlist file

        Returns:
            Number of duplicates removed
        """
        try:
            if not playlist_path.exists():
                return 0

            # Load playlist
            with open(playlist_path, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)

            items = playlist_data.get("items", [])
            original_count = len(items)

            # Remove duplicates (keep first occurrence)
            seen_paths = set()
            unique_items = []

            for item in items:
                path = item.get("path")
                if path not in seen_paths:
                    seen_paths.add(path)
                    unique_items.append(item)

            duplicates_removed = original_count - len(unique_items)

            if duplicates_removed > 0:
                playlist_data["items"] = unique_items

                # Save cleaned playlist
                with open(playlist_path, 'w', encoding='utf-8') as f:
                    json.dump(playlist_data, f, indent=2, ensure_ascii=False)

                print(f"Removed {duplicates_removed} duplicate(s) from {playlist_path}")

            return duplicates_removed

        except Exception as e:
            print(f"Error removing duplicates: {e}")
            return 0

    def sort_playlist(self, playlist_path: Path, sort_by: str = "label") -> bool:
        """Sort playlist entries

        Args:
            playlist_path: Path to playlist file
            sort_by: Field to sort by ('label', 'path', 'core_name')

        Returns:
            True if successful
        """
        try:
            if not playlist_path.exists():
                return False

            # Load playlist
            with open(playlist_path, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)

            items = playlist_data.get("items", [])

            # Sort items
            items.sort(key=lambda x: x.get(sort_by, "").lower())
            playlist_data["items"] = items

            # Save sorted playlist
            with open(playlist_path, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=2, ensure_ascii=False)

            print(f"Sorted playlist by {sort_by}: {playlist_path}")
            return True

        except Exception as e:
            print(f"Error sorting playlist: {e}")
            return False

    def validate_playlist(self, playlist_path: Path) -> List[str]:
        """Validate playlist and check for issues

        Args:
            playlist_path: Path to playlist file

        Returns:
            List of validation warnings/errors
        """
        issues = []

        try:
            if not playlist_path.exists():
                issues.append(f"Playlist file not found: {playlist_path}")
                return issues

            # Load playlist
            with open(playlist_path, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)

            items = playlist_data.get("items", [])

            if not items:
                issues.append("Playlist is empty")
                return issues

            # Check each entry
            for idx, item in enumerate(items):
                rom_path = item.get("path", "")

                # Check if ROM file exists
                if not Path(rom_path).exists():
                    issues.append(f"Entry {idx}: ROM file not found: {rom_path}")

                # Check required fields
                if not item.get("label"):
                    issues.append(f"Entry {idx}: Missing label")

                if not item.get("core_name"):
                    issues.append(f"Entry {idx}: Missing core name")

            return issues

        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON format: {e}")
            return issues
        except Exception as e:
            issues.append(f"Error validating playlist: {e}")
            return issues
