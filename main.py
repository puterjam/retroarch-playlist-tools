#!/usr/bin/env python3
"""
RetroArch Toolkit - Main CLI Interface
A tool for managing RetroArch playlists and ROM collections
"""

import argparse
import json
import sys
from pathlib import Path

from toolkit.config import Config
from toolkit.core import ROMScanner, ROMMatcher, PlaylistGenerator, BaseFetcher


def cmd_init(args):
    """Initialize RetroArch configuration"""
    config = Config()

    retroarch_path = args.path

    if not retroarch_path:
        retroarch_path = input("Enter RetroArch installation path (local working directory): ").strip()

    if not retroarch_path:
        print("Error: RetroArch path is required")
        return 1

    # Ask for runtime path
    runtime_roms_path = args.runtime_path
    if not runtime_roms_path and not args.no_runtime:
        print("\nOptional: Enter runtime ROMs path for playlists")
        print("(Leave empty to use the same as local path)")
        print("Example for Switch: /retroarch/roms")
        runtime_roms_path = input("Runtime ROMs path: ").strip()

    if config.init_retroarch_path(retroarch_path, runtime_roms_path or None):
        print(f"\nRetroArch Toolkit initialized successfully!")
        print(f"RetroArch path: {config.get('retroarch_path')}")
        print(f"ROMs path (local): {config.get('roms_path')}")
        if config.get('roms_path_runtime') != config.get('roms_path'):
            print(f"ROMs path (runtime): {config.get('roms_path_runtime')}")
        print(f"Playlists path: {config.get('playlists_path')}")
        print(f"Thumbnails path: {config.get('thumbnails_path')}")
        print(f"\nConfiguration saved to: {config.config_path}")
        return 0
    else:
        print("Error: Failed to initialize RetroArch configuration")
        return 1


def cmd_scan(args):
    """Scan ROM directory and match against database"""
    config = Config()

    if not config.is_initialized():
        print("Error: RetroArch Toolkit not initialized. Run 'init' command first.")
        return 1

    scanner = ROMScanner(config)

    # Progress callback
    def show_progress(current, total, rom_info):
        if rom_info:
            print(f"[{current}/{total}] Found: {rom_info.filename} ({rom_info.system})")

    # Scan path
    scan_path = args.path if args.path else None
    calculate_crc = not args.no_crc

    print("\n" + "=" * 60)
    print("STEP 1: Scanning ROMs")
    print("=" * 60)

    # Scan ROMs
    roms = scanner.scan(
        path=scan_path,
        recursive=args.recursive,
        calculate_crc=calculate_crc,
        progress_callback=show_progress if args.verbose else None
    )

    if not roms:
        print("No ROMs found!")
        return 1

    print("\n" + "=" * 60)
    print("STEP 2: Matching ROMs to Database")
    print("=" * 60)

    # Match ROMs to database
    matcher = ROMMatcher(config)
    matched, total = matcher.match_all_roms(roms)

    # Check for missing databases
    if matcher.has_missing_databases():
        missing = matcher.get_missing_databases()
        print("\n⚠️  WARNING: Missing databases for systems:")
        for system in missing:
            print(f"  - {system}")
        print("\nRun 'download-db' command to download missing databases:")
        print("  python main.py download-db")

    # Save unmatched ROMs to unknown_games.json
    unmatched = scanner.get_unmatched_roms()
    if unmatched:
        scanner.save_unmatched_roms(unmatched)
        print(f"\n💡 Use 'match' command to interactively fix {len(unmatched)} unmatched ROM(s)")

    # Print summary
    scanner.print_summary()

    # Export results if requested
    if args.output:
        scanner.export_scan_results(args.output)

    return 0


def cmd_match(args):
    """Interactively match unmatched ROMs from unknown_games.json"""
    config = Config()

    if not config.is_initialized():
        print("Error: RetroArch Toolkit not initialized. Run 'init' command first.")
        return 1

    # Load unknown games
    unknown_db_path = Path(config.get("unknown_games_db"))
    if not unknown_db_path.exists():
        print("No unknown games found. Run 'scan' command first.")
        return 1

    with open(unknown_db_path, 'r', encoding='utf-8') as f:
        unknown_games = json.load(f)

    if not unknown_games:
        print("No unmatched games to fix.")
        return 0

    # Load manual matches to avoid duplicates
    manual_matches_path = Path(config.get("manual_matches_db", "manual_matches.json"))
    already_matched = set()
    if manual_matches_path.exists():
        with open(manual_matches_path, 'r', encoding='utf-8') as f:
            already_matched = set(json.load(f).keys())

    # Create matcher
    matcher = ROMMatcher(config)

    print(f"\nFound {len(unknown_games)} unmatched ROM(s)")
    print(f"Already fixed: {len(already_matched)} ROM(s)")

    # Filter out already matched ROMs
    remaining_games = {k: v for k, v in unknown_games.items() if k not in already_matched}

    if not remaining_games:
        print("\nAll unknown games have already been fixed!")
        return 0

    print(f"Remaining to fix: {len(remaining_games)} ROM(s)\n")

    # Start interactive matching shell
    from toolkit.core.interactive_matcher import InteractiveMatcher

    interactive_matcher = InteractiveMatcher(config, matcher, remaining_games, manual_matches_path)
    return interactive_matcher.run()


