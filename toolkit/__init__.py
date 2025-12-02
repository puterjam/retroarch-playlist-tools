"""
RetroArch Toolkit
A tool for managing RetroArch playlists and ROM collections
"""

__version__ = "1.0.0"
__author__ = "RetroArch Toolkit Contributors"

from .config import Config
from .core import ROMScanner, ROMMatcher, PlaylistGenerator, BaseFetcher

__all__ = [
    'Config',
    'ROMScanner',
    'ROMMatcher',
    'PlaylistGenerator',
    'BaseFetcher'
]
