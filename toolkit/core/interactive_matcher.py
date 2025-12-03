"""
Interactive Matcher Module
Interactive shell for matching unmatched ROMs using prompt_toolkit
"""

import os
import sys
import io
import time
import re
from pathlib import Path
from typing import Dict, List, Tuple
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

from .models import ROMInfo
from .matcher import ROMMatcher


class InteractiveMatcher:
    """Interactive shell for matching unmatched ROMs"""

    def __init__(self, config, matcher: ROMMatcher, unknown_games: Dict, manual_matches_path: Path):
        """Initialize interactive matcher

        Args:
            config: Config instance
            matcher: ROMMatcher instance
            unknown_games: Dictionary of unknown games from unknown_games.json
            manual_matches_path: Path to manual_matches.json
        """
        self.config = config
        self.matcher = matcher
        self.unknown_games = unknown_games
        self.manual_matches_path = manual_matches_path
        self.current_index = 0
        self.games_list = list(unknown_games.items())
        self.fixed_count = 0
        self.skipped_count = 0
        self._processed_roms = set()  # Track processed ROM indices

        # Create prompt session
        self.session = PromptSession()

        # Define custom style
        self.style = Style.from_dict({
            'prompt': '#00aa00 bold',
            'game-info': '#00aaaa',
            'match-info': '#888888',
            'success': '#00ff00',
            'warning': '#ffaa00',
            'error': '#ff0000',
        })

    def _enter_alternate_screen(self):
        """Enter alternate screen buffer (like vim/less)"""
        sys.stdout.write('\033[?1049h')  # Enable alternate screen
        sys.stdout.write('\033[H')        # Move cursor to top-left
        sys.stdout.flush()

    def _exit_alternate_screen(self):
        """Exit alternate screen buffer and restore original screen"""
        sys.stdout.write('\033[?1049l')  # Disable alternate screen
        sys.stdout.flush()

    def _clear_screen(self):
        """Clear the terminal screen"""
        sys.stdout.write('\033[2J')      # Clear screen
        sys.stdout.write('\033[H')        # Move cursor to top-left
        sys.stdout.flush()

    def _clear_lines(self, n: int):
        """Clear n lines up from current position"""
        for _ in range(n):
            print('\033[1A\033[2K', end='')  # Move up and clear line

    def run(self) -> int:
        """Run interactive matching loop

        Returns:
            Exit code (0 for success)
        """
        # Enter alternate screen buffer (like vim/less)
        self._enter_alternate_screen()

        try:
            # Show ROM selection menu (10 per page)
            while True:
                selected_indices = self._show_rom_selection_menu()

                if selected_indices is None:
                    # User quit
                    print("\nCancelled by user")
                    time.sleep(0.5)
                    return 0

                if not selected_indices:
                    # No more ROMs to process
                    break

                # Process selected ROMs
                for idx in selected_indices:
                    self._process_single_rom(idx)

            # Print summary
            self._print_summary()
            input("Press Enter to exit...")
            return 0

        finally:
            # Always exit alternate screen buffer to restore original screen
            self._exit_alternate_screen()

    def _show_rom_selection_menu(self) -> list:
        """Show ROM selection menu with pagination (10 per page)

        Returns:
            List of selected ROM indices, or None if quit
        """
        page = 0
        items_per_page = 10

        while True:
            # Clear screen for clean display
            self._clear_screen()

            print("=" * 60)
            print("Interactive ROM Matcher")
            print("=" * 60)
            print("Total unmatched: {} | Fixed: {} | Skipped: {}".format(
                len(self.games_list), self.fixed_count, self.skipped_count
            ))
            print("=" * 60)

            # Calculate pagination
            start_idx = page * items_per_page
            end_idx = min(start_idx + items_per_page, len(self.games_list))

            # Filter out already processed ROMs
            remaining_games = []

            for i in range(len(self.games_list)):
                if i not in self._processed_roms:
                    remaining_games.append(i)

            if not remaining_games:
                print("All ROMs have been processed!")
                input("Press Enter to continue...")
                return []

            # Get current page items
            page_items = remaining_games[start_idx:end_idx]

            # Display ROMs on current page
            print("Page {}/{}:".format(
                page + 1,
                (len(remaining_games) + items_per_page - 1) // items_per_page
            ))
            print()

            for i, rom_idx in enumerate(page_items, 1):
                _, rom_info = self.games_list[rom_idx]
                print("  {}. {} ({})".format(i, rom_info['filename'], rom_info['system']))

            print()
            print("=" * 60)
            print("Commands:")
            print("  1-10     - Select ROM to match")
            print("  a/all    - Match all on this page")
            print("  n/next   - Next page")
            print("  p/prev   - Previous page")
            print("  q/quit   - Quit")
            print("=" * 60)

            choice = self.session.prompt(
                HTML('<prompt>Choice: </prompt>'),
                style=self.style
            ).strip().lower()

            if choice in ['q', 'quit']:
                return None
            elif choice in ['n', 'next']:
                if end_idx < len(remaining_games):
                    page += 1
                else:
                    print("Already at last page")
                    time.sleep(0.5)
            elif choice in ['p', 'prev']:
                if page > 0:
                    page -= 1
                else:
                    print("Already at first page")
                    time.sleep(0.5)
            elif choice in ['a', 'all']:
                return page_items
            else:
                # Try to parse as number
                try:
                    idx = int(choice)
                    if 1 <= idx <= len(page_items):
                        return [page_items[idx - 1]]
                    else:
                        print("Invalid choice. Try 1-{}".format(len(page_items)))
                        time.sleep(0.5)
                except ValueError:
                    print("Invalid choice")
                    time.sleep(0.5)

    def _process_single_rom(self, rom_index: int):
        """Process a single ROM interactively

        Args:
            rom_index: Index in self.games_list
        """
        # Clear screen for clean display
        self._clear_screen()

        crc, rom_info = self.games_list[rom_index]

        # Convert dict to ROMInfo object
        rom = self._dict_to_rom_info(rom_info)

        # Show current ROM info
        current_position = len(self._processed_roms) + 1
        self._display_rom_info(rom, current_position, len(self.games_list))

        # Get similar games (limit to 5) - suppress database load messages
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            similar_games = self.matcher.find_similar_games(rom, limit=5)
        finally:
            sys.stdout = old_stdout

        # Interactive selection
        try:
            result = self._interactive_select(rom, similar_games)

            # Mark as processed
            self._processed_roms.add(rom_index)

            if result == 'quit':
                return
            elif result == 'skip':
                self.skipped_count += 1
                print("⊘ Skipped")
                time.sleep(0.3)
            elif isinstance(result, dict):
                # Matched successfully
                if self.matcher.save_manual_match(crc, result, rom_info):
                    # Show success message briefly
                    print("\n✓ Saved: {} -> {}".format(rom.filename, result.get('name')))
                    self.fixed_count += 1
                    # Pause briefly to show success
                    time.sleep(0.5)
                else:
                    print("\n✗ Failed to save match for {}".format(rom.filename))
                    input("Press Enter to continue...")
                    # Remove from processed if failed
                    self._processed_roms.remove(rom_index)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            # Don't mark as processed if interrupted
            if rom_index in self._processed_roms:
                self._processed_roms.remove(rom_index)
            return
        except Exception as e:
            print("\nError: {}".format(e))
            input("Press Enter to continue...")
            # Don't mark as processed if error
            if rom_index in self._processed_roms:
                self._processed_roms.remove(rom_index)



    def _dict_to_rom_info(self, rom_dict: Dict) -> ROMInfo:
        """Convert dictionary to ROMInfo object

        Args:
            rom_dict: ROM info as dictionary

        Returns:
            ROMInfo object
        """
        file_path = Path(rom_dict['path'])
        return ROMInfo(
            path=rom_dict['path'],
            filename=rom_dict['filename'],
            system=rom_dict['system'],
            extension=file_path.suffix,
            size=rom_dict.get('size', 0),
            size_formatted=rom_dict.get('size_formatted', '0 B'),
            crc32=rom_dict.get('crc32'),
            normalized_name=rom_dict.get('normalized_name', ''),
            region=rom_dict.get('region')
        )

    def _display_rom_info(self, rom: ROMInfo, current: int, total: int):
        """Display current ROM information (compact, no extra newlines)

        Args:
            rom: ROMInfo object
            current: Current ROM index
            total: Total number of ROMs
        """
        print("=" * 60)
        print("[{}/{}] {} ({})".format(current, total, rom.filename, rom.system))
        print("CRC32: {} | Region: {}".format(rom.crc32 or 'N/A', rom.region or 'N/A'))
        print("=" * 60)

    def _display_similar_games(self, similar_games: List[Tuple[Dict, float]], quiet: bool = False):
        """Display list of similar games (compact, max 5 items)

        Args:
            similar_games: List of (game_entry, score) tuples (max 5)
            quiet: If True, suppress output (for loading databases)
        """
        if quiet:
            return

        if not similar_games:
            print("⚠️  No similar games found")
            return

        print("Similar games:")
        for i, (entry, score) in enumerate(similar_games[:5], 1):
            name = entry.get('name', 'Unknown')
            region = entry.get('region', 'N/A')
            year = entry.get('releaseyear', 'N/A')

            # Color indicator based on similarity
            if score > 0.8:
                marker = "🟢"
            elif score > 0.6:
                marker = "🟡"
            else:
                marker = "🔴"

            print("  {} {}. {} | {} | {} | {:.1%}".format(
                marker, i, name, region, year, score
            ))

    def _interactive_select(self, rom: ROMInfo, similar_games: List[Tuple[Dict, float]]) -> any:
        """Interactive selection using arrow keys or commands

        Args:
            rom: ROMInfo object
            similar_games: List of similar games

        Returns:
            Selected game dict, or command string ('skip', 'quit', 'all')
        """
        self._display_similar_games(similar_games)

        if not similar_games:
            # No matches found - allow skip
            print("Commands: s (search local) | o (search online) | n (skip) | q (quit)")
            while True:
                choice = self.session.prompt(
                    HTML('<prompt>Choice: </prompt>'),
                    style=self.style
                ).strip().lower()

                if choice in ['n', 'skip', '']:
                    return 'skip'
                elif choice in ['q', 'quit']:
                    return 'quit'
                elif choice in ['s', 'search']:
                    return self._custom_search(rom)
                elif choice in ['o', 'online']:
                    return self._online_search(rom)
                else:
                    print("Invalid choice. Try: s/o/n/q")
        else:
            # Has matches - show selection
            print("Commands: 1-5 (select) | s (search local) | o (search online) | n (skip) | q (quit)")

            completer = WordCompleter(['search', 's', 'online', 'o', 'skip', 'n', 'quit', 'q'] +
                                    [str(i) for i in range(1, 6)], ignore_case=True)

            while True:
                choice = self.session.prompt(
                    HTML('<prompt>Choice: </prompt>'),
                    style=self.style,
                    completer=completer
                ).strip().lower()

                if choice in ['q', 'quit']:
                    return 'quit'
                elif choice in ['n', 'skip', '']:
                    return 'skip'
                elif choice in ['s', 'search']:
                    return self._custom_search(rom)
                elif choice in ['o', 'online']:
                    return self._online_search(rom)
                else:
                    # Try to parse as number
                    try:
                        idx = int(choice)
                        if 1 <= idx <= len(similar_games):
                            return similar_games[idx - 1][0]
                        else:
                            print("Invalid number. Choose 1-{}".format(len(similar_games)))
                    except ValueError:
                        print("Invalid choice. Try: 1-5/s/o/n/q")

    def _custom_search(self, rom: ROMInfo) -> any:
        """Custom search for games

        Args:
            rom: ROMInfo object

        Returns:
            Selected game entry or 'skip'
        """
        query = self.session.prompt(
            HTML('<prompt>Search query: </prompt>'),
            style=self.style
        ).strip()

        if not query:
            return 'skip'

        # Clear and show search screen
        self._clear_screen()
        print("=" * 60)
        print("Search Results: {}".format(query))
        print("=" * 60)

        system = rom.system

        if system not in self.matcher.databases:
            if not self.matcher.load_database(system):
                print("Cannot load database for {}".format(system))
                input("Press Enter to continue...")
                return 'skip'

        database = self.matcher.databases[system]

        # Search for entries
        entries = []
        if database['type'] == 'rdb':
            try:
                entries = self.matcher.rdb_query.find_by_name_glob(database['path'], '*{}*'.format(query))
            except Exception as e:
                print("Error: {}".format(e))
                input("Press Enter to continue...")
                return 'skip'
        else:
            query_lower = query.lower()
            for entry in database['data']:
                entry_name = entry.get('name', '').lower()
                if query_lower in entry_name:
                    entries.append(entry)

        if not entries:
            print("No results found")
            input("Press Enter to continue...")
            return 'skip'

        # Show results (max 10)
        display_limit = min(10, len(entries))
        for i, entry in enumerate(entries[:display_limit], 1):
            name = entry.get('name', 'Unknown')
            region = entry.get('region', 'N/A')
            year = entry.get('releaseyear', 'N/A')
            print("  {}. {} | {} | {}".format(i, name, region, year))

        if len(entries) > display_limit:
            print("  ... and {} more results".format(len(entries) - display_limit))

        print("  0. Cancel")
        print("=" * 60)

        # Get selection
        while True:
            try:
                choice = self.session.prompt(
                    HTML('<prompt>Select [0-{}]: </prompt>'.format(display_limit)),
                    style=self.style
                ).strip()

                idx = int(choice)
                if idx == 0:
                    return 'skip'
                elif 1 <= idx <= len(entries):
                    return entries[idx - 1]
                else:
                    print("Invalid choice. Try again.")
            except ValueError:
                print("Please enter a number")
            except (EOFError, KeyboardInterrupt):
                raise

    def _online_search(self, rom: ROMInfo) -> any:
        """Search online databases (LaunchBox/No-Intro)

        Args:
            rom: ROMInfo object

        Returns:
            Selected game entry or 'skip'
        """
        # Ask for search query (default to ROM name)
        default_query = rom.normalized_name or rom.filename
        query = self.session.prompt(
            HTML('<prompt>Search query [{}]: </prompt>'.format(default_query)),
            style=self.style
        ).strip()

        if not query:
            query = default_query

        # Clear and show search screen
        self._clear_screen()
        print("=" * 60)
        print("Online Search: {}".format(query))
        print("=" * 60)
        print("Searching LaunchBox...")

        # Import LaunchBox plugin
        try:
            from ..plugins.launchbox import LaunchBoxFetcher

            launchbox = LaunchBoxFetcher(self.config.get("fetch_sources", {}).get("launchbox", {}))

            # Search LaunchBox
            result = launchbox.search_game(query, rom.system)
            
            if result.success and result.data:
                entries = result.data

                if not entries:
                    print("No results found on LaunchBox")
                    input("Press Enter to continue...")
                    return 'skip'
                else:
                    print("Found {} results on LaunchBox".format(len(entries)))
                    print()

                    # Show results (max 15)
                    display_limit = min(15, len(entries))
                    for i, entry in enumerate(entries[:display_limit], 1):
                        name = entry.get('name', 'Unknown')
                        platform = entry.get('platform', 'N/A')
                        year = entry.get('releaseyear', 'N/A')
                        print("  {}. {} | {}{}".format(
                            i, name, platform,
                            " | {}".format(year) if year != 'N/A' else ''
                        ))

                    if len(entries) > display_limit:
                        print("  ... and {} more results".format(len(entries) - display_limit))

                    print()
                    print("  0. Cancel")
                    print("=" * 60)

                    # Get selection
                    while True:
                        try:
                            choice = self.session.prompt(
                                HTML('<prompt>Select [0-{}]: </prompt>'.format(display_limit)),
                                style=self.style
                            ).strip()

                            idx = int(choice)
                            if idx == 0:
                                return 'skip'
                            elif 1 <= idx <= len(entries):
                                selected = entries[idx - 1]

                                # Build LaunchBox details URL
                                game_key = selected.get('id', '')
                                game_name = selected.get('name', '').replace(' ', '-').lower()
                                # URL encode and clean the name
                                game_name_clean = re.sub(r'[^a-z0-9-]', '', game_name)
                                details_url = "https://gamesdb.launchbox-app.com/games/details/{}-{}".format(
                                    game_key, game_name_clean
                                )

                                # Convert LaunchBox format to local DB format
                                converted = {
                                    'name': selected.get('name', ''),
                                    'region': selected.get('region', 'N/A'),
                                    'releaseyear': selected.get('releaseyear', 'N/A'),
                                    'developer': selected.get('developer', ''),
                                    'publisher': selected.get('publisher', ''),
                                    'crc': '',  # LaunchBox doesn't provide CRC
                                    'launchbox_url': details_url,  # Add LaunchBox URL for reference
                                    'launchbox_id': game_key,
                                    'source': 'launchbox'  # Mark as from LaunchBox
                                }
                                return converted
                            else:
                                print("Invalid choice")
                        except ValueError:
                            print("Please enter a number")
                        except (EOFError, KeyboardInterrupt):
                            raise
            else:
                print("Error searching LaunchBox: {}".format(result.error if hasattr(result, 'error') else 'Unknown error'))
                input("Press Enter to continue...")
                return 'skip'

        except Exception as e:
            print("Error: {}".format(e))
            input("Press Enter to continue...")
            return 'skip'

    def _print_summary(self):
        """Print matching session summary"""
        self._clear_screen()
        print("=" * 60)
        print("Matching Summary")
        print("=" * 60)
        print("Fixed:   {}".format(self.fixed_count))
        print("Skipped: {}".format(self.skipped_count))
        print("Total:   {}".format(len(self.games_list)))
        print()
        print("Manual matches: {}".format(self.manual_matches_path))
        print("=" * 60)
        print()
