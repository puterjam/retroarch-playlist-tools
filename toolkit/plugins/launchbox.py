"""
LaunchBox Games DB Fetcher
Fetches game information from LaunchBox Games Database API
"""

import urllib.request
import urllib.parse
import json
from pathlib import Path
from typing import Optional, List

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
        """Search for a game using LaunchBox JSON API

        Args:
            query: Game name to search
            system: System/platform name (optional filter)
            **kwargs: Additional parameters

        Returns:
            FetchResult with search results
        """
        try:
            # URL encode the query
            encoded_query = urllib.parse.quote(query)

            # Construct API search URL
            api_url = f"https://api.gamesdb.launchbox-app.com/api/search/{encoded_query}"

            # Make request
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', 'Retroarch-Playlist-Tools/1.0')
            request.add_header('Accept', 'application/json')

            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))

            # Extract games from response
            # Response format: {"count": N, "data": [...]}
            games = []
            if data.get('data'):
                for item in data['data']:
                    game = {
                        'id': str(item.get('gameKey', '')),
                        'name': item.get('name', ''),
                        'platform': item.get('platformName', 'N/A'),
                        'releaseyear': 'N/A',  # API doesn't provide year in search results
                        'thumb': item.get('thumbName', '')
                    }
                    games.append(game)

            # If platform filter is provided, filter results
            if system and games:
                platform = self.PLATFORM_MAPPINGS.get(system)
                if platform:
                    games = [g for g in games if platform.lower() in g.get('platform', '').lower()]

            return FetchResult(
                success=True,
                data=games,
                source=self.PLUGIN_NAME
            )

        except urllib.error.HTTPError as e:
            return FetchResult(
                success=False,
                error=f"HTTP Error {e.code}: {e.reason}",
                source=self.PLUGIN_NAME
            )
        except json.JSONDecodeError as e:
            return FetchResult(
                success=False,
                error=f"JSON decode error: {e}",
                source=self.PLUGIN_NAME
            )
        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                source=self.PLUGIN_NAME
            )

    def get_game_info(self, game_id: str, retries: int = 3, use_cache: bool = True) -> FetchResult:
        """Get detailed game information and images from game details page

        Args:
            game_id: LaunchBox game ID
            retries: Number of retry attempts
            use_cache: Use cached HTML if available

        Returns:
            FetchResult with game information including image URLs
        """
        import time
        import hashlib

        # Setup cache directory
        cache_dir = self.cache_dir / "launchbox" / "html_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache file based on game_id
        cache_file = cache_dir / f"{game_id}.html"

        # Check cache first
        if use_cache and cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Parse images from cached HTML
                images = self._parse_game_images(html_content)

                return FetchResult(
                    success=True,
                    data={
                        "game_id": game_id,
                        "images": images
                    },
                    source=self.PLUGIN_NAME
                )
            except Exception as e:
                # Cache corrupted, continue to fetch
                pass

        last_error = None

        for attempt in range(retries):
            try:
                # Construct details page URL
                url = f"{self.base_url}/games/details/{game_id}"

                # Make request to get HTML page
                request = urllib.request.Request(url)
                request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
                request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
                request.add_header('Accept-Language', 'en-US,en;q=0.9')

                with urllib.request.urlopen(request, timeout=30) as response:
                    html_content = response.read().decode('utf-8')

                # Cache the HTML content
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                except Exception:
                    pass  # Cache write failure is not critical

                # Parse images from HTML
                images = self._parse_game_images(html_content)

                return FetchResult(
                    success=True,
                    data={
                        "game_id": game_id,
                        "images": images
                    },
                    source=self.PLUGIN_NAME
                )

            except urllib.error.HTTPError as e:
                last_error = f"HTTP Error {e.code}: {e.reason}"
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                    continue

            except Exception as e:
                last_error = str(e)
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                    continue

        return FetchResult(
            success=False,
            error=last_error or "Unknown error",
            source=self.PLUGIN_NAME
        )

    def _parse_game_images(self, html_content: str) -> dict:
        """Parse game images from HTML content

        Args:
            html_content: HTML content of game details page

        Returns:
            Dictionary with image types and their URLs
        """
        import re

        images = {
            "box_front": [],
            "screenshot_title": [],
            "screenshot_gameplay": []
        }

        # Find all img tags with src and alt attributes
        img_pattern = r'<img[^>]+src="([^"]+)"[^>]+alt="([^"]+)"[^>]*>'

        for match in re.finditer(img_pattern, html_content):
            img_url = match.group(1)
            alt_text = match.group(2)

            # Only process images from LaunchBox CDN
            if "images.launchbox-app.com" not in img_url and "gamesdb-images.launchbox.gg" not in img_url:
                continue

            # Extract region from alt text (text in parentheses before dimensions)
            region_match = re.search(r'\(([^)]+)\)\s*-\s*\d+x\d+', alt_text)
            region = region_match.group(1) if region_match else "Unknown"

            # Extract filename from URL
            img_filename = img_url.split('/')[-1]

            # Categorize by checking keywords in alt text
            image_entry = {
                "url": img_url,
                "filename": img_filename,
                "region": region,
                "alt": alt_text
            }

            # Extract dimensions from alt text (e.g., "320x224")
            dims_match = re.search(r'(\d+)x(\d+)', alt_text)
            if dims_match:
                width = int(dims_match.group(1))
                height = int(dims_match.group(2))
                image_entry["width"] = width
                image_entry["height"] = height

            if "Box - Front" in alt_text:
                # Priority: Box - Front - Reconstructed > Box - Front
                image_entry["priority"] = 1 if "Reconstructed" in alt_text else 2
                images["box_front"].append(image_entry)
            elif "Screenshot - Game Title" in alt_text:
                images["screenshot_title"].append(image_entry)
            elif "Screenshot - Gameplay" in alt_text:
                images["screenshot_gameplay"].append(image_entry)

        return images

    def download_game_images(self, game_id: str, rom_filename: str = "",
                            image_types: Optional[List[str]] = None,
                            output_dir: Optional[Path] = None,
                            prefer_region: str = "North America") -> FetchResult:
        """Download game images from LaunchBox details page in RetroArch format

        Args:
            game_id: LaunchBox game ID
            rom_filename: ROM filename (without extension) for naming thumbnails
            image_types: List of image types to download (box_front, clear_logo, screenshot_title, screenshot_gameplay)
                        If None, downloads all types
            output_dir: Base output directory (system directory)
            prefer_region: Preferred region for images (default: "North America")

        Returns:
            FetchResult with download status and paths
        """
        if output_dir is None:
            output_dir = self.cache_dir / "launchbox" / "images"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Default to all image types if not specified
        if image_types is None:
            image_types = ["box_front", "clear_logo", "screenshot_title", "screenshot_gameplay"]

        try:
            # Use ROM filename for thumbnail naming
            filename_base = rom_filename if rom_filename else str(game_id)

            # Map image types to RetroArch directory names
            type_to_dir = {
                "box_front": "Named_Boxarts",
                "screenshot_title": "Named_Titles",
                "screenshot_gameplay": "Named_Snaps"
            }

            # Check if all images already exist
            all_exist = True
            existing_paths = {}
            for img_type in image_types:
                if img_type == "clear_logo":
                    continue

                dir_name = type_to_dir.get(img_type)
                if dir_name:
                    type_dir = output_dir / dir_name
                    output_path = type_dir / f"{filename_base}.png"
                    if output_path.exists():
                        existing_paths[img_type] = str(output_path)
                    else:
                        all_exist = False

            # If all images exist, skip fetching game info
            if all_exist and existing_paths:
                print(f"  ⊙ All images already exist, skipping download")
                return FetchResult(
                    success=True,
                    data={"paths": existing_paths, "count": len(existing_paths)},
                    source=self.PLUGIN_NAME
                )

            # Get game info with images (will use cache if available)
            game_info = self.get_game_info(game_id)

            if not game_info.success:
                return game_info

            images_data = game_info.data.get("images", {})
            downloaded_paths = {}

            # Download each requested image type
            for img_type in image_types:
                # Skip clear_logo as it's not part of standard RetroArch structure
                if img_type == "clear_logo":
                    continue

                images_list = images_data.get(img_type, [])

                if not images_list:
                    print(f"  ⚠️  No {img_type} images found")
                    continue

                print(f"  Found {len(images_list)} {img_type} image(s)")

                # Filter and sort images based on type
                if img_type == "box_front":
                    # Sort by priority (Reconstructed first) and prefer region
                    filtered_images = images_list
                    # Sort: priority 1 (Reconstructed) first, then by matching region
                    filtered_images.sort(key=lambda x: (
                        x.get("priority", 999),
                        0 if prefer_region in x.get("region", "") else 1
                    ))
                elif img_type in ["screenshot_title", "screenshot_gameplay"]:
                    # Filter screenshots: width <= 1000
                    filtered_images = [
                        img for img in images_list
                        if img.get("width", 0) <= 1000
                    ]
                    if not filtered_images:
                        print(f"  ⚠️  No {img_type} images with width <= 1000")
                        continue
                    # Prefer matching region
                    filtered_images.sort(key=lambda x: 0 if prefer_region in x.get("region", "") else 1)
                else:
                    filtered_images = images_list

                selected_image = filtered_images[0] if filtered_images else None

                if selected_image:
                    image_url = selected_image["url"]

                    # Get RetroArch directory name for this image type
                    dir_name = type_to_dir.get(img_type)
                    if not dir_name:
                        continue

                    # Create subdirectory for image type
                    type_dir = output_dir / dir_name
                    type_dir.mkdir(parents=True, exist_ok=True)

                    # RetroArch thumbnails are always PNG
                    output_path = type_dir / f"{filename_base}.png"

                    # Skip if already downloaded
                    if output_path.exists():
                        print(f"  ⊙ {img_type} already exists, skipping")
                        downloaded_paths[img_type] = str(output_path)
                        continue

                    print(f"  Downloading {img_type} from {image_url}")

                    # Download and convert to PNG if needed
                    if self._download_and_convert_image(image_url, output_path):
                        downloaded_paths[img_type] = str(output_path)
                        print(f"  ✓ Saved to {output_path}")
                    else:
                        print(f"  ✗ Failed to download {img_type}")

            if downloaded_paths:
                return FetchResult(
                    success=True,
                    data={"paths": downloaded_paths, "count": len(downloaded_paths)},
                    source=self.PLUGIN_NAME
                )
            else:
                return FetchResult(
                    success=False,
                    error=f"No images downloaded for game {game_id}",
                    source=self.PLUGIN_NAME
                )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                source=self.PLUGIN_NAME
            )

    def _download_and_convert_image(self, image_url: str, output_path: Path) -> bool:
        """Download image and convert to PNG if needed

        Args:
            image_url: URL of the image
            output_path: Output path (should end with .png)

        Returns:
            True if successful
        """
        try:
            # Download to temporary location first
            temp_path = output_path.with_suffix('.tmp')

            if not self.download_file(image_url, temp_path):
                return False

            # Check if conversion is needed (JPG to PNG)
            if image_url.lower().endswith(('.jpg', '.jpeg')):
                try:
                    from PIL import Image
                    # Convert JPG to PNG
                    img = Image.open(temp_path)
                    # Convert to RGB if necessary (remove alpha channel)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    img.save(output_path, 'PNG')
                    temp_path.unlink()  # Remove temp file
                    return True
                except ImportError:
                    # PIL not available, just rename the file
                    # RetroArch can handle JPG files even with .png extension
                    temp_path.rename(output_path)
                    return True
            else:
                # Already PNG, just rename
                temp_path.rename(output_path)
                return True

        except Exception as e:
            print(f"  Error converting image: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return False

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
