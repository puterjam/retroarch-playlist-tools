"""
RetroArch Toolkit Plugins Module
Provides extensible plugin system for fetching game data from various sources
"""

from ..core.fetcher import BaseFetcher, FetchResult, FetchPlugin
from .retroarch_db import RetroArchDBFetcher
from .libretro_thumbnails import LibretroThumbnailsFetcher
from .launchbox import LaunchBoxFetcher

__all__ = [
    'BaseFetcher',
    'FetchResult',
    'FetchPlugin',
    'RetroArchDBFetcher',
    'LibretroThumbnailsFetcher',
    'LaunchBoxFetcher'
]
