#!/usr/bin/env python3
"""
Test download functionality with progress display
"""

import sys
from pathlib import Path

# Add retroarch_toolkit to path
sys.path.insert(0, str(Path(__file__).parent))

from toolkit.config import Config
from toolkit.plugins.retroarch_db import RetroArchDBFetcher


def test_download():
    """Test database download with progress"""
    print("Testing database download with progress display...\n")

    config = Config()

    # Create fetcher
    fetcher = RetroArchDBFetcher({
        "enabled": True,
        "base_url": "https://github.com/libretro/libretro-database/raw/master/rdb"
    })

    # Test downloading a few databases
    test_databases = [
        "Nintendo - Nintendo Entertainment System.rdb",
        "Nintendo - Game Boy.rdb",
    ]

    print(f"Testing download of {len(test_databases)} database(s)...\n")

    for idx, db_name in enumerate(test_databases, 1):
        print(f"[{idx}/{len(test_databases)}] Testing: {db_name}")
        result = fetcher.download_database(db_name)

        if result.success:
            if result.cached:
                size_str = result.data.get('size_str', 'unknown')
                print(f"  ✓ Already cached ({size_str})\n")
            else:
                print(f"  ✓ Download complete\n")
        else:
            print(f"  ✗ Failed: {result.error}\n")

    print("\n" + "="*70)
    print("Test completed!")
    print("="*70)


if __name__ == "__main__":
    try:
        test_download()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
