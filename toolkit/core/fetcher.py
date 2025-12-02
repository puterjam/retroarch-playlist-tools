"""
Base Fetcher Module
Provides base class and plugin system for fetch modules
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path
import urllib.request
import urllib.error
import time


@dataclass
class FetchResult:
    """Result from a fetch operation"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    source: str = ""
    cached: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class FetchPlugin(ABC):
    """Base class for fetch plugins

    All fetch plugins must inherit from this class and implement the required methods.
    This allows for extensible search plugins that can fetch data from various sources.
    """

    def __init__(self, config: Dict, cache_dir: Optional[Path] = None):
        """Initialize plugin

        Args:
            config: Plugin configuration
            cache_dir: Cache directory for storing downloaded data
        """
        self.config = config
        self.cache_dir = cache_dir or Path.home() / ".cache" / "retroarch_toolkit"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = config.get("enabled", True)

    @abstractmethod
    def get_name(self) -> str:
        """Get plugin name

        Returns:
            Plugin name
        """
        pass

    @abstractmethod
    def search_game(self, query: str, system: Optional[str] = None, **kwargs) -> FetchResult:
        """Search for a game

        Args:
            query: Search query (game name)
            system: System/platform name
            **kwargs: Additional search parameters

        Returns:
            FetchResult with search results
        """
        pass

    @abstractmethod
    def get_game_info(self, game_id: str, **kwargs) -> FetchResult:
        """Get detailed game information

        Args:
            game_id: Game identifier
            **kwargs: Additional parameters

        Returns:
            FetchResult with game information
        """
        pass

    def download_file(self, url: str, output_path: Path, retry: int = 3,
                     show_progress: bool = True) -> bool:
        """Download a file from URL with progress display

        Args:
            url: URL to download
            output_path: Where to save the file
            retry: Number of retry attempts
            show_progress: Show download progress

        Returns:
            True if successful
        """
        # Spinner animation frames
        spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

        for attempt in range(retry):
            try:
                # Create parent directory if needed
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Download file with progress
                with urllib.request.urlopen(url, timeout=30) as response:
                    # Get file size from headers
                    file_size = response.headers.get('Content-Length')
                    if file_size:
                        file_size = int(file_size)
                    else:
                        file_size = None

                    # Read data in chunks
                    chunk_size = 8192
                    downloaded = 0
                    data_chunks = []
                    spinner_idx = 0

                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        data_chunks.append(chunk)
                        downloaded += len(chunk)

                        # Update progress with spinner
                        if show_progress:
                            if file_size:
                                progress = (downloaded / file_size) * 100
                                spinner = spinner_frames[spinner_idx % len(spinner_frames)]
                                print(f"\r  {spinner} ({progress:5.1f}%) {self._format_size(downloaded)}/{self._format_size(file_size)}",
                                      end='', flush=True)
                            else:
                                spinner = spinner_frames[spinner_idx % len(spinner_frames)]
                                print(f"\r  {spinner} Downloading... {self._format_size(downloaded)}",
                                      end='', flush=True)
                            spinner_idx += 1

                    # Save to file
                    with open(output_path, 'wb') as f:
                        for chunk in data_chunks:
                            f.write(chunk)

                    # Show completion
                    final_size = output_path.stat().st_size
                    if show_progress:
                        print(f"\r  ✓ (100.0%) {self._format_size(final_size)}/{self._format_size(final_size)}", flush=True)

                return True

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # File not found, no need to retry
                    if show_progress:
                        print(f"\r  ✗ File not found (404)", flush=True)
                    return False
                if show_progress:
                    print(f"\r  ✗ HTTP Error {e.code}", flush=True)
            except Exception as e:
                if show_progress:
                    print(f"\r  ✗ Error: {str(e)[:50]}", flush=True)

            if attempt < retry - 1:
                if show_progress:
                    print(f"  Retrying... (attempt {attempt + 2}/{retry})")
                time.sleep(1)  # Wait before retry

        return False

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., '1.5 MB')
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def get_cached_file(self, cache_key: str) -> Optional[Path]:
        """Get cached file if it exists

        Args:
            cache_key: Cache key (relative path in cache directory)

        Returns:
            Path to cached file or None if not found
        """
        cache_path = self.cache_dir / cache_key
        if cache_path.exists():
            return cache_path
        return None

    def is_enabled(self) -> bool:
        """Check if plugin is enabled

        Returns:
            True if enabled
        """
        return self.enabled


class BaseFetcher:
    """Base fetcher class that manages multiple fetch plugins"""

    def __init__(self, config):
        """Initialize fetcher

        Args:
            config: Config instance
        """
        self.config = config
        self.plugins: Dict[str, FetchPlugin] = {}
        self._load_plugins()

    def _load_plugins(self):
        """Load and initialize fetch plugins"""
        # Import plugin classes
        from ..plugins.retroarch_db import RetroArchDBFetcher
        from ..plugins.libretro_thumbnails import LibretroThumbnailsFetcher
        from ..plugins.launchbox import LaunchBoxFetcher

        # Initialize plugins
        plugin_classes = [
            RetroArchDBFetcher,
            LibretroThumbnailsFetcher,
            LaunchBoxFetcher
        ]

        for plugin_class in plugin_classes:
            try:
                # Get plugin config
                plugin_name = plugin_class.PLUGIN_NAME
                plugin_config = self.config.get(f"fetch_sources.{plugin_name}", {})

                # Initialize plugin
                plugin = plugin_class(plugin_config)

                if plugin.is_enabled():
                    self.plugins[plugin_name] = plugin
                    print(f"Loaded fetch plugin: {plugin_name}")

            except Exception as e:
                print(f"Error loading plugin {plugin_class.__name__}: {e}")

    def get_plugin(self, plugin_name: str) -> Optional[FetchPlugin]:
        """Get a specific plugin

        Args:
            plugin_name: Plugin name

        Returns:
            Plugin instance or None
        """
        return self.plugins.get(plugin_name)

    def search_all(self, query: str, system: Optional[str] = None) -> Dict[str, FetchResult]:
        """Search across all enabled plugins

        Args:
            query: Search query
            system: Optional system filter

        Returns:
            Dictionary mapping plugin name to FetchResult
        """
        results = {}

        for plugin_name, plugin in self.plugins.items():
            try:
                result = plugin.search_game(query, system)
                results[plugin_name] = result
            except Exception as e:
                results[plugin_name] = FetchResult(
                    success=False,
                    error=str(e),
                    source=plugin_name
                )

        return results

    def get_game_info_all(self, game_id: str) -> Dict[str, FetchResult]:
        """Get game info from all enabled plugins

        Args:
            game_id: Game identifier

        Returns:
            Dictionary mapping plugin name to FetchResult
        """
        results = {}

        for plugin_name, plugin in self.plugins.items():
            try:
                result = plugin.get_game_info(game_id)
                results[plugin_name] = result
            except Exception as e:
                results[plugin_name] = FetchResult(
                    success=False,
                    error=str(e),
                    source=plugin_name
                )

        return results

    def list_plugins(self) -> List[str]:
        """Get list of loaded plugin names

        Returns:
            List of plugin names
        """
        return list(self.plugins.keys())

    def register_plugin(self, plugin: FetchPlugin) -> bool:
        """Register a custom plugin

        Args:
            plugin: Plugin instance

        Returns:
            True if registered successfully
        """
        try:
            plugin_name = plugin.get_name()
            self.plugins[plugin_name] = plugin
            print(f"Registered custom plugin: {plugin_name}")
            return True
        except Exception as e:
            print(f"Error registering plugin: {e}")
            return False
