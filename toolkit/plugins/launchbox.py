"""
LaunchBox Games DB Fetcher
Fetches game information from LaunchBox Games Database
"""

import urllib.request
import urllib.parse
import json
from pathlib import Path
from typing import Optional, List, Dict

from ..core.fetcher import FetchPlugin, FetchResult


class LaunchBoxFetcher(FetchPlugin):
    """Fetcher for LaunchBox Games Database"""

    PLUGIN_NAME = "launchbox"

    # Platform ID mappings (LaunchBox platform IDs)
    PLATFORM_MAPPINGS = {
        "Nintendo - Nintendo Entertainment System": "Nintendo Entertainment System",
        "Nintendo - Super Nintendo Entertainment System": "Super Nintendo Entertainment System",
        "Nintendo - Game Boy": "Nintendo Game Boy",
        "Nintendo - Game Boy Color": "Nintendo Game Boy Color",
        "Nintendo - Game Boy Advance": "Nintendo Game Boy Advance",
        "Nintendo - Nintendo 64": "Nintendo 64",
        "Sega - Master System - Mark III": "Sega Master System",
        "Sega - Mega Drive - Genesis": "Sega Genesis",
        "Sega - Game Gear": "Sega Game Gear",
        "Sony - PlayStation": "Sony Playstation",
        "Arcade": "Arcade",
    }

    def __init__(self, config: dict):
        """Initialize LaunchBox fetcher

        Args:
            config: Plugin configuration
        """
        super().__init__(config)
        self.base_url = config.get("base_url", "https://gamesdb.launchbox-app.com")
        self.api_key = config.get("api_key", "")

    def get_name(self) -> str:
        """Get plugin name"""
        return self.PLUGIN_NAME

    def search_game(self, query: str, system: Optional[str] = None, **kwargs) -> FetchResult:
        """Search for a game

        Args:
            query: Game name to search
            system: System/platform name
            **kwargs: Additional parameters

        Returns:
            FetchResult with search results
        """
        # Map RetroArch system name to LaunchBox platform name
        platform = None
        if system:
            platform = self.PLATFORM_MAPPINGS.get(system)

        try:
            # Construct API URL
            # LaunchBox API endpoint: /api/v1/games/search
            params = {
                "name": query,
            }

            if platform:
                params["platform"] = platform

            # Note: LaunchBox API may require authentication
            # This is a simplified implementation
            url = f"{self.base_url}/api/v1/games/search"
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"

            # Add API key if available
            if self.api_key:
                full_url += f"&apikey={self.api_key}"

            # Make request
            request = urllib.request.Request(full_url)
            request.add_header('User-Agent', 'RetroArch-Toolkit/1.0')

            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            return FetchResult(
                success=True,
                data=data,
                source=self.PLUGIN_NAME
            )

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return FetchResult(
                    success=False,
                    error=f"Game not found: {query}",
                    source=self.PLUGIN_NAME
                )
            else:
                return FetchResult(
                    success=False,
                    error=f"HTTP Error {e.code}: {e.reason}",
                    source=self.PLUGIN_NAME
                )
        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                source=self.PLUGIN_NAME
            )

    def get_game_info(self, game_id: str, **kwargs) -> FetchResult:
        """Get detailed game information

        Args:
            game_id: LaunchBox game ID
            **kwargs: Additional parameters

        Returns:
            FetchResult with game information
        """
        try:
            # Construct API URL
            url = f"{self.base_url}/api/v1/games/{game_id}"

            if self.api_key:
                url += f"?apikey={self.api_key}"

            # Make request
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'RetroArch-Toolkit/1.0')

            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            return FetchResult(
                success=True,
                data=data,
                source=self.PLUGIN_NAME
            )

        except urllib.error.HTTPError as e:
            return FetchResult(
                success=False,
                error=f"HTTP Error {e.code}: {e.reason}",
                source=self.PLUGIN_NAME
            )
        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                source=self.PLUGIN_NAME
            )

    def download_game_image(self, game_id: str, image_type: str = "box-front",
                           output_dir: Optional[Path] = None) -> FetchResult:
        """Download game image

        Args:
            game_id: LaunchBox game ID
            image_type: Type of image (box-front, screenshot, etc.)
            output_dir: Output directory

        Returns:
            FetchResult with download status
        """
        if output_dir is None:
            output_dir = self.cache_dir / "launchbox" / "images"

        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Get game info to find image URL
            game_info = self.get_game_info(game_id)

            if not game_info.success:
                return game_info

            # Extract image URL from game data
            # This is simplified - actual API structure may differ
            images = game_info.data.get("images", [])
            image_url = None

            for img in images:
                if img.get("type") == image_type:
                    image_url = img.get("url")
                    break

            if not image_url:
                return FetchResult(
                    success=False,
                    error=f"No {image_type} image found for game {game_id}",
                    source=self.PLUGIN_NAME
                )

            # Download image
            output_path = output_dir / f"{game_id}_{image_type}.jpg"

            if self.download_file(image_url, output_path):
                return FetchResult(
                    success=True,
                    data={"path": str(output_path)},
                    source=self.PLUGIN_NAME
                )
            else:
                return FetchResult(
                    success=False,
                    error=f"Failed to download image",
                    source=self.PLUGIN_NAME
                )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                source=self.PLUGIN_NAME
            )

    def get_platform_list(self) -> List[str]:
        """Get list of supported platforms

        Returns:
            List of platform names
        """
        return list(self.PLATFORM_MAPPINGS.values())

    def map_system_to_platform(self, system: str) -> Optional[str]:
        """Map RetroArch system name to LaunchBox platform name

        Args:
            system: RetroArch system name

        Returns:
            LaunchBox platform name or None
        """
        return self.PLATFORM_MAPPINGS.get(system)