def cmd_playlist(args):
    """Generate RetroArch playlists"""
    config = Config()

    if not config.is_initialized():
        print("Error: RetroArch Toolkit not initialized. Run 'init' command first.")
        return 1

    # Scan and match ROMs
    scanner = ROMScanner(config)
    print("Scanning ROMs...")
    roms = scanner.scan(calculate_crc=True)

    if not roms:
        print("No ROMs found")
        return 1

    # Match ROMs if requested
    if not args.no_match:
        print("\nMatching ROMs to database...")
        matcher = ROMMatcher(config)
        matcher.match_all_roms(roms)

    # Generate playlists
    print("\nGenerating playlists...")
    generator = PlaylistGenerator(config)
    playlists = generator.generate_playlists(roms, group_by_system=not args.single)

    print(f"\nGenerated {len(playlists)} playlist(s):")
    for name, path in playlists.items():
        print(f"  - {name}: {path}")

    return 0


def cmd_download_db(args):
    """Download RetroArch databases"""
    config = Config()

    fetcher = BaseFetcher(config)
    db_fetcher = fetcher.get_plugin("retroarch_db")

    if not db_fetcher:
        print("Error: RetroArch DB fetcher not available")
        return 1

    output_dir = Path(args.output) if args.output else Path(config.get("database_path"))

    if args.list:
        # List available databases
        databases = db_fetcher.list_available_databases()
        print("Available databases:")
        for db in databases:
            print(f"  - {db}")
        return 0

    # Download databases
    systems = args.systems if args.systems else None
    results = db_fetcher.download_all_databases(output_dir=output_dir, systems=systems)

    # Summary
    successful = sum(1 for r in results.values() if r.success)
    print(f"\nDownloaded {successful}/{len(results)} database(s)")

    return 0


