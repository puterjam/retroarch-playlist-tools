"""
RetroArch Toolkit Configuration Module
Handles configuration loading, saving, and validation
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class Config:
    """Configuration manager for RetroArch Toolkit"""

    @staticmethod
    def _load_system_defaults() -> dict:
        """Load default system configurations from external file

        Returns:
            Dictionary with cores, fetch_sources, and scan_options
        """
        # Try to load from cores config file
        config_file = Path(__file__).parent.parent / "config" / "cores.json"

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load cores config: {e}")

        # Fallback to minimal default
        return {
            "cores": {
                "Nintendo - Nintendo Entertainment System": {
                    "core_name": "nestopia_libretro",
                    "extensions": [".nes", ".fds", ".unf", ".unif"],
                    "db_name": "Nintendo - Nintendo Entertainment System.rdb"
                },
                "Arcade": {
                    "core_name": "mame_libretro",
                    "extensions": [".zip", ".7z"],
                    "db_name": "MAME.rdb"
                }
            },
            "fetch_sources": {
                "retroarch_db": {
                    "enabled": True,
                    "base_url": "https://github.com/libretro/libretro-database/raw/master/rdb"
                }
            },
            "scan_options": {
                "recursive": True,
                "calculate_crc32": True,
                "match_hack_versions": True,
                "download_thumbnails": True,
                "create_playlists": True,
                "auto_rename": False
            }
        }

    @property
    def DEFAULT_CONFIG(self) -> dict:
        """Get default configuration with system defaults loaded from file"""
        system_defaults = self._load_system_defaults()
        return {
            "retroarch_path": "",
            "roms_path": "",
            "roms_path_runtime": "",  # Runtime path for playlist (e.g., Switch mount point)
            "playlists_path": "",
            "thumbnails_path": "",
            "database_path": "",
            "cores": system_defaults.get("cores", {}),
            "fetch_sources": system_defaults.get("fetch_sources", {}),
            "scan_options": system_defaults.get("scan_options", {}),
            "unknown_games_db": "unknown_games.json",
            "manual_matches_db": "manual_matches.json"
        }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration

        Args:
            config_path: Path to config file. If None, uses default location
        """
        if config_path is None:
            config_dir = Path.home() / ".config" / "retroarch_toolkit"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "config.json"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with default config to ensure all keys exist
                    merged = self._merge_configs(self.DEFAULT_CONFIG.copy(), loaded_config)
                    # Always use cores and fetch_sources from cores.json (don't let user config override)
                    system_defaults = self._load_system_defaults()
                    merged['cores'] = system_defaults.get('cores', {})
                    merged['fetch_sources'] = system_defaults.get('fetch_sources', {})
                    return merged
            except json.JSONDecodeError as e:
                print(f"Error loading config: {e}")
                print("Using default configuration")
                return self.DEFAULT_CONFIG.copy()
        else:
            return self.DEFAULT_CONFIG.copy()

    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """Recursively merge configurations"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._merge_configs(base[key], value)
            else:
                base[key] = value
        return base

    def save(self) -> bool:
        """Save current configuration to file

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def init_retroarch_path(self, retroarch_path: str, runtime_roms_path: Optional[str] = None) -> bool:
        """Initialize RetroArch paths

        Args:
            retroarch_path: Base RetroArch directory (local/working directory)
            runtime_roms_path: Runtime ROMs path for playlist (e.g., Switch mount point)
                              If None, uses same as roms_path

        Returns:
            True if successful, False otherwise
        """
        retroarch_path = Path(retroarch_path).expanduser().resolve()

        if not retroarch_path.exists():
            print(f"Error: RetroArch path does not exist: {retroarch_path}")
            return False

        self.config["retroarch_path"] = str(retroarch_path)

        # Set default paths based on RetroArch structure
        self.config["roms_path"] = str(retroarch_path / "roms")
        self.config["playlists_path"] = str(retroarch_path / "playlists")
        self.config["thumbnails_path"] = str(retroarch_path / "thumbnails")
        self.config["database_path"] = str(retroarch_path / "database" / "rdb")

        # Set runtime ROMs path (for playlist generation)
        if runtime_roms_path:
            self.config["roms_path_runtime"] = runtime_roms_path
        else:
            # If not specified, use same as roms_path
            self.config["roms_path_runtime"] = self.config["roms_path"]

        # Create directories if they don't exist
        for path_key in ["roms_path", "playlists_path", "thumbnails_path", "database_path"]:
            path = Path(self.config[path_key])
            path.mkdir(parents=True, exist_ok=True)

        return self.save()

    def get_runtime_rom_path(self, local_rom_path: str) -> str:
        """Convert local ROM path to runtime path for playlist

        Args:
            local_rom_path: Local ROM file path

        Returns:
            Runtime ROM path for use in playlist
        """
        local_roms_path = self.config.get("roms_path", "")
        runtime_roms_path = self.config.get("roms_path_runtime", "")

        # If runtime path is not configured or same as local, return original
        if not runtime_roms_path or runtime_roms_path == local_roms_path:
            return local_rom_path

        # Replace local roms path with runtime roms path
        try:
            local_path = Path(local_rom_path)
            local_base = Path(local_roms_path)

            # Get relative path from roms directory
            relative_path = local_path.relative_to(local_base)

            # Construct runtime path
            runtime_path = Path(runtime_roms_path) / relative_path

            return str(runtime_path).replace('\\', '/')  # Use forward slashes for cross-platform
        except ValueError:
            # If path is not relative to roms_path, return original
            return local_rom_path

    def get(self, key: str, default=None):
        """Get configuration value

        Args:
            key: Configuration key (supports dot notation, e.g., 'cores.Nintendo')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value) -> None:
        """Set configuration value

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_core_by_extension(self, extension: str) -> Optional[Dict]:
        """Get core configuration by file extension

        Args:
            extension: File extension (e.g., '.nes')

        Returns:
            Core configuration dict or None if not found
        """
        extension = extension.lower()

        # First pass: Try to find systems where this extension is the primary (first) extension
        # This handles cases like .gbc which should match GBC, not GB
        for system_name, core_config in self.config["cores"].items():
            extensions = [ext.lower() for ext in core_config["extensions"]]
            if extensions and extensions[0] == extension:
                return {
                    "system_name": system_name,
                    **core_config
                }

        # Second pass: Fall back to any system that supports this extension
        for system_name, core_config in self.config["cores"].items():
            if extension in [ext.lower() for ext in core_config["extensions"]]:
                return {
                    "system_name": system_name,
                    **core_config
                }

        return None

    def get_all_extensions(self) -> List[str]:
        """Get all supported file extensions

        Returns:
            List of file extensions
        """
        extensions = []
        for core_config in self.config["cores"].values():
            extensions.extend(core_config["extensions"])
        return list(set(extensions))

    def is_initialized(self) -> bool:
        """Check if RetroArch path is configured

        Returns:
            True if initialized, False otherwise
        """
        retroarch_path = self.config.get("retroarch_path", "")
        return bool(retroarch_path and Path(retroarch_path).exists())

    def validate(self) -> List[str]:
        """Validate configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.is_initialized():
            errors.append("RetroArch path not configured. Run 'init' command first.")
            return errors

        # Check if paths exist
        for key in ["roms_path", "playlists_path", "thumbnails_path", "database_path"]:
            path = Path(self.config[key])
            if not path.exists():
                errors.append(f"{key} does not exist: {path}")

        return errors
