"""
Core utility functions for ROM processing
"""

import re
import zlib
from pathlib import Path
from typing import Optional, Tuple
import zipfile


def calculate_crc32(file_path: Path) -> Optional[str]:
    """Calculate CRC32 checksum for a file

    Args:
        file_path: Path to the file

    Returns:
        CRC32 checksum as hex string, or None if error
    """
    try:
        # Handle compressed files
        if file_path.suffix.lower() == '.zip':
            return _calculate_crc32_zip(file_path)
        elif file_path.suffix.lower() == '.7z':
            return _calculate_crc32_7z(file_path)
        else:
            return _calculate_crc32_file(file_path)
    except Exception as e:
        print(f"Error calculating CRC32 for {file_path}: {e}")
        return None


def _calculate_crc32_file(file_path: Path) -> str:
    """Calculate CRC32 for a regular file"""
    crc = 0
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):  # Read in 64KB chunks
            crc = zlib.crc32(chunk, crc)
    return f"{crc & 0xFFFFFFFF:08x}".upper()


def _calculate_crc32_zip(file_path: Path) -> Optional[str]:
    """Calculate CRC32 for the first ROM file in a ZIP archive"""
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            # Find first ROM file (skip directories and non-ROM files)
            rom_extensions = {'.nes', '.smc', '.sfc', '.gb', '.gbc', '.gba', '.md', '.smd', '.gen', '.bin'}
            for info in zf.infolist():
                if not info.is_dir() and Path(info.filename).suffix.lower() in rom_extensions:
                    # ZIP file already has CRC32 in the file info
                    return f"{info.CRC:08x}".upper()
        return None
    except Exception as e:
        print(f"Error reading ZIP file {file_path}: {e}")
        return None


def _calculate_crc32_7z(file_path: Path) -> Optional[str]:
    """Calculate CRC32 for 7z files

    Note: Requires py7zr package
    """
    try:
        import py7zr
        with py7zr.SevenZipFile(file_path, 'r') as archive:
            rom_extensions = {'.nes', '.smc', '.sfc', '.gb', '.gbc', '.gba', '.md', '.smd', '.gen', '.bin'}
            for name, bio in archive.readall().items():
                if Path(name).suffix.lower() in rom_extensions:
                    crc = 0
                    data = bio.read()
                    crc = zlib.crc32(data, crc)
                    return f"{crc & 0xFFFFFFFF:08x}".upper()
        return None
    except ImportError:
        print("Warning: py7zr not installed. Cannot calculate CRC32 for .7z files")
        return None
    except Exception as e:
        print(f"Error reading 7z file {file_path}: {e}")
        return None


def normalize_rom_name(filename: str) -> str:
    """Normalize ROM filename for matching

    Removes region codes, revision info, and other metadata

    Args:
        filename: Original filename

    Returns:
        Normalized filename
    """
    # Remove file extension
    name = Path(filename).stem

    # Common patterns to remove
    patterns = [
        r'\([^)]*\)',  # Remove anything in parentheses (region, etc.)
        r'\[[^\]]*\]',  # Remove anything in square brackets
        r'\{[^}]*\}',   # Remove anything in curly braces
        r'\s+v?\d+\.?\d*$',  # Remove version numbers at end
        r'\s+-\s+.*$',  # Remove everything after dash
    ]

    for pattern in patterns:
        name = re.sub(pattern, '', name)

    # Clean up whitespace
    name = ' '.join(name.split())
    name = name.strip(' -_')

    return name


def is_hack_version(filename: str) -> Tuple[bool, Optional[str]]:
    """Detect if ROM is a hack/mod version and extract base game name

    Args:
        filename: ROM filename

    Returns:
        Tuple of (is_hack, base_game_name)
    """
    name = filename.lower()

    # Patterns indicating hacks
    hack_patterns = [
        r'\bhack\b',
        r'\bmod\b',
        r'\btranslation\b',
        r'\btrans\b',
        r'\bpatch\b',
        r'\bhomebrew\b',
        r'\bunlicensed\b',
        r'\bpirate\b',
        r'\b\[h\d*\]',  # [h], [h1], etc.
        r'\b\[t\+?\d*\]',  # [t], [t+], [t1], etc.
        r'\b\[p\d*\]',  # [p], [p1], etc.
    ]

    is_hack = any(re.search(pattern, name) for pattern in hack_patterns)

    if is_hack:
        # Try to extract base game name
        base_name = normalize_rom_name(filename)
        return True, base_name

    return False, None


def extract_region_info(filename: str) -> Optional[str]:
    """Extract region information from ROM filename

    Args:
        filename: ROM filename

    Returns:
        Region code (e.g., 'USA', 'Japan', 'Europe') or None
    """
    # Common region patterns
    region_patterns = {
        'USA': [r'\(USA\)', r'\(U\)', r'\(US\)'],
        'Japan': [r'\(Japan\)', r'\(J\)', r'\(JP\)'],
        'Europe': [r'\(Europe\)', r'\(E\)', r'\(EU\)'],
        'World': [r'\(World\)', r'\(W\)'],
        'Asia': [r'\(Asia\)', r'\(A\)'],
        'Korea': [r'\(Korea\)', r'\(K\)'],
        'China': [r'\(China\)', r'\(C\)'],
    }

    for region, patterns in region_patterns.items():
        for pattern in patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                return region

    return None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., '1.5 MB')
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')

    return filename
