"""
Libretro Thumbnails Fetcher
Downloads game thumbnails from thumbnails.libretro.com
"""

import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, List
import re

from ..core.fetcher import FetchPlugin, FetchResult


class LibretroThumbnailsFetcher(FetchPlugin):
    """Fetcher for Libretro thumbnails"""

    PLUGIN_NAME = "libretro_thumbnails"

    # Thumbnail types
    THUMBNAIL_TYPES = ["Named_Boxarts", "Named_Snaps", "Named_Titles"]

    def __init__(self, config: dict):
        """Initialize Libretro Thumbnails fetcher

        Args:
            config: Plugin configuration
        """
        super().__init__(config)
        self.base_url = config.get("base_url", "http://thumbnails.libretro.com")

    def get_name(self) -> str:
        """Get plugin name"""
        return self.PLUGIN_NAME

    def download_thumbnail(self, system: str, game_name: str,
                          thumbnail_type: str = "Named_Boxarts",
                          output_dir: Optional[Path] = None,
                          output_filename: Optional[str] = None) -> FetchResult:
        """Download a game thumbnail

        Args:
            system: System name (e.g., "Nintendo - Nintendo Entertainment System")
            game_name: Game name (must match database name)
            thumbnail_type: Type of thumbnail (Named_Boxarts, Named_Snaps, Named_Titles)
            output_dir: Output directory (uses cache if None)
            output_filename: Override output filename (without extension)

        Returns:
            FetchResult with download status
        """
        if thumbnail_type not in self.THUMBNAIL_TYPES:
            return FetchResult(
                success=False,
                error=f"Invalid thumbnail type: {thumbnail_type}",
                source=self.PLUGIN_NAME
            )

        if output_dir is None:
            output_dir = self.cache_dir / "thumbnails" / system / thumbnail_type

        output_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize game name for filename
        safe_game_name = self._sanitize_thumbnail_name(game_name)

        # Use custom output filename if provided, otherwise use game name
        output_file_base = output_filename if output_filename else safe_game_name

        # Try different image extensions
        extensions = [".png", ".jpg"]

        for ext in extensions:
            # Construct URL using the game_name (for searching in libretro)
            search_filename = f"{safe_game_name}{ext}"
            encoded_system = urllib.parse.quote(system)
            encoded_type = urllib.parse.quote(thumbnail_type)
            encoded_name = urllib.parse.quote(search_filename)
            url = f"{self.base_url}/{encoded_system}/{encoded_type}/{encoded_name}"

            # Save with custom filename
            output_filename_full = f"{output_file_base}{ext}"
            output_path = output_dir / output_filename_full

            # Check if already cached
            if output_path.exists():
                return FetchResult(
                    success=True,
                    data={
                        "path": str(output_path),
                        "type": thumbnail_type,
                        "format": ext[1:]
                    },
                    source=self.PLUGIN_NAME,
                    cached=True
                )

            # Try to download
            if self.download_file(url, output_path):
                return FetchResult(
                    success=True,
                    data={
                        "path": str(output_path),
                        "type": thumbnail_type,
                        "format": ext[1:]
                    },
                    source=self.PLUGIN_NAME
                )

        return FetchResult(
            success=False,
            error=f"Thumbnail not found: {game_name}",
            source=self.PLUGIN_NAME
        )

    def download_all_thumbnails(self, system: str, game_name: str,
                               output_dir: Optional[Path] = None) -> dict:
        """Download all thumbnail types for a game

        Args:
            system: System name
            game_name: Game name
            output_dir: Output directory

        Returns:
            Dictionary mapping thumbnail type to FetchResult
        """
        results = {}

        for thumbnail_type in self.THUMBNAIL_TYPES:
            result = self.download_thumbnail(system, game_name, thumbnail_type, output_dir)
            results[thumbnail_type] = result

        return results

    def batch_download_thumbnails(self, system: str, game_names: List[str],
                                 thumbnail_types: Optional[List[str]] = None,
                                 output_dir: Optional[Path] = None) -> dict:
        """Download thumbnails for multiple games

        Args:
            system: System name
            game_names: List of game names
            thumbnail_types: Types to download (all if None)
            output_dir: Output directory

        Returns:
            Dictionary mapping game name to download results
        """
        if thumbnail_types is None:
            thumbnail_types = self.THUMBNAIL_TYPES

        results = {}

        print(f"Downloading thumbnails for {len(game_names)} game(s)...")

        for idx, game_name in enumerate(game_names, 1):
            print(f"[{idx}/{len(game_names)}] {game_name}")

            game_results = {}
            for thumbnail_type in thumbnail_types:
                result = self.download_thumbnail(system, game_name, thumbnail_type, output_dir)
                game_results[thumbnail_type] = result

                if result.success:
                    status = "cached" if result.cached else "downloaded"
                    print(f"  ✓ {thumbnail_type} ({status})")
                else:
                    print(f"  ✗ {thumbnail_type} (not found)")

            results[game_name] = game_results

        return results

    def _sanitize_thumbnail_name(self, game_name: str) -> str:
        """Sanitize game name for thumbnail filename

        Libretro thumbnails use specific naming conventions

        Args:
            game_name: Original game name

        Returns:
            Sanitized name
        """
        # Replace invalid characters
        name = game_name

        # Replace slashes
        name = name.replace('/', '_')
        name = name.replace('\\', '_')

        # Replace other problematic characters
        name = name.replace(':', '_')
        name = name.replace('*', '_')
        name = name.replace('?', '_')
        name = name.replace('"', '_')
        name = name.replace('<', '_')
        name = name.replace('>', '_')
        name = name.replace('|', '_')

        return name

    def search_game(self, query: str, system: Optional[str] = None, **kwargs) -> FetchResult:
        """Search for game thumbnails

        Args:
            query: Game name
            system: System name (required)
            **kwargs: Additional parameters

        Returns:
            FetchResult with available thumbnails
        """
        if not system:
            return FetchResult(
                success=False,
                error="System name is required for thumbnail search",
                source=self.PLUGIN_NAME
            )

        # Try to download thumbnails
        results = self.download_all_thumbnails(system, query)

        # Check if any were successful
        successful = [t for t, r in results.items() if r.success]

        if successful:
            return FetchResult(
                success=True,
                data={
                    "game_name": query,
                    "system": system,
                    "thumbnails": {t: r.data for t, r in results.items() if r.success}
                },
                source=self.PLUGIN_NAME
            )
        else:
            return FetchResult(
                success=False,
                error=f"No thumbnails found for: {query}",
                source=self.PLUGIN_NAME
            )

    def get_game_info(self, game_id: str, **kwargs) -> FetchResult:
        """Get game thumbnail info

        Args:
            game_id: Game name
            **kwargs: Must include 'system' parameter

        Returns:
            FetchResult with thumbnail info
        """
        system = kwargs.get('system')
        return self.search_game(game_id, system)

    def get_thumbnail_url(self, system: str, game_name: str, thumbnail_type: str, extension: str = "png") -> str:
        """Get thumbnail URL

        Args:
            system: System name
            game_name: Game name
            thumbnail_type: Thumbnail type
            extension: Image extension

        Returns:
            Full thumbnail URL
        """
        safe_game_name = self._sanitize_thumbnail_name(game_name)
        filename = f"{safe_game_name}.{extension}"

        encoded_system = urllib.parse.quote(system)
        encoded_type = urllib.parse.quote(thumbnail_type)
        encoded_name = urllib.parse.quote(filename)

        return f"{self.base_url}/{encoded_system}/{encoded_type}/{encoded_name}"
