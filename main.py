#!/usr/bin/env python3
"""
RetroArch Toolkit - Main CLI Interface
A tool for managing RetroArch playlists and ROM collections
"""

import argparse
import sys
from pathlib import Path

from toolkit.config import Config
from toolkit.core import ROMScanner, ROMMatcher, PlaylistGenerator, BaseFetcher


def cmd_init(args):
    """Initialize RetroArch configuration"""
    config = Config()

    retroarch_path = args.path

    if not retroarch_path:
        retroarch_path = input("Enter RetroArch installation path: ").strip()

    if not retroarch_path:
        print("Error: RetroArch path is required")
        return 1

    if config.init_retroarch_path(retroarch_path):
        print(f"\nRetroArch Toolkit initialized successfully!")
        print(f"RetroArch path: {config.get('retroarch_path')}")
        print(f"ROMs path: {config.get('roms_path')}")
        print(f"Playlists path: {config.get('playlists_path')}")
        print(f"Thumbnails path: {config.get('thumbnails_path')}")
        print(f"\nConfiguration saved to: {config.config_path}")
        return 0
    else:
        print("Error: Failed to initialize RetroArch configuration")
        return 1


def cmd_scan(args):
    """Scan ROM directory"""
    config = Config()

    if not config.is_initialized():
        print("Error: RetroArch Toolkit not initialized. Run 'init' command first.")
        return 1

    scanner = ROMScanner(config)

    # Progress callback
    def show_progress(current, total, rom_info):
        if rom_info:
            print(f"[{current}/{total}] Found: {rom_info.filename} ({rom_info.system})")

    # Scan ROMs
    scan_path = args.path if args.path else None
    calculate_crc = not args.no_crc

    roms = scanner.scan(
        path=scan_path,
        recursive=args.recursive,
        calculate_crc=calculate_crc,
        progress_callback=show_progress if args.verbose else None
    )

    # Print summary
    scanner.print_summary()

    # Export results if requested
    if args.output:
        scanner.export_scan_results(args.output)

    return 0


def cmd_match(args):
    """Match ROMs to game database"""
    config = Config()

    if not config.is_initialized():
        print("Error: RetroArch Toolkit not initialized. Run 'init' command first.")
        return 1

    # First scan ROMs
    scanner = ROMScanner(config)
    print("Scanning ROMs...")
    roms = scanner.scan(calculate_crc=True)

    if not roms:
        print("No ROMs found")
        return 1

    # Match ROMs to database
    matcher = ROMMatcher(config)

    matched, total = matcher.match_all_roms(roms)

    # Show unmatched ROMs
    unmatched = matcher.get_unmatched_roms()
    if unmatched and args.verbose:
        print("\nUnmatched ROMs:")
        for rom in unmatched:
            print(f"  - {rom.filename} ({rom.system})")

            if args.similar:
                # Show similar games
                similar = matcher.find_similar_games(rom, limit=3)
                if similar:
                    print("    Similar games:")
                    for game, score in similar:
                        print(f"      {game.get('name', 'Unknown')} ({score:.2%})")

    # Save unknown games
    if unmatched:
        matcher.save_unknown_games()

    return 0


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
    """Download game thumbnails"""
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

    # Match ROMs to get proper names
    print("\nMatching ROMs...")
    matcher = ROMMatcher(config)
    matcher.match_all_roms(roms)

    # Download thumbnails
    fetcher = BaseFetcher(config)
    thumbnail_fetcher = fetcher.get_plugin("libretro_thumbnails")

    if not thumbnail_fetcher:
        print("Error: Thumbnail fetcher not available")
        return 1

    output_dir = Path(config.get("thumbnails_path"))

    # Group ROMs by system
    systems = scanner.get_roms_by_system()

    for system_name, system_roms in systems.items():
        print(f"\nDownloading thumbnails for {system_name}...")

        # Only download for matched ROMs
        matched_roms = [rom for rom in system_roms if rom.matched and rom.game_name]

        if not matched_roms:
            print("  No matched ROMs, skipping")
            continue

        game_names = [rom.game_name for rom in matched_roms]
        thumbnail_fetcher.batch_download_thumbnails(
            system=system_name,
            game_names=game_names,
            output_dir=output_dir
        )

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
    parser_init.add_argument('path', nargs='?', help='RetroArch installation path')

    # Scan command
    parser_scan = subparsers.add_parser('scan', help='Scan ROM directory')
    parser_scan.add_argument('-p', '--path', help='Path to scan (uses config roms_path if not specified)')
    parser_scan.add_argument('-r', '--recursive', action='store_true', default=True, help='Scan subdirectories')
    parser_scan.add_argument('--no-crc', action='store_true', help='Skip CRC32 calculation')
    parser_scan.add_argument('-o', '--output', help='Export scan results to JSON file')
    parser_scan.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    # Match command
    parser_match = subparsers.add_parser('match', help='Match ROMs to game database')
    parser_match.add_argument('-v', '--verbose', action='store_true', help='Show unmatched ROMs')
    parser_match.add_argument('-s', '--similar', action='store_true', help='Show similar games for unmatched ROMs')

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
