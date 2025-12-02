"""
RetroArch Database Fetcher
Downloads and manages RetroArch official game databases
"""

import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, List
import json

from ..core.fetcher import FetchPlugin, FetchResult


class RetroArchDBFetcher(FetchPlugin):
    """Fetcher for RetroArch official databases"""

    PLUGIN_NAME = "retroarch_db"

    def __init__(self, config: dict):
        """Initialize RetroArch DB fetcher

        Args:
            config: Plugin configuration
        """
        super().__init__(config)
        self.base_url = config.get("base_url", "https://github.com/libretro/libretro-database/raw/master/rdb")
        self.available_databases = self._load_available_databases()

    def _load_available_databases(self) -> List[str]:
        """Load available databases list from cores config file

        Returns:
            List of database names extracted from cores configuration
        """
        # Try to load from cores config file
        config_file = Path(__file__).parent.parent.parent / "config" / "cores.json"

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cores = data.get("cores", {})
                    # Extract db_name from each core configuration
                    databases = []
                    for system_name, core_config in cores.items():
                        db_name = core_config.get("db_name")
                        if db_name and db_name not in databases:
                            databases.append(db_name)
                    return databases
            except Exception as e:
                print(f"Warning: Could not load cores config: {e}")

        # Fallback to minimal default list
        return [
            "Nintendo - Nintendo Entertainment System.rdb",
            "MAME.rdb"
        ]

    def get_name(self) -> str:
        """Get plugin name"""
        return self.PLUGIN_NAME

    def download_database(self, db_name: str, output_dir: Optional[Path] = None) -> FetchResult:
        """Download a RetroArch database file

        Args:
            db_name: Database filename (e.g., "Nintendo - Nintendo Entertainment System.rdb")
            output_dir: Output directory (uses cache if None)

        Returns:
            FetchResult with download status
        """
        if output_dir is None:
            output_dir = self.cache_dir / "databases"

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / db_name

        # Check if already cached
        if output_path.exists():
            file_size = output_path.stat().st_size
            # Use the _format_size from parent class
            from ..core.utils import format_file_size
            size_str = format_file_size(file_size)
            return FetchResult(
                success=True,
                data={"path": str(output_path), "size": file_size, "size_str": size_str},
                source=self.PLUGIN_NAME,
                cached=True
            )

        # Construct download URL
        # URL encode the database name
        encoded_name = urllib.parse.quote(db_name)
        url = f"{self.base_url}/{encoded_name}"

        # Download file with progress (inline display)
        if self.download_file(url, output_path, show_progress=True):
            file_size = output_path.stat().st_size
            from ..core.utils import format_file_size
            size_str = format_file_size(file_size)
            return FetchResult(
                success=True,
                data={"path": str(output_path), "size": file_size, "size_str": size_str},
                source=self.PLUGIN_NAME
            )
        else:
            return FetchResult(
                success=False,
                error=f"Failed to download database: {db_name}",
                source=self.PLUGIN_NAME
            )

    def download_all_databases(self, output_dir: Optional[Path] = None,
                               systems: Optional[List[str]] = None) -> dict:
        """Download multiple database files

        Args:
            output_dir: Output directory
            systems: List of system names to download (downloads all if None)

        Returns:
            Dictionary mapping database name to FetchResult
        """
        results = {}

        # Determine which databases to download
        if systems:
            # Filter databases by system names
            databases_to_download = [
                db for db in self.available_databases
                if any(system in db for system in systems)
            ]
        else:
            databases_to_download = self.available_databases

        print(f"\n{'='*70}")
        print(f"Downloading {len(databases_to_download)} database(s)")
        print(f"{'='*70}\n")

        total_size = 0
        downloaded_count = 0
        cached_count = 0
        failed_count = 0

        for idx, db_name in enumerate(databases_to_download, 1):
            # Display file name on its own line
            print(f"[{idx}/{len(databases_to_download)}] {db_name}")

            result = self.download_database(db_name, output_dir)
            results[db_name] = result

            if result.success:
                if result.cached:
                    cached_count += 1
                    size_str = result.data.get('size_str', 'unknown')
                    # Show cached status
                    print(f"  ✓ Cached {size_str}")
                else:
                    downloaded_count += 1
                    # Download progress already shown by download_file (on line 2)
                    pass

                # Add to total size
                if 'size' in result.data:
                    total_size += result.data['size']
            else:
                failed_count += 1
                print(f"  ✗ Failed: {result.error}")

        # Print summary
        print(f"\n{'='*70}")
        print(f"Download Summary:")
        print(f"  Total databases: {len(databases_to_download)}")
        print(f"  Downloaded: {downloaded_count}")
        print(f"  Cached: {cached_count}")
        if failed_count > 0:
            print(f"  Failed: {failed_count}")

        # Show total size
        from ..core.utils import format_file_size
        print(f"  Total size: {format_file_size(total_size)}")
        print(f"{'='*70}\n")

        return results

    def search_game(self, query: str, system: Optional[str] = None, **kwargs) -> FetchResult:
        """Search for a game in RetroArch databases

        Note: This requires databases to be downloaded first and converted to JSON format

        Args:
            query: Game name to search
            system: System name
            **kwargs: Additional parameters

        Returns:
            FetchResult with search results
        """
        # This is a placeholder - actual search would require parsing RDB files
        # or using converted JSON databases
        return FetchResult(
            success=False,
            error="Direct search not implemented. Use matcher with downloaded databases.",
            source=self.PLUGIN_NAME
        )

    def get_game_info(self, game_id: str, **kwargs) -> FetchResult:
        """Get game information

        Args:
            game_id: Game identifier (CRC32)
            **kwargs: Additional parameters

        Returns:
            FetchResult with game info
        """
        # This is a placeholder - actual lookup would require parsing RDB files
        return FetchResult(
            success=False,
            error="Direct lookup not implemented. Use matcher with downloaded databases.",
            source=self.PLUGIN_NAME
        )

    def list_available_databases(self) -> List[str]:
        """Get list of available databases

        Returns:
            List of database names
        """
        return self.available_databases.copy()

    def get_database_url(self, db_name: str) -> str:
        """Get download URL for a database

        Args:
            db_name: Database filename

        Returns:
            Full download URL
        """
        encoded_name = urllib.parse.quote(db_name)
        return f"{self.base_url}/{encoded_name}"
