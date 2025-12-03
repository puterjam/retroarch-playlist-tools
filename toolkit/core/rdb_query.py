"""
LibretroRDB Query Module
Wrapper for libretrodb_tool to query game databases
"""

import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Union


class LibretroDBQuery:
    """Query interface for LibretroRDB database files"""

    def __init__(self, tool_path: Optional[str] = None):
        """Initialize RDB query tool

        Args:
            tool_path: Path to libretrodb_tool executable (auto-detect if None)
        """
        if tool_path is None:
            # Auto-detect tool path relative to this file
            tool_path = Path(__file__).parent.parent.parent / "tools" / "libretrodb_tool"

        self.tool_path = Path(tool_path)

        if not self.tool_path.exists():
            raise FileNotFoundError(f"libretrodb_tool not found: {self.tool_path}")

        if not self.tool_path.is_file():
            raise ValueError(f"libretrodb_tool is not a file: {self.tool_path}")

    def _run_command(self, db_path: Path, command: str, *args) -> str:
        """Run libretrodb_tool command

        Args:
            db_path: Path to RDB database file
            command: Command to execute (list, find, get-names, create-index)
            *args: Additional command arguments

        Returns:
            Command output as string

        Raises:
            FileNotFoundError: If database file not found
            RuntimeError: If command execution fails
        """
        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")

        cmd = [str(self.tool_path), str(db_path), command] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False  # Don't check exit code, libretrodb_tool returns 1 even on success
        )
        # libretrodb_tool returns exit code 1 even when successfully outputting data
        # Empty output is valid (no results found) and should not raise an error
        # Only raise an error if there's stderr output indicating a real problem
        if result.returncode != 0 and result.stderr.strip():
            raise RuntimeError(f"libretrodb_tool error: {result.stderr}")

        return result.stdout

    def _parse_output(self, output: str) -> List[Dict]:
        """Parse libretrodb_tool output into structured data

        Args:
            output: Raw output from libretrodb_tool

        Returns:
            List of game entry dictionaries
        """
        entries = []

        # The libretrodb_tool outputs JSON format (one entry per line)
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            try:
                # Parse JSON entry
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                # If JSON parsing fails, skip this line
                continue

        return entries

    def list_all(self, db_path: Union[str, Path]) -> List[Dict]:
        """List all entries in database

        Args:
            db_path: Path to RDB database file

        Returns:
            List of all game entries
        """
        output = self._run_command(Path(db_path), "list")
        return self._parse_output(output)

    def find_by_crc32(self, db_path: Union[str, Path], crc32: str) -> Optional[Dict]:
        """Find game by CRC32 checksum

        Args:
            db_path: Path to RDB database file
            crc32: CRC32 checksum (hex string, e.g., '31B965DB')

        Returns:
            Game entry or None if not found
        """
        # Ensure CRC32 is uppercase and without '0x' prefix
        crc32 = crc32.upper().replace('0X', '')

        query = f"{{'crc':b'{crc32}'}}"
        output = self._run_command(Path(db_path), "find", query)

        entries = self._parse_output(output)
        return entries[0] if entries else None

    def find_by_md5(self, db_path: Union[str, Path], md5: str) -> Optional[Dict]:
        """Find game by MD5 checksum

        Args:
            db_path: Path to RDB database file
            md5: MD5 checksum (hex string)

        Returns:
            Game entry or None if not found
        """
        md5 = md5.upper()
        query = f"{{'md5':b'{md5}'}}"
        output = self._run_command(Path(db_path), "find", query)

        entries = self._parse_output(output)
        return entries[0] if entries else None

    def find_by_sha1(self, db_path: Union[str, Path], sha1: str) -> Optional[Dict]:
        """Find game by SHA1 checksum

        Args:
            db_path: Path to RDB database file
            sha1: SHA1 checksum (hex string)

        Returns:
            Game entry or None if not found
        """
        sha1 = sha1.upper()
        query = f"{{'sha1':b'{sha1}'}}"
        output = self._run_command(Path(db_path), "find", query)

        entries = self._parse_output(output)
        return entries[0] if entries else None

    def find_by_serial(self, db_path: Union[str, Path], serial: str) -> Optional[Dict]:
        """Find game by serial number

        Args:
            db_path: Path to RDB database file
            serial: Serial number (e.g., 'SLUS-01234')

        Returns:
            Game entry or None if not found
        """
        query = f"{{'serial':'{serial}'}}"
        output = self._run_command(Path(db_path), "find", query)

        entries = self._parse_output(output)
        return entries[0] if entries else None

    def find_by_name_glob(self, db_path: Union[str, Path], name_pattern: str) -> List[Dict]:
        """Find games by name pattern (glob matching)

        Args:
            db_path: Path to RDB database file
            name_pattern: Name pattern with wildcards (e.g., 'Street Fighter*')

        Returns:
            List of matching game entries
        """
        query = f"{{'name':glob('{name_pattern}')}}"
        output = self._run_command(Path(db_path), "find", query)
        return self._parse_output(output)

    def find_by_release_date(self, db_path: Union[str, Path],
                            year: Optional[int] = None,
                            month: Optional[int] = None) -> List[Dict]:
        """Find games by release date

        Args:
            db_path: Path to RDB database file
            year: Release year (e.g., 1995)
            month: Release month (1-12)

        Returns:
            List of matching game entries
        """
        conditions = []

        if year is not None:
            conditions.append(f"'releaseyear':{year}")

        if month is not None:
            conditions.append(f"'releasemonth':{month}")

        if not conditions:
            raise ValueError("Must specify at least year or month")

        query = "{" + ",".join(conditions) + "}"
        output = self._run_command(Path(db_path), "find", query)

        return self._parse_output(output)

    def find_by_developer(self, db_path: Union[str, Path], developer: str) -> List[Dict]:
        """Find games by developer (glob matching)

        Args:
            db_path: Path to RDB database file
            developer: Developer name pattern (e.g., 'Nintendo*')

        Returns:
            List of matching game entries
        """
        query = f"{{'developer':glob('{developer}')}}"
        output = self._run_command(Path(db_path), "find", query)

        return self._parse_output(output)

    def find_by_publisher(self, db_path: Union[str, Path], publisher: str) -> List[Dict]:
        """Find games by publisher (glob matching)

        Args:
            db_path: Path to RDB database file
            publisher: Publisher name pattern (e.g., 'Capcom*')

        Returns:
            List of matching game entries
        """
        query = f"{{'publisher':glob('{publisher}')}}"
        output = self._run_command(Path(db_path), "find", query)

        return self._parse_output(output)

    def find_by_query(self, db_path: Union[str, Path], query: str) -> List[Dict]:
        """Execute custom query

        Args:
            db_path: Path to RDB database file
            query: Custom query expression (e.g., "{'name':glob('Mario*'),'releaseyear':1996}")

        Returns:
            List of matching game entries
        """
        output = self._run_command(Path(db_path), "find", query)
        return self._parse_output(output)

    def get_names_only(self, db_path: Union[str, Path], query: str) -> List[str]:
        """Get only game names matching query

        Args:
            db_path: Path to RDB database file
            query: Query expression

        Returns:
            List of game names
        """
        output = self._run_command(Path(db_path), "get-names", query)

        # Parse names from output
        names = []
        for line in output.strip().split('\n'):
            line = line.strip()
            if line:
                names.append(line)

        return names

    def create_index(self, db_path: Union[str, Path],
                    index_name: str, field_name: str) -> bool:
        """Create index on database field

        Args:
            db_path: Path to RDB database file
            index_name: Name for the index
            field_name: Field to index

        Returns:
            True if successful
        """
        try:
            self._run_command(Path(db_path), "create-index", index_name, field_name)
            return True
        except RuntimeError:
            return False

    def check_db_exists(self, db_path: Union[str, Path]) -> bool:
        """Check if database file exists and is readable

        Args:
            db_path: Path to RDB database file

        Returns:
            True if database exists and is readable
        """
        try:
            # Try to list first entry to verify DB is valid
            self._run_command(Path(db_path), "list")
            return True
        except (FileNotFoundError, RuntimeError):
            return False