def cmd_download_thumbnails(args):
    """Download game thumbnails for LaunchBox matched games only"""
    config = Config()

    if not config.is_initialized():
        print("Error: RetroArch Toolkit not initialized. Run 'init' command first.")
        return 1

    # Load manual matches to find LaunchBox matched games
    manual_matches_path = Path(config.get("manual_matches_db", "manual_matches.json"))
    if not manual_matches_path.exists():
        print("No manual matches found. Run 'match' command first.")
        return 1

    with open(manual_matches_path, 'r', encoding='utf-8') as f:
        manual_matches = json.load(f)

    # Filter only LaunchBox matched games
    launchbox_games = {
        crc: match for crc, match in manual_matches.items()
        if match.get('source') == 'launchbox' and match.get('launchbox_id')
    }

    if not launchbox_games:
        print("No LaunchBox matched games found.")
        print("Use the 'match' command with online search to match games with LaunchBox.")
        return 0

    print(f"Found {len(launchbox_games)} LaunchBox matched game(s)")

    # Initialize LaunchBox fetcher
    fetcher = BaseFetcher(config)
    launchbox = fetcher.get_plugin("launchbox")

    if not launchbox:
        print("Error: LaunchBox fetcher not available")
        return 1

    output_dir = Path(config.get("thumbnails_path"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download thumbnails for each LaunchBox game
    success_count = 0
    failed_count = 0
    total_images = 0

    # Image types to download (RetroArch standard types)
    image_types = ["box_front", "screenshot_title", "screenshot_gameplay"]

    for crc, match in launchbox_games.items():
        game_id = match.get('launchbox_id')
        filename = match.get('filename', 'Unknown')
        system = match.get('system', 'Unknown')

        # Extract ROM filename without extension
        rom_name = Path(filename).stem

        print(f"\nDownloading images for: {rom_name}")
        print(f"  System: {system}")
        print(f"  LaunchBox ID: {game_id}")

        # Create system-specific output directory
        system_output_dir = output_dir / system
        system_output_dir.mkdir(parents=True, exist_ok=True)

        # Download all image types (using ROM filename)
        result = launchbox.download_game_images(
            game_id=game_id,
            rom_filename=rom_name,
            image_types=image_types,
            output_dir=system_output_dir,
            prefer_region="North America"
        )

        if result.success:
            paths = result.data.get('paths', {})
            count = result.data.get('count', 0)
            total_images += count

            print(f"  ✓ Downloaded {count} image(s):")
            if 'box_front' in paths:
                print(f"    - Named_Boxarts/{rom_name}.png")
            if 'screenshot_title' in paths:
                print(f"    - Named_Titles/{rom_name}.png")
            if 'screenshot_gameplay' in paths:
                print(f"    - Named_Snaps/{rom_name}.png")

            success_count += 1
        else:
            print(f"  ✗ Failed: {result.error}")
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"Thumbnail Download Summary")
    print(f"{'='*60}")
    print(f"Games processed: {len(launchbox_games)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Total images downloaded: {total_images}")

    return 0




def cmd_config(args):
    """Manage configuration"""
    config = Config()

    if args.show:
        # Show current configuration
        print("Current configuration:")
        print(f"  RetroArch path: {config.get('retroarch_path')}")
        print(f"  ROMs path: {config.get('roms_path')}")
        print(f"  Playlists path: {config.get('playlists_path')}")
        print(f"  Thumbnails path: {config.get('thumbnails_path')}")
        print(f"  Database path: {config.get('database_path')}")
        print(f"\n  Config file: {config.config_path}")

    elif args.set:
        # Set configuration value
        key, value = args.set.split('=', 1)
        config.set(key, value)
        config.save()
        print(f"Set {key} = {value}")

    elif args.validate:
        # Validate configuration
        errors = config.validate()
        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return 1
        else:
            print("Configuration is valid")

    return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="RetroArch Toolkit - Manage playlists and ROM collections",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Init command
    parser_init = subparsers.add_parser('init', help='Initialize RetroArch configuration')
    parser_init.add_argument('path', nargs='?', help='RetroArch installation path (local working directory)')
    parser_init.add_argument('-r', '--runtime-path', help='Runtime ROMs path for playlists (e.g., Switch mount point)')
    parser_init.add_argument('--no-runtime', action='store_true', help='Skip runtime path configuration')

    # Scan command
    parser_scan = subparsers.add_parser('scan', help='Scan ROM directory and match against database')
    parser_scan.add_argument('-p', '--path', help='Path to scan (uses config roms_path if not specified)')
    parser_scan.add_argument('-r', '--recursive', action='store_true', default=True, help='Scan subdirectories')
    parser_scan.add_argument('--no-crc', action='store_true', help='Skip CRC32 calculation')
    parser_scan.add_argument('-o', '--output', help='Export scan results to JSON file')
    parser_scan.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    # Match command (interactive shell)
    parser_match = subparsers.add_parser('match', help='Interactively match unmatched ROMs from unknown_games.json')

    # Playlist command
    parser_playlist = subparsers.add_parser('playlist', help='Generate RetroArch playlists')
    parser_playlist.add_argument('--no-match', action='store_true', help='Skip database matching')
    parser_playlist.add_argument('--single', action='store_true', help='Create single playlist for all ROMs')

    # Download DB command
    parser_db = subparsers.add_parser('download-db', help='Download RetroArch databases')
    parser_db.add_argument('-l', '--list', action='store_true', help='List available databases')
    parser_db.add_argument('-s', '--systems', nargs='+', help='Systems to download (downloads all if not specified)')
    parser_db.add_argument('-o', '--output', help='Output directory')

    # Download thumbnails command
    parser_thumbnails = subparsers.add_parser('download-thumbnails', help='Download game thumbnails')

    # Config command
    parser_config = subparsers.add_parser('config', help='Manage configuration')
    parser_config.add_argument('--show', action='store_true', help='Show current configuration')
    parser_config.add_argument('--set', help='Set configuration value (format: key=value)')
    parser_config.add_argument('--validate', action='store_true', help='Validate configuration')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Execute command
    commands = {
        'init': cmd_init,
        'scan': cmd_scan,
        'match': cmd_match,
        'playlist': cmd_playlist,
        'download-db': cmd_download_db,
        'download-thumbnails': cmd_download_thumbnails,
        'config': cmd_config,
    }

    command_func = commands.get(args.command)
    if command_func:
        try:
            return command_func(args)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user")
            return 130
        except Exception as e:
            print(f"Error: {e}")
            if args.command in ['scan', 'match'] and hasattr(args, 'verbose') and args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
