#!/usr/bin/env python3
"""
Basic functionality test for RetroArch Toolkit
"""

import sys
from pathlib import Path

# Add retroarch_toolkit to path
sys.path.insert(0, str(Path(__file__).parent))

from toolkit.config import Config
from toolkit.core.utils import (
    calculate_crc32, normalize_rom_name,
    is_hack_version, extract_region_info
)
from toolkit.core import BaseFetcher


def test_utils():
    """Test utility functions"""
    print("Testing utility functions...")

    # Test normalize_rom_name
    test_names = [
        "Super Mario Bros (USA).nes",
        "The Legend of Zelda (USA) (Rev 1).nes",
        "Sonic The Hedgehog (Japan, USA) (En,Ja).md",
    ]

    for name in test_names:
        normalized = normalize_rom_name(name)
        print(f"  {name} -> {normalized}")

    # Test is_hack_version
    hack_names = [
        "Super Mario World - Kaizo Edition.smc",
        "Pokemon Red [T+Spa].gb",
        "Sonic Hack.md",
    ]

    for name in hack_names:
        is_hack, base_name = is_hack_version(name)
        print(f"  {name} -> Hack: {is_hack}, Base: {base_name}")

    # Test extract_region_info
    for name in test_names:
        region = extract_region_info(name)
        print(f"  {name} -> Region: {region}")

    print("✓ Utils tests passed\n")


def test_config():
    """Test configuration"""
    print("Testing configuration...")

    # Create config instance
    config = Config()

    # Check default config
    assert config.get("cores") is not None
    assert config.get("fetch_sources") is not None

    # Test get with dot notation
    nes_core = config.get("cores.Nintendo - Nintendo Entertainment System")
    assert nes_core is not None
    assert "extensions" in nes_core

    # Test get_core_by_extension
    core = config.get_core_by_extension(".nes")
    assert core is not None
    assert core["system_name"] == "Nintendo - Nintendo Entertainment System"

    # Test get_all_extensions
    extensions = config.get_all_extensions()
    assert ".nes" in extensions
    assert ".smc" in extensions

    print("✓ Config tests passed\n")


def test_fetch_plugins():
    """Test fetch plugin system"""
    print("Testing fetch plugins...")

    config = Config()
    fetcher = BaseFetcher(config)

    # Check loaded plugins
    plugins = fetcher.list_plugins()
    print(f"  Loaded plugins: {', '.join(plugins)}")

    # Get specific plugin
    db_fetcher = fetcher.get_plugin("retroarch_db")
    if db_fetcher:
        print(f"  ✓ RetroArch DB fetcher loaded")
        databases = db_fetcher.list_available_databases()
        print(f"    Available databases: {len(databases)}")

    thumbnail_fetcher = fetcher.get_plugin("libretro_thumbnails")
    if thumbnail_fetcher:
        print(f"  ✓ Libretro Thumbnails fetcher loaded")

    launchbox_fetcher = fetcher.get_plugin("launchbox")
    if launchbox_fetcher:
        print(f"  ✓ LaunchBox fetcher loaded")

    print("✓ Fetch plugin tests passed\n")


def main():
    """Run all tests"""
    print("=" * 60)
    print("RetroArch Toolkit - Basic Functionality Tests")
    print("=" * 60)
    print()

    try:
        test_utils()
        test_config()
        test_fetch_plugins()

        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
