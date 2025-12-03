"""
RetroArch Toolkit Core Module
"""

from .utils import calculate_crc32, normalize_rom_name, is_hack_version
from .models import ROMInfo
from .scanner import ROMScanner
from .matcher import ROMMatcher
from .playlist import PlaylistGenerator
from .fetcher import BaseFetcher, FetchPlugin, FetchResult
from .rdb_query import LibretroDBQuery

__all__ = [
    'calculate_crc32',
    'normalize_rom_name',
    'is_hack_version',
    'ROMInfo',
    'ROMScanner',
    'ROMMatcher',
    'PlaylistGenerator',
    'BaseFetcher',
    'FetchPlugin',
    'FetchResult',
    'LibretroDBQuery'
]
